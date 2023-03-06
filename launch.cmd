:: Launcher script with auto restart and logging
:: (c) Neuronic 2023

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:CHECK_RELEASE
:: Check for latest archive for those that are deployed as ZIP files
:: e.g. Unity EXEs
python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\archive_update.py"

goto START

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:START
::goto END

: CHECK_FILES

:: FOR UPDATE GOOGLE SHEET [IF EXE APP]
::start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\report_status.py"
:: FOR EXE
start /min cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\guard.py"

::goto START
:END



