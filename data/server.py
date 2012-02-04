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

"""Provides an HTTP connection to send and receive data from clients.

When using the provided clients in net-lib this server is used to send and
receive back data from the clients.  The idea here is that we want to be able
to send and receive information from clients without having to write and then
read files from Disk.  We were motivated by the following example.

Given a list of URLs scrape those pages and generate a list of URLs referring to
all the embedded objects in those pages.  We then want to have N clients running
on other machines each get copies of that list, time how long it takes them to
download the items and then return back results.  Then we need to gather those
results from the server.

This server must also be easy to launch in a separate process or thread so that
it can be a step in a larger experiment.  If all of this seems complicated it
is, but we are encapsulating that complexity here to make it relatively simple
to use this in a script.

  DataHandler: Custom HTTP handlers able to deal with python data.
  DataServer: Custom HTTP server that sends and receives from memory.

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

import BaseHTTPServer
import cPickle
import logging
import multiprocessing
import socket
import sys

from net-lib import config
from net-lib.data import client
from net-lib.net import http


class DataHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """Custom HTTP handlers able to deal with python data.

  This class extends the base request handler and allows us to do something
  unique on GET and POST requests.  Here we are able to call a custom call back
  function for each and work with sending python data structures over HTTP.

  For an example of how to best use the DataHandler request handler see the
  DataServer class.
  """

  @staticmethod
  def GetCallback(DataHandler,  #pylint: disable-msg=C6409,W0621
                  address, path):
    """Allows doing dynamic things for requests.

    See DataServer.__init__ for details.

    Args:
      DataHandler: Instance reference passed when calling from an Instance.
      address: The client's IP address.
      path: The path portion of the request.

    Raises:
      NotImplementedError: because this needs to be over written.
    """
    raise NotImplementedError

  @staticmethod
  def PostCallback(DataHandler,  #pylint: disable-msg=C6409,W0621
                   address, path, data):
    """Allows doing dynamic things for posts.

    See DataServer.__init__ for details.

    Args:
      DataHandler: Instance reference passed when calling from an Instance.
      address: The client's IP address.
      path: The path portion of the request.
      data: The value that is to be stored from the client.

    Raises:
      NotImplementedError: because this needs to be over written.
    """
    raise NotImplementedError

  # name is required by parent class.
  def do_GET(self):  #pylint: disable-msg=C6409
    """Called when the request is an HTTP GET.

    Passes the request to the custom call back which provides the data to be
    returned.  Since the data is probably a python data structure we want to
    preserve that by pickling it and sending the pickle string.
    """
    data = DataHandler.GetCallback(self, self.client_address[0], self.path[1:])
    if not data is None:
      logging.info('%s%s', self.client_address[0], self.path)
      self.send_response(200)
      self.send_header('content-type', 'text/text')
      self.send_header('python-type', str(type(data)))
      self.end_headers()
      self.wfile.write(cPickle.dumps(data))
    else:
      logging.error('%s%s', self.client_address[0], self.path)
      self.send_error(404, self.path)

  # name is required by parent class.
  def do_POST(self):  #pylint: disable-msg=C6409
    """Called when the request is an HTTP POST.

    This is the opposite end of the do_GET in that we check to see if the
    python-type header is set and if it is we treat that as data to be
    unpickled.  Since that data needs to be acted on and possibly stored
    somewhere we make use of the custom POST call back.
    """
    length = int(self.headers.getheader('content-length'))
    if self.headers.getheader('content-type') == 'text/text':
      if 'python-type' in self.headers:
        data = cPickle.loads(self.rfile.read(length))
      else:
        data = self.rfile.read(length)
    else:
      data = ''
    response = DataHandler.PostCallback(self, self.client_address[0],
                                        self.path[1:], data)
    if not response is None:
      logging.info('%s%s', self.client_address[0], self.path)
      self.send_response(200)
      self.send_header('content-type', 'text/text')
      self.end_headers()
      self.wfile.write(response)
    else:
      logging.error('%s%s', self.client_address[0], self.path)
      self.send_error(404, self.path)


class DataServer(object):
  """Custom HTTP server that sends and receives from memory.

  This HTTP server allows us to specify custom  methods to be called for every
  HTTP GET or POST request.  All posts are stored in a dictionary for later
  retrieval, and data to be returned to the clients is kept in one of two data
  structures depending on the way the data is to be distributed.

  Attributes:
    ip_cache: A cache of hostname to IP addresses.
    data_recv: Storage for incoming data.
    ip_data_store: Items to be returned to a specific IP address.
    all_data_store: Items that should be returned to any IP address.
    GET_ALL_DATA: A unique key that keeps us from dumping the data by mistake.
    keep_running:
  """

  ip_cache = dict()
  data_recv = dict()
  ip_data_store = dict()
  all_data_store = dict()
  GET_ALL_DATA = '9e5bb17c123c0cda16cd16e742a55c72'
  keep_running = False

  @staticmethod
  def GetCallback(DataHandler,  #pylint: disable-msg=W0613,C6409,W0621
                  address, path):
    """Returns the right data for a client based on IP or path.

    There is an order of precedence for client address and path.  If a path is
    given and that path is in the DataServer.all_data_store it will be returned.
    If there is not path or that path is not in the DataServer.all_data_store
    then the DataServer.ip_data_store is checked for the client's IP address and
    if a match is found there then that data is returned.  Otherwise None is
    returned most likely resulting in a 404 for the client.

    Args:
      DataHandler: Instance reference passed when calling from an Instance.
      address: The client's IP address.
      path: The path portion of the request.

    Returns:
      data to be returned to the client.
    """
    if path == DataServer.GET_ALL_DATA:
      return DataServer.data_recv
    if path in DataServer.all_data_store:
      return DataServer.all_data_store[path]
    elif address in DataServer.ip_data_store:
      return DataServer.ip_data_store[address]
    else:
      return None

  @staticmethod
  def PostCallback(DataHandler,  #pylint: disable-msg=W0613,C6409,W0621
                   address, path, data):
    """Stores the data from a client based on IP and path.

    A key is generated from the client's IP address and the supplied path from
    the HTTP POST request.  The value supplied in data is then stored in the
    DataServer.data_recv dictionary with the generated key.  The length of the
    data stored and the generated key is returned to the client as confirmation
    of the transaction.

    Args:
      DataHandler: Instance reference passed when calling from an Instance.
      address: The client's IP address.
      path: The path portion of the request.
      data: The value that is to be stored from the client.

    Returns:
      string: the length of the data stored and the key it was stored under.
    """
    if path == DataServer.GET_ALL_DATA:
      logging.error('Please use GET for getAllDataRecv.')
      return None
    else:
      key = '%s_%s' % (path, address)
      DataServer.data_recv[key] = data
      return '%s = %d Bytes' % (key, len(data))

  def __init__(self, host, port):
    """Inits a DataServer with a host and a port.

    Created an HTTPServer with our custom DataHandler.  Since the DataHandler
    objects are created on a per-request basis, and rewriting the DataHandler
    __init__ function would require modification to parts of the Python std lib
    we are instead specifying our call back functions as static functions that
    will be in place for every instance of our handler.

    Args:
      host: the host interface to listen on.
      port: the port number to listen on.
    """
    self.host = host
    self.port = port
    self.httpserver = BaseHTTPServer.HTTPServer((host, port), DataHandler)
    self.httpserver.RequestHandlerClass.GetCallback = DataServer.GetCallback
    self.httpserver.RequestHandlerClass.PostCallback = DataServer.PostCallback
    self.server = None

  def __del__(self):
    """Allows a DataServer to be deleted gracefuly."""
    self.Stop()

  def __Start(self):
    """Helper function to start the server.

    Will keep handling requests as long as keep_running is true.  This allows
    us to stop the server in a nice way.
    """
    while self.keep_running:
      self.httpserver.handle_request()

  def Start(self):
    """Starts the server.

    Since we will be starting the server in another process, we use the _Start
    helper method.  The server will serve requests as long as keep_running is
    True.
    """
    logging.info('%s listening on port %d', self.host, self.port)
    self.keep_running = True
    self.server = multiprocessing.Process(target=self.__Start)
    self.server.start()

  def Stop(self):
    """Stops a server.

    If the server is running the keep_running is set to False and a final
    request for all the data that was collected is given.  The data is retrieved
    in this manner because it simplifies dealing with multiprocess shared
    memory data structures.
    """
    if not self.server is None:
      self.keep_running = False
      tmp_client = client.DataClient(config.LOCAL_LOOPBACK, self.port)
      recv_data = tmp_client.Recv(DataServer.GET_ALL_DATA)
      self.server.join(timeout=1)
      if self.server.is_alive():
        self.server.terminate()
      self.server = None
      for key in recv_data:
        DataServer.data_recv[key] = recv_data[key]

  def Restart(self):
    """Restarts the server.

    See DataServer.Stop and DataServer.Start for details.
    """
    if not self.server is None:
      self.Stop()
    self.Start()

  def AddData(self, value, hostname=None, key=None):
    """Adds data to the server.

    Data should only be added to a stopped server since it needs to be shared in
    memory.  If the server is already running they will be stopped, and then
    restarted once the data has been added to the static data structure.  Data
    can be stored by hostname and thus will be available only to that host, OR
    by path and available to any host that specifies that path.

    Args:
      value: the value to be stored.
      hostname: specified if the value is only to be returned for a given host.
      key: the path to be returned to request this data for any host.
    """
    if not self.server is None:
      self.Stop()
      restart = True
    else:
      restart = False
    if not key is None:
      assert not hostname
      DataServer.all_data_store[key] = value
    elif not hostname is None:
      assert not key
      if not hostname in DataServer.ip_cache:
        DataServer.ip_cache[hostname] = socket.gethostbyname(hostname)
      DataServer.ip_data_store[DataServer.ip_cache[hostname]] = value
    else:
      logging.error('AddData only supports key OR hostname at this time.')
    if restart:
      self.Start()

  def Results(self):
    """Returns the results that were posted to the server.

    This should only be called on a stopped server as calling it on a running
    server will most likely yield incomplete results.

    Returns:
      DataServer.data_recv: a dictionary mapping of IP addresses and path to
      values that were posted from that IP address.
    """
    if not self.server is None:
      logging.warn('Grabbing results from a running server is risky...')
    return DataServer.data_recv
