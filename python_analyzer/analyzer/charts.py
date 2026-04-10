"""Chart generation: skill demand by region, level distribution."""

import io
import base64
from collections import defaultdict, Counter
from typing import List

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt

from .skills import extract_skills
from .classifier import classify_level


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return data


def skills_by_region_chart(vacancies: list, top_skills: int = 10, top_regions: int = 5) -> str:
    """Heatmap: top skills (rows) × top regions (cols). Returns base64 PNG."""
    region_skill: dict = defaultdict(Counter)

    for v in vacancies:
        region = v.get("area", {}).get("name", "Unknown")
        text = " ".join([
            v.get("name", ""),
            v.get("snippet", {}).get("requirement", "") or "",
            v.get("description", "") or "",
        ])
        for skill in extract_skills(text):
            region_skill[region][skill] += 1

    # Pick top regions by total vacancy count
    region_counts = Counter({r: sum(c.values()) for r, c in region_skill.items()})
    regions = [r for r, _ in region_counts.most_common(top_regions)]

    # Pick globally top skills
    global_skills: Counter = Counter()
    for c in region_skill.values():
        global_skills.update(c)
    skills = [s for s, _ in global_skills.most_common(top_skills)]

    if not regions or not skills:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
        return _fig_to_base64(fig)

    data = [[region_skill[r].get(s, 0) for r in regions] for s in skills]

    fig, ax = plt.subplots(figsize=(max(8, len(regions) * 1.5), max(6, len(skills) * 0.6)))
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(regions)))
    ax.set_xticklabels(regions, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(skills)))
    ax.set_yticklabels(skills, fontsize=9)
    plt.colorbar(im, ax=ax, label="Vacancies mentioning skill")
    ax.set_title("Skill demand by region")
    return _fig_to_base64(fig)


def level_distribution_chart(vacancies: list) -> str:
    """Pie chart of junior/middle/senior distribution. Returns base64 PNG."""
    dist: dict = {"junior": 0, "middle": 0, "senior": 0}
    for v in vacancies:
        level = classify_level(v)
        dist[level] += 1

    labels = list(dist.keys())
    sizes = [dist[l] for l in labels]
    colors = ["#4CAF50", "#2196F3", "#FF5722"]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%", startangle=140)
    ax.set_title("Vacancy level distribution")
    return _fig_to_base64(fig)


def top_skills_bar_chart(vacancies: list, top_n: int = 15) -> str:
    """Horizontal bar chart of top N skills. Returns base64 PNG."""
    counter: Counter = Counter()
    for v in vacancies:
        text = " ".join([
            v.get("name", ""),
            v.get("snippet", {}).get("requirement", "") or "",
            v.get("description", "") or "",
        ])
        for skill in extract_skills(text):
            counter[skill] += 1

    if not counter:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center")
        return _fig_to_base64(fig)

    items = counter.most_common(top_n)
    skills = [i[0] for i in reversed(items)]
    counts = [i[1] for i in reversed(items)]

    fig, ax = plt.subplots(figsize=(8, max(4, top_n * 0.45)))
    ax.barh(skills, counts, color="#1976D2")
    ax.set_xlabel("Number of vacancies")
    ax.set_title(f"Top {top_n} in-demand skills")
    return _fig_to_base64(fig)
