"""
kalkulator_wypasu.py — model danych i logika kalkulatora obciążenia pastwiska
ZRSK 2023-2027, PS WPR
"""

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


# ── Współczynniki DJP (standard europejski, niezmienne) ───────────────────────

DJP: dict[str, float] = {
    "Krowy mleczne":              1.0,
    "Krowy mamki / mięsne":       0.8,
    "Buhaje":                     1.4,
    "Jałówki powyżej 2 lat":      0.8,
    "Jałówki 1–2 lata":           0.7,
    "Jałówki ½–1 rok":            0.3,
    "Cielęta do ½ roku":          0.15,
    "Konie (ogier, klacz)":       1.2,
    "Koniki polskie / hucuły":    0.6,
    "Źrebaki powyżej 2 lat":      1.0,
    "Źrebaki 1–2 lata":           0.8,
    "Źrebaki ½–1 rok":            0.5,
    "Źrebięta do ½ roku":         0.3,
    "Owce (tryki, maciorki)":     0.1,
    "Jarlaki owcze":              0.08,
    "Jagnięta do 3½ miesiąca":    0.05,
    "Kozy / jelenie / daniele":   0.15,
    "Inne zwierzęta trawożerne":  0.5,
}

GRUPY_DJP = list(DJP.keys())

# Miesiące sezonu pastwiskowego
MIESIACE = ["IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
MIESIACE_DNI = {"IV": 30, "V": 31, "VI": 30, "VII": 31,
                "VIII": 31, "IX": 30, "X": 31, "XI": 30}

# ── Limity per wariant ZRSK 2023-2027 ────────────────────────────────────────
# obsada_min, obsada_max [DJP/ha], obciazenie_max [DJP/ha], dni_sezonu

@dataclass
class LimitWypasu:
    obsada_min: float    # DJP/ha minimum
    obsada_max: float    # DJP/ha maksimum
    obciazenie_max: float  # DJP/ha max obciążenie
    dni_sezonu: int      # standardowy sezon
    opis: str            # opis wymagań

LIMITY_ZRSK: dict[str, LimitWypasu] = {
    "1.1": LimitWypasu(0.3, 1.0, 10.0, 168,
        "Wypas kośno-pastwiskowy po pokosie, do 15.10, obsada 0,3–1,0 DJP/ha"),
    "2.1": LimitWypasu(0.3, 1.0, 10.0, 168,
        "Wypas kośno-pastwiskowy po pokosie, do 15.10, obsada 0,3–1,0 DJP/ha"),
    "1.2": LimitWypasu(0.3, 0.5, 10.0, 45,
        "Wypas kośno-pastwiskowy po pokosie, 1.09–15.10, obsada do 0,5 DJP/ha"),
    "2.2": LimitWypasu(0.3, 0.5, 10.0, 45,
        "Wypas kośno-pastwiskowy po pokosie, 1.09–15.10, obsada do 0,5 DJP/ha"),
    "1.3": LimitWypasu(0.3, 1.0, 10.0, 168,
        "Wypas pastwiskowy 1.05–15.10, obsada 0,3–1,0 DJP/ha"),
    "2.3": LimitWypasu(0.3, 1.0, 10.0, 168,
        "Wypas pastwiskowy 1.05–15.10, obsada 0,3–1,0 DJP/ha"),
    "1.4": LimitWypasu(0.3, 0.5, 10.0, 90,
        "Wypas kośno-pastwiskowy po pokosie, 15.07–15.10, obsada do 0,5 DJP/ha"),
    "2.4": LimitWypasu(0.3, 0.5, 10.0, 90,
        "Wypas kośno-pastwiskowy po pokosie, 15.07–15.10, obsada do 0,5 DJP/ha"),
    "1.5": LimitWypasu(0.3, 1.0, 10.0, 90,
        "Wypas kośno-pastwiskowy po pokosie, do 15.10, obsada 0,3–1,0 DJP/ha"),
    "2.5": LimitWypasu(0.3, 1.0, 10.0, 90,
        "Wypas kośno-pastwiskowy po pokosie, do 15.10, obsada 0,3–1,0 DJP/ha"),
    "1.7": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "2.7": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "1.8": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "2.8": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "1.9": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "2.9": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "1.10": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "2.10": LimitWypasu(0.3, 0.5, 10.0, 60,
        "Wypas kośno-pastwiskowy po pokosie, obsada do 0,5 DJP/ha"),
    "3":   LimitWypasu(0.3, 1.5, 10.0, 168,
        "Wypas ekstensywny, obsada 0,3–1,5 DJP/ha, obciążenie do 10 DJP/ha"),
}

# Domyślny limit gdy wariant nieznany
LIMIT_DOMYSLNY = LimitWypasu(0.3, 1.5, 10.0, 168,
    "Ogólny limit ZRSK: obsada 0,3–1,5 DJP/ha, obciążenie do 10 DJP/ha")


# ── Model danych ──────────────────────────────────────────────────────────────

@dataclass
class GrupaZwierzat:
    """Jedna grupa zwierząt w planie wypasu."""
    gatunek: str          # np. "Krowy mleczne"
    liczba: int           # sztuki
    djp_wsp: float        # współczynnik DJP (domyślnie z tabeli, edytowalny)
    # Dni wypasu per miesiąc
    dni: dict[str, int] = field(default_factory=lambda: {m: 0 for m in MIESIACE})

    @property
    def djp_lacznie(self) -> float:
        """Łączna liczba DJP dla tej grupy."""
        return self.liczba * self.djp_wsp

    @property
    def dni_lacznie(self) -> int:
        return sum(self.dni.values())

    @property
    def punkty(self) -> float:
        """Suma punktów = szt × DJP × dni per miesiąc."""
        return sum(self.liczba * self.djp_wsp * d for d in self.dni.values())


@dataclass
class PlanWypasu:
    """Plan wypasu dla jednej działki rolnej w jednym sezonie."""
    id: str
    dzialka_ozn: str          # oznaczenie literowe
    dzialka_id: str
    wariant: str
    pow_ha: float
    rok_od: int               # rok początku planu
    rok_do: int               # rok końca planu (zazwyczaj +4)
    # Limity — domyślnie z rozporządzenia, edytowalne per działka
    obsada_min: float
    obsada_max: float
    obciazenie_max: float
    dni_sezonu: int
    # Stado planowane
    grupy: list[GrupaZwierzat] = field(default_factory=list)
    # Korekty planu
    korekty: list[dict] = field(default_factory=list)
    uwagi: str = ""
    data_opracowania: str = ""
    autor: str = ""

    @property
    def djp_lacznie(self) -> float:
        return sum(g.djp_lacznie for g in self.grupy)

    @property
    def obsada(self) -> float:
        """Obsada DJP/ha."""
        if self.pow_ha <= 0:
            return 0.0
        return round(self.djp_lacznie / self.pow_ha, 3)

    @property
    def punkty_lacznie(self) -> float:
        return sum(g.punkty for g in self.grupy)

    @property
    def obciazenie(self) -> float:
        """Obciążenie pastwiska DJP/ha."""
        if self.pow_ha <= 0 or self.dni_sezonu <= 0:
            return 0.0
        return round(self.punkty_lacznie / (self.pow_ha * self.dni_sezonu), 3)

    @property
    def status_obsady(self) -> str:
        """OK / NISKA / ZA_WYSOKA"""
        if self.obsada < self.obsada_min:
            return "NISKA"
        if self.obsada > self.obsada_max:
            return "ZA_WYSOKA"
        return "OK"

    @property
    def status_obciazenia(self) -> str:
        if self.obciazenie > self.obciazenie_max:
            return "ZA_WYSOKIE"
        return "OK"

    def rezerwa_obsady_pct(self) -> float:
        """% rezerwy do limitu maksymalnego obsady."""
        if self.obsada_max <= 0:
            return 0.0
        return round((1 - self.obsada / self.obsada_max) * 100, 1)

    def rezerwa_obciazenia_pct(self) -> float:
        if self.obciazenie_max <= 0:
            return 0.0
        return round((1 - self.obciazenie / self.obciazenie_max) * 100, 1)


# ── Symulacja: zmiana parametrów ─────────────────────────────────────────────

def symuluj_dni(plan: PlanWypasu, nowe_dni: int) -> tuple[float, float]:
    """
    Symuluje jak zmiana liczby dni sezonu wpływa na obciążenie.
    Zwraca (nowa_obsada, nowe_obciazenie).
    """
    if plan.pow_ha <= 0 or nowe_dni <= 0:
        return 0.0, 0.0
    obsada = plan.djp_lacznie / plan.pow_ha
    # Przelicz punkty z nową liczbą dni (proporcjonalnie)
    if plan.dni_sezonu > 0:
        wspolczynnik = nowe_dni / plan.dni_sezonu
        nowe_punkty = plan.punkty_lacznie * wspolczynnik
    else:
        nowe_punkty = 0.0
    obciazenie = nowe_punkty / (plan.pow_ha * nowe_dni)
    return round(obsada, 3), round(obciazenie, 3)


def symuluj_stado(plan: PlanWypasu, nowa_liczba_djp: float) -> tuple[float, float]:
    """
    Symuluje jak zmiana łącznej liczby DJP wpływa na obsadę i obciążenie.
    """
    if plan.pow_ha <= 0:
        return 0.0, 0.0
    obsada = nowa_liczba_djp / plan.pow_ha
    if plan.djp_lacznie > 0:
        wspolczynnik = nowa_liczba_djp / plan.djp_lacznie
        nowe_punkty = plan.punkty_lacznie * wspolczynnik
    else:
        nowe_punkty = nowa_liczba_djp * plan.dni_sezonu
    if plan.pow_ha > 0 and plan.dni_sezonu > 0:
        obciazenie = nowe_punkty / (plan.pow_ha * plan.dni_sezonu)
    else:
        obciazenie = 0.0
    return round(obsada, 3), round(obciazenie, 3)


def maks_zwierzat(plan: PlanWypasu, gatunek: str) -> int:
    """
    Oblicza maksymalną liczbę sztuk danego gatunku
    przy zachowaniu limitu obsady.
    """
    djp_wsp = DJP.get(gatunek, 0.5)
    if djp_wsp <= 0 or plan.pow_ha <= 0:
        return 0
    max_djp = plan.obsada_max * plan.pow_ha
    # Odejmij DJP innych grup
    djp_inne = sum(g.djp_lacznie for g in plan.grupy if g.gatunek != gatunek)
    dostepne_djp = max_djp - djp_inne
    return max(0, int(dostepne_djp / djp_wsp))


# ── Serializacja ──────────────────────────────────────────────────────────────

def plan_do_dict(plan: PlanWypasu) -> dict:
    d = asdict(plan)
    return d


def plan_z_dict(d: dict) -> PlanWypasu:
    grupy = [GrupaZwierzat(**g) for g in d.pop("grupy", [])]
    plan = PlanWypasu(**d)
    plan.grupy = grupy
    return plan


def get_limit(wariant: str) -> LimitWypasu:
    return LIMITY_ZRSK.get(wariant, LIMIT_DOMYSLNY)
