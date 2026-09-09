# Sends email via Office 365, Gmail, or GreenGeeks - see settings.py
# to pick the provider and fill in its credentials.
# Requires: pip install msal

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
import os
import sys

import settings_loader  # must run before `import settings` below
import settings
import mail_auth
import mail_stats
import mail_log

# Usage: python send_email.py <recipient_email> [attachment_file]
if len(sys.argv) < 2:
    print("Usage: python send_email.py <recipient_email> [attachment_file]")
    sys.exit(1)

receiver_email = sys.argv[1]
attachment_arg = sys.argv[2] if len(sys.argv) > 2 else None
msg_html = settings.message

def send_email_with_attachment(to_addr, attachment_file = None):
    msg = MIMEMultipart()
    msg['Subject'] = settings.subject
    msg['From'] = settings.sender_email
    msg['To'] = to_addr

    part2 = MIMEText(msg_html, 'html')
    msg.attach(part2)

    attachment_size = None
    if attachment_file:
        data = open(attachment_file, "rb").read()
        attachment_size = len(data)

        part3 = MIMEBase('application', "octet-stream")
        part3.set_payload(data)
        encode_base64(part3)

        visible_name = "attachment"
        extension = os.path.splitext(attachment_file)[1]
        part3.add_header('Content-Disposition', 'attachment; filename="' + visible_name + extension + '"')
        msg.attach(part3)

    try:
        server = mail_auth.connect()
        server.sendmail(settings.sender_email, to_addr, msg.as_string())
        server.quit()
    except Exception as e:
        mail_log.log_sent(to_addr, attachment_size=attachment_size, success=False, error=str(e))
        raise

    mail_stats.record_sent()
    mail_log.log_sent(to_addr, attachment_size=attachment_size, success=True)

    print (datetime.now(), ": Mail sent to", to_addr)

# Try to log in to server and send email
try:
    send_email_with_attachment(receiver_email, attachment_arg)

except Exception as e:
    # Print any error messages to stdout
    print(e)
finally:
    print ("Done")

# If a full calendar day's worth of sends hasn't been reported yet, email
# the daily stats now (no-op unless settings.send_daily_test_mail_to
# is set and a day boundary has actually passed).
try:
    mail_stats.send_daily_report_if_due()
except Exception as e:
    print("Daily report error:", e)
