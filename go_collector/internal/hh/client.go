package hh

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"sync"
	"time"

	"github.com/evenikkal/hhanalyst/go_collector/internal/models"
)

// nonRetryableError marks an HTTP client error (4xx other than 429)
// that will never succeed on retry.
type nonRetryableError struct{ code int }

func (e *nonRetryableError) Error() string {
	return fmt.Sprintf("hh API returned %d (non-retryable)", e.code)
}

const (
	defaultBaseURL = "https://api.hh.ru"
	poolSize       = 5
	pageSize       = 100
	maxRetries     = 3                      // attempts per page before giving up
	retryBackoff   = 500 * time.Millisecond // base delay, grows linearly per attempt
)

// job is a unit of work sent to the worker pool.
type job struct {
	Query string
	Area  string
	Page  int
	Resp  chan<- jobResult
}

// jobResult carries the outcome of a single page fetch.
type jobResult struct {
	Page  int
	Items []models.Vacancy
	Err   error
}

// Client is an hh.ru API client backed by a persistent worker pool.
// Workers are started once via NewClient and live for the lifetime of
// the process, waiting for jobs on an internal channel.
type Client struct {
	http    *http.Client
	baseURL string
	limiter <-chan time.Time
	jobs    chan job
}

// NewClient creates a client and starts poolSize background workers.
func NewClient() *Client {
	pool, err := x509.SystemCertPool()
	if err != nil || pool == nil {
		pool = x509.NewCertPool()
	}
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			RootCAs: pool,
		},
	}

	c := &Client{
		http:    &http.Client{Timeout: 15 * time.Second, Transport: transport},
		baseURL: defaultBaseURL,
		limiter: time.Tick(250 * time.Millisecond), // 4 req/s
		jobs:    make(chan job, poolSize*2),
	}

	// Start persistent workers — they block on c.jobs and live forever.
	for i := 0; i < poolSize; i++ {
		go c.worker(i)
	}
	log.Printf("started %d background workers", poolSize)

	return c
}

// worker is a long-lived goroutine that pulls jobs from the shared channel.
func (c *Client) worker(id int) {
	for j := range c.jobs {
		result, err := c.fetchPage(j.Query, j.Area, j.Page)
		if err != nil {
			j.Resp <- jobResult{Page: j.Page, Err: err}
		} else {
			j.Resp <- jobResult{Page: j.Page, Items: result.Items}
		}
	}
}

// fetchPage requests one page of /vacancies, retrying on transient
// failures (network errors, HTTP 429 and 5xx). Each attempt is
// rate-limited via the shared limiter; the back-off between attempts
// grows linearly and honours the Retry-After header when present.
func (c *Client) fetchPage(query, area string, page int) (*models.SearchResponse, error) {
	var lastErr error
	for attempt := 1; attempt <= maxRetries; attempt++ {
		result, retryAfter, err := c.tryFetchPage(query, area, page)
		if err == nil {
			return result, nil
		}
		lastErr = err

		// Client errors (4xx other than 429) will never succeed — stop now.
		var nre *nonRetryableError
		if errors.As(err, &nre) {
			return nil, err
		}

		if attempt == maxRetries {
			break
		}
		// Linear back-off, but never shorter than the server's Retry-After.
		wait := time.Duration(attempt) * retryBackoff
		if retryAfter > wait {
			wait = retryAfter
		}
		log.Printf("page %d attempt %d/%d failed: %v — retrying in %s",
			page, attempt, maxRetries, err, wait)
		time.Sleep(wait)
	}
	return nil, fmt.Errorf("page %d: all %d attempts failed: %w", page, maxRetries, lastErr)
}

// tryFetchPage performs a single rate-limited request. It returns a
// non-zero retryAfter when the server asked us to slow down (HTTP 429).
func (c *Client) tryFetchPage(query, area string, page int) (*models.SearchResponse, time.Duration, error) {
	<-c.limiter

	params := url.Values{}
	params.Set("text", query)
	params.Set("per_page", fmt.Sprintf("%d", pageSize))
	params.Set("page", fmt.Sprintf("%d", page))
	params.Set("only_with_salary", "false")
	if area != "" {
		params.Set("area", area)
	}

	req, err := http.NewRequest("GET", c.baseURL+"/vacancies?"+params.Encode(), nil)
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("User-Agent", "hhanalyst/1.0 (evenikkal@github)")
	req.Header.Set("HH-User-Agent", "hhanalyst/1.0 (evenikkal@github)")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, 0, err // transient network error — caller will retry
	}
	defer resp.Body.Close()

	switch {
	case resp.StatusCode == http.StatusOK:
		// fall through to body parsing below
	case resp.StatusCode == http.StatusTooManyRequests:
		return nil, parseRetryAfter(resp.Header.Get("Retry-After")),
			fmt.Errorf("hh API rate-limited (429)")
	case resp.StatusCode >= 500:
		return nil, 0, fmt.Errorf("hh API server error %d", resp.StatusCode)
	default:
		// 4xx other than 429 is a client error — do not retry.
		return nil, 0, &nonRetryableError{code: resp.StatusCode}
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, 0, err
	}

	var result models.SearchResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, 0, err
	}
	return &result, 0, nil
}

// parseRetryAfter reads a Retry-After header given as integer seconds.
func parseRetryAfter(h string) time.Duration {
	if h == "" {
		return 0
	}
	if secs, err := strconv.Atoi(h); err == nil && secs > 0 {
		return time.Duration(secs) * time.Second
	}
	return 0
}

// Collect fetches up to maxPages pages by dispatching work to the pool.
// The first page is fetched inline to learn the total page count,
// then remaining pages are fanned out to the background workers.
func (c *Client) Collect(query, area string, maxPages int) ([]models.Vacancy, error) {
	first, err := c.fetchPage(query, area, 0)
	if err != nil {
		return nil, err
	}

	total := first.Pages
	if total > maxPages {
		total = maxPages
	}

	results := make([][]models.Vacancy, total)
	results[0] = first.Items

	if total <= 1 {
		return results[0], nil
	}

	// Fan out remaining pages to the worker pool.
	pending := total - 1
	respCh := make(chan jobResult, pending)

	for p := 1; p < total; p++ {
		c.jobs <- job{
			Query: query,
			Area:  area,
			Page:  p,
			Resp:  respCh,
		}
	}

	// Collect results.
	var mu sync.Mutex
	var collectErr error
	for i := 0; i < pending; i++ {
		r := <-respCh
		mu.Lock()
		if r.Err != nil && collectErr == nil {
			collectErr = r.Err
		} else if r.Err == nil {
			results[r.Page] = r.Items
		}
		mu.Unlock()
	}

	if collectErr != nil {
		return nil, collectErr
	}

	var all []models.Vacancy
	for _, r := range results {
		all = append(all, r...)
	}
	return all, nil
}
