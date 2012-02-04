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

"""High level module for dealing with HTTP.

Presently this module provides an easy interface for scraping a web page for
linked files, generating a list of those files, and measuring the response time
for downloading those files using HTTP over TCP.

  URLRecord: Class to simplify working with URL data.
  HttpScraper: Class for scraping a webpage.
  HttpLatency: Method that measures the reposnse time for downloading a file.
  ThreadLatency: Allows using N threads to use HttpLatency.
  ThreadLatencyWorker: Helper method for ThreadLatency.

Simple usage:
  scraper = HttpScraper('http://www.google.com')
  urls = scraper.GenUrlList()
  results = ThreadedLatency(urls, max_threads=8)
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'


import collections
import copy
import httplib
import logging
import socket
import sys
import threading
import time
import urlparse

from net-lib import config


HTTPS_CONNECTION = httplib.HTTPSConnection
HTTP_CONNECTION = httplib.HTTPConnection


class URLRecord(collections.namedtuple('URLRecord', ['netloc', 'path', 'scheme',
                                                     'size', 'resp_time',
                                                     'err_time'])):
  """Class to simplify working with URL data.

  This works like a struct in C/C++.  See named tuple for more information.
  http://docs.python.org/library/collections.html#collections.namedtuple

  Attributes:
    netloc: Location of the resource being requested.
    path: Resource that is being requested.
    scheme: Method of download.
    size: File size in Bytes.
    resp_time: Time to download.
    err_time: Measurment error.
  """
  pass
#END CLASS URLRecord


class HttpScraper(object):
  """Class for scraping a webpage.

  Simply create a HttpScraper object by giving it a web page and it downloads
  the page and stores a list of files that are sourced by the page.  Then on
  request, the object checks all of the files in the list and changes the url
  information in the case of redirects or drops it from the list altogether if
  it 404s or worse.
  """

  def __init__(self, url, timeout=10):
    """Inits a HttpScraper with a url and an optional timeout.

    If the url is good or if it redirects to a good url then we get an object
    that has a list of (one) urls and a list of files that are on the page
    referenced by the url -- see GenUrlList for converting these files into
    something that is more accessable.

    Args:
      url: the url of the page that is to be scrapped.
      timeout: how long should the scrapper wait for a valid http connection?

    Returns:
      HttpScraper: a valid instance of the HttpScraper class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.timeout = timeout
    tmp = urlparse.urlsplit(url)
    result = self.HttpCheck(tmp.netloc, tmp.path, tmp.scheme)
    self.files = list()
    self.url_list = list()
    if result:
      self.url_list.append(result)
      self.netloc = result[0]
      self.path = result[1]
      self.scheme = result[2]
      if self.scheme == 'https':
        conn = HTTPS_CONNECTION(self.netloc, timeout=self.timeout)
      else:
        conn = HTTP_CONNECTION(self.netloc, timeout=self.timeout)
      conn.request('GET', self.path, headers=config.header_list)
      resp = conn.getresponse()
      if resp.status >= 200 and resp.status <= 206:
        logging.info('%d %s -- %s://%s%s', resp.status,
                     resp.reason, self.scheme, self.netloc, self.path)
      elif resp.status >= 300 and resp.status <= 307:
        logging.warn('%d %s -- %s://%s%s', resp.status,
                     resp.reason, self.scheme, self.netloc, self.path)
      else:
        # resp.status >= 400 and resp.status <= 417 --> not found etc.
        # resp.status >= 500 and resp.status <= 505 --> server error.
        logging.error('%d %s -- %s://%s%s', resp.status,
                      resp.reason, self.scheme, self.netloc, self.path)
      page = resp.read()
      tokens = page.split()
      # Note: the need to handle sloppy html...
      self.files = [x.split('"')[1] for x in tokens if (x.startswith('src="') or
                                                        x.startswith('SRC="') or
                                                        x.startswith('Src="'))]

  def GenUrlList(self, host=None, prefix=None):
    """Convert the file_list to more handy url entries in url_list.

    Usually when this is invoked there will be one entry in the url_list for the
    home page, and a list of files that are linked to the home page.  For each
    of those files we run HttpCheck on it and place the returned url entry in
    the url_list.

    On hosts and prefixes: note that a prefix does not make sense without a
    host.  If you want to scrape a page with wget and place the whole directory
    on another server with http://<host>/<prefix>/<origional url> then these are
    for you!

    Note that if you don't need to specify a host or prefix then you should
    probably make good use of GenUrlListThreaded.

    Args:
      host: place to put a page scraped with wget.
      prefix: parent path for a page scraped with wget.

    Returns:
      url_list: a reference to the urls pointing to the list of files.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    for f in self.files:
      if f:
        tmp = urlparse.urlsplit(f)
      else:
        continue
      if host:
        if prefix:
          result = self.HttpCheck(host, '/%s/%s/%s' % (prefix, tmp.netloc,
                                                       tmp.path))
        else:
          result = self.HttpCheck(host, '%s/%s' % (tmp.netloc, tmp.path))
      else:
        # TODO(gavaletz): find a better way to ban tlds
        if not tmp.netloc in config.BANNED_NETLOCS:
          result = self.HttpCheck(tmp.netloc, tmp.path, tmp.scheme)
        else:
          result = None
      if result:
        self.url_list.append(result)
    return self.url_list

  def GenUrlListThreaded(self, max_threads=1):
    """Faster way to convert the file_list to url entries in url_list.

    Assumes that the objects will be downloaded from their native host, and
    therefore no prefix is needed.  On pages that have lots of objects, this
    method checks them max_threads at a time until they have all been checked.

    Args:
      max_threads: how many objects to check at once.

    Returns:
      url_list: a reference to the urls pointing to the list of files.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    main_thread = threading.currentThread()
    logging.info('fetching %d urls %d at a time', len(self.files), max_threads)
    files = copy.copy(self.files)
    while files:
      ended = (max_threads + 1) - len(threading.enumerate())
      if ended:
        logging.debug('Starting %d HTTP threads', ended)
        for i in range(ended):
          t = threading.Thread(target=self.__GenUrlListThreadedWorker,
                               args=(files,))
          t.start()
          logging.debug('Starting %d of %d HTTP threads', i, ended)
      time.sleep(0.1)
    for t in threading.enumerate():
      if t is not main_thread:
        t.join()
    logging.info('built %d urls', len(self.url_list))
    return self.url_list

  def __GenUrlListThreadedWorker(self, files):
    """Method spawned by GenUrlListThreaded.

    First makes sure that there are files left to be processed since the list
    could have been depleted between the time this method was called and when it
    starts doing some work.  Make sure that the location is not in a banned
    domain.  Then do a HttpCheck on the location.

    Args:
      files: a list of files (must be thread safe).

    Raises:
      IndexError: handled here because of shared access to files.
      No new exceptions generated here.
    """
    if files:
      try:
        tmp = urlparse.urlsplit(files.pop())
        if not tmp.netloc in config.BANNED_NETLOCS:
          result = self.HttpCheck(tmp.netloc, tmp.path, tmp.scheme)
          if result:
            self.url_list.append(result)
      except IndexError:
        return

  def HttpCheck(self, host, resource, scheme='http'):
    """Method to get rid of redirects, 400's and possibly avoid some 500's.

    If a specific scheme is not specified then a global scheme is used, and the
    same is done for the netloc (host).  Makes sure that the resource string is
    up to par and then tries to get the HEAD (does not download the whole
    object).  In the case of 200 level responses the origional url is kept, but
    in the case of a 300 the new url entry is returned.  In the case of a 400,
    500 or exception then None is returned and the file should be excluded from
    future work.

    Args:
      host: the server FQDN or IP address.
      resource: what should be retrieved from the server.
      scheme: what protocol should be used to retrieve it (http or https).

    Returns:
      url_list tuple: (netloc, resource, scheme, size)

    Raises:
      all lower exceptions caught here -- Generally bad to do, but because we
      are depending on unreliable 3rd party resources we don't want to throw
      everything away on an error.  Just don't use this point of data.
      No new exceptions generated here.
    """
    if not host:
      host = self.netloc
    if not scheme:
      scheme = self.scheme
    if not resource.startswith('/'):
      resource = '/%s' % resource
    try:
      if scheme == 'https':
        conn = HTTPS_CONNECTION(host)
      else:
        conn = HTTP_CONNECTION(host)
      conn.request('HEAD', resource)
      resp = conn.getresponse()
    # Failure is not an option.  See docstring for details.
    except:  #pylint: disable-msg=W0702
      logging.error('EXCEPTION %s on %s://%s%s', sys.exc_info()[0], scheme,
                    host, resource)
      return
    if resp.status >= 200 and resp.status <= 206:
      return (host, resource, scheme, resp.getheader('content-length'))
    elif resp.status >= 300 and resp.status <= 307:
      logging.warn('%d %s -- http://%s%s', resp.status,
                   resp.reason, host, resource)
      tmp = urlparse.urlsplit(resp.getheader('location'))
      return (tmp.netloc, tmp.path, tmp.scheme,
              resp.getheader('content-length'))
    else:
      # resp.status >= 400 and resp.status <= 417 --> not found etc.
      # resp.status >= 500 and resp.status <= 505 --> server error.
      logging.error('%d %s -- http://%s%s', resp.status,
                    resp.reason, host, resource)


# TODO(gavaletz): incorperate the statuses here
# http://www.google.com/support/webmasters/bin/answer.py?hl=en&answer=40132
def HttpLatency(host, resource, scheme='http', method='GET', to=10):
  """Method that measures the reposnse time for downloading a file.

  A timer is started for both wall-time and cpu-time, and then we set up a
  connection to the http server and then request the file.  On reading the file
  the timers are stopped.  Since this is an IO bound operation the wall-time is
  the amount of time that was required to download the file (response time) and
  the cpu-time is the amount of overhead where python was running (error).

  Args:
    host: the server FQDN or IP address.
    resource: what should be retrieved from the server.
    scheme: what protocol should be used to retrieve it (http or https).
    method: one of GET, POST, or HEAD.
    to: how long should we wait for a connection before timing out?

  Returns:
    URLRecord: see the URLRecord class for a more complete description.

  Raises:
    all lower exceptions caught here -- Generally bad to do, but because we
    are depending on unreliable 3rd party resources we don't want to throw
    everything away on an error.  Just don't use this point of data.
    No new exceptions generated here.
  """
  start_cpu = time.clock()
  start_wall = time.time()
  try:
    if scheme == 'https':
      conn = HTTPS_CONNECTION(host, timeout=to)
    else:
      conn = HTTP_CONNECTION(host, timeout=to)
    conn.request(method, resource, headers=config.header_list)
    resp = conn.getresponse()
    data = resp.read()
  except socket.timeout:
    logging.warn('PYTHON TIMEOUT -- http://%s%s', host, resource)
    return False
  except:
    logging.error('EXCEPTION %s on http://%s%s', sys.exc_info()[0],
                  host, resource)
    return False
  end_wall = time.time()
  end_cpu = time.clock()
  # The content-length is the same as the binary file size, and the same as the
  # length.  This works even with large amounts of unicode.  Checked with
  # os.path.getsize("tmp") and resp.getheader('content-length')
  sz_data = len(data)
  if resp.status >= 200 and resp.status <= 206:
    return URLRecord(host, resource, scheme, sz_data, end_wall - start_wall,
                     end_cpu - start_cpu)
  elif resp.status >= 300 and resp.status <= 307:
    logging.warn('%d %s -- http://%s%s', resp.status,
                 resp.reason, host, resource)
    return URLRecord(host, resource, scheme, sz_data, end_wall - start_wall,
                     end_cpu - start_cpu)
  else:
    # resp.status >= 400 and resp.status <= 417 --> not found etc.
    # resp.status >= 500 and resp.status <= 505 --> server error.
    logging.error('%d %s -- http://%s%s', resp.status,
                  resp.reason, host, resource)
    return False


# private method used to enable threaded latency checks.
def __ThreadLatencyWorker(url_list, results):  #pylint: disable-msg=C6409
  """Helper method for ThreadLatency.

  This method looks to see if these is work to be done, and if so tries to grab
  a url to check.  It is always possible that the url if finds will be gone when
  it tries to use it (hence the try catch) so we have to be careful of race
  conditions.

  For more info: http://docs.python.org/library/threading.html

  Args:
    url_list: a reference to the urls pointing to the list of files.
    results: a shared list (threadsafe) to place URLRecods in.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  if url_list:
    try:
      url = url_list.pop()
      results.append(HttpLatency(url[0], url[1], url[2]))
    # This is going to happen to all of the threads that are started and end up
    # not having any data to act on.  They will die quickly and there are no bad
    # side effects.
    except IndexError:
      return


def ThreadedLatency(url_list, max_threads=1):
  """Allows using N threads to use HttpLatency.

  A much more efficeint way to get latency results.  This method uses N threads
  to download things in parallel.  This is closer to the behavior of most client
  applications on the Internet today.  It is good to keep N reasonable in
  practice we have found that N should be around 8 for the best results.

  Args:
    url_list: a reference to the urls pointing to the list of files.
    max_threads: the maximum number of threads that should be spawned.

  Returns:
    list <URLRecord>: see the URLRecord class for a more complete description.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  main_thread = threading.currentThread()
  logging.info('fetching %d urls %d at a time', len(url_list), max_threads)
  results = list()
  while url_list:
    ended = (max_threads + 1) - len(threading.enumerate())
    if ended:
      logging.debug('Starting %d HTTP threads', ended)
      for i in range(ended):
        t = threading.Thread(target=__ThreadLatencyWorker, args=(url_list,
                                                                 results))
        t.start()
        logging.debug('Starting %d of %d HTTP threads', i, ended)
    time.sleep(0.1)
  for t in threading.enumerate():
    if t is not main_thread:
      t.join()
  logging.info('returning %d results', len(results))
  return results
