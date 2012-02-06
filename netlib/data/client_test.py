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

"""Tests for netlib.data.client."""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import cPickle
import unittest

from netlib.data import client


# Our test data.
default_body = 'Just a string folks!'


class MockResponse(object):
  """Mock object for reponse objects returned by an http connections.

  This needs to allow for reading the response and accessing the headers.
  """

  headers = dict()

  def __init__(self, status=200, reason='OK', body=default_body):
    """Inits a MockResponse."""
    self.status = status
    self.reason = reason
    self.body = body

  # overriding a predefined method name.
  def read(self):  #pylint: disable-msg=C6409
    """Returns a string for the response body."""
    return self.body

  # overriding a predefined method name.
  def getheader(self, name):  #pylint: disable-msg=C6409
    """Returns a header."""
    if name == 'content-length':
      return len(self.body)
    else:
      return MockResponse.headers[name]


class MockHttpConnection(object):
  """Mock object for http connections.

  This needs to allow for making a request and getting the response.
  """

  post_data = ''

  # constructor signature needs to match.
  def __init__(self, netloc, timeout=0):  #pylint: disable-msg=W0613
    """Inits a MockHttp."""
    self.netloc = netloc

  # overriding a predefined method name.
  # constructor signature needs to match.
  def request(self, method, path,  #pylint: disable-msg=C6409,W0613
              body=None, headers=None):  #pylint: disable-msg=W0613
    """Sets up a MockResponse."""
    if method == 'POST':
      MockHttpConnection.post_data = body
    if path == 'pickle':
      MockResponse.headers = {'python-type': str(type(default_body))}
      self.response = MockResponse(body=cPickle.dumps(default_body))
    else:
      MockResponse.headers = dict()
      self.response = MockResponse()

  # overriding a predefined method name.
  def getresponse(self):  #pylint: disable-msg=C6409
    """Returns a MockResponse."""
    return self.response

  # overriding a predefined method name.
  def close(self):  #pylint: disable-msg=C6409
    """Pretends to close a non-existant connection."""
    pass


class DataClientTest(unittest.TestCase):
  """Test for HttpScraper."""

  def setUp(self):
    """Make sure we are using our mock objects."""
    client.HTTP_CONNECTION = MockHttpConnection
    self.data_client = client.DataClient('192.168.42.100', '50007')

  def testRecv(self):
    """Make sure that we get the right stuff back."""
    ret = self.data_client.Recv('plain')
    self.assertEqual(ret, default_body)
    ret = self.data_client.Recv('pickle')
    self.assertEqual(ret, default_body)

  def testSend(self):
    """Make sure we send the right things."""
    self.data_client.Send(default_body)
    self.assertEqual(cPickle.loads(MockHttpConnection.post_data), default_body)
#END CLASS DataClientTest


if __name__ == '__main__':
  unittest.main()
