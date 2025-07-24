@echo off
echo ========================================
echo    AZURE OCR CLIENT - TEST
echo ========================================
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

REM Zkontroluj jestli existuje zdrojový soubor
if not exist "src\azure_ocr_client.py" (
    echo ❌ CHYBA: Soubor src\azure_ocr_client.py neexistuje!
    echo 📁 Zkontroluj že jsi ve správném adresáři
    goto :error
)

REM Zkontroluj jestli existuje config
if not exist "src\config.py" (
    echo ❌ CHYBA: Soubor src\config.py neexistuje!
    goto :error
)

echo 🚀 Spouštím Azure OCR test...
echo.
echo ============= VÝSTUP SKRIPTU =============

REM Spusť Azure OCR client
py src\azure_ocr_client.py

echo.
echo ============= KONEC VÝSTUPU =============
echo.

if %ERRORLEVEL% EQU 0 (
    echo ✅ Test dokončen úspěšně!
) else (
    echo ❌ Test skončil s chybou (kód: %ERRORLEVEL%)
    echo.
    echo 💡 Možné příčiny:
    echo    - Chybí Azure dependencies: py -m pip install azure-ai-documentintelligence
    echo    - Neplatné Azure credentials v config.py
    echo    - Neexistující Azure model "pokus1"
    echo    - Prázdná složka data/processed/2025
)

goto :end

:error
echo.
echo ❌ Test nelze spustit kvůli chybám výše
echo.

:end
echo.
echo 🔍 Pro debug zkontroluj:
echo    - config.py (Azure endpoint a key)
echo    - data\processed\2025\ (test data)
echo    - pip list (nainstalované packages)
echo.
pause 