# Send Mail Scripts — Setup & Usage

Two scripts send email through the same shared configuration and auth layer:

- **`send_email.py`** — sends a single test email to the address hardcoded at the top of the file.
- **`send_email_bulk.py`** — watches a folder for `.csv` files (each naming a recipient + an attachment), emails them out, then deletes the processed files. Runs continuously and is meant to run unattended on Windows.

All configuration — provider choice, credentials, subject/message, folders — lives in **`settings_email.py`**, separate from `settings.py` (which holds this machine's kiosk/guard/pulse settings and is unrelated). `settings_email.py` is gitignored (so real credentials never get committed); `settings_email.py.sample` is the checked-in template to copy from on a fresh install.

Shared support files (you shouldn't need to edit these):

- **`mail_auth.py`** — connects to the right SMTP server and authenticates, based on `provider`.
- **`oauth365.py`** — handles the Office 365 OAuth2/MFA login flow.
- **`mail_stats.py`** — tracks daily send counts and emails the optional daily report.
- **`mail_log.py`** — writes the optional CSV log of every sent email.

## Requirements

```
pip install msal
```

`send_email_bulk.py` additionally needs the `keyboard` package (used for the Win+Shift+D shortcut that closes its hidden console) and only runs on Windows (it uses `ctypes.windll`).

## 1. Choose a provider

Open `settings_email.py` and set:

```python
provider = "office365"   # or "gmail", or "greengeeks"
```

Also fill in the always-required fields:

```python
sender_name = "..."
sender_email = "..."
```

Then follow the section below for whichever provider you picked.

### Office 365

Requires MFA-compatible OAuth2 (Microsoft no longer accepts plain passwords for SMTP once an account has MFA enabled). One-time setup in Azure Portal (Entra ID):

1. **App registrations → New registration**
   - Supported account types: *Accounts in this organizational directory only* (fine for most cases)
   - Redirect URI: *Public client/native (mobile & desktop)* → `http://localhost`
2. **API permissions → Add a permission → APIs my organization uses → "Office 365 Exchange Online" → Delegated permissions → `SMTP.Send`**
   (grant admin consent if your tenant requires it)
3. **Exchange admin center** → the mailbox → confirm **"Authenticated SMTP"** is enabled.
4. Copy the app's *Application (client) ID* and *Directory (tenant) ID* into `settings_email.py`:

```python
tenant_id = "..."
client_id = "..."
```

The first time you send an email, a browser window opens for you to log in — this is where MFA happens. After that, a refresh token is cached to `msal_token_cache.bin` (created next to the scripts) and reused silently, so scheduled/unattended runs won't prompt again until that token expires (Microsoft default: ~90 days of inactivity).

### Gmail

Google no longer accepts your regular account password for SMTP. Instead:

1. Turn on **2-Step Verification** on the Google account, if it isn't already.
2. Generate an app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Paste it into `settings_email.py`:

```python
gmail_app_password = "xxxx xxxx xxxx xxxx"   # spaces don't matter
```

No Google Cloud project or OAuth setup needed — the app password is the standard, simplest way to use Gmail SMTP on an MFA-enabled account.

### GreenGeeks (or other cPanel-hosted mail)

GreenGeeks' mail hosting doesn't support 2FA/OAuth on SMTP — it's a plain account password over an SSL connection (port 465). You need:

1. **`smtp_host`** — your mail server, usually `mail.yourdomain.com`. Confirm the exact value in cPanel → Email Accounts → **Connect Devices** for the mailbox (GreenGeeks doesn't use one universal hostname across all accounts).
2. **`greengeeks_password`** — the mailbox password.

```python
smtp_host = "mail.yourdomain.com"
greengeeks_password = "..."
```

## 2. Set the message content

Still in `settings_email.py`:

```python
subject = "..."
message = """\
<html>
  <head></head>
  <body>
    Your display email message here<br>
  </body>
</html>
"""
```

For `send_email_bulk.py` only, also set:

```python
folder = r'C:\path\to\watch'   # folder monitored for CSV files, and where attachments live
```

## 3. (Optional) Daily send-count report

Set `send_daily_test_mail_to` in `settings_email.py` to have a summary email sent automatically once each calendar day finishes, reporting how many emails were sent that day (including 0, on quiet days):

```python
send_daily_test_mail_to = "you@example.com"   # leave "" to disable
```

This works best with `send_email_bulk.py`, since it's the long-running process — it checks once per loop iteration and sends the report the first time it notices a day has ended, using counts persisted in `mail_stats.json`. `send_email.py` also records its sends and checks for a due report before exiting, so it'll pick up a pending report too if it's run at least once a day (e.g., via Task Scheduler), but a day with zero runs of either script won't get a report.

## 4. (Optional) Sent-mail CSV log

Set `mail_log_folder` in `settings_email.py` to have every send attempt appended as a row to `mail_log.csv` in that folder (header row written automatically the first time):

```python
mail_log_folder = r'C:\path\to\log'   # leave "" to disable
```

Columns: `date_time`, `email_address`, `attachment_size_bytes` (blank if there was no attachment), `success` (`True`/`False`), `error` (blank on success, the exception message on failure). Both successes and failures are logged — a failed send still gets a row with `success=False` and the error, it just isn't counted in the daily stats.

Both scripts write to the same file, so it accumulates a combined history across `send_email.py` test sends and `send_email_bulk.py` runs.

## 5. Running

**`send_email.py`** — edit `receiver_email` at the top of the file to your test address, then:

```
python send_email.py
```

It sends one email (with an optional attachment argument to `send_email_with_attachment`) and prints `Mail sent to ...` or the error.

**`send_email_bulk.py`**:

```
python send_email_bulk.py
```

It watches `settings_email.folder` for `*.csv` files. Each CSV should have one row per file:

```
recipient@example.com,attachment_filename.ext
```

The attachment file must already exist in the same folder. On finding a CSV, the script emails the recipient with that attachment, deletes the attachment on success, then deletes the CSV. Activity is logged to `send_mail.log` in that same folder. The script loops forever and hides its console window — press **Win+Shift+D** to close it. Only the *last* row of a CSV is actually processed if a file has multiple rows, so it's safest to keep one recipient per CSV.

Because this runs unattended, run it interactively once after setup (before it hides its window) so any first-time interactive login (Office 365 case) can complete. After that, it can run unattended.

## Notes

- `msal_token_cache.bin` (Office 365 only) holds your cached login — don't share or commit it. Delete it to force a fresh interactive login.
- Switching `provider` at any time re-routes both scripts to the new service; no other code changes needed.
- `smtp_host` / `smtp_port` in `settings_email.py` are optional overrides — leave blank to use each provider's default (Office 365 and Gmail already have sensible defaults; GreenGeeks requires `smtp_host` to be set explicitly).
- `mail_stats.json` holds the send counts behind the daily report. Delete it to reset counters; safe to do any time.
- `settings_email.py` is separate from `settings.py` (used by `guard.py`/`pulse.py` for kiosk monitoring) — the two aren't related, so email config never touches kiosk config or vice versa.
- If `mail_log_folder` isn't writable, the send itself still succeeds — a warning is just logged and the CSV write is skipped.
- While wiring up success/failure logging in `send_email_bulk.py`, fixed two pre-existing bugs it depended on: a typo (`Encoders.encode_base64` → `encoders.encode_base64`) that crashed any attachment send, and `send_email_with_attachment` unconditionally returning `True` even when sending failed (which caused `open_csv_and_send_mail` to treat failed sends as successful).
