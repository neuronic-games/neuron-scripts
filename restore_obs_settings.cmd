:: restore_obs_settings.cmd
:: Restores OBS Studio's settings from
:: Documents\Neuronic\settings-backup\obs-studio back into %appdata%\obs-studio.
:: (c) Neuronic 2026

@echo off
echo ============================================================
echo  OBS settings restore
echo ============================================================
echo.

set "SRC=%USERPROFILE%\Documents\Neuronic\settings-backup\obs-studio"
set "DEST=%appdata%\obs-studio"

if not exist "%SRC%" (
    echo ERROR: Backup folder not found:
    echo   %SRC%
    pause
    exit /b 1
)

echo This will overwrite the current OBS settings at:
echo   %DEST%
echo with the backup at:
echo   %SRC%
echo.
choice /M "Continue"
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Closing OBS if it's running...
taskkill /IM obs64.exe /F >nul 2>&1

if not exist "%DEST%" mkdir "%DEST%"

echo Restoring...
robocopy "%SRC%" "%DEST%" /MIR /R:2 /W:2 /NFL /NDL /NJH

:: robocopy exit codes 0-7 mean success/informational; 8+ means failure
if %errorlevel% GEQ 8 (
    echo.
    echo ERROR: Restore failed - robocopy exit code %errorlevel%.
    pause
    exit /b 1
)

echo.
echo Restore complete.
pause
