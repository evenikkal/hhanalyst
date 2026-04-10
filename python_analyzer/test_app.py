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


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_skills_endpoint(mock_fetch):
    resp = client.get("/skills?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_vacancies"] == 3
    skill_names = [s[0] for s in data["top_skills"]]
    assert "python" in skill_names
    assert "docker" in skill_names


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_levels_endpoint(mock_fetch):
    resp = client.get("/levels?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    dist = data["distribution"]
    assert dist["junior"] == 1
    assert dist["senior"] == 1
    assert dist["middle"] == 1


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_chart_top_skills(mock_fetch):
    resp = client.get("/charts/top-skills?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "chart_base64" in data
    assert len(data["chart_base64"]) > 100  # non-empty PNG


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_chart_level_distribution(mock_fetch):
    resp = client.get("/charts/level-distribution?query=python&max_pages=1")
    assert resp.status_code == 200
    assert "chart_base64" in resp.json()


@patch("app.fetch_vacancies", new_callable=AsyncMock, return_value=SAMPLE_VACANCIES)
def test_full_analyze(mock_fetch):
    resp = client.post("/analyze?query=python&max_pages=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_skills" in data
    assert "level_distribution" in data
    assert "charts" in data
    assert all(k in data["charts"] for k in ("top_skills", "level_distribution", "skills_by_region"))
