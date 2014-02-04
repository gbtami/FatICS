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

import os.path
import subprocess
import telnetlib
import subprocess
import time

from test import *

timeseal_prog = '../timeseal/openseal'
wine_prog = '/usr/bin/wine'
timeseal_prog_win = '/home/wmahan/chess/timeseal.exe'

class TestTimeseal(Test):
    def test_timeseal(self):
        if not os.path.exists(timeseal_prog):
            raise unittest.SkipTest('no timeseal binary')
        t = self.connect_as_guest('GuestABCD')

        try:
            import pexpect
        except ImportError:
            raise unittest.SkipTest('pexpect module not installed')

        process = pexpect.spawn(timeseal_prog, [host, str(compatibility_port)])

        process.expect_exact('login:')
        process.send('admin\n')
        process.send('%s\n' % admin_passwd)

        process.expect_exact('fics%')

        process.send('finger\n')
        process.expect_exact('Finger of admin')
        process.expect_exact('Timeseal 1:  On')
        process.expect_exact('Acc:         openseal')
        process.expect_exact('System:      Running on an operating system')

        t.write('set style 12\n')
        process.send('set style 12\n')

        t.write('match admin 1 0 white\n')
        process.expect_exact('Challenge:')
        process.send('a\n')
        process.expect_exact('Creating:')
        self.expect('Creating:', t)

        t.write('e4\n')
        self.expect('<12> ', t)
        process.expect_exact('<12> ')

        process.send('c5\n')
        self.expect('<12> ', t)
        process.expect_exact('<12> ')

        t.write('Nf3\n')
        self.expect('<12> ', t)
        process.expect_exact('<12> ')

        process.send('e6\n')
        self.expect('<12> ', t)
        process.expect_exact('<12> ')

        t.write('d4\n')
        self.expect('<12> ', t)
        process.expect_exact('<12> ')

        t.write('abort\n')
        process.send('abort\n')
        self.expect('aborted', t)
        process.expect_exact('aborted')

        process.send('quit\n')
        process.expect_exact('Thank you for using')
        process.expect_exact(pexpect.EOF)

        self.close(t)
        process.close()

class TestTimesealWindows(Test):
    def test_timeseal_windows(self):
        raise unittest.SkipTest('temporarily disabled')
        if not os.path.exists(wine_prog):
            raise unittest.SkipTest('no wine binary')
        if not os.path.exists(timeseal_prog_win):
            raise unittest.SkipTest('no timeseal windows binary')

        try:
            import pexpect
        except ImportError:
            raise unittest.SkipTest('pexpect module not installed')

        process = pexpect.spawn(wine_prog,
            [timeseal_prog_win, host, str(compatibility_port)])

        process.expect_exact('login:')
        process.send('admin\n')
        process.send('%s\n' % admin_passwd)
        process.expect_exact('fics%')

        process.send('finger\n')
        process.expect_exact('Finger of admin')
        process.expect_exact('Timeseal 1:  On')

        process.send('quit\n')
        process.expect_exact('Thank you for using')
        process.expect_exact(pexpect.EOF)
        process.close()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
