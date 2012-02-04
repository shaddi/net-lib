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

"""Tests for net-lib.net.http.

mock.MockHost.results are stored for places where data needs to be returned to
keep the objects under test happy.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import unittest

from net-lib.net import http


# Our test webpage.
default_body = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <title>Python Programming Language &ndash; Official Website</title>
  <script type="text/javascript" src="/js/iotbs2-core.js"></script>
</head>
<body>
  <img id="logo" src="/images/python-logo.gif" alt="homepage" border="0" />
</body>
</html>
"""

# the size of the test webpage.
sz = len(default_body)

# the right urls for our test webpage.
default_urls = [('www.python.org', '/', 'http', sz),
                ('www.python.org', '/js/iotbs2-core.js', 'http', sz),
                ('www.python.org', '/images/python-logo.gif', 'http', sz)]

# the right results for our test webpage (timing may differ).
default_results = [http.URLRecord(netloc='www.python.org',
                                  path='/images/python-logo.gif',
                                  scheme='http', size=sz, resp_time=0.3,
                                  err_time=0.009),
                   http.URLRecord(netloc='www.python.org',
                                  path='/js/iotbs2-core.js', scheme='http',
                                  size=sz, resp_time=0.4, err_time=0.002),
                   http.URLRecord(netloc='www.python.org', path='/',
                                  scheme='http', size=sz, resp_time=0.6,
                                  err_time=0.02)]


class MockResponse(object):
  """Mock object for reponse objects returned by an http connections.

  This needs to allow for reading the response and accessing the headers.
  """

  headers = {'location': 'http://www.python.org'}

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


class MockHttp(object):
  """Mock object for http connections.

  This needs to allow for making a request and getting the response.
  """

  # constructor signature needs to match.
  def __init__(self, netloc, timeout=0):  #pylint: disable-msg=W0613
    """Inits a MockHttp."""
    self.netloc = netloc

  # overriding a predefined method name.
  # constructor signature needs to match.
  def request(self, method, path,  #pylint: disable-msg=C6409,W0613
              headers=None):  #pylint: disable-msg=W0613
    """Sets up a MockResponse."""
    self.response = MockResponse()

  # overriding a predefined method name.
  def getresponse(self):  #pylint: disable-msg=C6409
    """Returns a MockResponse."""
    return self.response


class HttpScraperTest(unittest.TestCase):
  """Test for HttpScraper."""

  def setUp(self):
    """Make sure we are using our mock objects."""
    http.HTTPS_CONNECTION = MockHttp
    http.HTTP_CONNECTION = MockHttp

  def testInit(self):
    """Make sure that we are setting things up right."""
    self.scraper = http.HttpScraper('http://www.python.org')
    self.assertIsNotNone(self.scraper.files)
    self.assertIsNotNone(self.scraper.url_list)
    self.assertIsNotNone(self.scraper.netloc)
    self.assertIsNotNone(self.scraper.path)
    self.assertIsNotNone(self.scraper.scheme)

  def testGenUrlList(self):
    """Tesintg URL list generation."""
    self.scraper = http.HttpScraper('http://www.python.org')
    urls = self.scraper.GenUrlList()
    self.assertEqual(len(urls), len(default_urls))

  def testGenUrlListThreaded(self):
    """Tesintg URL list generation."""
    self.scraper = http.HttpScraper('http://www.python.org')
    urls = self.scraper.GenUrlListThreaded()
    self.assertEqual(len(urls), len(default_urls))

  def testHttpLatency(self):
    """Tesintg latency measurement."""
    result = http.HttpLatency(default_urls[0][0], default_urls[0][1])
    self.assertEqual(len(result), len(default_results[0]))

  def testThreadedLatency(self):
    """Tesintg latency measurement."""
    results = http.ThreadedLatency(default_urls, max_threads=2)
    self.assertEqual(len(results), len(default_results))
#END CLASS HttpScraperTest


if __name__ == '__main__':
  unittest.main()
