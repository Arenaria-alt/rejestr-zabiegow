"""
dane.py — model danych rejestru zabiegów
Zapis/odczyt do JSON, import z CSV ARiMR
"""

import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional
import pandas as pd


# ── Typy użytkowania TUZ ──────────────────────────────────────────────────────
SPOSOBY_UZYTKOWANIA = ["kośne", "pastwiskowe", "kośno-pastwiskowe", "inne"]

# ── Modele danych ─────────────────────────────────────────────────────────────

@dataclass
class DzialkaRolna:
    """Jedna działka rolna (oznaczenie literowe) w gospodarstwie."""
    id: str                          # uuid
    oznaczenie: str                  # A, B, C...
    uprawa: str                      # TUZ, pszenica itp.
    sposob_uzytkowania: str          # kośne / pastwiskowe / kośno-pastwiskowe
    wariant: str                     # 2.4, 1.8 itp.
    symbol_dzialania: str            # ZRSK2327, RE2327 PS itp.
    # Lista numerów ewidencyjnych przypisanych do tej działki rolnej
    numery_ewid: list[str] = field(default_factory=list)
    # Powierzchnia łączna [ha]
    pow_ha: float = 0.0
    # Historia zmian oznaczenia: [{rok: int, stare_ozn: str, nowe_ozn: str}]
    historia_oznaczen: list[dict] = field(default_factory=list)
    # Powierzchnia per numer ewidencyjny: {"081106_5.0008.833/1": 4.98, ...}
    pow_ewid: dict[str, float] = field(default_factory=dict)
    uwagi: str = ""


@dataclass
class ZabiegAgrotechniczny:
    """Jeden wpis w wykazie działań agrotechnicznych."""
    id: str
    dzialka_id: str                  # id DzialkaRolna
    oznaczenie: str                  # literowe (może być stare lub nowe)
    nr_ewid: str                     # nr działki ewidencyjnej
    data: str                        # "dd.mm.yyyy"
    pow_ha: float                    # powierzchnia działki/uprawy
    rodzaj_uzytkowania: str          # kośne / inne
    czynnosc: str                    # z katalogu lub wpisana ręcznie
    srodek: str                      # nazwa środka/nawozu lub "-"
    ilosc: str                       # ilość lub "-"
    symbol_dzialania: str            # ZRSK2327, RE2327 itp.
    wariant: str = ""              # numer wariantu np. "2.4"
    uwagi: str = ""


@dataclass
class WpisWypasu:
    """Jeden wpis w wykazie wypasów zwierząt."""
    id: str
    dzialka_id: str
    oznaczenie: str
    nr_ewid: str
    data: str                        # "dd.mm.yyyy"
    pow_ha: float
    gatunek: str                     # bydło, owce itp.
    liczba: str                      # np. "5 krów, 2 jałówki"
    symbol_dzialania: str
    wariant: str = ""              # numer wariantu np. "2.4"
    uwagi: str = ""                  # rodzaj wypasu, typ użytkowania itp.


@dataclass
class Gospodarstwo:
    """Kompletne dane jednego gospodarstwa."""
    nazwa: str
    rolnik: str
    nr_identyfikacyjny: str
    warianty: list[str] = field(default_factory=list)   # kody wariantów na str. tytułowej
    dzialki: list[DzialkaRolna] = field(default_factory=list)
    zabiegi: list[ZabiegAgrotechniczny] = field(default_factory=list)
    wypasy: list[WpisWypasu] = field(default_factory=list)
    plany_wypasu: list[dict] = field(default_factory=list)  # serializowane PlanWypasu
    data_utworzenia: str = field(default_factory=lambda: date.today().isoformat())
    ostatni_import_csv: str = ""


# ── Serializacja / deserializacja ─────────────────────────────────────────────

def _nowy_id() -> str:
    return str(uuid.uuid4())[:8]


def zapisz(gosp: Gospodarstwo, sciezka: str):
    """Zapisuje gospodarstwo do pliku JSON."""
    data = {
        "nazwa":               gosp.nazwa,
        "rolnik":              gosp.rolnik,
        "nr_identyfikacyjny":  gosp.nr_identyfikacyjny,
        "warianty":            gosp.warianty,
        "data_utworzenia":     gosp.data_utworzenia,
        "ostatni_import_csv":  gosp.ostatni_import_csv,
        "dzialki":      [asdict(d) for d in gosp.dzialki],
        "zabiegi":      [asdict(z) for z in gosp.zabiegi],
        "wypasy":       [asdict(w) for w in gosp.wypasy],
        "plany_wypasu": gosp.plany_wypasu,
    }
    Path(sciezka).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def wczytaj(sciezka: str) -> Gospodarstwo:
    """Wczytuje gospodarstwo z pliku JSON."""
    raw = json.loads(Path(sciezka).read_text(encoding="utf-8"))
    gosp = Gospodarstwo(
        nazwa              = raw.get("nazwa", ""),
        rolnik             = raw.get("rolnik", ""),
        nr_identyfikacyjny = raw.get("nr_identyfikacyjny", ""),
        warianty           = raw.get("warianty", []),
        data_utworzenia    = raw.get("data_utworzenia", ""),
        ostatni_import_csv = raw.get("ostatni_import_csv", ""),
    )
    for d in raw.get("dzialki", []):
        gosp.dzialki.append(DzialkaRolna(**d))
    for z in raw.get("zabiegi", []):
        gosp.zabiegi.append(ZabiegAgrotechniczny(**z))
    for w in raw.get("wypasy", []):
        gosp.wypasy.append(WpisWypasu(**w))
    return gosp


# ── Import z CSV ARiMR ────────────────────────────────────────────────────────

def _fmt_wariant(v) -> str:
    if pd.isna(v) or str(v).strip() in ("", "nan"):
        return ""
    try:
        return f"{float(str(v).replace(',', '.')):g}"
    except (ValueError, TypeError):
        return str(v).strip()


def _symbol_dzialania(platnosci: str, wariant: str) -> str:
    """Wyznacza symbol działania na podstawie listy płatności i wariantu."""
    p = platnosci.upper()
    if "RE2327" in p:
        return "RE2327 PS"
    if "ZRSK" in p or wariant:
        return "ZRSK2327"
    return ""


def importuj_csv(sciezka: str) -> tuple[list[DzialkaRolna], list[str]]:
    """
    Wczytuje CSV z ARiMR i zwraca:
    - listę DzialkaRolna (jedna per oznaczenie literowe)
    - listę unikalnych wariantów (do strony tytułowej)
    """
    df = pd.read_csv(sciezka, sep=None, engine="python", dtype=str)
    df.columns = df.columns.str.strip()

    COL_OZN    = "Oznaczenie Uprawy / działki rolnej"
    COL_UPRAWA = "Roślina uprawna"
    COL_POW    = "Powierzchnia uprawy w granicach działki ewidencyjnej - ha"
    COL_POW2   = "Powierzchnia [ha]"
    COL_NR     = "Nr działki ewidencyjnej"
    COL_ZRSK   = "Nr pakietu/wariantu/opcji - płatność ZRSK2327"
    COL_PLATNO = "Lista płatności"

    # Grupuj po oznaczeniu literowym
    dzialki_map: dict[str, DzialkaRolna] = {}
    warianty_set: set[str] = set()

    for _, row in df.iterrows():
        ozn    = str(row.get(COL_OZN, "") or "").strip()
        uprawa = str(row.get(COL_UPRAWA, "") or "").strip()
        nr     = str(row.get(COL_NR, "") or "").strip()
        platno = str(row.get(COL_PLATNO, "") or "").strip()
        zrsk   = _fmt_wariant(row.get(COL_ZRSK, ""))

        try:
            pow_val = float(str(row.get(COL_POW, row.get(COL_POW2, "0")) or "0")
                            .replace(",", "."))
        except (ValueError, TypeError):
            pow_val = 0.0

        if not ozn:
            continue

        symbol = _symbol_dzialania(platno, zrsk)
        if zrsk:
            warianty_set.add(zrsk)

        # Sposób użytkowania — domyślnie kośne dla TUZ
        sposob = "kośne" if "TUZ" in uprawa.upper() else "inne"

        if ozn not in dzialki_map:
            dzialki_map[ozn] = DzialkaRolna(
                id=_nowy_id(),
                oznaczenie=ozn,
                uprawa=uprawa,
                sposob_uzytkowania=sposob,
                wariant=zrsk,
                symbol_dzialania=symbol,
                numery_ewid=[],
                pow_ha=0.0,
            )

        d = dzialki_map[ozn]
        if nr and nr not in d.numery_ewid:
            d.numery_ewid.append(nr)
        if nr:
            d.pow_ewid[nr] = round(pow_val, 4)
        d.pow_ha = round(d.pow_ha + pow_val, 4)

    return list(dzialki_map.values()), sorted(warianty_set)


def dopasuj_zmiany_literacji(
    stare: list[DzialkaRolna],
    nowe_csv: list[DzialkaRolna],
    rok: int
) -> list[dict]:
    """
    Porównuje stare działki z nowymi po numerze ewidencyjnym.
    Zwraca propozycje zmian literacji: [{stare_ozn, nowe_ozn, nr_ewid, pewnosc}]
    """
    propozycje = []

    # Zbuduj słownik: nr_ewid -> oznaczenie dla starych
    stare_mapa: dict[str, str] = {}
    for d in stare:
        for nr in d.numery_ewid:
            stare_mapa[nr] = d.oznaczenie

    # Sprawdź nowe działki
    for d_nowa in nowe_csv:
        for nr in d_nowa.numery_ewid:
            if nr in stare_mapa:
                stare_ozn = stare_mapa[nr]
                if stare_ozn != d_nowa.oznaczenie:
                    propozycje.append({
                        "stare_ozn": stare_ozn,
                        "nowe_ozn":  d_nowa.oznaczenie,
                        "nr_ewid":   nr,
                        "rok":       rok,
                        "pewnosc":   "wysoka",
                    })

    return propozycje
