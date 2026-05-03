"""
app.py — Rejestr Działalności Rolnośrodowiskowej
Aplikacja Tkinter do prowadzenia rejestru zabiegów agrotechnicznych i wypasów
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))

from dane import (Gospodarstwo, DzialkaRolna, ZabiegAgrotechniczny, WpisWypasu,
                   zapisz, wczytaj, importuj_csv, dopasuj_zmiany_literacji, _nowy_id)
from katalog import (KATALOG_ZABIEGOW, wszystkie_zabiegi, GATUNKI_ZWIERZAT,
                      SYMBOLE_DZIALAN, dodaj_do_katalogu)
from dane import SPOSOBY_UZYTKOWANIA
from eksport import eksportuj_pdf
from walidacja import (waliduj_zabieg, waliduj_wpis_wypasu,
                        waliduj_caly_rejestr, komunikat_ostrzezenia)
from kalkulator_wypasu import (PlanWypasu, GrupaZwierzat, DJP, GRUPY_DJP,
                               MIESIACE, MIESIACE_DNI, LIMITY_ZRSK,
                               get_limit, symuluj_dni, symuluj_stado,
                               maks_zwierzat, plan_do_dict, plan_z_dict)
from dane import _nowy_id as _nowy_id_wypas
from eksport_wypasu import eksportuj_plan_wypasu

# ── Stałe wyglądu ─────────────────────────────────────────────────────────────
KOLOR_TLO     = "#F0F4F8"
KOLOR_NAV     = "#1F4E79"
KOLOR_AKCENT  = "#2E75B6"
KOLOR_SUKCES  = "#217346"
KOLOR_BLAD    = "#C00000"
KOLOR_WARN    = "#BF8F00"
KOLOR_GREEN   = "#375623"
CZCIONKA      = "Segoe UI"

# Globalne gospodarstwo
_gosp: Gospodarstwo | None = None
_plik_json: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _btn(parent, text, cmd, kolor=None, **kw):
    return tk.Button(parent, text=text, command=cmd, font=(CZCIONKA, 10),
                     relief=tk.FLAT, bg=kolor or KOLOR_AKCENT, fg="white",
                     padx=10, pady=4, activebackground=KOLOR_NAV,
                     cursor="hand2", **kw)


def _lbl(parent, text, bold=False, **kw):
    f = (CZCIONKA, 10, "bold") if bold else (CZCIONKA, 10)
    return tk.Label(parent, text=text, bg=KOLOR_TLO, font=f, **kw)



def _skroc_nr(nr: str) -> str:
    """Zwraca pełny numer działki ewidencyjnej (bez skracania)."""
    return nr if nr else ""

def _zapisz_auto():
    global _gosp, _plik_json
    if _gosp and _plik_json:
        zapisz(_gosp, _plik_json)



class DatePickerDialog(tk.Toplevel):
    """Prosty interaktywny kalendarz do wyboru daty."""
    def __init__(self, parent, current_date: str = ""):
        super().__init__(parent)
        self.title("Wybierz datę")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.wynik: str = current_date
        self._f = tk.Frame(self, bg=KOLOR_TLO)
        self._f.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        # Parsuj datę wejściową
        try:
            d = datetime.strptime(current_date.strip(), "%d.%m.%Y").date()
        except ValueError:
            d = date.today()
        self._rok  = d.year
        self._miesiac = d.month
        self._dzien   = d.day
        self._buduj()

    def _buduj(self):
        f = self._f
        # Nawigacja miesiąc/rok
        nav = tk.Frame(f, bg=KOLOR_TLO)
        nav.pack(fill=tk.X, pady=(0,6))
        _btn(nav, "◀", self._prev_miesiac, kolor=KOLOR_AKCENT).pack(side=tk.LEFT)
        self._lbl_miesiac = tk.Label(nav, text="", bg=KOLOR_TLO,
                                      font=(CZCIONKA, 11, "bold"), width=18)
        self._lbl_miesiac.pack(side=tk.LEFT, expand=True)
        _btn(nav, "▶", self._next_miesiac, kolor=KOLOR_AKCENT).pack(side=tk.RIGHT)

        # Siatka kalendarza
        self._grid_frame = tk.Frame(f, bg=KOLOR_TLO)
        self._grid_frame.pack()

        # Przyciski OK/Anuluj
        bf = tk.Frame(f, bg=KOLOR_TLO)
        bf.pack(pady=(6,0))
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.RIGHT, padx=4)

        self._rysuj_kalendarz()

    def _rysuj_kalendarz(self):
        for w in self._grid_frame.winfo_children():
            w.destroy()

        import calendar
        MIESACE_PL = ["","Styczeń","Luty","Marzec","Kwiecień","Maj","Czerwiec",
                       "Lipiec","Sierpień","Wrzesień","Październik","Listopad","Grudzień"]
        DNI_PL = ["Pon","Wto","Śro","Czw","Pią","Sob","Nie"]

        self._lbl_miesiac.config(
            text=f"{MIESACE_PL[self._miesiac]} {self._rok}")

        # Nagłówki dni
        for i, d in enumerate(DNI_PL):
            kol = "#E8F0F8" if i < 5 else "#FFE8E8"
            tk.Label(self._grid_frame, text=d, bg=kol,
                     font=(CZCIONKA, 9, "bold"), width=4,
                     relief=tk.FLAT).grid(row=0, column=i, padx=1, pady=1)

        cal = calendar.monthcalendar(self._rok, self._miesiac)
        today = date.today()

        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    tk.Label(self._grid_frame, text="", bg=KOLOR_TLO,
                             width=4).grid(row=row_idx+1, column=col_idx, padx=1, pady=1)
                else:
                    is_today    = (day == today.day and
                                   self._miesiac == today.month and
                                   self._rok == today.year)
                    is_selected = (day == self._dzien and
                                   self._miesiac == self._miesiac and
                                   self._rok == self._rok)
                    if day == self._dzien:
                        bg = KOLOR_NAV; fg = "white"; font_w = "bold"
                    elif is_today:
                        bg = "#D6E4F0"; fg = KOLOR_NAV; font_w = "bold"
                    elif col_idx >= 5:
                        bg = "#FFF5F5"; fg = "#CC4444"; font_w = "normal"
                    else:
                        bg = "white"; fg = "black"; font_w = "normal"

                    btn = tk.Button(self._grid_frame, text=str(day),
                                    bg=bg, fg=fg, font=(CZCIONKA, 9, font_w),
                                    width=4, relief=tk.FLAT, cursor="hand2",
                                    command=lambda d=day: self._wybierz(d))
                    btn.grid(row=row_idx+1, column=col_idx, padx=1, pady=1)

    def _prev_miesiac(self):
        if self._miesiac == 1:
            self._miesiac = 12; self._rok -= 1
        else:
            self._miesiac -= 1
        self._rysuj_kalendarz()

    def _next_miesiac(self):
        if self._miesiac == 12:
            self._miesiac = 1; self._rok += 1
        else:
            self._miesiac += 1
        self._rysuj_kalendarz()

    def _wybierz(self, dzien):
        self._dzien = dzien
        self.wynik = f"{dzien:02d}.{self._miesiac:02d}.{self._rok}"
        self.destroy()


def _pole_daty(parent, var: tk.StringVar, row: int, col: int,
               label_text: str, dialog_parent) -> tk.Entry:
    """Tworzy label + entry + przycisk kalendarza dla pola daty."""
    _lbl(parent, label_text).grid(row=row, column=col, padx=(16,4), pady=6, sticky="e")
    entry = tk.Entry(parent, textvariable=var, font=(CZCIONKA, 10), width=12)
    entry.grid(row=row, column=col+1, padx=(0,2), pady=6, sticky="w")

    def _otworz_kal():
        dlg = DatePickerDialog(dialog_parent, var.get())
        dialog_parent.wait_window(dlg)
        if dlg.wynik:
            var.set(dlg.wynik)

    tk.Button(parent, text="📅", command=_otworz_kal,
              font=(CZCIONKA, 9), relief=tk.FLAT, bg="#E8F0F8",
              cursor="hand2", padx=4).grid(row=row, column=col+2, padx=(0,8), pady=6)
    return entry

# ── Status bar ────────────────────────────────────────────────────────────────

class StatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=KOLOR_TLO, bd=1, relief=tk.SUNKEN)
        self.lbl = tk.Label(self, text="Gotowy.", anchor=tk.W,
                            bg=KOLOR_TLO, font=(CZCIONKA, 9))
        self.lbl.pack(fill=tk.X, padx=6, pady=2)

    def ustaw(self, tekst, kolor=None):
        self.lbl.config(text=tekst, fg=kolor or "black")
        self.update()


# ── Dialog: nowe/edytuj gospodarstwo ─────────────────────────────────────────

class DialogGospodarstwo(tk.Toplevel):
    def __init__(self, parent, gosp: Gospodarstwo | None = None):
        super().__init__(parent)
        self.update()
        self.title("Dane gospodarstwa")
        self.resizable(True, True)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.wynik: Gospodarstwo | None = None
        self._gosp = gosp
        self._buduj(gosp)
        self.geometry("620x520")

    def _buduj(self, gosp):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        nb = ttk.Notebook(self)
        nb.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        # ── Zakładka: Dane podstawowe ─────────────────────────────────────
        f1 = tk.Frame(nb, bg=KOLOR_TLO)
        nb.add(f1, text="  Dane podstawowe  ")

        pola = [
            ("Nazwa gospodarstwa:", "nazwa", gosp.nazwa if gosp else ""),
            ("Rolnik / zarządca:",  "rolnik", gosp.rolnik if gosp else ""),
            ("Nr identyfikacyjny:", "nr_id",  gosp.nr_identyfikacyjny if gosp else ""),
        ]
        self._vars = {}
        for i, (label, klucz, val) in enumerate(pola):
            _lbl(f1, label).grid(row=i, column=0, padx=(16,4), pady=10, sticky="e")
            var = tk.StringVar(value=val)
            self._vars[klucz] = var
            tk.Entry(f1, textvariable=var, font=(CZCIONKA, 10),
                     width=36).grid(row=i, column=1, padx=(0,16), pady=10, sticky="w")

        # ── Zakładka: Zobowiązania i warianty ─────────────────────────────
        f2 = tk.Frame(nb, bg=KOLOR_TLO)
        nb.add(f2, text="  Zobowiązania / warianty  ")
        f2.columnconfigure(0, weight=1)
        f2.rowconfigure(1, weight=1)

        tk.Label(f2, text="Lista pakietów/wariantów/praktyk realizowanych w gospodarstwie (pojawią się na stronie tytułowej rejestru):",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"),
                 fg="#555555", justify="left").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(10,4), sticky="w")

        # Lewa kolumna — lista obecnych wariantów
        lista_frame = tk.LabelFrame(f2, text="  Aktualne zobowiązania  ",
                                     bg=KOLOR_TLO, font=(CZCIONKA, 9, "bold"),
                                     fg=KOLOR_NAV, bd=2)
        lista_frame.grid(row=1, column=0, sticky="nsew", padx=(12,4), pady=4)
        lista_frame.rowconfigure(0, weight=1)
        lista_frame.columnconfigure(0, weight=1)

        self._lb_war = tk.Listbox(lista_frame, font=(CZCIONKA, 10),
                                   selectmode=tk.SINGLE, width=20, height=12,
                                   bg="white", bd=1, relief=tk.SOLID)
        vsb = ttk.Scrollbar(lista_frame, orient=tk.VERTICAL,
                             command=self._lb_war.yview)
        self._lb_war.configure(yscrollcommand=vsb.set)
        self._lb_war.grid(row=0, column=0, sticky="nsew", padx=(6,0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6, padx=(0,4))

        # Wstaw istniejące warianty
        for w in (gosp.warianty if gosp else []):
            self._lb_war.insert(tk.END, w)

        # Prawa kolumna — dodawanie nowych
        prawa = tk.Frame(f2, bg=KOLOR_TLO)
        prawa.grid(row=1, column=1, sticky="ns", padx=(4,12), pady=4)

        # Szybkie dodawanie z listy ZRSK
        tk.Label(prawa, text="Dodaj wariant ZRSK:",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "bold")).pack(anchor="w", pady=(8,2))
        from walidacja import REGULY_KOSZENIA
        warianty_zrsk = sorted(REGULY_KOSZENIA.keys(),
                                key=lambda x: [int(p) if p.isdigit() else p
                                               for p in x.replace(".", " ").split()])
        self._var_zrsk = tk.StringVar()
        ttk.Combobox(prawa, textvariable=self._var_zrsk,
                     values=warianty_zrsk, width=12,
                     state="readonly").pack(anchor="w", pady=(0,4))
        _btn(prawa, "➕ Dodaj ZRSK", self._dodaj_zrsk).pack(anchor="w", pady=(0,10))

        # Dodawanie innych (RE, ekoschematy itp.)
        tk.Label(prawa, text="Dodaj inne zobowiązanie:",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "bold")).pack(anchor="w", pady=(4,2))
        INNE = ["RE2327 PS", "PRSK1420", "E_EKSTUZ", "E_MPW", "E_OPN",
                "E_ZSU", "E_OBR", "E_USU", "E_WSG", "E_IPR", "E_MIOD",
                "E_RET", "E_BOU"]
        self._var_inne = tk.StringVar()
        ttk.Combobox(prawa, textvariable=self._var_inne,
                     values=INNE, width=16).pack(anchor="w", pady=(0,4))
        _btn(prawa, "➕ Dodaj", self._dodaj_inne).pack(anchor="w", pady=(0,10))

        # Własny wpis ręczny
        tk.Label(prawa, text="Wpisz ręcznie:",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "bold")).pack(anchor="w", pady=(4,2))
        self._var_reczny = tk.StringVar()
        tk.Entry(prawa, textvariable=self._var_reczny,
                 font=(CZCIONKA, 9), width=18).pack(anchor="w", pady=(0,4))
        _btn(prawa, "➕ Dodaj własny", self._dodaj_reczny).pack(anchor="w", pady=(0,16))

        # Usuń zaznaczony
        _btn(prawa, "🗑 Usuń zaznaczony", self._usun_wariant,
             kolor="#C00000").pack(anchor="w", pady=(0,4))
        _btn(prawa, "⬆ Przesuń wyżej", self._przesun_wyzej,
             kolor="#888888").pack(anchor="w", pady=(0,4))
        _btn(prawa, "⬇ Przesuń niżej", self._przesun_nizej,
             kolor="#888888").pack(anchor="w")

        # ── Przyciski główne ──────────────────────────────────────────────
        bf = tk.Frame(self, bg=KOLOR_TLO)
        bf.grid(row=1, column=0, pady=(4,12))
        _btn(bf, "✅ Zapisz", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

    def _dodaj_do_listy(self, val):
        val = val.strip()
        if not val:
            return
        obecne = list(self._lb_war.get(0, tk.END))
        if val not in obecne:
            self._lb_war.insert(tk.END, val)
            self._lb_war.see(tk.END)

    def _dodaj_zrsk(self):
        self._dodaj_do_listy(self._var_zrsk.get())

    def _dodaj_inne(self):
        self._dodaj_do_listy(self._var_inne.get())

    def _dodaj_reczny(self):
        self._dodaj_do_listy(self._var_reczny.get())
        self._var_reczny.set("")

    def _usun_wariant(self):
        sel = self._lb_war.curselection()
        if sel:
            self._lb_war.delete(sel[0])

    def _przesun_wyzej(self):
        sel = self._lb_war.curselection()
        if sel and sel[0] > 0:
            i = sel[0]
            val = self._lb_war.get(i)
            self._lb_war.delete(i)
            self._lb_war.insert(i - 1, val)
            self._lb_war.selection_set(i - 1)

    def _przesun_nizej(self):
        sel = self._lb_war.curselection()
        if sel and sel[0] < self._lb_war.size() - 1:
            i = sel[0]
            val = self._lb_war.get(i)
            self._lb_war.delete(i)
            self._lb_war.insert(i + 1, val)
            self._lb_war.selection_set(i + 1)

    def _ok(self):
        nazwa  = self._vars["nazwa"].get().strip()
        rolnik = self._vars["rolnik"].get().strip()
        nr     = self._vars["nr_id"].get().strip()
        if not nazwa or not rolnik:
            messagebox.showwarning("Brakuje danych", "Podaj nazwę i rolnika.", parent=self)
            return
        warianty = list(self._lb_war.get(0, tk.END))
        self.wynik = Gospodarstwo(nazwa=nazwa, rolnik=rolnik,
                                   nr_identyfikacyjny=nr,
                                   warianty=warianty)
        self.destroy()


# ── Dialog: zmiana literacji ──────────────────────────────────────────────────

class DialogLiteracja(tk.Toplevel):
    def __init__(self, parent, propozycje: list[dict]):
        super().__init__(parent)
        self.update()
        self.title("Propozycje zmian literacji działek")
        self.resizable(True, False)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.zatwierdzone: list[dict] = []
        self._vars = []
        self._buduj(propozycje)

    def _buduj(self, propozycje):
        tk.Label(self, text="Wykryto zmiany literacji — zaznacz które chcesz zastosować:",
                 bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"), fg=KOLOR_NAV).pack(
            padx=16, pady=(12,4))

        frame = tk.Frame(self, bg=KOLOR_TLO)
        frame.pack(padx=16, pady=4, fill=tk.X)

        nagl = ["", "Stare ozn.", "Nowe ozn.", "Nr działki ewid.", "Rok", "Pewność"]
        for c, h in enumerate(nagl):
            tk.Label(frame, text=h, bg=KOLOR_TLO, font=(CZCIONKA, 9, "bold"),
                     width=14 if c > 0 else 3).grid(row=0, column=c, padx=4, pady=2)

        for i, p in enumerate(propozycje):
            var = tk.BooleanVar(value=True)
            self._vars.append((var, p))
            tk.Checkbutton(frame, variable=var, bg=KOLOR_TLO).grid(row=i+1, column=0)
            for c, val in enumerate([p["stare_ozn"], p["nowe_ozn"],
                                       p["nr_ewid"], str(p["rok"]), p["pewnosc"]], 1):
                tk.Label(frame, text=val, bg=KOLOR_TLO,
                         font=(CZCIONKA, 9)).grid(row=i+1, column=c, padx=4)

        bf = tk.Frame(self, bg=KOLOR_TLO)
        bf.pack(pady=12)
        _btn(bf, "Zastosuj zaznaczone", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Pomiń wszystkie", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

    def _ok(self):
        self.zatwierdzone = [p for var, p in self._vars if var.get()]
        self.destroy()


# ── Zakładka: Działki ─────────────────────────────────────────────────────────

class ZakladkaDzialki(tk.Frame):
    def __init__(self, parent, status: StatusBar, on_change):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self.on_change = on_change
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._buduj()

    def _buduj(self):
        # Pasek narzędzi
        tb = tk.Frame(self, bg=KOLOR_TLO)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        _btn(tb, "📂 Importuj CSV ARiMR", self._importuj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "✏️ Edytuj zaznaczoną", self._edytuj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "➕ Dodaj ręcznie", self._dodaj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "🗑 Usuń zaznaczoną", self._usun, kolor="#C00000").pack(side=tk.LEFT)

        # Tabela działek
        cols = ("ozn", "uprawa", "sposob", "wariant", "symbol", "pow", "numery")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                  selectmode="browse")
        nagl = [("ozn","Ozn.",60), ("uprawa","Uprawa",120),
                ("sposob","Użytkowanie",150), ("wariant","Wariant",80),
                ("symbol","Symbol działania",140), ("pow","Pow.[ha]",80),
                ("numery","Nr działek ewid.",400)]
        for col, txt, w in nagl:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, minwidth=40)

        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12,0), pady=4)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        hsb.grid(row=2, column=0, sticky="ew", padx=12)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        info = tk.Label(self, text="💡 Zmień 'Użytkowanie' na pastwiskowe/kośno-pastwiskowe — działka trafi też do zakładki Wypasy",
                        bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"), fg="#555555")
        info.grid(row=3, column=0, sticky="w", padx=14, pady=(0,8))

    def odswiez(self):
        self.tree.delete(*self.tree.get_children())
        if not _gosp:
            return
        for d in sorted(_gosp.dzialki, key=lambda x: x.oznaczenie):
            numery = ", ".join(_skroc_nr(n) for n in d.numery_ewid[:3])
            if len(d.numery_ewid) > 3:
                numery += f" (+{len(d.numery_ewid)-3})"
            self.tree.insert("", tk.END, iid=d.id, values=(
                d.oznaczenie, d.uprawa, d.sposob_uzytkowania,
                d.wariant, d.symbol_dzialania,
                f"{d.pow_ha:.4f}".replace(".", ","), numery))

    def _zaznaczona(self) -> DzialkaRolna | None:
        sel = self.tree.selection()
        if not sel or not _gosp:
            return None
        return next((d for d in _gosp.dzialki if d.id == sel[0]), None)

    def _importuj(self):
        global _gosp
        if not _gosp:
            messagebox.showinfo("Brak gospodarstwa",
                                "Najpierw otwórz lub utwórz gospodarstwo.")
            return
        sciezka = filedialog.askopenfilename(
            title="Wybierz CSV z ARiMR",
            filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")])
        if not sciezka:
            return
        try:
            nowe, warianty = importuj_csv(sciezka)

            # Sprawdź zmiany literacji
            if _gosp.dzialki:
                rok = date.today().year
                propozycje = dopasuj_zmiany_literacji(_gosp.dzialki, nowe, rok)
                if propozycje:
                    dlg = DialogLiteracja(self, propozycje)
                    self.wait_window(dlg)
                    for p in dlg.zatwierdzone:
                        for d in _gosp.dzialki:
                            if d.oznaczenie == p["stare_ozn"]:
                                d.historia_oznaczen.append(p)
                                d.oznaczenie = p["nowe_ozn"]

            # Dodaj nowe działki (których jeszcze nie ma)
            istniejace_ozn = {d.oznaczenie for d in _gosp.dzialki}
            dodano = 0
            for d in nowe:
                if d.oznaczenie not in istniejace_ozn:
                    _gosp.dzialki.append(d)
                    dodano += 1
                else:
                    # Zaktualizuj numery i powierzchnię
                    istn = next(x for x in _gosp.dzialki
                                if x.oznaczenie == d.oznaczenie)
                    for nr in d.numery_ewid:
                        if nr not in istn.numery_ewid:
                            istn.numery_ewid.append(nr)
                    istn.pow_ha = d.pow_ha

            # Zaktualizuj warianty
            for w in warianty:
                if w not in _gosp.warianty:
                    _gosp.warianty.append(w)

            _gosp.ostatni_import_csv = sciezka
            _zapisz_auto()
            self.odswiez()
            self.on_change()
            self.status.ustaw(
                f"✅ Zaimportowano {len(nowe)} działek, dodano {dodano} nowych.",
                KOLOR_SUKCES)
        except Exception as e:
            messagebox.showerror("Błąd importu", str(e))

    def _dodaj(self):
        if not _gosp:
            return
        dlg = DialogDzialka(self)
        self.wait_window(dlg)
        if dlg.wynik:
            _gosp.dzialki.append(dlg.wynik)
            _zapisz_auto()
            self.odswiez()
            self.on_change()

    def _edytuj(self):
        d = self._zaznaczona()
        if not d:
            messagebox.showinfo("Brak wyboru", "Zaznacz działkę do edycji.")
            return
        dlg = DialogDzialka(self, d)
        self.wait_window(dlg)
        if dlg.wynik:
            idx = next(i for i, x in enumerate(_gosp.dzialki) if x.id == d.id)
            _gosp.dzialki[idx] = dlg.wynik
            _zapisz_auto()
            self.odswiez()
            self.on_change()

    def _usun(self):
        d = self._zaznaczona()
        if not d:
            return
        if messagebox.askyesno("Usuń", f"Usunąć działkę {d.oznaczenie}?"):
            _gosp.dzialki = [x for x in _gosp.dzialki if x.id != d.id]
            _zapisz_auto()
            self.odswiez()
            self.on_change()


# ── Dialog: edycja działki ────────────────────────────────────────────────────

class DialogDzialka(tk.Toplevel):
    def __init__(self, parent, dzialka: DzialkaRolna | None = None):
        super().__init__(parent)
        self.update()
        self.title("Działka rolna")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.wynik: DzialkaRolna | None = None
        self._d = dzialka
        self._buduj()

    def _buduj(self):
        d = self._d
        pola = [
            ("Oznaczenie (A, B…):", "ozn",    d.oznaczenie if d else ""),
            ("Uprawa:",              "uprawa", d.uprawa if d else "TUZ"),
            ("Pow. łączna [ha]:",    "pow",    str(d.pow_ha) if d else "0"),
            ("Wariant:",             "wariant",d.wariant if d else ""),
            ("Symbol działania:",    "symbol", d.symbol_dzialania if d else "ZRSK2327"),
            ("Uwagi:",               "uwagi",  d.uwagi if d else ""),
        ]
        self._vars = {}
        for i, (label, klucz, val) in enumerate(pola):
            _lbl(self, label).grid(row=i, column=0, padx=(16,4), pady=6, sticky="e")
            var = tk.StringVar(value=val)
            self._vars[klucz] = var
            if klucz == "symbol":
                cb = ttk.Combobox(self, textvariable=var,
                                   values=SYMBOLE_DZIALAN, width=28)
                cb.grid(row=i, column=1, padx=(0,16), pady=6, sticky="w")
            else:
                tk.Entry(self, textvariable=var, font=(CZCIONKA, 10),
                         width=30).grid(row=i, column=1, padx=(0,16), pady=6, sticky="w")

        # Sposób użytkowania
        r = len(pola)
        _lbl(self, "Użytkowanie TUZ:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_sposob = tk.StringVar(value=d.sposob_uzytkowania if d else "kośne")
        ttk.Combobox(self, textvariable=self._var_sposob,
                     values=SPOSOBY_UZYTKOWANIA, state="readonly",
                     width=28).grid(row=r, column=1, padx=(0,16), pady=6, sticky="w")

        # Numery ewidencyjne
        r += 1
        _lbl(self, "Nr ewid. (1 per wiersz):").grid(
            row=r, column=0, padx=(16,4), pady=6, sticky="ne")
        self._txt_numery = tk.Text(self, font=(CZCIONKA, 9), width=30, height=4)
        self._txt_numery.grid(row=r, column=1, padx=(0,16), pady=6, sticky="w")
        if d and d.numery_ewid:
            self._txt_numery.insert("1.0", "\n".join(d.numery_ewid))

        bf = tk.Frame(self, bg=KOLOR_TLO)
        bf.grid(row=r+1, column=0, columnspan=2, pady=12)
        _btn(bf, "Zapisz", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

    def _ok(self):
        ozn = self._vars["ozn"].get().strip().upper()
        if not ozn:
            messagebox.showwarning("Brak danych", "Podaj oznaczenie działki.", parent=self)
            return
        try:
            pow_ha = float(self._vars["pow"].get().replace(",", "."))
        except ValueError:
            pow_ha = 0.0
        numery = [n.strip() for n in
                  self._txt_numery.get("1.0", tk.END).strip().splitlines()
                  if n.strip()]
        self.wynik = DzialkaRolna(
            id=self._d.id if self._d else _nowy_id(),
            oznaczenie=ozn,
            uprawa=self._vars["uprawa"].get().strip(),
            sposob_uzytkowania=self._var_sposob.get(),
            wariant=self._vars["wariant"].get().strip(),
            symbol_dzialania=self._vars["symbol"].get().strip(),
            numery_ewid=numery,
            pow_ha=pow_ha,
            historia_oznaczen=self._d.historia_oznaczen if self._d else [],
            uwagi=self._vars["uwagi"].get().strip(),
        )
        self.destroy()



# ── Dialog: wpis grupowy (zabiegi i wypasy) ───────────────────────────────────

class DialogWpisGrupowy(tk.Toplevel):
    """
    Wpis grupowy — opcja C:
    Wiele zabiegów (każdy z datą + czynnością) × wiele działek.
    Każda działka ma checkboxy osobno dla każdego zabiegu.
    """
    def __init__(self, parent, gosp: Gospodarstwo, tryb: str = "zabieg"):
        super().__init__(parent)
        self.title("Wpis grupowy – zabiegi" if tryb == "zabieg"
                   else "Wpis grupowy – wypasy")
        self.resizable(True, True)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self._gosp = gosp
        self._tryb = tryb
        self.wyniki: list = []
        self._wiersze_dzialek: dict = {}   # {dzialka_id: {dzialka, pow_var, checks}}
        self._zabiegi_vars: list = []      # [{var_data, var_czyn, var_srodek, ...}]
        self._buduj()
        self.geometry("1020x740")

    def _buduj(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Panel górny: lista zabiegów ───────────────────────────────────────
        top_outer = tk.LabelFrame(self,
            text="  Zabiegi (dodaj wiersze klawiszem ➕)  ",
            bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"), fg=KOLOR_NAV, bd=2)
        top_outer.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        top_outer.columnconfigure(0, weight=1)

        # Nagłówki zabiegów
        hdr = tk.Frame(top_outer, bg="#E8F0F8")
        hdr.pack(fill=tk.X, padx=4, pady=(4,0))
        for c, (txt, w) in enumerate([
            ("#", 3), ("Data", 14), ("", 3),  # "" = przycisk kal
            ("Czynność / rodzaj zabiegu", 40),
            ("Środek/nawóz", 16), ("Ilość", 8),
            ("Symbol", 10), ("Wariant", 8), ("Uwagi", 14),
        ]):
            tk.Label(hdr, text=txt, bg="#E8F0F8",
                     font=(CZCIONKA, 9, "bold"), width=w, anchor="w").grid(
                row=0, column=c, padx=3, pady=3)
        if self._tryb == "zabieg":
            tk.Label(hdr, text="Użytkowanie", bg="#E8F0F8",
                     font=(CZCIONKA, 9, "bold"), width=14, anchor="w").grid(
                row=0, column=9, padx=3, pady=3)

        # Canvas dla wierszy zabiegów (scrollowany)
        canv_z = tk.Canvas(top_outer, bg=KOLOR_TLO,
                            highlightthickness=0, height=130)
        vsb_z  = ttk.Scrollbar(top_outer, orient=tk.VERTICAL, command=canv_z.yview)
        canv_z.configure(yscrollcommand=vsb_z.set)
        canv_z.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4,0), pady=4)
        vsb_z.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        self._zabiegi_frame = tk.Frame(canv_z, bg=KOLOR_TLO)
        cw_z = canv_z.create_window((0,0), window=self._zabiegi_frame, anchor="nw")

        def _cfg_z(e):
            canv_z.configure(scrollregion=canv_z.bbox("all"))
            canv_z.itemconfig(cw_z, width=canv_z.winfo_width())
        self._zabiegi_frame.bind("<Configure>", _cfg_z)
        canv_z.bind("<Configure>", lambda e: canv_z.itemconfig(cw_z, width=e.width))

        # Przyciski dodaj/usuń zabieg
        btn_z = tk.Frame(top_outer, bg=KOLOR_TLO)
        btn_z.pack(fill=tk.X, padx=4, pady=(0,4))
        _btn(btn_z, "➕ Dodaj zabieg", self._dodaj_zabieg_wiersz,
             kolor=KOLOR_GREEN).pack(side=tk.LEFT, padx=(0,6))
        _btn(btn_z, "🗑 Usuń ostatni", self._usun_ostatni_zabieg,
             kolor="#888888").pack(side=tk.LEFT)

        # Domyślny pierwszy wiersz
        self._dodaj_zabieg_wiersz()

        # ── Panel środkowy: lista działek × zabiegi ───────────────────────────
        mid = tk.LabelFrame(self,
            text="  Zaznacz działki dla każdego zabiegu  ",
            bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"), fg=KOLOR_GREEN, bd=2)
        mid.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(1, weight=1)

        # Nagłówki działek — dynamicznie przebudowywane
        self._nagl_frame = tk.Frame(mid, bg="#E8F0F8")
        self._nagl_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(4,0))

        # Canvas działek
        canv_d_frame = tk.Frame(mid, bg=KOLOR_TLO)
        canv_d_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        canv_d_frame.columnconfigure(0, weight=1)
        canv_d_frame.rowconfigure(0, weight=1)

        self._canv_d = tk.Canvas(canv_d_frame, bg=KOLOR_TLO, highlightthickness=0)
        vsb_d = ttk.Scrollbar(canv_d_frame, orient=tk.VERTICAL, command=self._canv_d.yview)
        hsb_d = ttk.Scrollbar(canv_d_frame, orient=tk.HORIZONTAL, command=self._canv_d.xview)
        self._canv_d.configure(yscrollcommand=vsb_d.set, xscrollcommand=hsb_d.set)
        self._canv_d.grid(row=0, column=0, sticky="nsew")
        vsb_d.grid(row=0, column=1, sticky="ns")
        hsb_d.grid(row=1, column=0, sticky="ew")

        self._lista_frame = tk.Frame(self._canv_d, bg=KOLOR_TLO)
        self._canv_win = self._canv_d.create_window(
            (0,0), window=self._lista_frame, anchor="nw")

        def _cfg_d(e):
            self._canv_d.configure(scrollregion=self._canv_d.bbox("all"))
            self._canv_d.itemconfig(self._canv_win,
                                     width=self._canv_d.winfo_width())
        self._lista_frame.bind("<Configure>", _cfg_d)
        self._canv_d.bind("<Configure>",
            lambda e: self._canv_d.itemconfig(self._canv_win, width=e.width))

        # Filtry
        filtr_frame = tk.Frame(mid, bg=KOLOR_TLO)
        filtr_frame.grid(row=2, column=0, sticky="w", padx=4, pady=(0,2))
        self._var_filtr = tk.StringVar(
            value="TUZ" if self._tryb == "zabieg" else "pastwiskowe")
        tk.Label(filtr_frame, text="Pokaż:", bg=KOLOR_TLO,
                 font=(CZCIONKA, 9)).pack(side=tk.LEFT, padx=(0,4))
        for txt, val in [("Wszystkie","all"), ("Tylko TUZ","TUZ"),
                          ("Kośne","kośne"), ("Pastwiskowe","pastwiskowe")]:
            tk.Radiobutton(filtr_frame, text=txt, variable=self._var_filtr,
                           value=val, bg=KOLOR_TLO, font=(CZCIONKA, 9),
                           command=self._odswiez_liste).pack(side=tk.LEFT, padx=4)
        tk.Label(filtr_frame, text="  Wariant:", bg=KOLOR_TLO,
                 font=(CZCIONKA, 9)).pack(side=tk.LEFT, padx=(12,4))
        warianty_gosp = sorted({d.wariant for d in self._gosp.dzialki if d.wariant})
        self._var_wariant_filtr = tk.StringVar(value="wszystkie")
        ttk.Combobox(filtr_frame, textvariable=self._var_wariant_filtr,
                     values=["wszystkie"] + warianty_gosp,
                     width=10, state="readonly").pack(side=tk.LEFT)
        self._var_wariant_filtr.trace_add("write", lambda *a: self._odswiez_liste())

        # Zaznacz/odznacz wszystkie
        btn_frame = tk.Frame(mid, bg=KOLOR_TLO)
        btn_frame.grid(row=3, column=0, sticky="w", padx=4, pady=(0,6))
        _btn(btn_frame, "☑ Zaznacz wszystkie zabiegi",
             self._zaznacz_wszystkie, kolor=KOLOR_AKCENT).pack(side=tk.LEFT, padx=(0,6))
        _btn(btn_frame, "☐ Odznacz wszystkie",
             self._odznacz_wszystkie, kolor="#888888").pack(side=tk.LEFT)

        # ── Przyciski główne ──────────────────────────────────────────────────
        bot = tk.Frame(self, bg=KOLOR_TLO)
        bot.grid(row=2, column=0, pady=(4,12))
        _btn(bot, "✅ Zapisz wszystkie wpisy", self._ok,
             kolor=KOLOR_NAV).pack(side=tk.LEFT, padx=(0,8))
        _btn(bot, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT)

        self._odswiez_liste()

    # ── Zarządzanie wierszami zabiegów ────────────────────────────────────────

    def _dodaj_zabieg_wiersz(self):
        """Dodaje nowy wiersz zabiegu do panelu górnego."""
        i = len(self._zabiegi_vars)
        kolory = ["#FFFFFF", "#F5F9FF"]
        bg = kolory[i % 2]

        f = tk.Frame(self._zabiegi_frame, bg=bg)
        f.pack(fill=tk.X, padx=2, pady=1)

        # Numer
        tk.Label(f, text=str(i+1), bg=bg,
                 font=(CZCIONKA, 9, "bold"), fg=KOLOR_NAV, width=3).grid(
            row=0, column=0, padx=4, pady=4)

        # Data z kalendarzem
        var_data = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        entry_data = tk.Entry(f, textvariable=var_data,
                               font=(CZCIONKA, 9), width=12)
        entry_data.grid(row=0, column=1, padx=(0,2), pady=4)

        def _kal(v=var_data):
            dlg = DatePickerDialog(self, v.get())
            self.wait_window(dlg)
            if dlg.wynik:
                v.set(dlg.wynik)
            if hasattr(self, '_nagl_frame'): self._odswiez_naglowki()

        tk.Button(f, text="📅", command=_kal,
                  font=(CZCIONKA, 9), relief=tk.FLAT,
                  bg="#E8F0F8", cursor="hand2", padx=3).grid(
            row=0, column=2, padx=(0,4), pady=4)

        # Czynność
        var_czyn = tk.StringVar()
        if self._tryb == "zabieg":
            cb = ttk.Combobox(f, textvariable=var_czyn,
                               values=wszystkie_zabiegi(), width=38)
        else:
            cb = tk.Entry(f, textvariable=var_czyn,
                          font=(CZCIONKA, 9), width=38)
        cb.grid(row=0, column=3, padx=(0,4), pady=4)
        var_czyn.trace_add("write", lambda *a: self._odswiez_naglowki() if hasattr(self, '_nagl_frame') else None)

        # Środek i ilość (tylko zabiegi)
        var_srodek = tk.StringVar(value="–")
        var_ilosc  = tk.StringVar(value="–")
        if self._tryb == "zabieg":
            tk.Entry(f, textvariable=var_srodek, font=(CZCIONKA, 9),
                     width=14).grid(row=0, column=4, padx=(0,4), pady=4)
            tk.Entry(f, textvariable=var_ilosc, font=(CZCIONKA, 9),
                     width=7).grid(row=0, column=5, padx=(0,4), pady=4)

        # Symbol i wariant
        var_symbol  = tk.StringVar(value="ZRSK2327")
        var_wariant = tk.StringVar(value="")
        ttk.Combobox(f, textvariable=var_symbol,
                     values=SYMBOLE_DZIALAN, width=10).grid(
            row=0, column=6, padx=(0,4), pady=4)
        tk.Entry(f, textvariable=var_wariant,
                 font=(CZCIONKA, 9), width=7).grid(
            row=0, column=7, padx=(0,4), pady=4)

        # Uwagi
        var_uwagi = tk.StringVar()
        tk.Entry(f, textvariable=var_uwagi,
                 font=(CZCIONKA, 9), width=12).grid(
            row=0, column=8, padx=(0,4), pady=4)

        # Użytkowanie (tylko zabiegi)
        var_uzytkowanie = tk.StringVar(value="kośne")
        if self._tryb == "zabieg":
            ttk.Combobox(f, textvariable=var_uzytkowanie,
                         values=["kośne","pastwiskowe","kośno-pastwiskowe",
                                 "kośne z dopuszczonym wypasem","inne"],
                         width=14, state="readonly").grid(
                row=0, column=9, padx=(0,6), pady=4)

        # Gatunek i liczba (tylko wypasy)
        var_gatunek = tk.StringVar()
        var_liczba  = tk.StringVar()
        if self._tryb == "wypas":
            ttk.Combobox(f, textvariable=var_gatunek,
                         values=GATUNKI_ZWIERZAT, width=20).grid(
                row=0, column=4, padx=(0,4), pady=4)
            tk.Entry(f, textvariable=var_liczba,
                     font=(CZCIONKA, 9), width=12).grid(
                row=0, column=5, padx=(0,4), pady=4)

        self._zabiegi_vars.append({
            "frame":        f,
            "var_data":     var_data,
            "var_czyn":     var_czyn,
            "var_srodek":   var_srodek,
            "var_ilosc":    var_ilosc,
            "var_symbol":   var_symbol,
            "var_wariant":  var_wariant,
            "var_uwagi":    var_uwagi,
            "var_uzytkowanie": var_uzytkowanie,
            "var_gatunek":  var_gatunek,
            "var_liczba":   var_liczba,
        })

        # Przebuduj checkboxy działek — tylko jeśli panele już istnieją
        if hasattr(self, '_lista_frame') and hasattr(self, '_nagl_frame'):
            self._odswiez_liste()
            if hasattr(self, '_nagl_frame'): self._odswiez_naglowki()

    def _usun_ostatni_zabieg(self):
        if len(self._zabiegi_vars) <= 1:
            return
        last = self._zabiegi_vars.pop()
        last["frame"].destroy()
        self._odswiez_liste()
        self._odswiez_naglowki()

    def _odswiez_naglowki(self):
        """Odświeża nagłówki kolumn zabiegów w liście działek."""
        for w in self._nagl_frame.winfo_children():
            w.destroy()
        # Stałe kolumny — szerokości muszą odpowiadać _odswiez_liste
        for c, (txt, w) in enumerate([
            ("Dz.", 4), ("Uprawa", 10), ("War.", 6), ("Pow.[ha]", 8), ("Nr ewid.", 20)
        ]):
            tk.Label(self._nagl_frame, text=txt, bg="#E8F0F8",
                     font=(CZCIONKA, 9, "bold"), width=w,
                     anchor="center").grid(row=0, column=c, padx=2, pady=3)
        # Kolumny per zabieg — stała szerokość 90px
        COL_W = 90
        for j, zv in enumerate(self._zabiegi_vars):
            data = zv["var_data"].get()
            czyn = zv["var_czyn"].get()
            czyn_kr = czyn[:14]+"…" if len(czyn)>14 else czyn
            label = f"Z{j+1} {data}\n{czyn_kr}"
            lbl = tk.Label(self._nagl_frame, text=label, bg="#D6E4F0",
                     font=(CZCIONKA, 8, "bold"),
                     wraplength=86, justify="center", anchor="center")
            lbl.grid(row=0, column=5+j, padx=0, pady=2, sticky="ew")
            self._nagl_frame.columnconfigure(5+j, minsize=COL_W)
    # ── Lista działek ─────────────────────────────────────────────────────────

    def _filtruj_dzialki(self):
        filtr = self._var_filtr.get()
        dzialki = self._gosp.dzialki
        if filtr == "TUZ":
            dzialki = [d for d in dzialki if "TUZ" in d.uprawa.upper()]
        elif filtr == "kośne":
            dzialki = [d for d in dzialki if "kośne" in d.sposob_uzytkowania]
        elif filtr == "pastwiskowe":
            dzialki = [d for d in dzialki
                       if any(s in d.sposob_uzytkowania
                              for s in ["pastwiskowe", "kośno-pastwiskowe"])]
        war = getattr(self, "_var_wariant_filtr", None)
        if war and war.get() != "wszystkie":
            dzialki = [d for d in dzialki if d.wariant == war.get()]
        return dzialki

    def _odswiez_liste(self):
        # Zapamiętaj aktualne zaznaczenia przed przebudową
        stan = {
            d_id: [c.get() for c in wd["checks"]]
            for d_id, wd in self._wiersze_dzialek.items()
        }

        for w in self._lista_frame.winfo_children():
            w.destroy()
        self._wiersze_dzialek.clear()

        dzialki = sorted(self._filtruj_dzialki(), key=lambda d: d.oznaczenie)
        kolory  = ["#FFFFFF", "#F5F9FF"]
        n_zab   = len(self._zabiegi_vars)

        # Szerokości kolumn checkboxów — takie same jak w nagłówkach
        CB_W = 12

        for i, d in enumerate(dzialki):
            bg = kolory[i % 2]
            f  = tk.Frame(self._lista_frame, bg=bg)
            f.pack(fill=tk.X, padx=2, pady=1)

            # Oznaczenie
            tk.Label(f, text=d.oznaczenie, bg=bg,
                     font=(CZCIONKA, 10, "bold"), fg=KOLOR_NAV,
                     width=4, anchor="center").grid(row=0, column=0, padx=3, pady=3)
            # Uprawa
            tk.Label(f, text=d.uprawa[:10], bg=bg,
                     font=(CZCIONKA, 9), width=10, anchor="w").grid(
                row=0, column=1, padx=2)
            # Wariant — nowa kolumna (pkt 2)
            war_txt = d.wariant or "–"
            tk.Label(f, text=war_txt, bg=bg,
                     font=(CZCIONKA, 9, "bold"), fg=KOLOR_GREEN,
                     width=6, anchor="center").grid(row=0, column=2, padx=2)
            # Pow łączna
            pow_var = tk.StringVar(value=f"{d.pow_ha:.2f}".replace(".",","))
            tk.Entry(f, textvariable=pow_var, font=(CZCIONKA, 9),
                     width=8, justify="right", bg="#EBF3FB").grid(
                row=0, column=3, padx=2, pady=3)
            # Nr ewid
            numery_txt = "  ".join(d.numery_ewid) if d.numery_ewid else "—"
            tk.Label(f, text=numery_txt, bg=bg,
                     font=(CZCIONKA, 8), anchor="w", width=20).grid(
                row=0, column=4, padx=3)

            # Checkboxy per zabieg — kolumna tej samej szerokości co nagłówek
            COL_W = 90
            checks = []
            poprzednie = stan.get(d.id, [])
            for j in range(n_zab):
                prev_val = poprzednie[j] if j < len(poprzednie) else False
                var_c = tk.BooleanVar(value=prev_val)
                cb = tk.Checkbutton(f, variable=var_c, bg=bg,
                                    activebackground=bg)
                cb.grid(row=0, column=5+j, pady=3, sticky="")
                f.columnconfigure(5+j, minsize=COL_W)
                checks.append(var_c)

            self._wiersze_dzialek[d.id] = {
                "dzialka": d,
                "pow_var": pow_var,
                "checks":  checks,
            }

    def _zaznacz_wszystkie(self):
        for w in self._wiersze_dzialek.values():
            for c in w["checks"]:
                c.set(True)

    def _odznacz_wszystkie(self):
        for w in self._wiersze_dzialek.values():
            for c in w["checks"]:
                c.set(False)

    # ── Zapis ─────────────────────────────────────────────────────────────────

    def _ok(self):
        from walidacja import _parse_date as _pd
        from collections import defaultdict

        # Waliduj zabiegi
        for j, zv in enumerate(self._zabiegi_vars):
            data = zv["var_data"].get().strip()
            czyn = zv["var_czyn"].get().strip() if self._tryb == "zabieg" else ""
            if not data:
                messagebox.showwarning("Brak danych",
                    f"Zabieg {j+1}: podaj datę.", parent=self)
                return
            if self._tryb == "zabieg" and not czyn:
                messagebox.showwarning("Brak danych",
                    f"Zabieg {j+1}: podaj czynność.", parent=self)
                return

        # Zbierz zaznaczenia i buduj rekordy
        ostrzezenia_all = []
        zabiegi_gosp = list(self._gosp.zabiegi if self._tryb == "zabieg"
                            else self._gosp.wypasy)

        for d_id, wd in self._wiersze_dzialek.items():
            dzialka = wd["dzialka"]
            try:
                pow_ha = float(wd["pow_var"].get().replace(",", "."))
            except ValueError:
                pow_ha = dzialka.pow_ha

            for j, (zv, check_var) in enumerate(
                    zip(self._zabiegi_vars, wd["checks"])):
                if not check_var.get():
                    continue

                data    = zv["var_data"].get().strip()
                symbol  = zv["var_symbol"].get().strip()
                uwagi   = zv["var_uwagi"].get().strip()
                war     = zv["var_wariant"].get().strip() or dzialka.wariant

                numery  = dzialka.numery_ewid if dzialka.numery_ewid else [""]

                for nr in numery:
                    pow_nr = (dzialka.pow_ewid.get(nr, pow_ha)
                              if nr and dzialka.pow_ewid else pow_ha)

                    if self._tryb == "zabieg":
                        czyn    = zv["var_czyn"].get().strip()
                        srodek  = zv["var_srodek"].get().strip()
                        ilosc   = zv["var_ilosc"].get().strip()
                        uzytkow = zv["var_uzytkowanie"].get()
                        dodaj_do_katalogu(czyn)
                        self.wyniki.append(ZabiegAgrotechniczny(
                            id=_nowy_id(),
                            dzialka_id=dzialka.id,
                            oznaczenie=dzialka.oznaczenie,
                            nr_ewid=nr, data=data, pow_ha=pow_nr,
                            rodzaj_uzytkowania=uzytkow,
                            czynnosc=czyn, srodek=srodek, ilosc=ilosc,
                            symbol_dzialania=symbol, wariant=war,
                            uwagi=uwagi,
                        ))
                    else:
                        gatunek = zv["var_gatunek"].get().strip()
                        liczba  = zv["var_liczba"].get().strip()
                        self.wyniki.append(WpisWypasu(
                            id=_nowy_id(),
                            dzialka_id=dzialka.id,
                            oznaczenie=dzialka.oznaczenie,
                            nr_ewid=nr, data=data, pow_ha=pow_nr,
                            gatunek=gatunek, liczba=liczba,
                            symbol_dzialania=symbol, wariant=war,
                            uwagi=uwagi,
                        ))

        if not self.wyniki:
            messagebox.showwarning("Brak wyboru",
                "Zaznacz co najmniej jedną działkę dla co najmniej jednego zabiegu.",
                parent=self)
            return

        # Walidacja ostrzeżeń (zebranych)
        from walidacja import (waliduj_zabieg, waliduj_wpis_wypasu,
                                komunikat_ostrzezenia)
        dzialki_map = {d.id: d for d in self._gosp.dzialki}
        zabiegi_per = defaultdict(list)
        for z in zabiegi_gosp:
            dd = _pd(z.data)
            if dd: zabiegi_per[(z.dzialka_id, dd.year)].append(z)

        ost_all = []
        seen = set()
        for wpis in self.wyniki:
            dzialka = dzialki_map.get(wpis.dzialka_id)
            wariant = dzialka.wariant if dzialka else ""
            uwagi_dz = dzialka.uwagi if dzialka else ""
            dd = _pd(wpis.data)
            rok = dd.year if dd else 0
            if self._tryb == "zabieg":
                inne = zabiegi_per.get((wpis.dzialka_id, rok), [])
                ost = waliduj_zabieg(wpis.oznaczenie, wpis.nr_ewid, wariant,
                                      wpis.data, wpis.czynnosc, inne, uwagi_dz)
            else:
                ost = waliduj_wpis_wypasu(wpis.oznaczenie, wpis.nr_ewid,
                                           wariant, wpis.data, uwagi_dz)
            for o in ost:
                key = (wpis.dzialka_id, wpis.data,
                       getattr(wpis,'czynnosc',''), o.komunikat)
                if key not in seen:
                    seen.add(key)
                    ost_all.append(o)

        if ost_all:
            if not messagebox.askyesno("⚠️ Ostrzeżenie",
                                        komunikat_ostrzezenia(ost_all),
                                        parent=self):
                self.wyniki.clear()
                return

        self.destroy()



# ── Zakładka: Zabiegi agrotechniczne ─────────────────────────────────────────

class ZakladkaZabiegi(tk.Frame):
    def __init__(self, parent, status: StatusBar):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._buduj()

    def _buduj(self):
        tb = tk.Frame(self, bg=KOLOR_TLO)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        _btn(tb, "➕ Dodaj zabieg", self._dodaj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "➕ Dodaj wypas", self._dodaj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "📋 Wpis grupowy", self._dodaj_grupowo, kolor=KOLOR_GREEN).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "✏️ Edytuj", self._edytuj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "🗑 Usuń", self._usun, kolor="#C00000").pack(side=tk.LEFT, padx=(0,12))
        tk.Label(tb, text="Filtruj rok:", bg=KOLOR_TLO,
                 font=(CZCIONKA, 9)).pack(side=tk.LEFT, padx=(8,2))
        self._var_rok = tk.StringVar(value="wszystkie")
        self._cb_rok = ttk.Combobox(tb, textvariable=self._var_rok,
                                     values=["wszystkie"] + [str(r) for r in
                                             range(date.today().year, 2022, -1)],
                                     width=10, state="readonly")
        self._cb_rok.pack(side=tk.LEFT)
        self._cb_rok.bind("<<ComboboxSelected>>", lambda e: self.odswiez())

        cols = ("ozn","nr_ewid","data","pow","uzytkowanie","czynnosc",
                "srodek","ilosc","symbol","wariant","uwagi")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                  selectmode="browse")
        nagl = [("ozn","Ozn.",50),("nr_ewid","Nr ewid.",160),
                ("data","Data",90),("pow","Pow.[ha]",70),
                ("uzytkowanie","Użytkowanie",110),
                ("czynnosc","Czynność",200),("srodek","Środek/nawóz",110),
                ("ilosc","Ilość",70),("symbol","Symbol",90),
                ("wariant","Wariant",70),("uwagi","Uwagi",150)]
        for col, txt, w in nagl:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, minwidth=40)

        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12,0), pady=4)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        hsb.grid(row=2, column=0, sticky="ew", padx=12)
        self.rowconfigure(1, weight=1)

        self.lbl_count = tk.Label(self, text="", bg=KOLOR_TLO,
                                   font=(CZCIONKA, 9, "italic"), fg="#555555")
        self.lbl_count.grid(row=3, column=0, sticky="w", padx=14, pady=(0,6))

    def odswiez(self):
        self.tree.delete(*self.tree.get_children())
        if not _gosp:
            return
        rok_filtr = self._var_rok.get()
        zabiegi = _gosp.zabiegi
        if rok_filtr != "wszystkie":
            zabiegi = [z for z in zabiegi if z.data.endswith(rok_filtr)]
        zabiegi = sorted(zabiegi, key=lambda x: (x.data[6:], x.data[3:5], x.data[:2]))
        for z in zabiegi:
            self.tree.insert("", tk.END, iid=z.id, values=(
                z.oznaczenie, z.nr_ewid, z.data,
                f"{z.pow_ha:.2f}".replace(".",","),
                z.rodzaj_uzytkowania, z.czynnosc,
                z.srodek or "–", z.ilosc or "–",
                z.symbol_dzialania,
                getattr(z, "wariant", "") or "–",
                z.uwagi))
        self.lbl_count.config(text=f"Wpisów: {len(zabiegi)}")

    def _zaznaczony(self) -> ZabiegAgrotechniczny | None:
        sel = self.tree.selection()
        if not sel or not _gosp:
            return None
        return next((z for z in _gosp.zabiegi if z.id == sel[0]), None)

    def _dodaj(self):
        if not _gosp or not _gosp.dzialki:
            messagebox.showinfo("Brak działek", "Najpierw zaimportuj lub dodaj działki.")
            return
        dlg = DialogZabieg(self, gosp=_gosp)
        self.wait_window(dlg)
        if dlg.wynik:
            _gosp.zabiegi.append(dlg.wynik)
            _zapisz_auto()
            self.odswiez()
            self.status.ustaw("✅ Dodano zabieg.", KOLOR_SUKCES)

    def _dodaj_grupowo(self):
        if not _gosp or not _gosp.dzialki:
            messagebox.showinfo("Brak działek", "Najpierw zaimportuj lub dodaj działki.")
            return
        dlg = DialogWpisGrupowy(self, _gosp, tryb="zabieg")
        self.wait_window(dlg)
        if dlg.wyniki:
            _gosp.zabiegi.extend(dlg.wyniki)
            _zapisz_auto()
            self.odswiez()
            n = len(dlg.wyniki)
            self.status.ustaw(f"✅ Dodano {n} wpisów zabiegów.", KOLOR_SUKCES)

    def _edytuj(self):
        z = self._zaznaczony()
        if not z:
            messagebox.showinfo("Brak wyboru", "Zaznacz wpis do edycji.")
            return
        dlg = DialogZabieg(self, gosp=_gosp, zabieg=z)
        self.wait_window(dlg)
        if dlg.wynik:
            idx = next(i for i, x in enumerate(_gosp.zabiegi) if x.id == z.id)
            _gosp.zabiegi[idx] = dlg.wynik
            _zapisz_auto()
            self.odswiez()

    def _usun(self):
        z = self._zaznaczony()
        if not z:
            return
        if messagebox.askyesno("Usuń", f"Usunąć wpis z {z.data}?"):
            _gosp.zabiegi = [x for x in _gosp.zabiegi if x.id != z.id]
            _zapisz_auto()
            self.odswiez()


# ── Dialog: zabieg agrotechniczny ─────────────────────────────────────────────

class DialogZabieg(tk.Toplevel):
    def __init__(self, parent, gosp: Gospodarstwo,
                 zabieg: ZabiegAgrotechniczny | None = None):
        super().__init__(parent)
        self.update()
        self.title("Zabieg agrotechniczny")
        self.resizable(False, False)
        self.configure(bg=KOLOR_TLO)
        self.wynik: ZabiegAgrotechniczny | None = None
        self._gosp = gosp
        self._z = zabieg
        self.update()
        self._buduj()
        self.grab_set()

    def _buduj(self):
        z = self._z
        # Słownik działek: oznaczenie -> (id, numery_ewid, pow, sposob, symbol)
        self._dzialki_map = {d.oznaczenie: d for d in self._gosp.dzialki}
        ozn_lista = sorted(self._dzialki_map.keys())

        r = 0
        # Działka
        _lbl(self, "Działka (ozn.):").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_ozn = tk.StringVar(value=z.oznaczenie if z else (ozn_lista[0] if ozn_lista else ""))
        cb_ozn = ttk.Combobox(self, textvariable=self._var_ozn,
                               values=ozn_lista, width=10, state="readonly")
        cb_ozn.grid(row=r, column=1, padx=(0,4), pady=6, sticky="w")
        cb_ozn.bind("<<ComboboxSelected>>", self._on_dzialka_change)

        # Nr ewidencyjny
        _lbl(self, "Nr ewid.:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_nr = tk.StringVar(value=z.nr_ewid if z else "")
        self._cb_nr = ttk.Combobox(self, textvariable=self._var_nr, width=22)
        self._cb_nr.grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Data z kalendarzem
        self._var_data = tk.StringVar(
            value=z.data if z else date.today().strftime("%d.%m.%Y"))
        _pole_daty(self, self._var_data, r, 0, "Data:", self)

        # Powierzchnia
        _lbl(self, "Pow. [ha]:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_pow = tk.StringVar(value=str(z.pow_ha).replace(".", ",") if z else "")
        tk.Entry(self, textvariable=self._var_pow, font=(CZCIONKA, 10),
                 width=10).grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Rodzaj użytkowania
        _lbl(self, "Rodzaj użytkowania:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_uzytkowanie = tk.StringVar(value=z.rodzaj_uzytkowania if z else "kośne")
        ttk.Combobox(self, textvariable=self._var_uzytkowanie,
                     values=["kośne", "pastwiskowe", "kośno-pastwiskowe",
                             "kośne z dopuszczonym wypasem", "inne"],
                     width=22, state="readonly").grid(
            row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Czynność — z katalogu lub własna
        _lbl(self, "Czynność:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_czyn = tk.StringVar(value=z.czynnosc if z else "")
        cb_czyn = ttk.Combobox(self, textvariable=self._var_czyn,
                                values=wszystkie_zabiegi(), width=40)
        cb_czyn.grid(row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Środek i ilość
        _lbl(self, "Środek/nawóz:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_srodek = tk.StringVar(value=z.srodek if z else "–")
        tk.Entry(self, textvariable=self._var_srodek, font=(CZCIONKA, 10),
                 width=22).grid(row=r, column=1, padx=(0,4), pady=6, sticky="w")
        _lbl(self, "Ilość:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_ilosc = tk.StringVar(value=z.ilosc if z else "–")
        tk.Entry(self, textvariable=self._var_ilosc, font=(CZCIONKA, 10),
                 width=14).grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Symbol działania
        _lbl(self, "Symbol działania:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_symbol = tk.StringVar(value=z.symbol_dzialania if z else "ZRSK2327")
        ttk.Combobox(self, textvariable=self._var_symbol,
                     values=SYMBOLE_DZIALAN, width=22).grid(
            row=r, column=1, padx=(0,4), pady=6, sticky="w")
        _lbl(self, "Wariant/pakiet:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_wariant = tk.StringVar(value=z.wariant if z else "")
        tk.Entry(self, textvariable=self._var_wariant, font=(CZCIONKA, 10),
                 width=10).grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        # Uwagi
        _lbl(self, "Uwagi:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="ne")
        self._txt_uwagi = tk.Text(self, font=(CZCIONKA, 9), width=46, height=3)
        self._txt_uwagi.grid(row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        if z and z.uwagi:
            self._txt_uwagi.insert("1.0", z.uwagi)
        r += 1

        bf = tk.Frame(self, bg=KOLOR_TLO)
        bf.grid(row=r, column=0, columnspan=4, pady=12)
        _btn(bf, "Zapisz", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

        # Inicjalizuj listę numerów
        self._on_dzialka_change()

    def _on_dzialka_change(self, event=None):
        ozn = self._var_ozn.get()
        d = self._dzialki_map.get(ozn)
        if d:
            self._cb_nr["values"] = d.numery_ewid
            if d.numery_ewid and not self._var_nr.get():
                self._var_nr.set(d.numery_ewid[0])
            if not self._z:
                self._var_symbol.set(d.symbol_dzialania)
                self._var_wariant.set(d.wariant)
                self._var_uzytkowanie.set(
                    "kośne" if "kośne" in d.sposob_uzytkowania else d.sposob_uzytkowania)
            self._aktualizuj_pow_ewid()

    def _aktualizuj_pow_ewid(self, event=None):
        ozn = self._var_ozn.get()
        d   = self._dzialki_map.get(ozn)
        if d:
            # Pokaż numery bez kodu gminy, zgrupowane
            skrocone = " | ".join(d.numery_ewid)
            self._var_nr.set(skrocone)
            self._var_pow.set(f"{d.pow_ha:.4f}".replace(".", ","))

    def _ok(self):
        ozn = self._var_ozn.get().strip()
        nr = self._var_nr.get().strip()
        data = self._var_data.get().strip()
        czyn = self._var_czyn.get().strip()
        if not ozn or not data or not czyn:
            messagebox.showwarning("Brak danych",
                                   "Podaj oznaczenie, datę i czynność.", parent=self)
            return
        # Dodaj do katalogu jeśli nowa czynność
        dodaj_do_katalogu(czyn)
        try:
            pow_ha = float(self._var_pow.get().replace(",", "."))
        except ValueError:
            pow_ha = 0.0
        d = self._dzialki_map.get(ozn)
        nowy_wpis = ZabiegAgrotechniczny(
            id=self._z.id if self._z else _nowy_id(),
            dzialka_id=d.id if d else "",
            oznaczenie=ozn,
            nr_ewid=nr,
            data=data,
            pow_ha=pow_ha,
            rodzaj_uzytkowania=self._var_uzytkowanie.get(),
            czynnosc=czyn,
            srodek=self._var_srodek.get().strip(),
            ilosc=self._var_ilosc.get().strip(),
            symbol_dzialania=self._var_symbol.get().strip(),
            wariant=self._var_wariant.get().strip(),
            uwagi=self._txt_uwagi.get("1.0", tk.END).strip(),
        )
        # Walidacja
        from walidacja import _parse_date as _pd
        dd = _pd(data)
        rok = dd.year if dd else 0
        inne = [z for z in self._gosp.zabiegi
                if z.dzialka_id == nowy_wpis.dzialka_id
                and z.id != nowy_wpis.id
                and _pd(z.data) and _pd(z.data).year == rok]
        ost = waliduj_zabieg(ozn, nr.split(".")[0] if "." in nr else nr,
                              d.wariant if d else "",
                              data, czyn, inne, d.uwagi if d else "")
        if ost:
            if not messagebox.askyesno("⚠️ Ostrzeżenie",
                                        komunikat_ostrzezenia(ost), parent=self):
                return
        self.wynik = nowy_wpis
        self.destroy()


# ── Zakładka: Wypasy ──────────────────────────────────────────────────────────

class ZakladkaWypasy(tk.Frame):
    def __init__(self, parent, status: StatusBar):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._buduj()

    def _buduj(self):
        tb = tk.Frame(self, bg=KOLOR_TLO)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        _btn(tb, "➕ Dodaj wypas", self._dodaj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "📋 Wpis grupowy", self._dodaj_grupowo, kolor=KOLOR_GREEN).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "✏️ Edytuj", self._edytuj).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "🗑 Usuń", self._usun, kolor="#C00000").pack(side=tk.LEFT, padx=(0,12))
        tk.Label(tb, text="Filtruj rok:", bg=KOLOR_TLO,
                 font=(CZCIONKA, 9)).pack(side=tk.LEFT, padx=(8,2))
        self._var_rok = tk.StringVar(value="wszystkie")
        ttk.Combobox(tb, textvariable=self._var_rok,
                     values=["wszystkie"] + [str(r) for r in
                             range(date.today().year, 2022, -1)],
                     width=10, state="readonly").pack(side=tk.LEFT)
        self._var_rok.trace_add("write", lambda *a: self.odswiez())

        cols = ("ozn","nr_ewid","data","pow","gatunek","liczba","symbol","wariant","uwagi")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                  selectmode="browse")
        nagl = [("ozn","Ozn.",50),("nr_ewid","Nr ewid.",160),
                ("data","Data",90),("pow","Pow.[ha]",70),
                ("gatunek","Gatunek zwierząt",150),("liczba","Liczba",120),
                ("symbol","Symbol",90),("wariant","Wariant",70),
                ("uwagi","Uwagi/rodzaj wypasu",250)]
        for col, txt, w in nagl:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, minwidth=40)

        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12,0), pady=4)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        hsb.grid(row=2, column=0, sticky="ew", padx=12)
        self.rowconfigure(1, weight=1)

        info = tk.Label(self,
            text="💡 Działki pastwiskowe/kośno-pastwiskowe pojawiają się automatycznie po imporcie CSV",
            bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"), fg="#555555")
        info.grid(row=3, column=0, sticky="w", padx=14, pady=(0,6))

    def odswiez(self):
        self.tree.delete(*self.tree.get_children())
        if not _gosp:
            return
        rok_filtr = self._var_rok.get()
        wypasy = _gosp.wypasy
        if rok_filtr != "wszystkie":
            wypasy = [w for w in wypasy if w.data.endswith(rok_filtr)]
        wypasy = sorted(wypasy, key=lambda x: (x.data[6:], x.data[3:5], x.data[:2]))
        for w in wypasy:
            self.tree.insert("", tk.END, iid=w.id, values=(
                w.oznaczenie, w.nr_ewid, w.data,
                f"{w.pow_ha:.2f}".replace(".",","),
                w.gatunek, w.liczba, w.symbol_dzialania,
                getattr(w, "wariant", "") or "–",
                w.uwagi))

    def _zaznaczony(self) -> WpisWypasu | None:
        sel = self.tree.selection()
        if not sel or not _gosp:
            return None
        return next((w for w in _gosp.wypasy if w.id == sel[0]), None)

    def _dzialki_pastwiskowe(self):
        if not _gosp:
            return []
        return [d for d in _gosp.dzialki
                if any(s in d.sposob_uzytkowania
                       for s in ["pastwiskowe", "kośno-pastwiskowe"])]

    def _dodaj(self):
        if not _gosp:
            return
        dzialki_past = self._dzialki_pastwiskowe()
        if not dzialki_past:
            messagebox.showinfo("Brak działek pastwiskowych",
                                "Zmień sposób użytkowania działek TUZ na pastwiskowe "
                                "lub kośno-pastwiskowe w zakładce Działki.")
            return
        dlg = DialogWypas(self, _gosp, dzialki_past)
        self.wait_window(dlg)
        if dlg.wynik:
            _gosp.wypasy.append(dlg.wynik)
            _zapisz_auto()
            self.odswiez()
            self.status.ustaw("✅ Dodano wpis wypasu.", KOLOR_SUKCES)

    def _dodaj_grupowo(self):
        if not _gosp or not _gosp.dzialki:
            return
        dlg = DialogWpisGrupowy(self, _gosp, tryb="wypas")
        self.wait_window(dlg)
        if dlg.wyniki:
            _gosp.wypasy.extend(dlg.wyniki)
            _zapisz_auto()
            self.odswiez()
            n = len(dlg.wyniki)
            self.status.ustaw(f"✅ Dodano {n} wpisów wypasów.", KOLOR_SUKCES)

    def _edytuj(self):
        w = self._zaznaczony()
        if not w:
            messagebox.showinfo("Brak wyboru", "Zaznacz wpis do edycji.")
            return
        dlg = DialogWypas(self, _gosp, self._dzialki_pastwiskowe(), wypas=w)
        self.wait_window(dlg)
        if dlg.wynik:
            idx = next(i for i, x in enumerate(_gosp.wypasy) if x.id == w.id)
            _gosp.wypasy[idx] = dlg.wynik
            _zapisz_auto()
            self.odswiez()

    def _usun(self):
        w = self._zaznaczony()
        if not w:
            return
        if messagebox.askyesno("Usuń", f"Usunąć wpis wypasu z {w.data}?"):
            _gosp.wypasy = [x for x in _gosp.wypasy if x.id != w.id]
            _zapisz_auto()
            self.odswiez()


# ── Dialog: wpis wypasu ───────────────────────────────────────────────────────

class DialogWypas(tk.Toplevel):
    def __init__(self, parent, gosp: Gospodarstwo,
                 dzialki: list[DzialkaRolna],
                 wypas: WpisWypasu | None = None):
        super().__init__(parent)
        self.title("Wypas zwierząt")
        self.resizable(False, False)
        self.configure(bg=KOLOR_TLO)
        self.wynik: WpisWypasu | None = None
        self._gosp = gosp
        self._dzialki = {d.oznaczenie: d for d in dzialki}
        self._wypas = wypas
        # Wymuś pełną inicjalizację okna przed tworzeniem widgetów (Python 3.14)
        self.update()
        self._buduj()
        self.grab_set()

    def _buduj(self):
        self._f = tk.Frame(self, bg=KOLOR_TLO)
        self._f.pack(fill=tk.BOTH, expand=True)
        w = self._wypas
        f = self._f
        ozn_lista = sorted(self._dzialki.keys())
        r = 0

        _lbl(f, "Działka (ozn.):").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_ozn = tk.StringVar(value=w.oznaczenie if w else (ozn_lista[0] if ozn_lista else ""))
        cb = ttk.Combobox(f, textvariable=self._var_ozn,
                          values=ozn_lista, width=10, state="readonly")
        cb.grid(row=r, column=1, padx=(0,4), pady=6, sticky="w")
        cb.bind("<<ComboboxSelected>>", self._on_dzialka_change)
        _lbl(f, "Nr ewid.:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_nr = tk.StringVar(value=w.nr_ewid if w else "")
        self._cb_nr = ttk.Combobox(f, textvariable=self._var_nr, width=22)
        self._cb_nr.grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        self._cb_nr.bind("<<ComboboxSelected>>", self._aktualizuj_pow_ewid)
        r += 1

        # Data z kalendarzem
        self._var_data = tk.StringVar(value=w.data if w else date.today().strftime("%d.%m.%Y"))
        _pole_daty(f, self._var_data, r, 0, "Data:", self)
        _lbl(f, "Pow. [ha]:").grid(row=r, column=2, padx=(8,4), pady=6, sticky="e")
        self._var_pow = tk.StringVar(value=str(w.pow_ha).replace(".", ",") if w else "")
        tk.Entry(f, textvariable=self._var_pow, font=(CZCIONKA, 10),
                 width=10).grid(row=r, column=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        _lbl(f, "Gatunek zwierząt:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_gatunek = tk.StringVar(value=w.gatunek if w else "")
        ttk.Combobox(f, textvariable=self._var_gatunek,
                     values=GATUNKI_ZWIERZAT, width=30).grid(
            row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        _lbl(f, "Liczba zwierząt:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_liczba = tk.StringVar(value=w.liczba if w else "")
        tk.Entry(f, textvariable=self._var_liczba, font=(CZCIONKA, 10),
                 width=30).grid(row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        r += 1

        _lbl(f, "Symbol działania:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="e")
        self._var_symbol = tk.StringVar(value=w.symbol_dzialania if w else "ZRSK2327")
        ttk.Combobox(f, textvariable=self._var_symbol,
                     values=SYMBOLE_DZIALAN, width=22).grid(
            row=r, column=1, padx=(0,4), pady=6, sticky="w")
        r += 1

        _lbl(f, "Uwagi / rodzaj\nwypasu:").grid(row=r, column=0, padx=(16,4), pady=6, sticky="ne")
        self._txt_uwagi = tk.Text(f, font=(CZCIONKA, 9), width=46, height=3)
        self._txt_uwagi.grid(row=r, column=1, columnspan=3, padx=(0,16), pady=6, sticky="w")
        if w and w.uwagi:
            self._txt_uwagi.insert("1.0", w.uwagi)
        r += 1

        bf = tk.Frame(f, bg=KOLOR_TLO)
        bf.grid(row=r, column=0, columnspan=4, pady=12)
        _btn(bf, "Zapisz", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

        self._on_dzialka_change()

    def _on_dzialka_change(self, event=None):
        ozn = self._var_ozn.get()
        d = self._dzialki.get(ozn)
        if d:
            self._cb_nr["values"] = d.numery_ewid
            if d.numery_ewid and not self._var_nr.get():
                self._var_nr.set(d.numery_ewid[0])
            if not self._wypas:
                self._var_symbol.set(d.symbol_dzialania)
                self._var_wariant.set(d.wariant)
            self._aktualizuj_pow_ewid()

    def _aktualizuj_pow_ewid(self, event=None):
        ozn = self._var_ozn.get()
        nr  = self._var_nr.get()
        d   = self._dzialki.get(ozn)
        if d and nr and nr in d.pow_ewid:
            self._var_pow.set(f"{d.pow_ewid[nr]:.4f}".replace(".", ","))
        elif d and not nr:
            self._var_pow.set(str(d.pow_ha).replace(".", ","))

    def _ok(self):
        ozn = self._var_ozn.get().strip()
        if not ozn or not self._var_data.get().strip():
            messagebox.showwarning("Brak danych", "Podaj działkę i datę.", parent=self)
            return
        try:
            pow_ha = float(self._var_pow.get().replace(",", "."))
        except ValueError:
            pow_ha = 0.0
        d = self._dzialki.get(ozn)
        nowy_wypas = WpisWypasu(
            id=self._wypas.id if self._wypas else _nowy_id(),
            dzialka_id=d.id if d else "",
            oznaczenie=ozn,
            nr_ewid=self._var_nr.get().strip(),
            data=self._var_data.get().strip(),
            pow_ha=pow_ha,
            gatunek=self._var_gatunek.get().strip(),
            liczba=self._var_liczba.get().strip(),
            symbol_dzialania=self._var_symbol.get().strip(),
            wariant=self._var_wariant.get().strip(),
            uwagi=self._txt_uwagi.get("1.0", tk.END).strip(),
        )
        # Walidacja
        ost = waliduj_wpis_wypasu(ozn, self._var_nr.get().strip(),
                                   d.wariant if d else "",
                                   self._var_data.get().strip(),
                                   d.uwagi if d else "")
        if ost:
            if not messagebox.askyesno("⚠️ Ostrzeżenie",
                                        komunikat_ostrzezenia(ost), parent=self):
                return
        self.wynik = nowy_wypas
        self.destroy()




# ── Zakładka: Kalkulator wypasu ───────────────────────────────────────────────

class ZakladkaKalkulatorWypasu(tk.Frame):
    """
    Kalkulator obciążenia pastwiska ZRSK 2023-2027.
    Plan bazowy 5-letni per działka rolna, z możliwością korekt.
    """
    def __init__(self, parent, status: StatusBar):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self._aktywny_plan: PlanWypasu | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._buduj()

    def _buduj(self):
        # Pasek narzędzi
        tb = tk.Frame(self, bg=KOLOR_TLO)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        _btn(tb, "➕ Nowy plan dla działki", self._nowy_plan).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "✏️ Edytuj plan", self._edytuj_plan).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "📋 Dodaj korektę", self._dodaj_korekte).pack(side=tk.LEFT, padx=(0,6))
        _btn(tb, "🗑 Usuń plan", self._usun_plan, kolor="#C00000").pack(side=tk.LEFT, padx=(0,12))
        _btn(tb, "🖨 Eksportuj PDF", self._eksportuj_pdf, kolor=KOLOR_NAV).pack(side=tk.LEFT)

        # Główny podział: lewa lista planów, prawa szczegóły
        main = tk.Frame(self, bg=KOLOR_TLO)
        main.grid(row=1, column=0, sticky="nsew", padx=12, pady=4)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Lewa: lista planów
        left = tk.LabelFrame(main, text="  Plany wypasu  ",
                              bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"),
                              fg=KOLOR_NAV, bd=2)
        left.grid(row=0, column=0, sticky="ns", padx=(0,6))
        left.rowconfigure(0, weight=1)

        self._lb_plany = tk.Listbox(left, font=(CZCIONKA, 10),
                                     selectmode=tk.SINGLE, width=20, height=20,
                                     bg="white", bd=1, relief=tk.SOLID)
        vsb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self._lb_plany.yview)
        self._lb_plany.configure(yscrollcommand=vsb.set)
        self._lb_plany.grid(row=0, column=0, sticky="nsew", padx=(6,0), pady=6)
        vsb.grid(row=0, column=1, sticky="ns", pady=6, padx=(0,4))
        self._lb_plany.bind("<<ListboxSelect>>", self._on_plan_select)

        # Prawa: szczegóły planu
        self._right = tk.Frame(main, bg=KOLOR_TLO)
        self._right.grid(row=0, column=1, sticky="nsew")
        self._right.columnconfigure(0, weight=1)
        self._right.rowconfigure(1, weight=1)

        self._lbl_pusty = tk.Label(self._right,
            text="Wybierz plan z listy lub utwórz nowy – kliknij '➕ Nowy plan dla działki'",
            bg=KOLOR_TLO, font=(CZCIONKA, 10, "italic"), fg="#888888")
        self._lbl_pusty.pack(expand=True)

    def odswiez(self):
        self._lb_plany.delete(0, tk.END)
        if not _gosp:
            return
        from kalkulator_wypasu import plan_z_dict
        for pd in _gosp.plany_wypasu:
            try:
                plan = plan_z_dict(dict(pd))
                ikona = "✓" if (plan.status_obsady == "OK" and
                                plan.status_obciazenia == "OK") else "⚠"
                self._lb_plany.insert(tk.END,
                    f"{ikona} Dz.{plan.dzialka_ozn} – {plan.wariant} "
                    f"({plan.rok_od}–{plan.rok_do})")
            except Exception:
                self._lb_plany.insert(tk.END, "⚠ Błąd danych")

    def _aktywny_idx(self) -> int:
        sel = self._lb_plany.curselection()
        return sel[0] if sel else -1

    def _on_plan_select(self, event=None):
        idx = self._aktywny_idx()
        if idx < 0 or not _gosp or idx >= len(_gosp.plany_wypasu):
            return
        from kalkulator_wypasu import plan_z_dict
        plan = plan_z_dict(dict(_gosp.plany_wypasu[idx]))
        self._aktywny_plan = plan
        self._pokaz_szczegoly(plan)

    def _pokaz_szczegoly(self, plan: PlanWypasu):
        for w in self._right.winfo_children():
            w.destroy()

        f = self._right
        f.columnconfigure(0, weight=1)

        # Nagłówek
        kol = KOLOR_SUKCES if (plan.status_obsady == "OK" and
                               plan.status_obciazenia == "OK") else KOLOR_WARN
        tk.Label(f, text=f"Działka {plan.dzialka_ozn}  |  Wariant {plan.wariant}  |  "
                          f"{plan.pow_ha:.2f} ha  |  {plan.rok_od}–{plan.rok_do}",
                 bg=KOLOR_TLO, font=(CZCIONKA, 12, "bold"), fg=KOLOR_NAV).pack(
            anchor="w", padx=8, pady=(8,2))
        limit = get_limit(plan.wariant)
        tk.Label(f, text=limit.opis, bg=KOLOR_TLO,
                 font=(CZCIONKA, 9, "italic"), fg="#375623").pack(anchor="w", padx=8)

        # Panel wskaźników
        wsk = tk.Frame(f, bg=KOLOR_TLO)
        wsk.pack(fill=tk.X, padx=8, pady=8)

        def _karta(parent, tytul, wartosc, limit_txt, rezerwa, status, col):
            kolory = {"OK": ("#EBF5E1","#217346"), "NISKA": ("#FFF3CD","#BF8F00"),
                      "ZA_WYSOKA": ("#FFE0E0","#C00000"), "ZA_WYSOKIE": ("#FFE0E0","#C00000")}
            bg, fg = kolory.get(status, ("#F0F4F8","#333333"))
            card = tk.Frame(parent, bg=bg, bd=1, relief=tk.SOLID)
            card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")
            parent.columnconfigure(col, weight=1)
            tk.Label(card, text=tytul, bg=bg, font=(CZCIONKA, 9, "bold"),
                     fg=fg).pack(pady=(6,2))
            tk.Label(card, text=wartosc, bg=bg,
                     font=(CZCIONKA, 16, "bold"), fg=fg).pack()
            tk.Label(card, text=f"Limit: {limit_txt}", bg=bg,
                     font=(CZCIONKA, 8), fg=fg).pack()
            tk.Label(card, text=f"Rezerwa: {rezerwa}%",
                     bg=bg, font=(CZCIONKA, 8, "italic"), fg=fg).pack(pady=(0,6))

        _karta(wsk, "Obsada [DJP/ha]",
               f"{plan.obsada:.3f}".replace(".",","),
               f"{plan.obsada_min:.1f}–{plan.obsada_max:.1f}".replace(".",","),
               f"{plan.rezerwa_obsady_pct():.1f}".replace(".",","),
               plan.status_obsady, 0)
        _karta(wsk, "Obciążenie [DJP/ha]",
               f"{plan.obciazenie:.3f}".replace(".",","),
               f"do {plan.obciazenie_max:.1f}".replace(".",","),
               f"{plan.rezerwa_obciazenia_pct():.1f}".replace(".",","),
               plan.status_obciazenia, 1)
        _karta(wsk, "Łącznie DJP",
               f"{plan.djp_lacznie:.2f}".replace(".",","),
               f"max {plan.obsada_max * plan.pow_ha:.1f}".replace(".",","),
               "", "OK", 2)
        _karta(wsk, "Dni sezonu",
               str(plan.dni_sezonu),
               f"{limit.dni_sezonu} (standard)",
               "", "OK", 3)

        # Tabela grup zwierząt
        tk.Label(f, text="Skład stada:", bg=KOLOR_TLO,
                 font=(CZCIONKA, 10, "bold"), fg=KOLOR_NAV).pack(
            anchor="w", padx=8, pady=(4,2))

        cols = ("gatunek","szt","djp_wsp","djp_l",
                "IV","V","VI","VII","VIII","IX","X","XI","dni_l","punkty")
        tree = ttk.Treeview(f, columns=cols, show="headings",
                             height=8, selectmode="none")
        hdrs = [("gatunek","Gatunek/grupa",160),("szt","Szt.",50),
                ("djp_wsp","DJP wsp.",55),("djp_l","DJP lacznie",60),
                ("IV","IV",35),("V","V",35),("VI","VI",35),("VII","VII",35),
                ("VIII","VIII",40),("IX","IX",35),("X","X",35),("XI","XI",35),
                ("dni_l","Dni lacznie",55),("punkty","Punkty",60)]
        for col, txt, w in hdrs:
            tree.heading(col, text=txt)
            tree.column(col, width=w, minwidth=30, anchor="center")
        tree.column("gatunek", anchor="w")

        for g in plan.grupy:
            if g.liczba == 0: continue
            tree.insert("", tk.END, values=(
                g.gatunek, g.liczba,
                f"{g.djp_wsp:.2f}".replace(".",","),
                f"{g.djp_lacznie:.2f}".replace(".",","),
                *[g.dni.get(m, 0) for m in MIESIACE],
                g.dni_lacznie,
                f"{g.punkty:.1f}".replace(".",","),
            ))

        hsb = ttk.Scrollbar(f, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        tree.pack(fill=tk.X, padx=8)
        hsb.pack(fill=tk.X, padx=8)

        # Korekty
        if plan.korekty:
            tk.Label(f, text=f"Korekty planu: {len(plan.korekty)}",
                     bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"),
                     fg=KOLOR_WARN).pack(anchor="w", padx=8, pady=2)

    def _nowy_plan(self):
        if not _gosp or not _gosp.dzialki:
            messagebox.showinfo("Brak działek", "Najpierw zaimportuj działki."); return
        dlg = DialogPlanWypasu(self, _gosp)
        self.wait_window(dlg)
        if dlg.wynik:
            from kalkulator_wypasu import plan_do_dict
            _gosp.plany_wypasu.append(plan_do_dict(dlg.wynik))
            _zapisz_auto()
            self.odswiez()
            self.status.ustaw("✅ Plan wypasu zapisany.", KOLOR_SUKCES)

    def _edytuj_plan(self):
        idx = self._aktywny_idx()
        if idx < 0: messagebox.showinfo("Brak wyboru", "Zaznacz plan."); return
        from kalkulator_wypasu import plan_z_dict, plan_do_dict
        plan = plan_z_dict(dict(_gosp.plany_wypasu[idx]))
        dlg = DialogPlanWypasu(self, _gosp, plan)
        self.wait_window(dlg)
        if dlg.wynik:
            _gosp.plany_wypasu[idx] = plan_do_dict(dlg.wynik)
            _zapisz_auto()
            self.odswiez()
            self._lb_plany.selection_set(idx)
            self._on_plan_select()

    def _dodaj_korekte(self):
        idx = self._aktywny_idx()
        if idx < 0: messagebox.showinfo("Brak wyboru", "Zaznacz plan."); return
        dlg = DialogKorekta(self)
        self.wait_window(dlg)
        if dlg.wynik:
            from kalkulator_wypasu import plan_z_dict, plan_do_dict
            plan = plan_z_dict(dict(_gosp.plany_wypasu[idx]))
            nr = len(plan.korekty) + 1
            plan.korekty.append({
                "nr": nr,
                "data": dlg.wynik["data"],
                "przyczyna": dlg.wynik["przyczyna"],
                "autor": dlg.wynik["autor"],
            })
            _gosp.plany_wypasu[idx] = plan_do_dict(plan)
            _zapisz_auto()
            self.odswiez()
            self._lb_plany.selection_set(idx)
            self._on_plan_select()
            self.status.ustaw(f"✅ Korekta nr {nr} dodana.", KOLOR_SUKCES)

    def _usun_plan(self):
        idx = self._aktywny_idx()
        if idx < 0: return
        if messagebox.askyesno("Usuń plan", "Usunąć plan wypasu dla tej działki?"):
            _gosp.plany_wypasu.pop(idx)
            _zapisz_auto()
            self.odswiez()
            for w in self._right.winfo_children(): w.destroy()
            self._lbl_pusty = tk.Label(self._right,
                text="Wybierz plan z listy lub utwórz nowy.",
                bg=KOLOR_TLO, font=(CZCIONKA, 10, "italic"), fg="#888888")
            self._lbl_pusty.pack(expand=True)

    def _eksportuj_pdf(self):
        if not _gosp or not _gosp.plany_wypasu:
            messagebox.showinfo("Brak planów", "Brak planów wypasu do eksportu."); return
        sciezka = filedialog.asksaveasfilename(
            title="Zapisz plan wypasu PDF", defaultextension=".pdf",
            initialfile=f"Plan_wypasu_{_gosp.rolnik.replace(' ','_')}.pdf",
            filetypes=[("PDF", "*.pdf")])
        if not sciezka: return
        try:
            from kalkulator_wypasu import plan_z_dict
            plany = [plan_z_dict(dict(pd)) for pd in _gosp.plany_wypasu]
            eksportuj_plan_wypasu(
                plany=plany, sciezka=sciezka,
                rolnik=_gosp.rolnik, nr_id=_gosp.nr_identyfikacyjny,
                nazwa_gosp=_gosp.nazwa,
                autor=plany[0].autor if plany else "")
            messagebox.showinfo("Gotowe", "PDF zapisany:\n" + sciezka)
            self.status.ustaw(f"✅ PDF planu wypasu zapisany.", KOLOR_SUKCES)
        except Exception as e:
            messagebox.showerror("Błąd", str(e))


# ── Dialog: nowy/edytuj plan wypasu ──────────────────────────────────────────

class DialogPlanWypasu(tk.Toplevel):
    def __init__(self, parent, gosp: Gospodarstwo,
                 plan: PlanWypasu | None = None):
        super().__init__(parent)
        self.title("Plan wypasu – działka rolna")
        self.resizable(True, True)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.wynik: PlanWypasu | None = None
        self._gosp = gosp
        self._plan = plan
        self._f = tk.Frame(self, bg=KOLOR_TLO)
        self._f.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self._grupy_vars: list[dict] = []
        self._buduj()
        self.geometry("1050x720")

    def _buduj(self):
        f = self._f
        f.columnconfigure(0, weight=1)

        nb = ttk.Notebook(f)
        nb.pack(fill=tk.BOTH, expand=True)

        # ── Zakładka 1: Podstawowe ────────────────────────────────────────
        f1 = tk.Frame(nb, bg=KOLOR_TLO)
        nb.add(f1, text="  Dane podstawowe  ")

        dzialki = sorted(_gosp.dzialki, key=lambda d: d.oznaczenie)
        ozn_lista = [d.oznaczenie for d in dzialki]
        plan = self._plan

        r = 0
        _lbl(f1, "Działka rolna:").grid(row=r, column=0, padx=(12,4), pady=6, sticky="e")
        self._var_ozn = tk.StringVar(value=plan.dzialka_ozn if plan else (ozn_lista[0] if ozn_lista else ""))
        cb = ttk.Combobox(f1, textvariable=self._var_ozn, values=ozn_lista,
                           width=10, state="readonly")
        cb.grid(row=r, column=1, padx=(0,4), pady=6, sticky="w")
        cb.bind("<<ComboboxSelected>>", self._on_dzialka_change)

        _lbl(f1, "Rok od:").grid(row=r, column=2, padx=(12,4), pady=6, sticky="e")
        self._var_rok_od = tk.StringVar(value=str(plan.rok_od if plan else date.today().year))
        tk.Entry(f1, textvariable=self._var_rok_od, width=8,
                 font=(CZCIONKA, 10)).grid(row=r, column=3, padx=(0,4), pady=6, sticky="w")

        _lbl(f1, "Rok do:").grid(row=r, column=4, padx=(8,4), pady=6, sticky="e")
        self._var_rok_do = tk.StringVar(value=str(plan.rok_do if plan else date.today().year + 4))
        tk.Entry(f1, textvariable=self._var_rok_do, width=8,
                 font=(CZCIONKA, 10)).grid(row=r, column=5, padx=(0,12), pady=6, sticky="w")
        r += 1

        # Powierzchnia i limity
        _lbl(f1, "Pow. [ha]:").grid(row=r, column=0, padx=(12,4), pady=6, sticky="e")
        self._var_pow = tk.StringVar(value=str(plan.pow_ha if plan else "0").replace(".", ","))
        tk.Entry(f1, textvariable=self._var_pow, width=10,
                 font=(CZCIONKA, 10), bg="#EBF3FB").grid(
            row=r, column=1, padx=(0,4), pady=6, sticky="w")

        _lbl(f1, "Wariant:").grid(row=r, column=2, padx=(12,4), pady=6, sticky="e")
        self._var_wariant = tk.StringVar(value=plan.wariant if plan else "")
        cb_w = ttk.Combobox(f1, textvariable=self._var_wariant,
                             values=sorted(LIMITY_ZRSK.keys()), width=10)
        cb_w.grid(row=r, column=3, padx=(0,4), pady=6, sticky="w")
        cb_w.bind("<<ComboboxSelected>>", self._on_wariant_change)
        r += 1

        # Edytowalne limity
        tk.Label(f1, text="Limity (domyślne z rozporządzenia, edytowalne gdy ekspert zmienił):",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"),
                 fg="#375623").grid(row=r, column=0, columnspan=6, padx=12, pady=(8,2), sticky="w")
        r += 1

        self._lbl_opis_limitu = tk.Label(f1, text="", bg=KOLOR_TLO,
                                          font=(CZCIONKA, 8), fg="#555555", wraplength=600)
        self._lbl_opis_limitu.grid(row=r, column=0, columnspan=6, padx=12, pady=(0,4), sticky="w")
        r += 1

        for i, (klucz, label, domyslna) in enumerate([
            ("obs_min", "Obsada min [DJP/ha]:", plan.obsada_min if plan else 0.3),
            ("obs_max", "Obsada max [DJP/ha]:", plan.obsada_max if plan else 1.0),
            ("obc_max", "Obciążenie max [DJP/ha]:", plan.obciazenie_max if plan else 10.0),
            ("dni",     "Dni sezonu:",              plan.dni_sezonu if plan else 168),
        ]):
            col = (i % 2) * 3
            rr = r + i // 2
            _lbl(f1, label).grid(row=rr, column=col, padx=(12,4), pady=4, sticky="e")
            var = tk.StringVar(value=str(domyslna).replace(".", ","))
            setattr(self, f"_var_{klucz}", var)
            tk.Entry(f1, textvariable=var, width=10,
                     font=(CZCIONKA, 10), bg="#FFF9C4").grid(
                row=rr, column=col+1, padx=(0,4), pady=4, sticky="w")
        r += 3

        _lbl(f1, "Autor planu:").grid(row=r, column=0, padx=(12,4), pady=6, sticky="e")
        self._var_autor = tk.StringVar(value=plan.autor if plan else "")
        tk.Entry(f1, textvariable=self._var_autor, font=(CZCIONKA, 10),
                 width=30).grid(row=r, column=1, columnspan=3, padx=(0,4), pady=6, sticky="w")

        _lbl(f1, "Data oprac.:").grid(row=r, column=4, padx=(8,4), pady=6, sticky="e")
        self._var_data_opr = tk.StringVar(
            value=plan.data_opracowania if plan else date.today().strftime("%d.%m.%Y"))
        tk.Entry(f1, textvariable=self._var_data_opr, font=(CZCIONKA, 10),
                 width=14).grid(row=r, column=5, padx=(0,12), pady=6, sticky="w")
        r += 1

        _lbl(f1, "Uwagi:").grid(row=r, column=0, padx=(12,4), pady=6, sticky="ne")
        self._txt_uwagi = tk.Text(f1, font=(CZCIONKA, 9), width=60, height=3)
        self._txt_uwagi.grid(row=r, column=1, columnspan=5, padx=(0,12), pady=6, sticky="w")
        if plan and plan.uwagi:
            self._txt_uwagi.insert("1.0", plan.uwagi)

        # ── Zakładka 2: Stado i dni wypasu ────────────────────────────────
        f2 = tk.Frame(nb, bg=KOLOR_TLO)
        nb.add(f2, text="  Stado i dni wypasu  ")
        f2.columnconfigure(0, weight=1)
        f2.rowconfigure(0, weight=1)

        # Nagłówki
        hdr = tk.Frame(f2, bg="#E8F0F8")
        hdr.pack(fill=tk.X, padx=4, pady=(6,0))
        for c, (txt, w) in enumerate([
            ("Gatunek/grupa", 22), ("Szt.", 6), ("DJP wsp.", 8),
            *[(m, 5) for m in MIESIACE], ("DJP lacznie", 8), ("Punkty", 8)
        ]):
            tk.Label(hdr, text=txt, bg="#E8F0F8",
                     font=(CZCIONKA, 8, "bold"), width=w, anchor="center").grid(
                row=0, column=c, padx=2, pady=3)

        # Scrollowany obszar grup
        canv_frame = tk.Frame(f2, bg=KOLOR_TLO)
        canv_frame.pack(fill=tk.BOTH, expand=True, padx=4)
        canv_frame.columnconfigure(0, weight=1)
        canv_frame.rowconfigure(0, weight=1)

        canv = tk.Canvas(canv_frame, bg=KOLOR_TLO, highlightthickness=0)
        vsb = ttk.Scrollbar(canv_frame, orient=tk.VERTICAL, command=canv.yview)
        canv.configure(yscrollcommand=vsb.set)
        canv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._stado_frame = tk.Frame(canv, bg=KOLOR_TLO)
        cw = canv.create_window((0, 0), window=self._stado_frame, anchor="nw")

        def _on_cfg(e):
            canv.configure(scrollregion=canv.bbox("all"))
            canv.itemconfig(cw, width=canv.winfo_width())
        self._stado_frame.bind("<Configure>", _on_cfg)
        canv.bind("<Configure>", lambda e: canv.itemconfig(cw, width=e.width))

        # Wypełnij wiersze grup
        self._buduj_wiersze_stada(plan)

        # Panel wyników na żywo
        wynik_frame = tk.Frame(f2, bg="#E8F0F8", bd=1, relief=tk.SOLID)
        wynik_frame.pack(fill=tk.X, padx=4, pady=4)
        self._lbl_obsada = tk.Label(wynik_frame, text="Obsada: –",
                                     bg="#E8F0F8", font=(CZCIONKA, 10, "bold"))
        self._lbl_obsada.pack(side=tk.LEFT, padx=12, pady=4)
        self._lbl_obciazenie = tk.Label(wynik_frame, text="Obciążenie: –",
                                         bg="#E8F0F8", font=(CZCIONKA, 10, "bold"))
        self._lbl_obciazenie.pack(side=tk.LEFT, padx=12)
        self._lbl_status = tk.Label(wynik_frame, text="",
                                     bg="#E8F0F8", font=(CZCIONKA, 10, "bold"))
        self._lbl_status.pack(side=tk.LEFT, padx=12)

        # ── Przyciski ─────────────────────────────────────────────────────
        bf = tk.Frame(self._f, bg=KOLOR_TLO)
        bf.pack(pady=(4,8))
        _btn(bf, "✅ Zapisz plan", self._ok, kolor=KOLOR_NAV).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

        # Inicjalizacja
        self._on_dzialka_change()
        self._przelicz()

    def _buduj_wiersze_stada(self, plan):
        for w in self._stado_frame.winfo_children():
            w.destroy()
        self._grupy_vars.clear()

        kolory = ["#FFFFFF", "#F5F9FF"]
        for i, gatunek in enumerate(GRUPY_DJP):
            djp_dom = DJP[gatunek]
            # Znajdź istniejące dane jeśli edytujemy
            istn = None
            if plan:
                istn = next((g for g in plan.grupy if g.gatunek == gatunek), None)

            liczba = istn.liczba if istn else 0
            djp_wsp = istn.djp_wsp if istn else djp_dom
            dni_val = istn.dni if istn else {m: 0 for m in MIESIACE}

            bg = kolory[i % 2]
            row_f = tk.Frame(self._stado_frame, bg=bg)
            row_f.pack(fill=tk.X, padx=2, pady=1)

            # Gatunek
            tk.Label(row_f, text=gatunek, bg=bg, font=(CZCIONKA, 9),
                     width=22, anchor="w").grid(row=0, column=0, padx=3)

            # Liczba sztuk
            var_l = tk.StringVar(value=str(liczba))
            tk.Entry(row_f, textvariable=var_l, width=6,
                     font=(CZCIONKA, 9), justify="center",
                     bg="#EBF3FB" if liczba > 0 else bg).grid(
                row=0, column=1, padx=3)

            # DJP współczynnik
            var_d = tk.StringVar(value=str(djp_wsp).replace(".", ","))
            tk.Entry(row_f, textvariable=var_d, width=8,
                     font=(CZCIONKA, 9), justify="center",
                     bg="#FFF9C4").grid(row=0, column=2, padx=3)

            # Dni per miesiąc
            vars_m = {}
            for j, m in enumerate(MIESIACE):
                vm = tk.StringVar(value=str(dni_val.get(m, 0)))
                tk.Entry(row_f, textvariable=vm, width=5,
                         font=(CZCIONKA, 9), justify="center").grid(
                    row=0, column=3+j, padx=2)
                vars_m[m] = vm

            # DJP łącznie (tylko wyświetlane)
            var_djp_l = tk.StringVar(value="0.00")
            lbl_djp = tk.Label(row_f, textvariable=var_djp_l,
                                bg=bg, font=(CZCIONKA, 9, "bold"), width=8)
            lbl_djp.grid(row=0, column=11, padx=3)

            # Punkty (tylko wyświetlane)
            var_pkt = tk.StringVar(value="0")
            lbl_pkt = tk.Label(row_f, textvariable=var_pkt,
                                bg=bg, font=(CZCIONKA, 9), width=8)
            lbl_pkt.grid(row=0, column=12, padx=3)

            entry = {"gatunek": gatunek, "var_liczba": var_l,
                     "var_djp": var_d, "vars_m": vars_m,
                     "var_djp_l": var_djp_l, "var_pkt": var_pkt}
            self._grupy_vars.append(entry)

            # Bind przeliczania
            var_l.trace_add("write", lambda *a: self._przelicz())
            var_d.trace_add("write", lambda *a: self._przelicz())
            for vm in vars_m.values():
                vm.trace_add("write", lambda *a: self._przelicz())

    def _on_dzialka_change(self, event=None):
        ozn = self._var_ozn.get()
        d = next((x for x in self._gosp.dzialki if x.oznaczenie == ozn), None)
        if d:
            self._var_pow.set(str(d.pow_ha).replace(".", ","))
            if not self._plan:
                self._var_wariant.set(d.wariant)
                self._on_wariant_change()

    def _on_wariant_change(self, event=None):
        war = self._var_wariant.get()
        limit = get_limit(war)
        self._var_obs_min.set(str(limit.obsada_min).replace(".", ","))
        self._var_obs_max.set(str(limit.obsada_max).replace(".", ","))
        self._var_obc_max.set(str(limit.obciazenie_max).replace(".", ","))
        self._var_dni.set(str(limit.dni_sezonu))
        self._lbl_opis_limitu.config(text=limit.opis)
        self._przelicz()

    def _przelicz(self):
        """Oblicza wyniki na żywo i aktualizuje etykiety."""
        try:
            pow_ha = float(self._var_pow.get().replace(",", "."))
            dni_s  = int(self._var_dni.get().replace(",", ".").replace(" ",""))
            obs_min = float(self._var_obs_min.get().replace(",", "."))
            obs_max = float(self._var_obs_max.get().replace(",", "."))
            obc_max = float(self._var_obc_max.get().replace(",", "."))
        except ValueError:
            return

        djp_total = 0.0
        pkt_total = 0.0

        for e in self._grupy_vars:
            try:
                l = int(e["var_liczba"].get() or 0)
                d = float(e["var_djp"].get().replace(",", ".") or 0)
                djp_l = l * d
                pkt = sum(l * d * int(e["vars_m"][m].get() or 0)
                          for m in MIESIACE)
                e["var_djp_l"].set(f"{djp_l:.2f}".replace(".", ","))
                e["var_pkt"].set(f"{pkt:.1f}".replace(".", ","))
                djp_total += djp_l
                pkt_total += pkt
            except (ValueError, TypeError):
                pass

        obsada = round(djp_total / pow_ha, 3) if pow_ha > 0 else 0.0
        obciaz = round(pkt_total / (pow_ha * dni_s), 3) if pow_ha > 0 and dni_s > 0 else 0.0

        # Kolory statusu
        def _kol(v, mn, mx):
            if v < mn: return KOLOR_WARN
            if v > mx: return KOLOR_BLAD
            return KOLOR_SUKCES

        c_obs = _kol(obsada, obs_min, obs_max)
        c_obc = "#C00000" if obciaz > obc_max else KOLOR_SUKCES

        self._lbl_obsada.config(
            text=f"Obsada: {obsada:.3f} DJP/ha  (limit: {obs_min:.1f}–{obs_max:.1f})".replace(".", ","),
            fg=c_obs)
        self._lbl_obciazenie.config(
            text=f"Obciążenie: {obciaz:.3f} DJP/ha  (max: {obc_max:.1f})".replace(".", ","),
            fg=c_obc)

        ok = (obs_min <= obsada <= obs_max) and (obciaz <= obc_max)
        self._lbl_status.config(
            text="✅ Wymogi spełnione" if ok else "⚠️ Sprawdź limity",
            fg=KOLOR_SUKCES if ok else KOLOR_BLAD)

    def _ok(self):
        ozn = self._var_ozn.get()
        d = next((x for x in self._gosp.dzialki if x.oznaczenie == ozn), None)
        try:
            pow_ha = float(self._var_pow.get().replace(",", "."))
            rok_od = int(self._var_rok_od.get())
            rok_do = int(self._var_rok_do.get())
            obs_min = float(self._var_obs_min.get().replace(",", "."))
            obs_max = float(self._var_obs_max.get().replace(",", "."))
            obc_max = float(self._var_obc_max.get().replace(",", "."))
            dni_s   = int(self._var_dni.get())
        except ValueError:
            messagebox.showwarning("Błąd", "Sprawdź wartości liczbowe.", parent=self)
            return

        grupy = []
        for e in self._grupy_vars:
            try:
                l = int(e["var_liczba"].get() or 0)
                d_wsp = float(e["var_djp"].get().replace(",", ".") or 0)
                dni = {m: int(e["vars_m"][m].get() or 0) for m in MIESIACE}
                if l > 0:
                    grupy.append(GrupaZwierzat(
                        gatunek=e["gatunek"], liczba=l,
                        djp_wsp=d_wsp, dni=dni))
            except (ValueError, TypeError):
                pass

        self.wynik = PlanWypasu(
            id=self._plan.id if self._plan else _nowy_id_wypas(),
            dzialka_ozn=ozn,
            dzialka_id=d.id if d else "",
            wariant=self._var_wariant.get(),
            pow_ha=pow_ha,
            rok_od=rok_od, rok_do=rok_do,
            obsada_min=obs_min, obsada_max=obs_max,
            obciazenie_max=obc_max, dni_sezonu=dni_s,
            grupy=grupy,
            korekty=self._plan.korekty if self._plan else [],
            uwagi=self._txt_uwagi.get("1.0", tk.END).strip(),
            data_opracowania=self._var_data_opr.get(),
            autor=self._var_autor.get(),
        )
        self.destroy()


# ── Dialog: korekta planu ─────────────────────────────────────────────────────

class DialogKorekta(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Korekta planu wypasu")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg=KOLOR_TLO)
        self.wynik = None
        self._f = tk.Frame(self, bg=KOLOR_TLO)
        self._f.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)
        self._buduj()

    def _buduj(self):
        f = self._f
        r = 0
        _lbl(f, "Data korekty:").grid(row=r, column=0, padx=(0,8), pady=6, sticky="e")
        self._var_data = tk.StringVar(value=date.today().strftime("%d.%m.%Y"))
        tk.Entry(f, textvariable=self._var_data, font=(CZCIONKA, 10),
                 width=14).grid(row=r, column=1, pady=6, sticky="w")
        r += 1
        _lbl(f, "Autor korekty:").grid(row=r, column=0, padx=(0,8), pady=6, sticky="e")
        self._var_autor = tk.StringVar()
        tk.Entry(f, textvariable=self._var_autor, font=(CZCIONKA, 10),
                 width=30).grid(row=r, column=1, pady=6, sticky="w")
        r += 1
        _lbl(f, "Przyczyna korekty:").grid(row=r, column=0, padx=(0,8), pady=6, sticky="ne")
        self._txt = tk.Text(f, font=(CZCIONKA, 9), width=40, height=4)
        self._txt.grid(row=r, column=1, pady=6, sticky="w")
        r += 1
        bf = tk.Frame(f, bg=KOLOR_TLO)
        bf.grid(row=r, column=0, columnspan=2, pady=8)
        _btn(bf, "Zapisz", self._ok).pack(side=tk.LEFT, padx=6)
        _btn(bf, "Anuluj", self.destroy, kolor="#888888").pack(side=tk.LEFT, padx=6)

    def _ok(self):
        self.wynik = {
            "data":      self._var_data.get().strip(),
            "autor":     self._var_autor.get().strip(),
            "przyczyna": self._txt.get("1.0", tk.END).strip(),
        }
        self.destroy()

# ── Zakładka: Kontrola terminów ──────────────────────────────────────────────

class ZakladkaKontrola(tk.Frame):
    def __init__(self, parent, status: StatusBar):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._buduj()

    def _buduj(self):
        tb = tk.Frame(self, bg=KOLOR_TLO)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10,4))
        _btn(tb, "🔍 Sprawdź cały rejestr", self._sprawdz).pack(side=tk.LEFT, padx=(0,8))
        self.lbl_wynik = tk.Label(tb, text="", bg=KOLOR_TLO,
                                   font=(CZCIONKA, 10, "bold"))
        self.lbl_wynik.pack(side=tk.LEFT)

        # Tabela ostrzeżeń
        cols = ("poziom", "dzialka", "wariant", "data", "czynnosc", "komunikat", "szczegoly")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                  selectmode="browse")
        nagl = [("poziom","Poziom",80), ("dzialka","Działka",70),
                ("wariant","Wariant",80), ("data","Data",90),
                ("czynnosc","Zabieg/czynność",200),
                ("komunikat","Komunikat",280), ("szczegoly","Szczegóły",260)]
        for col, txt, w in nagl:
            self.tree.heading(col, text=txt)
            self.tree.column(col, width=w, minwidth=40)

        # Kolory tagów
        self.tree.tag_configure("BŁĄD",  background="#FFE0E0")
        self.tree.tag_configure("UWAGA", background="#FFF9C4")
        self.tree.tag_configure("INFO",  background="#E3F2FD")

        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12,0), pady=4)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        hsb.grid(row=2, column=0, sticky="ew", padx=12)

        # Legenda
        leg = tk.Frame(self, bg=KOLOR_TLO)
        leg.grid(row=3, column=0, sticky="w", padx=14, pady=(0,8))
        for kolor, txt in [("#FFE0E0","🔴 Błąd"), ("#FFF9C4","🟡 Uwaga"), ("#E3F2FD","🔵 Info")]:
            tk.Label(leg, text=txt, bg=kolor, font=(CZCIONKA, 9),
                     padx=8, pady=2, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=4)
        tk.Label(leg, text="  Terminy wg wymogów ZRSK2327 / RE2327 PS",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9, "italic"),
                 fg="#555555").pack(side=tk.LEFT, padx=8)

    def odswiez(self):
        if _gosp:
            self._sprawdz(auto=True)

    def _sprawdz(self, auto=False):
        self.tree.delete(*self.tree.get_children())
        if not _gosp:
            return

        ost_lista = waliduj_caly_rejestr(_gosp)

        if not ost_lista:
            self.lbl_wynik.config(
                text="✅ Brak ostrzeżeń — terminy i limity w porządku",
                fg=KOLOR_SUKCES)
            if not auto:
                self.status.ustaw("✅ Kontrola zakończona — brak problemów.", KOLOR_SUKCES)
            return

        for o in ost_lista:
            self.tree.insert("", tk.END, tags=(o.poziom,), values=(
                f"{o.ikona} {o.poziom}",
                o.dzialka_ozn,
                o.wariant,
                o.data,
                o.czynnosc[:50] + ("…" if len(o.czynnosc) > 50 else ""),
                o.komunikat,
                o.szczegoly,
            ))

        n_bledow = sum(1 for o in ost_lista if o.poziom == "BŁĄD")
        n_uwag   = sum(1 for o in ost_lista if o.poziom == "UWAGA")
        self.lbl_wynik.config(
            text=f"⚠️  Znaleziono: {n_bledow} błędów, {n_uwag} ostrzeżeń",
            fg=KOLOR_BLAD if n_bledow else KOLOR_WARN)

        if not auto:
            self.status.ustaw(
                f"⚠️  Kontrola: {n_bledow} błędów, {n_uwag} ostrzeżeń — sprawdź zakładkę Kontrola.",
                KOLOR_BLAD if n_bledow else KOLOR_WARN)

# ── Zakładka: Eksport PDF ─────────────────────────────────────────────────────

class ZakladkaEksport(tk.Frame):
    def __init__(self, parent, status: StatusBar):
        super().__init__(parent, bg=KOLOR_TLO)
        self.status = status
        self._buduj()

    def _buduj(self):
        tk.Label(self, text="Wybierz zakres eksportu do PDF",
                 bg=KOLOR_TLO, font=(CZCIONKA, 12, "bold"),
                 fg=KOLOR_NAV).pack(padx=20, pady=(20,6))

        # Sekcje
        sek = tk.LabelFrame(self, text="  Sekcje dokumentu  ",
                             bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"),
                             fg=KOLOR_NAV, bd=2)
        sek.pack(padx=20, pady=8, fill=tk.X)

        self._var_tytul   = tk.BooleanVar(value=True)
        self._var_zabiegi = tk.BooleanVar(value=True)
        self._var_wypasy  = tk.BooleanVar(value=True)

        for var, txt in [
            (self._var_tytul,   "📄 Strona tytułowa"),
            (self._var_zabiegi, "🌾 Wykaz działań agrotechnicznych"),
            (self._var_wypasy,  "🐄 Wykaz wypasów zwierząt"),
        ]:
            tk.Checkbutton(sek, variable=var, text=txt, bg=KOLOR_TLO,
                           font=(CZCIONKA, 10)).pack(anchor="w", padx=12, pady=4)

        # Zakres dat
        def _data_frame(parent, tytul, var_od, var_do):
            f = tk.LabelFrame(parent, text=f"  {tytul}  ",
                              bg=KOLOR_TLO, font=(CZCIONKA, 10, "bold"),
                              fg=KOLOR_NAV, bd=2)
            tk.Label(f, text="Data od:", bg=KOLOR_TLO,
                     font=(CZCIONKA, 9)).grid(row=0, column=0, padx=(12,4), pady=8)
            tk.Entry(f, textvariable=var_od, font=(CZCIONKA, 10),
                     width=12).grid(row=0, column=1, padx=(0,16), pady=8)
            tk.Label(f, text="Data do:", bg=KOLOR_TLO,
                     font=(CZCIONKA, 9)).grid(row=0, column=2, padx=(8,4), pady=8)
            tk.Entry(f, textvariable=var_do, font=(CZCIONKA, 10),
                     width=12).grid(row=0, column=3, padx=(0,12), pady=8)
            tk.Label(f, text="(pozostaw puste = wszystkie)",
                     bg=KOLOR_TLO, font=(CZCIONKA, 8, "italic"),
                     fg="#888888").grid(row=0, column=4, padx=(4,12))
            return f

        # Szybki wybór roku
        rok_frame = tk.Frame(self, bg=KOLOR_TLO)
        rok_frame.pack(padx=20, pady=(0,4), fill=tk.X)
        tk.Label(rok_frame, text="Szybki wybór roku:",
                 bg=KOLOR_TLO, font=(CZCIONKA, 9)).pack(side=tk.LEFT, padx=(0,8))
        self._var_szybki_rok = tk.StringVar(value="")
        lata = [""] + [str(r) for r in range(date.today().year, 2022, -1)]
        cb = ttk.Combobox(rok_frame, textvariable=self._var_szybki_rok,
                          values=lata, width=8, state="readonly")
        cb.pack(side=tk.LEFT)
        cb.bind("<<ComboboxSelected>>", self._on_szybki_rok)

        self._var_od_z  = tk.StringVar()
        self._var_do_z  = tk.StringVar()
        self._var_od_w  = tk.StringVar()
        self._var_do_w  = tk.StringVar()

        _data_frame(self, "Zakres dat — zabiegi",
                    self._var_od_z, self._var_do_z).pack(padx=20, pady=4, fill=tk.X)
        _data_frame(self, "Zakres dat — wypasy",
                    self._var_od_w, self._var_do_w).pack(padx=20, pady=4, fill=tk.X)

        _btn(self, "🖨  Generuj PDF", self._eksportuj,
             kolor=KOLOR_NAV).pack(pady=20)

    def _on_szybki_rok(self, event=None):
        rok = self._var_szybki_rok.get()
        if rok:
            self._var_od_z.set(f"01.01.{rok}")
            self._var_do_z.set(f"31.12.{rok}")
            self._var_od_w.set(f"01.01.{rok}")
            self._var_do_w.set(f"31.12.{rok}")
        else:
            for v in [self._var_od_z, self._var_do_z, self._var_od_w, self._var_do_w]:
                v.set("")

    def _eksportuj(self):
        if not _gosp:
            messagebox.showinfo("Brak danych", "Najpierw otwórz lub utwórz gospodarstwo.")
            return
        if not any([self._var_tytul.get(), self._var_zabiegi.get(), self._var_wypasy.get()]):
            messagebox.showwarning("Nic nie wybrano", "Zaznacz co najmniej jedną sekcję.")
            return

        rok = self._var_szybki_rok.get()
        nazwa_pliku = f"Rejestr_{_gosp.rolnik.replace(' ', '_')}_{rok or 'wszystkie'}.pdf"
        sciezka = filedialog.asksaveasfilename(
            title="Zapisz PDF rejestru",
            defaultextension=".pdf",
            initialfile=nazwa_pliku,
            filetypes=[("PDF", "*.pdf")])
        if not sciezka:
            return

        try:
            eksportuj_pdf(
                gosp=_gosp,
                sciezka=sciezka,
                eksportuj_strone_tytulowa=self._var_tytul.get(),
                eksportuj_zabiegi=self._var_zabiegi.get(),
                eksportuj_wypasy=self._var_wypasy.get(),
                data_od_zabiegi=self._var_od_z.get(),
                data_do_zabiegi=self._var_do_z.get(),
                data_od_wypasy=self._var_od_w.get(),
                data_do_wypasy=self._var_do_w.get(),
            )
            self.status.ustaw(f"✅ PDF zapisany: {Path(sciezka).name}", KOLOR_SUKCES)
            messagebox.showinfo("Gotowe", f"PDF zapisany:\n{sciezka}")
        except Exception as e:
            messagebox.showerror("Błąd eksportu", str(e))


# ── Główne okno ───────────────────────────────────────────────────────────────

class Aplikacja(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rejestr Działalności Rolnośrodowiskowej")
        self.geometry("1100x700")
        self.minsize(900, 550)
        self.configure(bg=KOLOR_TLO)
        self._buduj()

    def _buduj(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=KOLOR_TLO, tabmargins=[4,4,0,0])
        style.configure("TNotebook.Tab", font=(CZCIONKA, 10, "bold"),
                         padding=[14,6], background="#CADDED")
        style.map("TNotebook.Tab",
                  background=[("selected", KOLOR_NAV), ("active", KOLOR_AKCENT)],
                  foreground=[("selected", "white"), ("active", "white")])

        # Nagłówek — dwa rzędy: tytuł + pasek gospodarstwa
        header = tk.Frame(self, bg=KOLOR_NAV)
        header.pack(fill=tk.X)

        # Górny rząd: tytuł
        top_row = tk.Frame(header, bg=KOLOR_NAV)
        top_row.pack(fill=tk.X)
        tk.Label(top_row, text="📋  Rejestr Działalności Rolnośrodowiskowej WPR PS 2023–2027",
                 bg=KOLOR_NAV, fg="white",
                 font=(CZCIONKA, 12, "bold")).pack(side=tk.LEFT, padx=16, pady=(8,2))

        # Dolny rząd: przyciski gospodarstwa + info
        bot_row = tk.Frame(header, bg="#163d61")
        bot_row.pack(fill=tk.X)

        # Przyciski wyeksponowane
        def _hbtn(parent, text, cmd, kolor="#2E75B6"):
            return tk.Button(parent, text=text, command=cmd,
                             font=(CZCIONKA, 9, "bold"), relief=tk.FLAT,
                             bg=kolor, fg="white", padx=10, pady=3,
                             activebackground="#1F4E79", cursor="hand2")

        _hbtn(bot_row, "➕ Nowe gospodarstwo", self._nowe_gosp,
              kolor="#217346").pack(side=tk.LEFT, padx=(12,4), pady=4)
        _hbtn(bot_row, "📂 Otwórz...", self._otworz).pack(
              side=tk.LEFT, padx=(0,4), pady=4)
        _hbtn(bot_row, "💾 Zapisz", self._zapisz).pack(
              side=tk.LEFT, padx=(0,4), pady=4)
        _hbtn(bot_row, "✏️ Edytuj dane", self._edytuj_gosp,
              kolor="#5B5B5B").pack(side=tk.LEFT, padx=(0,12), pady=4)

        # Separator pionowy
        tk.Frame(bot_row, bg="#4A7EAA", width=1).pack(
              side=tk.LEFT, fill=tk.Y, pady=4)

        self.lbl_gosp = tk.Label(bot_row,
                                  text="⚠  Brak otwartego gospodarstwa — otwórz lub utwórz nowe",
                                  bg="#163d61", fg="#FFD700",
                                  font=(CZCIONKA, 9, "bold"))
        self.lbl_gosp.pack(side=tk.LEFT, padx=12)

        # Menu (nadal dostępne)
        menubar = tk.Menu(self)
        m_gosp = tk.Menu(menubar, tearoff=0)
        m_gosp.add_command(label="Nowe gospodarstwo",  command=self._nowe_gosp)
        m_gosp.add_command(label="Otwórz...",           command=self._otworz)
        m_gosp.add_command(label="Zapisz",              command=self._zapisz)
        m_gosp.add_separator()
        m_gosp.add_command(label="Edytuj dane gosp.",  command=self._edytuj_gosp)
        m_gosp.add_separator()
        m_gosp.add_command(label="Wyjście",             command=self.destroy)
        menubar.add_cascade(label="Gospodarstwo", menu=m_gosp)
        self.config(menu=menubar)

        # Status
        self.status = StatusBar(self)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.zak_dzialki  = ZakladkaDzialki(self.nb, self.status, self._on_change)
        self.zak_zabiegi  = ZakladkaZabiegi(self.nb, self.status)
        self.zak_wypasy   = ZakladkaWypasy(self.nb, self.status)
        self.zak_kalkulator = ZakladkaKalkulatorWypasu(self.nb, self.status)
        self.zak_kontrola = ZakladkaKontrola(self.nb, self.status)
        self.zak_eksport  = ZakladkaEksport(self.nb, self.status)

        self.nb.add(self.zak_dzialki, text="  🌿 Działki  ")
        self.nb.add(self.zak_zabiegi, text="  🌾 Zabiegi agrotechniczne  ")
        self.nb.add(self.zak_wypasy,  text="  🐄 Wypasy zwierząt  ")
        self.nb.add(self.zak_kalkulator, text="  🐄 Kalkulator wypasu  ")
        self.nb.add(self.zak_kontrola, text="  🔍 Kontrola terminów  ")
        self.nb.add(self.zak_eksport, text="  🖨 Eksport PDF  ")

    def _odswiez_wszystko(self):
        self.zak_dzialki.odswiez()
        self.zak_zabiegi.odswiez()
        self.zak_wypasy.odswiez()
        self.zak_kalkulator.odswiez()
        self.zak_kontrola.odswiez()
        if _gosp:
            self.lbl_gosp.config(
                text=f"✅  {_gosp.rolnik}  |  Nr: {_gosp.nr_identyfikacyjny}  |  "
                     f"Działek: {len(_gosp.dzialki)}  Zabiegów: {len(_gosp.zabiegi)}",
                fg="#90F0B0")

    def _on_change(self):
        self._odswiez_wszystko()

    def _nowe_gosp(self):
        global _gosp, _plik_json
        dlg = DialogGospodarstwo(self)
        self.wait_window(dlg)
        if not dlg.wynik:
            return
        sciezka = filedialog.asksaveasfilename(
            title="Zapisz plik gospodarstwa",
            defaultextension=".json",
            initialfile=f"Rejestr_{dlg.wynik.rolnik.replace(' ', '_')}.json",
            filetypes=[("JSON", "*.json")])
        if not sciezka:
            return
        _gosp = dlg.wynik
        _plik_json = sciezka
        zapisz(_gosp, _plik_json)
        self._odswiez_wszystko()
        self.status.ustaw(f"✅ Utworzono: {Path(sciezka).name}", KOLOR_SUKCES)

    def _otworz(self):
        global _gosp, _plik_json
        sciezka = filedialog.askopenfilename(
            title="Otwórz plik gospodarstwa",
            filetypes=[("JSON", "*.json"), ("Wszystkie", "*.*")])
        if not sciezka:
            return
        try:
            _gosp = wczytaj(sciezka)
            _plik_json = sciezka
            self._odswiez_wszystko()
            self.status.ustaw(f"✅ Otwarto: {Path(sciezka).name}", KOLOR_SUKCES)
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def _zapisz(self):
        if _gosp and _plik_json:
            zapisz(_gosp, _plik_json)
            self.status.ustaw("✅ Zapisano.", KOLOR_SUKCES)

    def _edytuj_gosp(self):
        global _gosp
        if not _gosp:
            return
        dlg = DialogGospodarstwo(self, _gosp)
        self.wait_window(dlg)
        if dlg.wynik:
            _gosp.nazwa              = dlg.wynik.nazwa
            _gosp.rolnik             = dlg.wynik.rolnik
            _gosp.nr_identyfikacyjny = dlg.wynik.nr_identyfikacyjny
            _gosp.warianty           = dlg.wynik.warianty
            _zapisz_auto()
            self._odswiez_wszystko()
            self.status.ustaw("✅ Dane gospodarstwa zaktualizowane.", KOLOR_SUKCES)


def main():
    app = Aplikacja()
    app.mainloop()


if __name__ == "__main__":
    main()
