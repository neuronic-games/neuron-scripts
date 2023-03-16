#!/usr/bin/env python
# coding: utf-8

# Copyright 2011 Álvaro Justen [alvarojusten at gmail dot com]
# License: GPL <http://www.gnu.org/copyleft/gpl.html>

import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from mimetypes import guess_type
from email.encoders import encode_base64
from getpass import getpass
from smtplib import SMTP


class Email(object):
    def __init__(self, from_, to, subject, message, message_type='plain',
                 attachments=None):
        self.email = MIMEMultipart()
        self.email['From'] = from_
        self.email['To'] = to
        self.email['Subject'] = subject
        text = MIMEText(message, message_type)
        self.email.attach(text)
        if attachments is not None:
            for filename in attachments:
                mimetype, encoding = guess_type(filename)
                mimetype = mimetype.split('/', 1)
                fp = open(filename, 'rb')
                attachment = MIMEBase(mimetype[0], mimetype[1])
                attachment.set_payload(fp.read())
                fp.close()
                encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment',
                                      filename=os.path.basename(filename))
                self.email.attach(attachment)

    def __str__(self):
        return self.email.as_string()


class EmailConnection(object):
    def __init__(self, server, username, password):
        if ':' in server:
            data = server.split(':')
            self.server = data[0]
            self.port = int(data[1])
        else:
            self.server = server
            self.port = 25
        self.username = username
        self.password = password
        self.connect()

    def connect(self):
        self.connection = SMTP(self.server, self.port)
        self.connection.ehlo()
        self.connection.starttls()
        self.connection.ehlo()
        self.connection.login(self.username, self.password)

    @staticmethod
    def get_email(email):
        if '<' in email:
            data = email.split('<')
            email = data[1].split('>')[0].strip()
        return email.strip()

    def send(self, message, from_=None, to=None):
        if isinstance(message, str):
            if from_ is None or to is None:
                raise ValueError('You need to specify `from_` and `to`')
            else:
                from_ = EmailConnection.get_email(from_)
                to = EmailConnection.get_email(to)
        else:
            from_ = message.email['From']
            to = message.email['To']
            message = str(message)
        return self.connection.sendmail(from_, to, message)

    def close(self):
        self.connection.close()