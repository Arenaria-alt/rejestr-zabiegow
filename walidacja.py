"""
walidacja.py — moduł kontrolny terminów i limitów zabiegów
Miękkie ostrzeżenia — nie blokują zapisu, tylko informują
"""

from datetime import datetime, date
from dataclasses import dataclass
from typing import Optional

# ── Reguły terminów koszenia (dd.mm) per wariant ─────────────────────────────

# Format: wariant -> {"od": (dzień, miesiąc), "do": (dzień, miesiąc),
#                     "opis": str, "alt_od": opcjonalnie alternatywne okno}
REGULY_KOSZENIA: dict[str, dict] = {
    "1.1": {
        "od": (15, 9), "do": (31, 10),
        "opis": "Koszenie w terminie 15.09–31.10",
        "alt_od": (15, 6), "alt_do": (30, 6),
        "alt_opis": "lub wyjątkowo 15.06–30.06",
    },
    "2.1": {
        "od": (15, 9), "do": (31, 10),
        "opis": "Koszenie w terminie 15.09–31.10",
        "alt_od": (15, 6), "alt_do": (30, 6),
        "alt_opis": "lub wyjątkowo 15.06–30.06",
    },
    "1.2": {
        "od": (15, 6), "do": (30, 9),
        "opis": "Koszenie w terminie 15.06–30.09",
    },
    "2.2": {
        "od": (15, 6), "do": (30, 9),
        "opis": "Koszenie w terminie 15.06–30.09",
    },
    "1.3": {
        "od": (1, 8), "do": (31, 10),
        "opis": "Koszenie nie wcześniej niż 01.08",
        "max_kosy": 1,
    },
    "2.3": {
        "od": (1, 8), "do": (31, 10),
        "opis": "Koszenie nie wcześniej niż 01.08",
        "max_kosy": 1,
    },
    "1.4": {
        "od": (15, 6), "do": (30, 10),
        "opis": "Koszenie nie wcześniej niż 15.06",
        "max_kosy": 2,
    },
    "2.4": {
        "od": (15, 6), "do": (30, 10),
        "opis": "Koszenie nie wcześniej niż 15.06",
        "max_kosy": 2,
    },
    "1.5": {
        "od": (15, 6), "do": (30, 10),
        "opis": "Koszenie nie wcześniej niż 15.06",
        "max_kosy": 2,
    },
    "2.5": {
        "od": (15, 6), "do": (30, 10),
        "opis": "Koszenie nie wcześniej niż 15.06",
        "max_kosy": 2,
    },
    # Warianty ptaków — lęgi kończą się późno
    "1.7":  {"od": (15, 7), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 15.07", "max_kosy": 2},
    "2.7":  {"od": (15, 7), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 15.07", "max_kosy": 2},
    "1.8":  {"od": (1,  8), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 01.08", "max_kosy": 2},
    "2.8":  {"od": (1,  8), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 01.08", "max_kosy": 2},
    "1.9":  {"od": (15, 7), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 15.07", "max_kosy": 2},
    "2.9":  {"od": (15, 7), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 15.07", "max_kosy": 2},
    "1.10": {"od": (1,  8), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 01.08", "max_kosy": 2},
    "2.10": {"od": (1,  8), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 01.08", "max_kosy": 2},
    # Wariant 3 — ekstensywne użytkowanie
    "3":    {"od": (1,  6), "do": (31, 10), "opis": "Koszenie nie wcześniej niż 01.06", "max_kosy": 2},
}

# Termin wypasów — wspólny dla wszystkich wariantów
WYPAS_OD = (1, 5)   # 1 maja
WYPAS_DO = (30, 11) # 30 listopada

# Słowa kluczowe identyfikujące zabiegi koszenia w katalogu
# Słowa identyfikujące ZABIEG KOSZENIA (limitowany)
# NIE zaliczamy: zbiór siana, zbiór biomasy, spasanie — to osobne czynności
SLOWA_KOSZENIA = [
    "koszenie", "pokos",
]

# Słowa wykluczające — jeśli czynność zawiera te słowa, NIE jest koszeniem
SLOWA_WYKLUCZONE_KOSZENIE = [
    "zbiór siana", "zbiór biomasy", "spasanie", "wypas", "nawożenie",
    "wapnowanie", "siew", "podsiew", "oprysk", "ochrona",
]


# ── Model ostrzeżenia ─────────────────────────────────────────────────────────

@dataclass
class Ostrzezenie:
    poziom: str          # "BŁĄD" / "UWAGA" / "INFO"
    dzialka_ozn: str     # oznaczenie działki (A, B, C)
    nr_ewid: str         # nr ewidencyjny
    wariant: str
    data: str
    czynnosc: str
    komunikat: str
    szczegoly: str = ""

    @property
    def ikona(self) -> str:
        return {"BŁĄD": "🔴", "UWAGA": "🟡", "INFO": "🔵"}.get(self.poziom, "⚪")

    def __str__(self):
        return (f"{self.ikona} [{self.poziom}] Działka {self.dzialka_ozn} "
                f"({self.wariant}) — {self.data}\n"
                f"   {self.komunikat}\n"
                f"   Zabieg: {self.czynnosc}")


# ── Funkcje pomocnicze ────────────────────────────────────────────────────────

def _parse_date(s: str) -> Optional[date]:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _czy_koszenie(czynnosc: str) -> bool:
    """Zwraca True tylko dla faktycznych zabiegów koszenia (nie zbiór siana itp.)"""
    c = czynnosc.lower()
    if any(w in c for w in SLOWA_WYKLUCZONE_KOSZENIE):
        return False
    return any(k in c for k in SLOWA_KOSZENIA)


def _czy_wypas(czynnosc: str) -> bool:
    c = czynnosc.lower()
    return any(k in c for k in ["wypas", "spasanie", "pasieni"])


def _w_oknie(d: date, od: tuple, do: tuple) -> bool:
    """Sprawdza czy data mieści się w oknie (dzień, miesiąc) w tym samym roku."""
    od_date = date(d.year, od[1], od[0])
    # Obsługa końca roku (np. do 31.10 następnego roku)
    rok_do = d.year if do[1] >= od[1] else d.year + 1
    try:
        do_date = date(rok_do, do[1], do[0])
    except ValueError:
        do_date = date(rok_do, do[1], 28)
    return od_date <= d <= do_date


# ── Główna funkcja walidacji ──────────────────────────────────────────────────

def waliduj_zabieg(
    ozn: str,
    nr_ewid: str,
    wariant: str,
    data_str: str,
    czynnosc: str,
    zabiegi_dzialki: list,   # lista ZabiegAgrotechniczny dla tej działki w danym roku
    uwagi_dzialki: str = "",  # uwagi z karty działki (np. "zakaz wczesnego wypasu")
) -> list[Ostrzezenie]:
    """
    Waliduje pojedynczy zabieg.
    Zwraca listę ostrzeżeń (pusta = brak problemów).
    """
    wyniki = []
    d = _parse_date(data_str)
    if d is None:
        wyniki.append(Ostrzezenie(
            poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
            wariant=wariant, data=data_str, czynnosc=czynnosc,
            komunikat="Nie można sparsować daty — sprawdź format dd.mm.rrrr"))
        return wyniki

    regula = REGULY_KOSZENIA.get(wariant)

    # ── Walidacja koszenia ────────────────────────────────────────────────────
    if _czy_koszenie(czynnosc) and regula:
        od = regula["od"]
        do = regula.get("do", (31, 10))
        alt_od = regula.get("alt_od")
        alt_do = regula.get("alt_do")

        w_glownym = _w_oknie(d, od, do)
        w_alt = alt_od and _w_oknie(d, alt_od, alt_do)

        if not w_glownym and not w_alt:
            od_str = f"{od[0]:02d}.{od[1]:02d}"
            do_str = f"{do[0]:02d}.{do[1]:02d}"
            alt_str = (f" lub {alt_od[0]:02d}.{alt_od[1]:02d}–"
                       f"{alt_do[0]:02d}.{alt_do[1]:02d}"
                       if alt_od else "")
            wyniki.append(Ostrzezenie(
                poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
                wariant=wariant, data=data_str, czynnosc=czynnosc,
                komunikat=f"Data koszenia poza dozwolonym terminem",
                szczegoly=f"Dozwolone: {od_str}–{do_str}{alt_str} "
                          f"({regula['opis']})"))

        # Limit pokosów — liczymy unikalne daty koszenia (nie duplikujemy per numer ewid.)
        max_kosy = regula.get("max_kosy", 2)
        rok = d.year
        # Unikalne daty zabiegów koszenia dla tej działki rolnej w tym roku
        daty_kosy = set(
            z.data for z in zabiegi_dzialki
            if _czy_koszenie(z.czynnosc)
            and _parse_date(z.data)
            and _parse_date(z.data).year == rok
        )
        kosy_w_roku = len(daty_kosy)
        if kosy_w_roku >= max_kosy:
            wyniki.append(Ostrzezenie(
                poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
                wariant=wariant, data=data_str, czynnosc=czynnosc,
                komunikat=f"Przekroczony limit pokosów w {rok} r.",
                szczegoly=f"Wariant {wariant}: max {max_kosy} "
                          f"{'pokos' if max_kosy == 1 else 'pokosy'} w roku. "
                          f"Daty koszenia: {', '.join(sorted(daty_kosy))}"))

    # ── Walidacja wypasu ──────────────────────────────────────────────────────
    if _czy_wypas(czynnosc):
        zakaz = "zakaz wczesnego wypasu" in uwagi_dzialki.lower()
        if zakaz:
            wyniki.append(Ostrzezenie(
                poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
                wariant=wariant, data=data_str, czynnosc=czynnosc,
                komunikat="Działka ma zaznaczony zakaz wczesnego wypasu w planie",
                szczegoly="Sprawdź zapisy planu rolno-środowiskowego"))

        if not _w_oknie(d, WYPAS_OD, WYPAS_DO):
            wyniki.append(Ostrzezenie(
                poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
                wariant=wariant, data=data_str, czynnosc=czynnosc,
                komunikat="Data wypasu poza standardowym sezonem (01.05–30.11)",
                szczegoly="Sprawdź zapisy planu rolno-środowiskowego"))

    return wyniki


def waliduj_wpis_wypasu(
    ozn: str,
    nr_ewid: str,
    wariant: str,
    data_str: str,
    uwagi_dzialki: str = "",
) -> list[Ostrzezenie]:
    """Waliduje wpis w wykazie wypasów."""
    wyniki = []
    d = _parse_date(data_str)
    if d is None:
        return wyniki

    zakaz = "zakaz wczesnego wypasu" in uwagi_dzialki.lower()
    if zakaz and d < date(d.year, WYPAS_OD[1], WYPAS_OD[0]):
        wyniki.append(Ostrzezenie(
            poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
            wariant=wariant, data=data_str, czynnosc="wypas",
            komunikat="Działka ma zaznaczony zakaz wczesnego wypasu w planie",
            szczegoly="Sprawdź zapisy planu rolno-środowiskowego"))

    if not _w_oknie(d, WYPAS_OD, WYPAS_DO):
        wyniki.append(Ostrzezenie(
            poziom="UWAGA", dzialka_ozn=ozn, nr_ewid=nr_ewid,
            wariant=wariant, data=data_str, czynnosc="wypas",
            komunikat="Data wypasu poza sezonem (01.05–30.11)",
            szczegoly="Wypas dopuszczony od 1 maja"))

    return wyniki


def waliduj_caly_rejestr(gosp) -> list[Ostrzezenie]:
    """
    Sprawdza wszystkie zabiegi i wypasy w gospodarstwie.
    Zwraca posortowaną listę ostrzeżeń.
    """
    wszystkie = []

    # Słownik: dzialka_id -> DzialkaRolna
    dzialki_map = {d.id: d for d in gosp.dzialki}

    # Grupuj zabiegi po (dzialka_id, rok) — per DZIAŁKA ROLNA, nie per numer ewid.
    # Dzięki temu limit pokosów liczy się dla całej działki rolnej (A, B, C)
    from collections import defaultdict
    zabiegi_per_dzialka: dict = defaultdict(list)
    for z in gosp.zabiegi:
        d = _parse_date(z.data)
        if d:
            zabiegi_per_dzialka[(z.dzialka_id, d.year)].append(z)

    # Waliduj zabiegi — deduplikuj ostrzeżenia o limitach per działka rolna
    # (nie generuj osobnego ostrzeżenia dla każdego numeru ewidencyjnego)
    ostrzezenia_limitow: set = set()  # (dzialka_id, rok, typ_ostrzezenia)

    for z in gosp.zabiegi:
        dzialka = dzialki_map.get(z.dzialka_id)
        wariant = dzialka.wariant if dzialka else ""
        uwagi_dz = dzialka.uwagi if dzialka else ""
        d = _parse_date(z.data)
        rok = d.year if d else 0

        # Inne zabiegi tej samej działki rolnej w tym roku (bez bieżącego)
        inne_zabiegi = [x for x in zabiegi_per_dzialka.get((z.dzialka_id, rok), [])
                        if x.id != z.id]

        ost = waliduj_zabieg(
            ozn=z.oznaczenie, nr_ewid=z.nr_ewid,
            wariant=wariant, data_str=z.data,
            czynnosc=z.czynnosc,
            zabiegi_dzialki=inne_zabiegi,
            uwagi_dzialki=uwagi_dz,
        )

        for o in ost:
            # Deduplikuj ostrzeżenia o limitach pokosów per działka rolna
            if "limit pokosów" in o.komunikat.lower():
                klucz = (z.dzialka_id, rok, "limit")
                if klucz in ostrzezenia_limitow:
                    continue  # już zgłoszone dla tej działki rolnej w tym roku
                ostrzezenia_limitow.add(klucz)
            wszystkie.append(o)

    # Waliduj wypasy
    for w in gosp.wypasy:
        dzialka = dzialki_map.get(w.dzialka_id)
        wariant = dzialka.wariant if dzialka else ""
        uwagi_dz = dzialka.uwagi if dzialka else ""
        ost = waliduj_wpis_wypasu(
            ozn=w.oznaczenie, nr_ewid=w.nr_ewid,
            wariant=wariant, data_str=w.data,
            uwagi_dzialki=uwagi_dz,
        )
        wszystkie.extend(ost)

    # Sortuj: najpierw BŁĄD, potem UWAGA, potem wg działki i daty
    poziom_sort = {"BŁĄD": 0, "UWAGA": 1, "INFO": 2}
    wszystkie.sort(key=lambda o: (poziom_sort.get(o.poziom, 9),
                                   o.dzialka_ozn, o.data))
    return wszystkie


def komunikat_ostrzezenia(ostrzezenia: list[Ostrzezenie]) -> str:
    """Buduje tekst komunikatu do okna dialogowego."""
    if not ostrzezenia:
        return ""
    linie = ["⚠️  Wykryto potencjalne problemy:\n"]
    for o in ostrzezenia:
        linie.append(f"{o.ikona} Działka {o.dzialka_ozn} ({o.wariant}) — {o.data}")
        linie.append(f"   {o.komunikat}")
        if o.szczegoly:
            linie.append(f"   ℹ️  {o.szczegoly}")
        linie.append("")
    linie.append("Czy mimo to zapisać wpis?")
    return "\n".join(linie)
