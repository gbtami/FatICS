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

from test.test import *

from pgn import Pgn

class TestSuicide(Test):
    def test_suicide(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        self.set_style_12(t)
        self.set_style_12(t2)

        t.write('match GuestEFGH white 5 0 suicide\n')
        self.expect('Issuing:', t)
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t.write('e4\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t2.write('d5\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t.write('e5\n')
        # FICS prints "You must capture." here, but I think it would be
        # more consistent to either print such messages for all
        # variants or for none at all, so currently no reason
        # is printed.
        self.expect('Illegal move (e5).', t)

        self.close(t)
        self.close(t2)

class TestPgn(Test):
    def test_pgn(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        self.set_style_12(t)
        self.set_style_12(t2)

        f = open('../data/sui.pgn', 'r')

        pgn = Pgn(f)
        for g in pgn:
            print('game %s' % g)
            t.write('match GuestEFGH white 5 0 suicide\n')
            self.expect('Issuing:', t)
            self.expect('Challenge:', t2)
            t2.write('accept\n')
            self.expect('<12> ', t)
            self.expect('<12> ', t2)

            wtm = True
            for mv in g.moves:
                if wtm:
                    #print 'sending %s to white' % mv.text
                    t.write('%s%s\n' % (mv.text, mv.decorator))
                else:
                    #print 'sending %s to black' % mv.text
                    t2.write('%s%s\n' % (mv.text, mv.decorator))
                self.expect('<12> ', t)
                self.expect('<12> ', t2)
                wtm = not wtm

            assert(not g.is_draw_nomaterial)
            # there is no checkmate in suicide
            if g.result == '1-0' and g.is_suicide:
                self.expect('wins by losing all material} 1-0', t)
                self.expect('wins by losing all material} 1-0', t2)
            elif g.result == '0-1' and g.is_suicide:
                self.expect('wins by losing all material} 0-1', t)
                self.expect('wins by losing all material} 0-1', t2)
            elif g.is_stalemate:
                if g.result == '1-0':
                    self.expect('wins by having less material (stalemate)} 1-0', t)
                    self.expect('wins by having less material (stalemate)} 1-0', t2)
                elif g.result == '0-1':
                    self.expect('wins by having less material (stalemate)} 0-1', t)
                    self.expect('wins by having less material (stalemate)} 0-1', t2)
                else:
                    self.expect_re('drawn by stalemate \((opposite color bishops|equal material)\)} 1/2-1/2', t)
                    self.expect_re('drawn by stalemate \((opposite color bishops|equal material)\)} 1/2-1/2', t2)
            elif g.result == '1/2-1/2' and g.is_repetition:
                if wtm:
                    t.write('draw\n')
                else:
                    t2.write('draw\n')
                self.expect('drawn by repetition} 1/2-1/2', t)
                self.expect('drawn by repetition} 1/2-1/2', t2)
            elif g.result == '1/2-1/2' and g.is_fifty:
                # this can happen
                random.choice([t, t2]).write('draw\n')
                self.expect('drawn by the 50 move rule} 1/2-1/2', t)
                self.expect('drawn by the 50 move rule} 1/2-1/2', t2)
            else:
                t.write('abort\n')
                t2.write('abort\n')
                # don't depend on the abort message, in case the PGN
                # omits the comment explaining why the game was drawn
                #self.expect('Game aborted', t)
                #self.expect('Game aborted', t2)

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
