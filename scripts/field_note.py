"""Field note: one working day on parallel Claude Code terminals, and the token trial of PK.

Usage:  python scripts/field_note.py [--day YYYY-MM-DD]

Reads three sources and writes results/field_note.json and paper/figures/field_note.png:
  1. the local Claude Code transcripts of the day (numbers only: time, model, token counts);
  2. results/trial_<model>.jsonl from scripts/token_trial.py;
  3. the PK skill file, to count the tokens that PK adds to the context of a session.
No prompt text and no session identifier leaves this script.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from scripts.probe import OPPOSITE, answer_side, load_items  # noqa: E402
from src.pklint import lint  # noqa: E402

TRANSCRIPTS = os.path.expanduser("~/.claude/projects/*/*.jsonl")
SKILL = os.path.join(ROOT, "skills", "polszczyzna-kontrolowana", "SKILL.md")
WINDOW = 300                                   # seconds per cell of the timeline
PRICE = {"out": 5.0, "write": 2.0, "read": 0.1}   # weights of the public price list, input token = 1


def local_epoch(ts):
    return time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - time.timezone


def read_sessions(day, family="claude-fable"):
    """Per session of the day: API calls (time, output, cache write, cache read), human prompts, PK skill load."""
    lo = time.mktime(time.strptime(day, "%Y-%m-%d"))
    sessions = []
    for path in glob.glob(TRANSCRIPTS):
        if os.path.getmtime(path) < lo:
            continue
        calls, prompts, skill_at = {}, [], None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                ts, m = d.get("timestamp"), d.get("message") or {}
                if not ts:
                    continue
                t = local_epoch(ts)
                if not lo <= t < lo + 86400:
                    continue
                c = m.get("content")
                if d.get("type") == "user" and not d.get("isMeta"):
                    parts = [c] if isinstance(c, str) else [x.get("text", "") for x in c or []
                                                            if isinstance(x, dict) and x.get("type") == "text"]
                    tool = isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c)
                    if parts and not tool and not parts[0].lstrip().startswith("<"):
                        prompts.append((t, " ".join(parts)))
                if d.get("type") == "assistant":
                    for x in c if isinstance(c, list) else []:
                        if isinstance(x, dict) and x.get("type") == "tool_use" and skill_at is None and \
                                "polszczyzna-kontrolowana" in json.dumps(x.get("input", {})):
                            skill_at = t
                    u = m.get("usage")
                    if u and str(m.get("model", "")).startswith(family):
                        old = calls.get(m.get("id"))
                        if old is None or (u.get("output_tokens") or 0) > old[1]:
                            calls[m.get("id")] = (t, u.get("output_tokens") or 0,
                                                  u.get("cache_creation_input_tokens") or 0,
                                                  u.get("cache_read_input_tokens") or 0)
        if calls:
            sessions.append({"calls": sorted(calls.values()), "prompts": sorted(prompts), "skill_at": skill_at})
    return sorted(sessions, key=lambda s: s["calls"][0][0])


def day_summary(sessions, skill_tokens):
    """Totals, concurrency per window, output tokens per human order, and what the PK skill costs in context."""
    grid = defaultdict(lambda: defaultdict(int))             # window -> session index -> output tokens
    per_order, skill_read, total = [], 0, Counter()
    for i, s in enumerate(sessions):
        for t, out, write, read in s["calls"]:
            grid[int(t // WINDOW)][i] += out
            total.update(calls=1, out=out, write=write, read=read)
            if s["skill_at"] is not None and t > s["skill_at"]:
                skill_read += skill_tokens                    # the skill text is re-read from cache on every later call
        edges = [t for t, _ in s["prompts"]] + [float("inf")]
        for a, b in zip(edges, edges[1:]):
            spent = sum(out for t, out, _, _ in s["calls"] if a <= t < b)
            if spent:
                per_order.append(spent)
    hits, words, _, _ = lint("\n\n".join(text for s in sessions for _, text in s["prompts"]))   # are the orders in PK?
    busy = Counter(len(v) for v in grid.values())
    return {"sessions": len(sessions), "skill_sessions": sum(s["skill_at"] is not None for s in sessions),
            "calls": total["calls"], "out": total["out"], "cache_write": total["write"], "cache_read": total["read"],
            "windows_by_active_sessions": dict(sorted(busy.items())),
            "max_parallel": max(busy) if busy else 0,
            "minutes_at_max": busy[max(busy)] * WINDOW // 60 if busy else 0,
            "orders": len(per_order), "order_words": words,
            "order_lint_per_1000_words": (sum(hits.values()) * 1000 / words) if words else None, "out_per_order_median": statistics.median(per_order) if per_order else 0,
            "skill_tokens": skill_tokens, "skill_cache_read": skill_read}, grid


def kind(answer):
    """'Tak', 'Nie' or 'ask' (the model asks back or gives no verdict)."""
    if "PYTANIE" in answer.upper() or answer.rstrip().endswith("?"):
        return "ask"
    side = answer_side(answer)
    return "ask" if side is None else ("Tak" if side == 1.0 else "Nie")


def trial_summary(model):
    """Shares of correct / asked / wrong decisions and tokens per call, ordinary Polish against PK."""
    path = os.path.join(ROOT, "results", f"trial_{model}.jsonl")
    if not os.path.exists(path):
        return None
    recs = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for r in map(json.loads, fh):
            recs[r["pid"]].append(r)
    out = {}
    for label, variant_of in (("ordinary", lambda intent: "nat"), ("pk", lambda intent: f"pk{intent}")):
        tally, tokens_in, tokens_out = Counter(), [], []
        for it in load_items():
            for intent, key in ((1, it["gray1"]), (2, OPPOSITE[it["gray1"]])):   # the author means reading 1 or reading 2
                for r in recs.get(f"{it['id']}:{variant_of(intent)}", []):
                    k = kind(r["answer"])
                    tally["ask" if k == "ask" else "ok" if k == key else "wrong"] += 1
                    tokens_in.append(r["in_tokens"])
                    tokens_out.append(r["out_tokens"])
        n = sum(tally.values())
        out[label] = {"n": n, "ok": tally["ok"] / n, "ask": tally["ask"] / n, "wrong": tally["wrong"] / n,
                      "in_mean": statistics.mean(tokens_in), "out_mean": statistics.mean(tokens_out)}
    for label in ("ordinary", "pk"):          # tokens until a correct decision: a question back or an error costs one more call in PK
        v, pk = out[label], out["pk"]
        v["tokens_to_correct"] = (v["in_mean"] + v["out_mean"]) + (v["ask"] + v["wrong"]) * (pk["in_mean"] + pk["out_mean"])
    return out


def skill_token_count():
    with open(SKILL, encoding="utf-8") as fh:
        text = fh.read()
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(text)), "o200k_base"
    except Exception:                          # ponytail: 3.2 characters per token when tiktoken is missing
        return round(len(text) / 3.2), "characters / 3.2"


def figure(day, summary, grid, trials, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap

    blue, orange, yellow, ink, ink2, rule = "#2a78d6", "#eb6834", "#eda100", "#0b0b0b", "#52514e", "#c3c2b7"
    seq = LinearSegmentedColormap.from_list("blue", ["#ffffff", "#cde2fb", "#3987e5", "#0d366b"])
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": rule,
                         "axes.labelcolor": ink2, "xtick.color": ink2, "ytick.color": ink2, "text.color": ink,
                         "legend.frameon": False, "savefig.dpi": 150, "savefig.bbox": "tight"})
    comma = lambda x, nd=0: f"{x:.{nd}f}".replace(".", ",")
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(7.4, 8.6), constrained_layout=True,
                                     gridspec_kw=dict(height_ratios=[1.0, 1.0, 0.8]))

    wins = sorted(grid)
    w0, w1 = wins[0], wins[-1]
    mat = np.zeros((summary["sessions"], w1 - w0 + 1))
    for w, row in grid.items():
        for i, out in row.items():
            mat[i, w - w0] = out / 1000
    im = a1.imshow(mat, aspect="auto", cmap=seq, interpolation="nearest",
                   extent=(w0 * WINDOW, (w1 + 1) * WINDOW, summary["sessions"] + 0.5, 0.5))
    step = 600 if (w1 - w0) * WINDOW < 7200 else 1800
    ticks = [t for t in range(int(w0 * WINDOW // step) * step, int((w1 + 1) * WINDOW) + 1, step) if t >= w0 * WINDOW]
    a1.set_xticks(ticks, [time.strftime("%H:%M", time.localtime(t)) for t in ticks])
    a1.set_yticks(range(1, summary["sessions"] + 1), [f"terminal {i}" for i in range(1, summary["sessions"] + 1)])
    fig.colorbar(im, ax=a1, pad=0.01, label="tokeny wyjściowe na 5 min [tys.]")
    a1.set_title(f"{day}: najwyżej {summary['max_parallel']} sesje Fable 5.2 naraz; "
                 f"razem {comma(summary['out'] / 1000)} tys. tokenów wyjściowych", pad=16)
    a1.annotate(f"1 wiersz = 1 sesja Claude Code; kolor = tokeny wyjściowe w oknie 5 min; stan z {time.strftime('%H:%M')}",
                (0, 1), xycoords="axes fraction",
                xytext=(0, 4), textcoords="offset points", fontsize=8, color=ink2, va="bottom")

    rows, labels = [], []
    for model, t in trials.items():
        for label, name in (("ordinary", "zwykła polszczyzna"), ("pk", "PK")):
            rows.append(t[label])
            labels.append(f"{model.capitalize()}, {name}")
    y = np.arange(len(rows))[::-1]
    left = np.zeros(len(rows))
    for key, color, name in (("ok", blue, "decyzja zgodna z intencją autora"), ("ask", yellow, "pytanie zwrotne"),
                             ("wrong", orange, "decyzja niezgodna z intencją")):
        vals = np.array([r[key] * 100 for r in rows])
        a2.barh(y, vals, left=left, color=color, height=0.62, edgecolor="white", linewidth=1.5, label=name)
        for yy, v, l in zip(y, vals, left):
            if v >= 6:
                a2.text(l + v / 2, yy, f"{comma(v)} %", ha="center", va="center", fontsize=8,
                        color="white" if color != yellow else ink)
        left += vals
    a2.set_yticks(y, labels)
    a2.set(xlim=(0, 100), xlabel="udział odpowiedzi [%]")
    a2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, fontsize=8)
    worst = max(trials.values(), key=lambda t: t["ordinary"]["wrong"] - t["pk"]["wrong"])
    a2.set_title(f"Zlecenie niejednoznaczne: PK zmniejsza udział pytań zwrotnych i decyzji niezgodnych z intencją", pad=16)
    a2.annotate(f"44 pary zdań, 2 intencje autora, 2 próby; n = {rows[0]['n']} odpowiedzi na słupek",
                (0, 1), xycoords="axes fraction", xytext=(0, 4), textcoords="offset points", fontsize=8, color=ink2, va="bottom")

    vals = [r["tokens_to_correct"] for r in rows]
    a3.barh(y, vals, color=[ink2 if i % 2 == 0 else blue for i in range(len(rows))], height=0.62)
    for yy, v in zip(y, vals):
        a3.text(v + max(vals) * 0.01, yy, comma(v), va="center", fontsize=8)
    a3.set_yticks(y, labels)
    a3.set(xlabel="tokeny (wejście i wyjście) do decyzji zgodnej z intencją", xlim=(0, max(vals) * 1.12))
    deltas = [1 - t["pk"]["tokens_to_correct"] / t["ordinary"]["tokens_to_correct"] for t in trials.values()]
    a3.set_title("Koszt zlecenia do poprawnej decyzji: PK " + " i ".join(
        f"{'niższy' if d > 0 else 'wyższy'} o {comma(abs(d) * 100)} % ({m.capitalize()})" for m, d in zip(trials, deltas)), pad=16)
    a3.annotate("pytanie zwrotne albo błędna decyzja = 1 dodatkowe wywołanie z tekstem w PK [założenie]",
                (0, 1), xycoords="axes fraction", xytext=(0, 4), textcoords="offset points", fontsize=8, color=ink2, va="bottom")
    fig.text(0, -0.01, "Źródło: scripts/field_note.py; transkrypty Claude Code (same liczby) i results/trial_*.jsonl",
             fontsize=7.5, color="#898781", va="top")
    fig.savefig(path)
    plt.close(fig)


START, END = "<!-- field-note:start -->", "<!-- field-note:end -->"


def markdown(out):
    """The README section, in PK, with a source marker after every fact."""
    s, day, at = out["summary"], out["day"], out["measured_at"]
    pl = lambda x, nd=0: f"{x:.{nd}f}".replace(".", ",")
    rows = []
    for model, t in out["trial"].items():
        for label, name in (("ordinary", "zwykła polszczyzna"), ("pk", "PK")):
            v = t[label]
            rows.append(f"| {model.capitalize()} | {name} | {pl(v['ok'] * 100)} % | {pl(v['ask'] * 100)} % | "
                        f"{pl(v['wrong'] * 100)} % | {pl(v['tokens_to_correct'])} |")
    gain = " i ".join(f"o {pl((1 - t['pk']['tokens_to_correct'] / t['ordinary']['tokens_to_correct']) * 100)} % ({m.capitalize()})"
                      for m, t in out["trial"].items())
    n = next(iter(out["trial"].values()))["pk"]["n"]
    return f"""## Notatka z pracy: {s['max_parallel']} sesje równolegle ({day})

Autor prowadził {day} równolegle {s['sessions']} sesje Claude Code z modelem Fable 5.2.
Standard PK był wczytany w {s['skill_sessions']} z {s['sessions']} sesji. Agenci pisali w PK plany, raporty
i zlecenia dla innych agentów. Autor ocenia, że PK ułatwia prowadzenie {s['sessions']} sesji naraz,
bo tekst agenta ma 1 odczytanie `[relacja: autor, {day}]`.

| Wielkość | Wartość |
|---|---|
| sesje z modelem Fable 5.2 | {s['sessions']} |
| najwięcej sesji aktywnych w 1 oknie 5 min | {s['max_parallel']} |
| wywołania modelu | {s['calls']} |
| tokeny wyjściowe | {pl(s['out'] / 1e3)} tys. |
| tokeny zapisu do cache'u | {pl(s['cache_write'] / 1e6, 2)} mln |
| tokeny odczytu z cache'u | {pl(s['cache_read'] / 1e6, 1)} mln |
| zlecenia autora | {s['orders']} |
| mediana tokenów wyjściowych na 1 zlecenie | {pl(s['out_per_order_median'] / 1e3)} tys. |

Źródło tabeli: `[pomiar: transkrypty Claude Code, {at}]`.

### Czy PK oszczędza tokeny

Wynik pomiaru: przy zleceniu niejednoznacznym PK oszczędza tokeny. Przy zleceniu o 1 odczytaniu
PK kosztuje tokeny.

Pomiar używa 44 par zdań z pracy badawczej (`data/items.csv`). Zdanie zwykłe ma 2 odczytania.
Zdanie PK ma 1 odczytanie. Model dostaje tekst i sytuację, w której 2 odczytania dają różne
decyzje. Model odpowiada „Tak” albo „Nie”, albo zadaje pytanie zwrotne. Autor zdania zwykłego
ma na myśli każde z 2 odczytań w połowie przypadków `[założenie]`.

| Model | Tekst | Decyzja zgodna z intencją | Pytanie zwrotne | Decyzja niezgodna | Tokeny do poprawnej decyzji |
|---|---|---|---|---|---|
{chr(10).join(rows)}

Źródło tabeli: `[pomiar: scripts/token_trial.py, {at}]`; {n} odpowiedzi na wiersz.

- Koszt tokenów do poprawnej decyzji jest w PK niższy {gain} `[obliczenie: tabela]`.
  Pytanie zwrotne albo decyzja niezgodna kosztuje 1 dodatkowe wywołanie z tekstem w PK `[założenie]`.
- Zdania testowe są wybrane jako niejednoznaczne. Dla zdania o 1 odczytaniu PK jest tylko
  kosztem: mediana narzutu wynosi 37 % tokenów `[źródło: paper/pk_complexity_pl.pdf, pomiar P3]`.
- Standard PK ma w kontekście sesji długość {s['skill_tokens']} tokenów `[obliczenie: tokenizer {s['tokenizer']}]`.
  W {s['skill_sessions']} sesjach dało to {pl(s['skill_cache_read'] / 1e6, 2)} mln tokenów odczytu z cache'u. Ta liczba odpowiada
  {pl(s['pk_context_cost_out_equiv'] / 1e3)} tys. tokenów wyjściowych według wag cennika: wyjście 5, odczyt 0,1 `[obliczenie]`.
- 1 zlecenie wykonane błędnie i powtórzone kosztuje medianę {pl(s['out_per_order_median'] / 1e3)} tys. tokenów wyjściowych.
  PK zwraca się, gdy zapobiega co najmniej 1 powtórce na dzień `[obliczenie]`.
- Liczby powtórek, którym PK zapobiegło {day}, nikt nie zmierzył. Zlecenia autora z tego dnia
  mają {pl(s['order_lint_per_1000_words'])} trafień sprawdzarki PK na 1000 słów, czyli nie są pisane w PK
  `[pomiar: src/pklint.py, {at}]`.

![Sesje z {day} i wynik pomiaru tokenów](paper/figures/field_note.png)

Odtworzenie pomiaru i rysunku:

```sh
python scripts/token_trial.py haiku && python scripts/token_trial.py sonnet
python scripts/field_note.py --day {day}
```
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=time.strftime("%Y-%m-%d"))
    args = ap.parse_args()
    skill_tokens, tokenizer = skill_token_count()
    sessions = read_sessions(args.day)
    summary, grid = day_summary(sessions, skill_tokens)
    trials = {m: t for m in ("haiku", "sonnet") if (t := trial_summary(m))}
    # what PK cost on that day, in output-token equivalents of the price list, and how many avoided reruns pay for it
    pk_cost = summary["skill_cache_read"] * PRICE["read"] / PRICE["out"]
    summary.update(tokenizer=tokenizer, pk_context_cost_out_equiv=round(pk_cost),
                   reruns_to_break_even=(pk_cost / summary["out_per_order_median"]) if summary["out_per_order_median"] else None)
    out = {"day": args.day, "measured_at": time.strftime("%Y-%m-%d %H:%M"), "summary": summary, "trial": trials}
    with open(os.path.join(ROOT, "results", "field_note.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    if summary["sessions"] and trials:
        figure(args.day, summary, grid, trials, os.path.join(ROOT, "paper", "figures", "field_note.png"))
        readme = os.path.join(ROOT, "README.md")
        with open(readme, encoding="utf-8") as fh:
            text = fh.read()
        a, b = text.index(START) + len(START), text.index(END)      # the section between the two markers is generated
        with open(readme, "w", encoding="utf-8") as fh:
            fh.write(text[:a] + "\n" + markdown(out) + "\n" + text[b:])
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
