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

class FingerTest(Test):
    def test_finger(self):
        t = self.connect_as_admin()
        t.write('finger\n')
        self.expect('Finger of admin(*):', t)
        self.expect('On for:', t)
        self.expect('Host:', t)
        self.expect('Email:', t)

        # finger with trailing space
        t.write('finger \r\n')
        self.expect('Finger of admin(*):', t)

        # finger with parameter
        t.write('finger admin\r\n')
        self.expect('Finger of admin(*):', t)

        # finger with prefix
        t.write('finger ad\n')
        self.expect('Finger of admin(*):', t)

        t.write('finger a\n')
        self.expect('need to specify at least', t)

        t.write('finger notarealuser\n')
        self.expect('no player matching', t, "nonexistent user")

        t.write('finger admin1\n')
        self.expect('not a valid handle', t, "invalid name")

        self.close(t)

    def test_finger_timezone(self):
        t = self.connect_as_guest()
        t.write('set tzone US/Eastern\n')
        self.expect('Time zone set', t)
        t.write('finger admin\n')
        self.expect_re(r'Last disconnected: .* E[DS]T', t)
        self.close(t)

    @with_player('admintwo')
    def test_ambiguous_finger(self):
        t = self.connect_as_admin()

        t.write('finger ad\n')
        self.expect('Finger of admin(*):', t, "finger with prefix ignores offline user")
        t2 = self.connect_as('admintwo')
        # ambiguous, both users online
        t2.write('finger ad\n')
        self.expect('Matches: admin admintwo', t2)
        self.close(t2)
        self.close(t)

        # ambiguous, both users offline
        t = self.connect_as_guest()
        t.write('finger ad\n')
        self.expect('Matches: admin admintwo', t)
        self.close(t)

    def test_finger_guest(self):
        t = self.connect_as_guest()

        # finger guest
        t.write('finger\n')
        self.expect('Finger of Guest', t)

        # finger offline user
        t.write('finger admin\n')
        self.expect('Last disconnected:', t)

        # finger offline user prefix
        t.write('finger ad\n')
        self.expect('Last disconnected:', t)

        t.write('finger admi\n')
        self.expect('Last disconnected:', t)

        t.close()

    def test_finger_game(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: GuestABCD (++++) admin (----) unrated lightning 1 0', t)
        self.expect('Creating: GuestABCD (++++) admin (----) unrated lightning 1 0', t2)

        t.write('finger admin\n')
        self.expect('(playing game 1: GuestABCD vs. admin)\r\n', t)
        t.write('finger guestabcd\n')
        self.expect('(playing game 1: GuestABCD vs. admin)\r\n', t)
        t2.write('finger admin\n')
        self.expect('(playing game 1: GuestABCD vs. admin)\r\n', t2)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_finger_registered(self):
        t = self.connect_as('TestPlayer')
        t.write('f\n')
        self.expect('Finger of TestPlayer:', t)
        self.expect('Email: ', t)
        self.expect('Total time online:', t)
        self.expect('% of life online: ', t)
        self.expect('(since ', t)

        t2 = self.connect_as_guest()
        t2.write('f testplayer\n')
        self.expect('Finger of TestPlayer:', t2)
        self.expect_not('Email:', t2)

        t.write('set 1 some note\n')
        self.expect('Note 1 set', t)

        t2.write('f testplayer\n')
        self.expect('has not played any rated games', t2)
        self.expect('1: some note', t2)
        t2.write('f testplayer n\n')
        self.expect_not('has not played any rated games', t2)
        t2.write('f testplayer n\n')
        self.expect('1: some note', t2)
        t2.write('f testplayer r\n')
        self.expect('has not played any rated games', t2)
        t2.write('f testplayer r\n')
        self.expect_not('1: some note', t2)

        self.close(t)
        self.close(t2)

    @with_player('aUniquePlayer')
    def test_finger_never_connected_1(self):
        t = self.connect_as_guest()
        t.write('f auniqueplayer\n')
        self.expect('aUniquePlayer has never connected.', t)
        self.close(t)

    def test_finger_never_connected_2(self):
        t = self.connect_as_admin()
        t.write('addplayer oneUniquePlayer somebody@example.com Some Name\n')
        self.expect('Added:', t)

        t2 = self.connect()
        t2.write('oneuniqueplayer\nwrongpass\n')
        self.expect('Invalid pass', t2)
        t2.close()

        t.write('f oneuniqueplayer\n')
        self.expect('oneUniquePlayer has never connected.', t)
        t.write('remplayer oneuniqueplayer\n')
        self.expect('removed', t)
        self.close(t)


class HandlesTest(Test):
    @with_player('someplayerone')
    @with_player('someplayertwo')
    @with_player('someplayerthree')
    def test_handles(self):
        t = self.connect_as_guest()

        t.write('handles d\n')
        self.expect('You need to specify at least two characters of the name.',
            t)

        t.write('handles doesnotexist\n')
        self.expect('There is no player matching the name doesnotexist.', t)

        t.write('handles someplayero\n')
        self.expect('-- Matches: 1 player --', t)
        self.expect('someplayerone', t)

        t.write('handles someplayer\n')
        self.expect('-- Matches: 3 players --', t)
        self.expect('someplayer', t)
        self.expect('someplayer', t)
        self.expect('someplayer', t)

        self.close(t)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
