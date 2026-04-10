"""Skill extraction from vacancy text using keyword matching."""

import re
from collections import Counter
from typing import List

KNOWN_SKILLS = [
    # Languages
    "python", "go", "golang", "rust", "java", "kotlin", "scala",
    "javascript", "typescript", "c++", "c#", ".net", "php", "ruby",
    # Web / API
    "fastapi", "django", "flask", "gin", "echo", "spring", "react",
    "vue", "angular", "graphql", "rest", "grpc",
    # Data / ML
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "spark", "kafka", "airflow", "dbt", "mlflow",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "clickhouse", "elasticsearch",
    "cassandra", "sqlite",
    # Infrastructure
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "github actions", "gitlab ci", "aws", "gcp", "azure",
    # Tools
    "git", "linux", "bash", "prometheus", "grafana", "nginx",
]


def extract_skills(text: str) -> List[str]:
    """Return list of recognized skills found in text (lowercased, deduped)."""
    if not text:
        return []
    text_lower = text.lower()
    # Remove HTML tags if present
    text_lower = re.sub(r"<[^>]+>", " ", text_lower)
    found = []
    for skill in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)
    return found


def top_skills(vacancies: list, top_n: int = 20) -> List[tuple]:
    """Return top_n (skill, count) pairs across all vacancies."""
    counter: Counter = Counter()
    for v in vacancies:
        text = " ".join([
            v.get("name", ""),
            v.get("snippet", {}).get("requirement", "") or "",
            v.get("snippet", {}).get("responsibility", "") or "",
            v.get("description", "") or "",
        ])
        for skill in extract_skills(text):
            counter[skill] += 1
    return counter.most_common(top_n)
