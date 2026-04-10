"""Classify vacancy seniority level: junior / middle / senior."""

import re

JUNIOR_PATTERNS = [
    r"\bjunior\b", r"\bjun\b", r"\bджун\b", r"\bмладший\b",
    r"\bстажёр\b", r"\bстажер\b", r"\bintern\b", r"\bentry.?level\b",
    r"опыт.{0,20}(не требуется|без опыта|от 0)",
    r"(0|без).{0,10}(лет|года).{0,10}опыта",
]

SENIOR_PATTERNS = [
    r"\bsenior\b", r"\bsen\b", r"\bсениор\b", r"\bстарший\b",
    r"\blead\b", r"\bтимлид\b", r"\bteam.?lead\b", r"\bпринципал\b",
    r"\bprincipal\b", r"\bstaff\b",
    r"опыт.{0,20}(от 5|более 5|свыше 5)",
    r"(5|6|7|8|9|10).{0,10}(лет|года).{0,10}опыта",
]

MIDDLE_PATTERNS = [
    r"\bmiddle\b", r"\bmid\b", r"\bмидл\b",
    r"опыт.{0,20}(от [23]|2-4|3-5)",
    r"([23]).{0,10}(лет|года).{0,10}опыта",
]


def _matches(text: str, patterns: list) -> bool:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def classify_level(vacancy: dict) -> str:
    """Return 'junior', 'middle', or 'senior' for a vacancy dict."""
    text = " ".join([
        vacancy.get("name", ""),
        vacancy.get("snippet", {}).get("requirement", "") or "",
        vacancy.get("experience", {}).get("name", "") or "",
    ])

    if _matches(text, SENIOR_PATTERNS):
        return "senior"
    if _matches(text, JUNIOR_PATTERNS):
        return "junior"
    if _matches(text, MIDDLE_PATTERNS):
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
