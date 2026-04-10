"""Classify vacancy seniority level: junior / middle / senior.

Uses Natasha lemmatization so inflected Russian ('старшего разработчика')
matches level patterns reliably.
"""

import re

from .nlp import lemmatize

JUNIOR_PATTERNS = [
    r"\bjunior\b", r"\bjun\b", r"\bджун\b", r"\bмладший\b",
    r"\bстажёр\b", r"\bстажер\b", r"\bintern\b", r"\bentry.?level\b",
    r"опыт.{0,20}(не требоваться|без опыт|от 0)",
    r"(0|без).{0,10}(лет|год).{0,10}опыт",
]

SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsen\b", r"\bсениор\b", r"\bстарший\b",
    r"\blead\b", r"\bтимлид\b", r"\bteam.?lead\b", r"\bпринципал\b",
    r"\bprincipal\b", r"\bstaff\b", r"\bархитектор\b",
    r"опыт.{0,20}(от 5|более 5|свыше 5)",
    r"(5|6|7|8|9|10).{0,10}(лет|год).{0,10}опыт",
]

MIDDLE_PATTERNS = [
    r"\bmiddle\b", r"\bmid\b", r"\bмидл\b",
    r"опыт.{0,20}(от [23]|2-4|3-5)",
    r"([23]).{0,10}(лет|год).{0,10}опыт",
]


def _matches(text: str, patterns: list) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def classify_level(vacancy: dict) -> str:
    """Return 'junior', 'middle', or 'senior' for a vacancy dict.

    Lemmatizes Russian text via Natasha for better pattern matching.
    """
    raw_text = " ".join([
        vacancy.get("name", ""),
        vacancy.get("snippet", {}).get("requirement", "") or "",
        vacancy.get("experience", {}).get("name", "") or "",
    ])

    # Check both raw text (for English keywords) and lemmatized (for Russian)
    lemmatized = lemmatize(raw_text)
    combined = raw_text + " " + lemmatized

    if _matches(combined, SENIOR_PATTERNS):
        return "senior"
    if _matches(combined, JUNIOR_PATTERNS):
        return "junior"
    if _matches(combined, MIDDLE_PATTERNS):
        return "middle"

    # Fallback: use hh.ru experience field
    exp_id = vacancy.get("experience", {}).get("id", "")
    if exp_id in ("noExperience",):
        return "junior"
    if exp_id in ("moreThan6",):
        return "senior"
    return "middle"


def level_distribution(vacancies: list) -> dict:
    """Return {level: count} distribution."""
    dist = {"junior": 0, "middle": 0, "senior": 0}
    for v in vacancies:
        level = classify_level(v)
        dist[level] = dist.get(level, 0) + 1
    return dist
