:: backup_obs_settings.cmd
:: Backs up OBS Studio's settings from %appdata%\obs-studio into
:: Documents\Neuronic\settings-backup\obs-studio.
:: (c) Neuronic 2026

@echo off
echo ============================================================
echo  OBS settings backup
echo ============================================================
echo.

set "SRC=%appdata%\obs-studio"
set "DEST=%USERPROFILE%\Documents\Neuronic\settings-backup\obs-studio"

if not exist "%SRC%" (
    echo ERROR: OBS settings folder not found:
    echo   %SRC%
    pause
    exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"

echo Backing up:
echo   %SRC%
echo to:
echo   %DEST%
echo.

robocopy "%SRC%" "%DEST%" /MIR /R:2 /W:2 /NFL /NDL /NJH

:: robocopy exit codes 0-7 mean success/informational; 8+ means failure
if %errorlevel% GEQ 8 (
    echo.
    echo ERROR: Backup failed - robocopy exit code %errorlevel%.
    pause
    exit /b 1
)

echo.
echo Backup complete.
pause
