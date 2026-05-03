# Rejestr Działalności Rolnośrodowiskowej WPR PS 2023–2027

Aplikacja desktopowa dla doradców rolnośrodowiskowych do prowadzenia rejestru zabiegów agrotechnicznych i wypasów zwierząt zgodnie z wymogami programów ZRSK 2023-2027 i RE2327 PS.

## ⬇️ Pobieranie (Windows)

1. Przejdź do zakładki **[Releases](../../releases/latest)**
2. Pobierz plik `RejestrZabiegow.exe`
3. Uruchom — **nie wymaga instalacji Pythona ani żadnych bibliotek**

## Funkcje

- 📂 **Import z CSV ARiMR** — automatyczne wczytanie działek z pliku pobranego z e-wniosek
- 📋 **Wpis grupowy** — wiele zabiegów × wiele działek w jednym formularzu z kalendarzem
- 🌾 **Zabiegi agrotechniczne** — koszenie, nawożenie, wypas z katalogiem czynności
- 🐄 **Wypasy zwierząt** — osobna zakładka dla działek pastwiskowych i kośno-pastwiskowych
- 🔍 **Kontrola terminów** — automatyczna walidacja terminów i limitów pokosów per wariant
- 🐄 **Kalkulator wypasu** — plan 5-letni z obsadą i obciążeniem pastwiska wg ZRSK 2023-2027
- 🖨️ **Eksport PDF** — zgodny z oficjalnym wzorem ARiMR, z tabelką kontrolną

## Obsługiwane warianty ZRSK

1.1–1.10 i 2.1–2.10 (łąki Natura 2000 i poza Natura 2000), wariant 3 (ekstensywne użytkowanie)

## Wymagania systemowe

- Windows 10 lub nowszy (wersja EXE)
- Linux/macOS: Python 3.9+ z bibliotekami (patrz `requirements.txt`)

## Uruchamianie ze źródeł (Linux/macOS)

```bash
pip install pandas openpyxl reportlab xlrd
python app.py
```

## Licencja

© 2026 Arenaria. Wszelkie prawa zastrzeżone.
