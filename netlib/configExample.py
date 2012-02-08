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

"""config.py provides package wide configurations.

This module groups together variables that are referenced throughout the
package, and provides a single place to change package configurations.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import logging
import sys

DATA_HOST = ''  # Symbolic name meaning the local host
DATA_PORT = 50007  # Arbitrary non-privileged port
LOCAL_LOOPBACK = '127.0.0.1'

CONTROL_SERVER = 'yourServer.yourDomain.com'
CONTROL_SERVER_PORT = 50007

DEBUG = logging.INFO

FORMAT = ('%(asctime)-15s [%(levelname)s] %(process)d %(filename)s:%(lineno)d '
          '-%(funcName)s- %(message)s')

logging.basicConfig(format=FORMAT, level=DEBUG)

TIMEOUT = 100  # seconds
WAIT_TIME = 5  # seconds

DEFAULT_HOST = 'anyhost'
DEFAULT_INTERFACE = 'eth0'

TCPDUMP_COUNT = 100

header_list = {'User-Agent': 'python-%s.%s' % ('net-lib', '0.1')}
BANNED_NETLOCS = ['ad.doubleclick.net',
                  'fls.doubleclick.net',
                  'b.scorecardresearch.com']


# Settings for the report module.
EMAIL_SND = 'userName@gmail.com'
EMAIL_SND_PASS = ''  # Fill this in to stop the password prompt.
EMAIL_RCV = EMAIL_SND
EMAIL_SUBJECT = 'net-lib status update'
EMAIL_DATA_SUBJECT = 'net-lib data'
EMAIL_SMTP = 'smtp.gmail.com'
EMAIL_SMTP_PORT = 587
