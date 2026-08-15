:: list_camera_devices.cmd
:: Lists camera/imaging devices and their PnP Instance IDs, so the right
:: one can be identified for a "soft" USB unplug/replug (pnputil
:: disable-device / enable-device) if OBS's own reconnect fix isn't
:: enough on its own to bring the camera back after startup.
:: (c) Neuronic 2026

@echo off
echo ============================================================
echo  Camera / imaging devices
echo ============================================================
echo.
powershell -NoProfile -Command "Get-PnpDevice -Class Camera,Image -Status OK,Error,Unknown,Degraded | Select-Object FriendlyName, InstanceId, Status | Format-List"
echo.
echo Find your webcam's name above and note its InstanceId - that's what
echo a pnputil-based reconnect fix would need.
echo.
pause
