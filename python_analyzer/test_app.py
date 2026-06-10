import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app import app

client = TestClient(app)

SAMPLE_VACANCIES = [
    {
        "id": "1",
        "name": "Junior Python Developer",
        "area": {"id": "1", "name": "Moscow"},
        "snippet": {"requirement": "Python, Django, PostgreSQL, Docker", "responsibility": "backend"},
        "experience": {"id": "noExperience", "name": "Без опыта"},
        "salary": {"from": 80000, "to": None, "currency": "RUR"},
    },
    {
        "id": "2",
        "name": "Senior Go Engineer",
        "area": {"id": "2", "name": "Saint Petersburg"},
        "snippet": {"requirement": "Go, Kubernetes, Redis, Kafka", "responsibility": "backend"},
        "experience": {"id": "moreThan6", "name": "Более 6 лет"},
        "salary": {"from": 300000, "to": None, "currency": "RUR"},
    },
    {
        "id": "3",
        "name": "Middle Python Developer",
        "area": {"id": "1", "name": "Moscow"},
        "snippet": {"requirement": "Python, FastAPI, PostgreSQL, Docker, Git", "responsibility": ""},
        "experience": {"id": "between1And3", "name": "От 1 до 3 лет"},
        "salary": None,
    },
]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_index_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "HH Analyst" in resp.text


@patch("app.fetch_vacancies_with_source", new_callable=AsyncMock,
       return_value=(SAMPLE_VACANCIES, "scrape"))
def test_dashboard(mock_fetch):
    resp = client.get("/dashboard?query=python&max_pages=1")
    assert resp.status_code == 200
    assert "Junior" in resp.text
    assert "Senior" in resp.text
    assert "python" in resp.text.lower()


@patch("app.fetch_vacancies_with_source", new_callable=AsyncMock,
       return_value=(SAMPLE_VACANCIES, "scrape"))
def test_api_skills(mock_fetch):
    resp = client.get("/api/skills?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_vacancies"] == 3
    assert data["source"] == "scrape"
    assert data["degraded"] is False
    skill_names = [s[0] for s in data["top_skills"]]
    assert "Python" in skill_names
    assert "Docker" in skill_names


@patch("app.fetch_vacancies_with_source", new_callable=AsyncMock,
       return_value=(SAMPLE_VACANCIES, "scrape"))
def test_api_levels(mock_fetch):
    resp = client.get("/api/levels?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    dist = data["distribution"]
    assert dist["junior"] == 1
    assert dist["senior"] == 1
    assert dist["middle"] == 1


@patch("app._fetch_vacancies_uncached", new_callable=AsyncMock,
       return_value=(SAMPLE_VACANCIES, "offline"))
def test_fallback_not_cached(mock_uncached):
    """Fallback data must never poison the cache, so each call retries live."""
    import asyncio
    import app as appmod

    appmod._vacancy_cache.clear()
    vac, source = asyncio.run(
        appmod.fetch_vacancies_with_source("rare-query-xyz", "", 1)
    )
    assert source == "offline"
    assert vac == SAMPLE_VACANCIES
    # Nothing was cached, so the uncached path runs again on the next call.
    key = "rare-query-xyz||1"
    assert key not in appmod._vacancy_cache


@patch("app.fetch_vacancies_with_source", new_callable=AsyncMock,
       return_value=(SAMPLE_VACANCIES, "offline"))
def test_api_skills_marks_degraded(mock_fetch):
    resp = client.get("/api/skills?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "offline"
    assert data["degraded"] is True


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_api_chart_top_skills(mock_fetch):
    resp = client.get("/api/charts/top-skills?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "chart_base64" in data
    assert len(data["chart_base64"]) > 100


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_api_chart_level_distribution(mock_fetch):
    resp = client.get("/api/charts/level-distribution?query=python&max_pages=1")
    assert resp.status_code == 200
    assert "chart_base64" in resp.json()


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_api_full_analyze(mock_fetch):
    resp = client.post("/api/analyze?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_skills" in data
    assert "level_distribution" in data
    assert "charts" in data
    assert all(k in data["charts"] for k in ("top_skills", "level_distribution", "skills_by_region"))
