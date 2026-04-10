import os
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from analyzer.skills import top_skills
from analyzer.classifier import level_distribution
from analyzer.charts import skills_by_region_chart, level_distribution_chart, top_skills_bar_chart

logger = logging.getLogger("hhanalyst")

app = FastAPI(title="HH Analyst", version="1.0.0")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://localhost:8082")


async def fetch_vacancies(query: str, area: str = "", max_pages: int = 3) -> list:
    params = {"query": query, "max_pages": max_pages}
    if area:
        params["area"] = area
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{COLLECTOR_URL}/vacancies", params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Collector error: {resp.status_code}")
        return resp.json()


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
        return templates.TemplateResponse("index.html", {
            "request": request,
            "query": query,
            "area": area,
            "max_pages": max_pages,
            "results": None,
            "error": None,
        })

    try:
        vacancies = await fetch_vacancies(query, area, max_pages)
        results = {
            "total_vacancies": len(vacancies),
            "top_skills": top_skills(vacancies),
            "level_distribution": level_distribution(vacancies),
            "charts": {
                "top_skills": top_skills_bar_chart(vacancies),
                "level_distribution": level_distribution_chart(vacancies),
                "skills_by_region": skills_by_region_chart(vacancies),
            },
        }
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
    skills = top_skills(vacancies, top_n=top_n)
    return {"query": query, "total_vacancies": len(vacancies), "top_skills": skills}


@app.get("/api/levels")
async def levels_endpoint(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    dist = level_distribution(vacancies)
    return {"query": query, "total_vacancies": len(vacancies), "distribution": dist}


@app.get("/api/charts/skills-by-region")
async def chart_skills_by_region(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
    img = skills_by_region_chart(vacancies)
    return {"chart_base64": img, "total_vacancies": len(vacancies)}


@app.get("/api/charts/level-distribution")
async def chart_level_distribution(
    query: str = Query("Go developer"),
    area: str = Query(""),
    max_pages: int = Query(3, ge=1, le=20),
):
    vacancies = await fetch_vacancies(query, area, max_pages)
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
