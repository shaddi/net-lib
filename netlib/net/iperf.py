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

"""One-line documentation for iperf module.

This module provides a clean interface from Python to iperf.  With a little
planning this can be used to generate a blocking call to generate a quick TCP
connection or a whole mess of traffic generators firing off at once to provide
lots of traffic.

  IperfServer: Class to simplify starting a remote iperf server.
  IperfClient: Class to simplify starting a remote iperf client.
  IperfSet: Class to start a set of iperf clients and a server.
  IperfTCP: IperfSet configured for TCP.
  IperfUDP: IperfSet configured for UDP.

Keep in mind that with iperf traffic flows from the client to the server.  So
your traffic sources (clients) are going to be sending packets to your
destinations (servers).

Simple UDP usage:
  IperfUDP(target_src, target_dst, dst, 1, rate='10M')

Simple TCP usage:
  IperfTCP(target_src, target_dst, dst, 1, window=256)

Simple Set usage:
  target_src_list = ['a.remote_host.com', 'b.remote_host.com']
  target_dst_list = ['c.remote_host.com', 'd.remote_host.com']
  dst_list = target_dst_list
  ips = IperfSet(target_src_list, target_dst_list, dst_list)
  ips.Start(length=5)
  ips.Results()
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import logging
import time

from netlib import config
from netlib.shell import bash


class IperfServer(object):
  """Class to simplify starting a remote iperf server.

  This class provides a service like interface for using iperf from within a
  Python script.

  Attributes:
    WAIT_TIME: how long to pause to allow the server to get going.
    KILL_STRING: shell command for killing iperf processes.
    pkt: size of packets to use in Bytes.
    interval: how long to wait between bandwidth reports in seconds.
  """

  WAIT_TIME = config.WAIT_TIME
  KILL_STRING = 'killall -q -r \".*iperf*\"'
  pkt = None
  interval = None

  def __init__(self, target):
    """Inits IperfServer with a target Host.

    After determining if we are being passed a string to turn into a Host
    object, or if we are getting a reference to an existing Host object we
    simply store that for later and create the instance variables for storing
    stuff later.

    Args:
      target: The host machine where the iperf server will run.

    Returns:
      IperfServer: an instance of the IperfServer class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if isinstance(target, bash.Host):
      self.host = target
    else:
      self.host = bash.Host(target)
    self.args = ['-s']
    self.data = None
    self.child_pid = None

  def __del__(self):
    """Tries to make sure that we clean up after ourselves.

    We don't want to leave processes running on systems for no good reason when
    we are done.  So try to kill them off just before this is killed off.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.host.Kill(self.child_pid, IperfServer.KILL_STRING)

  def Start(self, udp=False):
    """Start a iperf server.

    Assembles the command to be used for starting an iperf server on the system
    and uses the host object to fork off a process to begin that call.  Not
    running in UDP mode implies running in TCP mode.

    Args:
      udp: should the server run in UDP mode.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if not self.data is None:
      logging.warn('%s -- overwriting data', self.host.host)

    if udp:
      self.args.append('-u')
    if IperfServer.pkt:
      self.args.append('-M %s' % IperfServer.pkt)
    if IperfServer.interval:
      self.args.append('-i %s' % IperfServer.interval)

    cmd = 'iperf %s' % (' '.join(self.args))

    if not self.child_pid:
      self.child_pid = self.host.Run(cmd, echo_error=True, fork=True)
      time.sleep(IperfServer.WAIT_TIME)

  def Stop(self):
    """Stops the iperf server process.

    Uses the host object to stop the iperf server.  If necessary it will use the
    iperf kill string to send a SIGKILL singal.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.data = self.host.Communicate(self.child_pid, echo_error=True,
                                        kill=True,
                                        kill_string=IperfServer.KILL_STRING)
      self.child_pid = None

  def Restart(self, udp=False):
    """Convenience method for stopping and starting an IperfServer instance.

    Args:
      udp: should the server run in UDP mode.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.Stop()
    self.Start(udp)

  def Results(self):
    """Returns the IperfServer output.

    In the future this will return pre-processed results, but since we are not
    using this output then this will do for now.

    Returns:
      data: string of iperf output.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    return self.data
#END CLASS IperfServer


class IperfClient(object):
  """Class to simplify starting a remote iperf client.

  This class provides a service like interface for using iperf from within a
  Python script.

  Attributes:
    KILL_STRING: shell command for killing iperf processes.
    pkt: size of packets to use in Bytes.
    interval: how long to wait between bandwidth reports in seconds.
  """

  KILL_STRING = 'killall -q -r \".*iperf*\"'
  pkt = None
  interval = None

  def __init__(self, target, dst):
    """Inits IperfClient with a target Host.

    After determining if we are being passed a string to turn into a Host
    object, or if we are getting a reference to an existing Host object we
    simply store that for later and create the instance variables for storing
    stuff later.

    Args:
      target: The host machine where the iperf client will run.
      dst: The host machine address where the client should connect.

    Returns:
      IperfClient: an instance of the IperfClient class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if isinstance(target, bash.Host):
      self.host = target
    else:
      self.host = bash.Host(target)
    self.args = ['-c %s' % dst]
    self.data = None
    self.length = None
    self.child_pid = None

  def __del__(self):
    """Tries to make sure that we clean up after ourselves.

    We don't want to leave processes running on systems for no good reason when
    we are done.  So try to kill them off just before this is killed off.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.host.Kill(self.child_pid, IperfClient.KILL_STRING)

  def Start(self, length=None, rate=None, window=None, blocking_call=False):
    """Start a iperf client.

    Assembles the command to be used for starting an iperf client on the system
    and uses the host object to fork off a process to begin that call.  Using a
    rate implies UDP operation, window implies TCP operation, neither implies
    TCP operation and both is an error.

    If a length is provided then you can choose to use this as a blocking call
    or the call can return immediately.  If length is not provided then this
    call will fork a new process and then you will need to call Stop() to end
    it.

    Args:
      length: If set only generte traffic for this many seconds.
      rate: If set use UDP with a rate i.e. 10M 100K 1G.
      window: If set use TCP with a window size in Bytes.
      blocking_call: should we wait for the iperf client to finish?

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if not self.data is None:
      logging.warn('%s -- overwriting data', self.host.host)

    self.length = length
    if length:
      self.args.append('-t %d' % length)
    if IperfClient.pkt:
      self.args.append('-M %s' % IperfClient.pkt)
    if IperfClient.interval:
      self.args.append('-i %s' % IperfClient.interval)

    if rate and not window:
      self.args.append('-b %s' % rate)
      cmd = 'iperf -u %s' % (' '.join(self.args))
    elif window and not rate:
      self.args.append('-w %s' % window)
      cmd = 'iperf %s' % (' '.join(self.args))
    else:
      assert not window
      assert not rate
      cmd = 'iperf %s' % (' '.join(self.args))

    if not self.child_pid:
      if length and blocking_call:
        self.data = self.host.Run(cmd, echo_error=True, fork=False)
        self.child_pid = None
      else:
        self.child_pid = self.host.Run(cmd, echo_error=True, fork=True)

  def Stop(self):
    """Stops the iperf client process.

    Uses the host object to stop the iperf client.  If necessary it will use the
    iperf kill string to send a SIGKILL singal.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.data = self.host.Communicate(self.child_pid, echo_error=True,
                                        kill=(not self.length),
                                        kill_string=IperfClient.KILL_STRING)
      self.child_pid = None

  def Restart(self, length=None, rate=None, window=None, blocking_call=False):
    """Convenience method for stopping and starting an IperfClient instance.

    Args:
      length: If set only generte traffic for this many seconds.
      rate: If set use UDP with a rate in Mbps.
      window: If set use TCP with a window size in Bytes.
      blocking_call: should we wait for the iperf client to finish?

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.Stop()
    self.Start(length, rate, window, blocking_call)

  def Results(self):
    """Returns the IperfClient output.

    In the future this will return pre-processed results, but since we are not
    using this output then this will do for now.

    Returns:
      data: string of iperf output.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    return self.data
#END CLASS IperfClient


# TODO(gavaletz): class IperfResults(object):


class IperfSet(object):
  """Class to simplify starting a set of remote iperf clients and servers.

  This class provides a service like interface for using iperf from within a
  Python script.  You can create an IperfSet with:

  - a single source and a single target destination and destination
  - a list of sources and single target destination and destination
  - a list of sources and list of target destinations and destinations
  - a list of sources and list of target destinations and a single destination

  There is some complexity in starting a large set of clients and servers and
  stopping them.  This is especially complex when they may need to start as
  forked processes and then you need to wait on them all to finish before
  proceeding.
  """

  def __init__(self, target_src, target_dst, dst):
    """Inits an IperfSet.

    If you use a list for dst then you must use a list of equal length for
    target_dst.

    Args:
      target_src: A single host or list of hosts.
      target_dst: A single host or list of hosts (1:1 with target_src).
      dst: A single address/hostname or a list (1:1 with target_dst)

    Returns:
      IperfSet: an instance of the IperfSet class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.client_list = list()
    self.server_list = list()
    if isinstance(target_src, list):
      if isinstance(dst, list):
        assert len(target_src) == len(dst)
        for i in range(0, len(dst)):
          self.client_list.append(IperfClient(target_src[i], dst[i]))
      else:
        for src in target_src:
          self.client_list.append(IperfClient(src, dst))
      if isinstance(target_dst, list):
        assert isinstance(dst, list)
        assert len(target_src) == len(target_dst)
        assert len(target_src) == len(dst)
        for dst in target_dst:
          self.server_list.append(IperfServer(dst))
      else:
        self.server_list.append(IperfServer(target_dst))
    else:
      assert not isinstance(target_dst, list)
      assert not isinstance(dst, list)
      self.client_list.append(IperfClient(target_src, dst))
      self.server_list.append(IperfServer(target_dst))

  def __del__(self):
    """Tries to make sure that we clean up after ourselves.

    We don't want to leave processes running on systems for no good reason when
    we are done.  So try to kill them off just before this is killed off.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    for client in self.client_list:
      del client
    for server in self.server_list:
      del server

  def Start(self, length=None, rate=None, window=None, blocking_call=True):
    """Starts the set of iperf client(s) and server(s).

    See IperfClient.Start() for more details.  The blocking_call argument is
    slightly different here in that it is not passed directly to the underlying
    IperfClient objects (that would limit us to starting only one) but they are
    all started and then this call will block until they are all finished.

    Args:
      length: If set only generte traffic for this many seconds.
      rate: If set use UDP with a rate in Mbps.
      window: If set use TCP with a window size in Bytes.
      blocking_call: should we wait for all the iperf clients to finish?

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if rate and not window:
      udp = True
    elif window and not rate:
      udp = False
    else:
      udp = False

    for server in self.server_list:
      server.Start(udp)
    for client in self.client_list:
      client.Start(length, rate, window, blocking_call=False)

    if length and blocking_call:
      self.Stop(wait_for_client=True)

  def Stop(self, wait_for_client=False):
    """Stops the set of iperf client(s) and server(s).

    See IperfClient.Stop() for more details.  This method can make sure that we
    do not end an iperf client object prematurely by waiting for all of the
    clients to finish transmission.

    Args:
      wait_for_client: Should we wait for clients to finish first?

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if wait_for_client:
      status = False
      while not status:
        status = True
        for client in self.client_list:
          status = status and client.host.Poll(client.child_pid)
    for client in self.client_list:
      client.Stop()
    for server in self.server_list:
      server.Stop()

  def Restart(self, length=None, rate=None, window=None):
    """Convenience method for stopping and starting an IperfSet instance.

    Args:
      length: If set only generte traffic for this many seconds.
      rate: If set use UDP with a rate in Mbps.
      window: If set use TCP with a window size in Bytes.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.Stop()
    self.Start(length, rate, window)

  def Results(self):
    """Returns the IperfSet output.

    In the future this will return pre-processed results, but since we are not
    using this output then this will do for now.

    Returns:
      tuple:
        server_data_list: list of strings of iperf server output.
        client_data_list: list of strings of iperf client output.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    client_data_list = list()
    for client in self.client_list:
      client_data_list.append(client.data)
    server_data_list = list()
    for server in self.server_list:
      server_data_list.append(server.data)
    return (server_data_list, client_data_list)
#END CLASS IperfSet


def IperfTCP(target_src, target_dst, dst, length, window=None):
  """Convenience method for starting a TCP IperfSet.

  See IperfSet for more details.

  Args:
    target_src: A single host or list of hosts.
    target_dst: A single host or list of hosts (1:1 with target_src).
    dst: A single address/hostname or a list (1:1 with target_dst).
    length: Only generte traffic for this many seconds.
    window: If set use TCP with a window size in Bytes.

  Returns:
    tuple:
      server_data_list: list of strings of iperf server output.
      client_data_list: list of strings of iperf client output.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  iperf = IperfSet(target_src, target_dst, dst)
  iperf.Start(length, None, window)
  return iperf.Results()


def IperfUDP(target_src, target_dst, dst, length, rate='100M'):
  """Convenience method for starting a UDP IperfSet.

  See IperfSet for more details.

  Args:
    target_src: A single host or list of hosts.
    target_dst: A single host or list of hosts (1:1 with target_src).
    dst: A single address/hostname or a list (1:1 with target_dst).
    length: Only generte traffic for this many seconds.
    rate: If set use UDP with a rate in Mbps.

  Returns:
    tuple:
      server_data_list: list of strings of iperf server output.
      client_data_list: list of strings of iperf client output.

  Raises:
    No exceptions handled here.
    No new exceptions generated here.
  """
  iperf = IperfSet(target_src, target_dst, dst)
  iperf.Start(length, rate, None)
  return iperf.Results()
