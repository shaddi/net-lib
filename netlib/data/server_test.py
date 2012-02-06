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

"""Tests for netlib.data.server.

Test coverage is pretty light for this module, but most of the code in the
module is boiler plate and would required many many mocks to be created.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import unittest

from netlib.data import server


# Key constants
IP_0 = '192.168.42.100'
DATA_0 = 'whee'
IP_1 = '192.168.24.100'
DATA_1 = 'oops'
PATH_ALL = 'funny'
DATA_ALL = 'haha'
POST_PATH = 'keepThis'


class DataServerTest(unittest.TestCase):
  """Test for DataServer."""

  def setUp(self):
    """Make sure we are starting from a clean slate."""
    server.DataServer.data_recv = dict()
    server.DataServer.ip_data_store = {IP_0: DATA_0, IP_1: DATA_1}
    server.DataServer.all_data_store = {PATH_ALL: DATA_ALL}
    self.get_all_data = server.DataServer.GET_ALL_DATA

  def testGetCallback(self):
    """Testing the the right data is returned."""
    ret = server.DataServer.GetCallback(None, IP_0, '')
    self.assertEqual(ret, DATA_0)
    ret = server.DataServer.GetCallback(None, IP_1, '')
    self.assertEqual(ret, DATA_1)
    ret = server.DataServer.GetCallback(None, IP_0, PATH_ALL)
    self.assertEqual(ret, DATA_ALL)
    ret = server.DataServer.GetCallback(None, IP_1, PATH_ALL)
    self.assertEqual(ret, DATA_ALL)

  def testPostCallback(self):
    """Tesintg that data is stored with the right key."""
    ret = server.DataServer.PostCallback(None, IP_0, POST_PATH, DATA_0)
    key_0 = '%s_%s' % (POST_PATH, IP_0)
    self.assertEqual(ret, '%s = %d Bytes' % (key_0, len(DATA_0)))
    ret = server.DataServer.PostCallback(None, IP_1, POST_PATH, DATA_1)
    key_1 = '%s_%s' % (POST_PATH, IP_1)
    self.assertEqual(ret, '%s = %d Bytes' % (key_1, len(DATA_1)))
    data = {key_0: DATA_0, key_1: DATA_1}
    ret = ret = server.DataServer.GetCallback(None, IP_0, self.get_all_data)
    self.assertDictEqual(ret, data)
#END CLASS DataServerTestTest


if __name__ == '__main__':
  unittest.main()
