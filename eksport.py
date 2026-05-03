"""
eksport.py — generowanie PDF rejestru zabiegów agrotechnicznych
Format: poziomy A4, czcionka DejaVu (polskie znaki)
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, PageBreak, HRFlowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dane import Gospodarstwo, ZabiegAgrotechniczny, WpisWypasu

def _skroc_nr_ewid(nr: str) -> str:
    """Zwraca pełny numer działki ewidencyjnej (bez skracania)."""
    return nr if nr else "–"


_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "C:/Windows/Fonts",
    os.path.join(os.path.dirname(__file__), "fonts"),
]

def _znajdz_font(nazwa):
    for d in _FONT_DIRS:
        p = os.path.join(d, nazwa)
        if os.path.exists(p):
            return p
    return None

_f  = _znajdz_font("DejaVuSans.ttf")
_fb = _znajdz_font("DejaVuSans-Bold.ttf")
_fi = _znajdz_font("DejaVuSans-Oblique.ttf")

if _f:  pdfmetrics.registerFont(TTFont("DJ",  _f))
if _fb: pdfmetrics.registerFont(TTFont("DJB", _fb))
if _fi: pdfmetrics.registerFont(TTFont("DJI", _fi))

F  = "DJ"  if _f  else "Helvetica"
FB = "DJB" if _fb else "Helvetica-Bold"
FI = "DJI" if _fi else "Helvetica-Oblique"

# ── Kolory ────────────────────────────────────────────────────────────────────
C_DARK   = colors.HexColor("#1F4E79")
C_MED    = colors.HexColor("#2E75B6")
C_LIGHT  = colors.HexColor("#D6E4F0")
C_GREY   = colors.HexColor("#F5F5F5")
C_WHITE  = colors.white
C_BLACK  = colors.black
C_GREEN  = colors.HexColor("#375623")
C_GLIGHT = colors.HexColor("#EBF5E1")


def _styl(name, **kwargs) -> ParagraphStyle:
    base = dict(fontName=F, fontSize=9, leading=12, textColor=C_BLACK)
    base.update(kwargs)
    return ParagraphStyle(name, **base)


def _p(txt, **kwargs) -> Paragraph:
    return Paragraph(str(txt) if txt else "–", _styl("x", **kwargs))


def _tbl_styl(extra=None) -> TableStyle:
    base = [
        ("FONTNAME",    (0, 0), (-1, 0),  FB),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("BACKGROUND",  (0, 0), (-1, 0),  C_DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  C_WHITE),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",    (0, 1), (-1, -1), F),
        ("FONTSIZE",    (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_GREY]),
        ("GRID",        (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0,0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",(0, 0), (-1, -1), 3),
    ]
    if extra:
        base.extend(extra)
    return TableStyle(base)


def _par_nagl(txt) -> Paragraph:
    return Paragraph(txt, ParagraphStyle("H", fontName=FB, fontSize=8,
                                          textColor=C_WHITE, leading=10))


# ── Strona tytułowa ───────────────────────────────────────────────────────────

def _strona_tytulowa(story, gosp: Gospodarstwo):
    PS_TYTUL = _styl("tytul", fontName=FB, fontSize=14, textColor=C_DARK,
                      spaceAfter=6, alignment=1)
    PS_NORM  = _styl("norm", fontSize=10, spaceAfter=4)
    PS_BOLD  = _styl("bold", fontName=FB, fontSize=10, spaceAfter=4)
    PS_SMALL = _styl("small", fontSize=8, textColor=colors.HexColor("#555555"))

    story.append(Paragraph(
        "Rejestr działalności rolnośrodowiskowej lub działalności ekologicznej<br/>"
        "lub zabiegów agrotechnicznych WPR PS 2023–2027", PS_TYTUL))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_DARK, spaceAfter=10))

    # Dane rolnika
    dane_tabela = [
        [_p("Rolnik/zarządca:", fontName=FB), _p(gosp.rolnik)],
        [_p("Numer identyfikacyjny:", fontName=FB), _p(gosp.nr_identyfikacyjny)],
        [_p("Nazwa gospodarstwa:", fontName=FB), _p(gosp.nazwa)],
    ]
    t = Table(dane_tabela, colWidths=[6*cm, 12*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), F),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("TOPPADDING",(0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW", (0,-1), (-1,-1), 0.5, C_LIGHT),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Tabela wariantów
    story.append(Paragraph("Pakiety / interwencje / warianty / praktyki realizowane w gospodarstwie:",
                            _styl("hdr", fontName=FB, fontSize=10, textColor=C_DARK, spaceAfter=4)))

    war_dane = [[_par_nagl("Lp."), _par_nagl("Kod pakietu/interwencji/wariantu/praktyki"),
                 _par_nagl("Działanie/interwencja/praktyka")]]
    OPISY = {
        "1.1": "ZRSK2327 – Zmiennowilgotne łąki trzęślicowe (Natura 2000)",
        "1.2": "ZRSK2327 – Zalewowe łąki selernicowe (Natura 2000)",
        "1.3": "ZRSK2327 – Murawy (Natura 2000)",
        "1.4": "ZRSK2327 – Półnaturalne łąki wilgotne (Natura 2000)",
        "1.5": "ZRSK2327 – Półnaturalne łąki świeże (Natura 2000)",
        "1.6.1": "ZRSK2327 – Torfowiska wymogi kluczowe (Natura 2000)",
        "1.6.2": "ZRSK2327 – Torfowiska wymogi kluczowe i uzupełniające (Natura 2000)",
        "1.7": "ZRSK2327 – Siedliska lęgowe rzadkich gatunków ptaków (Natura 2000)",
        "1.8": "ZRSK2327 – Siedliska lęgowe dubelta i kulika (Natura 2000)",
        "1.9": "ZRSK2327 – Siedliska lęgowe wodniczki (Natura 2000)",
        "1.10": "ZRSK2327 – Siedliska lęgowe derkacza (Natura 2000)",
        "2.1": "ZRSK2327 – Zmiennowilgotne łąki trzęślicowe (poza Natura 2000)",
        "2.2": "ZRSK2327 – Zalewowe łąki selernicowe (poza Natura 2000)",
        "2.3": "ZRSK2327 – Murawy (poza Natura 2000)",
        "2.4": "ZRSK2327 – Półnaturalne łąki wilgotne (poza Natura 2000)",
        "2.5": "ZRSK2327 – Półnaturalne łąki świeże (poza Natura 2000)",
        "2.6.1": "ZRSK2327 – Torfowiska wymogi kluczowe (poza Natura 2000)",
        "2.6.2": "ZRSK2327 – Torfowiska wymogi kluczowe i uzupełniające (poza Natura 2000)",
        "2.7": "ZRSK2327 – Siedliska lęgowe rzadkich gatunków ptaków (poza Natura 2000)",
        "2.8": "ZRSK2327 – Siedliska lęgowe dubelta i kulika (poza Natura 2000)",
        "2.9": "ZRSK2327 – Siedliska lęgowe wodniczki (poza Natura 2000)",
        "2.10": "ZRSK2327 – Siedliska lęgowe derkacza (poza Natura 2000)",
        "3":   "ZRSK2327 – Ekstensywne użytkowanie łąk i pastwisk (Natura 2000)",
    }
    for i, w in enumerate(gosp.warianty, 1):
        opis = OPISY.get(w, f"ZRSK2327 – wariant {w}")
        war_dane.append([
            _p(str(i)),
            _p(w),
            _p(opis),
        ])
    # Puste wiersze do uzupełnienia
    for i in range(len(gosp.warianty) + 1, 8):
        war_dane.append([_p(str(i)), _p(""), _p("")])

    t2 = Table(war_dane, colWidths=[1.5*cm, 5*cm, 20*cm])
    t2.setStyle(_tbl_styl([
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [C_WHITE, C_GREY]),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "* wpisać kod pakietu/interwencji/wariantu/praktyki realizowanej w gospodarstwie",
        _styl("foot", fontSize=7, textColor=colors.HexColor("#555555"))))


# ── Wykaz działań agrotechnicznych ───────────────────────────────────────────

def _wykaz_zabiegow(story, gosp: Gospodarstwo,
                    data_od: str = "", data_do: str = ""):
    """Generuje strony z wykazem działań agrotechnicznych."""

    story.append(PageBreak())
    story.append(Paragraph("WYKAZ DZIAŁAŃ AGROTECHNICZNYCH",
                            _styl("tytul2", fontName=FB, fontSize=12,
                                  textColor=C_DARK, spaceAfter=2)))

    # Filtruj zabiegi wg zakresu dat
    zabiegi = _filtruj_wg_dat(gosp.zabiegi, data_od, data_do)

    if not zabiegi:
        story.append(Paragraph("Brak zabiegów w wybranym zakresie dat.",
                                _styl("brak", fontSize=9, textColor=colors.grey)))
        return

    # Info o zakresie
    if data_od or data_do:
        info = f"Zakres: {data_od or '–'} → {data_do or '–'}   |   Wpisów: {len(zabiegi)}"
    else:
        info = f"Wszystkie wpisy   |   Wpisów: {len(zabiegi)}"
    story.append(Paragraph(info, _styl("info", fontSize=8,
                                        textColor=colors.HexColor("#555555"),
                                        spaceAfter=6)))

    nagl = [
        _par_nagl("1\nOzn.\ndz."),
        _par_nagl("2\nNr działki\newidencyjnej"),
        _par_nagl("3\nData\n[dd.mm.rrrr]"),
        _par_nagl("4\nPow.\n[ha]"),
        _par_nagl("5\nRodzaj\nużytkowania"),
        _par_nagl("6\nRodzaj wykonywanej\nczynności"),
        _par_nagl("7\nNazwa środka/\nnawozu"),
        _par_nagl("8\nIlość\nśrodka"),
        _par_nagl("9\nSymbol działania/\nnr wariantu"),
        _par_nagl("10\nUwagi / pow.\nczynności"),
    ]

    tabela = [nagl]
    for z in zabiegi:
        tabela.append([
            _p(z.oznaczenie, fontName=FB),
            _p(_skroc_nr_ewid(z.nr_ewid)),
            _p(z.data),
            _p(f"{z.pow_ha:.2f}".replace(".", ",")),
            _p(z.rodzaj_uzytkowania),
            _p(z.czynnosc),
            _p(z.srodek or "–"),
            _p(z.ilosc or "–"),
            _p(getattr(z, "wariant", "") or z.symbol_dzialania),
            _p(z.uwagi),
        ])

    col_w = [1.2*cm, 4.5*cm, 2.2*cm, 1.5*cm, 2.5*cm,
             5.5*cm, 3.0*cm, 2.0*cm, 2.0*cm, 3.6*cm]

    t = Table(tabela, colWidths=col_w, repeatRows=1)
    t.setStyle(_tbl_styl())
    story.append(t)

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "* zabiegi agrotechniczne, pielęgnacyjne, zabiegi środkami ochrony roślin, nawożenie i inne",
        _styl("foot", fontSize=6, textColor=colors.HexColor("#777777"))))


# ── Wykaz wypasów ─────────────────────────────────────────────────────────────

def _wykaz_wypasow(story, gosp: Gospodarstwo,
                   data_od: str = "", data_do: str = ""):
    """Generuje strony z wykazem wypasów zwierząt."""

    story.append(PageBreak())
    story.append(Paragraph("WYKAZ WYKONANYCH WYPASÓW",
                            _styl("tytul3", fontName=FB, fontSize=12,
                                  textColor=C_DARK, spaceAfter=2)))

    wypasy = _filtruj_wg_dat(gosp.wypasy, data_od, data_do)

    if not wypasy:
        story.append(Paragraph("Brak wpisów wypasów w wybranym zakresie dat.",
                                _styl("brak", fontSize=9, textColor=colors.grey)))
        return

    if data_od or data_do:
        info = f"Zakres: {data_od or '–'} → {data_do or '–'}   |   Wpisów: {len(wypasy)}"
    else:
        info = f"Wszystkie wpisy   |   Wpisów: {len(wypasy)}"
    story.append(Paragraph(info, _styl("info", fontSize=8,
                                        textColor=colors.HexColor("#555555"),
                                        spaceAfter=6)))

    nagl = [
        _par_nagl("1\nOzn.\ndz."),
        _par_nagl("2\nNr działki\newidencyjnej"),
        _par_nagl("3\nData wypasu\n[dd.mm.rrrr]"),
        _par_nagl("4\nPow.\n[ha]"),
        _par_nagl("5\nGatunek\nzwierząt"),
        _par_nagl("6\nLiczba\nzwierząt"),
        _par_nagl("7\nSymbol\ndziałania"),
        _par_nagl("8\nUwagi / rodzaj wypasu\n(wolny/kwaterowy)"),
    ]

    tabela = [nagl]
    for w in wypasy:
        tabela.append([
            _p(w.oznaczenie, fontName=FB),
            _p(_skroc_nr_ewid(w.nr_ewid)),
            _p(w.data),
            _p(f"{w.pow_ha:.2f}".replace(".", ",")),
            _p(w.gatunek),
            _p(w.liczba),
            _p(getattr(w, "wariant", "") or w.symbol_dzialania),
            _p(w.uwagi),
        ])

    col_w = [1.2*cm, 4.5*cm, 2.5*cm, 1.8*cm, 3.5*cm, 3.5*cm, 2.0*cm, 8.5*cm]
    t = Table(tabela, colWidths=col_w, repeatRows=1)
    t.setStyle(_tbl_styl())
    story.append(t)


# ── Filtrowanie wg dat ────────────────────────────────────────────────────────

def _parse_date(s: str):
    """Parsuje datę z formatu dd.mm.yyyy lub yyyy-mm-dd."""
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _filtruj_wg_dat(wpisy, data_od: str, data_do: str):
    """Filtruje listę wpisów wg zakresu dat."""
    d_od = _parse_date(data_od)
    d_do = _parse_date(data_do)
    if not d_od and not d_do:
        return sorted(wpisy, key=lambda x: _parse_date(x.data) or datetime.min)

    wynik = []
    for w in wpisy:
        d = _parse_date(w.data)
        if d is None:
            continue
        if d_od and d < d_od:
            continue
        if d_do and d > d_do:
            continue
        wynik.append(w)
    return sorted(wynik, key=lambda x: _parse_date(x.data) or datetime.min)


# ── Główna funkcja eksportu ───────────────────────────────────────────────────

def eksportuj_pdf(
    gosp: Gospodarstwo,
    sciezka: str,
    eksportuj_strone_tytulowa: bool = True,
    eksportuj_zabiegi: bool = True,
    eksportuj_wypasy: bool = True,
    data_od_zabiegi: str = "",
    data_do_zabiegi: str = "",
    data_od_wypasy: str = "",
    data_do_wypasy: str = "",
):
    """Generuje kompletny PDF rejestru."""

    def _naglowek_stopka(canvas, doc):
        canvas.saveState()
        W, H = landscape(A4)

        # Nagłówek strony
        canvas.setFont(FB, 7)
        canvas.setFillColor(C_DARK)
        canvas.drawString(0.8*cm, H - 0.6*cm,
                          f"Rejestr – {gosp.rolnik}  |  Nr id: {gosp.nr_identyfikacyjny}")
        canvas.setFont(F, 6)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawRightString(W - 0.8*cm, H - 0.6*cm,
                               f"Strona {doc.page}  |  "
                               f"Wygenerowano: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

        # ── Tabelka kontrolna ──────────────────────────────────────────────
        # Pozycja: 0.4cm od dołu, pełna szerokość strony minus marginesy
        tbl_x     = 0.8*cm
        tbl_y     = 0.4*cm
        tbl_w     = W - 1.6*cm
        tbl_h     = 2.5*cm
        row1_h    = 0.7*cm   # wiersz nagłówkowy
        row2_h    = 0.9*cm   # wiersz pusty (do wpisania)
        row3_h    = tbl_h - row1_h - row2_h

        # Szerokości kolumn (proporcje z oryginału ARiMR)
        label_w   = 3.5*cm
        col_widths = [
            label_w,                          # "Pola wypełniane..."
            (tbl_w - label_w) * 0.18,         # Data kontroli
            (tbl_w - label_w) * 0.20,         # Nazwisko inspektora
            (tbl_w - label_w) * 0.14,         # Podpis inspektora
            (tbl_w - label_w) * 0.24,         # Nazwisko osoby obecnej
            (tbl_w - label_w) * 0.24,         # Podpis osoby obecnej
        ]

        # Szare tło całej tabelki
        canvas.setFillColor(colors.HexColor("#F0F0F0"))
        canvas.setStrokeColor(colors.HexColor("#888888"))
        canvas.setLineWidth(0.4)
        canvas.rect(tbl_x, tbl_y, tbl_w, tbl_h, fill=1, stroke=1)

        # Lewa kolumna — lekko ciemniejsze tło
        canvas.setFillColor(colors.HexColor("#E0E0E0"))
        canvas.rect(tbl_x, tbl_y, label_w, tbl_h, fill=1, stroke=0)

        # Linie pionowe kolumn
        canvas.setStrokeColor(colors.HexColor("#888888"))
        x = tbl_x
        for w in col_widths[:-1]:
            x += w
            canvas.line(x, tbl_y, x, tbl_y + tbl_h)

        # Linia pozioma między wierszem nagłówkowym a pustym
        canvas.line(tbl_x + label_w, tbl_y + row2_h + row3_h,
                    tbl_x + tbl_w,   tbl_y + row2_h + row3_h)
        # Linia pozioma między wierszem pustym a ostatnim
        canvas.line(tbl_x + label_w, tbl_y + row3_h,
                    tbl_x + tbl_w,   tbl_y + row3_h)
        # Ramka zewnętrzna na wierzchu
        canvas.rect(tbl_x, tbl_y, tbl_w, tbl_h, fill=0, stroke=1)

        # Etykieta lewa — rysuj od góry do dołu (od górnej krawędzi - padding)
        canvas.setFillColor(colors.black)
        _tekst_wieloliniowy(canvas, "Pola wypełniane podczas kontroli na miejscu",
                             tbl_x + 0.15*cm,
                             tbl_y + tbl_h - 0.3*cm,   # zacznij od góry
                             label_w - 0.2*cm, 6.5, 8,
                             od_gory=True)

        # Nagłówki kolumn — w wierszu nagłówkowym (górny wiersz prawej części)
        naglowki = [
            "Data kontroli na miejscu",
            "Nazwisko i imię inspektora terenowego",
            "Podpis inspektora terenowego",
            "Nazwisko i imię osoby obecnej przy kontroli",
            "Podpis osoby obecnej przy kontroli",
        ]
        x = tbl_x + label_w
        for i, (txt, cw) in enumerate(zip(naglowki, col_widths[1:])):
            cy = tbl_y + tbl_h - 0.3*cm   # nagłówki od góry
            _tekst_wieloliniowy(canvas, txt,
                                 x + 0.1*cm, cy,
                                 cw - 0.2*cm, 6, 7.5,
                                 od_gory=True)
            x += cw

        canvas.restoreState()

    def _tekst_wieloliniowy(canvas, tekst, x, y, max_w, font_size, leading,
                             od_gory=False):
        """Łamie tekst na wiersze.
        od_gory=True: y to górna krawędź, tekst idzie w dół
        od_gory=False: y to dolna krawędź, tekst idzie w górę (stare zachowanie)
        """
        canvas.setFont(F, font_size)
        canvas.setFillColor(colors.black)
        slowa = tekst.split()
        linie = []
        biezaca = ""
        for slowo in slowa:
            test = (biezaca + " " + slowo).strip()
            if canvas.stringWidth(test, F, font_size) <= max_w:
                biezaca = test
            else:
                if biezaca:
                    linie.append(biezaca)
                biezaca = slowo
        if biezaca:
            linie.append(biezaca)
        for i, linia in enumerate(linie):
            if od_gory:
                canvas.drawString(x, y - i * leading, linia)
            else:
                canvas.drawString(x, y + i * leading, linia)

    doc = SimpleDocTemplate(
        sciezka,
        pagesize=landscape(A4),
        leftMargin=0.8*cm, rightMargin=0.8*cm,
        topMargin=1.0*cm, bottomMargin=3.2*cm,
    )

    story = []

    if eksportuj_strone_tytulowa:
        _strona_tytulowa(story, gosp)

    if eksportuj_zabiegi:
        _wykaz_zabiegow(story, gosp, data_od_zabiegi, data_do_zabiegi)

    if eksportuj_wypasy:
        _wykaz_wypasow(story, gosp, data_od_wypasy, data_do_wypasy)

    if not story:
        story.append(Paragraph("Nie wybrano żadnych sekcji do eksportu.",
                                _styl("err", fontSize=10)))

    doc.build(story, onFirstPage=_naglowek_stopka, onLaterPages=_naglowek_stopka)
