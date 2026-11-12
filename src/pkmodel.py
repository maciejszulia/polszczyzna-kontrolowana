"""Set-theoretic model of controlled Polish (PK): readings, counting, parsing, Horn clauses.

Four independent parts, each small:
  1. readings as sets of worlds and the gray zone,
  2. exact counts of readings for the constructions that PK restricts (measurement P1),
  3. an Earley recognizer with an operation counter and a parse counter (measurement P2),
  4. PK0 conditionals as clauses: Horn test, linear-time Horn satisfiability, reduction from 3-SAT.

Run `python -m src.pkmodel` for the self-check.
"""

from __future__ import annotations

import itertools
import math
from collections import deque
from functools import lru_cache

# ---------------------------------------------------------------------------
# 1. Readings and the gray zone
# ---------------------------------------------------------------------------


def gray_zone(readings):
    """Worlds on which the readings disagree: union minus intersection."""
    readings = [frozenset(r) for r in readings]
    return frozenset.union(*readings) - frozenset.intersection(*readings)


def bits(n_readings):
    """Information missing from a sentence with n equally likely readings."""
    return math.log2(n_readings)


# ---------------------------------------------------------------------------
# 2. Exact counts of readings
# ---------------------------------------------------------------------------


def catalan(n):
    return math.comb(2 * n, n) // (n + 1)


def bracketings(ops):
    """Truth tables reachable by bracketing x0 op0 x1 op1 ... ; ops are 'and' / 'or'.

    Returns (number of bracketings, number of distinct Boolean functions).
    A truth table is an integer with 2**n bits.
    """
    n = len(ops) + 1
    rows = 1 << n
    atom = [sum(1 << r for r in range(rows) if r >> i & 1) for i in range(n)]

    @lru_cache(maxsize=None)
    def tables(i, j):
        if i == j:
            return frozenset([atom[i]])
        out = set()
        for k in range(i, j):
            for a in tables(i, k):
                for b in tables(k + 1, j):
                    out.add(a & b if ops[k] == "and" else a | b)
        return frozenset(out)

    return catalan(n - 1), len(tables(0, n - 1))


def alternating(n):
    """Operators of the chain 'A i B lub C i D ...' with n operands."""
    return tuple("and" if k % 2 == 0 else "or" for k in range(n - 1))


def scope_orders(quants):
    """Scope readings of a sentence with the quantifiers `quants` (a string over 'A', 'E').

    Returns (number of scope orders, number of logically distinct ones). Two orders that differ
    by swapping adjacent quantifiers of one kind are equivalent, so the canonical form sorts
    every maximal block. `scope_orders_semantic` confirms that canonical forms differ in meaning.
    """
    n = len(quants)
    canon = set()
    for perm in itertools.permutations(range(n)):
        blocks, cur = [], [perm[0]]
        for v in perm[1:]:
            if quants[v] == quants[cur[-1]]:
                cur.append(v)
            else:
                blocks.append(tuple(sorted(cur)))
                cur = [v]
        blocks.append(tuple(sorted(cur)))
        canon.add(tuple(blocks))
    return math.factorial(n), len(canon)


def scope_orders_semantic(quants):
    """Distinct truth-value vectors of the scope orders over every n-ary relation on a 2-element domain."""
    n = len(quants)
    cells = list(itertools.product((0, 1), repeat=n))
    index = {c: i for i, c in enumerate(cells)}

    def holds(order, rel):
        def go(depth, env):
            if depth == n:
                return rel >> index[tuple(env[v] for v in range(n))] & 1 == 1
            v = order[depth]
            results = (go(depth + 1, {**env, v: d}) for d in (0, 1))
            return all(results) if quants[v] == "A" else any(results)
        return go(0, {})

    vectors = set()
    for order in itertools.permutations(range(n)):
        vectors.add(tuple(holds(order, rel) for rel in range(1 << len(cells))))
    return len(vectors)


def pronoun_readings(pronouns, candidates):
    return candidates ** pronouns


def open_list_readings(universe, listed):
    """A list closed with 'itp.' denotes some superset of the listed items."""
    return 2 ** (universe - listed)


# ---------------------------------------------------------------------------
# 3. Earley recognizer with counters
# ---------------------------------------------------------------------------

# Terminals are word classes: n (noun), v (verb), p (preposition).
GRAMMAR_NAT = {            # a prepositional phrase attaches to the verb or to any earlier noun
    "S": [("NP", "VP")],
    "VP": [("v", "NP"), ("VP", "PP")],
    "NP": [("n",), ("NP", "PP")],
    "PP": [("p", "NP")],
}
GRAMMAR_PK = {             # rule B6: a modifier stands directly at the word it modifies
    "S": [("NP", "VP")],
    "VP": [("v", "NP")],
    "NP": [("n",), ("n", "PP")],
    "PP": [("p", "NP")],
}


def sentence(k):
    """'n v n (p n)^k': subject, verb, object and k prepositional phrases."""
    return ["n", "v", "n"] + ["p", "n"] * k


def earley(grammar, tokens, start="S"):
    """Earley recognition without Leo's optimisation.

    Returns (accepted, operations): an operation is one attempt to enter a state into the chart
    (prediction, scan or completion step), the usual unit of Earley's running time.
    """
    n = len(tokens)
    chart = [set() for _ in range(n + 1)]
    order = [[] for _ in range(n + 1)]
    waiting = [{} for _ in range(n + 1)]       # waiting[pos][symbol]: states at pos that expect symbol
    ops = 0

    def add(pos, state):
        nonlocal ops
        ops += 1
        if state not in chart[pos]:
            chart[pos].add(state)
            order[pos].append(state)
            lhs, rhs, dot, origin = state
            if dot < len(rhs):
                waiting[pos].setdefault(rhs[dot], []).append(state)

    for rhs in grammar[start]:
        add(0, (start, rhs, 0, 0))
    for pos in range(n + 1):
        i = 0
        while i < len(order[pos]):
            lhs, rhs, dot, origin = order[pos][i]
            i += 1
            if dot < len(rhs):
                sym = rhs[dot]
                if sym in grammar:                              # predict
                    for r in grammar[sym]:
                        add(pos, (sym, r, 0, pos))
                elif pos < n and tokens[pos] == sym:            # scan
                    add(pos + 1, (lhs, rhs, dot + 1, origin))
            else:                                               # complete
                for l2, r2, d2, o2 in list(waiting[origin].get(lhs, ())):
                    add(pos, (l2, r2, d2 + 1, o2))
    accepted = any(l == start and d == len(r) and o == 0 for l, r, d, o in chart[n])
    return accepted, ops


def count_parses(grammar, tokens, start="S"):
    """Number of parse trees (grammar without empty and without unit rules on nonterminals)."""
    tokens = tuple(tokens)

    @lru_cache(maxsize=None)
    def sym(a, i, j):
        if a not in grammar:
            return 1 if j == i + 1 and tokens[i] == a else 0
        return sum(seq(rhs, i, j) for rhs in grammar[a])

    @lru_cache(maxsize=None)
    def seq(rhs, i, j):
        if len(rhs) == 1:
            return sym(rhs[0], i, j)
        return sum(sym(rhs[0], i, k) * seq(rhs[1:], k, j) for k in range(i + 1, j - len(rhs) + 2))

    return sym(start, 0, len(tokens))


# ---------------------------------------------------------------------------
# 4. PK0 conditionals, Horn clauses, reduction from 3-SAT
# ---------------------------------------------------------------------------
# A literal is (atom, positive). A PK0 rule is (antecedent, consequent):
#   antecedent  list of literals joined by "i" (rule C2: no "lub" beside "i"),
#   consequent  an atom, or None for a conflict (MUSI and NIE WOLNO for one action).
# "Jezeli a i nie b, to c."  ->  (not a) or b or c.


def clause_of(rule):
    antecedent, consequent = rule
    lits = {(atom, not positive) for atom, positive in antecedent}
    if consequent is not None:
        lits.add((consequent, True))
    return frozenset(lits)


def negations(rule):
    return sum(1 for _, positive in rule[0] if not positive)


def is_horn(clauses):
    return all(sum(1 for _, positive in c if positive) <= 1 for c in clauses)


def horn_sat(clauses):
    """Satisfiability of Horn clauses by forward chaining; time linear in the total size.

    Returns (satisfiable, atoms true in the least model).
    """
    clauses = list(clauses)
    assert is_horn(clauses)
    head, missing, watch = [], [], {}
    queue, true = deque(), set()
    for idx, c in enumerate(clauses):
        body = [a for a, positive in c if not positive]
        heads = [a for a, positive in c if positive]
        head.append(heads[0] if heads else None)
        missing.append(len(body))
        for a in body:
            watch.setdefault(a, []).append(idx)
        if not body:
            queue.append(idx)
    while queue:
        idx = queue.popleft()
        h = head[idx]
        if h is None:
            return False, true
        if h in true:
            continue
        true.add(h)
        for j in watch.get(h, ()):
            missing[j] -= 1
            if missing[j] == 0:
                queue.append(j)
    return True, true


def brute_sat(clauses):
    clauses = list(clauses)
    atoms = sorted({a for c in clauses for a, _ in c}, key=str)
    for values in itertools.product((False, True), repeat=len(atoms)):
        val = dict(zip(atoms, values))
        if all(any(val[a] == positive for a, positive in c) for c in clauses):
            return True
    return False


def reduce_3sat(cnf):
    """3-SAT instance -> PK0 rules, each with a conjunctive antecedent and at most one negation.

    cnf: list of clauses, a clause is a list of 3 literals (variable, positive).
    Clause by number of positive literals:
      0  (x and y and z) -> conflict
      1  (x and y) -> z
      2  (x and not y) -> z
      3  (not x) -> u ;  (u and not y) -> z      with a fresh atom u
    """
    rules = []
    for idx, clause in enumerate(cnf):
        pos = [v for v, positive in clause if positive]
        neg = [v for v, positive in clause if not positive]
        if len(pos) == 0:
            rules.append(([(v, True) for v in neg], None))
        elif len(pos) == 1:
            rules.append(([(v, True) for v in neg], pos[0]))
        elif len(pos) == 2:
            rules.append(([(v, True) for v in neg] + [(pos[0], False)], pos[1]))
        else:
            u = f"u{idx}"
            rules.append(([(pos[0], False)], u))
            rules.append(([(u, True), (pos[1], False)], pos[2]))
    return rules


def selfcheck():
    assert gray_zone([{1, 2}, {1, 2, 3}]) == {3}
    assert [catalan(n) for n in range(6)] == [1, 1, 2, 5, 14, 42]
    assert bracketings(("and", "or")) == (2, 2)                   # "A i B lub C"
    assert bracketings(("and", "and", "and")) == (5, 1)           # associativity: one function
    assert scope_orders("AE") == (2, 2) and scope_orders("AA") == (2, 1)
    for q in ("AE", "AEA", "AEE", "EAE"):                         # "AEAE" takes 30 s: tests/ only
        assert scope_orders(q)[1] == scope_orders_semantic(q), q
    for k in range(6):
        toks = sentence(k)
        assert count_parses(GRAMMAR_NAT, toks) == catalan(k + 1)
        assert count_parses(GRAMMAR_PK, toks) == 1
        assert earley(GRAMMAR_NAT, toks)[0] and earley(GRAMMAR_PK, toks)[0]
    assert not earley(GRAMMAR_PK, ["n", "n"])[0]
    horn = [clause_of(([("a", True), ("b", True)], "c")), clause_of(([], "a")), clause_of(([], "b"))]
    assert horn_sat(horn) == (True, {"a", "b", "c"})
    assert horn_sat(horn + [clause_of(([("c", True)], None))])[0] is False
    return "ok"


if __name__ == "__main__":
    print(selfcheck())
