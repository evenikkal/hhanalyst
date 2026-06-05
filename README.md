# hhanalyst — Intelligent Job Vacancy Parser for hh.ru

**Вариант 21** | Курсовая работа по дисциплине «Методы и технологии программирования»  
Студент: Никишина Евгения Александровна, группа 221131

---

## Overview

Two-service system for scraping and analyzing job vacancies from [hh.ru](https://hh.ru):

| Service | Stack | Port | Role |
|---|---|---|---|
| `python_analyzer` | Python 3.12 + FastAPI | 8090 | Web UI, NLP analytics, charts, caching |
| `go_collector` | Go 1.21 | 8082 | Parallel hh.ru API scraper (optional) |

**Flow:** the browser hits `python_analyzer`, which resolves vacancy data through a layered fallback chain — Go collector → hh.ru API → scrape → persistent cache → demo data. Then it runs skill extraction, seniority classification, and renders charts.

---

## Quick Start

The analyzer works **standalone** — it talks to hh.ru directly and degrades gracefully to cached/demo data:

```bash
docker compose up --build
```

Then open the **web UI** at http://localhost:8090

To also run the Go collector (parallel scraper, behind a profile):

```bash
docker compose --profile with-collector up --build
```

- Web UI: http://localhost:8090
- API docs (Swagger): http://localhost:8090/docs
- Go collector health: http://localhost:8082/health

---

## API

### Python Analyzer (`localhost:8090`)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Web UI |
| `/dashboard` | GET | Dashboard view |
| `/health` | GET | Service health + `offline_mode` flag |
| `/api/skills` | GET | Top skills across vacancies |
| `/api/levels` | GET | intern/junior/middle/senior/lead distribution |
| `/api/charts/top-skills` | GET | Bar chart (base64 PNG) |
| `/api/charts/level-distribution` | GET | Pie chart (base64 PNG) |
| `/api/charts/skills-by-region` | GET | Heatmap by region (base64 PNG) |
| `/api/analyze` | POST | Full analysis (skills + levels + all charts) |
| `/api/cache` | GET | Inspect persistent SQLite cache |
| `/api/cache` | DELETE | Clear persistent cache |

All analysis endpoints accept `query`, `area`, `max_pages` query params.

### Go Collector (`localhost:8082`)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health |
| `/vacancies` | GET | Fetch vacancies from hh.ru |

Query params for `/vacancies`:
- `query` — search text (default: `Go developer`)
- `area` — region ID (`1`=Moscow, `2`=SPb, etc.)
- `max_pages` — 1–20 pages × 100 results each (default: 5)

---

## Architecture

```
┌─────────────────────┐     HTTP GET /vacancies     ┌──────────────────────┐
│  python_analyzer    │ ──────────────────────────► │   go_collector       │
│  FastAPI :8090      │ ◄────────────────────────── │   net/http :8082     │
│  - web UI           │     []Vacancy (JSON)        │   - 5 goroutines     │
│  - skill extraction │                             │   - rate limiter     │
│  - NLP classifier   │                             │   - hh.ru API client │
│  - matplotlib charts│       (optional profile)    └──────────────────────┘
│  - SQLite cache     │
└─────────────────────┘
```

### Go Collector internals

- `hh/client.go` — rate-limited HTTP client, parallel page fetching with `sync.WaitGroup`
- 4 req/s rate limit (`250ms` ticker) to respect hh.ru API limits
- Up to 5 concurrent goroutines per search
- `FROM scratch` final image (~8 MB)

### Python Analyzer internals

- `analyzer/skills.py` — keyword extraction with normalization against a curated skill list (50+ technologies)
- `analyzer/classifier.py` — seniority classification via regex patterns (RU + EN) + fallback on hh.ru `experience.id`
- `analyzer/charts.py` — matplotlib charts: bar, pie, heatmap; all returned as base64 PNG
- `analyzer/cache_db.py` — persistent SQLite cache (see below)
- Multi-stage Docker build keeps the final image lean; runs as non-root `appuser`

---

## Caching & Offline Mode

Vacancy data is cached at two levels for resilience and speed:

| Level | Store | TTL | Purpose |
|---|---|---|---|
| L1 | in-memory dict | 300 s | hot cache, lost on restart |
| L2 | SQLite (`data/vacancies.db`) | 300 s fresh / 7 days stale | survives restarts, offline fallback |

Every successful online fetch is written to the SQLite cache. If the network is unavailable, stale entries (up to 7 days old) are served automatically.

Set `OFFLINE_MODE=1` to skip all network calls entirely and serve only cached / bundled data:

```bash
# docker-compose.yml → python_analyzer.environment
- OFFLINE_MODE=1
```

Inspect or clear the cache via `GET` / `DELETE` on `/api/cache`.

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
# Terminal 1 — Go collector (optional)
cd go_collector && go run .

# Terminal 2 — Python analyzer
cd python_analyzer && pip install -r requirements.txt
uvicorn app:app --reload --port 8090
```

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR:

1. **test-go** — `go vet` + `go test`
2. **test-python** — `pytest` (uses `uv` for fast installs)
3. **security** — SAST scan: `bandit` (Python) + `go vet` (Go)

[Dependabot](.github/dependabot.yml) checks `gomod`, `pip`, and `github-actions` dependencies weekly.

---

## AI Tools

This project was developed with the assistance of AI tools:
- **[Claude Code](https://claude.ai/code)** (Anthropic) — code generation, architecture decisions, debugging
- **GitHub Copilot** — inline code suggestions during development
