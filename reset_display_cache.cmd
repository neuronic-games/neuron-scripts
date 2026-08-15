:: reset_display_cache.cmd
:: Clears Windows' cached per-monitor display configuration (topology,
:: position, resolution, refresh rate, DPI scaling) so displays get
:: re-detected fresh on next boot.
::
:: IMPORTANT CAVEAT: this does NOT reliably fix a mismatch between the
:: "Display 1/2" numbers shown in Windows Settings and the display index
:: your app gets from a Win32 API (EnumDisplayDevices/EnumDisplayMonitors).
:: Those are two different numbering systems by design - Settings assigns
:: numbers by connector-type priority, not detection order. Multiple
:: Microsoft support threads confirm clearing this cache does not resolve
:: that specific mismatch. What this DOES reliably fix: stuck/wrong
:: resolution, refresh rate, monitor position, or DPI scaling after
:: swapping monitors, cables, or ports.
::
:: Must run as Administrator. A REBOOT is required afterward - that's what
:: actually triggers re-detection, not just replugging monitors.
:: Monitor arrangement/position and DPI scaling will need to be redone in
:: Display Settings after reboot.

@echo off
echo ============================================================
echo  Display configuration cache reset
echo ============================================================
echo.

:: Confirm elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click reset_display_cache.cmd and choose "Run as administrator".
    pause
    exit /b 1
)

set "BACKUP_DIR=%~dp0display_cache_backup"
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo Backing up current registry keys to:
echo   %BACKUP_DIR%
reg export "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration" "%BACKUP_DIR%\Configuration.reg" /y >nul 2>&1
reg export "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Connectivity" "%BACKUP_DIR%\Connectivity.reg" /y >nul 2>&1
reg export "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\ScaleFactors" "%BACKUP_DIR%\ScaleFactors.reg" /y >nul 2>&1
echo Backup complete.
echo.

echo Deleting cached display configuration...
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration" /f >nul 2>&1
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Connectivity" /f >nul 2>&1
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\ScaleFactors" /f >nul 2>&1
echo Done.
echo.

echo ============================================================
echo  A reboot is required for this to take effect.
echo  After reboot you will likely need to redo monitor
echo  arrangement/position and DPI scaling in Display Settings.
echo  (To undo: re-import the .reg files from %BACKUP_DIR%)
echo ============================================================
echo.
choice /M "Reboot now"
if errorlevel 2 goto :skip
shutdown /r /t 10 /c "Rebooting to apply display configuration reset (run 'shutdown /a' to cancel)"
:skip
pause
