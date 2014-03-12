# -*- coding: utf-8 -*-
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

class TestMaciejg(Test):
    def test_maciejg_out(self):
        """ Test the compatibility port used for old clients that don't
        support FatICS's newline order and non-ASCII characters. """
        t = telnetlib.Telnet(host, compatibility_port)
        self.expect('&#x2659;&#x2658;&#x2657;&#x2656;&#x2655;&#x2654; FatICS', t)
        self.expect('freechess.org', t) # for Babas
        t.write("guestabcd\n\n")
        self.expect('fics% ', t)
        t.write('t guestabcd a à b\n')
        self.expect('tells you: a &#xe0; b', t)
        t.write('quit\n')
        self.expect('&#x2659;&#x2659;&#x2659; Thank you ', t)
        t.close()

    def test_maciejg_in(self):
        t = telnetlib.Telnet(host, compatibility_port)
        t.write("guestefgh\n\n")
        self.expect('fics% ', t)
        t2 = self.connect_as_guest('GuestABCD')

        t.write('t guestabcd &#x41f;&#x43e; &#x43e;&#x436;&#x438;&#x432;&#x43b;&#x451;&#x43d;&#x43d;&#x44b;&#x43c; &#x431;&#x435;&#x440;&#x435;&#x433;&#x430;&#x43c;\n')
        self.expect('По оживлённым берегам', t2)


        t.write('quit\n')
        self.expect('Thank you ', t)
        t.close()
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
