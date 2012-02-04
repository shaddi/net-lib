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

"""Simplifies calling bash from within Python.

This module provides both objects and static methods to simplify the calling of
bash commands from within python.

In general these calls are blocking calls and will not return until the
underlying bash command terminates.  Any output from the command is captured,
error messages written to stderr are echoed to the logging.error function and
stdout messages are returned as a string with any trailing or leading whitespace
removed.

  Host: Class to simplify calling lots of commands on a local or remote host.

Simple object usage:
  test_host = Host('a.remote_host.com')
  test_host.Run('hostname')
  test_host.LogSysInfo()
  print test_host.uname
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import logging
import shlex
import socket
import subprocess
import time

from net-lib import config


class Host(object):
  """Class to simplify calling lots of commands on a local or remote host.

  When the module is loaded it stores basic ID information so we can decide if
  the target host is local or remote.  Once we have this information you can
  then simply ask it to run a command and it will decide if it should be run as
  a remote ssh command or locally via bash.

  Attributes:
    localhost: one level list info on where the code is running.
  """

  __localhost = socket.gethostbyaddr(socket.gethostname())
  localhost = [__localhost[0],  # FQDN
               __localhost[1][0],  # Short name
               __localhost[2][0]]  # IP address

  def __init__(self, hostname, meta=None):
    """Inits Host with a hostname.

    The hostname is saved for future reference and the decision is made to run
    commands locally or wrapped as a remote command.

    Args:
      hostname: a string with either a FQDN short name or formatted IP address
      meta: a storage location for host associated data

    Returns:
      Host: an instance of the Host class

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if not hostname:
      self.local = True
      self.host = Host.localhost[0]
    else:
      self.local = hostname in Host.localhost
      self.host = hostname
    self.meta = meta
    self.sysctl_start = dict()
    self.sysctl_mod = dict()
    self.configuration = dict()
    self.process_dict = dict()
    self.__LogSysInfo()

  def __del__(self):
    """Cleans up saved state on host.

    This makes a best effort to clean up any system settings that were changed
    on a host.  The best practice is to clean up explicitly but in the case of
    unhandeled exceptions or crashes this may be able to pick up the slack.

    If you want changes to persist after program completion then you can hack
    this my emptying sysctl_mod.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.sysctl_mod:
      self.SysctlReset()

  def Run(self, cmd, echo_error=True, fork=False):
    """Method for running a command.

    The command is executed in a subprocess.  Output from stdout is returned as
    a string with leading and trailing whitespace stripped.

    If the host is a remote host, the command is wrapped to be run as a remote
    ssh command by a local bash shell:

      'ssh %s \"%s\"' % (host, cmd)

    The resulting command is then executed as a local command with all the
    benefits, side effects and complications inherited from remote ssh commands.
    Please see Host.RunLocal for more details on hos local commands are
    handled.

    Args:
      cmd: the command to be run.
      echo_error: should we echo any error reported?
      fork: should we wait until the cmd returns before returning?

    Returns:
      A string containing the stdout from the bash cmd unless the process is to
      be forked -- in this case a process id will be returned.  Any error that
      is not redirected to stdout will be echoed to logging.error.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    if self.local:
      args = shlex.split(cmd)
    else:
      args = shlex.split('ssh %s \"%s\"' % (self.host, cmd))
    sub_p = subprocess.Popen(args, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             close_fds=True)
    logging.info('%s:%d -- %s -- %s', Host.localhost[1], sub_p.pid,
                 self.host, cmd)
    self.process_dict[sub_p.pid] = sub_p
    if fork:
      return sub_p.pid
    else:
      return self.Communicate(sub_p.pid, echo_error)

  def Poll(self, pid):
    """Method for polling a forked cmd.

    Use this to determine if the referenced cmd (by pid) is done yet.

    Args:
      pid: the process id returned by Host.Run(cmd, forked=True).

    Returns:
      True if the cmd is finished and Flase otherwise.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    assert pid in self.process_dict
    if self.process_dict[pid].poll() is None:
      return False
    else:
      return True

  def Communicate(self, pid, echo_error=True, kill=False, kill_string=None):
    """Method for getting output from a cmd.

    Use this to get the output from a cmd (explicitly if the cmd is forked).  If
    the cmd will not return on it's own you can optionally Kill it (send
    SIGKILL) or wait for a miracle.  If you are killing a cmd on a remote host
    please provide a kill_string just in case.

    Args:
      pid: the process id returned by Host.Run(cmd, forked=True).
      echo_error: should we echo any error reported?
      kill: should we wait for cmd to finish or just whack it?
      kill_string: used by Host.Kill(pid, kill_string)

    Returns:
      The output of cmd as a string or None if there is no output.

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    assert pid in self.process_dict
    if kill:
      self.Kill(pid, kill_string)
    (out, err) = self.process_dict[pid].communicate()
    if err and echo_error:
      # Type of err is string.  Disabling inferred type msg
      logging.error('%s:%d -- %s -- %s', Host.localhost[1], pid,
                    self.host, err.strip())  # pylint: disable-msg=E1103
    # Type of out is string.  Disabling inferred type msg
    if out:
      return out.strip()  # pylint: disable-msg=E1103

  def Kill(self, pid, kill_string=None):
    """Method for killing a cmd.

    Use this to kill a cmd (useful for cmds that do not return on their own).
    Locally uses the signal SIGKILL.  If you are killing a cmd on a remote host
    please provide a kill_string.

    Args:
      pid: the process id returned by Host.Run(cmd, forked=True).
      kill_string: used by Host.Kill(pid, kill_string)

    Raises:
      No exceptions handled here.
      No new exceptions generated here.
    """
    assert pid in self.process_dict
    if not self.Poll(pid):
      if not self.local:
        assert not kill_string is None
        self.Run(kill_string, echo_error=True, fork=False)
    if not self.Poll(pid):
      self.process_dict[pid].kill()

  def __LogSysInfo(self):
    """Instance method for logging system info.

    System configuration information is grabbed as a snapshot for later use.
    The following commands are called and their output is stored in its entirety
    in a instance variable of the same name.

    Now in parallel!!!

      sysctl -A
      ifconfig -a
      uname -a
      date +%D-%T.%N
      netstat -a

    Raises:
      see Host.RunLocal
    """
    sysctl_pid = self.Run('sysctl -A', echo_error=False, fork=True)
    ifconfig_pid = self.Run('ifconfig -a', fork=True)
    uname_pid = self.Run('uname -a', fork=True)
    date_pid = self.Run('date +%D-%T.%N', fork=True)
    netstat_pid = self.Run('netstat -a', fork=True)
    self.configuration['sysctl'] = self.Communicate(sysctl_pid,
                                                    echo_error=False,
                                                    kill=False)
    self.configuration['ifconfig'] = self.Communicate(ifconfig_pid, kill=False)
    self.configuration['uname'] = self.Communicate(uname_pid, kill=False)
    self.configuration['date'] = self.Communicate(date_pid, kill=False)
    self.configuration['netstat'] = self.Communicate(netstat_pid, kill=False)
    for l in self.configuration['sysctl'].splitlines():
      tmp = l.split('=')
      self.sysctl_start[tmp[0].strip()] = tmp[1].strip()

  def Sysctl(self, key, value=None):
    """Instance method for setting a sysctl variable.

    This is used so often that in order to have cleaner code we have a special
    case for formatting these calls which can be run remotely or locally.  Note
    that sudo privileges are needed to run this command and an error will be
    generated if they are used without sudo rights.

    Origional values are saved in the sysctl_mod dictionary -- this is a
    snapshot of the system at the time the Host object is created.  Any changes
    that are made can be returned to the origional state by calling
    SysctlReset().

    Simple usage:
      host_obj.Run('sudo sysctl -w net.ipv4.tcp_congestion_control=reno')
      becomes
      host_obj.Sysctl('net.ipv4.tcp_congestion_control', 'reno')

    Args:
      key: the complete variable name to be set
      value: the value to be used in string format

    Raises:
      see Host.RunLocal
    """
    if not key in self.sysctl_start:
      tmp = self.Run('sudo sysctl %s' % key)
      if tmp:
        self.sysctl_start[key] = tmp.split('=')[1].strip()
      else:
        return

    if value is None:
      result = self.Run('sudo sysctl %s' % key, echo_error=False, fork=False)
    else:
      result = self.Run('sudo sysctl -w %s=\\\"%s\\\"' % (key, value),
                        echo_error=False, fork=False)

    if result:
      self.sysctl_mod[key] = value

  def SysctlReset(self):
    """Instance method for resetting all sysctl variables.

    Origional values are saved in the sysctl_mod dictionary -- this is a
    snapshot of the system at the time the Host object is created.  Any changes
    that are made can be returned to the origional state by calling
    SysctlReset().

    Simple usage:
      host_obj.SysctlReset()

    Raises:
      see Host.RunLocal
    """
    for key in self.sysctl_mod:
      self.Run('sudo sysctl -w %s=\\\"%s\\\"' % (key, self.sysctl_start[key]),
               echo_error=False, fork=False)
    self.sysctl_mod.clear()

  def Reboot(self):
    """Instance method for rebooting a host.

    Calls 'sudo reboot' on the remote host, waits for it to go down, then calls
    the hostname command on the remote host.  When the call returns a hostname
    that matches then we know the system is back up.

    Simple usage:
      host_obj.Reboot()

    Raises:
      see Host.RunLocal
    """
    logging.warn('DOWN -- %s', self.host)
    self.Run('sudo reboot', fork=False)
    result = ''
    start_time = time.time()
    while not result and time.time() - start_time < config.TIMEOUT:
      time.sleep(config.WAIT_TIME)
      result = self.Run('hostname', echo_error=False, fork=False)
    if result == self.host:
      logging.warn('UP -- %s', self.host)
    else:
      logging.error('TIMEOUT -- %s', self.host)
#END CLASS Host
