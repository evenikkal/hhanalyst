package main

import (
	"log"
	"net/http"
	"os"

	"github.com/evenikkal/hhanalyst/go_collector/internal/handler"
	"github.com/evenikkal/hhanalyst/go_collector/internal/hh"
)

func main() {
	client := hh.NewClient()
	h := handler.New(client)

	mux := http.NewServeMux()
	h.Register(mux)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8082"
	}

	log.Printf("go_collector listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}
