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

"""Tests for netlib.net.tcpdump."""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import os
import unittest

from netlib import config
from netlib.net import tcpdump
from netlib.shell import mock


class TCPDumpTest(unittest.TestCase):
  """Test for TCPDump.

  mock.MockHost.results are stored for places where data needs to be returned
  to keep the object under test happy.

  Attributes:
    TRACE: the contents of the sample trace file.
    TMP_FILE: the fake name of a fake tmp_file.
  """

  TRACE = open('trace.dat', 'r').read()
  TMP_FILE = '/tmp/tcpdump.dat.rnd10ext'
  mock.MockHost.results['mktemp -t tcpdump.dat.XXXXXXXXXX'] = TMP_FILE
  mock.MockHost.results['sudo tcpdump -tt -v -n -S -r %s' % TMP_FILE] = TRACE

  def setUp(self):
    """Create a mock Host object and a TCPDump object to test."""
    self.src = 'a.src'
    self.dst = 'a.dst'
    self.interface = 'eth0'
    self.count = 10
    self.fake_host = mock.MockHost('a.remote_host.com')
    self.fake_host.local = False
    self.td_obj = tcpdump.TCPDump(self.fake_host)

  def tearDown(self):
    """Free up the objects under test."""
    del self.td_obj
    del self.fake_host

  def testInit(self):
    """Make sure that we are setting things up right.

    There should be a temporary file created and we make sure that we are
    pointing to the right host and temp file.
    """
    cmd = self.fake_host.process_dict[1].cmd
    self.assertIn('mktemp', cmd)
    self.assertIn(' -t ', cmd)
    self.assertIn('tcpdump.dat.XXXXXXXXXX', cmd)
    self.assertEqual(self.td_obj.host, self.fake_host)
    self.assertEqual(self.td_obj.tmp_file, TCPDumpTest.TMP_FILE)

  def testStartSimple(self):
    """Test the simplest way to start a trace.

    This insures that the right commandline flags are being set and that there
    was no subprocess before, but that there is one after.
    """
    self.assertIsNone(self.td_obj.child_pid)
    self.td_obj.Start(interface=self.interface)
    cmd = self.fake_host.process_dict[2].cmd
    self.assertIn('sudo tcpdump', cmd)
    self.assertIn(' -i %s' % self.interface, cmd)
    self.assertIn(' -w %s' % TCPDumpTest.TMP_FILE, cmd)
    self.assertIn(' -s %d' % tcpdump.TCPDump.SNAPLEN, cmd)
    self.assertIn(' -c %d' % config.TCPDUMP_COUNT, cmd)
    self.assertNotIn(' ip src ', cmd)
    self.assertNotIn(' and dst', cmd)
    self.assertGreater(self.td_obj.child_pid, 0)

  def testStartNoCount(self):
    """Test an unlimited trace.

    This insures that the right commandline flags are being set and that there
    was no subprocess before, but that there is one after.  If we don't want a
    count then make sure it does not get sent anyways.
    """
    self.assertIsNone(self.td_obj.child_pid)
    self.td_obj.Start(interface=self.interface, count=None)
    cmd = self.fake_host.process_dict[2].cmd
    self.assertIn('sudo tcpdump', cmd)
    self.assertNotIn(' -c ', cmd)
    self.assertGreater(self.td_obj.child_pid, 0)

  def testStartSrcDst(self):
    """Test a trace with src and dst.

    This insures that the right commandline flags are being set and that there
    was no subprocess before, but that there is one after.  If a src and dst
    address are specified then it better be passed along to the cmd.
    """
    self.assertIsNone(self.td_obj.child_pid)
    self.td_obj.Start(src=self.src, dst=self.dst, interface=self.interface)
    cmd = self.fake_host.process_dict[2].cmd
    self.assertIn('sudo tcpdump', cmd)
    self.assertIn(' ip src %s' % self.src, cmd)
    self.assertIn(' and dst %s' % self.dst, cmd)
    self.assertGreater(self.td_obj.child_pid, 0)

  def testStop(self):
    """Make sure the breaks work...

    Similar to the start tests we want to make sure the right flags are passed
    along and that the process is dead when all is said and done.
    """
    self.td_obj.Start(interface=self.interface)
    self.assertGreater(self.td_obj.child_pid, 0)
    self.td_obj.Stop()
    cmd = self.fake_host.process_dict[3].cmd
    self.assertIn('sudo tcpdump', cmd)
    self.assertIn(' -tt ', cmd)
    self.assertIn(' -v ', cmd)
    self.assertIn(' -n ', cmd)
    self.assertIn(' -S ', cmd)
    self.assertIn(' -r %s' % TCPDumpTest.TMP_FILE, cmd)
    self.assertIsNone(self.td_obj.child_pid)

  def testRestart(self):
    """Make sure that we stop and then start."""
    self.td_obj.Start(interface=self.interface)
    self.assertGreater(self.td_obj.child_pid, 0)
    self.td_obj.Restart(src=self.src, dst=self.dst,
                        interface=self.interface,
                        count=self.count)
    self.assertGreater(self.td_obj.child_pid, 0)

  def testResults(self):
    """After a stop we should have some data to look at..."""
    self.td_obj.Start(interface=self.interface)
    self.td_obj.Stop()
    self.assertIsNotNone(self.td_obj.data)


class TCPDumpResultsTest(unittest.TestCase):
  """Test for TCPDumpResults.

  Attributes:
    TRACE: the contents of the sample trace file.
  """

  TRACE = open('trace.dat', 'r').read()

  def setUp(self):
    """Create a TCPDumpResults object."""
    self.td_res_obj = tcpdump.TCPDumpResults(TCPDumpResultsTest.TRACE)

  def tearDown(self):
    """Free up the object under test."""
    del self.td_res_obj

  def testInit(self):
    """Test result creation.

    Make sure that the trace string ended up in the right place, and that we end
    up with no more trace records than we had lines in the trace string.
    """
    self.assertIsNotNone(self.td_res_obj.trace)
    self.assertLessEqual(len(self.td_res_obj.records),
                         len(self.td_res_obj.trace))

  def testThroughput(self):
    """Test throughput calculations.

    Try a couple different step sizes and make sure that they are doing the
    right thing.  Larger bins should make for shorter return lists.  They should
    be the same length, and since we know this trace came from a 100Mbps link
    nothing should be negative or equal to 100 for the y values.  Also test that
    the zero_shift option is working.
    """
    x, y = self.td_res_obj.Throughput(step=1.0, zero_shift=False)
    base_len = len(x)
    self.assertEqual(len(x), len(y))
    self.assertLessEqual(max(y), 100.0)
    self.assertGreaterEqual(min(y), 0.0)

    x, y = self.td_res_obj.Throughput(step=0.5, zero_shift=False)
    self.assertAlmostEqual(len(x), base_len * 2, delta=2)
    self.assertEqual(len(x), len(y))
    self.assertLessEqual(max(y), 100.0)
    self.assertGreaterEqual(min(y), 0.0)

    x, y = self.td_res_obj.Throughput(step=0.1, zero_shift=True)
    self.assertAlmostEqual(len(x), base_len * 10, delta=10)
    self.assertEqual(len(x), len(y))
    self.assertAlmostEqual(x[0], 0.1, delta=0.01)
    self.assertLessEqual(max(y), 100.0)
    self.assertGreaterEqual(min(y), 0.0)


if __name__ == '__main__':
  unittest.main()
