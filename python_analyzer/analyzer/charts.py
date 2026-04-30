"""Chart generation: skill demand by region, level distribution."""

import io
import base64
from collections import defaultdict, Counter
from typing import List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from .skills import extract_skills
from .classifier import classify_level

DARK_BG = "#1e293b"
DARK_TEXT = "#f1f5f9"
DARK_GRID = "#334155"
ACCENT = "#3b82f6"
ACCENT2 = "#a78bfa"
TRANSPARENT = (0, 0, 0, 0)

plt.rcParams.update({
    "figure.facecolor": TRANSPARENT,
    "axes.facecolor": TRANSPARENT,
    "axes.edgecolor": DARK_GRID,
    "axes.labelcolor": DARK_TEXT,
    "text.color": DARK_TEXT,
    "xtick.color": DARK_TEXT,
    "ytick.color": DARK_TEXT,
    "grid.color": DARK_GRID,
    "savefig.facecolor": TRANSPARENT,
    "font.size": 11,
})


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, pad_inches=0.3, transparent=True)
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return data


def skills_by_region_chart(vacancies: list, top_skills: int = 10, top_regions: int = 5) -> str:
    """Heatmap: top skills (rows) x top regions (cols). Returns base64 PNG."""
    region_skill: dict = defaultdict(Counter)

    for v in vacancies:
        region = v.get("area", {}).get("name", "Unknown")
        for skill in extract_skills(v):
            region_skill[region][skill] += 1

    region_counts = Counter({r: sum(c.values()) for r, c in region_skill.items()})
    regions = [r for r, _ in region_counts.most_common(top_regions)]

    global_skills: Counter = Counter()
    for c in region_skill.values():
        global_skills.update(c)
    skills = [s for s, _ in global_skills.most_common(top_skills)]

    if not regions or not skills:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Not enough data", ha="center", va="center",
                fontsize=16, color="#94a3b8")
        ax.set_axis_off()
        return _fig_to_base64(fig)

    data = [[region_skill[r].get(s, 0) for r in regions] for s in skills]

    fig, ax = plt.subplots(figsize=(max(8, len(regions) * 2), max(5, len(skills) * 0.55)))
    cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["#0b1120", "#1e3a5f", ACCENT, ACCENT2, "#e879f9"])
    im = ax.imshow(data, aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(regions)))
    ax.set_xticklabels(regions, rotation=25, ha="right", fontsize=10)
    ax.set_yticks(range(len(skills)))
    ax.set_yticklabels(skills, fontsize=10)

    for i in range(len(skills)):
        for j in range(len(regions)):
            val = data[i][j]
            if val > 0:
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=9, fontweight="bold", color="#fff")

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Вакансий", fontsize=10)
    ax.set_title("Востребованность по регионам", fontsize=14, fontweight="bold", pad=12)
    fig.tight_layout()
    return _fig_to_base64(fig)


def level_distribution_chart(vacancies: list) -> str:
    """Donut chart of intern/junior/middle/senior distribution. Returns base64 PNG."""
    dist: dict = {"Intern": 0, "Junior": 0, "Middle": 0, "Senior": 0}
    for v in vacancies:
        level = classify_level(v)
        dist[level.capitalize()] += 1

    labels = [l for l in dist if dist[l] > 0]
    sizes = [dist[l] for l in labels]
    total = sum(sizes)
    color_map = {"Intern": "#06b6d4", "Junior": "#22c55e", "Middle": "#3b82f6", "Senior": "#ef4444"}
    colors = [color_map[l] for l in labels]

    fig, ax = plt.subplots(figsize=(6, 5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct=lambda p: f"{p:.0f}%\n({int(p*total/100)})",
        startangle=140, pctdistance=0.78,
        textprops={"fontsize": 12, "fontweight": "bold"},
        wedgeprops={"width": 0.45, "edgecolor": "none", "linewidth": 0},
    )
    for t in autotexts:
        t.set_fontsize(10)
        t.set_fontweight("bold")
    centre = plt.Circle((0, 0), 0.55, fc='none')
    ax.add_patch(centre)
    ax.set_title("Распределение по уровням", fontsize=14, fontweight="bold", pad=16)
    return _fig_to_base64(fig)


def top_skills_bar_chart(vacancies: list, top_n: int = 15) -> str:
    """Horizontal bar chart of top N skills. Returns base64 PNG."""
    counter: Counter = Counter()
    for v in vacancies:
        for skill in extract_skills(v):
            counter[skill] += 1

    if not counter:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Недостаточно данных", ha="center", va="center",
                fontsize=16, color="#94a3b8")
        ax.set_axis_off()
        return _fig_to_base64(fig)

    items = counter.most_common(top_n)
    skills = [i[0] for i in reversed(items)]
    counts = [i[1] for i in reversed(items)]
    max_count = max(counts) if counts else 1

    cmap = mcolors.LinearSegmentedColormap.from_list("bar", [ACCENT, ACCENT2, "#e879f9"])
    colors = [mcolors.to_hex(cmap(c / max_count * 0.85 + 0.15)) for c in counts]

    fig, ax = plt.subplots(figsize=(8, max(4, len(items) * 0.42)))
    bars = ax.barh(skills, counts, color=colors, height=0.65, edgecolor="none",
                   zorder=3)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + max_count * 0.02, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=10, fontweight="bold", color=DARK_TEXT)

    ax.set_xlabel("Количество вакансий", fontsize=11)
    ax.set_title(f"Топ-{min(top_n, len(items))} востребованных навыков",
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_xlim(0, max_count * 1.15)
    ax.grid(axis="x", alpha=0.15, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_alpha(0.3)
    ax.spines["left"].set_alpha(0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)
