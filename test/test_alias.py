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

import time

class TestSystemAlias(Test):
    def test_system(self):
        t = self.connect_as_admin()

        t.write('+ch 1\n')
        t.write('answer handle foo bar baz\n')
        self.expect('(1): (answering handle): foo bar baz', t)

        t.write('answer\n')
        self.expect('(1): (answering ): ', t)
        t.write('-ch 1\n')
        self.expect('[1] removed', t)

        t.write('! Test shout\n')
        self.expect('shouts: Test shout', t)

        self.close(t)

    def test_shout_tell(self):
        t = self.connect_as_admin()
        t.write('t admin test 1\n')
        self.expect('admin(*) tells you: test 1', t)

        t.write('.test 2\n')
        self.expect('admin(*) tells you: test 2', t)

        # case-insensitivity
        t.write("I is testing\n")
        self.expect("admin(*) is testing", t)

        self.close(t)

class TestUserAlias(Test):
    def test_guest_alias(self):
        t = self.connect_as_guest()

        t.write('alias\n')
        self.expect('You have no aliases', t)

        t.write('alias foo\n')
        self.expect('You have no alias named "foo"', t)

        t.write('alias foo finger\n')
        self.expect('Alias "foo" set.', t)
        t.write('foo\n')
        self.expect('Finger of Guest', t)
        t.write('foo ignore this\n')
        self.expect('Finger of Guest', t)

        t.write('alias foo\n')
        self.expect('foo -> finger', t)

        t.write('alias foo finger $@\n')
        self.expect('Alias "foo" changed.', t)
        t.write('foo admin\n')
        self.expect('Finger of admin', t)

        # numeric parameters
        t.write('alias foo tell $m $2 $1 jkl\n')
        self.expect('Alias "foo" changed.', t)
        t.write('foo abcd efgh 1234\n')
        self.expect(' tells you: efgh abcd jkl\r\n', t)

        t.write('unalias foo\n')
        self.expect('Alias "foo" unset.', t)

        # $.
        t.write('alias bar tell $. $@\n')
        self.expect('Alias "bar" set.', t)
        t.write('bar last tell player\n')
        self.expect(' tells you: last tell player', t)

        # $,
        t.write('alias bar tell $, $@\n')
        self.expect('Alias "bar" changed.', t)
        t.write('bar last tell channel\n')
        self.expect("No previous channel", t)
        t.write('t 4 channel test\n')
        self.expect('(4): channel test', t)
        t.write('bar another channel test\n')
        self.expect('(4): another channel test', t)

        # bare $
        t.write('alias bar finger $\n')
        self.expect('Alias "bar" changed.', t)
        t.write('bar\n')
        self.expect('error expanding aliases', t)

        t.write('alias bar finger $z\n')
        self.expect('Alias "bar" changed.', t)
        t.write('bar\n')
        self.expect('error expanding aliases', t)

        t.write('unalias nosuchvar\n')
        self.expect('You have no alias "nosuchvar".', t)

        self.close(t)

    def test_alias_o_p(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        # opponent
        t.write('match guestefgh 1 0\n')
        self.expect('Challenge: ', t2)
        t2.write('a\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        t.write('abo\n')
        self.expect('aborted', t2)

        t.write('alias gg tell $o gg $o!\n')
        t.write('gg\n')
        self.expect('(told GuestEFGH)', t)
        self.expect('GuestABCD(U) tells you: gg GuestEFGH!', t2)

        # partner
        t.write('set bugo 1\n')
        self.expect('open for bughouse', t)
        t2.write('part guestabcd\n')
        self.expect('GuestEFGH offers to be your bughouse partner', t)
        t.write('a\n')
        self.expect('GuestABCD accepts your partnership request', t2)
        t.write('alias fm xtell $p feed me $p!\n')
        t.write('fm\n')
        self.expect('GuestABCD(U) tells you: feed me GuestEFGH!', t2)

        self.close(t)
        self.close(t2)

    def test_user_alias(self):
        t = self.connect_as_admin()

        t.write('alias bar\n')
        self.expect('You have no alias named "bar"', t)

        t.write('alias bar tell admin my name is $m\n')
        self.expect('Alias "bar" set.', t)

        self.close(t)

        t = self.connect_as_admin()
        t.write('alias bar\n')
        self.expect('bar -> tell admin my name is $m', t)

        t.write('bar\n')
        self.expect('tells you: my name is admin', t)

        t.write('alias bar tell admin hi there\n')
        self.expect('Alias "bar" changed.', t)

        t.write('bar ignored\n')
        self.expect('tells you: hi there', t)

        t.write('unalias bar\n')
        self.expect('Alias "bar" unset.', t)

        t.write('unalias nosuchvar\n')
        self.expect('You have no alias "nosuchvar".', t)

        self.close(t)

    def test_noalias(self):
        t = self.connect_as_guest()

        t.write('alias bar tell admin hi there\n')
        self.expect('Alias "bar" set.', t)
        t.write('$bar\n')
        self.expect('bar: Command not found', t)

        self.close(t)

    def test_unidle(self):
        self._skip('semi-slow test')
        t = self.connect_as_guest()
        time.sleep(2)
        t.write('fi\n')
        self.expect('Idle: 0 seconds', t)
        time.sleep(2)
        t.write('$fi\n')
        self.expect('Idle: 0 seconds', t)
        time.sleep(2)
        t.write('$$fi\n')
        m = self.expect_re(r'Idle: (\d) second', t)
        self.assert_(int(m.group(1)) > 1)
        self.close(t)

    def test_blank(self):
        t = self.connect_as_guest()
        t.write('$\n')
        self.expect('fics% ', t)
        t.write('$$\n')
        self.expect('fics% ', t)
        t.write('$$$\n')
        self.expect('fics% ', t)
        t.write('$$$$\n')
        self.expect('$: Command not found', t)
        self.close(t)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent

