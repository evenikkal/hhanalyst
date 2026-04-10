package handler

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/evenikkal/hhanalyst/go_collector/internal/hh"
)

type Handler struct {
	client *hh.Client
}

func New(client *hh.Client) *Handler {
	return &Handler{client: client}
}

func (h *Handler) Register(mux *http.ServeMux) {
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/vacancies", h.Vacancies)
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "ok",
		"service": "go_collector",
	})
}

func (h *Handler) Vacancies(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	query := r.URL.Query().Get("query")
	if query == "" {
		query = "Go developer"
	}
	area := r.URL.Query().Get("area")
	maxPages := 5
	if p, err := strconv.Atoi(r.URL.Query().Get("max_pages")); err == nil && p > 0 && p <= 20 {
		maxPages = p
	}

	vacancies, err := h.client.Collect(query, area, maxPages)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(vacancies)
}
