:: Launcher script with auto restart and logging
:: (c) Neuronic 2023

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Close all previously running python files 
taskkill /IM python.exe /F

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: COMMENT & UNCOMMENT BELOW SCRIPTS BASED ON THE APP FUNCTIONALITIES
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Check for latest archive for those that are deployed as ZIP files if
:: audit_settings.checkForUpdate is True
:: e.g. Used for Unity EXEs

python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\archive_update.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Report status into Google Sheet

start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\report_status.py"

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: Run and monitor the app

start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\guard.py"
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
