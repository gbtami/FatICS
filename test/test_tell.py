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

class TellTest(Test):
    def test_tell(self):
        t = self.connect_as_admin()
        t.write('tell admin Hello there!\n')
        self.expect('admin(*) tells you: Hello there!', t, "tell self")

        t.write('tell admin \t  space  test\t  \n')
        self.expect('tells you:       space  test\r\n', t)

        t2 = self.connect_as_guest()
        t2.write('tell admin Guest tell\n')
        self.expect('(U) tells you: Guest tell', t, 'guest tell')
        self.close(t2)

        self.close(t)

    def test_tell_block_guests(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()

        t.write('set tell 0\n')
        self.expect('You will not hear direct tells from unregistered users.', t)
        t2.write('tell admin Hello there!\n')
        self.expect('''Player "admin" isn't listening to unregistered users' tells.''', t2)

        t.write('set tell 1\n')
        self.expect('You will now hear direct tells from unregistered users.', t)
        t2.write('tell admin test 2\n')
        self.expect('tells you: test 2', t)

        self.close(t)
        self.close(t2)


    def test_bad_tell(self):
        t = self.connect_as_guest()
        t.write('tell nonexistentname foo\n')
        self.expect('No player named "nonexistentname"', t)

        t.write('tell admin foo bar\n')
        self.expect('No player named "admin" is online', t)

        t.write('tell admin1 too baz\n')
        self.expect('not a valid handle', t)

        self.close(t)

    @with_player('aduser')
    def test_ambiguous_tell(self):
        t = self.connect_as('aduser')
        t2 = self.connect_as_guest()

        # not ambiguous when admin is offline
        t2.write('tell ad blah blah\n')
        self.expect('tells you: blah blah', t)
        self.expect('(told aduser)', t2)

        t3 = self.connect_as_admin()
        t2.write('tell a blah blah\n')
        self.expect('You need to specify at least', t2)

        t2.write('tell ad blah blah\n')
        self.expect('Ambiguous name', t2)

        self.close(t)
        self.close(t3)

        t2.write('tell ad blah blah\n')
        self.expect('No player named "ad" is online', t2)

        self.close(t2)

    def test_tell_idle(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()
        t.write('asetidle admin 3\n')
        self.expect('set to 180', t)
        t2.write('tell admin hello\n')
        self.expect('(told admin, who has been idle 3 mins)', t2)
        self.close(t2)
        self.close(t)

    def test_tell_disconnected(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()

        t2.write('t admin hello there\n')
        self.expect('hello there', t)
        self.close(t)

        t2.write('. where are you?\n')
        self.expect('admin is no longer online', t2)

        t = self.connect_as_admin()
        t2.write('. why hello again\n')
        self.expect('tells you: why hello again', t)

        self.close(t)
        self.close(t2)

    def test_told(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t.write('ex\n')
        self.expect('Starting a game', t)
        t2.write('t guestabcd woohoo\n')
        self.expect('(told GuestABCD, who is examining a game)', t2)
        self.close(t)
        self.close(t2)

class QtellTest(Test):
    @with_player('tdplayer', ['td'])
    def test_qtell(self):
        t = self.connect_as('tdplayer')
        t.write('qtell nonexistentname test\n')
        self.expect('*qtell nonexistentname 1*', t)

        t.write('qtell admin test\n')
        self.expect('*qtell admin 1*', t)

        t2 = self.connect_as_admin()
        t.write('qtell admin simple test\n')
        self.expect(':simple test', t2)
        self.expect('*qtell admin 0*', t)

        t.write('qtell admin \\bthis\\nis a \\Hmore complicated\\h test\n')
        self.expect(':\x07this', t2)
        self.expect(':is a \x1b[7mmore complicated\x1b[0m test', t2)
        self.expect('*qtell admin 0*', t)

        t2.write('qtell tdplayer test\n')
        self.expect('Only TD programs are allowed to use this command', t2)


        t2.write('+ch 55\n')
        self.expect('added', t2)
        t.write('qtell -1 hello world\n')
        self.expect('*qtell -1 1*', t)
        t.write('qtell 55 !!! ###\n')
        self.expect('*qtell 55 0*', t)
        self.expect('!!! ###', t2)
        t2.write('-ch 55\n')
        self.expect('removed', t2)

        self.close(t2)
        self.close(t)

class SayTest(Test):
    @with_player('testplayer')
    def test_say(self):
        t = self.connect_as('testplayer')
        t2 = self.connect_as_admin()

        self.set_style_12(t)
        self.set_style_12(t2)

        t.write('say hello\n')
        self.expect("I don't know", t)

        t.write('match admin white 1 0 u\n')
        self.expect('Issuing:', t)
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('<12> ', t)
        self.expect('<12> ', t2)

        t.write('say Hello!\n')
        self.expect('testplayer[1] says: Hello!\r\n', t2)
        self.expect('(told admin, who is playing)', t)

        t2.write('say hi\n')
        self.expect('admin(*)[1] says: hi\r\n', t)
        self.expect('(told testplayer, who is playing)', t2)

        t.write('e4\n')
        self.expect('P/e2-e4', t2)
        t2.write('c5\n')
        self.expect('P/c7-c5', t)

        t.write('resign\n')
        self.expect('testplayer resigns', t)
        self.expect('testplayer resigns', t2)

        t.write('say gg\n')
        self.expect('testplayer says: gg', t2)
        t2.write('say thanks\n')
        self.expect('admin(*) says: thanks', t)

        self.close(t)

        t2.write('say bye\n')
        self.expect('testplayer is no longer online.', t2)

        t = self.connect_as('testplayer')
        t2.write('say yo\n')
        self.expect('admin(*) says: yo', t)
        self.expect('(told testplayer)', t2)

        self.close(t)
        self.close(t2)

class SilenceVarTest(Test):
    @with_player('TestPlayer')
    def test_silence_var(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')

        t2.write('set silence 1\n')
        self.expect('You will now play games in silence.', t2)

        t.write('f testplayer\n')
        self.expect('TestPlayer is in silence mode.', t)

        t.write('+ch 5\n')
        self.expect('[5] added to your channel list.', t)
        t2.write('+ch 5\n')
        self.expect('[5] added to your channel list.', t2)

        t.write('t 5 Test 1; please ignore\n')
        self.expect('Test 1', t2)

        # playing a game
        t.write('match testplayer white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        t.write('t 5 Test 2; please ignore\n')
        self.expect_not('Test 2', t2)
        t.write('abort\n')
        self.expect('Game aborted', t)
        self.expect('Game aborted', t2)

        # examining a game
        t2.write('ex\n')
        self.expect('examine (scratch) mode', t2)
        t.write('t 5 Test 3; please ignore\n')
        self.expect_not('Test 3', t2)
        t2.write('unex\n')
        self.expect('You are no longer examining', t2)

        # observing a game
        t3 = self.connect_as_guest('GuestABCD')
        t.write('match guestabcd white 1 0\n')
        self.expect('Challenge:', t3)
        t3.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t3)
        t2.write('o 1\n')
        self.expect('now observing game 1', t2)
        t.write('t 5 test 4\n')
        self.expect_not('test 4', t2)
        t.write('abort\n')
        self.expect('Game aborted', t)
        self.expect('Game aborted', t2)
        self.expect('Game aborted', t3)
        self.close(t3)

        # shouts
        t2.write('ex\n')
        self.expect('examine (scratch) mode', t2)
        t.write('shout Test 5 please ignore\n')
        self.expect_not('Test 5', t2)

        # c-shouts
        t.write('cshout Test 6 please ignore\n')
        self.expect_not('Test 6', t2)

        # inchannel
        t.write('in 5\n')
        self.expect('{TestPlayer}', t)
        t2.write('unex\n')
        self.expect('You are no longer examining', t2)

        t.write('t 5 Test 7; please ignore\n')
        self.expect('Test 7; please ignore', t2)

        t.write('-ch 5\n')
        self.expect('[5] removed from your channel list.', t)
        t2.write('-ch 5\n')
        self.expect('[5] removed from your channel list.', t2)

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
