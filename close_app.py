# close_app.py
# Neuronic 2026
#
# Closes the exhibit app (settings.appEXEName), if it's running.
#
# start_obs.cmd runs this before it restarts OBS. A running app keeps the
# previous OBS's virtual camera open, and while it does, the new OBS can't
# start its own virtual camera ("Failed to start virtual camera"). Closing
# the app first avoids that. guard.py starts the app again afterwards.

import os
import subprocess
import sys
import time

import settings_loader  # must run before `import settings` below
import settings

APP_EXE_NAME = getattr(settings, 'appEXEName', '')


def _running():
    if sys.platform == 'win32':
        out = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {APP_EXE_NAME}'],
                             capture_output=True, text=True).stdout
        return APP_EXE_NAME.lower() in out.lower()
    return subprocess.run(['pgrep', '-f', APP_EXE_NAME], capture_output=True).returncode == 0


def main():
    if not APP_EXE_NAME:
        print('No app configured (appEXEName is blank) - nothing to close.')
        return
    if not _running():
        print(f'{APP_EXE_NAME} is not running.')
        return
    print(f'Closing {APP_EXE_NAME} so OBS can restart its virtual camera...')
    if sys.platform == 'win32':
        os.system(f'taskkill /IM "{APP_EXE_NAME}" /F >nul 2>&1')
    else:
        subprocess.run(['pkill', '-f', APP_EXE_NAME], capture_output=True)
    # Give Windows a moment to release the app's hold on the camera.
    for _ in range(10):
        if not _running():
            break
        time.sleep(0.5)
    time.sleep(1)
    print('Closed.' if not _running() else f'WARNING: {APP_EXE_NAME} is still running.')


if __name__ == '__main__':
    main()
