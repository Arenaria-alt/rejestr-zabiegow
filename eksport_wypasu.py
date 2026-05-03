"""
eksport_wypasu.py — generowanie PDF planu wypasu
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, PageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from kalkulator_wypasu import (PlanWypasu, GrupaZwierzat, MIESIACE,
                                MIESIACE_DNI, get_limit)

# ── Czcionki ──────────────────────────────────────────────────────────────────
_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu",
         "C:/Windows/Fonts", os.path.join(os.path.dirname(__file__), "fonts")]

def _ff(n):
    for d in _DIRS:
        p = os.path.join(d, n)
        if os.path.exists(p): return p
    return None

_f = _ff("DejaVuSans.ttf"); _fb = _ff("DejaVuSans-Bold.ttf")
_fi = _ff("DejaVuSans-Oblique.ttf")
if _f:  pdfmetrics.registerFont(TTFont("DJ",  _f))
if _fb: pdfmetrics.registerFont(TTFont("DJB", _fb))
if _fi: pdfmetrics.registerFont(TTFont("DJI", _fi))
F  = "DJ"  if _f  else "Helvetica"
FB = "DJB" if _fb else "Helvetica-Bold"
FI = "DJI" if _fi else "Helvetica-Oblique"

# ── Kolory ────────────────────────────────────────────────────────────────────
C_DARK  = colors.HexColor("#1F4E79")
C_MED   = colors.HexColor("#2E75B6")
C_LIGHT = colors.HexColor("#D6E4F0")
C_GREY  = colors.HexColor("#F5F5F5")
C_GREEN = colors.HexColor("#375623")
C_GLIGHT= colors.HexColor("#EBF5E1")
C_WARN  = colors.HexColor("#FFF3CD")
C_ERR   = colors.HexColor("#FFE0E0")
C_WHITE = colors.white


def _ps(name, **kw):
    d = dict(fontName=F, fontSize=9, leading=12, textColor=colors.black)
    d.update(kw)
    return ParagraphStyle(name, **d)


def _p(txt, **kw):
    return Paragraph(str(txt) if txt else "–", _ps("x", **kw))


def _tbl(data, col_widths, extra_style=None):
    base = [
        ("FONTNAME",    (0, 0), (-1, 0),  FB),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("BACKGROUND",  (0, 0), (-1, 0),  C_DARK),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  C_WHITE),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME",    (0, 1), (-1, -1), F),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_GREY]),
        ("GRID",        (0, 0), (-1, -1), 0.3, colors.HexColor("#BBBBBB")),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0,0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",(0, 0), (-1, -1), 3),
    ]
    if extra_style:
        base.extend(extra_style)
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(base))
    return t


def _kolor_statusu(status: str):
    return {"OK": C_GLIGHT, "NISKA": C_WARN,
            "ZA_WYSOKA": C_ERR, "ZA_WYSOKIE": C_ERR}.get(status, C_WHITE)


def _ikona_statusu(status: str) -> str:
    return {"OK": "✓", "NISKA": "↓", "ZA_WYSOKA": "↑", "ZA_WYSOKIE": "↑"}.get(status, "?")


def eksportuj_plan_wypasu(
    plany: list[PlanWypasu],
    sciezka: str,
    rolnik: str,
    nr_id: str,
    nazwa_gosp: str,
    autor: str = "",
    wariant_raportu: str = "pelny",  # "pelny" lub "roczny"
    rok_raportu: int = 0,
):
    """Generuje PDF planu wypasu dla listy działek."""

    def _stopka(canvas, doc):
        canvas.saveState()
        W, H = landscape(A4)
        canvas.setFont(FB, 7); canvas.setFillColor(C_DARK)
        canvas.drawString(0.8*cm, H - 0.6*cm,
                          f"Plan wypasu – {rolnik}  |  Nr id: {nr_id}")
        canvas.setFont(F, 6); canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawRightString(W - 0.8*cm, H - 0.6*cm,
                               f"Strona {doc.page}  |  "
                               f"{datetime.now().strftime('%d.%m.%Y %H:%M')}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        sciezka, pagesize=landscape(A4),
        leftMargin=0.8*cm, rightMargin=0.8*cm,
        topMargin=1.0*cm, bottomMargin=1.0*cm,
    )
    story = []

    # ── Strona tytułowa ───────────────────────────────────────────────────────
    story.append(Paragraph(
        "PLAN WYPASU ZWIERZĄT",
        _ps("T", fontName=FB, fontSize=16, textColor=C_DARK,
            spaceAfter=4, alignment=1)))
    story.append(Paragraph(
        "Nieobligatoryjny załącznik do Planu Działalności Rolnośrodowiskowej",
        _ps("sub", fontName=FI, fontSize=10, textColor=colors.HexColor("#555555"),
            spaceAfter=8, alignment=1)))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_DARK, spaceAfter=10))

    # Dane podstawowe
    story.append(_tbl(
        [[_p("Rolnik / zarządca:", fontName=FB), _p(rolnik)],
         [_p("Nr identyfikacyjny:", fontName=FB), _p(nr_id)],
         [_p("Nazwa gospodarstwa:", fontName=FB), _p(nazwa_gosp)],
         [_p("Okres realizacji:", fontName=FB),
          _p(f"{plany[0].rok_od}–{plany[0].rok_do}" if plany else "")],
         [_p("Autor planu:", fontName=FB), _p(autor)],
         [_p("Data opracowania:", fontName=FB),
          _p(plany[0].data_opracowania if plany else "")],
         [_p("Podstawa prawna:", fontName=FB),
          _p("Rozporządzenie MRiRW z dnia 13.03.2023 r. w sprawie szczegółowych "
             "warunków i trybu przyznawania płatności ZRSK PS WPR 2023-2027 "
             "(Dz.U. 2023 poz. 493 z późn. zm.)")]],
        [5.5*cm, 20*cm]
    ))
    story.append(Spacer(1, 0.5*cm))

    # Podsumowanie działek
    story.append(Paragraph("Zestawienie działek objętych planem:",
                            _ps("hdr", fontName=FB, fontSize=10,
                                textColor=C_DARK, spaceAfter=4)))

    sum_nagl = [_p(h, fontName=FB, textColor=colors.white) for h in
                ["Dz. rolna", "Wariant", "Pow. [ha]",
                 "Obsada [DJP/ha]", "Limit obsady", "Obciążenie\n[DJP/ha]",
                 "Limit obciążenia", "Rezerwa\nobsady", "Ocena"]]
    sum_dane = [sum_nagl]
    for plan in plany:
        obs_st = plan.status_obsady
        obci_st = plan.status_obciazenia
        ok = obs_st == "OK" and obci_st == "OK"
        ocena = "✓ SPEŁNIONE" if ok else ("↑ PRZEKROCZONO" if "ZA_" in obs_st or "ZA_" in obci_st else "↓ ZA NISKA")
        sum_dane.append([
            _p(plan.dzialka_ozn, fontName=FB),
            _p(plan.wariant),
            _p(f"{plan.pow_ha:.2f}".replace(".", ",")),
            _p(f"{plan.obsada:.3f}".replace(".", ",")),
            _p(f"{plan.obsada_min:.1f}–{plan.obsada_max:.1f}".replace(".", ",")),
            _p(f"{plan.obciazenie:.3f}".replace(".", ",")),
            _p(f"do {plan.obciazenie_max:.1f}".replace(".", ",")),
            _p(f"{plan.rezerwa_obsady_pct():.1f}%".replace(".", ",")),
            _p(ocena),
        ])
    cw = [1.5*cm, 1.8*cm, 2.0*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.2*cm, 3.0*cm]
    extra = []
    for i, plan in enumerate(plany, 1):
        obs_st = plan.status_obsady
        obci_st = plan.status_obciazenia
        kolor = _kolor_statusu(obs_st if "ZA_" in obs_st else obci_st)
        if kolor != C_WHITE:
            extra.append(("BACKGROUND", (0, i), (-1, i), kolor))
    story.append(_tbl(sum_dane, cw, extra))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "✓ SPEŁNIONE = obsada i obciążenie w dopuszczalnych granicach  |  "
        "↑ PRZEKROCZONO = powyżej limitu  |  ↓ ZA NISKA = poniżej minimum",
        _ps("leg", fontSize=7, textColor=colors.HexColor("#555555"))))

    # ── Szczegóły per działka ─────────────────────────────────────────────────
    for plan in plany:
        story.append(PageBreak())
        limit = get_limit(plan.wariant)

        story.append(Paragraph(
            f"Działka rolna: {plan.dzialka_ozn}  |  Wariant: {plan.wariant}  |  "
            f"Powierzchnia: {plan.pow_ha:.2f} ha".replace(".", ","),
            _ps("dz", fontName=FB, fontSize=11, textColor=C_DARK, spaceAfter=2)))
        story.append(Paragraph(limit.opis,
                                _ps("lim", fontName=FI, fontSize=8,
                                    textColor=colors.HexColor("#375623"),
                                    spaceAfter=6)))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                 color=C_LIGHT, spaceAfter=6))

        # Tabela grup zwierząt z dniami per miesiąc
        nagl_grupy = ([_p("Grupa zwierząt", fontName=FB, textColor=C_WHITE),
                       _p("Szt.", fontName=FB, textColor=C_WHITE),
                       _p("DJP\nwsp.", fontName=FB, textColor=C_WHITE),
                       _p("DJP\nłącznie", fontName=FB, textColor=C_WHITE)]
                      + [_p(m, fontName=FB, textColor=C_WHITE) for m in MIESIACE]
                      + [_p("Dni\nłącznie", fontName=FB, textColor=C_WHITE),
                         _p("Punkty", fontName=FB, textColor=C_WHITE)])

        dane_grupy = [nagl_grupy]
        for g in plan.grupy:
            if g.liczba == 0:
                continue
            wiersz = [
                _p(g.gatunek),
                _p(str(g.liczba)),
                _p(f"{g.djp_wsp:.2f}".replace(".", ",")),
                _p(f"{g.djp_lacznie:.2f}".replace(".", ",")),
            ]
            for m in MIESIACE:
                d = g.dni.get(m, 0)
                wiersz.append(_p(str(d) if d > 0 else "–"))
            wiersz.append(_p(str(g.dni_lacznie)))
            wiersz.append(_p(f"{g.punkty:.1f}".replace(".", ",")))
            dane_grupy.append(wiersz)

        # Wiersz sumy
        suma_djp = plan.djp_lacznie
        suma_pkt = plan.punkty_lacznie
        suma_dni_m = {m: sum(g.dni.get(m, 0) * g.liczba for g in plan.grupy)
                      for m in MIESIACE}
        wiersz_suma = [
            _p("SUMA / WYNIK", fontName=FB),
            _p(""),
            _p(""),
            _p(f"{suma_djp:.2f}".replace(".", ","), fontName=FB),
        ]
        for m in MIESIACE:
            wiersz_suma.append(_p(str(suma_dni_m[m]) if suma_dni_m[m] > 0 else "–"))
        wiersz_suma.append(_p(""))
        wiersz_suma.append(_p(f"{suma_pkt:.1f}".replace(".", ","), fontName=FB))
        dane_grupy.append(wiersz_suma)

        # Szerokości kolumn
        cw_g = [4.5*cm, 1.2*cm, 1.3*cm, 1.5*cm] + [1.3*cm]*8 + [1.4*cm, 1.8*cm]

        extra_g = [
            ("BACKGROUND", (0, len(dane_grupy)-1), (-1, len(dane_grupy)-1), C_LIGHT),
            ("FONTNAME",   (0, len(dane_grupy)-1), (-1, len(dane_grupy)-1), FB),
        ]
        story.append(_tbl(dane_grupy, cw_g, extra_g))
        story.append(Spacer(1, 0.4*cm))

        # Wyniki kalkulacji
        obs_st   = plan.status_obsady
        obci_st  = plan.status_obciazenia
        rez_obs  = plan.rezerwa_obsady_pct()
        rez_obc  = plan.rezerwa_obciazenia_pct()

        kol_obs  = _kolor_statusu(obs_st)
        kol_obc  = _kolor_statusu(obci_st)

        wyniki_data = [
            [_p("Wskaźnik", fontName=FB, textColor=C_WHITE),
             _p("Wartość planowana", fontName=FB, textColor=C_WHITE),
             _p("Limit min.", fontName=FB, textColor=C_WHITE),
             _p("Limit max.", fontName=FB, textColor=C_WHITE),
             _p("Rezerwa do limitu", fontName=FB, textColor=C_WHITE),
             _p("Ocena", fontName=FB, textColor=C_WHITE)],
            [_p("Obsada zwierząt [DJP/ha]"),
             _p(f"{plan.obsada:.3f}".replace(".", ","), fontName=FB),
             _p(f"{plan.obsada_min:.2f}".replace(".", ",")),
             _p(f"{plan.obsada_max:.2f}".replace(".", ",")),
             _p(f"{rez_obs:.1f}%".replace(".", ",")),
             _p(f"{_ikona_statusu(obs_st)} {obs_st.replace('_', ' ')}")],
            [_p("Obciążenie pastwiska [DJP/ha]"),
             _p(f"{plan.obciazenie:.3f}".replace(".", ","), fontName=FB),
             _p("–"),
             _p(f"{plan.obciazenie_max:.1f}".replace(".", ",")),
             _p(f"{rez_obc:.1f}%".replace(".", ",")),
             _p(f"{_ikona_statusu(obci_st)} {obci_st.replace('_', ' ')}")],
        ]
        extra_w = [
            ("BACKGROUND", (0, 1), (-1, 1), kol_obs),
            ("BACKGROUND", (0, 2), (-1, 2), kol_obc),
        ]
        story.append(_tbl(wyniki_data,
                          [6.0*cm, 3.0*cm, 2.5*cm, 2.5*cm, 3.0*cm, 3.5*cm],
                          extra_w))
        story.append(Spacer(1, 0.3*cm))

        # Korekty jeśli są
        if plan.korekty:
            story.append(Paragraph("Historia korekt planu:",
                                    _ps("kh", fontName=FB, fontSize=9,
                                        textColor=C_DARK, spaceAfter=3)))
            kor_nagl = [_p(h, fontName=FB, textColor=C_WHITE)
                        for h in ["Nr korekty", "Data", "Przyczyna", "Autor"]]
            kor_dane = [kor_nagl]
            for k in plan.korekty:
                kor_dane.append([
                    _p(str(k.get("nr", ""))),
                    _p(k.get("data", "")),
                    _p(k.get("przyczyna", "")),
                    _p(k.get("autor", "")),
                ])
            story.append(_tbl(kor_dane, [2.0*cm, 3.0*cm, 14.0*cm, 4.0*cm]))
            story.append(Spacer(1, 0.2*cm))

        # Uwagi
        if plan.uwagi:
            story.append(Paragraph(
                f"Uwagi: {plan.uwagi}",
                _ps("uw", fontName=FI, fontSize=8,
                    textColor=colors.HexColor("#444444"))))

    # ── Strona podpisów ───────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("POTWIERDZENIE OPRACOWANIA PLANU WYPASU",
                            _ps("podp", fontName=FB, fontSize=12,
                                textColor=C_DARK, spaceAfter=10, alignment=1)))

    story.append(_tbl([
        [_p("Opracował doradca/ekspert:", fontName=FB), _p(autor), _p("Data:"), _p("")],
        [_p("Podpis doradcy:", fontName=FB), _p(""), _p(""), _p("")],
        [_p("Przyjął rolnik/zarządca:", fontName=FB), _p(rolnik), _p("Data:"), _p("")],
        [_p("Podpis rolnika:", fontName=FB), _p(""), _p(""), _p("")],
    ], [5.0*cm, 10.0*cm, 2.5*cm, 8.5*cm]))

    doc.build(story, onFirstPage=_stopka, onLaterPages=_stopka)
