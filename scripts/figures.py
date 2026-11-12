"""Figures of the paper on controlled Polish (PK).

Usage:  python scripts/figures.py            every figure
        python scripts/figures.py tokens probe   only the named ones
Output: paper/figures/<name>.pdf for LaTeX and <name>.png for the README.

Every title states the finding and takes its numbers from results/*.json; none is typed by hand.
The line under the title says what is drawn; the footer names the source and the sample size.
"""

from __future__ import annotations

import csv
import glob
import json
import logging
import math
import os
import re
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
from src import pkmodel as M  # noqa: E402

OUT = os.path.join(ROOT, "paper", "figures")
os.makedirs(OUT, exist_ok=True)


def res(name):
    with open(os.path.join(ROOT, "results", name), encoding="utf-8") as fh:
        return json.load(fh)


def data(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# One colour per studied factor, fixed across the figures: ordinary Polish orange, PK blue.
NAT, PK, AQUA, YELLOW = "#eb6834", "#2a78d6", "#1baf7a", "#eda100"
INK, INK2, MUTED, GRID, RULE, PAPER = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#f4f3ee"
SEQ = LinearSegmentedColormap.from_list("blue", ["#ffffff", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

logging.getLogger("fontTools").setLevel(logging.ERROR)
for _f in glob.glob("/usr/share/texmf-dist/fonts/opentype/public/lm/lmroman10-*.otf"):
    font_manager.fontManager.addfont(_f)                      # the typeface of the paper, when installed
sns.set_theme(context="paper", style="ticks")
plt.rcParams.update({
    "font.family": ["Latin Modern Roman", "DejaVu Serif"], "mathtext.fontset": "cm", "font.size": 8.5,
    "axes.titlesize": 9.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
    "legend.frameon": False, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": RULE, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "text.color": INK, "axes.titlecolor": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "lines.linewidth": 1.5,
    "lines.markersize": 5, "lines.markeredgewidth": 0.8, "figure.facecolor": "white",
    "axes.facecolor": "white", "savefig.bbox": "tight", "savefig.dpi": 170,
})
COMMA = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "−"))
W = 6.3                                                        # text width of the paper in inches


def pl(x, nd=2):
    """Number with a Polish decimal comma."""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def big(n):
    s = str(int(n))
    return s if len(s) < 5 else re.sub(r"(?<=\d)(?=(\d{3})+$)", " ", s)


def head(fig, finding, what, width=92):
    """Title = the finding; the line under it says what is drawn."""
    lines = textwrap.wrap(finding, width)
    h = fig.get_figheight()
    fig.suptitle("\n".join(lines), x=0.01, y=1 + 0.30 / h, ha="left", va="bottom", fontsize=10, fontweight="bold")
    fig.text(0.01, 1 + 0.26 / h, "\n".join(textwrap.wrap(what, 118)), ha="left", va="top", fontsize=8, color=INK2)


def foot(fig, text):
    fig.text(0.01, -0.22 / fig.get_figheight(), "\n".join(textwrap.wrap(text, 135)), ha="left", va="top", fontsize=7, color=MUTED)


def models_word(n):
    """Polish plural of 'model' after a numeral."""
    return f"{n} model" if n == 1 else f"{n} modele" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else f"{n} modeli"


def bare(ax):
    """A drawing, not a chart: no ticks, no grid."""
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"))
    plt.close(fig)
    print("figure", name)


def box(ax, x, y, w, h, text, face, edge=RULE, size=7.5, color=INK, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012", fc=face, ec=edge, lw=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=color, fontweight=weight)


def elbow(ax, x0, y0, x1, y1, xm, color):
    """Edge with right angles only: horizontal, vertical, horizontal."""
    ax.plot([x0, xm, xm, x1], [y0, y0, y1, y1], color=color, lw=1.1, solid_joinstyle="miter", solid_capstyle="butt")


# ---------------------------------------------------------------------------
def fig_relation():
    """Set theory: the interpretation relation of ordinary Polish and the function of PK."""
    items = {r["id"]: r for r in data("items.csv")}
    a, b = items["D2a"], items["C4"]
    meanings = ["wiek < 3 lata", "wiek < 4 lata", "żaden zawór nie\njest zamknięty", "co najmniej 1\nzawór jest otwarty"]
    fig, axes = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw={"wspace": 0.08})
    ys = [0.82, 0.60, 0.34, 0.12]
    for ax, title, color in zip(axes, ["Zwykła polszczyzna: relacja", "PK: funkcja"], [NAT, PK]):
        bare(ax)
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(0, 1.04)
        ax.text(0, 1.03, title, fontsize=8.5, fontweight="bold", color=color, va="top")
        for y, m in zip(ys, meanings):
            box(ax, 0.64, y - 0.085, 0.36, 0.17, m, PAPER, size=6.6)
    ax = axes[0]
    for y, it, targets in ((0.71, a, ys[:2]), (0.23, b, ys[2:])):
        box(ax, 0.0, y - 0.1, 0.46, 0.2, textwrap.fill("„" + it["nat"] + "”", 22), "#fdeee7", NAT, size=7)
        for t in targets:
            elbow(ax, 0.46, y, 0.64, t, 0.55, NAT)
    ax = axes[1]
    for y, text in zip(ys, [a["pk1"], a["pk2"], b["pk1"], b["pk2"]]):
        box(ax, 0.0, y - 0.085, 0.52, 0.17, textwrap.fill("„" + text + "”", 27), "#e6f0fc", PK, size=6.4)
        elbow(ax, 0.52, y, 0.64, y, 0.58, PK)
    head(fig, "PK zamienia relację interpretacji w funkcję: 2 zdania mają 4 znaczenia, 4 zdania PK mają po 1 znaczeniu",
         "Zdania (po lewej) i znaczenia (po prawej); linia łączy zdanie ze znaczeniem zdania")
    foot(fig, "Źródło: przykłady reguł D2 i C4 ze standardu PK 0.1; n = 2 zdania zwykłe, 4 zdania PK.")
    save(fig, "relation")


def fig_gray():
    """Semantics: the two readings as sets on a number line and the gray zone between them."""
    rows = [  # item, axis label, reading 1 (lo, hi), reading 2 (lo, hi), probe, axis limits; None = unbounded
        ("D2a", "wiek dziecka w latach", (0, 3), (0, 4), 3 + 5 / 12, (0, 6)),
        ("D2b", "liczba sztuk w zamówieniu", (4.5, 10.5), (4.5, 9.5), 10, (3, 12)),
        ("D2c", "wartość zamówienia w zł", (100.6, 130), (100, 130), 100, (90, 110)),
        ("D4a", "dzień złożenia reklamacji (listopad 2026)", (1.5, 15.5), (1.5, 16.5), 16, (1, 20)),
        ("D6b", "zmierzona odległość w m", (45, 55), (40, 60), 58, (35, 65)),
    ]
    items = {r["id"]: r for r in data("items.csv")}
    fig, axes = plt.subplots(len(rows), 1, figsize=(W, 6.0))
    for ax, (iid, xlabel, r1, r2, probe_x, lim) in zip(axes, rows):
        it = items[iid]
        ax.grid(False)
        ax.set_ylim(0, 1)
        ax.set_xlim(*lim)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        lo, hi = max(lim[0], min(r1[0], r2[0])), min(lim[1], max(r1[1], r2[1]))
        inner_lo, inner_hi = max(r1[0], r2[0]), min(r1[1], r2[1])
        for a0, a1 in ((lo, inner_lo), (inner_hi, hi)):
            if a1 - a0 > 1e-9:
                ax.axvspan(a0, a1, color="#d9d8d2", lw=0, zorder=0)
        for y, (a0, a1), c in ((0.66, r1, NAT), (0.34, r2, "#f4a582")):
            ax.plot([max(a0, lim[0]), min(a1, lim[1])], [y, y], color=c, lw=5, solid_capstyle="butt")
        ax.plot([probe_x], [0.5], marker="D", color=INK, ms=5, zorder=5)
        ax.set_xlabel(xlabel, labelpad=1, fontsize=7.5)
        ax.xaxis.set_major_formatter(COMMA)
        if iid in ("D2b", "D4a"):
            ax.set_xticks(range(int(lim[0]) + 1, int(lim[1]) + 1, 1 if iid == "D2b" else 2))
        ax.text(0.0, 1.36, f"„{it['nat']}”", transform=ax.transAxes, fontsize=7.8, va="bottom", fontweight="bold")
        ax.text(0.0, 1.08, f"odczytanie 1: {it['r1']};  odczytanie 2: {it['r2']}", transform=ax.transAxes,
                fontsize=7, va="bottom", ha="left", color=INK2)
    fig.subplots_adjust(hspace=1.9)
    head(fig, "2 odczytania zdania zgadzają się poza wąską strefą szarą; sonda pyta o sytuację ze strefy szarej",
         "Pasek górny: odczytanie 1. Pasek dolny: odczytanie 2. Tło szare: strefa szara. Romb: sytuacja sondy")
    foot(fig, f"Źródło: data/items.csv, pozycje {', '.join(r[0] for r in rows)}; n = {len(rows)} z {len(items)} pozycji.")
    save(fig, "gray_zone")


def fig_truth():
    """Logic: truth tables of the two readings of one sentence."""
    t1 = [(a, b, c, int((a and b) or c), int(a and (b or c))) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    t2 = [(a, b, int(a or b), int(a != b)) for a in (0, 1) for b in (0, 1)]
    t3 = [(k, int(k == 0), int(k < 3)) for k in range(4)]
    panels = [
        ("„A i B lub C”", ["A", "B", "C"], ["(A i B) lub C", "A i (B lub C)"], t1, 3),
        ("„A lub B”", ["A", "B"], ["co najmniej 1 człon", "dokładnie 1 człon"], t2, 2),
        ("„Wszystkie zawory nie są zamknięte”", ["k"], ["żaden nie jest zamknięty", "nie każdy jest zamknięty"], t3, 1),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(W, 3.5), gridspec_kw={"width_ratios": [5, 4, 4.4]})
    diffs = []
    for ax, (title, inputs, readings, table, k) in zip(axes, panels):
        bare(ax)
        n = len(table)
        ax.set_xlim(-0.5, k + 2.9)
        ax.set_ylim(8 + 2.6, -1.3)
        d = 0
        for i, row in enumerate(table):
            differ = row[k] != row[k + 1]
            d += differ
            for j, v in enumerate(row[:k]):
                ax.text(j, i, str(v), ha="center", va="center", fontsize=8, color=INK2)
            for j, v in enumerate(row[k:]):
                ax.add_patch(Rectangle((k + j - 0.45, i - 0.45), 0.9, 0.9, fc=(PK if v else "white"), ec=RULE, lw=0.6))
                ax.text(k + j, i, str(v), ha="center", va="center", fontsize=8, color="white" if v else INK2)
            if differ:
                ax.add_patch(Rectangle((k - 0.5, i - 0.5), 2, 1, fc="none", ec=NAT, lw=1.5))
                ax.text(k + 2.05, i, "≠", ha="left", va="center", fontsize=10, color=NAT, fontweight="bold")
        diffs.append((d, n))
        for j, name in enumerate(inputs):
            ax.text(j, -0.75, name, ha="center", va="bottom", fontsize=7.5, color=INK2)
        for j, name in enumerate(readings):
            ax.text(k + j, -0.7, f"odcz.\n{j + 1}", ha="center", va="bottom", fontsize=6.6, color=INK, linespacing=0.95)
            ax.text(-0.4, 8.5 + 0.75 * j, f"odcz. {j + 1}: {name}", ha="left", va="center", fontsize=6.9, color=INK)
        if inputs == ["k"]:
            ax.text(-0.4, 10.0, "k: liczba zamkniętych zaworów z 3", ha="left", va="center", fontsize=6.9, color=INK2)
        ax.set_title(title, fontsize=8, pad=4, loc="left")
    head(fig, f"2 odczytania jednego zdania dają różną wartość logiczną w {diffs[0][0]} z {diffs[0][1]}, "
              f"w {diffs[1][0]} z {diffs[1][1]} i w {diffs[2][0]} z {diffs[2][1]} sytuacji",
         "Tablice prawdy: 1 oznacza prawdę. Ramka i znak ≠: wiersz, w którym odczytania się różnią")
    foot(fig, "Źródło: wyliczenie w scripts/figures.py; zdania z reguł C2, C1 i C4 standardu PK 0.1.")
    save(fig, "truth_tables")


def fig_growth():
    """Combinatorics: the number of readings against the number of choice points."""
    c = res("p1_counts.json")
    fig, ax = plt.subplots(figsize=(W, 3.0))
    ks = [r["k"] for r in c["attachment"][1:]]
    series = [
        ("frazy przyimkowe po dopełnieniu (reguła B6)", ks, [r["readings"] for r in c["attachment"][1:]], NAT, "o"),
        ("kwantyfikatory „każdy” i „pewien” na przemian (reguła C4)", [r["n"] for r in c["scope"]], [r["distinct"] for r in c["scope"]], YELLOW, "s"),
        ("spójniki „i” oraz „lub” na przemian (reguła C2)", [r["n"] - 1 for r in c["bracketing"]], [r["functions"] for r in c["bracketing"]], AQUA, "^"),
        ("zaimki z 2 kandydatami (reguła A3)", ks, [2 ** k for k in ks], MUTED, "v"),
    ]
    for label, x, y, color, marker in series:
        ax.plot(x, y, color=color, marker=marker, label=label)
    ax.plot(ks, [1] * len(ks), color=PK, marker="D", lw=2.2, label="zdanie w PK")
    ax.set_yscale("log")
    ax.set_xlabel("liczba miejsc wyboru w zdaniu: fraz, kwantyfikatorów, spójników albo zaimków")
    ax.set_ylabel("liczba różnych odczytań")
    ax.set_xticks(ks)
    ax.legend(loc="upper left", fontsize=7.2)
    att8 = c["attachment"][8]["readings"]
    head(fig, f"Liczba odczytań rośnie wykładniczo: 8 fraz przyimkowych daje {big(att8)} odczytania, zdanie w PK ma 1 odczytanie",
         "Liczba logicznie różnych odczytań zdania dla 4 konstrukcji; skala logarytmiczna")
    foot(fig, "Źródło: results/p1_counts.json, dokładne wyliczenie funkcjami count_parses, scope_orders i bracketings z src/pkmodel.py.")
    save(fig, "growth")


def fig_parser():
    """Complexity: measured operations of the Earley recognizer."""
    p = res("p2_parser.json")
    rows = p["rows"]
    x = np.array([r["words"] for r in rows])
    fig, ax = plt.subplots(figsize=(W, 3.0))
    ax.plot(x, [r["ops_nat"] for r in rows], color=NAT, marker="o", ms=3, label=f"gramatyka z niejednoznacznym przyłączeniem (wykładnik {pl(p['exp_nat'])})")
    ax.plot(x, [r["ops_pk"] for r in rows], color=PK, marker="D", ms=3, label=f"gramatyka PK (wykładnik {pl(p['exp_pk'])})")
    ax.axvline(25, color=MUTED, lw=0.9, ls=(0, (4, 3)))
    ax.text(26.5, 22, "reguła B8:\nco najwyżej 25 słów", fontsize=7, color=INK2, va="bottom")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([3, 5, 11, 25, 45, 83])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.tick_params(axis="x", which="minor", length=0)
    ax.set_xlabel("długość zdania w słowach")
    ax.set_ylabel("operacje parsera Earleya")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 1.0), framealpha=1, facecolor="white", frameon=True, edgecolor="white")
    last = rows[-1]
    head(fig, f"Parser wykonuje dla gramatyki PK {pl(last['ops_nat'] / last['ops_pk'], 1)} razy mniej operacji przy {last['words']} słowach; "
              f"wykładnik wzrostu spada z {pl(p['exp_nat'])} do {pl(p['exp_pk'])}",
         "Zmierzona liczba operacji rozpoznawania zdań „rzeczownik czasownik rzeczownik” z k frazami przyimkowymi; obie skale logarytmiczne")
    foot(fig, f"Źródło: results/p2_parser.json, funkcja earley z src/pkmodel.py; n = {len(rows)} zdań; wykładnik dopasowany dla zdań od {p['fit_from_words']} słów.")
    save(fig, "parser")


def fig_classes():
    """Complexity: where the problems around PK sit among the classes."""
    n_reg = sum(r["checker"] == "automat" for r in data("rules.csv") if r["id"] not in ("F", "KW"))
    cols = [
        ("czas\nliniowy", [(f"kontrola reguł\nmechanicznych\nPK ({n_reg} z 32)", PK),
                           ("spójność\nwymagań PK$_0$\nbez przeczeń\n(klauzule Horna)", PK)]),
        ("czas\nwielomianowy", [("parsing\ngramatyki\nbezkontekstowej", "g"), ("fragment Cop\n(sylogistyka)", "g")]),
        ("NP-\nzupełne", [("spójność\nwymagań PK$_0$\nz 1 przeczeniem\nw zdaniu", NAT), ("fragment\nCop+Rel\n(zdania względne)", "g")]),
        ("EXPTIME-\nzupełne", [("fragment\nCop+Rel+TV\n(czasowniki\nprzechodnie)", "g")]),
        ("NEXPTIME-\nzupełne", [("fragment\nCop+Rel+DTV\n(2 dopełnienia)", "g")]),
        ("nieroz-\nstrzygalne", [("fragment\nCop+Rel\n+TV+GA\n(zaimki bez\nograniczeń)", "g"), ("pełna polszczyzna;\ntakże PK 0.1", NAT)]),
    ]
    fig, ax = plt.subplots(figsize=(W, 3.3))
    bare(ax)
    ax.set_xlim(0, len(cols))
    ax.set_ylim(0, 1)
    for i, (name, boxes) in enumerate(cols):
        ax.add_patch(Rectangle((i + 0.03, 0.0), 0.94, 0.82, fc=PAPER, ec="none"))
        ax.text(i + 0.5, 0.92, name, ha="center", va="center", fontsize=7.4, fontweight="bold", linespacing=0.95)
        for j, (text, color) in enumerate(boxes):
            face = {"g": "white", PK: "#e6f0fc", NAT: "#fdeee7"}[color]
            edge = RULE if color == "g" else color
            box(ax, i + 0.07, 0.45 - j * 0.40, 0.86, 0.33, text, face, edge, size=6.0)
    ax.annotate("", xy=(len(cols) - 0.05, -0.05), xytext=(0.05, -0.05), xycoords="data",
                arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1), annotation_clip=False)
    ax.text(len(cols) / 2, -0.11, "rosnąca złożoność obliczeniowa", ha="center", va="top", fontsize=7.3, color=INK2)
    head(fig, "1 przeczenie w zdaniu warunkowym przenosi spójność zbioru wymagań z czasu liniowego do klasy problemów NP-zupełnych",
         "Niebieski i pomarańczowy: wyniki tej pracy. Biały: wyniki znane, fragmenty języka angielskiego według Pratta-Hartmanna i Thirda")
    foot(fig, "Źródło: twierdzenia 4.2 i 4.3 tej pracy; Dowling i Gallier (1984); Earley (1970); Pratt-Hartmann i Third (2006).")
    save(fig, "classes")


def fig_rules():
    """Classification of the 32 rules, module F and the requirement keywords."""
    rules = data("rules.csv")
    feats = [("ograniczenie: usuwa zdania", lambda r: "R" in r["operator"], NAT),
             ("konwencja: usuwa odczytania", lambda r: "K" in r["operator"], NAT),
             ("sprawdza automat skończony", lambda r: r["checker"] == "automat", PK),
             ("sprawdzenie wymaga składni", lambda r: r["checker"] == "składnia", PK),
             ("sprawdzenie wymaga znaczenia", lambda r: r["checker"] == "semantyka", PK),
             ("M1: zwija zbiór odczytań", lambda r: "M1" in r["mechanism"], AQUA),
             ("M2: ogranicza rozmiar", lambda r: "M2" in r["mechanism"], AQUA),
             ("M3: daje lokalność", lambda r: "M3" in r["mechanism"], AQUA)]
    fig, ax = plt.subplots(figsize=(W, 2.75))
    ax.grid(False)
    for j, (name, fn, color) in enumerate(feats):
        xs = [i for i, r in enumerate(rules) if fn(r)]
        ax.scatter(xs, [j] * len(xs), s=30, color=color, zorder=3)
        ax.text(len(rules) + 0.2, j, str(len(xs)), va="center", fontsize=7.5, color=INK2)
    for i in range(len(rules)):
        ax.plot([i, i], [-0.5, len(feats) - 0.5], color=GRID, lw=0.5, zorder=1)
    for y in (1.5, 4.5):
        ax.plot([-0.6, len(rules) - 0.4], [y, y], color=RULE, lw=0.8)
    ax.set_xticks(range(len(rules)))
    ax.set_xticklabels([r["id"] for r in rules], rotation=90, fontsize=6.8)
    ax.set_yticks(range(len(feats)))
    ax.set_yticklabels([f[0] for f in feats], fontsize=7.5)
    ax.set_ylim(len(feats) - 0.5, -0.5)
    ax.set_xlim(-0.7, len(rules) + 1.4)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    core = [r for r in rules if r["id"] not in ("F", "KW")]
    n = {k: sum(r["checker"] == k for r in core) for k in ("automat", "składnia", "semantyka")}
    head(fig, f"{n['automat']} z {len(core)} reguł PK sprawdza automat skończony; {n['składnia']} reguł wymaga analizy składni, "
              f"{n['semantyka']} reguł wymaga znaczenia",
         "Kropka: reguła ma cechę. Liczba po prawej: liczba reguł z cechą (32 reguły, moduł F i słowa kluczowe KW)")
    foot(fig, f"Źródło: data/rules.csv, klasyfikacja autora na podstawie tekstu standardu PK 0.1; n = {len(rules)} wierszy.")
    save(fig, "rules")


def fig_tokens():
    """Corpus linguistics: how much longer the PK sentence is."""
    t, s = res("p3_tokens.json"), res("summary.json")["tokens"]
    unit = "o200k_base"
    rows = [r for r in t["rows"] if r["kind"] != "convention"]
    rows.sort(key=lambda r: (r[unit]["pk1"] + r[unit]["pk2"]) / (2 * r[unit]["nat"]))
    fig, (a, b) = plt.subplots(1, 2, figsize=(W, 4.3), gridspec_kw={"width_ratios": [1.25, 1]})
    for i, r in enumerate(rows):
        nat, pk = r[unit]["nat"], (r[unit]["pk1"] + r[unit]["pk2"]) / 2
        a.plot([nat, pk], [i, i], color=RULE, lw=1.1, zorder=1)
        a.scatter([nat], [i], color=NAT, s=16, zorder=3)
        a.scatter([pk], [i], color=PK, s=16, zorder=3, marker="D")
    a.set_yticks(range(len(rows)))
    a.set_yticklabels([r["id"] for r in rows], fontsize=5.6)
    a.set_ylim(-0.8, len(rows) - 0.2)
    a.set_xlabel("liczba tokenów (tokenizer o200k)")
    a.scatter([], [], color=NAT, s=16, label="zdanie zwykłe")
    a.scatter([], [], color=PK, s=16, marker="D", label="zdanie w PK (średnia z 2)")
    a.legend(loc="center right", bbox_to_anchor=(1.0, 0.33))
    a.grid(axis="y", visible=False)
    names = {"words": "słowa", "chars": "znaki", "o200k_base": "tokeny o200k", "cl100k_base": "tokeny cl100k",
             "unsloth/Llama-3.2-3B-Instruct": "tokeny Llama 3.2", "unsloth/gemma-3-4b-it": "tokeny Gemma 3"}
    units = [u for u in t["units"] if u in names]
    rng = np.random.default_rng(1)
    for j, u in enumerate(units):
        d = [100 * ((r[u]["pk1"] + r[u]["pk2"]) / (2 * r[u]["nat"]) - 1) for r in rows]
        b.scatter(d, j + rng.uniform(-0.16, 0.16, len(d)), s=7, color=PK, alpha=0.45, lw=0)
        q1, med, q3 = np.percentile(d, [25, 50, 75])
        b.plot([q1, q3], [j, j], color=INK, lw=2.4, solid_capstyle="butt")
        b.plot([med], [j], marker="|", color=INK, ms=11, mew=2)
        b.text(305, j, f"{pl(med, 0)} %", va="center", fontsize=7.5, color=INK)
    b.axvline(0, color=MUTED, lw=0.8)
    b.set_yticks(range(len(units)))
    b.set_yticklabels([names[u] for u in units])
    b.set_ylim(len(units) - 0.5, -0.5)
    b.set_xlim(-45, 345)
    b.set_xlabel("narzut długości PK w %")
    b.grid(axis="y", visible=False)
    fig.subplots_adjust(wspace=0.42)
    m = s[unit]
    head(fig, f"PK wydłuża {pl(100 * m['share_longer'], 0)} % zdań; mediana narzutu wynosi {pl(100 * m['median'], 0)} % tokenów "
              f"(kwartyle: {pl(100 * m['q1'], 0)} % i {pl(100 * m['q3'], 0)} %)",
         "Lewy panel: długość każdej pozycji. Prawy panel: narzut w 6 miarach; kreska: mediana, odcinek: kwartyle, liczba: mediana")
    foot(fig, f"Źródło: results/p3_tokens.json; n = {len(rows)} pozycji przeredagowanych, każda z 2 zdaniami PK.")
    save(fig, "tokens")


def model_name(m):
    name = m["model"].split("/")[-1]
    name = re.sub(r"[:\-]?(q8_0|instruct|it)$", "", name, flags=re.I).strip("-:")
    return {"ollama": "lokalny", "openrouter": "OpenRouter", "claude": "Claude"}[m["backend"]] + ": " + name


def fig_probe():
    """Information theory: probability of reading 1 in the gray zone, per model."""
    p = res("p4_summary.json")
    models = p["models"]
    if not models:
        print("figure probe skipped: no probe results")
        return
    cols = min(4, len(models))
    rows_n = math.ceil(len(models) / cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(W, 3.3 * rows_n), squeeze=False, sharex=True)
    for ax in axes.flat[len(models):]:
        ax.set_visible(False)
    for ax, m in zip(axes.flat, models):
        items = sorted((r for r in m["items"] if r["kind"] == "restriction"), key=lambda r: r["nat"])
        y = np.arange(len(items))
        ax.hlines(y, [r["pk2"] for r in items], [r["pk1"] for r in items], color="#cfe0f6", lw=1.0, zorder=1)
        ax.scatter([r["pk1"] for r in items], y, marker=">", s=11, color=PK, zorder=3, lw=0)
        ax.scatter([r["pk2"] for r in items], y, marker="<", s=11, color=PK, zorder=3, lw=0)
        ax.scatter([r["nat"] for r in items], y, marker="o", s=13, color=NAT, zorder=4, lw=0)
        ax.set_xlim(-0.04, 1.04)
        ax.set_ylim(-1, len(items))
        ax.set_yticks([])
        ax.set_xticks([0, 0.5, 1])
        ax.xaxis.set_major_formatter(COMMA)
        ax.grid(axis="y", visible=False)
        note = "kotwice poniżej progu" if m["qualified"] is False else f"trafność PK {pl(100 * m['acc_pk'], 0)} %"
        ax.set_title(f"{model_name(m)}\n{note}", fontsize=7.2, pad=3, linespacing=1.1,
                     color=MUTED if m["qualified"] is False else INK)
    for ax in axes[-1]:
        ax.set_xlabel("P(odczytanie 1)")
    handles = [plt.Line2D([], [], marker="o", color=NAT, ls="", ms=4, label="zdanie zwykłe"),
               plt.Line2D([], [], marker=">", color=PK, ls="", ms=4, label="zdanie PK dla odczytania 1 (cel: 1)"),
               plt.Line2D([], [], marker="<", color=PK, ls="", ms=4, label="zdanie PK dla odczytania 2 (cel: 0)")]
    hgt = fig.get_figheight()
    fig.legend(handles=handles, loc="upper left", ncol=3, bbox_to_anchor=(0.0, 1 + 0.02 / hgt), columnspacing=1.2, handletextpad=0.3)
    fig.subplots_adjust(hspace=0.36, wspace=0.12, top=1 - 0.55 / hgt)
    ok = [m for m in models if m["qualified"] is not False]
    acc = [m["acc_pk"] for m in ok] or [m["acc_pk"] for m in models]
    split = p.get("nat_split_share")
    finding = (f"Zdania PK sterują odczytaniem modeli, które przeszły kontrolę: trafność od {pl(100 * min(acc), 0)} % "
               f"do {pl(100 * max(acc), 0)} %")
    if split is not None and len(ok) > 1:
        finding += f"; zdanie zwykłe dzieli te modele w {pl(100 * split, 0)} % pozycji"
    head(fig, finding, "Każdy wiersz to 1 pozycja; pozycje uporządkowane według odpowiedzi modelu na zdanie zwykłe")
    n = models[0]["n_rewrite"]
    foot(fig, f"Źródło: results/p4_summary.json; n = {n} pozycji przeredagowanych na model, {models_word(len(models))}. "
              "Modele Claude: udział odpowiedzi „Tak” w 2 próbach.")
    save(fig, "probe")


def fig_breakeven():
    """Cost model: when the longer PK text pays off."""
    s, p = res("summary.json")["tokens"], res("p4_summary.json")
    d = np.linspace(0, 1.5, 200)
    fig, ax = plt.subplots(figsize=(W, 3.0))
    errs = [1 - m["acc_pk"] for m in p["models"] if m["qualified"] is not False] or [0.0]
    e_mean = float(np.mean(errs))
    ax.fill_between(d, 1 - (1 - e_mean) / (1 + d), 1, color="#e6f0fc", lw=0)
    ax.fill_between(d, 0, 1 - (1 - e_mean) / (1 + d), color="#fdeee7", lw=0)
    ax.plot(d, 1 - 1 / (1 + d), color=PK, ls=(0, (4, 2)), lw=1.3, label="próg, gdy czytelnik odczytuje każde zdanie PK poprawnie")
    ax.plot(d, 1 - (1 - e_mean) / (1 + d), color=PK, lw=2,
            label=f"próg przy zmierzonym błędzie odczytania PK ({pl(100 * e_mean, 0)} %)")
    m = s["o200k_base"]
    ax.axvspan(m["q1"], m["q3"], color=MUTED, alpha=0.16, lw=0)
    ax.axvline(m["median"], color=INK2, lw=1)
    ax.text(m["median"] + 0.015, 0.03, f"mediana narzutu {pl(100 * m['median'], 0)} %\n(tło: kwartyle)", fontsize=7, color=INK2, va="bottom")
    ax.axhline(0.5, color=NAT, lw=1.2, ls=(0, (1, 2)))
    ax.text(0.015, 0.512, "zdanie z 2 równie prawdopodobnymi odczytaniami", fontsize=7, color=NAT, ha="left", va="bottom")
    ax.text(0.05, 0.9, "PK tańsza", fontsize=8.5, color=PK, fontweight="bold")
    ax.text(1.05, 0.08, "zwykła polszczyzna tańsza", fontsize=8.5, color=NAT, fontweight="bold")
    ax.set_xlim(0, 1.5)
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(100 * v))} %"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(100 * v))} %"))
    ax.set_xlabel("narzut długości PK")
    ax.set_ylabel("błąd odczytania zdania zwykłego")
    ax.legend(loc="upper left", bbox_to_anchor=(0.18, 0.86), fontsize=7)
    star = 1 - (1 - e_mean) / (1 + m["median"])
    head(fig, f"Przy narzucie {pl(100 * m['median'], 0)} % tokenów PK opłaca się, gdy czytelnik myli się w więcej niż "
              f"{pl(100 * star, 0)} % odczytów zdania zwykłego",
         "Próg opłacalności w modelu ponawiania do skutku: koszt oczekiwany to długość tekstu podzielona przez prawdopodobieństwo poprawnego odczytania")
    foot(fig, f"Źródło: twierdzenie 4.4 pracy; narzut z results/p3_tokens.json (n = {m['n_items']}); błąd odczytania PK "
              f"z results/p4_summary.json ({models_word(len(errs))} po kontroli).")
    save(fig, "breakeven")


def fig_corpus():
    """Corpus linguistics: density of mechanically detectable choice points."""
    c = res("p5_corpus.json")["rows"]
    labels = {"A3": "A3: zaimki", "KW": "KW: „może”, „musi”", "B8": "B8: ponad 25 słów", "A5": "A5: słowa nieostre",
              "C3": "C3: „jeśli”, „chyba że”", "C2": "C2: „i” z „lub”", "B5": "B5: imiesłowy", "C5": "C5: 2 przeczenia",
              "D4": "D4: termin bez dnia 1", "D2": "D2: granica „do”", "B1": "B1: „należy”, „trzeba”"}
    acts = [r for r in c if r["register"] == "akt prawny"]
    codes = sorted(labels, key=lambda k: -np.mean([r["per_1000"][k] for r in acts]))
    names = {"konstytucja": "Konstytucja RP", "kc": "Kodeks cywilny", "kp": "Kodeks pracy", "prd": "Prawo o ruchu drogowym",
             "ztp": "Zasady techniki prawodawczej", "pk-standard": "Standard PK 0.1", "pk-paper2": "Praca „Rachunek generatorów”",
             "pk-paper3": "Niniejsza praca"}
    mat = np.array([[r["per_1000"][k] for k in codes] + [r["total_per_1000"]] for r in c])
    n_checks = len(c[0]["hits"]) - 1                    # without the candidate check B1s
    fig, ax = plt.subplots(figsize=(W, 0.36 * len(c) + 2.2))
    ax.grid(False)
    vmax = mat[:, :-1].max()
    ax.imshow(np.clip(mat[:, :-1], 0, vmax), cmap=SEQ, vmin=0, vmax=vmax, aspect="auto", extent=(-0.5, len(codes) - 0.5, len(c) - 0.5, -0.5))
    for i in range(len(c)):
        for j in range(len(codes)):
            v = mat[i, j]
            ax.text(j, i, pl(v, 1), ha="center", va="center", fontsize=6.8, color="white" if v > 0.55 * vmax else INK)
        ax.text(len(codes) + 0.1, i, pl(mat[i, -1], 1), ha="center", va="center", fontsize=7.6, fontweight="bold")
    ax.text(len(codes) - 0.2, -0.62, f"razem ({n_checks} kontroli)", ha="left", va="bottom", fontsize=6.6, fontweight="bold", rotation=38)
    n_act = len(acts)
    ax.plot([-0.5, len(codes) + 0.6], [n_act - 0.5, n_act - 0.5], color=INK, lw=0.9, clip_on=False)
    ax.set_xticks(range(len(codes)))
    ax.xaxis.tick_top()
    ax.set_xticklabels([labels[k] for k in codes], fontsize=6.6, rotation=38, ha="left", rotation_mode="anchor")
    ax.set_yticks(range(len(c)))
    ax.set_yticklabels([names.get(r["id"], r["id"]) for r in c], fontsize=7.6)
    ax.set_xlim(-0.5, len(codes) + 0.7)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    pks = [r for r in c if r["register"] != "akt prawny"]
    head(fig, f"Akty prawne mają od {pl(min(r['total_per_1000'] for r in acts), 0)} do {pl(max(r['total_per_1000'] for r in acts), 0)} "
              f"trafień sprawdzarki na 1000 słów; teksty pisane w PK mają od {pl(min(r['total_per_1000'] for r in pks), 1)} "
              f"do {pl(max(r['total_per_1000'] for r in pks), 1)}",
         "Liczba trafień na 1000 słów dla 11 najczęstszych kontroli; kolumna „razem” obejmuje wszystkie kontrole")
    foot(fig, f"Źródło: results/p5_corpus.json; n = {big(sum(r['words'] for r in acts))} słów w {n_act} aktach prawnych "
              f"i {big(sum(r['words'] for r in pks))} słów w {len(pks)} tekstach PK.")
    save(fig, "corpus")


TIMELINE = [  # year, track, label
    (1666, 0, "Leibniz, „De arte combinatoria”"), (1879, 0, "Frege, „Begriffsschrift”"),
    (1921, 0, "Wittgenstein, „Tractatus”"), (1933, 0, "Tarski, pojęcie prawdy"),
    (1934, 0, "Ajdukiewicz, obraz świata\ni aparatura pojęciowa"), (1960, 0, "Quine, „Word and Object”"),
    (1970, 0, "Montague, „English as\na Formal Language”"),
    (1836, 1, "Humboldt, o różności\nbudowy języków"), (1929, 1, "Sapir, „The Status of\nLinguistics as a Science”"),
    (1940, 1, "Whorf, „Science\nand Linguistics”"), (1964, 1, "Schaff, „Język a poznanie”"),
    (1996, 1, "Gumperz i Levinson,\n„Rethinking Linguistic Relativity”"),
    (1930, 2, "Ogden, „Basic English”"), (1960, 2, "Brown, Loglan"), (1986, 2, "AECMA Simplified English"),
    (1997, 2, "RFC 2119"), (2009, 2, "EARS"), (2014, 2, "Kuhn, przegląd 100 języków\nkontrolowanych"), (2026, 2, "PK 0.1"),
]


def fig_timeline():
    """History of ideas: three traditions that meet in a controlled language. Time runs downwards."""
    tracks = ["język idealny i logika", "relatywizm językowy", "języki kontrolowane i normy"]
    colors = [PK, YELLOW, AQUA]

    def pos(year):                                     # years before 1900 are compressed five times
        return (year - 1650) * 0.2 if year < 1900 else 50 + (year - 1900)

    fig, ax = plt.subplots(figsize=(W, 5.6))
    ax.grid(False)
    ax.set_xlim(-0.12, 3.3)
    ax.set_ylim(pos(2032), -9)
    ax.set_xticks([])
    ticks = [1650, 1750, 1850, 1900, 1920, 1940, 1960, 1980, 2000, 2020]
    ax.set_yticks([pos(y) for y in ticks])
    ax.set_yticklabels([str(y) for y in ticks])
    ax.spines["bottom"].set_visible(False)
    ax.axhline(pos(1900), color=RULE, lw=0.8, ls=(0, (3, 3)))
    ax.text(3.28, pos(1900) - 1.2, "zmiana skali lat", fontsize=6.5, color=MUTED, ha="right", va="bottom")
    for t, name in enumerate(tracks):
        t = t * 1.1
        col = colors[round(t / 1.1)]
        ax.plot([t, t], [-2, pos(2030)], color=col, lw=1.8, zorder=1, solid_capstyle="butt")
        ax.text(t, -4.5, name, fontsize=8.4, fontweight="bold", color=col, va="center", ha="left")
        prev = -100.0
        for year, _t, label in sorted(e for e in TIMELINE if abs(e[1] * 1.1 - t) < 1e-9):
            lines = label.count("\n") + 1
            y = max(pos(year), prev)
            prev = y + 4.6 * lines + 2.2
            ax.scatter([t], [pos(year)], s=24, color=col, zorder=3, edgecolor="white", lw=0.6)
            ax.plot([t, t + 0.045, t + 0.045, t + 0.07], [pos(year), pos(year), y, y], color=RULE, lw=0.7, zorder=2,
                    solid_joinstyle="miter")
            ax.text(t + 0.085, y, f"{year}  {label}", fontsize=6.9, va="center_baseline" if lines == 1 else "top",
                    ha="left", color=INK, linespacing=1.0)
    fig.subplots_adjust(top=0.99, bottom=0.02)
    head(fig, "PK łączy 3 tradycje: logiczny ideał jednego znaczenia, tezę o wpływie języka na myślenie i inżynierskie języki kontrolowane",
         "Oś czasu wybranych prac; czas biegnie w dół")
    foot(fig, f"Źródło: bibliografia pracy; n = {len(TIMELINE)} pozycji.")
    save(fig, "timeline")


FIGURES = {"relation": fig_relation, "gray_zone": fig_gray, "truth_tables": fig_truth, "growth": fig_growth,
           "parser": fig_parser, "classes": fig_classes, "rules": fig_rules, "tokens": fig_tokens,
           "probe": fig_probe, "breakeven": fig_breakeven, "corpus": fig_corpus, "timeline": fig_timeline}

if __name__ == "__main__":
    for name in (sys.argv[1:] or FIGURES):
        FIGURES[name]()
