:: restore_obs_settings.cmd [/Y]
:: Restores OBS Studio's settings from
:: Documents\Neuronic\settings-backup\obs-studio back into %appdata%\obs-studio.
::
:: Pass /Y to run non-interactively - skips the confirmation prompt and the
:: final pause. Used by start_obs.cmd, which calls this unattended.
:: (c) Neuronic 2026

@echo off

set "SILENT=0"
if /I "%~1"=="/Y" set "SILENT=1"

echo ============================================================
echo  OBS settings restore
echo ============================================================
echo.

set "SRC=%USERPROFILE%\Documents\Neuronic\settings-backup\obs-studio"
set "DEST=%appdata%\obs-studio"

if not exist "%SRC%" (
    echo ERROR: Backup folder not found:
    echo   %SRC%
    if "%SILENT%"=="0" pause
    exit /b 1
)

if "%SILENT%"=="0" (
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
    if "%SILENT%"=="0" pause
    exit /b 1
)

echo.
echo Restore complete.
if "%SILENT%"=="0" pause
