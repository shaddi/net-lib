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

"""Tests for netlib.data.convert."""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import unittest

from netlib.data import convert


class ColsToRowsTest(unittest.TestCase):
  """Test for ColsToRows."""

  def setUp(self):
    self.x = range(10)
    self.y = range(10)
    for i in range(10):
      self.x[i] = range(10)
      self.y[i] = [self.y[i]] * 10

  def tearDown(self):
    del self.x
    del self.y

  def testColsToRows(self):
    """Make sure that we are doing things right."""
    result = convert.ColsToRows(self.x)
    self.assertListEqual(self.y, result)
    for i in range(len(self.y)):
      self.assertListEqual(self.y[i], result[i])
#END CLASS ColsToRowsTest


class CopyAllTest(unittest.TestCase):
  """Test for CopyAll."""

  def testDict(self):
    """Make sure that we are doing things right."""
    x = {'Py': 'thon', 'Co': 'ookie', 'Go': 'ogle'}
    y = dict()
    convert.CopyAll(x, y)
    self.assertDictEqual(x, y)
    y['Go'] = 'gle'
    self.assertNotEqual(y['Go'], x['Go'])
#END CLASS CopyAllTest


if __name__ == '__main__':
  unittest.main()
