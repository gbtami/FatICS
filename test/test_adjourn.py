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

class TestAdjourn(Test):
    @with_player('TestPlayer')
    def test_adjourn_and_resume(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')
        t.write('set style 12\n')
        t2.write('set style 12\n')

        t.write('match testplayer 3 4 w\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        moves = ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6',
            'Nc3', 'a6']
        wtm = True
        for mv in moves:
            if wtm:
                t.write('%s\n' % mv)
            else:
                t2.write('%s\n' % mv)
            self.expect('<12> ', t)
            self.expect('<12> ', t2)
            wtm = not wtm

        self.close(t)

        self.expect('{Game 1 (admin vs. TestPlayer) admin lost connection; game adjourned} *', t2)
        t = self.connect()
        t.write('%s\n%s\n' % ('admin', admin_passwd))

        self.expect('1 player who has an adjourned game with you is online: TestPlayer', t)
        self.expect('Notification: admin, who has an adjourned game with you, has arrived.', t2)

        t.write('stored\n')
        self.expect('1: W TestPlayer      Y [bnr  3   4] 38-38 W6   B90', t)
        t2.write('stored\n')
        self.expect('1: B admin           Y [bnr  3   4] 38-38 W6   B90', t2)

        t.write('match testplayer 3+0\n')
        self.expect('You have an adjourned game with TestPlayer.', t)

        t.write('match testplayer\n')
        self.expect('Issuing: admin (----) TestPlayer (----) rated blitz 3 4 (adjourned)', t)
        self.expect('Challenge: admin (----) TestPlayer (----) rated blitz 3 4 (adjourned)', t2)
        t2.write('a\n')

        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t)
        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t2)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t2)

        t.write('Be3\n')
        self.expect('B/c1-e3', t2)

        t2.write('moves\n')
        self.expect('Movelist for game 1:\r\n\r\nadmin (----) vs. TestPlayer (----) --- ', t2)

        t.write('abo\n')
        t2.write('abo\n')
        self.expect('aborted by agreement', t)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_adjourn_agreement(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')
        t3 = self.connect_as_guest()

        t.write('set style 12\n')
        t2.write('set style 12\n')

        t.write('match testplayer 3 4 w\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t3.write('o testplayer\n')
        self.expect('Game 1:', t3)


        moves = ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6',
            'Nc3', 'a6']
        wtm = True
        for mv in moves:
            if wtm:
                t.write('%s\n' % mv)
            else:
                t2.write('%s\n' % mv)
            self.expect('<12> ', t)
            self.expect('<12> ', t2)
            wtm = not wtm

        t2.write('adjourn\n')
        self.expect('Requesting to adjourn game 1.', t2)
        t2.write('adj\n')
        self.expect('You are already offering to adjourn game 1.', t2)
        self.expect('TestPlayer requests to adjourn game 1.', t)
        self.expect('TestPlayer requests to adjourn game 1.', t3)

        t.write('Be3\n')
        self.expect('Declining the adjourn request from TestPlayer.', t)
        self.expect('admin declines your adjourn request.', t2)
        self.expect('admin declines the adjourn request.', t3)

        t.write('adj\n')
        self.expect('Requesting to adjourn game 1.', t)
        self.expect('admin requests to adjourn game 1.', t2)
        self.expect('admin requests to adjourn game 1.', t3)
        t.write('wi\n')
        self.expect('Withdrawing your adjourn request to TestPlayer.', t)
        self.expect('admin withdraws the adjourn request.', t2)
        self.expect('admin withdraws the adjourn request.', t3)

        t2.write('adj\n')
        self.expect('Requesting to adjourn game 1.', t2)
        self.expect('TestPlayer requests to adjourn game 1.', t)
        self.expect('TestPlayer requests to adjourn game 1.', t3)

        # adjourn using "accept"
        t.write('accept\n')
        self.expect('admin accepts your adjourn request.', t2)
        self.expect('admin accepts the adjourn request.', t3)
        self.expect('{Game 1 (admin vs. TestPlayer) Game adjourned by agreement} *', t)
        self.expect('{Game 1 (admin vs. TestPlayer) Game adjourned by agreement} *', t2)
        self.expect('{Game 1 (admin vs. TestPlayer) Game adjourned by agreement} *', t3)

        self.close(t)
        self.close(t3)

        t = self.connect()
        t.write('%s\n%s\n' % ('admin', admin_passwd))
        self.expect('1 player who has an adjourned game with you is online: TestPlayer', t)
        self.expect('Notification: admin, who has an adjourned game with you, has arrived.', t2)

        self.set_nowrap(t)

        t.write('match testplayer 3+0\n')
        self.expect('You have an adjourned game with TestPlayer.  You cannot start a new game until you finish it.', t)

        t.write('match testplayer\n')
        self.expect('Issuing: admin (----) TestPlayer (----) rated blitz 3 4 (adjourned)', t)
        self.expect('Challenge: admin (----) TestPlayer (----) rated blitz 3 4 (adjourned)', t2)
        t2.write('a\n')

        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t)
        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t2)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t2)

        t2.write('e5\n')
        self.expect('P/e7-e5', t)

        # adjourn using the "adjourn" command
        t.write('adj\n')
        self.expect('Requesting to adjourn game 1.', t)
        self.expect('admin requests to adjourn game 1.', t2)
        t2.write('adj\n')
        self.expect('{Game 1 (admin vs. TestPlayer) Game adjourned by agreement} *', t)
        self.expect('{Game 1 (admin vs. TestPlayer) Game adjourned by agreement} *', t2)

        t2.write('match admin\n')
        self.expect('Issuing: TestPlayer (----) admin (----) rated blitz 3 4 (adjourned)', t2)
        self.expect('Challenge: TestPlayer (----) admin (----) rated blitz 3 4 (adjourned)', t)
        t.write('match testplayer\n')
        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t)
        self.expect('Creating: admin (----) TestPlayer (----) rated blitz 3 4', t2)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t)
        self.expect('{Game 1 (admin vs. TestPlayer) Continuing rated blitz match.}', t2)

        t.write('Nb3\n')
        self.expect('N/d4-b3', t2)

        t.write('abo\n')
        t2.write('abo\n')
        self.expect('aborted by agreement', t)

        self.close(t)
        self.close(t2)

    def test_adjourn_guest(self):
        t1 = self.connect_as_admin()
        t2 = self.connect_as_guest()

        t2.write('match admin 3 0\n')
        self.expect('Challenge: ', t1)
        t1.write('a\n')

        self.expect('Creating: ', t1)
        self.expect('Creating: ', t2)

        t1.write('adjourn\n')
        self.expect('All players must be registered to adjourn a game.  Use "abort".', t1)
        t2.write('adjourn\n')
        self.expect('All players must be registered to adjourn a game.  Use "abort".', t2)

        self.close(t1)
        self.close(t2)

class TestNoescape(Test):
    @with_player('TestOne')
    @with_player('TestTwo')
    def test_noescape(self):
        t = self.connect_as('TestOne')
        t2 = self.connect_as('TestTwo')
        t.write('set style 12\n')
        t2.write('set style 12\n')
        t.write('set noescape 1\n')
        self.expect('You will request noescape when games start.', t)
        t2.write('set noescape 1\n')
        self.expect('You will request noescape when games start.', t2)

        t.write('match testtwo 1 0 w\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        self.expect_re('Game \d+: A disconnection will be considered a forfeit.', t)
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        # turning off noescape after the game start shouldn't change
        # anything
        t.write('set noescape\n')
        self.expect('You will not request noescape when games start.', t)

        moves = ['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4', 'Nxd4', 'Nf6',
            'Nc3', 'a6']
        wtm = True
        for mv in moves:
            if wtm:
                t.write('%s\n' % mv)
            else:
                t2.write('%s\n' % mv)
            self.expect('<12> ', t)
            self.expect('<12> ', t2)
            wtm = not wtm

        self.close(t2)

        self.expect_re(r'{Game \d+ \(TestOne vs\. TestTwo\) TestTwo forfeits by disconnection} 1-0', t)

        self.close(t)


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
