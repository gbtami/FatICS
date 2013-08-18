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

from offer import Offer

import global_


class Partner(Offer):
    def __init__(self, a, b):
        Offer.__init__(self, 'partnership request')

        # check for existing offers
        a_sent = a.session.offers_sent
        b_sent = b.session.offers_sent
        o = next((o for o in b_sent if o.name == self.name and
            o.b == a), None)
        if o:
            # offers intercept
            o.accept()
            return
        o = next((o for o in a_sent if o.name == self.name and
            o.b == b), None)
        if o:
            a.write(_("You are already offering to be %s's partner.\n") %
                b.name)
            return

        self.a = a
        self.b = b
        a.write(_('Making a partnership offer to %s.\n') % b.name)
        b.write_('\n%s offers to be your bughouse partner; type "partner %s" to accept.\n', (a.name, a.name))
        self._register()
        self.pendinfo('partner', '#')

    def accept(self):
        Offer.accept(self)
        self.a.write_("\n%s agrees to be your partner.\n", (self.b.name,))
        self.b.write(_("You agree to be %s's partner.\n") % (self.a.name,))

        # end any existing partnerships
        if self.a.session.partner:
            self.a.session.partner.write_("\nYour partner has accepted a partnership with %s.", (self.b,))
            end_partnership(self.a, self.a.session.partner)
        if self.b.session.partner:
            self.b.session.partner.write_("\nYour partner has accepted a partnership with %s.", (self.a,))
            end_partnership(self.b, self.b.session.partner)

        self.a.session.partner = self.b
        self.b.session.partner = self.a
        global_.partners.append(set([self.a, self.b]))

        # end any pending partnership offers
        for offer in self.a.session.offers_sent[:]:
            if offer.name == 'partnership request':
                offer.b.write_('\n%(aname)s, who was offering a partnership with you, has accepted a partnership with %(bname)s.\n', {'aname': self.a.name, 'bname': self.b.name})
                offer.withdraw(notify=False)
        for offer in self.b.session.offers_sent[:]:
            if offer.name == 'partnership request':
                offer.b.write_('\n%(aname)s, who was offering a partnership with you, has accepted a partnership with %(bname)s.\n', {'aname': self.b.name, 'bname': self.a.name})
                offer.withdraw(notify=False)
        for offer in self.a.session.offers_received[:]:
            if offer.name == 'partnership request':
                offer.a.write_('\n%(aname)s, whom you were offering a partnership with, has accepted a partnership with %(bname)s.\n', {'aname': self.a.name, 'bname': self.b.name})
                offer.withdraw(notify=False)
        for offer in self.b.session.offers_received[:]:
            if offer.name == 'partnership request':
                offer.a.write_('\n%(aname)s, whom you were offering a partnership with, has accepted a partnership with %(bname)s.\n', {'aname': self.b.name, 'bname': self.a.name})
                offer.withdraw(notify=False)

    def withdraw_logout(self):
        Offer.withdraw_logout(self)
        self.a.write(_('Partnership offer to %s withdrawn.\n') % (self.b.name,))
        self.b.write_('\n%s, who was offering a partnership with you, has departed.\n',
            (self.a.name,))

    def decline_logout(self):
        Offer.decline_logout(self)
        self.a.write_('\n%s, whom you were offering a partnership with, has departed.\n', (self.b.name,))
        self.b.write(_('Partnership offer from %s removed.\n') % (self.a.name,))


def end_partnership(p1, p2):
    """ P1 ends the partnership with P2. """
    # TODO: don't assume "ended partnership", but also handle
    # becoming unavailable for matches, departing, and starting games
    assert(p1.session.partner == p2)
    assert(p2.session.partner == p1)
    global_.partners.remove(set([p1, p2]))
    #p2.write_('\n%s has ended partnership.\n', p1.name)
    p2.write_('\nYour partner has ended partnership.\n')
    for o in p1.session.offers_sent[:]:
        if o.name == 'match offer' and o.variant_name == 'bughouse':
            o.b.write_("\n%s, who was challenging you, has ended partnership.\nChallenge from %s removed.\n", (p1.name, p1.name))
            o.withdraw_partner()
            o.b.session.partner.write_("\n%s's partner has ended partnership.\n'", (p2.name))
            o.b.session.partner.write_("\nPartner's challenge from %s removed.\n'", (p1.name))
            p2.write_("Partner's challenge to %s withdrawn.\n", (o.b.name,))
    for o in p1.session.offers_received[:]:
        if o.name == 'match offer' and o.variant_name == 'bughouse':
            p1.write(_("Challenge from %s removed.\n"), o.a.name)
            o.a.write_("\n%s, whom you were challenging, has ended partnership.\nChallenge to %s withdrawn.\n", (p1.name, p1.name))
            o.a.session.partner.write_("\n%s, whom your partner was challenging, has ended partnership.\nPartner's challenge to %s removed.\n", (p1.name, p1.name))
            p2.write_("\nPartner's challenge from %s removed.\n", (o.a.name,))
            o.decline_partner()
    for o in p2.session.offers_sent[:]:
        if o.name == 'match offer' and o.variant_name == 'bughouse':
            p1.write(_("Partner's challenge to %s withdrawn.\n") % o.b.name)
            p2.write_("\nChallenge to %s withdrawn.\n", (o.b.name,))
            o.b.write_("%s's partner has ended partnership.\nChallenge from %s removed.\n", (p2.name, p2.name))
            o.b.session.partner.write_("%s, whose partner challenged your partner, has ended partnership.\nPartner's challenge from %s removed.\n", (p1.name, p2.name))
            o.withdraw_partner()
    for o in p2.session.offers_received[:]:
        if o.name == 'match offer' and o.variant_name == 'bughouse':
            p1.write(_("\nPartner's challenge from %s removed.\n") % o.a.name)
            p2.write_("\nChallenge from %s removed.\n", (o.a.name,))
            o.a.write_("%s's partner has ended partnership.\nChallenge to %s withdrawn.\n", (p2.name, p2.name))
            o.a.session.partner.write_("\n%s, whose partner your partner was challenging, has ended partnership.\nPartner's challenge to %s withdrawn.\n", (p1.name, p2.name))
            o.decline_partner()
    p1.session.partner = None
    p2.session.partner = None
    p1.write_('You no longer have a bughouse partner.\n')
    p2.write_('You no longer have a bughouse partner.\n')

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
