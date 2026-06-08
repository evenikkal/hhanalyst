"""Generate UML/architecture diagrams for the course paper."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np
import os

OUT = "E:/mitp/hhanalyst/diagrams"
os.makedirs(OUT, exist_ok=True)

FONT = "DejaVu Sans"
plt.rcParams["font.family"] = FONT

# ── Colours ──────────────────────────────────────────────────────
C_BLUE   = "#2E5FA3"
C_LBLUE  = "#D9E8F5"
C_GREEN  = "#2E7D32"
C_LGREEN = "#D9F0DA"
C_ORANGE = "#E65100"
C_LORNG  = "#FDEBD0"
C_GREY   = "#546E7A"
C_LGREY  = "#ECEFF1"
C_WHITE  = "#FFFFFF"
C_BLACK  = "#212121"
C_ARROW  = "#37474F"


def box(ax, x, y, w, h, label, sublabel="", fc=C_LBLUE, ec=C_BLUE, lw=2, fs=11):
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.02", fc=fc, ec=ec, lw=lw, zorder=3)
    ax.add_patch(rect)
    if sublabel:
        ax.text(x, y + 0.08, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=C_BLACK, zorder=4)
        ax.text(x, y - 0.13, sublabel, ha="center", va="center",
                fontsize=fs - 2, color=C_GREY, zorder=4, style="italic")
    else:
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=C_BLACK, zorder=4)


def arrow(ax, x1, y1, x2, y2, label="", color=C_ARROW, lw=1.5, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                connectionstyle="arc3,rad=0.0"), zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my + 0.05, label, ha="center", va="bottom",
                fontsize=8, color=color, zorder=5,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))


def curved_arrow(ax, x1, y1, x2, y2, label="", color=C_ARROW, rad=0.3, lw=1.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=lw,
                                connectionstyle=f"arc3,rad={rad}"), zorder=2)
    if label:
        mx = (x1+x2)/2 + rad * (y2-y1) * 0.3
        my = (y1+y2)/2 + rad * (x1-x2) * 0.3
        ax.text(mx, my, label, ha="center", va="center", fontsize=8,
                color=color, zorder=5,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))


# ════════════════════════════════════════════════════════════════
# Diagram 1 — Architecture overview
# ════════════════════════════════════════════════════════════════
def diag_architecture():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # Title
    ax.text(6.5, 6.6, "Рисунок 2.1 – Архитектура системы hhanalyst",
            ha="center", va="center", fontsize=14, fontweight="bold", color=C_BLACK)

    # Docker network background
    rect_docker = FancyBboxPatch((3.8, 0.6), 8.8, 5.1,
                                  boxstyle="round,pad=0.05",
                                  fc="#F3F7FB", ec=C_BLUE, lw=1.5, ls="--", zorder=0)
    ax.add_patch(rect_docker)
    ax.text(8.2, 0.85, "Docker Network (bridge)", ha="center", va="center",
            fontsize=9, color=C_BLUE, style="italic")

    # Nodes
    box(ax, 1.7, 4.0, 2.2, 1.0, "Пользователь", "Browser", fc=C_LGREY, ec=C_GREY)
    box(ax, 6.2, 4.2, 3.0, 1.2, "Python Analyzer", ":8090  FastAPI + NLP",
        fc=C_LGREEN, ec=C_GREEN, fs=11)
    box(ax, 10.8, 4.2, 2.6, 1.2, "Go Collector", ":8082  net/http",
        fc=C_LBLUE, ec=C_BLUE, fs=11)
    box(ax, 10.8, 1.7, 2.6, 1.0, "hh.ru API", "api.hh.ru", fc=C_LORNG, ec=C_ORANGE, fs=11)
    box(ax, 6.2, 1.7, 2.8, 0.9, "Offline Cache", "data/offline_cache.json",
        fc="#FFF9E6", ec="#F9A825", fs=9)

    # User <-> Python  (two clearly separated horizontal arrows)
    arrow(ax, 2.8, 4.25, 4.65, 4.25, "", color=C_GREEN, lw=2)
    ax.text(3.75, 4.42, "GET /dashboard", ha="center", va="bottom", fontsize=8.5,
            color=C_GREEN, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
    ax.annotate("", xy=(2.8, 3.75), xytext=(4.65, 3.75),
                arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=2, ls="dashed",
                                connectionstyle="arc3,rad=0"), zorder=2)
    ax.text(3.75, 3.55, "HTML + charts", ha="center", va="top", fontsize=8.5,
            color=C_GREEN, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

    # Python <-> Go
    arrow(ax, 7.75, 4.45, 9.45, 4.45, "", color=C_BLUE, lw=2)
    ax.text(8.6, 4.62, "GET /vacancies", ha="center", va="bottom", fontsize=8.5,
            color=C_BLUE, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
    ax.annotate("", xy=(7.75, 3.95), xytext=(9.45, 3.95),
                arrowprops=dict(arrowstyle="->", color=C_BLUE, lw=2, ls="dashed",
                                connectionstyle="arc3,rad=0"), zorder=2)
    ax.text(8.6, 3.75, "[]Vacancy JSON", ha="center", va="top", fontsize=8.5,
            color=C_BLUE, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

    # Go <-> hh.ru
    arrow(ax, 10.5, 3.55, 10.5, 2.25, "", color=C_ORANGE, lw=2)
    ax.text(9.35, 2.9, "4 req/s\n5 горутин", ha="center", va="center",
            fontsize=8, color=C_ORANGE,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
    ax.annotate("", xy=(11.1, 3.55), xytext=(11.1, 2.25),
                arrowprops=dict(arrowstyle="<-", color=C_ORANGE, lw=2, ls="dashed",
                                connectionstyle="arc3,rad=0"), zorder=2)
    ax.text(12.0, 2.9, "[]Vacancy", ha="center", va="center", fontsize=8,
            color=C_ORANGE, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

    # OFFLINE_MODE dashed arrow (Python -> Offline cache)
    ax.annotate("", xy=(6.2, 2.2), xytext=(6.2, 3.6),
                arrowprops=dict(arrowstyle="->", color="#F9A825", lw=1.5, ls="dashed",
                                connectionstyle="arc3,rad=0.0"), zorder=2)
    ax.text(5.35, 2.9, "OFFLINE\nMODE=1", ha="center", va="center",
            fontsize=8, color="#F9A825", style="italic",
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

    # Legend
    legend_items = [
        mpatches.Patch(fc=C_LGREY, ec=C_GREY, label="Клиент"),
        mpatches.Patch(fc=C_LGREEN, ec=C_GREEN, label="Python Analyzer"),
        mpatches.Patch(fc=C_LBLUE, ec=C_BLUE, label="Go Collector"),
        mpatches.Patch(fc=C_LORNG, ec=C_ORANGE, label="hh.ru API (внешний)"),
    ]
    ax.legend(handles=legend_items, loc="lower left", fontsize=9,
              framealpha=0.9, ncol=2, bbox_to_anchor=(0.0, 0.0))

    plt.tight_layout()
    path = f"{OUT}/arch.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved:", path)


# ════════════════════════════════════════════════════════════════
# Diagram 2 — Sequence diagram
# ════════════════════════════════════════════════════════════════
def diag_sequence():
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.set_xlim(0, 14); ax.set_ylim(0, 24)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(7, 23.4, "Рисунок 2.2 – Диаграмма последовательности (UML)",
            ha="center", va="center", fontsize=14, fontweight="bold", color=C_BLACK)

    # Participants
    participants = [
        (1.4, "User\n(браузер)", C_LGREY, C_GREY),
        (4.3, "Python\nAnalyzer", C_LGREEN, C_GREEN),
        (7.2, "In-Memory\nCache", "#FFF9E6", "#F9A825"),
        (10.0, "Go\nCollector", C_LBLUE, C_BLUE),
        (12.8, "hh.ru\nAPI", C_LORNG, C_ORANGE),
    ]

    for x, name, fc, ec in participants:
        rect = FancyBboxPatch((x - 0.85, 21.6), 1.7, 1.0,
                              boxstyle="round,pad=0.04", fc=fc, ec=ec, lw=2, zorder=3)
        ax.add_patch(rect)
        ax.text(x, 22.1, name, ha="center", va="center",
                fontsize=10, fontweight="bold", color=C_BLACK, zorder=4)
        ax.plot([x, x], [21.6, 0.8], ls="--", color=ec, lw=1.2, zorder=1, alpha=0.6)

    xs = [p[0] for p in participants]

    def seq_arrow(y, x1, x2, label, color=C_ARROW, dashed=False):
        ls = "dashed" if dashed else "solid"
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.6,
                                    linestyle=ls, connectionstyle="arc3,rad=0"), zorder=3)
        mid = (x1 + x2) / 2
        ax.text(mid, y + 0.18, label, ha="center", va="bottom", fontsize=9,
                color=color, zorder=4,
                bbox=dict(fc="white", ec="none", alpha=0.9, pad=1))

    def activation(x, y_top, y_bot, fc="#E3F2FD", ec=C_BLUE):
        ax.add_patch(FancyBboxPatch((x - 0.14, y_bot), 0.28, y_top - y_bot,
                                    boxstyle="square,pad=0", fc=fc, ec=ec, lw=1.5, zorder=2))

    def selfnote(x, y, text, fc=C_LGREEN, ec=C_GREEN):
        ax.add_patch(FancyBboxPatch((x + 0.3, y - 0.28), 4.2, 0.56,
                                    boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=1.2, zorder=4))
        ax.text(x + 2.4, y, text, ha="center", va="center", fontsize=9,
                color=C_BLACK, zorder=5, style="italic")
        # small self-call arrow
        ax.annotate("", xy=(x + 0.3, y), xytext=(x + 0.14, y),
                    arrowprops=dict(arrowstyle="->", color=ec, lw=1.2), zorder=5)

    # Python analyzer activation spans most of the flow
    activation(xs[1], 21.0, 1.8, fc=C_LGREEN, ec=C_GREEN)

    y = 20.7
    seq_arrow(y, xs[0], xs[1], "GET /dashboard?query=python", color=C_GREEN)

    y = 19.7
    seq_arrow(y, xs[1], xs[2], "Проверка кэша анализа", color="#F9A825")

    # ALT frame
    ax.add_patch(FancyBboxPatch((2.3, 7.6), 10.9, 11.1,
                                boxstyle="square,pad=0", fc="#F9FBE7", ec="#8BC34A",
                                lw=1.5, alpha=0.35, zorder=0))
    ax.text(2.55, 18.35, "alt", ha="left", va="center", fontsize=10,
            fontweight="bold", color="#558B2F",
            bbox=dict(fc="#C5E1A5", ec="#558B2F", pad=3))
    ax.text(7.5, 18.35, "[кэш устарел / отсутствует]", ha="center", va="center",
            fontsize=9.5, color="#558B2F", style="italic")

    y = 17.6
    seq_arrow(y, xs[1], xs[3], "GET /vacancies?query=python&max_pages=3", color=C_BLUE)
    activation(xs[3], 17.7, 12.6, fc=C_LBLUE, ec=C_BLUE)

    # loop frame
    ax.add_patch(FancyBboxPatch((8.7, 13.2), 4.4, 3.3,
                                boxstyle="square,pad=0", fc="#E3F2FD", ec=C_BLUE,
                                lw=1.2, alpha=0.45, zorder=0))
    ax.text(8.95, 16.15, "loop", ha="left", va="center", fontsize=9.5,
            fontweight="bold", color=C_BLUE,
            bbox=dict(fc="#BBDEFB", ec=C_BLUE, pad=2))
    ax.text(11.1, 16.15, "[стр. 0..N, 5 горутин]", ha="center", va="center",
            fontsize=9, color=C_BLUE, style="italic")

    y = 15.2
    seq_arrow(y, xs[3], xs[4], "GET /vacancies?page=N&per_page=100", color=C_ORANGE)
    y = 14.0
    seq_arrow(y, xs[4], xs[3], "[]Vacancy JSON", color=C_ORANGE, dashed=True)

    y = 11.9
    seq_arrow(y, xs[3], xs[1], "[]Vacancy (до 300 объектов)", color=C_BLUE, dashed=True)

    # processing self-notes on the analyzer side
    selfnote(xs[1], 10.8, "preprocess + NLP (Natasha)")
    selfnote(xs[1], 9.9, "extract_skills + classify_levels")
    selfnote(xs[1], 9.0, "generate_charts (matplotlib)")

    y = 8.1
    seq_arrow(y, xs[1], xs[2], "Сохранить результаты (TTL = 300 с)", color="#F9A825")

    # second alt branch separator
    ax.plot([2.3, 13.2], [7.6, 7.6], ls="--", color="#8BC34A", lw=1.2, zorder=1)
    ax.text(7.5, 7.25, "[кэш актуален]", ha="center", va="center",
            fontsize=9.5, color="#558B2F", style="italic")

    y = 6.4
    seq_arrow(y, xs[2], xs[1], "Готовые результаты из кэша", color="#F9A825", dashed=True)

    # final response
    y = 4.6
    seq_arrow(y, xs[1], xs[0], "HTML-страница + base64 диаграммы", color=C_GREEN, dashed=True)

    plt.tight_layout()
    path = f"{OUT}/sequence.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved:", path)


# ════════════════════════════════════════════════════════════════
# Diagram 3 — Component diagram
# ════════════════════════════════════════════════════════════════
def diag_components():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(7, 7.75, "Рисунок 2.3 – Диаграмма компонентов системы (UML)",
            ha="center", va="center", fontsize=13, fontweight="bold", color=C_BLACK)

    def component(ax, x, y, w, h, name, stereotype="«component»",
                  fc=C_LBLUE, ec=C_BLUE, fs=10):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=2, zorder=3)
        ax.add_patch(rect)
        # component icon (UML)
        ix, iy = x + w/2 - 0.25, y + h/2 - 0.18
        ax.add_patch(FancyBboxPatch((ix - 0.2, iy - 0.12), 0.4, 0.24,
                                    boxstyle="square,pad=0", fc="white", ec=ec, lw=1.2, zorder=5))
        for dy in [-0.06, 0.06]:
            ax.add_patch(FancyBboxPatch((ix - 0.28, iy + dy - 0.04), 0.16, 0.08,
                                        boxstyle="square,pad=0", fc="white", ec=ec, lw=1, zorder=6))
        ax.text(x, y + 0.1, stereotype, ha="center", va="center",
                fontsize=7.5, color=ec, style="italic", zorder=4)
        ax.text(x, y - 0.12, name, ha="center", va="center",
                fontsize=fs, fontweight="bold", color=C_BLACK, zorder=4)

    def interface(ax, x, y, label, side="right"):
        circle = plt.Circle((x, y), 0.12, fc="white", ec=C_GREY, lw=1.5, zorder=5)
        ax.add_patch(circle)
        offset = 0.22 if side == "right" else -0.22
        ax.text(x + offset, y, label, ha="left" if side == "right" else "right",
                va="center", fontsize=7.5, color=C_GREY, zorder=5)

    def subsystem(ax, x, y, w, h, name, fc="#F8F8F8", ec=C_GREY):
        rect = FancyBboxPatch((x, y), w, h,
                              boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=2,
                              ls="--", zorder=1)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.2, f"«subsystem» {name}",
                ha="center", va="center", fontsize=10, fontweight="bold",
                color=ec, style="italic")

    # Subsystems
    subsystem(ax, 0.3, 0.4, 5.8, 7.0, "go_collector", fc="#EBF5FB", ec=C_BLUE)
    subsystem(ax, 7.5, 0.4, 6.2, 7.0, "python_analyzer", fc="#EBF5FE".replace("5FE","F5E"), ec=C_GREEN)

    # GO side
    component(ax, 3.2, 6.2, 3.0, 0.9, "handler", "«component»", fc=C_LBLUE, ec=C_BLUE)
    component(ax, 3.2, 4.7, 3.0, 0.9, "hh.Client", "«component»", fc=C_LBLUE, ec=C_BLUE)
    component(ax, 3.2, 3.2, 3.0, 0.9, "WorkerPool", "«component»", fc="#D6EAF8", ec=C_BLUE)
    component(ax, 3.2, 1.7, 3.0, 0.9, "models.Vacancy", "«struct»", fc=C_LGREY, ec=C_GREY)

    arrow(ax, 3.2, 5.75, 3.2, 5.15, "", color=C_BLUE)
    arrow(ax, 3.2, 4.25, 3.2, 3.65, "", color=C_BLUE)
    arrow(ax, 3.2, 2.75, 3.2, 2.15, "", color=C_BLUE)

    # PYTHON side
    component(ax, 10.6, 6.2, 3.2, 0.9, "app.py (FastAPI)", "«component»", fc=C_LGREEN, ec=C_GREEN)
    component(ax, 10.6, 4.8, 3.2, 0.85, "skills.py", "«component»", fc=C_LGREEN, ec=C_GREEN)
    component(ax, 10.6, 3.8, 3.2, 0.75, "classifier.py", "«component»", fc=C_LGREEN, ec=C_GREEN)
    component(ax, 10.6, 2.9, 3.2, 0.75, "charts.py", "«component»", fc=C_LGREEN, ec=C_GREEN)
    component(ax, 10.6, 2.0, 3.2, 0.75, "nlp.py (Natasha)", "«component»", fc="#D5F5E3", ec=C_GREEN)
    component(ax, 10.6, 1.1, 3.2, 0.75, "scraper.py", "«component»", fc=C_LGREY, ec=C_GREY)

    for y1, y2 in [(5.75, 5.25), (4.4, 4.25), (3.45, 3.25), (2.55, 2.4), (1.65, 1.5)]:
        arrow(ax, 10.6, y1, 10.6, y2, "", color=C_GREEN)

    # Inter-service arrow
    ax.annotate("", xy=(7.5, 4.7), xytext=(6.1, 4.7),
                arrowprops=dict(arrowstyle="<->", color=C_ARROW, lw=2,
                                connectionstyle="arc3,rad=0"), zorder=5)
    ax.text(6.8, 4.85, "HTTP REST\n/vacancies", ha="center", va="bottom",
            fontsize=8.5, color=C_ARROW, fontweight="bold")

    # External
    box(ax, 7.0, 6.5, 1.6, 0.7, "hh.ru API", fc=C_LORNG, ec=C_ORANGE, fs=9)
    ax.annotate("", xy=(4.7, 4.2), xytext=(6.2, 6.2),
                arrowprops=dict(arrowstyle="<->", color=C_ORANGE, lw=1.5,
                                connectionstyle="arc3,rad=0.1"), zorder=4)
    ax.text(5.3, 5.5, "HTTPS\nGET /vacancies", ha="center", va="center",
            fontsize=7.5, color=C_ORANGE)

    # External user
    box(ax, 7.0, 0.8, 1.4, 0.6, "User\n(браузер)", fc=C_LGREY, ec=C_GREY, fs=8)
    ax.annotate("", xy=(9.0, 6.2), xytext=(7.7, 1.0),
                arrowprops=dict(arrowstyle="<->", color=C_GREY, lw=1.5,
                                connectionstyle="arc3,rad=0.2"), zorder=4)
    ax.text(8.8, 3.4, "HTTP\n/dashboard", ha="center", va="center",
            fontsize=7.5, color=C_GREY)

    plt.tight_layout()
    path = f"{OUT}/components.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved:", path)


# ════════════════════════════════════════════════════════════════
# Diagram 4 — Deployment diagram
# ════════════════════════════════════════════════════════════════
def diag_deployment():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12); ax.set_ylim(0, 7)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(6, 6.75, "Рисунок 2.4 – Диаграмма развёртывания (UML)",
            ha="center", va="center", fontsize=13, fontweight="bold", color=C_BLACK)

    def node(ax, x, y, w, h, name, stereotype="«device»", fc="#EEF2FF", ec="#3949AB"):
        # 3D-ish box top
        off = 0.22
        top = FancyBboxPatch((x - w/2 + off, y + h/2), w - off, off,
                             boxstyle="square,pad=0", fc=ec, ec=ec, lw=1.5, zorder=3)
        ax.add_patch(top)
        side = FancyBboxPatch((x + w/2 - off, y - h/2 + off), off, h - off,
                              boxstyle="square,pad=0", fc="#A0A0A0", ec="#707070", lw=1, zorder=3)
        ax.add_patch(side)
        rect = FancyBboxPatch((x - w/2, y - h/2), w - off, h,
                              boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=2, zorder=3)
        ax.add_patch(rect)
        ax.text(x - off/2, y + h/2 - 0.02, f"{stereotype} {name}",
                ha="center", va="bottom", fontsize=9, fontweight="bold", color="white", zorder=5)

    def artifact(ax, x, y, w, h, name, fc="white", ec=C_GREY):
        rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle="round,pad=0.03", fc=fc, ec=ec, lw=1.5, zorder=4)
        ax.add_patch(rect)
        # dog-ear
        ax.add_patch(plt.Polygon(
            [[x + w/2 - 0.18, y + h/2], [x + w/2, y + h/2 - 0.18],
             [x + w/2 - 0.18, y + h/2 - 0.18]],
            fc=ec, ec=ec, zorder=5))
        ax.text(x, y + 0.07, "«artifact»", ha="center", va="center",
                fontsize=7.5, color=ec, style="italic", zorder=5)
        ax.text(x, y - 0.1, name, ha="center", va="center",
                fontsize=9, fontweight="bold", color=C_BLACK, zorder=5)

    # Host machine
    node(ax, 6, 3.5, 11.2, 5.5, "Host Machine", "«device»", fc="#F5F5F5", ec="#546E7A")
    ax.text(6, 5.9, "OS: Windows / Linux / macOS   Docker Engine",
            ha="center", va="center", fontsize=8.5, color=C_GREY, style="italic")

    # Docker Compose environment
    rect_dc = FancyBboxPatch((0.8, 1.2), 10.0, 4.3,
                             boxstyle="round,pad=0.04", fc="#EBF5FB", ec=C_BLUE,
                             lw=1.5, ls="--", zorder=2)
    ax.add_patch(rect_dc)
    ax.text(5.8, 5.35, "«execution environment»  docker compose network",
            ha="center", va="center", fontsize=9, color=C_BLUE, fontweight="bold")

    # Container: python_analyzer
    node(ax, 3.2, 3.0, 4.0, 3.2, "python_analyzer", "«container»",
         fc=C_LGREEN, ec=C_GREEN)
    artifact(ax, 2.5, 2.8, 2.4, 0.6, "app.py", fc="white", ec=C_GREEN)
    artifact(ax, 2.5, 2.1, 2.4, 0.6, "analyzer/", fc="white", ec=C_GREEN)
    artifact(ax, 2.5, 1.4, 2.4, 0.6, "offline_cache.json", fc="#FFF9E6", ec="#F9A825")
    ax.text(4.0, 2.8, "port: 8090", ha="left", va="center", fontsize=8, color=C_GREEN)
    ax.text(4.0, 2.4, "FastAPI / uvicorn", ha="left", va="center", fontsize=8, color=C_GREEN)
    ax.text(4.0, 2.0, "Python 3.12-slim", ha="left", va="center", fontsize=8, color=C_GREY)
    ax.text(4.0, 1.65, "~180 MB", ha="left", va="center", fontsize=8, color=C_GREY)

    # Container: go_collector
    node(ax, 8.3, 3.0, 4.0, 3.2, "go_collector", "«container»",
         fc=C_LBLUE, ec=C_BLUE)
    artifact(ax, 7.6, 2.8, 2.2, 0.6, "collector", fc="white", ec=C_BLUE)
    ax.text(7.2, 2.25, "(static binary,\nno deps)", ha="center", va="center",
            fontsize=8, color=C_GREY, style="italic")
    ax.text(9.3, 2.8, "port: 8082", ha="left", va="center", fontsize=8, color=C_BLUE)
    ax.text(9.3, 2.4, "net/http", ha="left", va="center", fontsize=8, color=C_BLUE)
    ax.text(9.3, 2.0, "FROM scratch", ha="left", va="center", fontsize=8, color=C_GREY)
    ax.text(9.3, 1.65, "~8 MB", ha="left", va="center", fontsize=8, color=C_GREY)

    # Communication arrow
    ax.annotate("", xy=(6.3, 3.1), xytext=(5.2, 3.1),
                arrowprops=dict(arrowstyle="<->", color=C_ARROW, lw=2,
                                connectionstyle="arc3,rad=0"), zorder=6)
    ax.text(5.75, 3.28, "HTTP :8082", ha="center", va="bottom",
            fontsize=8, color=C_ARROW, fontweight="bold")

    # User outside
    box(ax, 1.2, 0.5, 1.6, 0.6, "Пользователь", fc=C_LGREY, ec=C_GREY, fs=9)
    ax.annotate("", xy=(2.0, 1.3), xytext=(1.5, 0.8),
                arrowprops=dict(arrowstyle="<->", color=C_GREY, lw=1.5,
                                connectionstyle="arc3,rad=0"), zorder=6)
    ax.text(2.5, 0.9, "HTTP :8090", ha="left", va="center", fontsize=8, color=C_GREY)

    # hh.ru external
    box(ax, 10.7, 0.5, 1.8, 0.6, "hh.ru API", fc=C_LORNG, ec=C_ORANGE, fs=9)
    ax.annotate("", xy=(9.5, 1.3), xytext=(10.3, 0.8),
                arrowprops=dict(arrowstyle="<->", color=C_ORANGE, lw=1.5,
                                connectionstyle="arc3,rad=0"), zorder=6)
    ax.text(9.0, 0.9, "HTTPS", ha="right", va="center", fontsize=8, color=C_ORANGE)

    plt.tight_layout()
    path = f"{OUT}/deployment.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved:", path)


def diag_usecase():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12); ax.set_ylim(0, 8)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(6, 7.6, "Рисунок 2.5 – Use Case диаграмма системы",
            ha="center", va="center", fontsize=14, fontweight="bold", color=C_BLACK)

    def actor(ax, x, y, name):
        # stick figure
        ax.add_patch(plt.Circle((x, y + 0.45), 0.18, fc="white", ec=C_BLACK, lw=1.8, zorder=4))
        ax.plot([x, x], [y + 0.27, y - 0.25], color=C_BLACK, lw=1.8, zorder=4)
        ax.plot([x - 0.28, x + 0.28], [y + 0.1, y + 0.1], color=C_BLACK, lw=1.8, zorder=4)
        ax.plot([x, x - 0.22], [y - 0.25, y - 0.6], color=C_BLACK, lw=1.8, zorder=4)
        ax.plot([x, x + 0.22], [y - 0.25, y - 0.6], color=C_BLACK, lw=1.8, zorder=4)
        ax.text(x, y - 0.9, name, ha="center", va="center", fontsize=10,
                fontweight="bold", color=C_BLACK)

    def usecase(ax, x, y, text, fc=C_LGREEN, ec=C_GREEN):
        e = mpatches.Ellipse((x, y), 2.9, 0.85, fc=fc, ec=ec, lw=1.8, zorder=3)
        ax.add_patch(e)
        ax.text(x, y, text, ha="center", va="center", fontsize=9.5,
                color=C_BLACK, zorder=4)

    # System boundary
    rect = FancyBboxPatch((3.2, 0.6), 7.2, 6.3, boxstyle="round,pad=0.04",
                          fc="#FBFDFF", ec=C_BLUE, lw=1.8, zorder=1)
    ax.add_patch(rect)
    ax.text(6.8, 6.6, "Система hhanalyst", ha="center", va="center",
            fontsize=11, fontweight="bold", color=C_BLUE, style="italic")

    # Actors
    actor(ax, 1.4, 4.5, "Пользователь\n(аналитик)")
    actor(ax, 1.4, 1.8, "Администратор")
    actor(ax, 11.0, 4.0, "hh.ru API\n(система)")

    # Use cases
    ucs_user = [
        (6.0, 6.0, "Просмотр дашборда аналитики"),
        (6.0, 5.1, "Анализ навыков по запросу"),
        (6.0, 4.2, "Просмотр распределения\nпо уровням"),
        (6.0, 3.3, "Построение диаграмм"),
    ]
    for x, y, t in ucs_user:
        usecase(ax, x, y, t)
        ax.annotate("", xy=(x - 1.45, y), xytext=(1.75, 4.4),
                    arrowprops=dict(arrowstyle="-", color=C_GREY, lw=1.2), zorder=2)

    ucs_adm = [
        (6.0, 2.3, "Управление кэшем"),
        (6.0, 1.4, "Очистка кэша / Health-check"),
    ]
    for x, y, t in ucs_adm:
        usecase(ax, x, y, t, fc=C_LORNG, ec=C_ORANGE)
        ax.annotate("", xy=(x - 1.45, y), xytext=(1.75, 1.7),
                    arrowprops=dict(arrowstyle="-", color=C_GREY, lw=1.2), zorder=2)

    # external system link
    for x, y, t in [ucs_user[1], ucs_user[0]]:
        ax.annotate("", xy=(x + 1.45, y), xytext=(10.6, 4.0),
                    arrowprops=dict(arrowstyle="-", color=C_GREY, lw=1.2, ls="--"), zorder=2)

    plt.tight_layout()
    path = f"{OUT}/usecase.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print("Saved:", path)


if __name__ == "__main__":
    diag_architecture()
    diag_sequence()
    diag_components()
    diag_deployment()
    diag_usecase()
    print("All diagrams generated in:", OUT)
