:: install_shortcuts.cmd
:: Creates a "launch" shortcut on the desktop that starts the exhibit
:: (cmd.exe /c launch.cmd - a shortcut to cmd.exe, rather than to
:: launch.cmd itself, can be pinned to the taskbar), with the Neuronic
:: icon, and a "terminal" shortcut that opens Command Prompt in the scripts
:: folder. Then asks whether to also put a copy of "launch" in the Startup
:: folder, so the exhibit starts whenever Windows signs in.
:: Safe to run again: it replaces the shortcuts it made before.
:: No goto/labels in this file: they can misbehave when a .cmd file has
:: Unix line endings.
:: (c) Neuronic 2026

@echo off
setlocal

set "SCRIPTS=%USERPROFILE%\Documents\Neuronic\neuron-scripts"
set "ICON=%SCRIPTS%\logo\neuronic.ico"
set "TERMINAL_ICON=%SCRIPTS%\logo\terminal.ico"
set "STARTUP=%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"

echo ============================================================
echo  Install exhibit shortcuts
echo ============================================================
echo.

if not exist "%SCRIPTS%\launch.cmd" (
    echo ERROR: launch.cmd not found in:
    echo   %SCRIPTS%
    echo The scripts must be in Documents\Neuronic\neuron-scripts.
    pause
    exit /b 1
)

:: Create the desktop shortcut. PowerShell finds the real Desktop folder,
:: even if it has been moved to OneDrive. Paths come in through
:: environment variables to avoid quoting problems.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$q = [char]34;" ^
  "$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'launch.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);" ^
  "$s.TargetPath = $env:ComSpec;" ^
  "$s.Arguments = '/c ' + $q + (Join-Path $env:SCRIPTS 'launch.cmd') + $q;" ^
  "$s.WorkingDirectory = $env:SCRIPTS;" ^
  "$s.IconLocation = $env:ICON;" ^
  "$s.Save();" ^
  "Write-Host ('Created ' + $lnk)"
if errorlevel 1 (
    echo ERROR: Could not create the desktop shortcut.
    pause
    exit /b 1
)

:: "terminal": Command Prompt, already in the scripts folder (/k keeps it open).
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$q = [char]34;" ^
  "$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'terminal.lnk';" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk);" ^
  "$s.TargetPath = $env:ComSpec;" ^
  "$s.Arguments = '/k cd /d ' + $q + $env:SCRIPTS + $q;" ^
  "$s.WorkingDirectory = $env:SCRIPTS;" ^
  "$s.IconLocation = $(if (Test-Path -LiteralPath $env:TERMINAL_ICON) { $env:TERMINAL_ICON } else { $env:ComSpec + ',0' });" ^
  "$s.Save();" ^
  "Write-Host ('Created ' + $lnk)"
if errorlevel 1 echo WARNING: Could not create the terminal shortcut.

echo.
choice /M "Start the exhibit automatically when Windows signs in (copy the shortcut to the Startup folder)"
set "ADD=1"
if errorlevel 2 set "ADD=0"
if "%ADD%"=="0" echo Not added to the Startup folder.

if "%ADD%"=="1" if not exist "%STARTUP%" mkdir "%STARTUP%"
if "%ADD%"=="1" powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$src = Join-Path ([Environment]::GetFolderPath('Desktop')) 'launch.lnk';" ^
  "$dst = Join-Path $env:STARTUP 'launch.lnk';" ^
  "Copy-Item -LiteralPath $src -Destination $dst -Force;" ^
  "Write-Host ('Copied to ' + $dst)"
if "%ADD%"=="1" if errorlevel 1 echo ERROR: Could not copy the shortcut to the Startup folder.

:: Warn about any OTHER startup shortcut that also runs launch.cmd: two of
:: them start Launch twice at sign-in, which breaks OBS's virtual camera.
if "%ADD%"=="1" powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "Get-ChildItem -LiteralPath $env:STARTUP -Filter *.lnk | Where-Object { $_.Name -ne 'launch.lnk' } | ForEach-Object {" ^
  "  $s = $w.CreateShortcut($_.FullName);" ^
  "  if (($s.TargetPath + ' ' + $s.Arguments) -match 'launch\.cmd') {" ^
  "    Write-Host ''; Write-Host ('WARNING: ' + $_.Name + ' in the Startup folder also runs launch.cmd.');" ^
  "    Write-Host 'Delete it, or the exhibit will be launched twice at sign-in.' } }"

echo.
echo Done. To pin it to the taskbar, right-click "launch" on the desktop
echo and choose "Pin to taskbar" (on Windows 11, under "Show more options").
echo.
pause
