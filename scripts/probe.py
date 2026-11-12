"""Gray-zone probe (measurement P4): does a model read a PK sentence more decisively?

Usage:
    python scripts/probe.py ollama MODEL [--limit N]
    python scripts/probe.py openrouter MODEL          (needs OPENROUTER_API_KEY)
    python scripts/probe.py claude MODEL [--samples N] [--subset gray]

Every probe is one yes/no question about a text in a situation. The situation
lies in the gray zone (the two readings disagree) or is an anchor (the two
readings agree). Backends with log-probabilities give P(Tak) from the first
answer token; the claude backend counts answers over N samples.
Raw answers go to results/probe_<backend>_<model>.jsonl; reruns skip what is there.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SYSTEM = "Odpowiadasz na pytania o znaczenie tekstu. Odpowiedz jednym słowem: Tak albo Nie."
TAIL = "Odpowiedz jednym słowem: Tak albo Nie."
OPPOSITE = {"Tak": "Nie", "Nie": "Tak"}


def load_items(path=os.path.join(ROOT, "data", "items.csv")):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def user_prompt(text, legend, question):
    lines = [f"Tekst: „{text}”"]
    if legend:
        lines.append(legend)
    lines += [question, TAIL]
    return "\n".join(lines)


def build_probes(items):
    """All probes of the study; `key` identifies a prompt, so equal prompts are asked once."""
    out = []
    for it in items:
        variants = [("nat", it["nat"], ""), ("pk1", it["pk1"], ""), ("pk2", it["pk2"], "")]
        if it["legend"]:
            variants += [("pk1L", it["pk1"], it["legend"]), ("pk2L", it["pk2"], it["legend"])]
        for vname, text, legend in variants:
            for probe in ("gray", "yes", "no"):
                if probe == "yes":
                    expect = "Tak"
                elif probe == "no":
                    expect = "Nie"
                elif vname == "nat":
                    expect = ""                       # the quantity under study
                else:
                    expect = it["gray1"] if vname.startswith("pk1") else OPPOSITE[it["gray1"]]
                prompt = user_prompt(text, legend, it["probe_" + probe])
                out.append({
                    "pid": f"{it['id']}:{vname}:{probe}", "item": it["id"], "variant": vname,
                    "probe": probe, "expect": expect, "prompt": prompt,
                    "key": hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12],
                })
    return out


def side(token):
    """'yes' / 'no' / None for one vocabulary token (a token may be a prefix of the word)."""
    t = re.sub(r"^[^a-ząćęłńóśźż]+", "", token.strip().lower())
    t = re.sub(r"[^a-ząćęłńóśźż]+$", "", t)
    if not t:
        return None
    if "tak".startswith(t) or t.startswith("tak"):
        return "yes"
    if "nie".startswith(t) or t.startswith("nie"):
        return "no"
    return None


def p_yes_from_logprobs(positions):
    """positions: list over answer tokens of [(token, logprob), ...] (top alternatives).

    Returns (p_yes, mass, top) from the first position where Tak/Nie carry at least 5 % of the mass.
    """
    for alts in positions:
        yes = sum(math.exp(lp) for tok, lp in alts if side(tok) == "yes")
        no = sum(math.exp(lp) for tok, lp in alts if side(tok) == "no")
        if yes + no >= 0.05:
            top = sorted(((tok, round(math.exp(lp), 4)) for tok, lp in alts), key=lambda x: -x[1])[:6]
            return yes / (yes + no), yes + no, top
    return None, 0.0, []


def answer_side(text):
    """1.0 for 'Tak', 0.0 for 'Nie'. A model that reasons aloud first gives the verdict as its last word."""
    t = text.strip().lower()
    m = re.search(r"\b(tak|nie)\W*$", t) or re.match(r"\W*(tak|nie)\b", t)     # the last word wins
    return {"tak": 1.0, "nie": 0.0}[m.group(1)] if m else None


def http_json(url, payload, headers=None, timeout=300, retries=4):
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", "replace")[:300]
            if err.code in (408, 429, 500, 502, 503, 529) and attempt + 1 < retries:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {err.code}: {body}") from err
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt + 1 < retries:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"network: {err}") from err


def ask_ollama(model, prompt):
    r = http_json("http://127.0.0.1:11434/api/chat", {
        "model": model, "stream": False, "logprobs": True, "top_logprobs": 20, "keep_alive": "10m",
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        "options": {"temperature": 0, "seed": 1, "num_predict": 4, "num_ctx": 2048},
    })
    positions = [[(a["token"], a["logprob"]) for a in tok.get("top_logprobs", [])] for tok in r.get("logprobs") or []]
    p, mass, top = p_yes_from_logprobs(positions)
    text = r.get("message", {}).get("content", "")
    return {"p_yes": p, "mass": round(mass, 4), "top": top, "answer": text.strip()[:40],
            "prompt_tokens": r.get("prompt_eval_count"), "n": 1}


def ask_openrouter(model, prompt):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    r = http_json("https://openrouter.ai/api/v1/chat/completions", {
        "model": model, "temperature": 0, "max_tokens": 4, "logprobs": True, "top_logprobs": 20,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    }, headers={"Authorization": f"Bearer {key}"}, timeout=120)
    if "error" in r:
        raise RuntimeError(str(r["error"])[:300])
    ch = r["choices"][0]
    content = (ch.get("logprobs") or {}).get("content") or []
    positions = [[(a["token"], a["logprob"]) for a in tok.get("top_logprobs", [])] for tok in content]
    p, mass, top = p_yes_from_logprobs(positions)
    text = ch.get("message", {}).get("content") or ""
    return {"p_yes": p, "mass": round(mass, 4), "top": top, "answer": text.strip()[:40],
            "prompt_tokens": (r.get("usage") or {}).get("prompt_tokens"), "n": 1}


def ask_claude(model, prompt, samples):
    """No log-probabilities: P(Tak) is the share of 'Tak' answers over `samples` calls."""
    votes, usage, texts = [], {}, []
    with tempfile.TemporaryDirectory() as empty:           # no project files, no CLAUDE.md of a repo
        for _ in range(samples):
            for attempt in range(4):                       # the CLI vanishes for a moment while it updates itself
                try:
                    cp = subprocess.run(
                        ["claude", "-p", prompt, "--model", model, "--system-prompt", SYSTEM,
                         "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
                         "--tools", "", "--no-session-persistence", "--output-format", "json"],
                        capture_output=True, text=True, timeout=180, cwd=empty)
                    if cp.returncode == 0:
                        break
                    error = f"claude rc={cp.returncode}: {(cp.stderr or cp.stdout).strip()[:300]}"
                except (FileNotFoundError, subprocess.TimeoutExpired) as err:
                    error = f"claude: {err}"
                if attempt == 3:
                    raise RuntimeError(error)
                time.sleep(20)
            r = json.loads(cp.stdout)
            texts.append(" ".join(str(r.get("result", "")).split())[:400])
            v = answer_side(texts[-1])
            if v is not None:
                votes.append(v)
            usage = r.get("usage") or usage
    inp = sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return {"p_yes": (sum(votes) / len(votes)) if votes else None, "mass": len(votes) / samples, "top": [],
            "answer": " | ".join(t if len(t) <= 40 else "… " + t[-120:] for t in texts), "prompt_tokens": inp or None, "n": samples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("backend", choices=["ollama", "openrouter", "claude"])
    ap.add_argument("model")
    ap.add_argument("--samples", type=int, default=1, help="claude backend: calls per probe")
    ap.add_argument("--subset", choices=["all", "gray", "standard"], default="all")
    ap.add_argument("--limit", type=int, default=0, help="stop after N new calls (pilot)")
    args = ap.parse_args()

    items = load_items()
    probes = build_probes(items)
    if args.subset == "gray":
        probes = [p for p in probes if p["probe"] == "gray"]
    elif args.subset == "standard":
        std = {it["id"] for it in items if it["source"] == "standard"}
        probes = [p for p in probes if p["item"] in std]

    slug = re.sub(r"[^A-Za-z0-9.]+", "-", args.model).strip("-").lower()
    path = os.path.join(ROOT, "results", f"probe_{args.backend}_{slug}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            done = {json.loads(line)["key"] for line in fh if line.strip()}
    todo, seen = [], set(done)
    for p in probes:                                       # equal prompts are asked once
        if p["key"] not in seen:
            seen.add(p["key"])
            todo.append(p)
    print(f"{args.backend} {args.model}: {len(probes)} probes, {len(done)} cached, {len(todo)} to ask", flush=True)

    ask = {"ollama": ask_ollama, "openrouter": ask_openrouter}.get(args.backend)
    t0, new = time.time(), 0
    with open(path, "a", encoding="utf-8") as fh:
        for p in todo:
            try:
                res = ask(args.model, p["prompt"]) if ask else ask_claude(args.model, p["prompt"], args.samples)
            except RuntimeError as err:
                print(f"FAILED {p['pid']}: {err}", flush=True)
                return 1
            fh.write(json.dumps({"key": p["key"], "backend": args.backend, "model": args.model, **res},
                                ensure_ascii=False) + "\n")
            fh.flush()
            new += 1
            if new % 25 == 0:
                rate = (time.time() - t0) / new
                print(f"progress {new}/{len(todo)}  {rate:.1f} s/call  eta {rate * (len(todo) - new) / 60:.0f} min", flush=True)
            if args.limit and new >= args.limit:
                break
    print(f"FINISHED {args.backend} {args.model}: {new} new calls in {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
