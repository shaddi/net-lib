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

"""Provides an HTTP connection to send and receive data from a data server.

When using the provided server in netlib this client is used to send and
receive back data from the server.  The idea here is that we want to be able
to send and receive information from the server without having to write and then
parse data from strings.

The idea is to make exchanging Python data structures with a server as simple as
calling Send or Recv.

  DataClient: Custom HTTP methods able to deal with python data.

Simple usage:
  On server:
    # Create a server and provide data for clients to request.
    data_server = server.DataServer('some.host.com', 50007)
    data_server.AddData(data_for_clients, key='client_data_key')
    data_server.Start()
  On client(s):
    # Create a client and request data.
    data_client = client.DataClient('some.host.com', 50007)
    data = data_client.Recv('client_data_key')
    results = DoSomethingUseful(data)
    # Send the data back to the client.
    data_client.Send(results, 'results')
  On server:
    # Stop the server and retrieve the results.
    data_server.Stop()
    results = data_server.Results()

NOTE: this could easily have nefarious uses so please be responsible.
      Don't be evil.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import sys
import cPickle
import logging
import httplib
import socket

from netlib import config
from netlib.net import http


class DataClient(object):
  """Custom HTTP methods able to deal with python data.

  This object aims to make exchanging data with the netlib.data.server as simple
  as calling Send or Recv.

  NOTE: that currently there is not a way for servers to push data to the
  client, but that this interface could be extended to such a module and that it
  could be made backwads compatible.  It can also be that if you were to use an
  exchange format that was more flexible than piclkling python objects (JSON
  strings for example) that you could have clients or servers that were written
  in different languages.
  """

  def __init__(self, server, port=config.DATA_PORT):
    """Inits a DataServer with a server hostname/IP and a port.

    A connection to the server is not opened immediately.  This just saves the
    info that we will need to open that connection later.

    Args:
      server: the hostname or IP addess of the netlib.data.server.
      port: the port where the netlib.data.server is listening.
    """
    self.server = server
    self.port = port

  def Recv(self, key=''):
    """Pulls data from a netlib.data.server instance.

    Does an HTTP GET request to the server which should return either the data
    specifically for this host based on IP address or general data for all hosts
    based on the key.  Usually providing one or the other is sufficient, but you
    should read the documentation and source for
    netlib.data.server.DataServer.GetCallBack for mor details.

    Args:
      key: the path to use for the request.

    Returns:
      data: the value that was mapped to the key on the server.
    """
    conn = httplib.HTTPConnection(self.server, self.port)
    my_headers = {'content-type':'text/text'}
    conn.request('GET', '/%s' % key, headers=my_headers)
    resp = conn.getresponse()
    if resp.status >= 200 and resp.status <= 206:
      logging.info('%s:%d -- %d %s' % (self.server,
                                       self.port,
                                       resp.status,
                                       resp.reason))
      if resp.getheader('python-type'):
        data = cPickle.loads(resp.read())
      else:
        data = resp.read()
    else:
      logging.error('%s:%d -- %d %s' % (self.server,
                                        self.port,
                                        resp.status,
                                        resp.reason))
      data = None
    conn.close()
    return data

  def Send(self, data, key=''):
    """Sends data to a netlib.data.server instance.

    Does an HTTP POST request to the server.  It used with the
    netlib.data.server the data is stored with a server-key made up of the client IP
    address and the key/path given in the arguments.  For example:

    server-key = "%s_%s" % (client_ip, key)

    Args:
      data: any data that can be pickled using cPickle.
      key: the key to use for storing the data on the server.
    """
    head = {'content-type':'text/text'}
    head['python-type'] = str(type(data))
    conn = httplib.HTTPConnection(self.server, self.port)
    conn.request('POST', '/%s' % key, body=cPickle.dumps(data), headers=head)
    resp = conn.getresponse()
    if resp.status >= 200 and resp.status <= 206:
      logging.info('%s:%d -- %d %s -- %s' % (self.server,
                                             self.port,
                                             resp.status,
                                             resp.reason,
                                             resp.read()))
    else:
      logging.error('%s:%d -- %d %s -- %s' % (self.server,
                                              self.port,
                                              resp.status,
                                              resp.reason,
                                              resp.read()))
    conn.close()
