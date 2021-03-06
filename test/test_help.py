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

from test import *

class TestHelp(Test):
    def test_help(self):
        t = self.connect_as_guest()

        t.write("help\n")
        self.expect("Command: help", t)
        self.expect("Usage: help", t)

        t.write("help say\n")
        self.expect("Command: say", t)
        self.expect("Usage: say", t)

        t.write("help SAY\n")
        self.expect("Command: say", t)
        self.expect("Usage: say", t)

        t.write('help commands\n')
        self.expect('Current command list:', t)

        # abbreviation
        t.write('help allob\n')
        self.expect("Command: allobservers", t)
        self.expect("Usage: allobservers", t)

        self.close(t)

    def test_help_error(self):
        t = self.connect_as_guest()
        t.write("help blahblah\n")
        self.expect('There is no help available for "blahblah".', t)
        t.write("help a/test\n")
        self.expect('There is no help available for "a/test".', t)
        self.close(t)

class TestNext(Test):
    def test_next(self):
        t = self.connect_as_guest()
        t.write('next\n')
        self.expect('There is no more', t)
        t.write('next foo\n')
        self.expect('Usage:', t)
        t.write('help license\n')
        self.expect('Type [next] to see next page.', t)

        # other commands should not interfere
        t.write('f\n')
        self.expect('Finger of ', t)

        for i in range(29):
            t.write('next\n')
            self.expect('Type [next] to see next page.', t)

        t.write('next\n')
        self.expect_not('Type [next] to see next page.', t)
        t.write('next\n')
        self.expect('There is no more', t)
        t.write('next\n')
        self.expect('There is no more', t)

        self.close(t)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
