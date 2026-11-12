"""Checker of the mechanically decidable rules of PK 0.1.

Every check is a regular constraint over the words of one sentence, so a finite automaton
decides it in linear time. The checks are approximate: they flag candidates, a human confirms.
Rules that need syntax or meaning (B2, B4, B6, A1, the two-readings test) are out of reach here.

Usage:  python -m src.pklint [--tex] FILE...      exit code 1 when a violation is found
"""

from __future__ import annotations

import re
import sys
from collections import Counter

ADJ = r"(?:y|a|e|ego|ej|emu|ym|ą|ych|ymi)"          # endings of a hard-stem adjective
ADJK = r"(?:i|a|ie|iego|iej|iemu|im|ą|ich|imi)"      # endings after k/g
NOT_PARTICIPLE = {"tysiąc", "miesiąc", "zając", "brzdąc", "pierwszy", "ciekawszy", "łaskawszy", "żwawszy"}
ABBREVIATIONS = ("godz", "np", "r", "nr", "tys", "mln", "mld", "ok", "art", "ust", "pkt", "poz", "dz", "u",
                 "św", "m", "in", "itp", "itd", "tzw", "tj", "tzn", "zob", "por", "ww", "ang", "łac", "min",
                 "maks", "s", "t", "red", "wyd", "prof", "dr", "mgr", "inż", "al", "ul", "pl", "os", "str",
                 "ds", "wg", "ryc", "rys", "tab", "sek", "rozdz", "lit", "zm", "j")


def _rx(pattern):
    return re.compile(pattern, re.IGNORECASE)


def _count(pattern):
    rx = _rx(pattern)
    return lambda s: len(rx.findall(s))


def _participles(s):
    """Adverbial participles; comparatives such as 'nowszy', 'pierwszy', 'najciekawszy' are adjectives."""
    hits = 0
    for w in re.findall(r"\b\w{3,}(?:ąc|wszy|łszy)\b", s.lower()):
        adjective = (w.endswith("owszy") and not w.endswith("owawszy")) or w.startswith("naj") or w in NOT_PARTICIPLE
        hits += 0 if adjective else 1
    return hits


def _approx(s):
    return 0 if "±" in s else len(_rx(r"\b(?:około|mniej więcej|prawie)\b").findall(s))


def _bounds(s):
    """Boundary words before a number and ranges of quantities written with a dash.

    Allowed by PK: 'od A do B włącznie' (rule D2) and 'z A do B' for a change of a value (rule D5).
    Not counted: dates, numbers of articles and standards, 'pasuje do 2 słów'.
    """
    s = re.sub(r"\d{4}-\d{2}-\d{2}", "DATA", s)
    s = re.sub(r"(?:art\.|§|ust\.|pkt|poz\.|nr|str\.|s\.|ISO|IEC|PN|EN|RFC)\s?\d+[a-z]?\s?[–—-]\s?\d+", "NUMERY", s, flags=re.IGNORECASE)
    hits = len(re.findall(r"(?<![\w/.-])\d+\s?[–—-]\s?\d+\s+(?=[a-ząćęłńóśźż%°])", s))
    if re.search(r"\bwłącznie\b", s, re.IGNORECASE):
        return hits
    s = re.sub(r"\bz\s+\d[\d ,]*\s*\S{0,4}\s+do\s+\d", "ZMIANA", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:pasuje|należy|się)\s+do\s+\d", "X", s, flags=re.IGNORECASE)
    return hits + len(_rx(r"\b(?:do|powyżej|poniżej|ponad|między|pomiędzy|minimum|maksimum)\s+(?:dnia\s+)?\d").findall(s))


def _decimal_point(s):
    s = re.sub(r"(?i)\b(?:PK|wersj\w+|Issue|v|tez\w+)\s*\d+\.\d+", "", s)    # version and thesis numbers
    return len(re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", s))


KW_RX = re.compile(r"\b(?:[Mm]usi|[Mm]uszą|[Pp]owin(?:ien|na|no|ni|ny)|[Mm]oże|[Mm]ogą)\b")
VAGUE = (r"\b(?:odpowiedni(?:a|e|ego|ej|emu|m|ą|ch|mi|o)?|właściw(?:" + ADJ[3:-1] + r"|ie)|stosown(?:" + ADJ[3:-1]
         + r"|ie)|należyt(?:" + ADJ[3:-1] + r"|ie)|niezwłocznie|wkrótce|szybko|na bieżąco|regularnie|okresowo"
         r"|często|rzadko|zwykle|kilk[au]|kilkoma|kilkanaście|kilkunastu|parę|wiele|wielu|większoś[ćc]i?"
         r"|duż" + ADJ + r"|mał" + ADJ + r"|wysok" + ADJK + r"|nisk" + ADJK + r"|dług" + ADJK + r"|krótk" + ADJK + r")\b")

# code, rule of PK, what the check finds, function(sentence) -> number of hits
CHECKS = [
    ("A2", "A2", "ilość nieokreślona: dowolny, niektóre, jakiś", _count(r"\b(?:dowoln\w+|niektór\w+|jak(?:iś|aś|ieś|iegoś|iejś|imś|ąś))\b")),
    ("A3", "A3", "zaimek zamiast nazwy", _count(
        r"\b(?:on|ona|ono|oni|one|jego|jej|jemu|ich|go|mu|im|nim|nią|niego|niej|nich|nimi"
        r"|swój|swoja|swoje|swojego|swojej|swojemu|swoim|swoją|swoich|swoimi)\b")),
    ("A4", "A4", "słowo „ostatni”: 2 znaczenia", _count(r"\bostatni\w*\b")),
    ("A5", "A5", "słowo nieostre", lambda s: len(_rx(VAGUE).findall(s)) + _approx(s)),
    ("A6", "A6", "lista otwarta: itp., itd., m.in.", _count(r"\b(?:itp|itd)\b|\bm\.\s?in\b|\bi inn[eiy]\b")),
    ("B1", "B1", "brak wykonawcy: należy, trzeba", _count(r"\b(?:należy(?!\s+(?:do|się)\b)|trzeba|powinno się|wymaga się)\b")),
    ("B5", "B5", "imiesłów -ąc, -wszy, -łszy", _participles),
    ("B8", "B8", "zdanie dłuższe niż 25 słów", lambda s: 1 if n_words(s) > 25 else 0),
    ("C1", "C1", "spójnik: bądź, względnie, ewentualnie, i/lub", _count(r"\b(?:bądź|względnie|ewentualnie)\b|\bi/lub\b")),
    ("C2", "C2", "„i” razem z „lub” albo „albo”",
     lambda s: 1 if re.search(r"\bi\b", s) and re.search(r"\b(?:lub|albo)\b", s) else 0),
    ("C3", "C3", "warunek: jeśli, o ile, w razie, chyba że", _count(r"\b(?:jeśli|jeśliby|o ile|w razie|chyba,? że|pod warunkiem,? że)\b")),
    ("C4", "C4", "„wszystkie” albo „każdy” z przeczeniem",
     lambda s: 1 if re.search(r"\b(?:wszys\w+|każd\w+)\b", s, re.IGNORECASE) and re.search(r"\bnie\b", s, re.IGNORECASE) else 0),
    ("C5", "C5", "więcej niż 1 przeczenie", lambda s: 1 if len(_rx(r"\bnie\b").findall(s)) > 1 else 0),
    ("D1", "D1", "kropka dziesiętna", _decimal_point),
    ("D2", "D2", "granica: do, powyżej, poniżej, między", _bounds),
    ("D3", "D3", "czas zależny od dnia czytania", _count(
        r"\b(?:dziś|dzisiaj|jutro|wczoraj|pojutrze|obecnie|ostatnio|następn\w+|przyszł" + ADJ + r"|zeszł\w+)\b"
        r"|\bdo\s+(?:poniedziałku|wtorku|środy|czwartku|piątku|soboty|niedzieli|jutra)\b")),
    ("D4", "D4", "termin bez dnia numer 1: w ciągu N dni",
     _count(r"\bw\s+(?:ciągu|terminie)\s+\d+\s+(?:dni|dnia|godzin|tygodni|miesięcy|miesiąca|lat)\b")),
    ("D6", "D6", "słowo „bilion”", _count(r"\bbilion\w*\b")),
    ("E4", "E4", "odesłanie bez numeru: powyżej, poniżej",
     _count(r"\b(?:powyżej|poniżej)\b(?!\s+(?:dnia\s+)?\d)|\bjak wspomniano\b|\bwyżej wymienion\w+|\bww\b")),
    ("F", "F", "brak źródła: podobno, chyba, raczej", _count(r"\b(?:podobno|raczej|prawdopodobnie)\b|\bchyba\b(?!,?\s+że)")),
    ("KW", "KW", "słowo kluczowe małymi literami", lambda s: len(KW_RX.findall(s))),
]
CANDIDATES = [("B1s", "B1", "konstrukcja ze słowem „się” (do oceny)", _count(r"\bsię\b"))]
CODES = [c[0] for c in CHECKS]


def strip_quotes(text):
    """Quotations and code are outside PK (section 'Granice standardu'): one placeholder word each."""
    text = re.sub(r"„[^”]*”", "X", text)
    text = re.sub(r"«[^»]*»", "X", text)
    return re.sub(r"`[^`]*`", "X", text)


def strip_tex(tex):
    """Prose of a LaTeX source: no comments, mathematics, tables, bibliography or commands."""
    tex = tex.split("\\begin{document}", 1)[-1]
    tex = re.sub(r"\\pk[A-Z][A-Za-z]*\{?\}?", "7", tex)          # generated numbers
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", "", tex, flags=re.S)
    for env in ("equation", "align", "gather", "displaymath", "tabular", "tabularx", "longtable", "verbatim",
                "tikzpicture", "lstlisting"):
        tex = re.sub(r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}", " X. ", tex, flags=re.S)
    tex = re.sub(r"\\\[.*?\\\]", " X ", tex, flags=re.S)
    tex = re.sub(r"\$[^$]*\$", "X", tex)
    tex = re.sub(r"\\(?:sub)*section\*?\{[^{}]*\}|\\paragraph\{[^{}]*\}|\\title\{.*?\}\s*\\author", "\n\n", tex, flags=re.S)
    tex = re.sub(r"\\(?:cite|ref|eqref|label|includegraphics|input|usepackage|bibitem|url)(?:\[[^\]]*\])?\{[^{}]*\}", "X", tex)
    tex = re.sub(r"\\(?:texttt|enquote|pkq)\{[^{}]*\}", "X", tex)
    tex = re.sub(r"\\(?:begin|end)\{[a-zA-Z*]+\}(?:\[[^\]]*\])?", "\n\n", tex)
    tex = re.sub(r"\\rysunek\{[^{}]*\}", "\n\n", tex)
    tex = re.sub(r"\\(?:item|par|medskip|smallskip|bigskip)\b", "\n\n", tex)
    tex = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", tex)
    tex = tex.replace("~", " ").replace("\\,", " ").replace("\\%", "%").replace("\\&", "&")
    return re.sub(r"[{}\\]", "", tex)


def sentences(text):
    """Sentences of a plain text; a dot after a known abbreviation does not end a sentence."""
    text = strip_quotes(text)
    abbr = "|".join(sorted(ABBREVIATIONS, key=len, reverse=True))
    text = re.sub(r"\b(" + abbr + r")\.", lambda m: m.group(1) + "\x00", text, flags=re.IGNORECASE)
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        for s in re.split(r"(?<=[.!?:;])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ0-9(\[])|(?<=[.!?])\s+", block):
            s = s.replace("\x00", ".").strip()
            if n_words(s):
                out.append(s)
    return out


def n_words(sentence):
    """Rule B8: a word is a string between spaces that holds a letter or a digit."""
    return sum(1 for w in sentence.split() if re.search(r"\w", w))


def lint(text, candidates=False):
    """Returns (hits per check, number of words, number of sentences, examples)."""
    hits, examples, words = Counter(), {}, 0
    sents = sentences(text)
    for s in sents:
        words += n_words(s)
        for code, _rule, _what, fn in CHECKS + (CANDIDATES if candidates else []):
            k = fn(s)
            if k:
                hits[code] += k
                examples.setdefault(code, []).append(s)
    return hits, words, len(sents), examples


def selfcheck():
    bad = {
        "A3": "Jan powiedział Piotrowi, że jego pompa przecieka.", "A5": "Regularnie sprawdzaj ciśnienie.",
        "A6": "Gościom nie wolno wnosić noży, nożyczek itp.", "B1": "Po pracy należy zamknąć zawór.",
        "B5": "Otwierając zawór, obserwuj manometr.", "C2": "Włącz pompę P1 i pompę P2 lub pompę P3.",
        "C3": "Zamknij zawór Z1, chyba że pompa P1 pracuje.", "C4": "Wszystkie zawory nie są zamknięte.",
        "C5": "Nie otwieraj zaworu, dopóki ciśnienie nie spadnie.", "D2": "Dzieci do 3 lat wchodzą bezpłatnie.",
        "D3": "Dostawa przyjedzie jutro.", "D4": "Złóż reklamację w ciągu 14 dni.", "D6": "Fundusz zarządza aktywami o wartości 2 bilionów dolarów.",
        "KW": "Zawór Z1 musi być zamknięty.", "D2x": "W zawodach startują osoby w wieku 18–25 lat.", "A4": "Wyślij ostatni raport.", "D1": "Ciśnienie wynosi 2.5 bar.",
    }
    for code, s in bad.items():
        assert lint(s)[0][code.rstrip("x")] >= 1, (code, s)
    good = ["Operator zamyka zawór Z1 po zakończeniu pracy.", "Sprawdzaj ciśnienie p1 co 15 min.",
            "Dziecko, które ma mniej niż 4 lata, wchodzi bezpłatnie.", "Operator MUSI zamknąć zawór Z1.",
            "Rabat dotyczy zamówienia, które obejmuje od 5 do 10 sztuk włącznie.",
            "Wyślij raport najpóźniej 2026-11-13 o godz. 16:00.", "Odległość wynosi 50 m ± 5 m.",
            "Jeżeli pompa P1 nie pracuje, to zamknij zawór Z1.", "Wyślij najnowszy gotowy raport.", "Władza zwierzchnia należy do Narodu.", "Norma ISO 24495-1 opisuje prosty język.",
            "Cena wzrosła z 40 zł do 50 zł, czyli o 10 zł (25 %).", "Dzień roboczy 1 to pierwszy dzień roboczy."]
    for s in good:
        assert not lint(s)[0], (s, lint(s)[0])
    assert len(sentences("Wyślij raport o godz. 16:00. Zamknij zawór Z1.")) == 2
    assert lint("Autor pisze: „należy zamknąć zawór”.")[0] == Counter()
    return "ok"


def main(argv):
    tex = "--tex" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(selfcheck())
        return 0
    total = 0
    for path in files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        hits, words, n_sent, examples = lint(strip_tex(text) if tex else text)
        longest = max((n_words(s) for s in sentences(strip_tex(text) if tex else text)), default=0)
        print(f"{path}: {n_sent} zdań, {words} słów, najdłuższe zdanie {longest} słów, naruszeń {sum(hits.values())}")
        for code in CODES:
            if hits[code]:
                print(f"  {code}: {hits[code]}")
                for s in examples[code][:5]:
                    print(f"      {s[:160]}")
        total += sum(hits.values())
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
