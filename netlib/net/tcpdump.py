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

"""Provides a Python interface to tcpdump.

This module provides a clean interface from Python to tcpdump.  The TCPDump
object can be started where it will fork off another process.  Then you can stop
that process and retrieve the results.

  TCPDump: Class to simplify getting remote tcpdump results.
  TCPDumpRecord: Named tuple to make sure our records stay together.
  TCPDumpResults: Class to parse tcpdump output and perform basic analysis.

Simple object usage:
  tcp_d = TCPDump('a.remote_host.com')
  tcp_d.Start(interface='eth0', count=None)
  # do traffic generating stuff...
  tcp_d.Stop()
  results = tcp_d.Results()
  thr_x, thr_y = results.Throughput(step=0.25)
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'


import collections
import logging


from netlib import config
from netlib.shell import bash


class TCPDump(object):
  """Class to simplify getting remote tcpdump results.

  This class provides a service like interface for using tcpdump from within a
  Python script.  All arguments (other than the host where it will be run) is
  supplied when the trace is started and stored in one of two args dictionaries.

  Attributes:
    WAIT_TIME: how long to wait before reading dump file.
    BIN: the binary to run on the system(s).
    KILL_STRING: shell command for killing tcpdump processes.
    SNAPLEN: the number of bytes to sample from each packet.
  """

  WAIT_TIME = config.WAIT_TIME
  BIN = 'sudo tcpdump'
  KILL_STRING = 'sudo killall -q -r \".*tcpdump*\"'
  SNAPLEN = 96  # default=96, units=Bytes
  # The following is useful but only in tcpdump v 4.0.0 or higher
  #BUFFER_SIZE = 100000 # default=1000, units=KiloBytes

  def __init__(self, target):
    """Inits TCPDump with a target Host.

    After determining if we are being passed a string to turn into a Host
    object, or if we are getting a reference to an existing Host object we
    simply store that for later and create the instance variables for storing
    stuff later.

    Args:
      target: The host machine where tcpdump will collect traffic.

    Returns:
      TCPDump: an instance of the TCPDump class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if isinstance(target, bash.Host):
      self.host = target
    else:
      self.host = bash.Host(target)
    self.capture_args = list()
    self.read_args = list()
    self.data = None
    self.count = None
    self.child_pid = None
    self.tmp_file = self.host.Run('mktemp -t tcpdump.dat.XXXXXXXXXX',
                                  echo_error=True, fork=False).strip()

  def __del__(self):
    """Tries to make sure that we clean up after ourselves.

    We don't want to leave processes running on systems for no good reason when
    we are done.  So try to kill them off just before this is killed off.  We
    should also make an attempt to clean up our tmp file.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.host.Kill(self.child_pid, TCPDump.KILL_STRING)
    self.host.Run('rm %s' % self.tmp_file, echo_error=True, fork=False)

  def Start(self, src=None, dst=None, interface=config.DEFAULT_INTERFACE,
            count=config.TCPDUMP_COUNT):
    """Starts collecting traces using tcpdump.

    Assembles the command to be used for starting tcpdump on the system and
    forks off a process to begin that call.

    Args:
      src: fliter by this ip/hostname as the source address.
      dst: fliter by this ip/hostname as the destination address.
      interface: listen on this interface.
      count: record this many packets (None -> Inf.).

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """

    assert interface
    assert self.tmp_file
    assert TCPDump.SNAPLEN
    self.capture_args.append('-i %s' % interface)
    self.capture_args.append('-w %s' % self.tmp_file)
    self.capture_args.append('-s %d' % TCPDump.SNAPLEN)
    # The following is useful but only in tcpdump v 4.0.0 or higher
    #self.capture_args.append('-B %d' % TCPDump.BUFFER_SIZE)
    if count:
      self.count = count
      self.capture_args.append('-c %d' % count)
    if src:
      self.capture_args.append('ip src %s' % src)
      if dst:
        self.capture_args.append('and dst %s' % dst)
    elif dst:
      self.capture_args.append('ip dst %s' % dst)

    self.read_args.append('-tt')
    self.read_args.append('-v')
    self.read_args.append('-n')
    self.read_args.append('-S')
    self.read_args.append('-r %s' % self.tmp_file)

    cmd = '%s %s' % (TCPDump.BIN, ' '.join(self.capture_args))
    if not self.child_pid:
      self.child_pid = self.host.Run(cmd, echo_error=True, fork=True)

  def Stop(self):
    """Stops collecting traces and returns results.

    If necessary (the client is active) we kill off the client and then collect
    the trace from the temporary dump file.  This is done to reduce the load
    placed on the system during the capture process by allowing parsing and
    processing of packets to be done off-line.  This of course can be subverted
    by making calls to Stop at bad times.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.child_pid:
      self.data = self.host.Communicate(self.child_pid, echo_error=True,
                                        kill=(not self.count),
                                        kill_string=TCPDump.KILL_STRING)
      cmd = '%s %s' % (TCPDump.BIN, ' '.join(self.read_args))
      self.child_pid = self.host.Run(cmd, fork=True)

  def Restart(self, src=None, dst=None, interface=config.DEFAULT_INTERFACE,
              count=config.TCPDUMP_COUNT):
    """Convenience method for stopping and then starting a TCPDump instance.

    Args:
      src: fliter by this ip/hostname as the source address.
      dst: fliter by this ip/hostname as the destination address.
      interface: listen on this interface.
      count: record this many packets (None -> Inf.).

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.Stop()
    self.Start(src, dst, interface, count)

  def Results(self):
    """Returns the processed tcpdump output.

    This returns the results in a more convenient format.  If you want access to
    the raw output from tcpdump (string) then simply access that at <TCPDump
    instance>.data.

    Returns:
      TCPDumpResults: the tcpdump output parsed and organized into lists.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if not self.child_pid is None:
      self.data = self.host.Communicate(self.child_pid, echo_error=True,
                                        kill=False)
      self.child_pid = None
    assert not self.data is None
    return TCPDumpResults(self.data)
#END CLASS TCPDump


class TCPDumpRecord(collections.namedtuple('TCPRecord', ['time_stamp', 'id_num',
                                                         'length', 'src', 'dst',
                                                         'start', 'ack'])):
  """Class to simplify working with tcpdump records.

  This works like a struct in C/C++.  See named tuple for more information.
  http://docs.python.org/library/collections.html#collections.namedtuple

  Attributes:
    time_stamp: unformatted time stamp in seconds (float)
    id_num: packet id (int)
    length: packet length in Bytes (int)
    src: source IP address (str)
    dst: destination IP address (str)
    start: first Byte in packet (int)
    ack: first Byte in packet this packet is acking (int)
  """
  pass
#END CLASS TCPDumpRecord


class TCPDumpSet(object):

  def __init__(self, target):
    self.td_list = list()
    if isinstance(target, list):
      for t in target:
        self.td_list.append(TCPDump(t))

  def __del__(self):
    for td in self.td_list:
      del td

  def Start(self, src=None, dst=None, interface=config.DEFAULT_INTERFACE,
            count=config.TCPDUMP_COUNT):
    length = len(self.td_list)
    if isinstance(src, list):
      assert len(src) == length
      src_list = src
    else:
      src_list = [src] * length
    if isinstance(dst, list):
      assert len(dst) == length
      dst_list = dst
    else:
      dst_list = [dst] * length
    if isinstance(interface, list):
      assert len(interface) == length
      interface_list = interface
    else:
      interface_list = [interface] * length
    if isinstance(count, list):
      assert len(count) == length
      count_list = count
    else:
      count_list = [count] * length

    for i in range(0, length):
      self.td_list[i].Start(src_list[i], dst_list[i], interface_list[i],
                            count_list[i])

  def Stop(self):
    for td in self.td_list:
      td.Stop()

  def Restart(self, src=None, dst=None, interface=config.DEFAULT_INTERFACE,
              count=config.TCPDUMP_COUNT):
    self.Stop()
    self.Start(src, dst, interface, count)

  def Results(self):
    results_list = list()
    for td in self.td_list:
      results_list.append(td.Results())
    return results_list


class TCPDumpResults(object):
  """Class to simplify working with tcpdump results.

  This class takes care of parsing and performing simple calculations on the
  output from tcpdump traces.  Any assumptions about the output format are to be
  met by the collection methods in the TCPDump class.
  """

  def __init__(self, trace):
    """Inits TCPDumpResults with some tcpdump results.

    Stores away the origional trace split into lines in self.trace and then
    proceeded to parse these lines into records.  These records are stored in a
    list of named tuples (TCPDumpRecord).  Missing values are represented with a
    None and proper precautions should be taken when traversing these records.

    Args:
      trace: a string with the output from running tcpdump.

    Returns:
      TCPDumpResults: in instance of the TCPDumpResults class.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    self.records = list()

    self.trace = trace.splitlines()
    self.trace.sort()
    self.__Parse()

  def __Parse(self):
    """Parse lines of tcpdump output.

    Take the lines of the tcpdump output (self.trace) and produce records that
    are easier to work with.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    for line in self.trace:
      l = line.split()
      if len(l) >= 29 and l[1] == 'IP':
        if l[21] == 'cksum':
          if l[24] == 'ack':
            start_tmp = None
            ack_tmp = int(l[25])
          elif l[25] == 'ack':
            tmp = l[24].split(':')
            start_tmp = int(tmp[0])
            ack_tmp = int(l[26])
          elif l[25] == 'win':
            tmp = l[24].split(':')
            start_tmp = int(tmp[0])
            ack_tmp = None
          else:
            logging.debug('skipping line -- \"%s...\"', line)
        elif l[22] == 'ack':
          tmp = l[21].split(':')
          start_tmp = int(tmp[0])
          ack_tmp = int(l[23])
        else:
          logging.debug('skipping line -- \"%s...\"', line)
          continue
        self.records.append(TCPDumpRecord(time_stamp=float(l[0]),
                                          id_num=int(l[7][:-1]),
                                          length=int(l[16][:-1]),
                                          src=l[17],
                                          dst=l[19][:-1],
                                          start=start_tmp,
                                          ack=ack_tmp))
      else:
        logging.debug('skipping line -- \"%s...\"', line)

  def Throughput(self, step=0.1, zero_shift=False):
    """Computes the average throughput for this trace.

    The throughput is calculated as the number of bits received for every step.
    If zero_shift is true then we will also normalize everything so that the
    trace begins at zero.  The units of throughput are Mbps.

    Args:
      step: the size of the bin to use in calculating throughput (seconds).
      zero_shift: should we adjust the output so that the first x value is 0.

    Returns:
      (x, y): a tuple of lists for the timestamps and throughput values.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    pkt_count = len(self.records)
    conv = 8.0 / 1000000.0 / step  # Bytes per bin to Mbps
    y = list()
    x = list()
    if zero_shift:
      zero = self.records[0].time_stamp
    else:
      zero = 0
    pos = self.records[0].time_stamp + step
    tmp = list()
    for i in range(0, pkt_count):
      if self.records[i].time_stamp <= pos:
        tmp.append(self.records[i].length)
      else:
        y.append(sum(tmp) * conv)
        x.append(pos - zero)
        tmp = [self.records[i].length]
        pos += step
    return (x, y)
#END CLASS TCPDumpResults
