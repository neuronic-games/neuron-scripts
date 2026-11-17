:: uninstall_onedrive.cmd
:: Removes OneDrive from an exhibit PC and stops it coming back.
::
:: Why: exhibit PCs signed in to the same Microsoft account all sync the
:: same OneDrive folders (often including Documents and Desktop), so files
:: - and settings - get copied between machines.
::
:: What it does, in this order:
::   1. Copies the shortcuts (.lnk/.url) from the OneDrive Desktop to the
::      normal Desktop (e.g. the "launch" shortcut), while OneDrive still
::      runs and can download them.
::   2. Points Documents, Desktop and Pictures back to the normal folders
::      under C:\Users\<you> (what "stop backup" does in OneDrive).
::   3. Stops OneDrive, removes it from startup and uninstalls it.
::   4. Blocks OneDrive with a Windows policy, so updates don't bring it back.
:: It does NOT delete anything: files already in the OneDrive folder stay
:: there (and in the cloud). The exhibit scripts live in
:: C:\Users\<you>\Documents\Neuronic, which OneDrive doesn't sync.
::
:: Run it as administrator (right-click > Run as administrator), signed in
:: as the exhibit's own Windows user. Stop the exhibit first (Ctrl+Shift+S),
:: and restart the PC afterwards.
:: No goto/labels in this file: they can misbehave when a .cmd file has
:: Unix line endings.
:: (c) Neuronic 2026

@echo off
setlocal

echo ============================================================
echo  Remove OneDrive
echo ============================================================
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo This needs administrator rights.
    echo Right-click uninstall_onedrive.cmd and choose "Run as administrator".
    pause
    exit /b 1
)

echo Windows user: %USERNAME%
echo Folders right now:
powershell -NoProfile -Command "'  Documents: ' + [Environment]::GetFolderPath('MyDocuments'); '  Desktop:   ' + [Environment]::GetFolderPath('Desktop'); '  Pictures:  ' + [Environment]::GetFolderPath('MyPictures')"
echo.
echo This will point Documents, Desktop and Pictures back to
echo   %USERPROFILE%\Documents, \Desktop and \Pictures,
echo then uninstall and block OneDrive. Nothing is deleted.
echo Make sure the user above is the exhibit's own Windows user.
echo.
choice /M "Continue"
if errorlevel 2 (
    echo Cancelled - nothing changed.
    pause
    exit /b 0
)

set "USF=HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"

echo.
echo [1/4] Copying desktop shortcuts out of OneDrive...
if not exist "%USERPROFILE%\Desktop" mkdir "%USERPROFILE%\Desktop"
if not exist "%USERPROFILE%\Documents" mkdir "%USERPROFILE%\Documents"
if not exist "%USERPROFILE%\Pictures" mkdir "%USERPROFILE%\Pictures"
powershell -NoProfile -Command ^
  "$src = [Environment]::GetFolderPath('Desktop'); $dst = Join-Path $env:USERPROFILE 'Desktop';" ^
  "if ($src -ne $dst) { Get-ChildItem -LiteralPath $src -File -ErrorAction SilentlyContinue |" ^
  "  Where-Object { $_.Extension -in '.lnk','.url' } | ForEach-Object {" ^
  "    Copy-Item -LiteralPath $_.FullName -Destination $dst -Force; '  ' + $_.Name } } else { '  (Desktop is not in OneDrive - nothing to copy)' }"

echo.
echo [2/4] Pointing Documents, Desktop and Pictures back to the normal folders...
reg add "%USF%" /v Personal /t REG_EXPAND_SZ /d "%%USERPROFILE%%\Documents" /f >nul
reg add "%USF%" /v {F42EE2D3-909F-4907-8871-4C22FC0BF756} /t REG_EXPAND_SZ /d "%%USERPROFILE%%\Documents" /f >nul
reg add "%USF%" /v Desktop /t REG_EXPAND_SZ /d "%%USERPROFILE%%\Desktop" /f >nul
reg add "%USF%" /v "My Pictures" /t REG_EXPAND_SZ /d "%%USERPROFILE%%\Pictures" /f >nul
reg add "%USF%" /v {0DDD015D-B06C-45D5-8C4C-F59713854639} /t REG_EXPAND_SZ /d "%%USERPROFILE%%\Pictures" /f >nul
echo   Done (takes full effect after a restart).

echo.
echo [3/4] Stopping and uninstalling OneDrive...
taskkill /f /im OneDrive.exe >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v OneDrive /f >nul 2>&1
winget uninstall --id Microsoft.OneDrive --silent --accept-source-agreements >nul 2>&1
if exist "%SystemRoot%\System32\OneDriveSetup.exe" "%SystemRoot%\System32\OneDriveSetup.exe" /uninstall >nul 2>&1
if exist "%SystemRoot%\SysWOW64\OneDriveSetup.exe" "%SystemRoot%\SysWOW64\OneDriveSetup.exe" /uninstall >nul 2>&1
powershell -NoProfile -Command ^
  "Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Microsoft\OneDrive') -Filter OneDriveSetup.exe -Recurse -ErrorAction SilentlyContinue |" ^
  "  ForEach-Object { Start-Process -FilePath $_.FullName -ArgumentList '/uninstall' -Wait }"
timeout /t 3 /nobreak >nul
tasklist /FI "IMAGENAME eq OneDrive.exe" 2>nul | find /I "OneDrive.exe" >nul
if not errorlevel 1 echo   WARNING: OneDrive is still running - uninstall it from Settings ^> Apps.
if errorlevel 1 echo   OneDrive stopped and uninstalled.

echo.
echo [4/4] Blocking OneDrive so Windows updates don't bring it back...
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\OneDrive" /v DisableFileSyncNGSC /t REG_DWORD /d 1 /f >nul
echo   Done.

echo.
echo ============================================================
echo  Finished. Restart the PC now. Then check:
echo   - the "launch" shortcut is on the desktop (if not, run
echo     install_shortcuts.cmd)
echo   - settings.py in Documents\Neuronic\neuron-scripts is this
echo     PC's own
echo   - the exhibit starts and guard.log looks normal
echo  Files that were in OneDrive are still in %USERPROFILE%\OneDrive.
echo  Do this on every exhibit PC signed in to the same account.
echo ============================================================
pause
