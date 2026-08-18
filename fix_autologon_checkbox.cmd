:: fix_autologon_checkbox.cmd
:: On some Windows 11 builds, the "Users must enter a user name and
:: password to use this computer" checkbox is missing from netplwiz,
:: because Windows Hello's "passwordless" feature hides it. This restores
:: the checkbox by turning that feature off via the registry.
::
:: This script ONLY fixes the missing checkbox - it does not set up
:: auto-logon itself. After running this (and rebooting if needed), open
:: netplwiz, uncheck the box, and enter the account's username/password as
:: normal.
::
:: Must run as Administrator.

@echo off
echo ============================================================
echo  Fix missing auto-logon checkbox in netplwiz
echo ============================================================
echo.

:: Confirm elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator.
    echo Right-click fix_autologon_checkbox.cmd and choose "Run as administrator".
    pause
    exit /b 1
)

set "REG_KEY=HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Passwordless\Device"
set "REG_VALUE=DevicePasswordlessBuildVersion"
set "BACKUP_DIR=%~dp0autologon_backup"

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo Backing up current registry key to:
echo   %BACKUP_DIR%\PasswordlessDevice.reg
reg export "%REG_KEY%" "%BACKUP_DIR%\PasswordlessDevice.reg" /y >nul 2>&1
echo Backup complete.
echo.

echo Setting %REG_VALUE% to 0...
reg add "%REG_KEY%" /v "%REG_VALUE%" /t REG_DWORD /d 0 /f
if %errorlevel% neq 0 (
    echo ERROR: Failed to set the registry value.
    pause
    exit /b 1
)
echo Done.
echo.

echo ============================================================
echo  Now open netplwiz (Win+R, type netplwiz, Enter). If the
echo  checkbox is still missing, sign out and back in, or reboot,
echo  then check again.
echo  (To undo: re-import %BACKUP_DIR%\PasswordlessDevice.reg)
echo ============================================================
echo.
pause
