# Terminy utworzone w projekcie gospodarstwa samowystarczalnego

Plik zawiera terminy, które Claude (model językowy firmy Anthropic) utworzył w projekcie „Samowystarczalny system do życia”. Projekt opisuje gospodarstwo o powierzchni 4,27 ha w Olsztynie i stosuje PK 0.1. Właścicielem projektu jest Maciej Szulia. Data projektu: 2026-11-11. Repozytorium projektu: [samowystarczalny-system-do-zycia](https://github.com/maciejszulia/samowystarczalny-system-do-zycia).

> Legenda: znacznik w nawiasie kwadratowym podaje źródło informacji według modułu F. Znacznik `[DO USTALENIA: …]` oznacza brak danych. „Lub” znaczy co najmniej 1 z członów. „Albo” znaczy dokładnie 1 z członów.

## Słownik

| Termin | Definicja | Nie pisz |
|---|---|---|
| słownik projektu | Sekcja „Słownik” w dokumencie projektu. Sekcja ma 22 terminy. | glosariusz |
| termin utworzony | Termin z 2 albo 3 słów, którego wyszukiwanie w sieci z 2026-11-11 nie znalazło w znaczeniu z projektu. | neologizm |
| termin zawężony | Termin zwykłej polszczyzny, któremu słownik projektu nadał mierzalną granicę. | termin własny |
| kolizja | Stan, w którym 1 nazwa ma w 1 dziedzinie 2 znaczenia. | konflikt nazw |

## 1. Wynik

Słownik projektu ma 22 terminy: 8 terminów utworzonych i 14 terminów zawężonych albo terminów dziedziny. Każdy termin utworzony zastąpił słowo nieostre z reguły A5. Każda definicja zawiera liczbę albo warunek, który czytelnik potrafi sprawdzić. Obliczenia i decyzje projektu używają tych liczb.

## 2. Terminy utworzone

| Nr | Termin | Definicja | Słowo, które termin zastępuje | Reguła | Skutek w projekcie |
|---|---|---|---|---|---|
| 1 | dzień pusty | Dzień kalendarzowy, w którym magazyn energii osiąga dolną granicę rozładowania 20%. | „blackout”, „brak prądu” | A4, A5, D4 | Liczba dni pustych na rok porównuje 9 wariantów instalacji. Wariant 25 kWp i 30 kWh daje 6,1 dnia pustego na rok `[obliczenie: PVGIS 5.3, usługa SHScalc]`. |
| 2 | stado pełne | Stado, które liczy co najwyżej 100 sztuk w szczycie sezonu. | „duże stado” | A4, A5, D2 | Odpowiedź właściciela „może być 100 sztuk” wskazała 1 wariant: 10 260 jaj i 3,4 t paszy na rok `[obliczenie]`. |
| 3 | stado domowe | Stado, które pokrywa tylko potrzeby 4 osób: 47 sztuk w szczycie sezonu. | „małe stado” | A4, A5 | Wariant wymaga zakupu 1,0 t paszy na rok `[obliczenie]`. |
| 4 | plon ostrożny | Plon gleby średniej pomnożony przez współczynnik od 0,50 do 0,60. | „niski plon” | A4, A5, D5 | Dolna granica wyniku: gospodarstwo pokrywa 66% energii diety 4 osób `[obliczenie]`. |
| 5 | plon dobry | Plon z tabeli projektu, który wymaga poprawy gleby i nawadniania. | „wysoki plon” | A4, A5 | Górna granica wyniku: gospodarstwo pokrywa 92% energii diety 4 osób `[obliczenie]`. |
| 6 | odbiornik priorytetu 1 | Odbiornik, który ma zasilanie przez całą dobę. | „odbiornik krytyczny” | A4, A5 | Instrukcja awaryjna ma 1 znaczenie: „Zasil odbiorniki priorytetu 1 z agregatu”. |
| 7 | odbiornik priorytetu 2 | Odbiornik, który ma zasilanie tylko w 2 przypadkach: od 10:00 do 15:00 lub przy stanie naładowania większym niż 70%. | „odbiornik przesuwalny” | A4, A5, C1, D2, D3 | Instalator wpisuje do sterownika 1 przedział godzin i 1 próg. |
| 8 | odbiornik priorytetu 3 | Odbiornik, który falownik wyłącza przy stanie naładowania mniejszym niż 30%. | „odbiornik zrzucany” | A4, A5, D2 | Instalator wpisuje do falownika 1 próg. |

Terminy od 2 do 5 tworzą 2 pary. Para nazywa 2 granice zakresu: stado domowe i stado pełne, plon ostrożny i plon dobry. Zdanie „gospodarstwo pokrywa od 66% do 92% energii diety” ma dzięki parze 2 nazwane granice.

Wynik wyszukiwania z 2026-11-11 `[obserwacja]`:

- Terminy „dzień pusty”, „plon ostrożny”, „stado pełne” i „stado domowe”: wyszukiwanie nie znalazło tych terminów w znaczeniu z projektu.
- Termin „plon dobry”: zwykła polszczyzna zna wyrażenie „dobry plon”. Wyrażenie nie ma liczby. Termin z definicją jest nowy.
- Terminy „odbiornik priorytetu 1”, „odbiornik priorytetu 2” i „odbiornik priorytetu 3”: dokumentacja falowników zna „priorytety” odbiorników `[źródło: Victron Energy, instrukcja urządzeń GX]`. Numer z progiem jest nowy.

## 3. Terminy zawężone

Tabela zawiera 6 z 14 terminów. Te terminy istnieją w zwykłej polszczyźnie. Słownik projektu nadał każdemu terminowi 1 granicę.

| Termin | Definicja w projekcie | Znaczenie, które definicja wyklucza | Reguła |
|---|---|---|---|
| grunt orny | Teren otwarty o spadku mniejszym niż 15%. | Użytek „R” z ewidencji gruntów. | A4, D2 |
| teren otwarty | Grunt gospodarstwa bez drzewostanu, bez budynków i poza polem kempingowym. | Każdy grunt bez drzew. | A4 |
| drzewostan | Grunt gospodarstwa pokryty drzewami o zwartych koronach. | „Las” w znaczeniu ustawy o lasach. | A1, A4 |
| pole kempingowe | Część działki 24/1, którą zajmują stanowiska kempingu. | Cała działka 24/1. | A2, A4 |
| tryb zimowy | Praca instalacji od listopada do lutego ze zużyciem 8 kWh na dobę. | „Oszczędzanie” bez liczby. | A5, D1 |
| gruzowisko | Kopiec gruzu o wymiarach 7 m × 6 m w strefie S2. | „Kopiec” o nieznanym składzie. | A2 |

Przykład skutku: grunt orny gospodarstwa ma 0,65 ha `[obliczenie]`. Ta liczba wynika z granicy 15% i decyduje o wyniku projektu. Słowo „pole” nie daje takiej liczby.

## 4. Nazwy obiektów

Projekt nadał 34 nazwy z oznaczeniem (reguła A2). Model 3D, rysunki i tabele projektu używają tych samych nazw.

| Grupa | Nazwy | Liczba nazw | Obiekt |
|---|---|---|---|
| strefy | S1, S2, S3, S4a, S4b, S5, S6, S7, S8a, S8b, S9, S10, D | 13 | Część gospodarstwa o 1 funkcji i o zmierzonej powierzchni. |
| pola | P1, P2, P3, P4, P5 | 5 | Pole płodozmianu. |
| obiekty | B1, W1, T1, M1, U1, K | 6 | Budynek inwentarski, zbiornik górny, tunel foliowy, piwnica ziemna, pasieka, gruzowisko. |
| etapy | E1, E2, E3, E4, E5, E6, E7 | 7 | Etap wdrożenia z kosztem i z terminem. |
| linie stelaża | A, B, C | 3 | Wariant położenia stelaża fotowoltaiki. |

Przykład: zdanie „Zbiornik W1 stoi 110 m od domu” ma 1 znaczenie. Zdanie „Zbiornik stoi 110 m od domu” ma 2 znaczenia, bo projekt ma zbiornik górny i zbiornik na deszczówkę.

## 5. Błędy i poprawki

Kontrola znalazła 4 błędy w terminach. Dokument projektu zawiera każdą poprawkę.

| Nr | Błąd | Reguła | Poprawka |
|---|---|---|---|
| 1 | Claude utworzył termin „gniazda wykotowe” dla kur bez źródła. Tezaurus AGROVOC podaje terminy „wykot kóz” i „wykot owiec” `[źródło: AGROVOC, pojęcie c_5604]`. | A4; zasada „Nie zgaduj faktów” | Opis zamiast terminu: „gniazda z rynną na jaja”. |
| 2 | Pierwsza nazwa brzmiała „odbiornik klasy 1”. Słowo „klasa” oznacza w elektrotechnice klasę ochronności urządzenia: 0, I, II albo III `[źródło: Lena Lighting, „Klasa ochronności”]`. To jest kolizja. | A1, A4 | Nazwa „odbiornik priorytetu 1”. |
| 3 | Definicja terminu „dzień pusty” zaczynała się od słowa „doba”. Symulacja liczy dni kalendarzowe. | D4 | Definicja zaczyna się od słów „dzień kalendarzowy”. |
| 4 | Definicja terminu „odbiornik priorytetu 2” łączyła 2 warunki słowem „albo”. Odbiornik ma zasilanie także wtedy, gdy zachodzą oba warunki. | C1 | Definicja łączy warunki słowem „lub”. |

## 6. Kontrola nowego terminu

Wykonaj każdy krok w tej kolejności przed pierwszym użyciem nowego terminu:

1. Wyszukaj pojęcie w źródłach dziedziny. Jeżeli dziedzina ma termin dla tego pojęcia, to użyj terminu dziedziny.
2. Wyszukaj każde słowo nowego terminu w normach i w słownikach dziedziny. Jeżeli znajdziesz kolizję, to zmień słowo.
3. Zapisz definicję wzorem z reguły A4. Definicja zawiera liczbę z jednostką albo warunek, który czytelnik potrafi sprawdzić.
4. Zapisz w kolumnie „Nie pisz” słowo nieostre, które termin zastępuje.
5. Jeżeli wynik ma 2 granice, to utwórz 2 terminy: po 1 terminie dla każdej granicy. Przykład: plon ostrożny i plon dobry.
6. Sprawdź definicję regułami C1, D2, D3, D4 i D5.
7. Wpisz termin do sekcji „Słownik” przed treścią.

## Decyzje i braki

| Nr | Fragment | Reguła | Znaczenia lub brak | Wybór |
|---|---|---|---|---|
| 1 | „wyrazy, które nie występują w zwykłym języku polskim” | A5 | Brak kryterium sprawdzenia. | Kryterium: wyszukiwanie w sieci z 2026-11-11 nie znalazło terminu w znaczeniu z projektu. Brak wyniku nie dowodzi, że termin nie istnieje. |
| 2 | „wyrazy” | A4 | 2 znaczenia: pojedyncze słowo; termin z 2 albo 3 słów. | Termin z 2 albo 3 słów. Projekt nie utworzył żadnego pojedynczego słowa. |
| 3 | „dobry przykład” | A5 | Brak kryterium. | Kryterium: termin zastąpił słowo nieostre i dał liczbę, której użyło obliczenie albo decyzja. |

## Źródła

- Dokument projektu: [„Projekt samowystarczalnego gospodarstwa – Młodzieżowa 1, Olsztyn”](https://github.com/maciejszulia/samowystarczalny-system-do-zycia/blob/main/projekt/PROJEKT.md), wersja z 2026-11-11, sekcje „Słownik” oraz „Decyzje i braki”.
- Dni puste: Komisja Europejska, Joint Research Centre, [PVGIS 5.3](https://re.jrc.ec.europa.eu/pvg_tools/en/), usługa SHScalc.
- Słowo „wykot”: FAO, tezaurus [AGROVOC, pojęcie c_5604](https://agrovoc.fao.org/skosmosAsfa/asfa/zh/page/c_5604?clang=nl).
- Klasy ochronności: Lena Lighting, baza wiedzy, [„Klasa ochronności”](https://lenalighting.pl/o-nas/baza-wiedzy/2106-klasa-ochronnosci) (klasy 0, I, II i III według normy PN-EN 61140).
- Priorytety odbiorników: Victron Energy, [instrukcja urządzeń GX, rozdział o odbiornikach nadwyżki energii](https://www.victronenergy.com/media/pg/Cerbo_GX/pl/gx-opportunity-loads.html).
