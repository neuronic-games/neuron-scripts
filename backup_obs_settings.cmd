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

:: OBS only writes things like saved projector positions to disk during a
:: normal exit/save - not continuously while running. Backing up while it's
:: still open can miss recent changes, so offer to close it first.
tasklist /FI "IMAGENAME eq obs64.exe" 2>nul | find /I "obs64.exe" >nul
if not errorlevel 1 (
    echo OBS is currently running. Things like projector positions are only
    echo saved to disk when OBS closes normally, so backing up now could
    echo miss recent changes.
    echo.
    choice /M "Close OBS now so this backup captures the current state"
    if errorlevel 2 (
        echo Continuing without closing OBS - the backup may not include recent changes.
    ) else (
        echo Closing OBS...
        taskkill /IM obs64.exe >nul 2>&1
        timeout /t 5 /nobreak >nul
        tasklist /FI "IMAGENAME eq obs64.exe" 2>nul | find /I "obs64.exe" >nul
        if not errorlevel 1 (
            echo WARNING: OBS did not close in time - backing up its current on-disk state anyway.
        )
    )
    echo.
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
