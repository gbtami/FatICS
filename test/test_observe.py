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

class TestObserve(Test):
    def test_observe_and_unobserve(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        self.set_style_12(t)
        self.set_style_12(t2)
        self.set_style_12(t3)

        t.write('observe\n')
        self.expect('Usage:', t)
        t.write('unobserve\n')
        self.expect('You are not observing any games', t)

        t.write('observe GuestABCD\n')
        self.expect('GuestABCD is not playing or examining a game', t)

        t.write('unobserve GuestABCD\n')
        self.expect('GuestABCD is not playing or examining a game', t)

        t.write('observe admin\n')
        self.expect('No player named "admin" is online', t)

        t2.write('match guestijkl 1 0 w\n')
        self.expect('Challenge:', t3)
        t3.write('a\n')
        self.expect('Creating:', t2)
        self.expect('Creating:', t3)

        t2.write('o 1\n')
        self.expect('You cannot observe yourself', t2)
        t3.write('o 1\n')
        self.expect('You cannot observe yourself', t3)

        t.write('o Guestijkl\n')
        self.expect('<12>', t)

        t2.write('h4\n')
        self.expect('<12>', t)
        self.expect('P/h2-h4', t)

        t.write('unobserve\n')
        self.expect('Removing game 1 from observation list.', t)
        t.write('unobserve guestefgh\n')
        self.expect('You are not observing game 1', t)

        t.write('o 1\n')
        self.expect('You are now observing game 1.', t)
        self.expect('Game 1: GuestEFGH (++++) GuestIJKL (++++) unrated lightning 1 0', t)
        self.expect('<12> ', t)
        t.write('o guestefgh\n')
        self.expect('You are already observing game 1.', t)

        t.write('unob 1\n')
        self.expect('Removing game 1 from observation list.', t)
        t.write('ob 1\n')
        self.expect('You are now observing game 1.', t)
        self.expect('<12> ', t)
        t.write('unob Guestefgh\n')
        self.expect('Removing game 1 from observation list.', t)
        t.write('ob guestijkl\n')
        self.expect('You are now observing game 1.', t)
        self.expect('<12> ', t)

        t3.write('h5\n')
        self.expect('P/h7-h5', t3)

        t2.write('res\n')
        self.expect('GuestEFGH resigns} 0-1', t)
        self.expect('Removing game 1 from observation list.', t)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_observe_examined(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t2.write('set style 12\n')

        t.write('ex\n')
        self.expect('Starting a game', t)
        t2.write('o guestabcd\n')
        self.expect('You are now observing game 1.', t2)
        self.expect('Game 1: GuestABCD (0) GuestABCD (0) unrated untimed 0 0', t2)
        self.expect('<12> ', t2)

        t.write('e4\n')
        self.expect('<12> rnbqkbnr pppppppp -------- -------- ----P--- -------- PPPP-PPP RNBQKBNR B -1 1 1 1 1 0 1 GuestABCD GuestABCD -2 0 0 39 39 0 0 1 P/e2-e4 (0:00) e4 0 0 0', t2)

        t.write('unex\n')
        self.expect('GuestABCD has stopped examining game 1.', t2)
        self.expect('Game 1 (which you were observing) has no examiners.', t2)
        self.expect('Removing game 1 from observation list.', t2)

        self.close(t)
        self.close(t2)

    def test_unobserve_logout(self):
        """ Test that games are implicitly unobserved when logging out. """
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        t2.write('match guestijkl 1 0 w\n')
        self.expect('Challenge:', t3)
        t3.write('a\n')
        self.expect('Creating:', t2)
        self.expect('Creating:', t3)

        t.write('o guestefgh\n')
        self.expect('You are now observing', t)

        t.write('quit\n')
        self.expect('Removing game 1 from observation list.', t)
        t.close()

        self.close(t2)
        self.close(t3)

    def test_unobserve_multiple(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')
        t4 = self.connect_as_guest('GuestMNOP')
        t5 = self.connect_as_guest()

        t.write('match guestefgh 1+0\n')
        self.expect('Challenge:', t2)
        t2.write('a\n')
        self.expect('Creating:', t)

        t3.write('match guestmnop 15+5 chess960\n')
        self.expect('Challenge:', t4)
        t4.write('a\n')
        self.expect('Creating:', t3)

        t5.write('o guestabcd\n')
        self.expect('You are now observing game 1', t5)
        t5.write('o guestmnop\n')
        self.expect('You are now observing game 2', t5)

        t5.write('unob\n')
        self.expect('Removing game 1 from observation list.', t5)
        self.expect('Removing game 2 from observation list.', t5)

        t.write('abort\n')
        t3.write('abort\n')

        for tt in [t, t2, t3, t4, t5]:
            self.close(tt)

    @with_player('testone')
    @with_player('testtwo')
    @with_player('testthree')
    @with_player('testfour')
    def test_observe_best(self):
        t = self.connect_as_admin()
        t.write('o /z\n')
        self.expect('No suitable star games are in progress.', t)


        t1 = self.connect_as('testone')
        t2 = self.connect_as('testtwo')
        t3 = self.connect_as('testthree')
        t4 = self.connect_as('testfour')
        t5 = self.connect_as_guest('testfive')
        t6 = self.connect_as_guest('testsix')

        t.write('asetrating testone blitz chess 1600 200 .005 100 75 35\n')
        self.expect('Set blitz chess rating for testone.', t)
        t.write('asetrating testtwo blitz chess 1700 200 .005 100 75 35\n')
        self.expect('Set blitz chess rating for testtwo.', t)
        t.write('asetrating testthree blitz chess 1500 200 .005 100 75 35\n')
        self.expect('Set blitz chess rating for testthree.', t)
        t.write('asetrating testfour blitz chess 1900 200 .005 100 75 35\n')
        self.expect('Set blitz chess rating for testfour.', t)

        t1.write('match testtwo 5 0 white\n')
        self.expect('Challenge: ', t2)
        t2.write('a\n')
        self.expect('Creating: ', t1)
        self.expect('Creating: ', t2)

        t3.write('match testfour 5 0 black\n')
        self.expect('Challenge: ', t4)
        t4.write('a\n')
        self.expect('Creating: ', t3)
        self.expect('Creating: ', t4)

        t5.write('match testsix 20 5 crazyhouse white\n')
        self.expect('Challenge: ', t6)
        t6.write('a\n')
        self.expect('Creating: ', t5)
        self.expect('Creating: ', t6)

        t.write('o *\n')
        self.expect('now observing', t)
        self.expect('testfour (1900) testthree (1500)', t)

        t.write('o /b\n')
        self.expect('now observing', t)
        self.expect('testone (1600) testtwo (1700)', t)

        t.write('o *\n')
        self.expect('No suitable star games are in progress.', t)

        t.write('obs /z\n')
        self.expect('testfive (++++) testsix (++++)', t)
        t.write('obs /z\n')
        self.expect('No suitable star games are in progress.', t)

        t1.write('abo\n')
        self.expect('aborted', t2)
        t3.write('abo\n')
        self.expect('aborted', t4)
        t5.write('abo\n')
        self.expect('aborted', t6)


        self.close(t1)
        self.close(t2)
        self.close(t3)
        self.close(t4)
        self.close(t5)
        self.close(t6)

        self.close(t)


class TestFollow(Test):
    def test_follow_examine(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest()

        t2.write('set style 12\n')
        t2.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t2)

        t2.write('foll guestabcd\n')
        self.expect("You are already following GuestABCD's games.", t2)

        t.write('ex\n')
        self.expect('GuestABCD, whom you are following, has started examining a game.', t2)
        self.expect('<12> ', t2)
        t.write('Nf3\n')
        self.expect('GuestABCD moves: Nf3', t2)

        t2.write('follow\n')
        self.expect("You will not follow any player's games.", t2)

        self.close(t)
        self.close(t2)

    def test_follow_play(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest()

        t3.write('set style 12\n')
        t3.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t3)

        t.write('match guestefgh 1+0 u w\n')
        self.expect('Challenge: ', t2)
        t2.write('a\n')

        self.expect("GuestABCD, whom you are following, has started a game with GuestEFGH.", t3)

        t3.write('unfollow\n')
        self.expect("You will not follow any player's games.", t3)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_follow_in_progress(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest()

        t.write('ex\n')
        self.expect('Starting a game', t)
        t.write('Nf3\n')
        self.expect('GuestABCD moves: Nf3', t)

        t2.write('set style 12\n')
        t2.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t2)
        self.expect('<12> ', t2)

        t2.write('o guestabcd\n')
        self.expect("You are already observing ", t2)

        t.write('d5\n')
        self.expect('GuestABCD moves: d5', t2)

        self.close(t)
        self.close(t2)

    def test_follow_logout_1(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest()

        t2.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t2)

        self.close(t)
        self.expect('GuestABCD, whose games you were following, has logged out.', t2)

        t2.write('var\n')
        self.expect('Variable settings of', t2)
        self.expect_not('Following:', t2)
        self.close(t2)

    def test_follow_logout_2(self):
        """ When a player logs out, they should no longer follow. """
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest()

        t2.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t2)

        self.close(t2)

        t.write('e\n')
        self.expect('Starting a game', t)
        # We are really checking that no exception occurs in the
        # server. Previously there was an exception attempting to
        # notify the logged-out player.
        self.close(t)

    def test_follow_observe_self(self):
        """ A player should not try to observe himself or herself
        when starting a game with a player they are following. """
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('follow guestabcd\n')
        self.expect("You will now be following GuestABCD's games.", t2)

        t.write('match guestefgh 1 0 u\n')
        self.expect('Challenge:', t2)
        t2.write('a\n')

        # We are also checking that no exception occurs in the
        # server.

        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        # this should start following, but not observe the current game
        t.write("follow guestefgh\n")
        self.expect("You will now be following GuestEFGH's games.", t)

        self.close(t)
        self.close(t2)

    def test_follow_bad(self):
        t = self.connect_as_guest('GuestABCD')

        t.write('follow\n')
        self.expect("You are not following any player's games.", t)
        t.write('follow admin\n')
        self.expect('No player named "admin" is online.', t)
        t.write('follow 1\n')
        self.expect('You need to specify at least', t)
        t.write('follow 11\n')
        self.expect('"11" is not a valid handle.', t)
        t.write('follow GuestABCD\n')
        self.expect("You can't follow your own games.", t)

        self.close(t)

class TestPfollow(Test):
    def test_pfollow_basics(self):
        t = self.connect_as_guest('GuestABCD')

        t.write('pfollow\n')
        self.expect("You are not following any player's partner's games.", t)
        t.write('pfollow doesnotexist\n')
        self.expect('No player', t)

        t.write('pfollow GuestABCD\n')
        self.expect("You will now be following GuestABCD's partner's games.", t)

        t.write('pfollow GuestABCD\n')
        self.expect("You are already following GuestABCD's partner's games.", t)

        t.write('var\n')
        self.expect("Following: GuestABCD's partner", t)

        t.write('pfollow\n')
        self.expect("You will not follow any player's partner's games.", t)

        t.write('pfollow GuestABCD\n')
        self.expect("You will now be following GuestABCD's partner's games.", t)

        # follow with no arguments cancels pfollow
        t.write('follow\n')
        self.expect("You will not follow any player's games.", t)

        t.write('pfollow GuestABCD\n')
        self.expect("You will now be following GuestABCD's partner's games.", t)

        t2 = self.connect_as_guest('GuestEFGH')
        t.write("follow GuestEFGH\n")
        self.expect("You will no longer be following GuestABCD's partner's games.", t)
        self.expect("You will now be following GuestEFGH's games.", t)

        t.write("pfollow\n")
        self.expect("You are not following any player's partner's games.", t)

        t.write("pfollow GuestABCD\n")
        self.expect("You will no longer be following GuestEFGH's games.", t)
        self.expect("You will now be following GuestABCD's partner's games.", t)
        self.close(t2)

        t.write('quit\n')
        self.expect("GuestABCD, whose partner's games you were following, has logged out.", t)
        t.close()

    def test_pfollow_game(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')
        t4 = self.connect_as_guest('GuestMNOP')
        t5 = self.connect_as_guest()
        self.set_nowrap(t5)
        self.set_style_12(t5)

        t5.write('pfollow guestabc\n')
        self.expect("You will now be following GuestABCD's partner's games.", t5)

        t2.write('set bugopen\n')
        self.expect('You are now open for bughouse.', t2)
        t.write('part guestefgh\n')
        self.expect('GuestABCD offers', t2)
        t2.write('part guestabcd\n')
        self.expect('GuestEFGH accepts', t)

        t4.write('set bugopen\n')
        self.expect('You are now open for bughouse.', t4)
        t3.write('part guestmnop\n')
        self.expect('GuestIJKL offers', t4)
        t4.write('a\n')
        self.expect('GuestMNOP accepts', t3)

        # non-bug game should not be observed
        t2.write('match guestmnop 1+0\n')
        self.expect('Challenge:', t4)
        t4.write('a\n')
        self.expect('Creating:', t4)
        self.expect_not('has started a game', t5)
        t4.write('abort\n')
        self.expect('aborted', t2)

        # pfollowing own partner should basially have no effect
        t.write('pfollow guestefgh\n')
        self.expect("now be following GuestEFGH's partner's games", t)

        # the order in which the linked games are created could
        # matter, so choose randomly
        if random.choice([True, False]):
            t.write('match guestijkl bughouse 3+0 w\n')
            self.expect('Challenge:', t3)
            t3.write('a\n')
        else:
            t2.write('match guestmnop bughouse 3+0 b\n')
            self.expect('Challenge:', t4)
            t4.write('a\n')

        self.expect('Creating: GuestABCD (++++) GuestIJKL', t)
        self.expect('Creating: GuestABCD (++++) GuestIJKL', t3)
        self.expect('Creating: GuestMNOP (++++) GuestEFGH', t2)
        self.expect('Creating: GuestMNOP (++++) GuestEFGH', t4)

        self.expect("GuestABCD's partner, GuestEFGH, whom you are following, has started a game with GuestMNOP.", t5)
        self.expect('GuestMNOP (++++) GuestEFGH (++++) unrated blitz bughouse 3 0', t5)

        t5.write('uno\n')
        self.expect('Removing game', t5)

        t5.write('pfollow guestefgh\n')
        self.expect("You will no longer be following GuestABCD's partner's games.", t5)
        self.expect("You will now be following GuestEFGH's partner's games.", t5)
        self.expect('GuestABCD (++++) GuestIJKL', t5)

        t.write('abo\n')
        self.expect('aborted', t5)

        self.close(t)
        self.close(t2)
        self.close(t3)
        self.close(t4)
        self.close(t5)

class TestAllobservers(Test):
    def test_allobservers(self):
        t = self.connect_as_guest()

        self.expect_command_prints_nothing("allobservers\n", t)
        t.write('allob 1\n')
        self.expect('There is no such game', t)
        t.write('allob nosuchuser\n')
        self.expect('No player named "nosuchuser" is online', t)
        t.write('allob i18n\n')
        self.expect('"i18n" is not a valid handle', t)

        self.close(t)

    def test_allobservers_played(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')
        t4 = self.connect_as_guest('GuestMNOP')

        t2.write('allob guestabcd\n')
        self.expect('GuestABCD is not playing or examining a game', t2)

        t.write('match guestefgh 1 0 w\n')
        self.expect('Challenge:', t2)
        t2.write('a\n')
        self.expect('Creating:', t)
        self.expect('Creating:', t2)

        t3.write('match guestmnop 1 0 w\n')
        self.expect('Challenge:', t4)
        t4.write('a\n')
        self.expect('Creating:', t3)
        self.expect('Creating:', t4)

        self.expect_command_prints_nothing("allobservers\n", t)

        t.write('o 2\n')
        self.expect('now observing', t)
        t3.write('o 1\n')
        self.expect('now observing', t3)
        t.write('allob\n')
        self.expect('Observing 1 [GuestABCD vs. GuestEFGH]: GuestIJKL(U) (1 user)', t)
        self.expect('Observing 2 [GuestIJKL vs. GuestMNOP]: GuestABCD(U) (1 user)', t)
        self.expect('  2 games displayed (of 2 in progress).', t)

        t4.write('o 1\n')
        self.expect('now observing', t4)

        t.write('allob guestefgh\n')
        self.expect('Observing 1 [GuestABCD vs. GuestEFGH]: GuestIJKL(U) GuestMNOP(U) (2 users)', t)
        self.expect('  1 game displayed (of 2 in progress).', t)

        t2.write('allob 1\n')
        self.expect('Observing 1 [GuestABCD vs. GuestEFGH]: GuestIJKL(U) GuestMNOP(U) (2 users)', t2)
        self.expect('  1 game displayed (of 2 in progress).', t2)

        t3.write('unob guestabcd\n')
        self.expect('Removing', t3)
        t4.write('unob 1\n')
        self.expect('Removing', t4)

        # allob should skip games with no observers
        t.write('allob\n')
        self.expect('Observing 2 [GuestIJKL vs. GuestMNOP]: GuestABCD(U) (1 user)', t)
        self.expect('  1 game displayed (of 2 in progress).', t)

        t.write('allob 1\n')
        self.expect('No one is observing game 1.', t)

        self.close(t)
        self.close(t2)
        self.close(t3)
        self.close(t4)

    def test_allobservers_examined(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        t.write('ex\n')
        self.expect('Starting a game', t)

        t.write('ame\n')
        self.expect('Examining 1 (scratch): #GuestABCD(U) (1 user)', t)
        self.expect('  1 game displayed (of 1 in progress).', t)

        t2.write('o guestabcd\n')
        self.expect('now observing', t2)
        t3.write('o guestabcd\n')
        self.expect('now observing', t3)
        t.write('mex guestefgh\n')
        self.expect('GuestABCD has made you an examiner', t2)

        t.write('allob\n')
        self.expect('Examining 1 (scratch): #GuestABCD(U) #GuestEFGH(U) GuestIJKL(U) (3 users)', t)

        self.close(t)
        self.close(t2)
        self.close(t3)


class TestPrimary(Test):
    @with_player('testobs')
    def test_primary(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')
        t4 = self.connect_as_guest('GuestMNOP')
        t5 = self.connect_as('testobs')

        t.write('ex\n')
        self.expect('Starting a game', t)

        t2.write('match guestijkl 2+12\n')
        self.expect('Challenge:', t3)
        t3.write('a\n')
        self.expect('Creating:', t2)

        t4.write('ex\n')
        self.expect('Starting a game', t4)

        t5.write('o 1\n')
        self.expect('now observing game 1', t5)
        t5.write('o 2\n')
        self.expect('now observing game 2', t5)
        t5.write('o 3\n')
        self.expect('now observing game 3', t5)

        t5.write('primary 1\n')
        t5.write('allobs 1\n')
        self.expect('Game 1 is already your primary game.', t5)
        t5.write('primary guestabcd\n')
        self.expect('Game 1 is already your primary game.', t5)

        t5.write('ki kibitz testing 123\n')
        t5.write('allobs 1\n')
        self.expect('kibitz testing 123', t)

        t5.write('pri 3\n')
        self.expect('Game 3 is now your primary game.', t5)
        t5.write('ki kibitz testing 456\n')
        self.expect('kibitz testing 456', t4)

        t5.write('pri guestefgh\n')
        self.expect('Game 2 is now your primary game.', t5)
        t5.write('ki kibitz testing 789\n')
        self.expect('kibitz testing 789', t2)

        t2.write('abort\n')
        self.expect('aborted on move 1', t5)
        t5.write('ki kibitz testing 987\n')
        self.expect('kibitz testing 987', t4)

        #t.write('primary\n') TODO

        t.write('unex\n')
        t4.write('unex\n')

        for tt in [t, t2, t3, t4, t5]:
            self.close(tt)

    def test_primary_bad(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest()

        t2.write('primary\n')
        self.expect('You are not observing any games.', t2)

        t2.write('primary 999\n')
        self.expect('There is no such game.', t2)

        t2.write('primary GuestABCD\n')
        self.expect('GuestABCD is not playing or examining a game.', t2)
        t.write('ex\n')
        self.expect('Starting a game', t)
        t2.write('primary GuestABCD\n')
        self.expect('You are not observing game', t2)

        self.close(t)
        self.close(t2)

class TestRobserve(Test):
    @with_player('tdplayer', ['td'])
    def test_robserve(self):
        t = self.connect_as('tdplayer')
        t2 = self.connect_as_guest('GuestABCD')
        t3 = self.connect_as_guest('GuestEFGH')

        t2.write('ex\n')
        self.expect('Starting a game', t2)

        t3.write('robserve tdplayer 1\n')
        self.expect('Only TD programs', t3)

        t.write('robserve GuestEFGH 1\n')
        self.expect('You are now observing game 1.', t3)
        t3.write('unob\n')
        self.expect('Removing game 1', t3)

        t.write('rob GuestEFGH GuestABCD\n')
        self.expect('You are now observing game 1.', t3)

        self.close(t)
        self.close(t2)
        self.close(t3)

class TestGames(Test):
    def test_games(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        t.write('games\n')
        self.expect('There are no games in progress', t)

        t.write('match guestefgh white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: GuestABCD (++++) GuestEFGH (++++) unrated lightning 1 0', t)
        self.expect('Creating: GuestABCD (++++) GuestEFGH (++++) unrated lightning 1 0', t2)

        t3.write('e\n')
        self.expect('Starting a game', t3)
        t3.write('games\n')
        # these are not exactly correct but rather what the server outputs now
        self.expect('  1 ++++ GuestABCD   ++++ GuestEFGH  [ lu  1   0]  0:00 -  0:00 (39-39) B:  1', t3)
        self.expect('  2 (Exam.    0 White          0 Black     ) [ uu  0   0] B:  1', t3)
        self.expect ('  2 games displayed (of   2 in progress).', t3)

        t.write('game 1\n')
        self.expect('  1 ++++ GuestABCD   ++++ GuestEFGH  [ lu  1   0]  0:00 -  0:00 (39-39) B:  1', t)
        self.expect ('  1 game displayed (of   2 in progress).', t)

        t.write('abort\n')
        self.expect('aborted', t2)

        self.close(t)
        self.close(t2)
        self.close(t3)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
