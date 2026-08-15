:: Launcher script with auto restart and logging
:: (c) Neuronic 2023

@echo off

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo ============================================================
echo  Neuron Launcher
echo ============================================================

:: Optional parameter: an alternate settings file to use instead of
:: settings.py, e.g.  launch.cmd settings-edit.py
:: Captured here (before any cd) so a bare filename resolves relative to
:: wherever launch.cmd was run from.
SET "ALT_SETTINGS=%~f1"

:: Always clear any NEURON_SETTINGS_FILE left over from a previous run in
:: this same shell session first. Without this, running `launch.cmd
:: settings-edit.py` once and then plain `launch.cmd` later in the same
:: window would silently keep reusing settings-edit.py instead of falling
:: back to settings.py.
SET "NEURON_SETTINGS_FILE="

IF "%ALT_SETTINGS%"=="" (
    echo Settings file: settings.py [default]
) ELSE (
    IF EXIST "%ALT_SETTINGS%" (
        echo Settings file: %ALT_SETTINGS%
        SET "NEURON_SETTINGS_FILE=%ALT_SETTINGS%"
    ) ELSE (
        echo WARNING: settings file not found: %ALT_SETTINGS%
        echo Falling back to settings.py [default]
    )
)

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo.
echo Stopping any previously running python.exe processes...
taskkill /IM python.exe /F

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
echo.
echo Pulling latest scripts from git...
cd /D "%USERPROFILE%\Documents\Neuronic\neuron-scripts"
git pull

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: COMMENT & UNCOMMENT BELOW SCRIPTS BASED ON THE APP FUNCTIONALITIES
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Check for latest archive for those that are deployed as ZIP files if
:: audit_settings.checkForUpdate is True
:: e.g. Used for Unity EXEs

echo.
echo Checking for app archive updates...
python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\archive_update.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Report status into Google Sheet

echo.
echo Starting pulse monitor (status reports)...
start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\pulse.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Run and monitor the app

echo.
echo Starting guard (app monitor / kiosk lockdown)...
start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\guard.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Power-cycles the webcam's USB hub port and toggles it in OBS, so exhibits
:: with a webcam that doesn't reconnect on its own don't need a physical
:: unplug/replug after every boot. Runs detached and waits on its own for
:: OBS's WebSocket server to come up, so it doesn't hold up this script.
:: No-op / harmless for deployments without a webcam or hub - it just logs
:: a connection failure to reset_camera.log if OBS isn't running.

echo.
echo Starting camera reset (USB power-cycle + OBS reconnect)...
start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\reset_camera.py"

echo.
echo ============================================================
echo  Launch complete. Press Ctrl+Shift+S in the app to quit.
echo ============================================================
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
