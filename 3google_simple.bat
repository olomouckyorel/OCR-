@echo off
echo ========================================
echo    GOOGLE SHEETS UPLOAD - SIMPLE
echo ========================================
echo.

REM Aktivuj virtual environment
if exist "..\venv\Scripts\activate.bat" (
    echo ✅ Aktivuji venv...
    call ..\venv\Scripts\activate.bat
) else (
    echo ⚠️  Používám systémový Python
)
echo.

echo 🔍 KONTROLY:
echo.

echo 1. Kontroluji google_sheets_client.py...
if exist "src\google_sheets_client.py" (
    echo ✅ src\google_sheets_client.py - OK
) else (
    echo ❌ src\google_sheets_client.py - CHYBÍ
    pause
    exit /b 1
)

echo 2. Kontroluji google-credentials.json...
if exist "google-credentials.json" (
    echo ✅ google-credentials.json - OK
) else (
    echo ❌ google-credentials.json - CHYBÍ
    pause
    exit /b 1
)

echo 3. Kontroluji data\output složku...
if exist "data\output" (
    echo ✅ data\output - OK
) else (
    echo ❌ data\output - CHYBÍ
    pause
    exit /b 1
)

echo 4. Kontroluji JSON soubory...
dir data\output\*_analysis.json >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ JSON soubory - OK
) else (
    echo ❌ JSON soubory - NENALEZENY
    pause
    exit /b 1
)

echo.
echo 🚀 Všechny kontroly prošly! Spouštím upload...
echo.

py src\google_sheets_client.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo ✅ ÚSPĚCH!
    echo 🔗 https://docs.google.com/spreadsheets/d/129XnRNQytuHbvSE3NEa6evVdzlFGDjCRwKxXG58sZfA
) else (
    echo ❌ CHYBA při uploadu
)
echo.
pause 