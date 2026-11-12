"""Measurements P1-P5 of the paper: every number in the text comes from this script.

Usage:  python scripts/measure.py            everything (needs the network for tokenizers and the corpus)
        python scripts/measure.py --offline  reuse results/p3_tokens.json and results/p5_corpus.json
Output: results/*.json and paper/data/*.tex (macros and table rows).
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import math
import os
import re
import statistics as st
import subprocess
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from src import pklint, pkmodel as M  # noqa: E402
import probe  # noqa: E402

RES = os.path.join(ROOT, "results")
TEX = os.path.join(ROOT, "paper", "data")
CACHE = os.path.expanduser("~/.cache/pk-corpus")
OFFLINE = "--offline" in sys.argv


def read_csv(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def dump(name, obj):
    with open(os.path.join(RES, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as fh:
        return json.load(fh)


def pl(x, nd=2):
    """Number with a Polish decimal comma."""
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def big(n):
    """Integer with thin spaces between groups of three digits (five or more digits)."""
    s = str(n)
    return s if len(s) < 5 else re.sub(r"(?<=\d)(?=(\d{3})+$)", r"\\,", s)


def h2(p):
    return 0.0 if p <= 0 or p >= 1 else -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def sign_test(plus, minus):
    """Exact two-sided sign test."""
    n, k = plus + minus, min(plus, minus)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def boot_median(values, seed=1, reps=10000):
    rng = np.random.default_rng(seed)
    v = np.asarray(values, dtype=float)
    meds = np.median(rng.choice(v, size=(reps, len(v)), replace=True), axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


# ---------------------------------------------------------------------------
def p1_counts():
    """Exact numbers of readings."""
    out = {
        "attachment": [{"k": k, "readings": M.count_parses(M.GRAMMAR_NAT, M.sentence(k))} for k in range(0, 11)],
        "bracketing": [dict(zip(("n", "bracketings", "functions"), (n, *M.bracketings(M.alternating(n)))))
                       for n in range(2, 12)],
        "scope": [dict(zip(("n", "orders", "distinct"), (n, *M.scope_orders(("AE" * n)[:n])))) for n in range(2, 8)],
        "binary": [{"k": k, "readings": 2 ** k} for k in range(0, 11)],
        "catalan_19": M.catalan(19), "catalan_24": M.catalan(24),
        "open_list": {"universe": 10, "listed": 2, "readings": M.open_list_readings(10, 2)},
    }
    assert all(r["readings"] == M.catalan(r["k"] + 1) for r in out["attachment"])
    dump("p1_counts.json", out)
    return out


def p2_parser():
    """Earley operations for the ambiguous grammar and for the PK grammar."""
    rows = []
    for k in range(0, 41):
        toks = M.sentence(k)
        ok1, nat = M.earley(M.GRAMMAR_NAT, toks)
        ok2, pk = M.earley(M.GRAMMAR_PK, toks)
        assert ok1 and ok2
        rows.append({"k": k, "words": len(toks), "ops_nat": nat, "ops_pk": pk,
                     "parses_nat": M.count_parses(M.GRAMMAR_NAT, toks), "parses_pk": M.count_parses(M.GRAMMAR_PK, toks)})
    fit = [r for r in rows if r["words"] >= 21]
    x = np.log([r["words"] for r in fit])
    out = {"rows": rows,
           "exp_nat": float(np.polyfit(x, np.log([r["ops_nat"] for r in fit]), 1)[0]),
           "exp_pk": float(np.polyfit(x, np.log([r["ops_pk"] for r in fit]), 1)[0]),
           "fit_from_words": 21}
    dump("p2_parser.json", out)
    return out


# The Bielik tokenizers are gated on the Hugging Face Hub (HTTP 401 without an accepted licence): left out.
TOKENIZERS = [("o200k_base", "tiktoken"), ("cl100k_base", "tiktoken"),
              ("unsloth/Llama-3.2-3B-Instruct", "hf"), ("unsloth/gemma-3-4b-it", "hf")]


def p3_tokens(items):
    """Length of the ordinary sentence and of the two PK sentences in words, characters and tokens."""
    if OFFLINE:
        return load("p3_tokens.json")
    counters, failed = {}, []
    for name, kind in TOKENIZERS:
        try:
            if kind == "tiktoken":
                import tiktoken
                enc = tiktoken.get_encoding(name)
                counters[name] = lambda s, enc=enc: len(enc.encode(s))
            else:
                from tokenizers import Tokenizer
                tok = Tokenizer.from_pretrained(name)
                counters[name] = lambda s, tok=tok: len(tok.encode(s, add_special_tokens=False).ids)
        except Exception as err:                                  # a gated or unreachable tokenizer is reported
            failed.append({"tokenizer": name, "error": str(err)[:160]})
    counters = {"words": pklint.n_words, "chars": len, **counters}
    rows = []
    for it in items:
        row = {"id": it["id"], "kind": it["kind"]}
        for unit, fn in counters.items():
            row[unit] = {v: fn(it[v]) for v in ("nat", "pk1", "pk2")}
        rows.append(row)
    legends = sorted({it["legend"] for it in items if it["legend"]})
    out = {"units": list(counters), "failed": failed, "rows": rows,
           "legends": [{"text": l, **{u: fn(l) for u, fn in counters.items()}} for l in legends]}
    dump("p3_tokens.json", out)
    return out


def p3_summary(tok):
    """Overhead of PK: length(PK) / length(ordinary) - 1 for the rewritten items."""
    out = {}
    for unit in tok["units"]:
        deltas = [r[unit][v] / r[unit]["nat"] - 1 for r in tok["rows"] if r["kind"] != "convention" for v in ("pk1", "pk2")]
        per_item = [(r[unit]["pk1"] + r[unit]["pk2"]) / (2 * r[unit]["nat"]) - 1 for r in tok["rows"] if r["kind"] != "convention"]
        q = st.quantiles(per_item, n=4)
        lo, hi = boot_median(per_item)
        out[unit] = {"n_items": len(per_item), "median": st.median(per_item), "q1": q[0], "q3": q[2],
                     "min": min(per_item), "max": max(per_item), "mean": st.mean(per_item),
                     "ci_lo": lo, "ci_hi": hi, "share_longer": sum(d > 0 for d in deltas) / len(deltas),
                     "sum_nat": sum(r[unit]["nat"] for r in tok["rows"] if r["kind"] != "convention"),
                     "sum_pk": sum((r[unit]["pk1"] + r[unit]["pk2"]) / 2 for r in tok["rows"] if r["kind"] != "convention")}
    return out


def p4_probe(items):
    """Aggregates of the gray-zone probe, one block per model file."""
    probes = probe.build_probes(items)
    by_item = {it["id"]: it for it in items}
    models = []
    for path in sorted(glob.glob(os.path.join(RES, "probe_*.jsonl"))):
        with open(path, encoding="utf-8") as fh:
            recs = [json.loads(line) for line in fh if line.strip()]
        if not recs:
            continue
        ans = {r["key"]: r for r in recs}
        backend, model = recs[0]["backend"], recs[0]["model"]
        per_item, anchors, missing = [], {"nat": [], "pk": []}, 0
        for it in items:
            def p(variant, kind, it=it):
                key = next(q["key"] for q in probes if q["pid"] == f"{it['id']}:{variant}:{kind}")
                r = ans.get(key)
                return None if r is None or r["p_yes"] is None else r["p_yes"]

            def q1(variant, it=it):                              # probability of reading 1 in the gray zone
                v = p(variant, "gray")
                return None if v is None else (v if it["gray1"] == "Tak" else 1 - v)

            q = {v: q1(v) for v in ("nat", "pk1", "pk2")}
            if it["legend"]:
                q.update({v: q1(v) for v in ("pk1L", "pk2L")})
            if any(q[v] is None for v in ("nat", "pk1", "pk2")):
                missing += 1
                continue
            for variant, bucket in (("nat", "nat"), ("pk1", "pk"), ("pk2", "pk")):
                for kind, want in (("yes", 1), ("no", 0)):
                    v = p(variant, kind)
                    if v is not None:
                        anchors[bucket].append(int((v > 0.5) == bool(want)))
            per_item.append({"id": it["id"], "kind": it["kind"], "source": it["source"], **q,
                             "h_nat": h2(q["nat"]), "h_pk": (h2(q["pk1"]) + h2(q["pk2"])) / 2,
                             "steer": q["pk1"] - q["pk2"],
                             "acc_pk": (int(q["pk1"] > 0.5) + int(q["pk2"] < 0.5)) / 2})
        if not per_item:
            continue
        rew = [r for r in per_item if r["kind"] == "restriction"]
        conv = [r for r in per_item if r["kind"] == "convention"]
        diff = [r["h_nat"] - r["h_pk"] for r in rew]
        plus, minus = sum(d > 1e-9 for d in diff), sum(d < -1e-9 for d in diff)
        graded = backend != "claude"                       # entropy needs log-probabilities
        samples = recs[0].get("n", 1)
        block = {
            "backend": backend, "model": model, "graded": graded, "n_items": len(per_item), "missing_items": missing,
            "n_rewrite": len(rew), "items": per_item,
            "h_nat_median": st.median(r["h_nat"] for r in rew), "h_pk_median": st.median(r["h_pk"] for r in rew),
            "h_nat_mean": st.mean(r["h_nat"] for r in rew), "h_pk_mean": st.mean(r["h_pk"] for r in rew),
            "sign_plus": plus, "sign_minus": minus, "sign_p": sign_test(plus, minus),
            "steer_median": st.median(r["steer"] for r in rew), "steer_mean": st.mean(r["steer"] for r in rew),
            "acc_pk": st.mean(r["acc_pk"] for r in rew),
            "acc_anchor_nat": st.mean(anchors["nat"]) if anchors["nat"] else None,
            "acc_anchor_pk": st.mean(anchors["pk"]) if anchors["pk"] else None,
            "reading1_share": st.mean(int(r["nat"] > 0.5) for r in per_item),
            "undecided_share": st.mean(int(0.2 < r["nat"] < 0.8) for r in per_item),
            "mass_median": st.median(r["mass"] for r in recs if r.get("mass") is not None),
            "samples": samples,
            # a local model qualifies when it answers at least 80 % of the anchors by the key; no anchors: None
            "qualified": None if not anchors["nat"] else bool(st.mean(anchors["nat"]) >= 0.8 and st.mean(anchors["pk"]) >= 0.8),
            "prompt_tokens_median": st.median(r["prompt_tokens"] for r in recs if r.get("prompt_tokens")),
            "unstable_nat": st.mean(int(0 < r["nat"] < 1) for r in per_item) if samples > 1 else None,
            "unstable_pk": st.mean((int(0 < r["pk1"] < 1) + int(0 < r["pk2"] < 1)) / 2 for r in per_item) if samples > 1 else None,
            "conv": [{"id": r["id"], "pk1": r["pk1"], "pk2": r["pk2"], "pk1L": r.get("pk1L"), "pk2L": r.get("pk2L")} for r in conv],
            "gap": [{"id": r["id"], "nat": r["nat"], "pk1": r["pk1"], "pk2": r["pk2"]} for r in per_item if r["kind"] == "gap"],
        }
        if len(diff) > 1:
            block["diff_median"] = st.median(diff)
            block["diff_ci"] = boot_median(diff)
        cl = [r for r in conv if r.get("pk1L") is not None and r.get("pk2L") is not None]
        if cl:
            block["conv_acc_plain"] = st.mean((int(r["pk1"] > 0.5) + int(r["pk2"] < 0.5)) / 2 for r in cl)
            block["conv_acc_legend"] = st.mean((int(r["pk1L"] > 0.5) + int(r["pk2L"] < 0.5)) / 2 for r in cl)
            block["conv_steer_plain"] = st.mean(r["pk1"] - r["pk2"] for r in cl)
            block["conv_steer_legend"] = st.mean(r["pk1L"] - r["pk2L"] for r in cl)
        models.append(block)

    # agreement between models: do the readers choose the same reading?
    agree = []
    readers = [m for m in models if m["qualified"] is not False]
    for it in items:
        votes = {v: [int(r[v] > 0.5) for m in readers for r in m["items"] if r["id"] == it["id"]] for v in ("nat", "pk1", "pk2")}
        if len(votes["nat"]) >= 2:
            agree.append({"id": it["id"], "kind": it["kind"], "readers": len(votes["nat"]),
                          "nat_reading1": sum(votes["nat"]), "pk1_reading1": sum(votes["pk1"]), "pk2_reading1": sum(votes["pk2"]),
                          "nat_split": 0 < sum(votes["nat"]) < len(votes["nat"]),
                          "pk_correct": sum(votes["pk1"]) == len(votes["pk1"]) and sum(votes["pk2"]) == 0})
    out = {"models": models, "agreement": agree, "readers": [m["model"] for m in readers]}
    cl = [m for m in models if m["backend"] == "claude"]
    if len(cl) == 2:                                   # the two Claude models as a pair of readers
        a, b = ({r["id"]: r for r in m["items"]} for m in cl)
        ids = [i for i in a if i in b]
        sure = [i for i in ids if a[i]["nat"] in (0, 1) and b[i]["nat"] in (0, 1)]
        out["claude_pair"] = {
            "items": len(ids), "unsure": len(ids) - len(sure),
            "split": sum(a[i]["nat"] != b[i]["nat"] for i in sure), "agree": sum(a[i]["nat"] == b[i]["nat"] for i in sure),
            "pk_both": sum(a[i]["acc_pk"] == 1 and b[i]["acc_pk"] == 1 for i in ids)}
    if agree:
        out["nat_split_share"] = st.mean(int(a["nat_split"]) for a in agree)
        out["pk_all_correct_share"] = st.mean(int(a["pk_correct"]) for a in agree)
    dump("p4_summary.json", out)
    return out


def fetch(source):
    """Text of one corpus source; downloads go to ~/.cache/pk-corpus (outside the repository)."""
    if not source.startswith("http"):
        path = os.path.join(ROOT, source)
        if not os.path.exists(path):
            return None, None
        with open(path, "rb") as fh:
            raw = fh.read()
    else:
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, hashlib.sha1(source.encode()).hexdigest()[:16] + os.path.splitext(source)[1])
        if not os.path.exists(path):
            req = urllib.request.Request(source, headers={"User-Agent": "corpus-statistics/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(path, "wb") as fh:
                fh.write(resp.read())
        with open(path, "rb") as fh:
            raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    if path.endswith(".pdf"):
        text = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, check=True).stdout.decode("utf-8")
        text = re.sub(r"(?m)^\s*(?:Dziennik Ustaw|©Kancelaria Sejmu).*$", "", text)
        text = re.sub(r"(?m)^\s*[–-]\s*\d+\s*[–-]\s*(?:Poz\.\s*\d+)?\s*$", "", text)
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text).replace("\f", "\n\n")
        text = re.sub(r"(?m)^\s*(?:Rozdział|DZIAŁ|TYTUŁ|KSIĘGA|Oddział)\b.*$", "", text)     # headings of units
        text = re.sub(r"(?m)^\s*(?:Art\.|§)\s*\d+[a-z]*\.?\s*", "", text)                    # numbers of units
        text = re.sub(r"(?m)^\s*\d+[a-z]?[.)]\s+", "", text)
    else:
        text = raw.decode("utf-8")
        if path.endswith(".tex"):
            def expand(m):
                sub = os.path.join(os.path.dirname(path), m.group(1) + ".tex")
                if "data/" in m.group(1) or not os.path.exists(sub):
                    return ""
                with open(sub, encoding="utf-8") as fh:
                    return fh.read()
            text = re.sub(r"\\input\{([^{}]+)\}", expand, text)
            text = pklint.strip_tex(text)
        elif path.endswith(".md"):
            text = re.sub(r"```.*?```", "", text, flags=re.S)
            text = re.sub(r"(?m)^\|.*$", "", text)                 # tables list forbidden words: mention, not use
            text = re.sub(r"(?m)^---\n.*?\n---\n", "", text, count=1, flags=re.S)
            text = re.sub(r"(?m)^#+ .*$", "", text)
            text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("**", "")
    return text, digest


def p5_corpus():
    """Density of mechanically detectable choice points per 1000 words."""
    if OFFLINE:
        return load("p5_corpus.json")
    rows = []
    for src in read_csv("corpus.csv"):
        text, digest = fetch(src["source"])
        if text is None:
            continue
        hits, words, n_sent, examples = pklint.lint(text, candidates=True)
        lengths = [pklint.n_words(s) for s in pklint.sentences(text)]
        rows.append({"id": src["id"], "register": src["register"], "title": src["title"], "sha256": digest,
                     "words": words, "sentences": n_sent, "sentence_median": st.median(lengths),
                     "share_over_25": sum(n > 25 for n in lengths) / len(lengths),
                     "hits": {c: hits[c] for c in pklint.CODES + ["B1s"]},
                     "per_1000": {c: 1000 * hits[c] / words for c in pklint.CODES + ["B1s"]},
                     "total_per_1000": 1000 * sum(hits[c] for c in pklint.CODES) / words,
                     "example": {c: examples[c][0][:200] for c in examples if c != "B8"}})
    out = {"rows": rows}
    dump("p5_corpus.json", out)
    return out


def precision():
    """Hand-rated random sample of 60 hits in the legal acts (one rater): share of valid hits, Wilson interval."""
    rows = read_csv("precision_sample.csv")
    n, k, z = len(rows), sum(int(r["valid"]) for r in rows), 1.96
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"n": n, "valid": k, "precision": p, "lo": centre - half, "hi": centre + half}


def runs():
    """Runs of the probe, read from the logs kept in results/logs."""
    out = []
    for path in sorted(glob.glob(os.path.join(RES, "logs", "probe-*.log"))):
        with open(path, encoding="utf-8") as fh:
            for m in re.finditer(r"FINISHED (\w+) (\S+): (\d+) new calls in ([\d.]+) min", fh.read()):
                out.append({"backend": m.group(1), "model": m.group(2), "calls": int(m.group(3)), "minutes": float(m.group(4))})
    return out


def lint_items(items):
    """How many ordinary sentences of the item set the checker flags."""
    detected = [it["id"] for it in items if pklint.lint(it["nat"])[0]]
    pk_hits = [it["id"] for it in items for v in ("pk1", "pk2") if pklint.lint(it[v])[0]]
    longest = max(pklint.n_words(s) for it in items for v in ("pk1", "pk2") for s in pklint.sentences(it[v]))
    return {"detected": detected, "undetected": [it["id"] for it in items if it["id"] not in detected],
            "pk_hits": pk_hits, "pk_longest": longest}


def reduction_check(seed=1, instances=400):
    """Random 3-SAT instances: the reduction keeps satisfiability and uses at most one negation per rule."""
    rng = np.random.default_rng(seed)
    sat = 0
    for _ in range(instances):
        n = int(rng.integers(3, 7))
        m = int(rng.integers(2, 4 * n))
        cnf = [[(f"x{v}", bool(rng.integers(2))) for v in rng.choice(np.arange(1, n + 1), size=3, replace=False)] for _ in range(m)]
        rules = M.reduce_3sat(cnf)
        assert all(M.negations(r) <= 1 for r in rules)
        a = M.brute_sat([frozenset(c) for c in cnf])
        assert a == M.brute_sat([M.clause_of(r) for r in rules])
        sat += a
    return {"instances": instances, "satisfiable": sat, "max_variables": 6}


# ---------------------------------------------------------------------------
def macros(d):
    lines = ["% generated by scripts/measure.py; do not edit"]
    for name, value in d.items():
        assert re.fullmatch(r"[A-Za-z]+", name), name
        lines.append(f"\\newcommand{{\\pk{name}}}{{{value}}}")
    with open(os.path.join(TEX, "numbers.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def table(name, rows):
    with open(os.path.join(TEX, name), "w", encoding="utf-8") as fh:
        fh.write("% generated by scripts/measure.py; do not edit\n")
        fh.write("\n".join(" & ".join(str(c) for c in r) + r" \\" for r in rows) + "\n")


def tex(s):
    return s.replace("%", r"\%").replace("&", r"\&").replace("_", r"\_").replace("^", r"\^{}").replace("#", r"\#")


SHORT = {"o200k_base": "o200k", "cl100k_base": "cl100k", "speakleash/Bielik-4.5B-v3.0-Instruct": "Bielik 4.5B",
         "speakleash/Bielik-1.5B-v3.0-Instruct": "Bielik 1.5B", "unsloth/Llama-3.2-3B-Instruct": "Llama 3.2 3B",
         "unsloth/gemma-3-4b-it": "Gemma 3 4B", "words": "słowa", "chars": "znaki"}


def model_label(m):
    name = m["model"].split("/")[-1]
    name = re.sub(r"[:\-]?(q8_0|Q8_0|instruct|it)$", "", name, flags=re.I).strip("-:")
    return {"ollama": "L", "openrouter": "O", "claude": "C"}[m["backend"]] + ": " + name


def main():
    os.makedirs(RES, exist_ok=True)
    os.makedirs(TEX, exist_ok=True)
    items, rules = read_csv("items.csv"), read_csv("rules.csv")
    c1, c2 = p1_counts(), p2_parser()
    tok = p3_tokens(items)
    tsum = p3_summary(tok)
    p4 = p4_probe(items)
    p5 = p5_corpus()
    li, red, prec = lint_items(items), reduction_check(), precision()
    dump("summary.json", {"tokens": tsum, "lint_items": li, "reduction": red, "precision": prec,
                          "rules": {"n": len(rules), "regular": sum(r["checker"] == "automat" for r in rules),
                                    "syntactic": sum(r["checker"] == "składnia" for r in rules),
                                    "semantic": sum(r["checker"] == "semantyka" for r in rules),
                                    "linted": sum(bool(r["lint"]) for r in rules)}})

    core = [r for r in rules if r["id"] not in ("F", "KW")]
    tok_units = [u for u in tok["units"] if u not in ("words", "chars")]
    main_unit = "o200k_base" if "o200k_base" in tsum else tok_units[0]
    last = c2["rows"][-1]
    row20 = next(r for r in c2["rows"] if r["words"] == 21)
    row25 = next(r for r in c2["rows"] if r["words"] == 25)
    gray_unique = len({p["key"] for p in probe.build_probes(items) if p["probe"] == "gray"})
    claude = [m for m in p4["models"] if m["backend"] == "claude"]
    mac = {
        "Items": len(items), "ItemsStd": sum(i["source"] == "standard" for i in items),
        "ItemsAuthor": sum(i["source"] == "author" for i in items),
        "ItemsRewrite": sum(i["kind"] == "restriction" for i in items),
        "ItemsConv": sum(i["kind"] == "convention" for i in items), "ItemsGap": sum(i["kind"] == "gap" for i in items),
        "Probes": len(probe.build_probes(items)), "ProbesUnique": len({p["key"] for p in probe.build_probes(items)}),
        "Rules": len(core), "RulesR": sum(r["operator"] == "R" for r in core),
        "RulesRK": sum(r["operator"] == "RK" for r in core), "RulesK": sum(r["operator"] == "K" for r in core),
        "RulesRegular": sum(r["checker"] == "automat" for r in core),
        "RulesSyntactic": sum(r["checker"] == "składnia" for r in core),
        "RulesSemantic": sum(r["checker"] == "semantyka" for r in core),
        "RulesLinted": sum(bool(r["lint"]) for r in core), "LintChecks": len(pklint.CHECKS),
        "LintDetected": len(li["detected"]), "LintUndetected": len(li["undetected"]), "LintPkLongest": li["pk_longest"],
        "CatalanNineteen": big(c1["catalan_19"]), "CatalanTwentyFour": big(c1["catalan_24"]),
        "AttachTen": big(c1["attachment"][10]["readings"]), "AttachEight": big(c1["attachment"][8]["readings"]),
        "BracketEleven": big(c1["bracketing"][-1]["functions"]), "BracketElevenAll": big(c1["bracketing"][-1]["bracketings"]),
        "ScopeSeven": big(c1["scope"][-1]["distinct"]), "ScopeSevenAll": big(c1["scope"][-1]["orders"]),
        "ScopeFour": c1["scope"][2]["distinct"], "ScopeFourAll": c1["scope"][2]["orders"],
        "OpenList": c1["open_list"]["readings"],
        "ParseExpNat": pl(c2["exp_nat"]), "ParseExpPk": pl(c2["exp_pk"]),
        "ParseWordsMax": last["words"], "ParseOpsNatMax": big(last["ops_nat"]), "ParseOpsPkMax": big(last["ops_pk"]),
        "ParseRatioMax": pl(last["ops_nat"] / last["ops_pk"], 1),
        "ParseOpsNatTwenty": big(row20["ops_nat"]), "ParseOpsPkTwenty": big(row20["ops_pk"]),
        "ParseTreesTwenty": big(row20["parses_nat"]),
        "ParseRatioTwentyFive": pl(row25["ops_nat"] / row25["ops_pk"], 1), "ParseTreesTwentyFive": big(row25["parses_nat"]),
        "ItemsPkSentences": 2 * len(items), "TokItems": tsum[main_unit]["n_items"],
        "TokMedMin": pl(100 * min(v["median"] for v in tsum.values()), 0),
        "TokMedMax": pl(100 * max(v["median"] for v in tsum.values()), 0),
        "ProbesGrayUnique": gray_unique,
        "ClaudeCalls": gray_unique * (claude[0]["samples"] if claude else 2),
        "ClaudeTokMedian": int(st.median(m["prompt_tokens_median"] for m in claude)) if claude else 0,
        "PrecN": prec["n"], "PrecValid": prec["valid"], "Prec": pl(100 * prec["precision"], 0),
        "PrecLo": pl(100 * prec["lo"], 0), "PrecHi": pl(100 * prec["hi"], 0),
        "RedInstances": red["instances"], "RedSat": red["satisfiable"], "RedUnsat": red["instances"] - red["satisfiable"],
        "TokUnit": SHORT.get(main_unit, main_unit), "TokTokenizers": len(tok_units), "TokFailed": len(tok["failed"]),
        "TokMedian": pl(100 * tsum[main_unit]["median"], 0), "TokQone": pl(100 * tsum[main_unit]["q1"], 0),
        "TokQthree": pl(100 * tsum[main_unit]["q3"], 0), "TokMean": pl(100 * tsum[main_unit]["mean"], 0),
        "TokMin": pl(100 * tsum[main_unit]["min"], 0), "TokMax": pl(100 * tsum[main_unit]["max"], 0),
        "TokCiLo": pl(100 * tsum[main_unit]["ci_lo"], 0), "TokCiHi": pl(100 * tsum[main_unit]["ci_hi"], 0),
        "TokShareLonger": pl(100 * tsum[main_unit]["share_longer"], 0),
        "TokBreakEven": pl(100 * tsum[main_unit]["median"] / (1 + tsum[main_unit]["median"]), 0),
        "TokBreakEvenMean": pl(100 * tsum[main_unit]["mean"] / (1 + tsum[main_unit]["mean"]), 0),
        "WordMedian": pl(100 * tsum["words"]["median"], 0), "WordMean": pl(100 * tsum["words"]["mean"], 0),
        "CharMedian": pl(100 * tsum["chars"]["median"], 0),
        "TokDeltaMedian": pl(tsum[main_unit]["median"]), "TokDeltaMean": pl(tsum[main_unit]["mean"]),
        "LegendTokMax": max((l.get(main_unit, 0) for l in tok["legends"]), default=0),
        "ProbeModels": len(p4["models"]),
        "ProbeModelsGraded": sum(m["graded"] for m in p4["models"]),
    }
    if p4["models"]:
        ms = p4["models"]
        ok = [m for m in ms if m["qualified"] is not False]
        local_ok = [m for m in ms if m["qualified"] is True]
        cl = [m for m in ms if m["backend"] == "claude"]
        anch = [m for m in ms if m["acc_anchor_nat"] is not None]
        e_pk = 1 - st.mean(m["acc_pk"] for m in ok) if ok else 0.0
        delta = tsum[main_unit]["median"]
        mac.update({
            "ProbeLocal": sum(m["backend"] == "ollama" for m in ms), "ProbeClaude": len(cl),
            "ProbeQualified": len(ok), "ProbeFailed": sum(m["qualified"] is False for m in ms),
            "AccPkMin": pl(100 * min(m["acc_pk"] for m in ms), 0), "AccPkMax": pl(100 * max(m["acc_pk"] for m in ms), 0),
            "AgreeItems": len(p4["agreement"]),
            "NatSplit": pl(100 * p4.get("nat_split_share", 0), 0), "PkAllCorrect": pl(100 * p4.get("pk_all_correct_share", 0), 0),
            "NatSplitCount": sum(a["nat_split"] for a in p4["agreement"]),
            "PkAllCorrectCount": sum(a["pk_correct"] for a in p4["agreement"]),
            "ErrPk": pl(100 * e_pk, 0), "BreakEvenStar": pl(100 * (1 - (1 - e_pk) / (1 + delta)), 0),
        })
        if anch:
            mac.update({"AnchorMin": pl(100 * min(min(m["acc_anchor_nat"], m["acc_anchor_pk"]) for m in anch), 0),
                        "AnchorMax": pl(100 * max(max(m["acc_anchor_nat"], m["acc_anchor_pk"]) for m in anch), 0)})
        if ok:
            mac.update({"AccPkQMin": pl(100 * min(m["acc_pk"] for m in ok), 0), "AccPkQMax": pl(100 * max(m["acc_pk"] for m in ok), 0),
                        "SteerQMin": pl(min(m["steer_mean"] for m in ok)), "SteerQMax": pl(max(m["steer_mean"] for m in ok)),
                        "UndecidedQMin": pl(100 * min(m["undecided_share"] for m in ok), 0),
                        "UndecidedQMax": pl(100 * max(m["undecided_share"] for m in ok), 0)})
            conv = [m for m in ok if "conv_acc_plain" in m]
            if conv:
                mac.update({"ConvPlainMin": pl(100 * min(m["conv_acc_plain"] for m in conv), 0),
                            "ConvPlainMax": pl(100 * max(m["conv_acc_plain"] for m in conv), 0),
                            "ConvLegendMin": pl(100 * min(m["conv_acc_legend"] for m in conv), 0),
                            "ConvLegendMax": pl(100 * max(m["conv_acc_legend"] for m in conv), 0)})
            # convention items by rule: number of PK sentences read by the key, without and with the legend
            for ids, name in ((("B2", "B2b"), "ConvOrder"), (("C1", "C1b"), "ConvOr")):
                cs = [c for m in conv for c in m["conv"] if c["id"] in ids and c["pk1L"] is not None]
                mac[name + "All"] = 2 * len(cs)
                mac[name + "Plain"] = sum(int(c["pk1"] > 0.5) + int(c["pk2"] < 0.5) for c in cs)
                mac[name + "Legend"] = sum(int(c["pk1L"] > 0.5) + int(c["pk2L"] < 0.5) for c in cs)
            mac["ProbeQualifiedConv"] = len(conv)
            for gid, name in (("G1", "GapOne"), ("G2", "GapTwo")):
                g = [x for m in ok for x in m["gap"] if x["id"] == gid]
                mac[name + "ReadingOne"] = sum(x["nat"] > 0.5 for x in g)
                mac[name + "PkOk"] = sum(x["pk1"] > 0.5 and x["pk2"] < 0.5 for x in g)
        if local_ok:
            mac.update({"HNatMin": pl(min(m["h_nat_median"] for m in local_ok)), "HNatMax": pl(max(m["h_nat_median"] for m in local_ok)),
                        "HPkMin": pl(min(m["h_pk_median"] for m in local_ok)), "HPkMax": pl(max(m["h_pk_median"] for m in local_ok)),
                        "SignWins": sum(m["sign_p"] < 0.05 and m["sign_plus"] > m["sign_minus"] for m in local_ok),
                        "ProbeLocalQualified": len(local_ok)})
        if "claude_pair" in p4:
            cp = p4["claude_pair"]
            mac.update({"ClaudeItems": cp["items"], "ClaudeSplitCount": cp["split"], "ClaudeAgreeCount": cp["agree"],
                        "ClaudeUnsureCount": cp["unsure"], "ClaudePkBothCount": cp["pk_both"]})
        if cl:
            mac.update({"AccPkClaudeMin": pl(100 * min(m["acc_pk"] for m in cl), 0),
                        "AccPkClaudeMax": pl(100 * max(m["acc_pk"] for m in cl), 0),
                        "SteerClaudeMin": pl(min(m["steer_mean"] for m in cl)), "SteerClaudeMax": pl(max(m["steer_mean"] for m in cl))})
        loc = [m for m in ms if m["backend"] == "ollama"]
        sizes = {r["model"]: float(r["parameters_billion"]) for r in read_csv("models.csv")}
        if loc:
            mac.update({"LocalParamMin": pl(min(sizes[m["model"]] for m in loc), 1),
                        "LocalParamMax": pl(max(sizes[m["model"]] for m in loc), 1)})
            mac.update({"AccPkLocalMin": pl(100 * min(m["acc_pk"] for m in loc), 0),
                        "AccPkLocalMax": pl(100 * max(m["acc_pk"] for m in loc), 0),
                        "SteerLocalMin": pl(min(m["steer_mean"] for m in loc)), "SteerLocalMax": pl(max(m["steer_mean"] for m in loc)),
                        "HNatLocalMin": pl(min(m["h_nat_median"] for m in loc)), "HNatLocalMax": pl(max(m["h_nat_median"] for m in loc)),
                        "HPkLocalMin": pl(min(m["h_pk_median"] for m in loc)), "HPkLocalMax": pl(max(m["h_pk_median"] for m in loc)),
                        "SignWinsLocal": sum(m["sign_p"] < 0.05 and m["sign_plus"] > m["sign_minus"] for m in loc)})
        if cl and cl[0]["unstable_nat"] is not None:
            mac.update({"UnstableNat": pl(100 * st.mean(m["unstable_nat"] for m in cl), 0),
                        "UnstablePk": pl(100 * st.mean(m["unstable_pk"] for m in cl), 0)})
    acts = [r for r in p5["rows"] if r["register"] == "akt prawny"]
    pks = [r for r in p5["rows"] if r["register"] != "akt prawny"]
    if acts:
        std = next((r for r in pks if r["id"] == "pk-standard"), None)
        mac["CorpusStdCfive"] = std["hits"]["C5"] if std else 0
        mac.update({"CorpusActs": len(acts), "CorpusPk": len(pks), "CorpusActWords": big(sum(r["words"] for r in acts)),
                    "CorpusActMin": pl(min(r["total_per_1000"] for r in acts), 0), "CorpusActMax": pl(max(r["total_per_1000"] for r in acts), 0),
                    "CorpusPkMin": pl(min(r["total_per_1000"] for r in pks), 1) if pks else "0",
                    "CorpusPkMax": pl(max(r["total_per_1000"] for r in pks), 1) if pks else "0",
                    "CorpusOverMin": pl(100 * min(r["share_over_25"] for r in acts), 0),
                    "CorpusOverMax": pl(100 * max(r["share_over_25"] for r in acts), 0)})
    macros(mac)

    table("table_counts.tex", [[r["k"], big(r["readings"]), big(b["functions"]) if b else "", big(s["distinct"]) if s else ""]
                               for r, b, s in zip(c1["attachment"][1:8], c1["bracketing"][:7], c1["scope"] + [None] * 2)])
    table("table_tokens.tex", [[SHORT.get(u, tex(u)), pl(100 * tsum[u]["median"], 0), pl(100 * tsum[u]["q1"], 0),
                                pl(100 * tsum[u]["q3"], 0), pl(100 * tsum[u]["min"], 0), pl(100 * tsum[u]["max"], 0),
                                pl(100 * tsum[u]["share_longer"], 0)] for u in tok["units"]])
    table("table_items.tex", [[it["id"], it["rule"].replace("gap", "luka"), {"restriction": "O", "convention": "K", "gap": "L"}[it["kind"]],
                               "S" if it["source"] == "standard" else "A", "„" + tex(it["nat"]) + "”",
                               tex(it["r1"]) + "; " + tex(it["r2"])] for it in items])
    table("table_probe.tex", [[tex(model_label(m)), m["n_rewrite"],
                               pl(m["h_nat_median"]) if m["graded"] else "--", pl(m["h_pk_median"]) if m["graded"] else "--",
                               f"{m['sign_plus']}:{m['sign_minus']}" if m["graded"] else "--",
                               (pl(m["sign_p"], 3) if m["sign_p"] >= 0.001 else "<0,001") if m["graded"] else "--",
                               pl(m["steer_mean"]), pl(100 * m["acc_pk"], 0),
                               pl(100 * m["acc_anchor_nat"], 0) if m["acc_anchor_nat"] is not None else "--",
                               pl(100 * m["acc_anchor_pk"], 0) if m["acc_anchor_pk"] is not None else "--"] for m in p4["models"]])
    table("table_conv.tex", [[tex(model_label(m)), pl(100 * m["conv_acc_plain"], 0), pl(100 * m["conv_acc_legend"], 0),
                              pl(m["conv_steer_plain"]), pl(m["conv_steer_legend"])] for m in p4["models"] if "conv_acc_plain" in m])
    table("table_runs.tex", [[{"ollama": "lokalny", "claude": "Claude", "openrouter": "OpenRouter"}[r["backend"]],
                              "\\texttt{" + tex(r["model"]) + "}", r["calls"], pl(r["minutes"], 1)] for r in runs()]
          or [["--", "--", "--", "--"]])
    table("table_corpus.tex", [[tex(r["title"].split(" (")[0]), big(r["words"]), pl(r["sentence_median"], 0),
                                pl(100 * r["share_over_25"], 0), pl(r["total_per_1000"], 1), pl(r["per_1000"]["B1s"], 1)]
                               for r in p5["rows"]])
    print(f"P1 ok; P2 exponents nat {c2['exp_nat']:.2f} pk {c2['exp_pk']:.2f}; P3 units {tok['units']} failed {len(tok['failed'])}; "
          f"P4 models {len(p4['models'])}; P5 texts {len(p5['rows'])}; lint detects {len(li['detected'])}/{len(items)}; "
          f"reduction {red['instances']} instances ok")


if __name__ == "__main__":
    main()
