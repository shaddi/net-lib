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

"""Convert is used to fix problems with moving python shelf objs to differnt OS..
"""

__author__ = 'gavaletz@google.com (Eric Gavaletz)'

import shelve
import cPickle

def ColsToRows(cols, missing='*', string=False):
  max_col = max([len(x) for x in cols])
  max_row = len(cols)
  rows = [missing] * max_col
  for i in range(0, max_col):
    rows[i] = [missing] * max_row
  for i in range(0, max_col):
    for j in range(0, max_row):
      if len(cols[j]) > i:
        rows[i][j] = cols[j][i]
  if string:
    for i in range(0, max_col):
      rows[i] = ' '.join(str(x) for x in rows[i])
    return '\n'.join(rows)
  else:
    return rows


def CopyAll(a, b):
  for k in a:
    b[k] = a[k]

def DarwinToLinux(darwin_file_name, linux_file_name):
    darwin = shelve.BsdDbShelf(bsddb.btopen(darwin_file_name, 'r'))
    linux = shelve.open(linux_file_name)
    CopyAll(darwin, linux)
    linux.close()
    darwin.close()

def LinuxToDarwin(linux_file_name, darwin_file_name):
    linux = shelve.open(linux_file_name)
    darwin = shelve.BsdDbShelf(bsddb.btopen(darwin_file_name, 'c'))
    CopyAll(linux, darwin)
    darwin.close()
    linux.close()

def LinuxToPickle(linux_file_name, pickle_file_name):
    linux = shelve.open(linux_file_name)
    data = dict()
    CopyAll(linux, data)
    linux.close()
    cPickle.dump(data, open(pickle_file_name, 'wb'))
