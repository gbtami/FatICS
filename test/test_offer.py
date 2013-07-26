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

class TestNotPlaying(Test):
    def test_not_playing(self):
        t = self.connect_as_guest()

        t.write('draw\n')
        self.expect('You are not playing a game.', t)

        t.write('abort\n')
        self.expect('You are not playing a game.', t)

        t.write('resign\n')
        self.expect('You are not playing a game.', t)

        t.write('accept\n')
        self.expect('There are no offers to accept.', t)

        t.write('decline\n')
        self.expect('There are no offers to decline.', t)

        t.write('withdraw\n')
        self.expect('There are no offers to withdraw.', t)

        t.write('accept 99\n')
        self.expect('There is no offer 99 to accept.', t)

        t.write('decline 99\n')
        self.expect('There is no offer 99 to decline.', t)

        t.write('withdraw 99\n')
        self.expect('There is no offer 99 to withdraw.', t)

        self.close(t)

class TestAbort(Test):
    def test_abort_ply_0(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('abort\n')
        self.expect('Game aborted on move 1 by Guest', t)
        self.expect('Game aborted on move 1 by Guest', t2)

        self.close(t)
        self.close(t2)

    def test_abort_ply_1(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()

        t2.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('abort\n')
        self.expect('Game aborted on move 1 by admin', t)
        self.expect('Game aborted on move 1 by admin', t2)

        self.close(t)
        self.close(t2)

    def test_abort_agreement(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t)
        t.write('abort\n')

        self.expect('Requesting to abort game 1', t)
        self.expect('GuestABCD requests to abort game 1', t2)

        t.write('abort\n')
        self.expect('You are already offering to abort game 1', t)

        t2.write('abort\n')
        self.expect('Game aborted by agreement', t)
        self.expect('Game aborted by agreement', t2)

        self.close(t)
        self.close(t2)

    def test_abort_decline(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('set style 12\n')
        t2.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t)
        t.write('abort\n')

        self.expect('GuestABCD requests to abort game 1', t2)

        t2.write('decline\n')
        self.expect('Declining the abort request from GuestABCD.', t2)
        self.expect('admin declines your abort request.', t)

        t.write('resign\n')
        self.expect('GuestABCD resigns} 0-1', t)
        self.expect('GuestABCD resigns} 0-1', t2)

        t2.write('aclearhist admin\n')

        self.close(t)
        self.close(t2)

    def test_abort_autodecline(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t2.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t2)
        t2.write('abort\n')

        self.expect('admin requests to abort game 1', t)

        t.write('f4\n')
        self.expect('Declining the abort request from admin.', t)
        self.expect('GuestABCD declines your abort request.', t2)

        self.close(t)
        self.close(t2)

    def test_abort_accept(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('set style 12\n')
        t2.write('set style 12\n')
        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)
        t2.write('e5\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)
        t.write('abort\n')

        self.expect('GuestABCD requests to abort game 1', t2)

        t2.write('accept\n')
        self.expect('Accepting the abort request from GuestABCD.', t2)
        self.expect('admin accepts your abort request.', t)
        self.expect('Game aborted by agreement', t)
        self.expect('Game aborted by agreement', t2)

        self.close(t)
        self.close(t2)

    def test_abort_withdraw(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t)
        t.write('abort\n')

        self.expect('GuestABCD requests to abort game 1', t2)

        t.write('withdraw\n')
        self.expect('Withdrawing your abort request to admin.', t)
        self.expect('GuestABCD withdraws the abort request.', t2)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_observer_sees_abort(self):
        t = self.connect_as('testplayer')
        t2 = self.connect_as_admin()
        t3 = self.connect_as_guest()

        t.write('set style 12\n')

        t.write('match admin white 1+0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t3.write('obs admin\n')
        self.expect('Game 1: TestPlayer (----) admin (----) rated lightning 1 0', t3)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t)

        t2.write('abo\n')
        self.expect('admin requests to abort game 1.', t)
        self.expect('admin requests to abort game 1.', t3)
        t.write('f4\n')
        self.expect('TestPlayer declines your abort request.', t2)
        self.expect('TestPlayer declines the abort request.', t3)

        t.write('abo\n')
        self.expect('TestPlayer requests to abort game 1.', t3)
        t2.write('abo\n')
        self.expect('admin accepts your abort request.', t)
        self.expect('admin accepts the abort request.', t3)
        self.expect('aborted by agreement} *', t)
        self.expect('aborted by agreement} *', t2)
        self.expect('aborted by agreement} *', t3)

        self.close(t)
        self.close(t2)
        self.close(t3)

class TestDraw(Test):
    def test_agree_draw(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('draw\n')
        self.expect('Offering a draw', t)
        self.expect('GuestABCD offers you a draw', t2)

        t2.write('draw\n')
        self.expect('admin accepts your draw offer', t)
        self.expect('{Game 1 (GuestABCD vs. admin) Game drawn by agreement} 1/2-1/2', t)
        self.expect('{Game 1 (GuestABCD vs. admin) Game drawn by agreement} 1/2-1/2', t2)

        self.close(t)
        self.close(t2)

    def test_draw_accept(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('draw\n')
        self.expect('Offering a draw', t)
        self.expect('GuestABCD offers you a draw', t2)

        t2.write('accept\n')
        self.expect('admin accepts your draw offer', t)
        self.expect('{Game 1 (GuestABCD vs. admin) Game drawn by agreement} 1/2-1/2', t)
        self.expect('{Game 1 (GuestABCD vs. admin) Game drawn by agreement} 1/2-1/2', t2)

        self.close(t)
        self.close(t2)

    def test_draw_decline(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('draw\n')
        self.expect('GuestABCD offers you a draw', t2)
        t2.write('decl\n')

        self.expect('Declining the draw offer', t2)
        self.expect('admin declines your draw offer', t)

        self.close(t)
        self.close(t2)

    def test_draw_autodecline(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t2.write('set style 12\n')

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('e5\n')
        self.expect('P/e7-e5', t2)
        t2.write('draw\n')
        self.expect('admin offers you a draw', t)

        t.write('f4\n')
        self.expect('Declining the draw offer from admin', t)
        self.expect('GuestABCD declines your draw offer', t2)

        t.write('draw\n')
        self.expect('GuestABCD offers you a draw', t2)
        t2.write('exf4\n')
        self.expect('Declining the draw offer from GuestABCD', t2)
        self.expect('admin declines your draw offer', t)

        self.close(t)
        self.close(t2)

    def test_withdraw_draw(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('draw\n')
        self.expect('GuestABCD offers you a draw', t2)
        t.write('withdraw\n')

        self.expect('You cannot withdraw a draw offer', t)

        self.close(t)
        self.close(t2)

    def test_cancel_draw(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t.write('draw\n')
        self.expect('GuestABCD offers you a draw', t2)

        t2.write('resign\n')
        t2.write('accept\n')

        self.expect('There are no offers to accept.', t2)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_observer_sees_draw(self):
        t = self.connect_as('testplayer')
        t2 = self.connect_as_admin()
        t3 = self.connect_as_guest()

        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t3.write('obs admin\n')
        self.expect('Game 1: TestPlayer (----) admin (----) rated lightning 1 0', t3)

        t2.write('draw\n')
        self.expect('admin offers you a draw.', t)
        self.expect('Game 1: admin offers a draw.', t3)
        t.write('e4\n')
        self.expect('TestPlayer declines your draw offer.', t2)
        self.expect('Game 1: TestPlayer declines the draw offer.', t3)

        t.write('draw\n')
        self.expect('Game 1: TestPlayer offers a draw.', t3)
        t2.write('draw\n')
        self.expect('admin accepts your draw offer.', t)
        self.expect('\nGame 1: admin accepts the draw offer.', t3)
        self.expect('drawn by agreement} 1/2-1/2', t3)

        t2.write('asetrating admin lightning chess 0 0 0 0 0 0\n')
        self.expect('Cleared lightning chess rating for admin.\r\n', t2)

        self.close(t)
        self.close(t2)
        self.close(t3)

class TestPendinfo(Test):
    def test_pendinfo(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t.write('iset pendinfo 1\n')
        t2.write('iset pendinfo 1\n')

        self.set_style_12(t)
        self.set_style_12(t2)

        t.write('match guestefgh 1 0 w\n')
        self.expect('Issuing:', t)
        m = self.expect_re('<pt> (\d+) w=GuestEFGH t=match p=GuestABCD .* \[white\] GuestEFGH .* unrated lightning 1 0', t)
        num = int(m.group(1))
        self.expect('Challenge:', t2)
        self.expect('<pf> %d w=GuestABCD t=match p=GuestABCD (++++) [white] GuestEFGH (++++) unrated lightning 1 0' % num, t2)

        t.write('accept %d\n' % num)
        self.expect('There is no offer', t)
        t2.write('accept %d\n' % num)
        self.expect('Accepting the match offer', t2)
        self.expect('<pr> %d\r\n' % num, t2)
        self.expect('Creating:', t2)
        self.expect('accepts your match offer', t)
        self.expect('<pr> %d\r\n' % num, t)
        self.expect('Creating:', t)

        t.write('draw\n')
        self.expect('Offering a draw', t)
        m = self.expect_re('<pt> (\d+) w=GuestEFGH t=draw p=#', t)
        num = int(m.group(1))
        self.expect('GuestABCD offers you a draw.', t2)
        self.expect('<pf> %d w=GuestABCD t=draw p=#' % num, t2)

        t2.write('decl %d\n' % num)
        self.expect('declines', t)
        self.expect('\n<pr> %d\r\n' % num, t)
        self.expect('Declining', t2)
        self.expect('\n<pr> %d\r\n' % num, t2)

        t.write('e4\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)
        t2.write('c5\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t2.write('abo\n')
        self.expect('Requesting to abort', t2)
        m = self.expect_re('<pt> (\d+) w=GuestABCD t=abort p=#', t2)
        num = int(m.group(1))
        self.expect('GuestEFGH requests', t)
        self.expect('<pf> %d w=GuestEFGH t=abort p=#' % num, t)

        t2.write('withdraw %d\n' % num)
        self.expect('Withdrawing', t2)
        self.expect('<pr> %d\r\n' % num, t2)
        self.expect('GuestEFGH withdraws', t)
        self.expect('<pr> %d\r\n' % num, t)

        t.write('abo\n')
        t2.write('abo\n')

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent

