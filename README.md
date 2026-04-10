# hhanalyst — Intelligent Job Vacancy Parser for hh.ru

**Вариант 21** | Курсовая работа по дисциплине «Методы и технологии программирования»  
Студент: Никишина Евгения Александровна, группа 221131

---

## Overview

Two-service system for scraping and analyzing job vacancies from [hh.ru](https://hh.ru):

| Service | Stack | Port | Role |
|---|---|---|---|
| `go_collector` | Go 1.21 | 8082 | Parallel hh.ru API scraper |
| `python_analyzer` | Python 3.12 + FastAPI | 8090 | NLP analytics + charts |

**Flow:** `python_analyzer` calls `go_collector/vacancies?query=...` → Go fetches pages from `api.hh.ru` in parallel goroutines → Python runs skill extraction, seniority classification, and generates charts.

---

## Quick Start

```bash
docker compose up --build
```

Then open:
- Go collector: http://localhost:8082/health
- Python analyzer docs: http://localhost:8090/docs

---

## API

### Go Collector (`localhost:8082`)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health |
| `/vacancies` | GET | Fetch vacancies from hh.ru |

Query params for `/vacancies`:
- `query` — search text (default: `Go developer`)
- `area` — region ID (`1`=Moscow, `2`=SPb, etc.)
- `max_pages` — 1–20 pages × 100 results each (default: 5)

### Python Analyzer (`localhost:8090`)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health |
| `/skills` | GET | Top skills across vacancies |
| `/levels` | GET | junior/middle/senior distribution |
| `/charts/top-skills` | GET | Bar chart (base64 PNG) |
| `/charts/level-distribution` | GET | Pie chart (base64 PNG) |
| `/charts/skills-by-region` | GET | Heatmap by region (base64 PNG) |
| `/analyze` | POST | Full analysis (skills + levels + all charts) |

All analyzer endpoints accept `query`, `area`, `max_pages` query params.

---

## Architecture

```
┌─────────────────────┐     HTTP GET /vacancies     ┌──────────────────────┐
│  python_analyzer    │ ──────────────────────────► │   go_collector       │
│  FastAPI :8090      │ ◄────────────────────────── │   net/http :8082     │
│  - skill extraction │     []Vacancy (JSON)        │   - 5 goroutines     │
│  - NLP classifier   │                             │   - rate limiter     │
│  - matplotlib charts│                             │   - hh.ru API client │
└─────────────────────┘                             └──────────────────────┘
         │                                                    │
         └───────────────── docker network ──────────────────┘
```

### Go Collector internals

- `hh/client.go` — rate-limited HTTP client, parallel page fetching with `sync.WaitGroup`
- 4 req/s rate limit (`250ms` ticker) to respect hh.ru API limits
- Up to 5 concurrent goroutines per search
- `FROM scratch` final image (~8 MB)

### Python Analyzer internals

- `analyzer/skills.py` — regex-based keyword extraction against a curated skill list (50+ technologies)
- `analyzer/classifier.py` — seniority classification via regex patterns (RU + EN) + fallback on hh.ru `experience.id`
- `analyzer/charts.py` — matplotlib charts: bar, pie, heatmap; all returned as base64 PNG
- Multi-stage Docker build (`pip install --prefix`) keeps final image lean
- Non-root `appuser` in container

---

## Development

### Run tests

```bash
# Go
cd go_collector && go test ./... -v

# Python
cd python_analyzer && pytest -v
```

### Run locally (without Docker)

```bash
# Terminal 1 — Go collector
cd go_collector && go run .

# Terminal 2 — Python analyzer
cd python_analyzer && pip install -r requirements.txt
uvicorn app:app --reload --port 8090
```

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
1. **test-go** and **test-python** run in parallel on every push/PR
2. **build-and-push** runs only on `main` push, after all tests pass — pushes to GHCR

Images:
- `ghcr.io/evenikkal/hhanalyst-collector:latest`
- `ghcr.io/evenikkal/hhanalyst-analyzer:latest`
