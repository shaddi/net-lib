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

"""Mock objects for testing system interaction.

  MockSubProcess: Replacement for the stdlib suprocess object.
  MockHost: Replacement for net-lib.shell.bash.Host objects.

Simple object usage:
  test_host = Host('a.remote_host.com')
  test_host.Run('hostname')
  test_host.LogSysInfo()
  print test_host.uname
"""


__author__ = 'gavaletz@google.com (Eric Gavaletz)'

from net-lib.shell import bash


class MockSubProcess(object):
  """Replacement for suprocess objects.

  By using this we can re-use most of the code in net-lib.shell.bash for the
  MockHost objects.  Tries to stay as close to the API for the stdlib subprocess
  as possible.
  """

  def __init__(self, host, pid, cmd, echo_error=True, fork=False):
    """Store all the info we will need later."""
    self.host = host
    self.pid = pid
    self.cmd = cmd
    self.echo_error = echo_error
    self.fork = fork
    self.active = True

  # overiding methods in the stdlib
  def wait(self):  # pylint: disable-msg=C6409
    """Assume the process has always returned."""
    self.active = False
    return 0

  # overiding methods in the stdlib
  def poll(self):  # pylint: disable-msg=C6409
    """Assume the process has always returned."""
    self.active = False
    return 0

  # overiding methods in the stdlib
  def kill(self):  # pylint: disable-msg=C6409
    """An easy kill..."""
    self.active = False

  # overiding methods in the stdlib
  def communicate(self):  # pylint: disable-msg=C6409
    """For Host.Reboot to work we need to return the actual hostname."""
    self.active = False
    if self.cmd == 'hostname':
      return (self.host, '')
    elif self.cmd in MockHost.results:
      return (MockHost.results[self.cmd], '')
    else:
      return ('', '')
#END CLASS MockSubProcess


class MockHost(bash.Host):
  """Replacement for net-lib.shell.bash.Host objects.

  Since we don't want to modify the state of real machines during tests this
  mock object will accept the cmd and reply with data stored the results
  dictionary (indexed by cmd).

  Attributes:
    results: mapping of commands to results (string) that should be returned.
  """

  results = dict()

  def __init__(self, hostname, meta=None):
    """Inits a MockHost with a hostname."""
    self.local = True
    self.host = hostname
    self.meta = meta
    self.sysctl_start = dict()
    self.sysctl_mod = dict()
    self.configuration = dict()
    self.__pid_counter = 1
    self.process_dict = dict()

  def GetPid(self):
    """We are not creating reall subprocesses so we need a replacement pid."""
    self.__pid_counter += 1
    return self.__pid_counter - 1

  def Run(self, cmd, echo_error=True, fork=False):
    """We are not creating reall subprocesses so inject a fake one."""
    # When tests break this is really handy info to have...
    print cmd
    sub_p = MockSubProcess(self.host, self.GetPid(), cmd, echo_error, fork)
    self.process_dict[sub_p.pid] = sub_p
    if fork:
      return sub_p.pid
    else:
      return self.Communicate(sub_p.pid, echo_error)
#END CLASS MockHost
