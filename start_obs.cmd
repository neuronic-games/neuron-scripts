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
start "" "obs64.exe" --startvirtualcam
popd

:: Open the Program projector ourselves, once OBS is actually ready, via
:: open_projector.py - works around a long-standing OBS bug where a
:: projector restored natively via "Save projectors on exit" opens before
:: OBS renders its first frame and gets stuck on a black screen. Runs
:: detached (start "") so it doesn't hold up this script; it does its own
:: waiting for OBS's WebSocket server to come up.
:: NOTE: turn OFF "Save projectors on exit" in OBS (Settings > General >
:: Projectors) so OBS doesn't also open its own stuck/black projector.
start "" python "%~dp0open_projector.py"
