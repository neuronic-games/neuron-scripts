# Tracks how many emails have been sent per calendar day, and (optionally)
# emails a daily summary once a day's count is final.
#
# Enable the daily summary by setting settings_email.send_daily_test_mail_to
# to an address; leave it "" to disable.
#
# Usage:
#   - Call record_sent() once per successfully sent email.
#   - Call send_daily_report_if_due() periodically - send_email_bulk.py
#     does this once per loop iteration; a one-shot script like
#     send_email.py can just call it once before exiting. It's a no-op
#     except the first time it's called after a calendar day has ended,
#     so it's safe to call as often as you like.
#
# Counts are persisted to mail_stats.json (next to these scripts) so they
# survive restarts of the long-running bulk sender.

import json
import os
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import settings_email
import mail_auth

_STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mail_stats.json")


def _load():
    if os.path.exists(_STATS_FILE):
        try:
            with open(_STATS_FILE, "r") as f:
                data = json.load(f)
                data.setdefault("counts", {})
                data.setdefault("last_report_date", "")
                return data
        except (ValueError, OSError):
            pass
    return {"counts": {}, "last_report_date": ""}


def _save(data):
    with open(_STATS_FILE, "w") as f:
        json.dump(data, f)


def _touch_today(data):
    """Make sure today has an entry (defaulting to 0) so a quiet day still
    shows up in the daily report instead of being silently skipped."""
    today = date.today().isoformat()
    data["counts"].setdefault(today, 0)
    return today


def record_sent():
    """Call once per successfully sent email."""
    data = _load()
    today = _touch_today(data)
    data["counts"][today] += 1
    _save(data)


def get_today_count():
    data = _load()
    today = _touch_today(data)
    _save(data)
    return data["counts"][today]


def send_daily_report_if_due():
    """If settings_email.send_daily_test_mail_to is set and there's a
    completed calendar day (yesterday or earlier) that hasn't been
    reported yet, email its send count and mark it reported."""
    to_addr = getattr(settings_email, "send_daily_test_mail_to", "")
    if not to_addr:
        return

    data = _load()
    today = _touch_today(data)
    _save(data)

    last_report = data.get("last_report_date", "")
    completed_days = sorted(d for d in data["counts"] if d < today and d > last_report)
    if not completed_days:
        return

    day_iso = completed_days[-1]  # most recent completed, unreported day
    count = data["counts"][day_iso]

    _send_report_email(to_addr, day_iso, count)

    # Only mark as reported (and prune) once the email actually goes out,
    # so a send failure gets retried on the next call instead of lost.
    data["last_report_date"] = day_iso
    data["counts"] = {d: c for d, c in data["counts"].items() if d > day_iso}
    _save(data)


def _send_report_email(to_addr, day_iso, count):
    body = """\
<html>
  <body>
    Daily email report for {day}<br>
    Emails sent: {count}
  </body>
</html>
""".format(day=day_iso, count=count)

    msg = MIMEMultipart()
    msg['Subject'] = "Daily test mail: {} email(s) sent on {}".format(count, day_iso)
    msg['From'] = settings_email.sender_email
    msg['To'] = to_addr
    msg.attach(MIMEText(body, 'html'))

    server = mail_auth.connect()
    server.sendmail(settings_email.sender_email, to_addr, msg.as_string())
    server.quit()
