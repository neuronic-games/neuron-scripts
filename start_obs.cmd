:: Start OBS Studio with the virtual camera running
:: (c) Neuronic 2026

@echo off

set "OBS_BACKUP=%USERPROFILE%\Documents\Neuronic\settings-backup\obs-studio"
set "OBS_SETTINGS=%appdata%\obs-studio"

:: Always make sure no existing OBS instance is still running before doing
:: anything else. Launching a second instance on top of one that's still
:: up just shows OBS's own "OBS is already running!" dialog, which sits
:: there waiting for a click and blocks the new instance from ever
:: starting its WebSocket server - every script below that waits on the
:: WebSocket then fails/times out. Confirmed on a real deployment: this
:: used to only happen inside restore_obs_settings.cmd below, which only
:: runs if a settings backup already exists - on a machine/profile
:: without one yet (e.g. a fresh Administrator account), OBS was never
:: closed at all. Unconditional and independent of the backup existing.
tasklist /FI "IMAGENAME eq obs64.exe" 2>nul | find /I "obs64.exe" >nul
if not errorlevel 1 (
    echo Closing the existing OBS instance...
    taskkill /IM obs64.exe >nul 2>&1
    timeout /t 5 /nobreak >nul
    tasklist /FI "IMAGENAME eq obs64.exe" 2>nul | find /I "obs64.exe" >nul
    if not errorlevel 1 (
        echo OBS did not close in time - forcing it closed.
        taskkill /IM obs64.exe /F >nul 2>&1
        timeout /t 2 /nobreak >nul
    )
)

:: If a known-good settings backup exists, restore it before launching, so
:: OBS always starts from that baseline instead of whatever state it was
:: last left in. Reuses restore_obs_settings.cmd in silent mode (/Y skips
:: its confirmation prompt and pause, since this runs unattended). %~dp0
:: resolves it relative to this script's own folder, regardless of the
:: caller's current directory.
if exist "%OBS_BACKUP%" (
    call "%~dp0restore_obs_settings.cmd" /Y
)

:: Force OBS's "Save Projectors on Exit" off before every launch, so OBS
:: never runs its own broken native projector restore (see
:: open_projector.py's docstring), regardless of what's baked into the
:: settings backup above. Runs synchronously (not detached) since it must
:: finish before OBS itself starts and reads this setting.
python "%~dp0disable_obs_save_projectors.py"

:: An unclean shutdown leaves the .sentinel folder behind, which forces
:: OBS to show an "unclean shutdown" warning dialog on next launch (bad for
:: an unattended kiosk). Delete it so OBS starts silently.
if exist "%OBS_SETTINGS%\.sentinel" rmdir /s /q "%OBS_SETTINGS%\.sentinel"

:: OBS needs its working directory set to its own bin folder to find its
:: plugins/data correctly when launched other than via its Start Menu
:: shortcut. pushd/popd instead of cd, so the caller's current directory is
:: restored afterward instead of being left inside OBS's bin folder.
pushd "C:\Program Files\obs-studio\bin\64bit"
start "" "obs64.exe" --startvirtualcam --disable-shutdown-check
popd

:: Resets the webcam if needed: power-cycles its USB hub port, then
:: presses its OBS source's own Activate/Deactivate properties button
:: twice (see reset_camera.py's docstring - this is the same control the
:: manual deactivate/reactivate fix uses, and it doesn't depend on scene
:: visibility, so there's no ordering requirement against
:: open_projector.py below). Gated by settings.resetCameraOnStart - a
:: no-op (just logs and exits immediately, without connecting to OBS)
:: for deployments without a webcam/hub, or where it's not enabled/
:: configured yet, so it's safe to always call this here.
python "%~dp0reset_camera.py"

:: Opens whatever projectors OBS has saved itself - a workaround for an
:: OBS startup race condition (see the file's docstring for details/
:: required OBS setting changes).
python "%~dp0open_projector.py"