#!/usr/bin/python2.6
#
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module allows you to easily send updates via email.

Because no one wants to hang out and wait for results to complete...this is
designed so that you can put in your password early on (or you can store it in
plaintext in the config file if you are brave) and place status update points
throughout (or maybe at the end) of your experiment.

  Email: Method for sending a simple message.
  EmailData: Method for sending a string as a file attachment.
  EmailFile: Sends the binary content of a file as an attachment.
  SetPassword: So you don't have to store a password in the config file.

Simple usage:
  filename = 'test.txt'
  filecontent = 'This is the testfile content.'
  snd = 'userName@gmail.com'
  rcv = 'otherName@gmail.com'
  subject = 'Testing report.py'
  msg = 'The subject says it all...'
  snd_pass = SetPassword() #Should record this while you are still around!
  EmailData(filename, filecontent, msg, snd, snd_pass, rcv, subject)

Simple usage (config file used):
  SetPassword()
  filename = 'test.txt'
  filecontent = 'This is the testfile content.'
  msg = 'The subject says it all...'
  EmailData(filename, filecontent, msg)
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'


import base64
import getpass
import logging
import select
import smtplib
import sys
import time

from netlib import config


def Email(msg, snd=config.EMAIL_SND, rcv=config.EMAIL_RCV,
    subject=config.EMAIL_SUBJECT):
  """Method for sending a simple message.

  Uses the SMTP server that is set in the config file to send a message to the
  recipient.  This has an unusually broad catch statement so that it is
  not likely to end an experiment because of a reporting error.

  Args:
    msg: the message to be sent.
    snd: the sender's email address.
    snd_pass: the sender's smtp server password (text).
    rcv: the recipient's email address.
    subject: the subject for the email.

  Returns:
    URLRecord: see the URLRecord class for a more complete description.

  Raises:
    all lower exceptions caught here -- Generally bad to do, but because we
    are depending on unreliable 3rd party resources we don't want to throw
    everything away on an error.  Just don't use this point of data.
    No new exceptions generated here.
  """
  marker = '4a7116234a8bb0e881b8d6938f58cc81'

  # Define the main headers.
  part1 = """From: %s <%s>
To: %s <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (snd.split('@')[0], snd,
         rcv.split('@')[0], rcv,
         subject, marker, marker)

  # Define the message action
  part2 = """Content-Type: text/plain
Content-Transfer-Encoding:8bit

%s
--%s
""" % (msg,marker)
  message = part1 + part2

  try:
    mailServer = smtplib.SMTP(config.EMAIL_SMTP, config.EMAIL_SMTP_PORT)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(snd, GetPassword())
    mailServer.sendmail(snd, rcv, message)
    mailServer.close()
  # Failure is not an option.  See docstring for details.
  except:  #pylint: disable-msg=W0702
    logging.error('EXCEPTION \"%s\" while sending email.', sys.exc_info()[0])


def EmailData(filename, filecontent, msg, snd=config.EMAIL_SND,
    rcv=config.EMAIL_RCV, subject=config.EMAIL_DATA_SUBJECT):
  """Method for sending a string as a file attachment.

  Uses the SMTP server that is set in the config file to send a message to the
  recipient.  The filename is the name that will be given to the file in the
  email, and the filecontent will be the MIME encoded content for that file.
  This has an unusually broad catch statement so that it is not likely to end
  an experiment because of a reporting error.

  Args:
    filename: the name that will be given to the email attachment.
    filecontent: the content of the email attachment.
    msg: the message to be sent.
    snd: the sender's email address.
    snd_pass: the sender's smtp server password (text).
    rcv: the recipient's email address.
    subject: the subject for the email.

  Raises:
    all lower exceptions caught here -- Generally bad to do, but because we
    are depending on unreliable 3rd party resources we don't want to throw
    everything away on an error.  Just don't use this point of data.
    No new exceptions generated here.
  """
  content = base64.b64encode(filecontent)  # base64
  marker = '4a7116234a8bb0e881b8d6938f58cc81'

  # Define the main headers.
  part1 = """From: %s <%s>
To: %s <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (snd.split('@')[0], snd,
         rcv.split('@')[0], rcv,
         subject, marker, marker)

  # Define the message action
  part2 = """Content-Type: text/plain
Content-Transfer-Encoding:8bit

%s
--%s
""" % (msg,marker)

  # Define the attachment section
  part3 = """Content-Type: multipart/mixed; name=\"%s\"
Content-Transfer-Encoding:base64
Content-Disposition: attachment; filename=%s

%s
--%s--
""" %(filename, filename, content, marker)
  message = part1 + part2 + part3

  try:
    mailServer = smtplib.SMTP(config.EMAIL_SMTP, config.EMAIL_SMTP_PORT)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(snd, GetPassword())
    mailServer.sendmail(snd, rcv, message)
    mailServer.close()
  # Failure is not an option.  See docstring for details.
  except:  #pylint: disable-msg=W0702
    logging.error('EXCEPTION \"%s\" while sending email.', sys.exc_info()[0])


def EmailFile(filename, msg, snd=config.EMAIL_SND,
    rcv=config.EMAIL_RCV, subject=config.EMAIL_DATA_SUBJECT):
  """Sends the binary content of a file as an attachment.

  Uses the SMTP server that is set in the config file to send a message to the
  recipient.  The filename is the name that will be read and given to the file
  in the email.  This has an unusually broad catch statement so that it is not
  likely to end an experiment because of a reporting error.

  Args:
    filename: file to be read and attached to the email.
    msg: the message to be sent.
    snd: the sender's email address.
    snd_pass: the sender's smtp server password (text).
    rcv: the recipient's email address.
    subject: the subject for the email.

  Raises:
    all lower exceptions caught here -- Generally bad to do, but because we
    are depending on unreliable 3rd party resources we don't want to throw
    everything away on an error.  Just don't use this point of data.
    No new exceptions generated here.
  """
  filecontent = open(filename, 'rb').read()
  EmailData(filename, filecontent, msg, snd, rcv, subject)


def SetPassword():
  """So you don't have to store a password in the config file.

  Since most people will not want to store their password in plaintext in the
  config file this is a nice way to get it into memory so it can be used to send
  mail later.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  config.EMAIL_SND_PASS = getpass.getpass("SMTP Password: ")


def GetPassword():
  """So you don't have to store a password in the config file.

  Since most people will not want to store their password in plaintext in the
  config file this is a nice way to get it into memory so it can be used to send
  mail later.

  Returns:
    password: the smtp password that was just set.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  if config.EMAIL_SND_PASS == '':
    config.EMAIL_SND_PASS = getpass.getpass("SMTP Password: ")
  return config.EMAIL_SND_PASS
