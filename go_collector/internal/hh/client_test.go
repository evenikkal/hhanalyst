package hh

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/evenikkal/hhanalyst/go_collector/internal/models"
)

func newTestClient(baseURL string) *Client {
	return &Client{
		http:    &http.Client{Timeout: 5 * time.Second},
		baseURL: baseURL,
		limiter: time.Tick(1 * time.Millisecond),
	}
}

func TestCollectSinglePage(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/vacancies" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		resp := models.SearchResponse{
			Items: []models.Vacancy{
				{ID: "1", Name: "Go Developer", Area: models.Area{ID: "1", Name: "Moscow"}},
				{ID: "2", Name: "Senior Go", Area: models.Area{ID: "2", Name: "SPb"}},
			},
			Found: 2,
			Pages: 1,
			Page:  0,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	c := newTestClient(srv.URL)
	vacancies, err := c.Collect("Go", "", 5)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}
	if len(vacancies) != 2 {
		t.Fatalf("expected 2 vacancies, got %d", len(vacancies))
	}
	if vacancies[0].Name != "Go Developer" {
		t.Errorf("expected 'Go Developer', got %q", vacancies[0].Name)
	}
}

func TestCollectMultiplePages(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		page := r.URL.Query().Get("page")
		resp := models.SearchResponse{
			Items: []models.Vacancy{
				{ID: page + "1", Name: "Dev page " + page},
			},
			Found: 200,
			Pages: 3,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	c := newTestClient(srv.URL)
	vacancies, err := c.Collect("test", "", 3)
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}
	if len(vacancies) != 3 {
		t.Fatalf("expected 3 vacancies (1 per page x 3 pages), got %d", len(vacancies))
	}
}

func TestCollectAPIError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusTooManyRequests)
	}))
	defer srv.Close()

	c := newTestClient(srv.URL)
	_, err := c.Collect("test", "", 1)
	if err == nil {
		t.Fatal("expected error for 429 response, got nil")
	}
}

func TestVacancyModelJSON(t *testing.T) {
	raw := `{
		"id": "99",
		"name": "Python Analyst",
		"area": {"id": "2", "name": "Saint Petersburg"},
		"salary": {"from": 150000, "to": null, "currency": "RUR"},
		"snippet": {"requirement": "Python, NLP", "responsibility": "data analysis"},
		"experience": {"id": "between1And3", "name": "От 1 года до 3 лет"}
	}`
	var v models.Vacancy
	if err := json.Unmarshal([]byte(raw), &v); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if v.ID != "99" {
		t.Errorf("expected ID=99, got %s", v.ID)
	}
	if v.Salary == nil || *v.Salary.From != 150000 {
		t.Error("salary not parsed correctly")
	}
	if v.Area.Name != "Saint Petersburg" {
		t.Errorf("expected SPb, got %s", v.Area.Name)
	}
}

func TestQueryParamsPassedThrough(t *testing.T) {
	var gotArea, gotText string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotArea = r.URL.Query().Get("area")
		gotText = r.URL.Query().Get("text")
		resp := models.SearchResponse{Pages: 1, Items: []models.Vacancy{{ID: "1"}}}
		json.NewEncoder(w).Encode(resp)
	}))
	defer srv.Close()

	c := newTestClient(srv.URL)
	c.Collect("Python developer", "2", 1)

	if gotArea != "2" {
		t.Errorf("expected area=2, got %q", gotArea)
	}
	if gotText != "Python developer" {
		t.Errorf("expected text='Python developer', got %q", gotText)
	}
}
