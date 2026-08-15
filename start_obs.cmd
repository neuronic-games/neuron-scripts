:: Start OBS Studio with the virtual camera running
:: (c) Neuronic 2026

:: An unclean shutdown leaves the .sentinel folder behind, which forces
:: OBS to show an "unclean shutdown" warning dialog on next launch (bad for
:: an unattended kiosk). Delete it first so OBS starts silently.
if exist "%appdata%\obs-studio\.sentinel" rmdir /s /q "%appdata%\obs-studio\.sentinel"

:: OBS needs its working directory set to its own bin folder to find its
:: plugins/data correctly when launched other than via its Start Menu shortcut.
cd /d "C:\Program Files\obs-studio\bin\64bit"
start "" "obs64.exe" --startvirtualcam
