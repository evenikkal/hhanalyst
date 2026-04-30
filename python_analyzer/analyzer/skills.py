"""Skill extraction: hh.ru tags + NLP noun-phrase extraction.

Three-layer approach:
1. Scraped key_skills tags from hh.ru (highest quality)
2. NLP: Natasha lemmatized tokens matched against description
3. Normalize via alias map to merge duplicates (golang→Go, к8с→Kubernetes)
"""

import re
from collections import Counter
from typing import List

from .nlp import get_lemmatized

_NORMALIZE = {
    "golang": "Go",
    "go": "Go",
    "python3": "Python",
    "python 3": "Python",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "vue": "Vue",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "angular": "Angular",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "c++": "C++",
    "с++": "C++",
    "c#": "C#",
    "с#": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
    "k8s": "Kubernetes",
    "к8с": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "докер": "Docker",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "постгрес": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    "clickhouse": "ClickHouse",
    "elasticsearch": "Elasticsearch",
    "kafka": "Kafka",
    "rabbitmq": "RabbitMQ",
    "ci/cd": "CI/CD",
    "ci cd": "CI/CD",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "linux": "Linux",
    "линукс": "Linux",
    "git": "Git",
    "sql": "SQL",
    "nosql": "NoSQL",
    "rest api": "REST API",
    "rest": "REST API",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring",
    "1c": "1C",
    "1с": "1C",
    "1с-битрикс": "1C-Битрикс",
    "1c-битрикс": "1C-Битрикс",
    "битрикс": "Битрикс",
    "bitrix": "Битрикс",
    "1с:erp": "1C:ERP",
    "1c:erp": "1C:ERP",
    "1с:упп": "1C:УПП",
    "1с:зуп": "1C:ЗУП",
    "1с:бухгалтерия": "1C:Бухгалтерия",
    "1с предприятие": "1C:Предприятие",
    "1c предприятие": "1C:Предприятие",
    "1с:предприятие": "1C:Предприятие",
    "1c:предприятие": "1C:Предприятие",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "spark": "Apache Spark",
    "apache spark": "Apache Spark",
    "airflow": "Apache Airflow",
    "apache airflow": "Apache Airflow",
    "nginx": "Nginx",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "celery": "Celery",
    "selenium": "Selenium",
    "pytest": "pytest",
    "jira": "Jira",
    "confluence": "Confluence",
    "agile": "Agile",
    "scrum": "Scrum",
    "kanban": "Kanban",
    "microservices": "Микросервисы",
    "микросервисы": "Микросервисы",
    "микросервис": "Микросервисы",
    "микросервисная архитектура": "Микросервисы",
    "devops": "DevOps",
    "mlops": "MLOps",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "нейронные сети": "Нейронные сети",
    "нейросеть": "Нейронные сети",
    "opencv": "OpenCV",
    "computer vision": "Computer Vision",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "etl": "ETL",
    "dbt": "dbt",
    "oracle": "Oracle",
    "sqlite": "SQLite",
    "cassandra": "Cassandra",
    "php": "PHP",
    "ruby": "Ruby",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "rust": "Rust",
    "java": "Java",
}

_NORMALIZE_LOWER = {k.lower(): v for k, v in _NORMALIZE.items()}

_SKIP_WORDS = {
    "опыт", "работа", "знание", "умение", "навык", "понимание",
    "использование", "разработка", "создание", "поддержка",
    "написание", "внедрение", "обеспечение", "требование",
    "обязанность", "задача", "условие", "компания", "проект",
    "команда", "год", "лет", "система", "работать",
    "также", "может", "будет", "если", "только",
    "experience", "work", "knowledge", "skill", "ability",
    "team", "project", "company", "year", "development",
    "we", "you", "our", "the", "and", "with", "for", "from",
}

_MIN_SKILL_LEN = 2


def _normalize(name: str) -> str:
    low = name.strip().lower()
    if low in _NORMALIZE_LOWER:
        return _NORMALIZE_LOWER[low]
    return name.strip()


def _is_valid_skill(name: str) -> bool:
    if len(name) < _MIN_SKILL_LEN:
        return False
    if name.lower() in _SKIP_WORDS:
        return False
    if re.match(r"^\d+$", name):
        return False
    return True


def extract_skills(vacancy: dict) -> List[str]:
    """Extract skills from hh.ru tags + NLP analysis of description."""
    found: dict[str, str] = {}

    for ks in vacancy.get("key_skills", []):
        raw = ks.get("name", "").strip()
        if not raw:
            continue
        norm = _normalize(raw)
        if _is_valid_skill(norm):
            found[norm.lower()] = norm

    text_lower = " ".join([
        vacancy.get("name", ""),
        vacancy.get("snippet", {}).get("requirement", "") or "",
        vacancy.get("snippet", {}).get("responsibility", "") or "",
        vacancy.get("description", "") or "",
    ]).lower()
    text_lower = re.sub(r"<[^>]+>", " ", text_lower)

    lemmatized = get_lemmatized(vacancy).lower()
    combined = text_lower + " " + lemmatized

    for pattern, canonical in _NORMALIZE_LOWER.items():
        if len(pattern) < 2:
            continue
        escaped = re.escape(pattern)
        if re.search(r"(?:^|[\s,;/.(])" + escaped + r"(?:$|[\s,;/.):])", combined):
            if canonical.lower() not in found:
                found[canonical.lower()] = canonical

    return list(found.values())


def top_skills(vacancies: list, top_n: int = 20) -> List[tuple]:
    """Return top_n (skill, count) pairs across all vacancies."""
    counter: Counter = Counter()
    for v in vacancies:
        for skill in extract_skills(v):
            counter[skill] += 1
    return counter.most_common(top_n)
