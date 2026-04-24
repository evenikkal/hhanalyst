"""NLP pipeline using Natasha (MIPT) for Russian text processing.

Based on: https://habr.com/ru/companies/mipt/articles/472890/
Uses Natasha's NER, morphological analysis, and segmentation.

Natasha internally uses pymorphy2 which requires pkg_resources (removed
in Python 3.14). We patch it to use pymorphy3 instead.
"""

import re
import sys
from collections import Counter
from typing import List

# Patch: redirect pymorphy2 → pymorphy3 for Python 3.14+ compatibility
import pymorphy3
sys.modules["pymorphy2"] = pymorphy3
sys.modules["pymorphy2.analyzer"] = pymorphy3.analyzer

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    Doc,
)

# Initialize pipeline components once (heavy objects, reuse across calls)
segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
ner_tagger = NewsNERTagger(emb)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _vacancy_text(v: dict) -> str:
    """Combine all text fields of a vacancy into one string."""
    return " ".join([
        v.get("name", ""),
        v.get("snippet", {}).get("requirement", "") or "",
        v.get("snippet", {}).get("responsibility", "") or "",
        v.get("description", "") or "",
    ])


def analyze_text(text: str) -> dict:
    """Run full NLP pipeline once. Returns lemmatized text + entities."""
    if not text:
        return {"lemmatized": "", "entities": []}

    text = _strip_html(text)
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    for token in doc.tokens:
        token.lemmatize(morph_vocab)
    doc.tag_ner(ner_tagger)
    for span in doc.spans:
        span.normalize(morph_vocab)

    lemmatized = " ".join(t.lemma for t in doc.tokens if t.lemma)
    entities = [
        {"text": s.text, "normal": s.normal, "type": s.type}
        for s in doc.spans
    ]
    return {"lemmatized": lemmatized, "entities": entities}


def preprocess_vacancies(vacancies: list) -> list:
    """Run NLP once per vacancy, attach results as '_nlp' key.

    This is the single entry point — call it once, then pass the
    enriched list to skills/classifier/entities functions.
    """
    for v in vacancies:
        text = _vacancy_text(v)
        v["_nlp"] = analyze_text(text)
    return vacancies


def get_lemmatized(vacancy: dict) -> str:
    """Get pre-computed lemmatized text for a vacancy."""
    nlp = vacancy.get("_nlp")
    if nlp:
        return nlp["lemmatized"]
    # Fallback if preprocess wasn't called
    return analyze_text(_vacancy_text(vacancy))["lemmatized"]


_TECH_TERMS = {
    "python", "go", "golang", "rust", "java", "kotlin", "scala",
    "javascript", "typescript", "c++", "c#", ".net", "php", "ruby", "swift",
    "fastapi", "django", "flask", "gin", "echo", "spring", "react",
    "vue", "angular", "graphql", "rest", "grpc", "node.js", "node",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "spark", "kafka", "airflow", "dbt", "mlflow", "opencv",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "clickhouse",
    "elasticsearch", "cassandra", "sqlite", "oracle", "sql",
    "docker", "kubernetes", "k8s", "terraform", "ansible", "jenkins",
    "aws", "gcp", "azure", "ci/cd", "git", "linux", "bash",
    "prometheus", "grafana", "nginx", "rabbitmq", "celery",
    "microservices", "agile", "scrum",
    "django framework", "rest api", "flask", "nestjs", "aiohttp",
    "asyncio", "sqlalchemy", "pydantic", "selenium", "pytest",
    "allure", "jira", "confluence",
    "telegram", "telethon", "pyrogram", "mtproto",
    "openai", "openai api", "chatgpt", "langchain",
    "high-load", "eventloop", "mediapipe",
    "lorawan", "nvidia", "cuda", "opencv",
    "plc", "плк", "modicon", "control expert", "hmi",
    "qa automation", "qa", "devops", "sre", "mlops",
    "пуско-наладочные",
    "github", "gitlab", "bitbucket",
    "api", "sdk", "orm", "etl", "crud",
}

_LOC_ALIASES = {
    "рф": "Россия",
    "российская федерация": "Россия",
    "мо": "Московская область",
    "рб": "Республика Беларусь",
}

_LOC_GARBAGE = {
    "английский", "русский", "немецкий", "французский",
    "чем", "чему", "где", "куда",
    "сбер", "яндекс", "юг", "север", "восток", "запад",
}

_ORG_GARBAGE = {
    "тк", "дмс", "pvt", "пвт", "рд", "software", "hardware",
    "postrgres", "postgre", "it-компании", "it-компания",
    "code review", "python developer", "claude-code",
    "perfomance-review", "performance-review",
    "computer vision", "сервис", "департамент медиа",
    "sentry", "basis",
}

_ORG_GARBAGE_PATTERNS = re.compile(
    r"[()»«]|центр разработк|developer|engineer|review|vision\s*-",
    re.IGNORECASE,
)

_LOC_GARBAGE_PATTERNS = re.compile(
    r"проспект|улица|шоссе|бульвар|переулок|набережная|площадь|тупик"
    r"|проезд|аллея|корпус|строение",
    re.IGNORECASE,
)

_GARBAGE_PER_WORDS = {
    "питон", "менторство", "документирование", "парсинг", "плюс",
    "что", "который", "дружелюбная", "дружелюбный",
    "программист", "разработчик", "инженер", "аналитик", "тестировщик",
    "контейнеризация", "деплой", "рефакторинг", "оптимизация",
    "архитектура", "интеграция", "автоматизация", "виртуализация",
}


_RU_LETTER = re.compile(r"^[А-ЯЁа-яё]+$")


def _is_valid_per(name: str) -> bool:
    if len(name) < 3:
        return False
    if re.search(r"[(){}[\]<>]", name):
        return False
    words = name.split()
    if len(words) < 2:
        return False
    for w in words:
        if w.lower() in _GARBAGE_PER_WORDS or w.lower() in _TECH_TERMS:
            return False
    ru_capitalized = sum(
        1 for w in words
        if _RU_LETTER.match(w) and w[0].isupper()
    )
    return ru_capitalized >= 2


_ROLE_PATTERNS = re.compile(
    r"(?:senior|middle|junior|lead|chief|head|team\s*lead|staff|principal)"
    r"?\s*"
    r"(?:python|go|golang|java|kotlin|scala|rust|c\+\+|php|ruby|swift"
    r"|javascript|typescript|node\.?js|react|vue|angular"
    r"|fullstack|full[\s-]?stack|backend|back[\s-]?end|frontend|front[\s-]?end"
    r"|devops|sre|mlops|qa|data|ml|ai|mobile|android|ios"
    r"|software|web|system|cloud|platform|infrastructure)"
    r"\s*"
    r"(?:developer|engineer|разработчик|программист|architect|архитектор"
    r"|analyst|аналитик|specialist|специалист|тестировщик|lead|лид)?",
    re.IGNORECASE,
)

_ROLE_RU_PATTERNS = [
    re.compile(r"(?:старший|ведущий|главный|младший)?\s*(?:python|go|java|kotlin|php|c\+\+|rust|react|vue|angular|node\.?js|fullstack|backend|frontend|devops|qa|data|ml)[\s-]*(?:разработчик|программист|инженер|архитектор|аналитик|тестировщик|специалист|лид)", re.IGNORECASE),
    re.compile(r"(?:разработчик|программист|инженер|архитектор|аналитик|тестировщик)\s+(?:python|go|java|kotlin|php|c\+\+|rust|react|vue|angular|node\.?js|fullstack|backend|frontend)", re.IGNORECASE),
]


_ROLE_NORMALIZE = {
    "developer": "Developer",
    "engineer": "Engineer",
    "architect": "Architect",
    "analyst": "Analyst",
    "specialist": "Specialist",
    "lead": "Lead",
    "разработчик": "разработчик",
    "программист": "программист",
    "инженер": "инженер",
    "архитектор": "архитектор",
    "аналитик": "аналитик",
    "тестировщик": "тестировщик",
    "специалист": "специалист",
    "лид": "лид",
}


def _re_i(pattern: str, repl: str, text: str) -> str:
    return re.sub(pattern, repl, text, flags=re.IGNORECASE)


def _normalize_role(role: str) -> str | None:
    role = re.sub(r"[\s-]+", " ", role).strip()
    if not role or len(role) <= 3:
        return None
    has_title_word = any(kw in role.lower() for kw in _ROLE_NORMALIZE)
    if not has_title_word:
        return None
    role = _re_i(r"\bsenior\b|\bстарший\b|\bведущий\b", "Senior", role)
    role = _re_i(r"\bjunior\b|\bмладший\b", "Junior", role)
    role = _re_i(r"\bmiddle\b", "Middle", role)
    role = _re_i(r"\blead\b|\bглавный\b", "Lead", role)
    role = _re_i(r"\bback[\s-]?end\b", "Backend", role)
    role = _re_i(r"\bfront[\s-]?end\b", "Frontend", role)
    role = _re_i(r"\bfull[\s-]?stack\b", "Fullstack", role)
    role = _re_i(r"\bdeveloper\b", "Developer", role)
    role = _re_i(r"\bengineer\b", "Engineer", role)
    role = _re_i(r"\bразработчик\b", "разработчик", role)
    role = _re_i(r"\bпрограммист\b", "программист", role)
    role = _re_i(r"\bинженер\b", "инженер", role)
    return role.strip()


def _extract_role(title: str) -> str | None:
    title = re.sub(r"<[^>]+>", " ", title).strip()
    if not title:
        return None
    for pat in _ROLE_RU_PATTERNS:
        m = pat.search(title)
        if m:
            return _normalize_role(m.group(0))
    m = _ROLE_PATTERNS.search(title)
    if m:
        return _normalize_role(m.group(0))
    return None


def extract_entities_batch(vacancies: list) -> dict:
    """Aggregate NER entities across all pre-processed vacancies."""
    orgs: Counter = Counter()
    roles: Counter = Counter()

    for v in vacancies:
        employer = v.get("employer")
        if employer and employer.get("name"):
            orgs[employer["name"]] += 1

        role = _extract_role(v.get("name", ""))
        if role:
            roles[role] += 1

    if not orgs:
        for v in vacancies:
            nlp = v.get("_nlp")
            if not nlp:
                continue
            for ent in nlp["entities"]:
                if ent["type"] != "ORG":
                    continue
                name = ent["normal"] or ent["text"]
                low = name.lower()
                if low in _TECH_TERMS or low in _ORG_GARBAGE:
                    continue
                if _ORG_GARBAGE_PATTERNS.search(name):
                    continue
                if len(name) <= 2:
                    continue
                orgs[name] += 1

    return {
        "ORG": dict(orgs.most_common(20)),
        "ROLE": dict(roles.most_common(20)),
    }
