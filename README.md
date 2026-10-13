# neuron-scripts

Scripts that run Neuronic exhibits on Windows kiosk PCs. They launch and watch the exhibit app, lock down the desktop, report the machine's health to PulseBoard, and keep the app and scripts up to date.

- [What runs on an exhibit](#what-runs-on-an-exhibit)
- [Install on Windows](#install-on-windows)
  - [Start automatically and add desktop and taskbar shortcuts](#6-start-the-exhibit-automatically-and-add-desktop-and-taskbar-shortcuts)
- [Install on Linux](#install-on-linux)
- [Edit the settings](#edit-the-settings)
- [Start the exhibit](#start-the-exhibit)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)

---

## What runs on an exhibit

`launch.cmd` starts everything, in this order:

1. Stops any Python scripts that are already running.
2. Runs `git pull` to get the latest scripts.
3. **`archive_update.py`**: if `checkForUpdate` is on, downloads and unzips a newer version of the app.
4. **`start_obs.cmd`**: starts OBS Studio, only if `startObs` is on.
5. **`pulse.py`**: sends this machine's status to PulseBoard (the Google Sheet) when it starts, when the app comes up, and every 5 hours after that.
6. **`clean_up_folder.py --loop`**: deletes old files, only if `cleanupFolders` is set.
7. **`launch_aux.cmd`**: your own extra launch steps, only if that file exists.
8. **`guard.py`**: starts the exhibit app full-screen, restarts it if it crashes, and locks the desktop.

Press **Ctrl+Shift+S** to quit the app and unlock the desktop.

On Linux, `launch.sh` does the same, except that it doesn't start OBS and doesn't lock the desktop. See [Install on Linux](#install-on-linux).

---

## Install on Windows

Run every command below in **Command Prompt** (`cmd`), not PowerShell. The `%USERPROFILE%` paths only work in Command Prompt.

### 1. Install Python and Git

```bat
winget install Python.Python.3.11
winget install Git.Git
```

**Close Command Prompt and open a new one** so Windows picks up the new `py` and `git` commands. Then check both work:

```bat
py -3 --version
git --version
```

You should see `Python 3.11.x` and a Git version. If either says *not recognized*, see [Troubleshooting](#troubleshooting).

### 2. Get the scripts

The scripts must live at `Documents\Neuronic\neuron-scripts`, because `launch.cmd` looks for them there.

```bat
mkdir "%USERPROFILE%\Documents\Neuronic"
cd "%USERPROFILE%\Documents\Neuronic"
git clone https://github.com/neuronic-games/neuron-scripts
cd "%USERPROFILE%\Documents\Neuronic\neuron-scripts"
```

> **Older installs** keep their apps in `%USERPROFILE%\Documents\Neuronic\Apps`. If you're updating one of those machines, see `appPath` under [Edit the settings](#edit-the-settings).

### 3. Install the Python packages

```bat
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
```

### 4. Create your settings file

```bat
copy settings.py.sample settings.py
notepad settings.py
```

Each machine has its own `settings.py`. Git never overwrites it, so your settings survive updates. Edit it as described in the next section, then save.

### 5. Check it works

Send one test report to PulseBoard:

```bat
py -3 pulse.py --test
```

It sends a single report, then stops. A success ends with `Success - check the '<sheetName>' tab for row '<exhibitName>'`, and the machine appears on that tab within a few seconds. A failure ends with `Failed` and the reason, such as a wrong `sheetID` or no internet. A test report doesn't clear `crash.log`.

On success it also prints a **Client link**: a read-only PulseBoard page showing only this tab's machines, with no login needed. It's created automatically the first time a tab reports, then reused, so you can send the same link to the client.

### 6. Start the exhibit automatically, and add desktop and taskbar shortcuts

Put a shortcut in the **Startup** folder (`shell:startup`) so the exhibit starts whenever Windows signs in. Put another on the **desktop**, and pin it to the **taskbar**, for restarting the exhibit by hand.

The shortcuts run `cmd /c "...\launch.cmd"` rather than `launch.cmd` itself, because Windows only lets you pin a shortcut to the taskbar when it starts a program such as `cmd.exe`.

**Quick way:** paste this whole line into Command Prompt. It creates a **Launch** shortcut, with the Neuronic icon, in both places:

```bat
powershell -NoProfile -Command "$d = Join-Path $env:USERPROFILE 'Documents\Neuronic\neuron-scripts'; $q = [char]34; $w = New-Object -ComObject WScript.Shell; foreach ($f in 'Startup','Desktop') { $s = $w.CreateShortcut((Join-Path ([Environment]::GetFolderPath($f)) 'Launch.lnk')); $s.TargetPath = $env:ComSpec; $s.Arguments = '/c ' + $q + (Join-Path $d 'launch.cmd') + $q; $s.WorkingDirectory = $d; $s.IconLocation = (Join-Path $d 'logo\neuronic.ico'); $s.Save(); Write-Host ('Created ' + $s.FullName) }"
```

You should see two `Created ...` lines: one in `...\Start Menu\Programs\Startup` and one on the desktop. This works even if the Desktop folder has been moved to OneDrive.

**By hand:**

1. Right-click an empty part of the desktop and choose **New → Shortcut**.
2. For the location, enter
   ```
   cmd /c "%USERPROFILE%\Documents\Neuronic\neuron-scripts\launch.cmd"
   ```
   then click **Next**, name it **Launch**, and click **Finish**.
3. Right-click the new shortcut and choose **Properties**.
   - Set **Start in** to `%USERPROFILE%\Documents\Neuronic\neuron-scripts`.
   - Click **Change Icon → Browse** and pick `logo\neuronic.ico` in that folder.
   - Click **OK**.
4. Press **Win+R**, type `shell:startup` and press **Enter**. Copy the desktop shortcut into the Startup folder that opens. Ctrl+C, then Ctrl+V works.

**Pin it to the taskbar:** right-click the **Launch** shortcut on the desktop and choose **Pin to taskbar**. On Windows 11 it may be under **Show more options**.

> **Always use a shortcut, not a copy.** A copy of `launch.cmd` doesn't get the fixes `git pull` brings in. Moving the real file breaks `git pull` and `launch.cmd` itself.

**Signing in automatically.** The Startup folder only runs once someone signs in. For a kiosk that should start the exhibit after a power cut or reboot, set Windows to sign in on its own:

1. Press **Win+R**, type `netplwiz` and press **Enter**.
2. Untick **Users must enter a user name and password to use this computer**, then click **OK** and enter the account's password.
3. If that checkbox is missing (common on Windows 11), right-click `fix_autologon_checkbox.cmd` in the scripts folder, choose **Run as administrator**, restart, and try again.

**Test it:** restart the PC. The exhibit should start by itself after Windows signs in.

**Turn off auto-start:** delete the **Launch** shortcut from `shell:startup`. The desktop and taskbar shortcuts can stay.

---

## Install on Linux

These steps are for Ubuntu and other Debian-based distributions, run in a **Terminal**.

**How Linux differs from Windows:**

- `launch.sh` starts everything instead of `launch.cmd`.
- `guard.py` starts the app and restarts it if it crashes, but **doesn't lock the desktop**. The wallpaper, lock screen and logo are Windows-only.
- `launch.sh` **doesn't start OBS**, so the OBS and camera settings aren't used.
- **Ctrl+Shift+S usually doesn't work**, because the `keyboard` package needs root access on Linux. Use the stop command in step 6 instead.

### 1. Install Python and Git

```bash
sudo apt update
sudo apt install -y python3 python3-pip git xdg-user-dirs
python3 --version
git --version
```

You need Python 3.9 or newer.

### 2. Get the scripts

The scripts must live at `~/Documents/Neuronic/neuron-scripts`, because `launch.sh` looks for them there.

```bash
mkdir -p ~/Documents/Neuronic
cd ~/Documents/Neuronic
git clone https://github.com/neuronic-games/neuron-scripts
cd ~/Documents/Neuronic/neuron-scripts
```

### 3. Install the Python packages

```bash
python3 -m pip install --user -r requirements.txt
```

If you see **`externally-managed-environment`** (common on Ubuntu 23.04 and newer), run this instead:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

### 4. Create your settings file

```bash
cp settings.py.sample settings.py
nano settings.py
```

Edit it as described in [Edit the settings](#edit-the-settings). In nano, press **Ctrl+O** then **Enter** to save, and **Ctrl+X** to exit. On Linux:

- **Paths** use forward slashes and need no `r`: `appEXEPath = '/home/kiosk/Documents/Neuronic/Skeletal Pop/Linux'`.
- **`appEXEName`** is the app's program file, such as `'skeletal-pop.x86_64'`. Make sure it can run: `chmod +x "/path/to/app/skeletal-pop.x86_64"`.
- **Web exhibits:** set `appEXEPath = '/opt/google/chrome'` and `appEXEName = 'chrome'`, then put the page in `appURL`. Google Chrome must be installed.

Check the file for mistakes:

```bash
python3 -c "import settings_loader, settings; print('settings.py OK')"
```

### 5. Check it works

```bash
python3 pulse.py --test
```

It sends one report and stops. Look for `Success` and the **Client link** for this tab, then check the machine appears on PulseBoard.

### 6. Start, stop, and start automatically

**Start the exhibit:**

```bash
~/Documents/Neuronic/neuron-scripts/launch.sh
```

To try other settings, run `./launch.sh settings-edit.py`, as described in [Trying settings without changing settings.py](#trying-settings-without-changing-settingspy).

**Stop the exhibit:** stop the scripts, then close the app.

```bash
pkill -f neuron-scripts/guard.py; pkill -f neuron-scripts/pulse.py; pkill -f neuron-scripts/clean_up_folder.py
```

> `launch.sh` stops **every** `python3` program for this user when it starts. Don't run other Python programs on an exhibit machine.

**Start automatically at sign-in, and add a desktop shortcut.** Paste this whole block into Terminal:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/neuron-launcher.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Launch
Comment=Start the Neuronic exhibit
Exec=$HOME/Documents/Neuronic/neuron-scripts/launch.sh
Path=$HOME/Documents/Neuronic/neuron-scripts
Icon=$HOME/Documents/Neuronic/neuron-scripts/logo/neuronic.png
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
DESK="$(xdg-user-dir DESKTOP)"
cp ~/.config/autostart/neuron-launcher.desktop "$DESK/"
chmod +x "$DESK/neuron-launcher.desktop"
gio set "$DESK/neuron-launcher.desktop" metadata::trusted true 2>/dev/null || true
```

The first part makes the exhibit start whenever you sign in. The second puts a **Launch** icon on the desktop. On Ubuntu, if the icon doesn't run when double-clicked, right-click it and choose **Allow Launching**.

**Sign in automatically.** Like the Windows Startup folder, auto-start only runs once someone signs in. On Ubuntu, open **Settings → Users** (or **System → Users**), click **Unlock**, and turn on **Automatic Login**. Then restart to check the exhibit starts by itself.

**Turn off auto-start:**

```bash
rm ~/.config/autostart/neuron-launcher.desktop
```

### Updating on Linux

`launch.sh` runs `git pull` on every start. To update by hand:

```bash
cd ~/Documents/Neuronic/neuron-scripts
git pull
python3 -m pip install --user -r requirements.txt
```

Add `--break-system-packages` to the last line if you needed it in step 3.

**Extra apps on start:** `launch.sh` runs `launch_aux.sh` before `guard.py`. Add any extra programs to start there.

---

## Edit the settings

Open the file with:

```bat
notepad "%USERPROFILE%\Documents\Neuronic\neuron-scripts\settings.py"
```

**How to edit `settings.py`**

- Each setting looks like `name = value`. Only change the part after `=`.
- Text goes inside quotes: `exhibitName = "SKELETAL-POP-1"`.
- For Windows folder paths, put an `r` in front of the quotes so the backslashes work: `appEXEPath = r'C:\Users\admin\Documents\Neuronic\Skeletal Pop'`.
- On/off settings are `True` or `False`, capitalized and without quotes.
- Lists use square brackets: `appEXEParam = ["-fullscreen", "-vrmode"]`. Use `[]` for an empty list.
- Lines starting with `#` are comments and are ignored.
- Replace every `???` with a real value.
- After saving, check the file for mistakes with:
  ```bat
  py -3 -c "import settings_loader, settings; print('settings.py OK')"
  ```
  If there's an error, it shows the line number.

**On Linux,** paths look different. See step 4 of [Install on Linux](#install-on-linux).

Most exhibits only need the **Required** settings. Every other section is only for exhibits that use that feature.

### Required: PulseBoard reporting

| Setting | What it does | Example |
|---|---|---|
| `sheetID` | The Google Sheet that PulseBoard reports go to. Leave it as it is unless you're told otherwise. | `"1FDmuen…"` |
| `sheetName` | The tab in that sheet for this site or client. If the tab doesn't exist yet, it's created on the first report. | `"CMH"` |
| `exhibitName` | This machine's name. It must be **unique on that tab**, because it's how PulseBoard finds this machine's row. Use capitals and dashes, with no spaces. | `"SKELETAL-POP-1"` |

### Required: the exhibit app

| Setting | What it does | Example |
|---|---|---|
| `appPath` | The folder that holds the apps. By default it's `Documents\Neuronic`, found even if Documents has been moved. Older installs use `r'C:\Users\<user>\Documents\Neuronic\Apps'`. | (leave as is) |
| `appFolder` | The app's folder name inside `appPath`. Updates are downloaded and unzipped here. Older settings files call this `appName`, which still works. | `'Skeletal Pop'` |
| `appEXEPath` | The folder that contains the app's `.exe`. | `r'C:\Users\admin\Documents\Neuronic\Skeletal Pop\Skeletal Pop Win'` |
| `appEXEName` | The `.exe` file that `guard.py` starts and watches. **Leave it blank** to show only a full-screen lock screen with the logo, which is useful before the app is installed. | `'skeletal-pop.exe'` |
| `appEXEParam` | Extra command-line options for the app, as a list. | `["-fullscreen"]` or `[]` |

**Web exhibits (Chrome kiosk):** set `appEXEPath` to Chrome's folder and `appEXEName` to `chrome.exe`. Then put the page to open in `appURL`. Chrome opens full-screen in kiosk mode, and `appEXEParam` is ignored.

| Setting | What it does |
|---|---|
| `appURL` | The web page Chrome opens in kiosk mode. Only used for Chrome. |
| `appParams` | Older setting, kept for compatibility. |

### Look and behavior

| Setting | What it does | Default |
|---|---|---|
| `logoBrand` | The client logo image, from the `logo` folder. It's shown on the desktop and the lock screen (Windows only). See [Change the logo](#change-the-logo). | `"neuronic.png"` |
| `lockScreenColor` | The lock screen's background color, as a hex code or a color name (Windows only). | `"#403a7a"` |
| `checkForUpdate` | `True` makes `launch.cmd` check for a newer app version on each start, using `archive.txt` in the app folder. Use it for zipped apps such as Unity builds. | `False` |
| `crashPath` | The log file `guard.py` writes to, in the scripts folder. | `"crash.log"` |

### Change the logo

On Windows, `guard.py` shows the logo in two places:

- **Desktop background:** while the exhibit runs, the logo becomes the desktop wallpaper. Anyone who gets past the app sees it instead of the usual desktop.
- **Lock screen:** if `appEXEName` is blank, a full-screen window shows the logo in the middle of a `lockScreenColor` background.

Linux doesn't show the logo.

**To use a client's logo:**

1. **Prepare the image** as a **PNG** file. The lock screen can only show PNG (or GIF), not JPG. A transparent background blends into `lockScreenColor` on the lock screen. On the desktop, check how Windows displays it, or give the logo a solid background that matches `desktopColor`.
2. **Size it to fit the screen.** The lock screen shows the image at its **actual pixel size** and doesn't shrink it, so a large image gets cut off. Around **800–1200 pixels wide** suits a 1920×1080 display.
3. **Give it a new name** and copy it into the `logo` folder, for example `logo\cmh.png`.
   > **Don't replace `neuronic.png`.** It's part of the repo, so overwriting it makes the automatic `git pull` in `launch.cmd` fail. That stops the scripts from updating. A new file name avoids this.
4. **Point the settings at it** in `settings.py`:
   ```python
   logoBrand = "cmh.png"
   ```
   Use only the file name, without the `logo\` folder.
5. **Optional colors.** These are hex codes or color names:
   - `lockScreenColor` sets the lock screen's background.
   - `desktopColor = RGB(255, 255, 255)` sets the desktop color around the wallpaper logo. It's black by default; note the different format.
6. **Restart the exhibit** to see it. Run `launch.cmd`, or press **Ctrl+Shift+S** and start it again.

**How the logo fills the desktop:** `guard.py` centers it with Windows' **Fit** placement, so the whole logo is scaled to the screen without cropping. To place it differently, add one of these to `settings.py`:
   ```python
   logoWallpaperStyle = "center"   # "fit" (default), "center" (real size), "fill" or "stretch"
   ```
   The PC's own wallpaper placement is put back when you quit with Ctrl+Shift+S.

**After quitting with Ctrl+Shift+S,** the desktop wallpaper is set back to the first image in the `background` folder.

**Same logo on every machine?** Commit the new file to the repo, and `git pull` will deliver it to every exhibit. For a single machine, just copy the file in. Git leaves files it doesn't track alone.

### OBS and camera (only for exhibits that use OBS; Windows only)

| Setting | What it does |
|---|---|
| `startObs` | `True` makes `launch.cmd` start OBS. Leave it `False` if the exhibit doesn't use OBS, and the rest of this section is ignored. |
| `obsHost`, `obsPort`, `obsPassword` | The OBS WebSocket connection. Find these in OBS under **Tools → WebSocket Server Settings**. |
| `obsProjectorMonitor` | Which monitor (counting from 0) gets the projector, if OBS has no saved projector layout yet. |
| `cameraSource` | The webcam source's exact name in OBS. |
| `resetCameraOnStart` | `True` restarts the camera's power each time OBS starts. Only turn this on after the hub settings below are confirmed working. |
| `cameraHubComPort` | The COM port of the StarTech USB hub, such as `"COM3"`. Run `CUSBC /Q` to find it. Camera resets don't happen without it. |
| `cameraHubPort` | The hub port the camera is plugged into. **Use port 1**, the only port that fully cuts power. |
| `cameraHubCusbcPath` | The full path to `CUSBC.exe` if Windows can't find it on its own. |
| `cameraHubPowerOffSec` | How many seconds the camera stays off during a reset. |

### Video (`send_video.py`)

| Setting | What it does |
|---|---|
| `introDir`, `outroDir` | The folders with intro and outro clips, named by story number (`1.mp4`, `2.mp4`, and so on). |
| `videoOutputDir` | Where finished videos are saved. |
| `ffmpegPath` | Leave it as `"ffmpeg"` if Windows can find ffmpeg on its own. Otherwise use the full path to `ffmpeg.exe`. |
| `videoTargetWidth`, `videoTargetHeight`, `videoTargetFps` | The size and frame rate every clip is converted to before they're joined. |

### Folder cleanup (`clean_up_folder.py`)

| Setting | What it does |
|---|---|
| `cleanupFolders` | The folders to clean automatically while the exhibit runs. Leave it as `[]` to turn cleanup off. Each item is either a folder path, or something like `{"folder": r"C:\...", "maxAge": 5, "unit": "minutes"}` to set the age for that folder. |
| `cleanupMaxAgeDays` | Files older than this many days are deleted, unless an item above sets its own age. |
| `cleanupIntervalSec` | How often, in seconds, the folders are checked. |

### Email (`send_email.py`, `send_email_bulk.py`)

| Setting | What it does |
|---|---|
| `provider` | Which email service to use: `"office365"`, `"gmail"`, `"greengeeks"` or `"mailgun"`. |
| `sender_name`, `sender_email` | Who emails come from. |
| `smtp_host`, `smtp_port` | Leave these blank to use the provider's defaults. GreenGeeks requires `smtp_host`, usually `mail.yourdomain.com`. |
| `tenant_id`, `client_id`, `scopes` | Office 365 only. These come from the Azure app registration; the steps are at the top of `oauth365.py`. |
| `gmail_app_password` | Gmail only. Create one at <https://myaccount.google.com/apppasswords>. The account needs 2-Step Verification turned on first. |
| `smtp_login`, `smtp_password` | GreenGeeks and Mailgun only. The mailbox or SMTP login. |
| `send_daily_test_mail_to` | If set, a daily email with the number of emails sent goes to this address. |
| `mail_log_folder` | If set, every send is logged to `mail_log.csv` in this folder. |
| `folder` | `send_email_bulk.py` only. The folder whose files get emailed. |
| `subject`, `message` | The email's subject and HTML body. |

### SharePoint upload (`send_to_sharepoint.py`)

This uses the same Azure app as Office 365 email, with the **Sites.ReadWrite.All** permission added.

| Setting | What it does |
|---|---|
| `sharepoint_username` | The account to sign in with. Leave it blank to use `sender_email`. |
| `sharepoint_hostname`, `sharepoint_site_path` | From the site's address. For `https://contoso.sharepoint.com/sites/Exhibits`, they're `"contoso.sharepoint.com"` and `"/sites/Exhibits"`. |
| `sharepoint_folder` | The folder to upload to inside the site's documents. Leave it blank for the top level. |

> **Keep passwords out of Git.** `settings.py` is meant to stay on the machine. Never commit it, and don't put real passwords or keys in `settings.py.sample`.

### Trying settings without changing `settings.py`

Copy the settings to a new file, edit the copy, and start the exhibit with it:

```bat
copy settings.py settings-edit.py
notepad settings-edit.py
launch.cmd settings-edit.py
```

Plain `launch.cmd` goes back to `settings.py`.

---

## Start the exhibit

```bat
"%USERPROFILE%\Documents\Neuronic\neuron-scripts\launch.cmd"
```

To install a new app from its `archive.txt` link:

```bat
py -3 install.py --archive https://example.com/path/to/archive.txt
```

That creates `appPath\appFolder`, downloads the app and unzips it there.

**Extra apps on start:** to start other programs before the exhibit locks the desktop, copy `launch_aux.cmd.sample` to `launch_aux.cmd` and add their commands.

---

## Updating

`launch.cmd` runs `git pull` on every start, so the scripts update themselves. To update by hand:

```bat
cd "%USERPROFILE%\Documents\Neuronic\neuron-scripts"
git pull
py -3 -m pip install -r requirements.txt
```

When new settings are added to `settings.py.sample`, copy the ones you need into your `settings.py`. Any setting you don't add keeps its default value.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'py' is not recognized` or `'git' is not recognized` | Close Command Prompt and open a new one. If it still fails, run the `winget install` command again, or install from <https://python.org> (tick **Add python.exe to PATH**) or <https://git-scm.com>. |
| `Settings file not found` | You skipped `copy settings.py.sample settings.py`, or you ran the scripts from a different folder. |
| `SyntaxError` mentioning `settings.py` | There's a typo in `settings.py`, often a missing quote or bracket, or `true` instead of `True`. The error message gives the line number. |
| `ERROR: Application not found` | `appEXEPath` and `appEXEName` don't point to a real `.exe`. Check both, and check the `r` in front of the path. |
| `launch.cmd` can't find the scripts | The scripts must be in `%USERPROFILE%\Documents\Neuronic\neuron-scripts`. |
| `unable to get local issuer certificate` | Run `py -3 -m pip install certifi`. |
| `Failed building wheel for cryptography` or `link.exe was not found` | This PC is Windows on ARM (the Python folder name ends in `-arm64`). Update the scripts (`git pull`) and run `py -3 -m pip install -r requirements.txt` again. `requirements.txt` now picks a `cryptography` version with a ready-made ARM build, so Visual Studio isn't needed. |
| `ModuleNotFoundError: No module named ...` | Run `py -3 -m pip install -r requirements.txt` again. |
| Machine doesn't appear on PulseBoard | Check `sheetID`, `sheetName` and `exhibitName`, then run `py -3 pulse.py --test` and read the message. |
| Desktop stays locked | Press **Ctrl+Shift+S**. |
| Exhibit doesn't start after a reboot | Check there's a shortcut in `shell:startup` and that Windows signs in automatically (Install on Windows, step 6). |
| PowerShell shortcut command fails | Create the shortcuts by hand instead (Install on Windows, step 6). |
| App keeps crashing | Check `crash.log` in the scripts folder. |
| Desktop logo is off-center | Update the scripts (`git pull`). `guard.py` now centers it. Check `logoWallpaperStyle` isn't set to something odd ([Change the logo](#change-the-logo)). |
| Lock screen shows no logo, or only part of it | Check `logoBrand` matches a **PNG** file in the `logo` folder. If only part shows, make the image smaller ([Change the logo](#change-the-logo)). |
| `git pull` fails with *Your local changes would be overwritten* | A file from the repo was changed on this machine, often the logo. Run `git checkout -- logo` to undo, then use a new file name ([Change the logo](#change-the-logo)). |
| **Linux:** `externally-managed-environment` when installing packages | Add `--break-system-packages` (Install on Linux, step 3). |
| **Linux:** `Permission denied` running `launch.sh` | Run `chmod +x ~/Documents/Neuronic/neuron-scripts/launch.sh`. |
| **Linux:** the app doesn't start | Check `guard.log` in the scripts folder. Make sure the app file can run (`chmod +x`), and that `appEXEPath` and `appEXEName` are right. |
| **Linux:** `Hotkey not available` in `guard.log` | This is expected without root. Stop the exhibit with the command in Install on Linux, step 6. |
