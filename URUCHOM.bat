@echo off
cd /d "%~dp0"
python app.py
if errorlevel 1 (
    echo.
    echo Blad uruchomienia. Sprawdz czy zainstalowano biblioteki:
    echo   pip install pandas openpyxl reportlab xlrd
    pause
)
