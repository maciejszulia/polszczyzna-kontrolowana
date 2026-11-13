"""Token trial: does an order in PK cost fewer tokens than the same order in ordinary Polish?

The model plays a worker. It gets the text of an order, a situation and a question
(the gray-zone question of measurement P4). It answers Tak or Nie, or it asks one
question back when the text does not settle the case. Each of the 44 items is asked
in three texts: ordinary Polish (nat) and the two PK texts (pk1, pk2), one for each
reading the author may intend. A PK text carries its legend where the item has one.

Usage:  python scripts/token_trial.py MODEL [--samples N] [--workers K] [--limit N]
Raw answers go to results/trial_<model>.jsonl; reruns skip what is there.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from scripts.probe import load_items  # noqa: E402

SYSTEM = ("Wykonujesz polecenia z tekstu. Dostajesz tekst, opis sytuacji i pytanie. "
          "Jeżeli tekst rozstrzyga pytanie, to odpowiedz jednym słowem: Tak albo Nie. "
          "Jeżeli tekst nie rozstrzyga pytania, to napisz słowo PYTANIE i zadaj dokładnie "
          "1 pytanie do autora tekstu.")


def prompts(items):
    """(pid, prompt) for every item and text variant."""
    for it in items:
        for variant, text, legend in (("nat", it["nat"], ""), ("pk1", it["pk1"], it["legend"]),
                                      ("pk2", it["pk2"], it["legend"])):
            lines = [f"Tekst: „{text}”"] + ([legend] if legend else []) + [it["probe_gray"]]
            yield f"{it['id']}:{variant}", "\n".join(lines)


def ask(model, prompt):
    """One isolated call of the Claude CLI: no project files, no settings, no tools."""
    with tempfile.TemporaryDirectory() as empty:
        for attempt in range(4):
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
    u = r.get("usage") or {}
    return {"answer": " ".join(str(r.get("result", "")).split())[:500],
            "in_tokens": sum(int(u.get(k) or 0) for k in
                             ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
            "out_tokens": int(u.get("output_tokens") or 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0, help="first N items only (smoke test)")
    args = ap.parse_args()
    path = os.path.join(ROOT, "results", f"trial_{args.model}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            done = {(r["pid"], r["sample"]) for r in map(json.loads, fh)}
    items = load_items()
    todo = [(pid, prompt, s) for pid, prompt in prompts(items[:args.limit] if args.limit else items)
            for s in range(args.samples) if (pid, s) not in done]
    print(f"{args.model}: {len(todo)} calls to make, {len(done)} already in {os.path.basename(path)}", flush=True)

    def work(job):
        pid, prompt, s = job
        return {"pid": pid, "sample": s, "model": args.model, **ask(args.model, prompt)}

    with ThreadPoolExecutor(args.workers) as pool, open(path, "a", encoding="utf-8") as fh:
        for n, rec in enumerate(pool.map(work, todo), 1):
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if n % 20 == 0:
                print(f"  {n} of {len(todo)}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
