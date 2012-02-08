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

"""Tests for netlib.report.report.

This is not a real unit test and you are going to have to see if the email
actually shows up or not.  One day we might have a real unit test, but for now
using this as a functional test is more practical.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import unittest

from netlib import config
from netlib.report import report


class EmailTest(unittest.TestCase):
  """Test for Email."""

  def setUp(self):
    self.filename = 'test.txt'
    self.filecontent = 'This is the testfile content.'
    self.msg = 'Testing netlib.report'
    if config.EMAIL_SND_PASS == '':
      report.SetPassword()

  def testConfig(self):
    """Make sure we have settings that are OK."""
    self.assertGreaterEqual(len(config.EMAIL_SND), 6)
    self.assertIn('@', config.EMAIL_SND)
    self.assertIn('.', config.EMAIL_SND)
    self.assertGreaterEqual(len(config.EMAIL_SND_PASS), 1)
    self.assertGreaterEqual(len(config.EMAIL_RCV), 6)
    self.assertIn('@', config.EMAIL_RCV)
    self.assertIn('.', config.EMAIL_RCV)
    self.assertGreaterEqual(len(config.EMAIL_SMTP), 4)
    self.assertIn('.', config.EMAIL_SMTP)
    self.assertGreaterEqual(config.EMAIL_SMTP_PORT, 1)

  def testEmail(self):
    """Try sending a plain message."""
    report.Email(self.msg)

  def testEmailData(self):
    """Try sending a message with data."""
    report.EmailData(self.filename, self.filecontent, self.msg)
#END CLASS EmailTest


if __name__ == '__main__':
  unittest.main()
