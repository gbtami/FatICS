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

class TestBugwho(Test):
    def test_bugwho_none(self):
        t = self.connect_as_guest()

        t.write('bugwho foo\n')
        self.expect('Usage:', t)

        t.write('bugwho g\n')
        self.expect('Bughouse games in progress', t)
        self.expect_re(r'\d+ games displayed\.', t)

        t.write('bugwho p\n')
        self.expect('Partnerships not playing bughouse', t)
        self.expect_re(r'\d+ partnerships? displayed\.', t)

        t.write('bugwho u\n')
        self.expect('Unpartnered players with bugopen on', t)
        self.expect_re(r'\d+ players? displayed \(of \d+\)\.', t)

        t.write('bu gp\n')
        self.expect('Bughouse games in progress', t)
        self.expect('Partnerships not playing bughouse', t)

        t.write('bugwho\n')
        self.expect('Bughouse games in progress', t)
        self.expect('Partnerships not playing bughouse', t)
        self.expect('Unpartnered players with bugopen on', t)
        self.close(t)

    def test_bugwho(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')
        t4 = self.connect_as_guest('GuestMNOP')

        t.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t)
        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)
        t3.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t3)
        t4.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t4)

        t.write('part guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner; type "partner GuestABCD"', t2)
        t2.write('a\n')
        self.expect('GuestEFGH accepts', t)

        t.write('bugwho\n')
        self.expect('Bughouse games in progress', t)
        self.expect_re(r'\d+ games? displayed\.', t)
        self.expect('Partnerships not playing bughouse', t)
        self.expect('++++ GuestABCD(U) / ++++ GuestEFGH(U)', t)
        self.expect_re(r'\d+ partnerships? displayed.', t)
        self.expect('Unpartnered players with bugopen on', t)
        self.expect('++++ GuestIJKL(U)', t)
        self.expect('++++ GuestMNOP(U)', t)
        self.expect_re(r'\d+ players? displayed \(of \d+\)\.', t)

        self.close(t)
        self.close(t2)
        self.close(t3)
        self.close(t4)

class TestPartner(Test):
    def test_bugopen(self):
        t = self.connect_as_guest('GuestABCD')
        t.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t)
        t.write('set bugopen 0\n')
        self.expect('You are not open for bughouse.', t)

        t2 = self.connect_as_guest('GuestEFGH')
        t2.write('set bugopen\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('Setting you open for bughouse.', t)
        self.expect('offers to be your bughouse partner', t2)

        t.write('wi\n')
        self.expect('GuestABCD withdraws the partnership request.', t2)

        t.write('partner guestefgh\n')
        self.expect('offers to be your bughouse partner', t2)
        t2.write('a\n')
        self.expect('GuestEFGH agrees to be your partner', t)
        # end partnership by setting bugopen 0
        t2.write('set bugopen 0\n')
        # On original fics, the order of the next two messages is reversed.
        self.expect('You are not open for bughouse.', t2)
        self.expect('You no longer have a bughouse partner.', t2)
        self.expect('Your partner has ended partnership', t)

        t.write('set bugopen\n')
        self.expect('You are not open for bughouse.', t)

        self.close(t)
        self.close(t2)

    def test_partner(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t.write('partner\n')
        self.expect('You do not have a bughouse partner.', t)

        t.write("partner guestefgh\n")
        self.expect('GuestEFGH is not open for bughouse.', t)

        t2.write('set bugopen\n')
        self.expect('You are now open for bughouse.', t2)

        t.write("partner guestefgh\n")
        self.expect("Making a partnership offer to GuestEFGH.", t)
        self.expect("GuestABCD offers to be your bughouse partner", t2)

        t.write("partner guestefgh\n")
        self.expect("You are already offering to be GuestEFGH's partner.", t)

        t2.write('a\n')
        self.expect("GuestEFGH accepts your partnership request.", t)
        self.expect("Accepting the partnership request from GuestABCD.", t2)

        self.expect("GuestEFGH agrees to be your partner.", t)
        self.expect("You agree to be GuestABCD's partner.", t2)

        t2.write('open\n')
        self.expect('Your partner has become unavailable for matches.', t)
        t2.write('open\n')
        self.expect('Your partner has become available for matches.', t)

        t.write("ptell Hello 1\n")
        self.expect("GuestABCD(U) (your partner) tells you: Hello 1", t2)
        self.expect("(told GuestEFGH)", t)
        t2.write("ptell Hello 2\n")
        self.expect("GuestEFGH(U) (your partner) tells you: Hello 2", t)
        self.expect("(told GuestABCD)", t2)

        t.write('bugwho p\n')
        self.expect('1 partnership displayed.', t)

        t.write('var\n')
        self.expect('Bughouse partner: GuestEFGH\r\n', t)
        t.write('var guestefgh\n')
        self.expect('Bughouse partner: GuestABCD\r\n', t)

        t.write("partner guestefgh\n")
        self.expect("You are already GuestEFGH's bughouse partner.", t)

        t3 = self.connect_as_guest('GuestIJKL')
        t3.write('partner guestefgh\n')
        self.expect('GuestEFGH already has a partner.', t3)
        self.close(t3)

        t.write('partner\n')
        self.expect('You no longer have a bughouse partner.', t)
        self.expect('Your partner has ended partnership.', t2)
        self.expect('You no longer have a bughouse partner.', t2)

        t.write('bugwho p\n')
        self.expect('0 partnerships displayed.', t)

        self.close(t)
        self.close(t2)

    def test_partner_decline(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t2.write('decl\n')
        self.expect('Declining the partnership request from GuestABCD.', t2)
        self.expect('GuestEFGH declines your partnership request.', t)

        self.close(t)
        self.close(t2)

    def test_partner_withdraw(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t.write('wi\n')
        self.expect('Withdrawing your partnership request to GuestEFGH.', t)
        self.expect('GuestABCD withdraws the partnership request.', t2)

        t2.write('decl\n')
        self.expect('There are no offers to decline.', t2)

        self.close(t)
        self.close(t2)

    def test_partner_decline_logout(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)

        t2.write('quit\n')
        self.expect('Partnership offer from GuestABCD removed.', t2)
        self.expect('GuestEFGH, whom you were offering a partnership with, has departed.', t)
        t2.close()

        self.close(t)

    def test_partner_withdraw_logout(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)

        t.write('quit\n')
        self.expect('Partnership offer to GuestEFGH withdrawn.', t)
        self.expect('GuestABCD, who was offering a partnership with you, has departed.', t2)
        t.close()

        self.close(t2)

    def test_end_partnership_bugopen(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)

        t2.write('a\n')
        self.expect('agrees to be your partner', t)

        t.write('set bugopen\n')
        # On original fics, the order of the next two messages is reversed
        self.expect('You are not open for bughouse.', t)
        self.expect('You no longer have a bughouse partner.', t)
        self.expect('Your partner has become unavailable for bughouse.', t2)
        self.expect('Your partner has ended partnership.', t2)
        self.expect('You no longer have a bughouse partner.', t2)

        self.close(t)
        self.close(t2)

    def test_partner_withdraw_bugopen(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)

        t.write('set bugopen\n')
        # On original fics, the order of the next two messages is reversed
        self.expect('You are not open for bughouse.', t)
        self.expect('Partnership offer to GuestEFGH withdrawn.', t)
        self.expect('GuestABCD, who was offering a partnership with you, has become', t2)
        self.expect('Partnership offer from GuestABCD removed.', t2)

        t2.write('a\n')
        self.expect('There are no offers to accept.', t2)

        self.close(t)
        self.close(t2)

    def test_partner_decline_bugopen(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)

        t2.write('set bugopen\n')
        # On original fics, the order of the next two messages is reversed
        self.expect('You are not open for bughouse.', t2)
        self.expect('Partnership offer from GuestABCD removed.', t2)
        self.expect('GuestEFGH, whom you were offering a partnership with, has become', t)
        self.expect('Partnership offer to GuestEFGH withdrawn.', t)

        t.write('a\n')
        self.expect('There are no offers to accept.', t)

        self.close(t)
        self.close(t2)

    def test_partner_decline_other_partner(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        self.set_nowrap(t)
        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)
        t3.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t3)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t2.write('part guestijkl\n')
        self.expect('GuestEFGH offers to be your bughouse partner', t3)

        t3.write('a\n')
        self.expect('GuestEFGH, whom you were offering a partnership with, has accepted a partnership with GuestIJKL.', t)
        t.write('wi\n')
        self.expect('There are no offers to withdraw.', t)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_partner_withdraw_other_partner(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')
        t3 = self.connect_as_guest('GuestIJKL')

        self.set_nowrap(t2)
        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)
        t3.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t3)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t.write('part guestijkl\n')
        self.expect('GuestABCD offers to be your bughouse partner', t3)

        t3.write('a\n')
        self.expect('GuestABCD, who was offering a partnership with you, has accepted a partnership with GuestIJKL.', t2)
        t2.write('a\n')
        self.expect('There are no offers to accept.', t2)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_partner_leave(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t2.write('partner guestabcd\n')
        self.expect('Accepting the partnership request from GuestABCD.', t2)
        self.expect('GuestEFGH accepts your partnership request.', t)
        self.expect("GuestEFGH agrees to be your partner.", t)
        self.expect("You agree to be GuestABCD's partner.", t2)

        self.close(t)
        self.expect('Your partner, GuestABCD, has departed.', t2)

        t2.write('part\n')
        self.expect('You do not have a bughouse partner.', t2)

        self.close(t2)

    def test_partner_dump(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t.write('partner guestefgh\n')
        self.expect('GuestABCD offers to be your bughouse partner', t2)
        t2.write('partner guestabcd\n')
        self.expect('Accepting the partnership request from GuestABCD.', t2)
        self.expect('GuestEFGH accepts your partnership request.', t)
        self.expect("GuestEFGH agrees to be your partner.", t)
        self.expect("You agree to be GuestABCD's partner.", t2)

        t3 = self.connect_as_guest('GuestIJKL')
        t3.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t3)

        t.write('part guestijkl\n')
        self.expect('GuestABCD offers to be your bughouse partner', t3)
        t3.write('a\n')
        self.expect('Your partner has accepted a partnership with GuestIJKL.', t2)
        self.expect('You no longer have a bughouse partner.', t2)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_partner_bad(self):
        t = self.connect_as_guest('GuestABCD')
        t.write('part Guestabcd\n')
        self.expect("You can't be your own bughouse partner.", t)
        t.write('partner nosuchuser\n')
        self.expect('No player named "nosuchuser" is online.', t)
        t.write('ptell test\n')
        self.expect('You do not have a partner at present.', t)
        self.close(t)

    def test_partner_censor(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_guest('GuestEFGH')

        t2.write('set bugopen 1\n')
        self.expect('You are now open for bughouse.', t2)

        t2.write('+cen guestabcd\n')
        self.expect('GuestABCD added to your censor list.', t2)

        t.write('part guestefgh\n')
        self.expect('GuestEFGH is censoring you.', t)

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
