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

"""One-line documentation for report module.

A detailed description of report.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'


import base64
import select
import smtplib
import sys
import time

def email(snd, rcv, subject, msg):
  marker = "4a7116234a8bb0e881b8d6938f58cc81"

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

  smtpObj = smtplib.SMTP('smtp.google.com')
  smtpObj.sendmail(snd, rcv, message)


def email_data(filename, filecontent, snd, rcv, subject, msg):
  content = base64.b64encode(filecontent)  # base64
  marker = "4a7116234a8bb0e881b8d6938f58cc81"

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

  smtpObj = smtplib.SMTP('smtp.google.com')
  smtpObj.sendmail(snd, rcv, message)


def email_file(filename, snd, rcv, subject, msg):
  filecontent = open(filename, 'rb').read()
  email_data(filename, filecontent, snd, rcv, subject, msg)

def main():
  filename = "test.txt"
  filecontent = "This is the testfile content."
  snd = 'gavaletz@google.com'
  rcv = 'gavaletz@google.com'
  subject = "Testing report.py"
  msg = "The subject says it all..."
  email_data(filename, filecontent, snd, rcv, subject, msg)
  email(snd, rcv, subject, msg)

if __name__ == '__main__':
  main()
