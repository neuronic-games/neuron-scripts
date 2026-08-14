:: Launcher script with auto restart and logging
:: (c) Neuronic 2023

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Optional parameter: an alternate settings file to use instead of
:: settings.py, e.g.  launch.cmd settings-edit.py
:: Captured here (before any cd) so a bare filename resolves relative to
:: wherever launch.cmd was run from.
SET "ALT_SETTINGS=%~f1"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Close all previously running python files
taskkill /IM python.exe /F

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Pull latest scripts from git
cd /D "%USERPROFILE%\Documents\Neuronic\neuron-scripts"
git pull

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: If an alternate settings file was passed in, point NEURON_SETTINGS_FILE at
:: it instead of copying anything over settings.py. settings_loader.py (which
:: every script imports before `import settings`) reads this env var and
:: loads that file as the "settings" module for this run only - settings.py
:: itself is never touched. python/start below inherit this since they're
:: child processes of this same cmd session.
IF NOT "%ALT_SETTINGS%"=="" (
    IF EXIST "%ALT_SETTINGS%" (
        echo Using settings file: %ALT_SETTINGS%
        SET "NEURON_SETTINGS_FILE=%ALT_SETTINGS%"
    ) ELSE (
        echo WARNING: settings file not found: %ALT_SETTINGS%
        echo Falling back to the existing settings.py
    )
)

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: COMMENT & UNCOMMENT BELOW SCRIPTS BASED ON THE APP FUNCTIONALITIES
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Check for latest archive for those that are deployed as ZIP files if
:: audit_settings.checkForUpdate is True
:: e.g. Used for Unity EXEs

python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\archive_update.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Report status into Google Sheet

start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\pulse.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Run and monitor the app

start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\neuron-scripts\guard.py"
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
