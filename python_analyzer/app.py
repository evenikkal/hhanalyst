import os
import logging
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from analyzer.skills import top_skills
from analyzer.classifier import level_distribution
from analyzer.charts import skills_by_region_chart, level_distribution_chart, top_skills_bar_chart
from analyzer.nlp import extract_entities_batch, preprocess_vacancies
from analyzer.scraper import scrape_vacancies

logger = logging.getLogger("hhanalyst")

app = FastAPI(title="HH Analyst", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://localhost:8082")
HH_API_BASE = "https://api.hh.ru"
HH_PAGE_SIZE = 100
HH_TOKEN = os.environ.get("HH_TOKEN", "")

_vacancy_cache: dict[str, tuple[float, list]] = {}
_analysis_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300


async def _fetch_from_collector(query: str, area: str, max_pages: int) -> list:
    params = {"query": query, "max_pages": max_pages}
    if area:
        params["area"] = area
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{COLLECTOR_URL}/vacancies", params=params)
        if resp.status_code != 200:
            body = resp.text[:300]
            raise RuntimeError(f"Collector {resp.status_code}: {body}")
        return resp.json()


async def _fetch_direct(query: str, area: str, max_pages: int) -> list:
    headers = {
        "User-Agent": "hhanalyst/1.0 (github.com/evenikkal/hhanalyst)",
        "HH-User-Agent": "hhanalyst/1.0 (github.com/evenikkal/hhanalyst)",
    }
    if HH_TOKEN:
        headers["Authorization"] = f"Bearer {HH_TOKEN}"
    all_items: list = []
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for page in range(max_pages):
            params = {
                "text": query,
                "per_page": HH_PAGE_SIZE,
                "page": page,
                "only_with_salary": "false",
            }
            if area:
                params["area"] = area
            resp = await client.get(f"{HH_API_BASE}/vacancies", params=params)
            if resp.status_code != 200:
                if page == 0:
                    raise RuntimeError(
                        f"hh.ru API вернул {resp.status_code}: {resp.text[:300]}"
                    )
                break
            data = resp.json()
            all_items.extend(data.get("items", []))
            if page + 1 >= data.get("pages", 0):
                break
    return all_items


def _demo_vacancies(query: str) -> list:
    """Realistic sample data for when hh.ru API is unavailable."""
    q = query.lower()
    base = [
        {
            "id": "101", "name": "Junior Python Developer",
            "employer": {"name": "Тинькофф"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Знание Python, Django, PostgreSQL, Docker. Опыт работы с Git.",
                "responsibility": "Разработка серверной части веб-приложений, написание unit-тестов.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Django"}, {"name": "PostgreSQL"}, {"name": "Docker"}, {"name": "Git"}],
            "experience": {"id": "noExperience", "name": "Нет опыта"},
            "salary": {"from": 80000, "to": 120000, "currency": "RUR"},
        },
        {
            "id": "102", "name": "Middle Python/FastAPI разработчик",
            "employer": {"name": "Сбер"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Python 3, FastAPI, SQLAlchemy, Redis, Docker, Kubernetes. Опыт от 2 лет.",
                "responsibility": "Проектирование и разработка микросервисов, code review.",
            },
            "key_skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "SQLAlchemy"}, {"name": "Redis"}, {"name": "Docker"}, {"name": "Kubernetes"}, {"name": "Микросервисы"}],
            "experience": {"id": "between1And3", "name": "От 1 года до 3 лет"},
            "salary": {"from": 180000, "to": 250000, "currency": "RUR"},
        },
        {
            "id": "103", "name": "Senior Backend Developer (Python)",
            "employer": {"name": "VK"},
            "area": {"id": "2", "name": "Санкт-Петербург"},
            "snippet": {
                "requirement": "Python, Go, PostgreSQL, MongoDB, Kafka, Docker, Kubernetes, CI/CD. Опыт 5+ лет.",
                "responsibility": "Архитектура высоконагруженных систем, менторство команды.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Go"}, {"name": "PostgreSQL"}, {"name": "MongoDB"}, {"name": "Kafka"}, {"name": "Docker"}, {"name": "Kubernetes"}, {"name": "CI/CD"}],
            "experience": {"id": "moreThan6", "name": "Более 6 лет"},
            "salary": {"from": 350000, "to": 500000, "currency": "RUR"},
        },
        {
            "id": "104", "name": "Python-разработчик в Яндекс",
            "employer": {"name": "Яндекс"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Python, asyncio, FastAPI/aiohttp, PostgreSQL, ClickHouse, Docker.",
                "responsibility": "Разработка внутренних инструментов аналитики.",
            },
            "key_skills": [{"name": "Python"}, {"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "ClickHouse"}, {"name": "Docker"}, {"name": "asyncio"}],
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "salary": {"from": 250000, "to": 400000, "currency": "RUR"},
        },
        {
            "id": "105", "name": "Data Engineer / Python Developer",
            "employer": {"name": "Ozon"},
            "area": {"id": "2", "name": "Санкт-Петербург"},
            "snippet": {
                "requirement": "Python, Apache Airflow, Spark, SQL, pandas, Docker.",
                "responsibility": "Построение ETL-пайплайнов, работа с большими данными.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Apache Airflow"}, {"name": "Apache Spark"}, {"name": "SQL"}, {"name": "Pandas"}, {"name": "Docker"}, {"name": "ETL"}],
            "experience": {"id": "between1And3", "name": "От 1 года до 3 лет"},
            "salary": {"from": 150000, "to": 220000, "currency": "RUR"},
        },
        {
            "id": "106", "name": "Go Developer (Golang)",
            "employer": {"name": "Авито"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Go, gRPC, PostgreSQL, Redis, Docker, Kubernetes, микросервисная архитектура.",
                "responsibility": "Разработка высоконагруженных backend-сервисов.",
            },
            "key_skills": [{"name": "Go"}, {"name": "gRPC"}, {"name": "PostgreSQL"}, {"name": "Redis"}, {"name": "Docker"}, {"name": "Kubernetes"}, {"name": "Микросервисы"}],
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "salary": {"from": 280000, "to": 420000, "currency": "RUR"},
        },
        {
            "id": "107", "name": "Junior+ Go разработчик",
            "employer": {"name": "Ростелеком"},
            "area": {"id": "3", "name": "Новосибирск"},
            "snippet": {
                "requirement": "Go, SQL, REST API, Git. Понимание многопоточности.",
                "responsibility": "Разработка микросервисов, участие в code review.",
            },
            "key_skills": [{"name": "Go"}, {"name": "SQL"}, {"name": "REST API"}, {"name": "Git"}, {"name": "Микросервисы"}],
            "experience": {"id": "noExperience", "name": "Нет опыта"},
            "salary": {"from": 90000, "to": 140000, "currency": "RUR"},
        },
        {
            "id": "108", "name": "Senior Go/Kotlin Developer",
            "employer": {"name": "Kaspersky"},
            "area": {"id": "2", "name": "Санкт-Петербург"},
            "snippet": {
                "requirement": "Go, Kotlin, Kafka, PostgreSQL, MongoDB, Docker, Kubernetes, Terraform.",
                "responsibility": "Архитектурные решения, развитие платформы.",
            },
            "key_skills": [{"name": "Go"}, {"name": "Kotlin"}, {"name": "Kafka"}, {"name": "PostgreSQL"}, {"name": "MongoDB"}, {"name": "Docker"}, {"name": "Kubernetes"}, {"name": "Terraform"}],
            "experience": {"id": "moreThan6", "name": "Более 6 лет"},
            "salary": {"from": 400000, "to": None, "currency": "RUR"},
        },
        {
            "id": "109", "name": "Fullstack Developer (React + Python)",
            "employer": {"name": "Wildberries"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Python, Django/FastAPI, React, TypeScript, PostgreSQL, Docker.",
                "responsibility": "Разработка веб-приложений полного цикла.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Django"}, {"name": "FastAPI"}, {"name": "React"}, {"name": "TypeScript"}, {"name": "PostgreSQL"}, {"name": "Docker"}],
            "experience": {"id": "between1And3", "name": "От 1 года до 3 лет"},
            "salary": {"from": 160000, "to": 230000, "currency": "RUR"},
        },
        {
            "id": "110", "name": "DevOps / Python Engineer",
            "employer": {"name": "МТС"},
            "area": {"id": "1", "name": "Москва"},
            "snippet": {
                "requirement": "Python, Ansible, Terraform, Docker, Kubernetes, CI/CD, Linux, Prometheus, Grafana.",
                "responsibility": "Автоматизация инфраструктуры, поддержка CI/CD пайплайнов.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Ansible"}, {"name": "Terraform"}, {"name": "Docker"}, {"name": "Kubernetes"}, {"name": "CI/CD"}, {"name": "Linux"}, {"name": "Prometheus"}, {"name": "Grafana"}],
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "salary": {"from": 220000, "to": 350000, "currency": "RUR"},
        },
        {
            "id": "111", "name": "ML Engineer (Python)",
            "employer": {"name": "Сбер"},
            "area": {"id": "2", "name": "Санкт-Петербург"},
            "snippet": {
                "requirement": "Python, PyTorch, scikit-learn, pandas, Docker, MLflow. Математическое образование.",
                "responsibility": "Разработка и внедрение ML-моделей в продакшен.",
            },
            "key_skills": [{"name": "Python"}, {"name": "PyTorch"}, {"name": "scikit-learn"}, {"name": "Pandas"}, {"name": "Docker"}, {"name": "MLflow"}, {"name": "Machine Learning"}],
            "experience": {"id": "between3And6", "name": "От 3 до 6 лет"},
            "salary": {"from": 300000, "to": 450000, "currency": "RUR"},
        },
        {
            "id": "112", "name": "QA Automation Engineer (Python)",
            "employer": {"name": "Positive Technologies"},
            "area": {"id": "3", "name": "Новосибирск"},
            "snippet": {
                "requirement": "Python, Selenium, pytest, Allure, REST API, SQL, Git.",
                "responsibility": "Автоматизация тестирования, разработка фреймворка.",
            },
            "key_skills": [{"name": "Python"}, {"name": "Selenium"}, {"name": "pytest"}, {"name": "Allure"}, {"name": "REST API"}, {"name": "SQL"}, {"name": "Git"}],
            "experience": {"id": "between1And3", "name": "От 1 года до 3 лет"},
            "salary": {"from": 120000, "to": 180000, "currency": "RUR"},
        },
    ]
    if "go" in q and "python" not in q:
        return [v for v in base if "go" in v["name"].lower() or "golang" in v["name"].lower()]
    if "python" in q:
        return [v for v in base if "python" in v["name"].lower() or "Python" in v["snippet"]["requirement"]]
    return base


async def fetch_vacancies(query: str, area: str = "", max_pages: int = 3) -> list:
    import copy
    key = f"{query}|{area}|{max_pages}"
    cached = _vacancy_cache.get(key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL:
        return copy.deepcopy(cached[1])

    vacancies = await _fetch_vacancies_uncached(query, area, max_pages)
    _vacancy_cache[key] = (time.monotonic(), copy.deepcopy(vacancies))
    return vacancies


async def _fetch_vacancies_uncached(query: str, area: str, max_pages: int) -> list:
    # 1) Try Go collector
    try:
        return await _fetch_from_collector(query, area, max_pages)
    except Exception as collector_err:
        logger.warning("Collector unavailable (%s)", collector_err)

    # 2) Try hh.ru API directly (needs HH_TOKEN)
    if HH_TOKEN:
        try:
            return await _fetch_direct(query, area, max_pages)
        except Exception as api_err:
            logger.warning("hh.ru API failed (%s)", api_err)

    # 3) Scrape hh.ru website
    try:
        return await scrape_vacancies(query, area, max_pages)
    except Exception as scrape_err:
        logger.warning("hh.ru scraping failed (%s), using demo data", scrape_err)

    # 4) Demo fallback
    return _demo_vacancies(query)


# ── Web UI ──────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "query": "",
        "area": "",
        "max_pages": 3,
        "results": None,
        "error": None,
    })


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    query: str = "",
    area: str = "",
    max_pages: int = 3,
):
    if not query:
        return templates.TemplateResponse(request, "index.html", {
            "query": query,
            "area": area,
            "max_pages": max_pages,
            "results": None,
            "error": None,
        })

    cache_key = f"{query}|{area}|{max_pages}"
    cached = _analysis_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL:
        results, error = cached[1], None
    else:
        try:
            vacancies = await fetch_vacancies(query, area, max_pages)
            preprocess_vacancies(vacancies)
            entities = extract_entities_batch(vacancies)
            results = {
                "total_vacancies": len(vacancies),
                "top_skills": top_skills(vacancies),
                "level_distribution": level_distribution(vacancies),
                "entities": entities,
                "charts": {
                    "top_skills": top_skills_bar_chart(vacancies),
                    "level_distribution": level_distribution_chart(vacancies),
                    "skills_by_region": skills_by_region_chart(vacancies),
                },
            }
            _analysis_cache[cache_key] = (time.monotonic(), results)
            error = None
        except Exception as e:
            logger.exception("Analysis failed")
            results = None
            error = f"Ошибка при анализе: {e}"

    return templates.TemplateResponse(request, "index.html", {
        "query": query,
        "area": area,
        "max_pages": max_pages,
        "results": results,
        "error": error,
    })


# ── JSON API ────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "python_analyzer"}


@app.get("/api/skills")
async def skills_endpoint(
    query: str = Query("Go developer", description="Search query for hh.ru"),
    area: str = Query("", description="Region ID (1=Moscow, 2=SPb, etc.)"),
    max_pages: int = Query(3, ge=1, le=20),
    top_n: int = Query(20, ge=1, le=50),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    skills = top_skills(vacancies, top_n=top_n)
    return {"query": query, "total_vacancies": len(vacancies), "top_skills": skills}


@app.get("/api/levels")
async def levels_endpoint(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    dist = level_distribution(vacancies)
    return {"query": query, "total_vacancies": len(vacancies), "distribution": dist}


@app.get("/api/charts/skills-by-region")
async def chart_skills_by_region(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    img = skills_by_region_chart(vacancies)
    return {"chart_base64": img, "total_vacancies": len(vacancies)}


@app.get("/api/charts/level-distribution")
async def chart_level_distribution(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    img = level_distribution_chart(vacancies)
    return {"chart_base64": img, "total_vacancies": len(vacancies)}


@app.get("/api/charts/top-skills")
async def chart_top_skills(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
    top_n: int = Query(15, ge=5, le=30),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    img = top_skills_bar_chart(vacancies, top_n=top_n)
    return {"chart_base64": img, "total_vacancies": len(vacancies)}


@app.post("/api/analyze")
async def analyze(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    """Full analysis: skills + level distribution + all charts."""
    vacancies = await fetch_vacancies(query, area, max_pages)
    preprocess_vacancies(vacancies)
    return {
        "query": query,
        "total_vacancies": len(vacancies),
        "top_skills": top_skills(vacancies),
        "level_distribution": level_distribution(vacancies),
        "charts": {
            "top_skills": top_skills_bar_chart(vacancies),
            "level_distribution": level_distribution_chart(vacancies),
            "skills_by_region": skills_by_region_chart(vacancies),
        },
    }
