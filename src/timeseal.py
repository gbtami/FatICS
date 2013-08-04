# Copyright (C) 2010  Wil Mahan <wmahan+fatics@gmail.com>
#
# This file is part of FatICS.
#
# FatICS is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FatICS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with FatICS.  If not, see <http://www.gnu.org/licenses/>.
#

import re
import subprocess

# the difference between timeseal 1 and 2 is that the
# timeseal 1 ping always comes at the beginning of a line,
# whereas timeseal 2's ping can come at any point
TIMESEAL_1_PING = '\n[G]\n'
TIMESEAL_2_PING = '[G]\x00'
ZIPSEAL_PING = '[G]\x00'
TIMESEAL_PONG = '\x02\x39' # also known as "\x029" or "9"

class Timeseal(object):
    _timeseal_pat = re.compile(r'''^(\d+): (.*)\n$''')
    _zipseal_pat = re.compile(r'''^([0-9a-f]+): (.*)\n$''')
    zipseal_in = 0
    zipseal_out = 0
    def __init__(self):
        self.timeseal = subprocess.Popen(['timeseal/openseal_decoder'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        self.zipseal_decoder = subprocess.Popen(['timeseal/zipseal_decoder'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        self.zipseal_encoder = subprocess.Popen(['timeseal/zipseal_encoder'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)

    def decode_timeseal(self, line):
        self.timeseal.stdin.write(line + '\n')
        dec = self.timeseal.stdout.readline()
        m = self._timeseal_pat.match(dec)
        if not m:
            #print('timeseal failed to match: {{%r}}' % dec)
            return (-1, None)
        return (int(m.group(1), 10), m.group(2))

    def decode_zipseal(self, line):
        if not isinstance(line, str):
            line = line.encode('utf-8')
        self.zipseal_decoder.stdin.write(line + '\n')
        dec = self.zipseal_decoder.stdout.readline()
        m = self._zipseal_pat.match(dec)
        if not m or int(m.group(1), 16) == 0:
            #print('zipseal failed to match: {{%r}}' % dec)
            return (-1, None)
        return (int(m.group(1), 16), m.group(2))

    def compress_zipseal(self, line):
        try:
            line = line[0:1023] # XXX
            self.zipseal_encoder.stdin.write('%04x%s' % (len(line),line))
            count_str = self.zipseal_encoder.stdout.read(4)
            count = int(count_str, 16)
            ret = self.zipseal_encoder.stdout.read(count)
        except IOError:
            ret = None
        else:
            self.zipseal_in += len(line)
            self.zipseal_out += len(ret)
        return ret

    _timeseal_1_re = re.compile('TIMESTAMP\|(.+?)\|(.+?)\|')
    _timeseal_2_re = re.compile('TIMESEAL2\|(.+?)\|(.+?)\|')
    def check_hello(self, line, conn):
        """ Decodes the introductory hello string. Returns True on success. """
        session = conn.session
        m = self._timeseal_1_re.match(line)
        if m:
            session.use_timeseal = True
            session.timeseal_version = 1
            session.timeseal_acc = m.group(1)
            session.timeseal_system = m.group(2)
            return True

        m = self._timeseal_2_re.match(line)
        if m:
            session.use_timeseal = True
            session.timeseal_version = 2
            session.timeseal_acc = m.group(1)
            session.timeseal_system = m.group(2)
            return True
        return False

    _zipseal_re = re.compile('ZIPSEAL\|(\d+)\|(\d+)\|(.+?)\|(.+?)\|')
    def check_hello_zipseal(self, line, conn):
        m = self._zipseal_re.match(line)
        if m and m.group(1) == '1' and m.group(2) == '0':
            conn.session.use_zipseal = True
            conn.session.timeseal_acc = m.group(3)
            conn.session.timeseal_system = m.group(4)
            conn.transport.encoder = self.compress_zipseal
            return True

        return False

    def print_stats(self):
        return
        if self.zipseal_in > 0:
            print("compression statistics: %d in, %d out, ratio = %.3f" %
                (self.zipseal_in, self.zipseal_out,
                    float(self.zipseal_out) / self.zipseal_in))

timeseal = Timeseal()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
