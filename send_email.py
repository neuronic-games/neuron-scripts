# Test email sending. Pyton v2

from datetime import datetime
""" from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.mime.text import MIMEText """
from email import Encoders
import smtplib, ssl
import email_setting
import argparse

receiver_email = "tam@myaing.com"
msg_html = email_setting.message

# Create a secure SSL context (with Python 3)
# context = ssl.create_default_context()

def send_email_with_attachment(to_addr, attachment_file = None):
    msg = MIMEMultipart()
    msg['Subject'] = email_setting.subject
    msg['From'] = email_setting.sender_email
    msg['To'] = to_addr

    part2 = MIMEText(msg_html, 'html')
    msg.attach(part2)

    if attachment_file:
        part3 = MIMEBase('application', "octet-stream")
        part3.set_payload(open(attachment_file, "rb").read())
        Encoders.encode_base64(part3)

        visible_name = "attachment"
        extension = os.path.splitext(attachment_file)[1]
        part3.add_header('Content-Disposition', 'attachment; filename="' + visible_name + extension + '"')
        msg.attach(part3)

    server = smtplib.SMTP(email_setting.smtp_server, email_setting.port)
    server.ehlo() # Can be omitted
    server.starttls() #context=context) # Secure the connection (with Phyton 3)
    server.ehlo() # Can be omitted
    server.login(email_setting.sender_email, email_setting.password)
    server.sendmail(email_setting.sender_email, to_addr, msg.as_string())
    server.quit()

    print datetime.now(), ": Mail sent to", to_addr
  
# Try to log in to server and send email
try:
    send_email_with_attachment(receiver_email)

except Exception as e:
    # Print any error messages to stdout
    print(e)
finally:
    print "Done"