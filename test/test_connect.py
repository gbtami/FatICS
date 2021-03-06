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

from test import  *

import time

class ConnectTest(Test):
    def test_welcome(self):
        t = self.connect()
        self.expect('Welcome', t, "welcome message")
        t.close()

    def test_login(self):
        t = self.connect()
        self.expect('login:', t, "login prompt")
        t.close()

    def test_GET(self):
        t = self.connect()
        t.write('GET / HTTP/1.0\n')
        self.expect_EOF(t)

    def test_long_line(self):
        t = self.connect()
        self.expect('login:', t)
        t.write(('A' * 1022) + '\n')
        self.expect(' should be at most ', t)
        t.write(('A' * 1023) + '\n')
        self.expect('line too long', t)
        t.close()

class LoginTest(Test):
    def test_login(self):
        t = self.connect()
        t.read_until('login:', 2)
        t.write('\n')
        self.expect('login:', t, "blank line at login prompt")

        t.write('ad\n')
        # login username too short
        self.expect(' should be at least ', t)

        # login username too long
        t.write('adminabcdefghijklmn\n')
        self.expect(' should be at most ', t)

        # login username contains numbers
        t.write('admin1\n')
        self.expect(' should only consist of ', t)

        # login contains underscores
        t.write('ad_min\n')
        self.expect(' should only consist of ', t)

        # anonymous guest login start
        t.write('guest\n')
        self.expect('Press return to enter', t)
        self.expect_not('login:', t)

        # anonymous guest login complete
        t.write('\n')
        self.expect(' Starting FICS session as ', t)
        self.close(t)

    def test_immediate_disconnect(self):
        t = self.connect()
        t.close()
        # no tests here; we need to make sure this doesn't raise an
        # exception in the server

    def test_named_guest(self):
        t = self.connect()
        t.write('GuestABCD\n\n')
        self.expect('Starting FICS session as GuestABCD(U)', t)
        self.close(t)

    def test_half_login(self):
        """ User should not actually be logged in until a correct password
        is entered. """
        t = self.connect()
        t.write('admin\n')
        t2 = self.connect_as_guest()
        t2.write('finger admin\n')
        self.expect('Last disconnected:', t2)
        self.close(t2)
        t.close()

    def test_registered_user_login(self):
        t = self.connect()
        # registered login start
        t.write('admin\n')
        self.expect('is a registered', t)

        t.write('\n')
        self.expect('login:', t)

        t.write('ADMIN\n')
        self.expect('"admin" is a registered name', t)
        t.write(admin_passwd + '\n')
        self.expect(' Starting FICS session as admin(*)', t)
        self.close(t)

    def test_double_login(self):
        t = self.connect_as_admin()
        t2 = self.connect()
        t2.write('admin\n%s\n' % admin_passwd)
        self.expect(' is already logged in', t2)
        self.expect("admin has arrived; you can't both be logged in", t)
        self.expect_EOF(t)

        t2.write('fi\n')
        self.expect('On for: ', t2)

        self.close(t2)

    def test_failed_login(self):
        """ A failed login should not interfere with a user actually
        logged in. """
        t = self.connect_as_admin()
        t2 = self.connect()
        self.expect('login: ', t2)
        t2.write('admin\nwrongpass\n')
        self.expect('*** Invalid password! ***', t2)

        # there should be a delay after a failed login
        t2.write('g\n\n')
        self.expect_not('login:', t2, timeout=1)
        self.expect('login:', t2, timeout=5)

        time.sleep(0.1)
        t.write('finger\n')
        self.expect('On for:', t)
        self.close(t)

        self.expect('fics%', t2)
        self.close(t2)

class PromptTest(Test):
    def test_prompt(self):
        t = self.connect()
        t.write('guest\n\n')
        self.expect('fics%', t, "fics% prompt")
        # there should not be more than one prompt
        self.expect_not('fics%', t)
        self.close(t)

class LogoutTest(Test):
    def test_logout(self):
        t = self.connect_as_admin()
        t.write('quit\n')
        self.expect('Logging you out.', t)
        self.expect('Thank you for using', t)
        t.close()

    def test_unclean_disconnect(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()
        t2.write('who\n')
        m = self.expect_re('(\d+) players', t2)
        count = int(m.group(1))
        t.close()
        time.sleep(0.1)

        t2.write('who\n')
        m = self.expect_re('(\d) player', t2)
        self.assert_(int(m.group(1)) == count - 1)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
