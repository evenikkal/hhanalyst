package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"strconv"

	"github.com/evenikkal/hhanalyst/go_collector/hh"
)

var client = hh.NewClient()

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/vacancies", vacanciesHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8082"
	}
	log.Printf("go_collector listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok", "service": "go_collector"})
}

func vacanciesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	query := r.URL.Query().Get("query")
	if query == "" {
		query = "Go developer"
	}
	area := r.URL.Query().Get("area") // e.g. "1" = Moscow, "2" = SPb
	maxPagesStr := r.URL.Query().Get("max_pages")
	maxPages := 5
	if p, err := strconv.Atoi(maxPagesStr); err == nil && p > 0 && p <= 20 {
		maxPages = p
	}

	vacancies, err := client.Collect(query, area, maxPages)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(vacancies)
}
