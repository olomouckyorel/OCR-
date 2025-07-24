@echo off
echo ========================================
echo    PREPROCESSING - RAWDATA TO INPUT
echo ========================================
echo.
echo 🎯 ÚKOL:
echo    - Zkontroluje velikost souborů v data\rawdata\
echo    - Soubory > 4MB zkomprimuje pod 4MB
echo    - Všechny soubory PŘESUNE do data\input\
echo.

REM Přejdi do správného adresáře
cd /d "%~dp0"
echo 📁 Adresář: %CD%
echo.

REM Aktivuj virtual environment pokud existuje
if exist "..\venv\Scripts\activate.bat" (
    echo 🐍 Aktivuji virtual environment...
    call ..\venv\Scripts\activate.bat
    echo ✅ Virtual environment aktivován
) else if exist "venv\Scripts\activate.bat" (
    echo 🐍 Aktivuji virtual environment...
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment aktivován
) else (
    echo ⚠️  Virtual environment nenalezen - používám systémový Python
)
echo.

REM Zkontroluj jestli existují potřebné soubory
if not exist "src\file_preprocessor.py" (
    echo ❌ CHYBA: Soubor src\file_preprocessor.py neexistuje!
    goto :error
)

if not exist "data\rawdata" (
    echo ❌ CHYBA: Složka data\rawdata neexistuje!
    echo 💡 Vložte soubory do data\rawdata\ před spuštěním
    goto :error
)

REM Zkontroluj jestli jsou soubory v rawdata
echo 🔍 Kontroluji soubory v data\rawdata...
dir /b "data\rawdata\*.pdf" "data\rawdata\*.jpg" "data\rawdata\*.jpeg" "data\rawdata\*.png" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Žádné podporované soubory v data\rawdata\
    echo 💡 Podporované formáty: PDF, JPG, JPEG, PNG, TIFF, BMP
    goto :error
)

echo ✅ Soubory nalezeny v data\rawdata\
echo.

echo 🚀 Spouštím preprocessing (rawdata → input)...
echo 📏 Soubory > 4MB budou komprimovány a přesunuty
echo 📋 Soubory ≤ 4MB budou přesunuty beze změny
echo.
echo ============= VÝSTUP SKRIPTU =============

REM Spusť file preprocessor
py src\file_preprocessor.py

echo.
echo ============= KONEC VÝSTUPU =============
echo.

if %ERRORLEVEL% EQU 0 (
    echo ✅ Preprocessing dokončen úspěšně!
    echo.
    echo 📁 VÝSLEDKY:
    echo    - data\input\ (připravené soubory ≤ 4MB)
    echo    - data\rawdata\ (prázdná - soubory přesunuty)
    echo.
    echo 🎯 DALŠÍ KROKY:
    echo    1. Spusť azure_test.bat (OCR analýza)
    echo    2. Spusť google_simple.bat (upload do Google Sheets)
) else (
    echo ❌ Preprocessing skončil s chybou (kód: %ERRORLEVEL%)
    echo.
    echo 💡 Možné příčiny:
    echo    - Chybí Python dependencies: pip install Pillow
    echo    - Poškozené soubory v rawdata
    echo    - Nedostatek místa na disku
)

goto :end

:error
echo.
echo ❌ Preprocessing nelze spustit kvůli chybám výše
echo.

:end
echo.
pause 