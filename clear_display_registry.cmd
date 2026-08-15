:: clear_display_registry.cmd
:: Temporary fix: clears the two cached display-configuration registry keys
:: (Configuration, Connectivity) so Windows re-detects monitor topology,
:: position, resolution, and refresh rate fresh on next boot.
::
:: NOTE: this does not reliably fix a mismatch between the "Display 1/2"
:: numbers in Windows Settings and the display index an app gets from a
:: Win32 API - those are separate numbering systems. See
:: reset_display_cache.cmd for the fuller version (also clears DPI scaling
:: cache and backs up the keys first).
::
:: Must run as Administrator. Reboot required afterward.

@echo off
echo ============================================================
echo  Clear display configuration registry cache
echo ============================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click clear_display_registry.cmd and choose "Run as administrator".
    pause
    exit /b 1
)

echo Deleting HKLM\...\GraphicsDrivers\Configuration ...
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration" /f

echo Deleting HKLM\...\GraphicsDrivers\Connectivity ...
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Connectivity" /f

echo.
echo Done. A reboot is required for this to take effect.
echo Monitor arrangement/position will need to be redone in Display Settings after reboot.
echo.
pause
