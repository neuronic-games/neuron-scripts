# Sends email via Office 365, Gmail, or GreenGeeks - see email_setting.py
# to pick the provider and fill in its credentials.
# Requires: pip install msal

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
import os
import email_setting
import mail_auth
import mail_stats
import mail_log

receiver_email = "tam@myaing.com"
msg_html = email_setting.message

def send_email_with_attachment(to_addr, attachment_file = None):
    msg = MIMEMultipart()
    msg['Subject'] = email_setting.subject
    msg['From'] = email_setting.sender_email
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
        server.sendmail(email_setting.sender_email, to_addr, msg.as_string())
        server.quit()
    except Exception as e:
        mail_log.log_sent(to_addr, attachment_size=attachment_size, success=False, error=str(e))
        raise

    mail_stats.record_sent()
    mail_log.log_sent(to_addr, attachment_size=attachment_size, success=True)

    print (datetime.now(), ": Mail sent to", to_addr)

# Try to log in to server and send email
try:
    send_email_with_attachment(receiver_email)

except Exception as e:
    # Print any error messages to stdout
    print(e)
finally:
    print ("Done")

# If a full calendar day's worth of sends hasn't been reported yet, email
# the daily stats now (no-op unless email_setting.send_daily_test_mail_to
# is set and a day boundary has actually passed).
try:
    mail_stats.send_daily_report_if_due()
except Exception as e:
    print("Daily report error:", e)
