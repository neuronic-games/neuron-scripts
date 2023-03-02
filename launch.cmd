::start cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\report_status.py"
::start cmd /c python "%USERPROFILE%\Documents\Neuronic\Apps\neuron-scripts\guard.py"

:: Launcher script with auto restart and logging
:: (c) Neuronic 2021
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:CHECK_RELEASE
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



