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

"""Tests for netlib.net.iperf.

mock.MockHost.results are stored for places where data needs to be returned to
keep the objects under test happy.
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import unittest

from netlib.net import iperf
from netlib.shell import mock


server_result = """------------------------------------------------------------
Server listening on TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  4] local 192.168.31.61 port 5001 connected with 192.168.31.60 port 33910
[  5] local 192.168.31.61 port 5001 connected with 192.168.31.59 port 41063
[  4] 0.0-10.0 sec  59.6 MBytes  49.9 Mbits/sec
[  5]  0.0-10.0 sec  53.3 MBytes  44.7 Mbits/sec"""

client_result = """------------------------------------------------------------
Client connecting to a.dst, TCP port 5001
TCP window size: 16.0 KByte (default)
------------------------------------------------------------
[  3] local 192.168.31.59 port 41063 connected with 192.168.31.61 port 5001
[  3] 0.0-10.0 sec  53.3 MBytes  44.7 Mbits/sec"""

mock.MockHost.results['iperf -s'] = server_result
mock.MockHost.results['iperf -c a.dst -t 10'] = client_result
mock.MockHost.results['iperf -c b.dst -t 10'] = client_result
mock.MockHost.results['iperf -c c.dst -t 10'] = client_result


class IperfServerTest(unittest.TestCase):
  """Test for IperfServer."""

  def setUp(self):
    """Create a mock Host object and a IperfServer object to test."""
    self.fake_host = mock.MockHost('a.remote_host.com')
    self.fake_host.local = False
    self.ips_obj = iperf.IperfServer(self.fake_host)

  def tearDown(self):
    """Free up the objects under test."""
    del self.ips_obj
    del self.fake_host
    iperf.IperfServer.pkt = None
    iperf.IperfServer.interval = None

  def testInit(self):
    """Make sure that we are setting things up right."""
    self.assertIsNotNone(self.ips_obj.host)
    self.assertIsNotNone(self.ips_obj.args)
    self.assertIsNone(self.ips_obj.data)
    self.assertIsNone(self.ips_obj.child_pid)

  def testStartSimple(self):
    """Make sure that we are not setting any flags we are not supposed to."""
    self.assertIsNone(self.ips_obj.child_pid)
    self.ips_obj.Start()
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('iperf', cmd)
    self.assertIn(' -s', cmd)
    self.assertNotIn(' -u', cmd)
    self.assertNotIn(' -M', cmd)
    self.assertNotIn(' -i', cmd)
    self.assertGreater(self.ips_obj.child_pid, 0)

  def testStartUDP(self):
    """Make sure we are setting the UDP flag."""
    self.assertIsNone(self.ips_obj.child_pid)
    self.ips_obj.Start(udp=True)
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('iperf', cmd)
    self.assertIn(' -s', cmd)
    self.assertIn(' -u', cmd)
    self.assertNotIn(' -M', cmd)
    self.assertNotIn(' -i', cmd)
    self.assertGreater(self.ips_obj.child_pid, 0)

  def testStartPktInterval(self):
    """Make sure we are setting the interval flag."""
    self.assertIsNone(self.ips_obj.child_pid)
    iperf.IperfServer.pkt = 1460
    iperf.IperfServer.interval = 1
    self.ips_obj.Start()
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('iperf', cmd)
    self.assertIn(' -s', cmd)
    self.assertNotIn(' -u', cmd)
    self.assertIn(' -M %d' % 1460, cmd)
    self.assertIn(' -i %d' % 1, cmd)
    self.assertGreater(self.ips_obj.child_pid, 0)

  def testStop(self):
    """Make sure we are stopping the subprocess."""
    self.ips_obj.Start()
    self.assertGreater(self.ips_obj.child_pid, 0)
    self.ips_obj.Stop()
    self.assertIsNone(self.ips_obj.child_pid)

  def testResults(self):
    """Make sure that we can get some data back from this thing."""
    self.ips_obj.Start()
    self.ips_obj.Stop()
    self.ips_obj.Results()
    self.assertIsNotNone(self.ips_obj.data)
#END CLASS IperfServerTest


class IperfClientTest(unittest.TestCase):
  """Test for IperfClient."""

  def setUp(self):
    """Create a mock Host object and a IperfClient object to test."""
    self.fake_host = mock.MockHost('a.remote_host.com')
    self.fake_host.local = False
    self.dst = 'a.dst'
    self.ipc_obj = iperf.IperfClient(self.fake_host, self.dst)

  def tearDown(self):
    """Free up the objects under test."""
    del self.ipc_obj
    del self.fake_host
    iperf.IperfClient.pkt = None
    iperf.IperfClient.interval = None

  def testInit(self):
    """Make sure that we are setting things up right."""
    self.assertIsNotNone(self.ipc_obj.host)
    self.assertIsNotNone(self.ipc_obj.args)
    self.assertIsNone(self.ipc_obj.data)
    self.assertIsNone(self.ipc_obj.length)
    self.assertIsNone(self.ipc_obj.child_pid)

  def testStartSimple(self):
    """Make sure that we are not setting any flags we are not supposed to."""
    self.assertIsNone(self.ipc_obj.child_pid)
    self.ipc_obj.Start()
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('iperf', cmd)
    self.assertIn(' -c %s' % self.dst, cmd)
    self.assertNotIn(' -t', cmd)
    self.assertNotIn(' -w', cmd)
    self.assertNotIn(' -b', cmd)
    self.assertNotIn(' -u', cmd)
    self.assertNotIn(' -M', cmd)
    self.assertNotIn(' -i', cmd)
    self.assertGreater(self.ipc_obj.child_pid, 0)

  def testStartUDPLength(self):
    """Make sure we are setting the UDP flag."""
    self.assertIsNone(self.ipc_obj.child_pid)
    self.ipc_obj.Start(length=10, rate='10M')
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn(' -u', cmd)
    self.assertIn(' -c %s' % self.dst, cmd)
    self.assertIn(' -t %d' % 10, cmd)
    self.assertIn(' -b %s' % '10M', cmd)
    self.assertNotIn(' -w', cmd)
    self.assertNotIn(' -M', cmd)
    self.assertNotIn(' -i', cmd)
    self.assertGreater(self.ipc_obj.child_pid, 0)

  def testStartPktInterval(self):
    """Make sure we are setting the interval flag."""
    self.assertIsNone(self.ipc_obj.child_pid)
    iperf.IperfClient.pkt = 1460
    iperf.IperfClient.interval = 1
    self.ipc_obj.Start()
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('iperf', cmd)
    self.assertIn(' -M %d' % 1460, cmd)
    self.assertIn(' -i %d' % 1, cmd)
    self.assertGreater(self.ipc_obj.child_pid, 0)

  def testStop(self):
    """Make sure we are stopping the subprocess."""
    self.ipc_obj.Start()
    self.assertGreater(self.ipc_obj.child_pid, 0)
    self.ipc_obj.Stop()
    self.assertIsNone(self.ipc_obj.child_pid)

  def testResults(self):
    """Make sure that we can get some data back from this thing."""
    self.ipc_obj.Start(length=10, blocking_call=True)
    self.ipc_obj.Results()
    self.assertIsNotNone(self.ipc_obj.data)
#END CLASS IperfClientTest


class IperfSetTest(unittest.TestCase):
  """Test for IperfClient."""
  target_src = ['f.remote_host.com', 'e.remote_host.com', 'f.remote_host.com']
  target_dst = ['a.remote_host.com', 'b.remote_host.com', 'c.remote_host.com']
  dst = ['a.dst', 'b.dst', 'c.dst']

  def setUp(self):
    """Create mock Host objects."""
    self.fake_host_src = [mock.MockHost(x) for x in IperfSetTest.target_src]
    self.fake_host_dst = [mock.MockHost(x) for x in IperfSetTest.target_dst]
    for host in self.fake_host_src:
      host.local = False
    for host in self.fake_host_dst:
      host.local = False
    self.ips_obj = None

  def tearDown(self):
    """Free up the objects under test."""
    del self.ips_obj
    for host in self.fake_host_src:
      del host
    for host in self.fake_host_dst:
      del host
    iperf.IperfServer.pkt = None
    iperf.IperfServer.interval = None
    iperf.IperfClient.pkt = None
    iperf.IperfClient.interval = None

  def testInitOneToOne(self):
    """Make sure that we are setting things up right."""
    self.ips_obj = iperf.IperfSet(self.fake_host_src[0],
                                  self.fake_host_dst[0],
                                  IperfSetTest.dst[0])
    self.assertEqual(len(self.ips_obj.client_list), 1)
    self.assertEqual(len(self.ips_obj.server_list), 1)
    for client in self.ips_obj.client_list:
      self.assertTrue(isinstance(client, iperf.IperfClient))
      self.assertIn('-c %s' % IperfSetTest.dst[0], client.args)
    for server in self.ips_obj.server_list:
      self.assertTrue(isinstance(server, iperf.IperfServer))

  def testInitManyToMany(self):
    """Make sure that we are setting things up right."""
    self.ips_obj = iperf.IperfSet(self.fake_host_src,
                                  self.fake_host_dst,
                                  IperfSetTest.dst)
    self.assertEqual(len(self.ips_obj.client_list),
                     len(self.fake_host_src))
    self.assertEqual(len(self.ips_obj.server_list),
                     len(self.fake_host_dst))
    for i in range(0, len(self.ips_obj.client_list)):
      self.assertTrue(isinstance(self.ips_obj.client_list[i],
                                 iperf.IperfClient))
      self.assertIn('-c %s' % IperfSetTest.dst[i],
                    self.ips_obj.client_list[i].args)
      self.assertEqual(self.ips_obj.client_list[i].host.host,
                       IperfSetTest.target_src[i])
    for i in range(0, len(self.ips_obj.server_list)):
      self.assertTrue(isinstance(self.ips_obj.server_list[i],
                                 iperf.IperfServer))
      self.assertEqual(self.ips_obj.server_list[i].host.host,
                       IperfSetTest.target_dst[i])

  def testInitManyToOne(self):
    """Make sure that we are setting things up right."""
    self.ips_obj = iperf.IperfSet(self.fake_host_src,
                                  self.fake_host_dst[0],
                                  IperfSetTest.dst[0])
    self.assertEqual(len(self.ips_obj.client_list),
                     len(self.fake_host_src))
    self.assertEqual(len(self.ips_obj.server_list), 1)
    for i in range(0, len(self.ips_obj.client_list)):
      self.assertTrue(isinstance(self.ips_obj.client_list[i],
                                 iperf.IperfClient))
      self.assertIn('-c %s' % IperfSetTest.dst[0],
                    self.ips_obj.client_list[i].args)
      self.assertEqual(self.ips_obj.client_list[i].host.host,
                       IperfSetTest.target_src[i])
    for server in self.ips_obj.server_list:
      self.assertTrue(isinstance(server, iperf.IperfServer))

  def testStart(self):
    """Make sure that all server and clients are started.

    Let's also make sure that they have the right hostnames.
    """
    self.ips_obj = iperf.IperfSet(self.fake_host_src,
                                  self.fake_host_dst,
                                  IperfSetTest.dst)
    for server in self.ips_obj.server_list:
      self.assertIsNone(server.child_pid)
    for client in self.ips_obj.client_list:
      self.assertIsNone(client.child_pid)
    self.ips_obj.Start()
    for server in self.ips_obj.server_list:
      self.assertGreater(server.child_pid, 0)
    for client in self.ips_obj.client_list:
      self.assertGreater(client.child_pid, 0)

  def testStop(self):
    """Make sure that all server and clients are stopped."""
    self.ips_obj = iperf.IperfSet(self.fake_host_src,
                                  self.fake_host_dst,
                                  IperfSetTest.dst)
    self.ips_obj.Start()
    for server in self.ips_obj.server_list:
      self.assertGreater(server.child_pid, 0)
    for client in self.ips_obj.client_list:
      self.assertGreater(client.child_pid, 0)
    self.ips_obj.Stop()
    for server in self.ips_obj.server_list:
      self.assertIsNone(server.child_pid)
    for client in self.ips_obj.client_list:
      self.assertIsNone(client.child_pid)

  def testResults(self):
    """Make sure that all server and clients are saving results.

    Let's also make sure that they have the right content.
    """
    self.ips_obj = iperf.IperfSet(self.fake_host_src,
                                  self.fake_host_dst,
                                  IperfSetTest.dst)
    self.ips_obj.Start(length=10)
    self.ips_obj.Stop()
    results = self.ips_obj.Results()
    self.assertEqual(len(results), 2)
    self.assertEqual(len(results[0]), len(self.fake_host_dst))
    self.assertEqual(len(results[1]), len(self.fake_host_src))
    for i in range(0, len(self.fake_host_dst)):
      self.assertIn('Server listening', results[0][i])
    for i in range(0, len(self.fake_host_src)):
      self.assertIn('Client connecting', results[1][i])
#END CLASS IperfSetTest


if __name__ == '__main__':
  unittest.main()
