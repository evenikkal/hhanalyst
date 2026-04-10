package hh

import (
	"crypto/tls"
	"crypto/x509"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/evenikkal/hhanalyst/go_collector/internal/models"
)

const (
	defaultBaseURL = "https://api.hh.ru"
	maxWorkers     = 5
	pageSize       = 100
)

type Client struct {
	http    *http.Client
	baseURL string
	limiter <-chan time.Time
}

func NewClient() *Client {
	// Explicitly load the system certificate pool to ensure TLS works
	// on all platforms (including Windows where the default may fail).
	pool, err := x509.SystemCertPool()
	if err != nil || pool == nil {
		pool = x509.NewCertPool()
	}
	transport := &http.Transport{
		TLSClientConfig: &tls.Config{
			RootCAs: pool,
		},
	}
	return &Client{
		http:    &http.Client{Timeout: 15 * time.Second, Transport: transport},
		baseURL: defaultBaseURL,
		limiter: time.Tick(250 * time.Millisecond),
	}
}

func (c *Client) searchPage(query, area string, page int) (*models.SearchResponse, error) {
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
		return nil, err
	}
	req.Header.Set("User-Agent", "hhanalyst/1.0 (evenikkal@github)")
	req.Header.Set("HH-User-Agent", "hhanalyst/1.0 (evenikkal@github)")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("hh API returned %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result models.SearchResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

// Collect fetches up to maxPages pages in parallel for the given query.
func (c *Client) Collect(query, area string, maxPages int) ([]models.Vacancy, error) {
	first, err := c.searchPage(query, area, 0)
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

	type job struct {
		page int
	}
	jobs := make(chan job, total-1)
	for p := 1; p < total; p++ {
		jobs <- job{p}
	}
	close(jobs)

	var mu sync.Mutex
	var wg sync.WaitGroup
	var collectErr error

	workers := maxWorkers
	if total-1 < workers {
		workers = total - 1
	}

	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs {
				page, err := c.searchPage(query, area, j.page)
				mu.Lock()
				if err != nil && collectErr == nil {
					collectErr = err
				} else if err == nil {
					results[j.page] = page.Items
				}
				mu.Unlock()
			}
		}()
	}
	wg.Wait()

	if collectErr != nil {
		return nil, collectErr
	}

	var all []models.Vacancy
	for _, r := range results {
		all = append(all, r...)
	}
	return all, nil
}
