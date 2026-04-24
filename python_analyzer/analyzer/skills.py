"""Skill extraction from vacancy text using NLP-powered keyword matching.

Uses Natasha lemmatization so that inflected Russian text
('разработкой на Python') still matches skill keywords.
"""

import re
from collections import Counter
from typing import List

from .nlp import get_lemmatized

KNOWN_SKILLS = [
    # Languages
    "python", "go", "golang", "rust", "java", "kotlin", "scala",
    "javascript", "typescript", "c++", "c#", ".net", "php", "ruby", "swift",
    # Web / API
    "fastapi", "django", "flask", "gin", "echo", "spring", "react",
    "vue", "angular", "graphql", "rest", "grpc", "node.js",
    # Data / ML
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "spark", "kafka", "airflow", "dbt", "mlflow", "opencv",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "clickhouse", "elasticsearch",
    "cassandra", "sqlite", "oracle",
    # Infrastructure
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "github actions", "gitlab ci", "aws", "gcp", "azure", "ci/cd",
    # Tools & practices
    "git", "linux", "bash", "prometheus", "grafana", "nginx",
    "rabbitmq", "celery", "microservices", "agile", "scrum",
]

# Russian-language skill aliases (lemmatized forms)
RU_SKILL_ALIASES = {
    "микросервис": "microservices",
    "микросервисный": "microservices",
    "контейнеризация": "docker",
    "оркестрация": "kubernetes",
}


def extract_skills(vacancy: dict) -> List[str]:
    """Return list of recognized skills found in a vacancy (deduped).

    Uses pre-computed Natasha lemmatization for Russian morphology matching.
    """
    text_lower = " ".join([
        vacancy.get("name", ""),
        vacancy.get("snippet", {}).get("requirement", "") or "",
        vacancy.get("snippet", {}).get("responsibility", "") or "",
        vacancy.get("description", "") or "",
    ]).lower()
    text_lower = re.sub(r"<[^>]+>", " ", text_lower)

    if not text_lower.strip():
        return []

    # Use pre-computed lemmatized text (from preprocess_vacancies)
    text_lemmatized = get_lemmatized(vacancy).lower()

    found = set()

    # Match known skills in both raw and lemmatized text
    for skill in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower) or re.search(pattern, text_lemmatized):
            found.add(skill)

    # Match Russian aliases in lemmatized text
    for ru_lemma, skill in RU_SKILL_ALIASES.items():
        if ru_lemma in text_lemmatized:
            found.add(skill)

    return list(found)


def top_skills(vacancies: list, top_n: int = 20) -> List[tuple]:
    """Return top_n (skill, count) pairs across all vacancies."""
    counter: Counter = Counter()
    for v in vacancies:
        for skill in extract_skills(v):
            counter[skill] += 1
    return counter.most_common(top_n)
