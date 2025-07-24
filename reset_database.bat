@echo off
echo ========================================
echo    RESET DATABÁZE DUPLIKÁTŮ
echo ========================================
echo.
echo ⚠️  POZOR: Toto smaže historii zpracovaných souborů!
echo     Po spuštění budou všechny soubory považovány za nové.
echo.
pause
echo.

cd /d "%~dp0"

echo 🗑️ Mažu databázi duplikátů...

if exist "processed_files.txt" (
    del "processed_files.txt"
    echo ✅ Smazán: processed_files.txt
) else (
    echo ⚠️  processed_files.txt neexistuje
)

if exist "duplicates_log.txt" (
    del "duplicates_log.txt"  
    echo ✅ Smazán: duplicates_log.txt
) else (
    echo ⚠️  duplicates_log.txt neexistuje
)

echo.
echo ✅ RESET DOKONČEN!
echo.
echo 🎯 VÝSLEDEK:
echo    - Všechny soubory budou považovány za nové
echo    - Můžeš spustit čistý test celého procesu
echo    - Database se vytvoří znovu při příštím uploadu
echo.
pause 