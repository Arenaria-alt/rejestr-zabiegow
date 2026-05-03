#!/bin/bash
cd "$(dirname "$0")"

# Sprawdź czy Python 3 jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "Nie znaleziono Python 3. Zainstaluj:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-tk"
    echo "  Fedora:        sudo dnf install python3 python3-pip python3-tkinter"
    exit 1
fi

# Sprawdź czy tkinter działa
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "Brakuje modułu tkinter. Zainstaluj:"
    echo "  Ubuntu/Debian: sudo apt install python3-tk"
    echo "  Fedora:        sudo dnf install python3-tkinter"
    exit 1
fi

# Sprawdź biblioteki
python3 -c "import pandas, openpyxl, reportlab" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Instaluję brakujące biblioteki..."
    pip3 install pandas openpyxl reportlab xlrd --break-system-packages 2>/dev/null \
        || pip3 install pandas openpyxl reportlab xlrd
fi

python3 app.py
