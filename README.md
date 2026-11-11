# Polszczyzna Kontrolowana (PK)

PK to ulepszenie języka polskiego dla tekstów, według których ktoś działa. To zwykły
polski plus zbiór reguł. Każda reguła usuwa jedno źródło zdań, które mają więcej niż
jedno znaczenie. Czytelnik, który zna konwencję, odczytuje każde zdanie w jeden sposób.

Wersja 0.1. Autor: Maciej Szulia. Pełny standard: [`SKILL.md`](skills/polszczyzna-kontrolowana/SKILL.md).

## Po co

Polska gramatyka zostawia czytelnikowi wybór w stałych miejscach: brak rodzajników,
swobodny szyk, dopełniacz, spójniki, granice przedziałów. PK zamyka każde z tych miejsc
konwencją.

| Zdanie w zwykłym polskim | Znaczenia | Zdanie w PK |
|---|---|---|
| „Dzieci do 3 lat wchodzą bezpłatnie.” | mniej niż 3 lata; mniej niż 4 lata | „Dziecko, które ma mniej niż 4 lata, wchodzi bezpłatnie.” |
| „Zawór zamyka się po pracy.” | ktoś zamyka zawór; zawór zamyka się sam; czytelnik ma zamknąć zawór | „Operator zamyka zawór Z1 po zakończeniu pracy.” |
| „Wyślij raport do piątku.” | termin obejmuje piątek; termin kończy się przed piątkiem | „Wyślij raport najpóźniej 2026-11-13 o godz. 16:00.” |
| „Wszystkie zawory nie są zamknięte.” | żaden nie jest zamknięty; nie każdy jest zamknięty | „Żaden zawór nie jest zamknięty.” albo „Co najmniej 1 zawór jest otwarty.” |

## Co zawiera standard

- **Słowa kluczowe wymagań:** MUSI, NIE WOLNO, POWINIEN, NIE POWINIEN, MOŻE. Wzorem jest RFC 2119.
- **32 numerowane reguły w 5 grupach:** A. Słowa, B. Zdanie, C. Logika, D. Liczby, wielkości, czas,
  E. Struktura tekstu. Do tego moduł F dla raportów: znacznik źródła przy każdym fakcie.
- **Słowa zakazane** z powodem i zamiennikiem, na przykład „niezwłocznie”, „regularnie”, „do”, „i/lub”.
- **Kontrola:** 7 kroków po napisaniu tekstu, w tym liczenie słów i test 2 znaczeń.
- **Zasada braków:** brakującej liczby, daty lub wykonawcy nie wolno zgadywać. W tekście
  zostaje znacznik `[DO USTALENIA: czego brakuje]`.

## Do czego służy

Instrukcja, procedura, regulamin, wymaganie, specyfikacja, umowa, raport techniczny.
PK nie służy do literatury, reklamy i rozmowy. PK to inny standard niż prosty język
(ISO 24495-1): prosty język służy łatwemu zrozumieniu, PK służy jednemu znaczeniu.
Umowa w PK nadal wymaga oceny prawnika.

## Użycie jako skill Claude

```sh
git clone https://github.com/maciejszulia/polszczyzna-kontrolowana.git
ln -s "$PWD/polszczyzna-kontrolowana/skills/polszczyzna-kontrolowana" ~/.claude/skills/
```

Claude Code wczyta skill w następnej sesji. Skill ma 3 tryby:

| Tryb | Prośba | Wynik |
|---|---|---|
| PISZ | „napisz instrukcję w PK” | nowy tekst w PK oraz tabela „Decyzje i braki” |
| PRZEREDAGUJ | „usuń niejednoznaczności” | tekst w PK oraz tabela „Decyzje i braki” |
| SPRAWDŹ | „sprawdź w PK” | tabela naruszeń, tekst źródłowy bez zmian |

## Źródła

Reguły opierają się między innymi na RFC 2119, ASD-STE100 Simplified Technical English,
„Zasadach techniki prawodawczej”, notacji EARS i ISO 8601. Pełna lista ze wskazaniem
reguł jest w sekcji „Źródła” pliku `SKILL.md`.

---

**EN:** Polszczyzna Kontrolowana (PK, "Controlled Polish") is an improvement of the Polish
language for text people act on: ordinary Polish plus a numbered rule set that leaves
every sentence exactly one meaning. It closes the places where Polish grammar leaves the
reader a choice (no articles, free word order, the genitive, conjunctions, range
boundaries). It ships as a Claude skill that writes, rewrites and audits Polish text;
its English counterpart is ASD-STE100.
