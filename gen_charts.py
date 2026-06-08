"""Generate light-themed analysis charts (from demo dataset) for the course paper."""
import os, sys, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python_analyzer"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Re-theme charts module for print (light background, dark text) BEFORE use
import analyzer.charts as ch
ch.DARK_TEXT = "#1a1a1a"
ch.DARK_GRID = "#d0d0d0"
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#d0d0d0",
    "axes.labelcolor": "#1a1a1a",
    "text.color": "#1a1a1a",
    "xtick.color": "#1a1a1a",
    "ytick.color": "#1a1a1a",
    "grid.color": "#d0d0d0",
    "savefig.facecolor": "white",
    "font.size": 11,
})

from app import _demo_vacancies

OUT = "E:/mitp/hhanalyst/diagrams"
os.makedirs(OUT, exist_ok=True)

vacs = _demo_vacancies("python developer")
print(f"demo vacancies: {len(vacs)}")


def save_b64(b64: str, name: str):
    path = f"{OUT}/{name}"
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    print("Saved:", path)


save_b64(ch.top_skills_bar_chart(vacs, top_n=15), "chart_top_skills.png")
save_b64(ch.level_distribution_chart(vacs), "chart_levels.png")
print("done")
