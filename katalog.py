"""
katalog.py — katalog zabiegów agrotechnicznych i wypasów
Rozszerzany automatycznie przy dodawaniu nowych wpisów
"""

# ── Zabiegi agrotechniczne — pogrupowane ─────────────────────────────────────

KATALOG_ZABIEGOW: dict[str, list[str]] = {
    "Koszenie": [
        "Koszenie całej powierzchni działki rolnej",
        "Koszenie z pozostawieniem stref niekoszonych (10%)",
        "Koszenie z pozostawieniem stref niekoszonych (20%)",
        "Koszenie pasowe",
        "Koszenie mozaikowe",
        "Koszenie ręczne lub kosą",
        "Koszenie od środka działki",
        "Koszenie od zewnątrz do środka działki",
    ],
    "Wypas": [
        "Wypas wolny",
        "Wypas kwaterowy",
        "Spasanie wiosenne",
        "Spasanie jesienne",
        "Wypas rotacyjny",
    ],
    "Nawożenie": [
        "Nawożenie obornikiem",
        "Nawożenie gnojówką",
        "Nawożenie gnojowicą",
        "Nawożenie kompostem",
        "Nawożenie mineralne (NPK)",
        "Nawożenie azotem",
        "Wapnowanie",
        "Stosowanie płynnych nawozów naturalnych metodą bezrozbryzgową",
        "Wymieszanie obornika z glebą w ciągu 12h",
    ],
    "Uprawki": [
        "Siew mieszanki traw/roślin",
        "Podsiew łąki",
        "Dosiewanie ubytków",
        "Wymieszanie słomy z glebą",
        "Uprawa konserwująca bezorkowa (strip-till)",
        "Siew międzyplonu ozimego",
        "Wsiewka śródplonowa",
        "Mulczowanie po 15.11",
    ],
    "Ochrona roślin": [
        "Zabieg środkiem ochrony roślin (herbicyd)",
        "Zabieg środkiem ochrony roślin (fungicyd)",
        "Zabieg środkiem ochrony roślin (insektycyd)",
        "Zabieg biologicznym środkiem ochrony roślin",
        "Usuwanie chwastów ręcznie/mechanicznie",
    ],
    "Inne": [
        "Usuwanie odrostów drzew i krzewów",
        "Usuwanie zakrzewień",
        "Utrzymanie rowów melioracyjnych",
        "Konserwacja urządzeń wodnych",
        "Retencjonowanie wody (spiętrzenie)",
        "Zbiór siana",
        "Zbiór biomasy",
        "Obserwacja i monitoring siedliska",
    ],
}

# Płaski słownik: nazwa → grupa (do wyszukiwania)
ZABIEGI_FLAT: dict[str, str] = {
    zabieg: grupa
    for grupa, zabiegi in KATALOG_ZABIEGOW.items()
    for zabieg in zabiegi
}

# Lista wszystkich zabiegów (posortowana alfabetycznie w grupach)
def wszystkie_zabiegi() -> list[str]:
    wynik = []
    for grupa, zabiegi in KATALOG_ZABIEGOW.items():
        wynik.extend(zabiegi)
    return wynik


# ── Gatunki zwierząt do wypasów ───────────────────────────────────────────────

GATUNKI_ZWIERZAT: list[str] = [
    "bydło – krowy",
    "bydło – jałówki",
    "bydło – buhaje",
    "bydło – cielęta",
    "owce",
    "kozy",
    "konie",
    "osły",
    "inne zwierzęta trawożerne",
]

# ── Rodzaje użytkowania ───────────────────────────────────────────────────────

RODZAJE_UZYTKOWANIA = [
    "kośne",
    "pastwiskowe",
    "kośno-pastwiskowe",
    "kośne z dopuszczonym wypasem",
    "spasanie wiosenne/jesienne",
]

# ── Symbole działań ───────────────────────────────────────────────────────────

SYMBOLE_DZIALAN: list[str] = [
    "ZRSK2327",
    "RE2327 PS",
    "PRSK1420",
    "E_MPW",
    "E_OPN",
    "E_USU",
    "E_WSG",
    "E_EKSTUZ",
    "E_ZSU",
    "E_OBR",
    "E_IPR",
    "E_MIOD",
    "E_RET",
    "E_BOU",
]


def dodaj_do_katalogu(czynnosc: str, grupa: str = "Inne") -> bool:
    """
    Dodaje nową czynność do katalogu jeśli jeszcze nie istnieje.
    Zwraca True jeśli dodano, False jeśli już istniała.
    """
    czynnosc = czynnosc.strip()
    if not czynnosc or czynnosc in ZABIEGI_FLAT:
        return False
    if grupa not in KATALOG_ZABIEGOW:
        KATALOG_ZABIEGOW[grupa] = []
    KATALOG_ZABIEGOW[grupa].append(czynnosc)
    ZABIEGI_FLAT[czynnosc] = grupa
    return True
