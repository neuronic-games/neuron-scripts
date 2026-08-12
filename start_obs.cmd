:: Start OBS Studio with the virtual camera running
:: (c) Neuronic 2026

:: OBS needs its working directory set to its own bin folder to find its
:: plugins/data correctly when launched other than via its Start Menu shortcut.
cd /d "C:\Program Files\obs-studio\bin\64bit"
start "" "obs64.exe" --startvirtualcam
