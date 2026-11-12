"""Checks of the model, the data files and the link between the text and the measured numbers."""

import csv
import glob
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from src import pklint, pkmodel as M  # noqa: E402
import probe  # noqa: E402


def rows(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_selfchecks():
    assert M.selfcheck() == "ok"
    assert pklint.selfcheck() == "ok"


def test_scope_orders_agree_with_semantics_for_four_quantifiers():
    assert M.scope_orders("AEAE")[1] == M.scope_orders_semantic("AEAE") == 14


def test_reduction_keeps_satisfiability():
    import random
    rng = random.Random(7)
    for _ in range(150):
        n = rng.randint(3, 6)
        cnf = [[(f"x{v}", rng.random() < 0.5) for v in rng.sample(range(n), 3)] for _ in range(rng.randint(2, 4 * n))]
        rules = M.reduce_3sat(cnf)
        assert all(M.negations(r) <= 1 for r in rules)
        assert M.brute_sat([frozenset(c) for c in cnf]) == M.brute_sat([M.clause_of(r) for r in rules])


def test_horn_sat_agrees_with_enumeration():
    import random
    rng = random.Random(3)
    for _ in range(200):
        atoms = [f"a{i}" for i in range(rng.randint(2, 6))]
        rules = [(([(a, True) for a in rng.sample(atoms, rng.randint(0, min(3, len(atoms))))]),
                  rng.choice(atoms + [None])) for _ in range(rng.randint(1, 8))]
        clauses = [M.clause_of(r) for r in rules]
        assert M.is_horn(clauses)
        assert M.horn_sat(clauses)[0] == M.brute_sat(clauses)


def test_items_are_consistent():
    items = rows("items.csv")
    assert len(items) == 44 and len({i["id"] for i in items}) == 44
    assert sum(i["source"] == "standard" for i in items) >= 15
    for it in items:
        assert all(it[k] for k in ("nat", "r1", "r2", "pk1", "pk2", "probe_gray", "probe_yes", "probe_no")), it["id"]
        assert it["gray1"] in ("Tak", "Nie") and it["pk1"] != it["pk2"], it["id"]
        assert (it["kind"] == "convention") == bool(it["legend"]), it["id"]
        for v in ("pk1", "pk2"):
            assert not pklint.lint(it[v])[0], (it["id"], v)          # every PK sentence passes the checker
            assert max(pklint.n_words(s) for s in pklint.sentences(it[v])) <= 25


def test_rules_table():
    rules = rows("rules.csv")
    core = [r for r in rules if r["id"] not in ("F", "KW")]
    assert len(core) == 32 and len(rules) == 34
    assert all(r["operator"] in ("R", "K", "RK") and r["checker"] in ("automat", "składnia", "semantyka") for r in rules)
    assert all(not r["lint"] or r["lint"] in pklint.CODES for r in rules)


def test_probes():
    ps = probe.build_probes(rows("items.csv"))
    assert len(ps) == 420
    assert probe.side(" Tak") == "yes" and probe.side("Nie.") == "no" and probe.side("To") is None
    p, mass, _ = probe.p_yes_from_logprobs([[("Tak", -0.2231), ("Nie", -1.6094)]])
    assert abs(p - 0.8) < 1e-3 and abs(mass - 1.0) < 1e-3


def test_every_number_in_the_text_is_generated():
    with open(os.path.join(ROOT, "paper", "data", "numbers.tex"), encoding="utf-8") as fh:
        defined = set(re.findall(r"\\newcommand\{\\(pk[A-Za-z]+)\}", fh.read()))
    used = set()
    for path in glob.glob(os.path.join(ROOT, "paper", "*.tex")):
        with open(path, encoding="utf-8") as fh:
            used |= set(re.findall(r"\\(pk[A-Z][A-Za-z]*)", fh.read()))
    assert used <= defined, sorted(used - defined)


def test_every_reference_is_cited():
    text = ""
    for path in glob.glob(os.path.join(ROOT, "paper", "*.tex")):
        with open(path, encoding="utf-8") as fh:
            text += fh.read()
    keys = set(re.findall(r"\\bibitem\{([^}]+)\}", text))
    cited = {k.strip() for group in re.findall(r"\\cite\{([^}]+)\}", text) for k in group.split(",")}
    assert keys and keys <= cited, sorted(keys - cited)
    assert cited <= keys, sorted(cited - keys)
