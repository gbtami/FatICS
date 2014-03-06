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

class TestTakeback(Test):
    def test_takeback_not_playing(self):
        t = self.connect_as_guest()
        t.write('takeback\n')
        self.expect('You are not playing a game.', t)
        t.write('e\n')
        self.expect('Starting a game', t)
        t.write('takeback 1\n')
        self.expect('You are not playing a game.', t)
        self.close(t)

    def test_takeback(self):
        # TODO: check that an observer sees the correct
        # messages

        t1 = self.connect_as_guest('GuestOne')
        t2 = self.connect_as_guest('GuestTwo')

        self.set_style_12(t1)
        self.set_style_12(t2)

        t1.write('match guesttwo 3 0 u white\n')
        self.expect('Challenge: ', t2)
        t2.write('a\n')
        self.expect('Creating: ', t1)
        self.expect('Creating: ', t2)

        t1.write('takeback\n')
        self.expect('There are no moves in your game.', t1)
        t2.write('takeback 2\n')
        self.expect('There are no moves in your game.', t2)

        t1.write('c4\n')
        self.expect('<12> ', t1)
        self.expect('<12> ', t2)
        t1.write('takeback 2\n')
        self.expect('There is only 1 half-move in your game.', t1)
        t2.write('e5\n')
        self.expect('<12> ', t1)
        self.expect('<12> ', t2)
        t2.write('takeback 3\n')
        self.expect('There are only 2 half-moves in your game.', t2)

        t1.write('Nc3\n')
        self.expect('<12> ', t1)
        self.expect('<12> ', t2)

        t2.write('Nc6\n')
        self.expect('<12> ', t1)
        self.expect('<12> ', t2)

        t2.write('set notakeback\n')
        self.expect('You will not allow takebacks.', t2)
        t1.write('takeback\n')
        self.expect('Your opponent has requested no takebacks.', t1)
        t2.write('set notakeback 0\n')
        self.expect('You will now allow takebacks.', t2)

        t1.write('takeback\n')
        self.expect('Takeback request sent.', t1)
        self.expect('GuestOne would like to take back 1 half-move(s).', t2)

        t1.write('takeback\n')
        self.expect('You are already offering to takeback the last 1 half-move(s).', t1)

        t1.write('takeback 3\n')
        self.expect('Updated takeback request sent.', t1)
        self.expect('Updated takeback request received.', t2)
        self.expect('GuestOne would like to take back 3 half-move(s).', t2)

        t2.write('takeback 1\n')
        self.expect('You disagree on the number of half-moves to take back.', t2)
        self.expect('Alternate takeback request sent.', t2)
        self.expect('GuestTwo proposes a different number (1) of half-move(s).', t1)

        t1.write('a\n')
        self.expect('Accepting the takeback request from GuestTwo', t1)
        self.expect('GuestOne accepts your takeback request.', t2)
        self.expect_re('<12> rnbqkbnr pppp-ppp -------- ----p--- --P----- --N----- PP-PPPPP R-BQKBNR B -1 1 1 1 1 1 (\d+) GuestOne GuestTwo -1 3 0 39 39 \d+ \d+ 2 N/b1-c3 \(0:00\) Nc3 0 1 0', t1)
        self.expect_re('<12> rnbqkbnr pppp-ppp -------- ----p--- --P----- --N----- PP-PPPPP R-BQKBNR B -1 1 1 1 1 1 (\d+) GuestOne GuestTwo 1 3 0 39 39 \d+ \d+ 2 N/b1-c3 \(0:00\) Nc3 1 1 0', t2)

        t2.write('takeback 3\n')
        self.expect('GuestTwo would like to take back 3 half-move(s).', t1)
        t1.write('takeback 3\n')
        self.expect('Accepting the takeback request from GuestTwo', t1)
        self.expect_re('<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 (\d+) GuestOne GuestTwo 1 3 0 39 39 \d+ \d+ 1 none \(0:00\) none 0 0 0', t1)
        self.expect_re('<12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 (\d+) GuestOne GuestTwo -1 3 0 39 39 \d+ \d+ 1 none \(0:00\) none 1 0 0', t2)

        self.close(t1)
        self.close(t2)


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
