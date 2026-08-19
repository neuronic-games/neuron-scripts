:: Start OBS Studio with the virtual camera running
:: (c) Neuronic 2026

@echo off

set "OBS_BACKUP=%USERPROFILE%\Documents\Neuronic\settings-backup\obs-studio"
set "OBS_SETTINGS=%appdata%\obs-studio"

:: If a known-good settings backup exists, restore it before launching, so
:: OBS always starts from that baseline instead of whatever state it was
:: last left in. Reuses restore_obs_settings.cmd in silent mode (/Y skips
:: its confirmation prompt and pause, since this runs unattended). %~dp0
:: resolves it relative to this script's own folder, regardless of the
:: caller's current directory.
if exist "%OBS_BACKUP%" (
    call "%~dp0restore_obs_settings.cmd" /Y
)

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

:: Once OBS is actually ready, open_projector.py opens the Program
:: projector itself - a workaround for an OBS startup race condition (see
:: the file's docstring for details/required OBS setting changes). Runs
:: detached (start "") so it doesn't hold up this script; it does its own
:: waiting for OBS's WebSocket server to come up.
start "" python "%~dp0open_projector.py"

:: Power-cycles the webcam's USB hub port and toggles it in OBS, so
:: exhibits with a webcam that doesn't reconnect on its own don't need a
:: physical unplug/replug after every OBS start. Runs detached and waits
:: on its own for OBS's WebSocket server to come up. Gated by
:: settings.resetCameraOnStart - a no-op (just logs and exits) for
:: deployments without a webcam/hub, or where it's not enabled/configured
:: yet, so it's safe to always call this here.
start "" python "%~dp0reset_camera.py"