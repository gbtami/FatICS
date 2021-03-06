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

from twisted.internet import defer

import global_


def _find_free_slot():
    """ Find the next available offer number. """
    i = 1
    while True:
        if i not in global_.offers:
            return i
        i += 1


class Offer(object):
    """represents an offer from one player to another"""
    def __init__(self, name):
        self.name = name
        self.game = None
        self.number = _find_free_slot()
        global_.offers[self.number] = self

    def _register(self):
        """ Store the offer as being made for both users. """
        self.a.session.offers_sent.append(self)
        self.b.session.offers_received.append(self)

    def _remove(self):
        """ Called when an offer is no longer open, so that
        the offer number is freed and clients with the pendinfo
        ivariable set are notified. """
        for p in [self.a, self.b]:
            if p.session.ivars['pendinfo']:
                p.write_nowrap('\n<pr> %d\n' % self.number)
        del global_.offers[self.number]

    def pendinfo(self, type_, param):
        if self.a.session.ivars['pendinfo']:
            self.a.write_nowrap('\n<pt> %d w=%s t=%s p=%s\n' % (self.number,
                    self.b.name, type_, param))
        if self.b.session.ivars['pendinfo']:
            self.b.write_nowrap('\n<pf> %d w=%s t=%s p=%s\n' % (self.number,
                    self.a.name, type_, param))

    def accept(self):
        """player b accepts"""
        self.a.session.offers_sent.remove(self)
        self.b.session.offers_received.remove(self)

        self.b.write(_("Accepting the %(offer)s from %(name)s.\n") % {
            'offer': self.name, 'name': self.a.name})
        self.a.write_("\n%(name)s accepts your %(offer)s.\n", {
            'name': self.b.name, 'offer': self.name})
        if self.game:
            for p in self.game.observers:
                p.write_("\nGame %(num)d: %(name)s accepts the %(offer)s.\n", {
                    'num': self.game.number, 'name': self.b.name, 'offer': self.name})
        self._remove()

    def decline(self, notify=True):
        """player b declines"""
        if notify:
            self.b.write(_("Declining the %(offer)s from %(name)s.\n") %
                {'offer': self.name, 'name': self.a.name})
            self.a.write_("\n%(name)s declines your %(offer)s.\n",
                {'name': self.b.name, 'offer': self.name})
            if self.game:
                for p in self.game.observers:
                    p.write_("\nGame %(num)d: %(pname)s declines the %(offer)s.\n",
                        {'num': self.game.number, 'pname': self.b.name, 'offer': self.name})
        self.a.session.offers_sent.remove(self)
        self.b.session.offers_received.remove(self)
        self._remove()

    def withdraw(self, notify=True):
        """player a withdraws the offer"""
        if notify:
            self.a.write(_("Withdrawing your %(offer)s to %(pname)s.\n") %
                {'offer': self.name, 'pname': self.b.name})
            self.b.write_("\n%(pname)s withdraws the %(offer)s.\n",
                {'pname': self.a.name, 'offer': self.name})
            if self.game:
                for p in self.game.observers:
                    p.write_("\nGame %(num)d: %(pname)s withdraws the %(offer)s.\n",
                        {'num': self.game.number, 'pname': self.a.name, 'offer': self.name})
        self.a.session.offers_sent.remove(self)
        self.b.session.offers_received.remove(self)
        self._remove()

    def withdraw_logout(self):
        """ Player a withdraws the offer by logging out. """
        self.withdraw(notify=False)

    def decline_logout(self):
        """ Player b declines the offer by logging out. """
        self.decline(notify=False)


class Abort(Offer):
    def __init__(self, game, user):
        Offer.__init__(self, 'abort request')

        self.a = user
        self.b = game.get_opp(user)
        self.game = game
        offers = [o for o in game.pending_offers if o.name == self.name]
        if len(offers) > 1:
            raise RuntimeError('more than one abort request in game %d'
                % game.number)
        if len(offers) > 0:
            o = offers[0]
            if o.a == self.a:
                user.write(_('You are already offering to abort game %d.\n')
                    % (game.number,))
            else:
                o.accept()
        else:
            game.pending_offers.append(self)
            assert(user == global_.curuser)
            user.write(_('Requesting to abort game %d.\n') % (game.number,))
            self.b.write_('\n%(name)s requests to abort game %(num)d.\n', {
                'name': user.name, 'num': game.number})
            for p in game.observers:
                p.write_('\n%(name)s requests to abort game %(num)d.\n', {
                    'name': user.name, 'num': game.number})
            self._register()
            self.pendinfo('abort', '#')

    def decline(self, notify=True):
        Offer.decline(self, notify)
        self.game.pending_offers.remove(self)

    def accept(self):
        Offer.accept(self)
        self.game.pending_offers.remove(self)
        d = self.game.result('Game aborted by agreement', '*')
        assert(d.called)

    def withdraw(self, notify=True):
        Offer.withdraw(self, notify)
        self.game.pending_offers.remove(self)


class Adjourn(Offer):
    def __init__(self, game, user):
        Offer.__init__(self, 'adjourn request')

        self.a = user
        self.b = game.get_opp(user)
        self.game = game
        offers = [o for o in game.pending_offers if o.name == self.name]
        if len(offers) > 1:
            raise RuntimeError('more than one adjourn offer in game %d'
                % game.number)
        if len(offers) > 0:
            o = offers[0]
            if o.a == self.a:
                user.write(_('You are already offering to adjourn game %d.\n')
                    % (game.number,))
            else:
                # XXX should we disallow adjourning games in the first few
                # moves?
                o.accept()
        else:
            game.pending_offers.append(self)
            assert(user == global_.curuser)
            user.write(_('Requesting to adjourn game %d.\n') % (game.number,))
            self.b.write_('\n%s requests to adjourn game %d.\n', (user.name, game.number))
            for p in game.observers:
                p.write_('\n%s requests to adjourn game %d.\n', (user.name, game.number))
            self._register()
            self.pendinfo('adjourn', '#')

    def decline(self, notify=True):
        Offer.decline(self, notify)
        self.game.pending_offers.remove(self)

    @defer.inlineCallbacks
    def accept(self):
        Offer.accept(self)
        self.game.pending_offers.remove(self)
        yield self.game.adjourn('Game adjourned by agreement')

    def withdraw(self, notify=True):
        Offer.withdraw(self, notify)
        self.game.pending_offers.remove(self)


class Draw(Offer):
    def __init__(self, game, user):
        Offer.__init__(self, 'draw offer')

        self.a = user
        self.b = game.get_opp(user)
        self.game = game

    @defer.inlineCallbacks
    def finish_init(self, game, user):
        offers = [o for o in game.pending_offers if o.name == self.name]
        if len(offers) > 1:
            raise RuntimeError('more than one draw offer in game %d'
                % game.number)
        if len(offers) > 0:
            o = offers[0]
            if o.a == self.a:
                user.write(_('You are already offering a draw.\n'))
            else:
                yield o.accept()
        else:
            # check for draw by 50-move rule, repetition
            # The old fics checked for 50-move draw before repetition,
            # and we do the same so the adjudications are identical.
            if game.variant.pos.is_draw_fifty():
                yield game.result('Game drawn by the 50 move rule', '1/2-1/2')
                return
            elif game.variant.pos.is_draw_repetition(game.get_user_side(
                    self.a)):
                yield game.result('Game drawn by repetition', '1/2-1/2')
                return

            game.pending_offers.append(self)
            # original FICS sends "Draw request sent."
            user.write(_('Offering a draw to %s.\n') % (self.b.name,))
            self.b.write_('\n%s offers you a draw.\n', (user.name,))
            for p in self.game.observers:
                p.write_('\nGame %d: %s offers a draw.\n',
                    (game.number, user.name))

            self._register()
            self.pendinfo('draw', '#')

    @defer.inlineCallbacks
    def accept(self):
        Offer.accept(self)
        self.game.pending_offers.remove(self)
        yield self.game.result('Game drawn by agreement', '1/2-1/2')

    def decline(self, notify=True):
        Offer.decline(self, notify)
        self.game.pending_offers.remove(self)

    def withdraw(self, notify=True):
        if notify:
            self.a.write(_('You cannot withdraw a draw offer.\n'))


class Takeback(Offer):
    def __init__(self, game, user, ply):
        Offer.__init__(self, 'takeback request')

        self.a = user
        self.b = game.get_opp(user)
        self.game = game
        self.ply = ply

    @defer.inlineCallbacks
    def finish_init(self, game, user, ply):
        if game.variant.name == 'bughouse':
            user.write(_('Takeback is not allowed in bughouse.\n'))
            return
        if game.variant.pos.ply == 0:
            user.write(_('There are no moves in your game.\n'))
            return
        if ply > game.variant.pos.ply:
            # yes, original FICS will print "There are only 1 half moves
            # in your game."
            user.write(ngettext("There is only %d half-move in your game.\n",
                "There are only %d half-moves in your game.\n", game.variant.pos.ply) % game.variant.pos.ply)
            return

        offers = [o for o in game.pending_offers if o.name == self.name]
        if len(offers) > 1:
            raise RuntimeError('more than one takeback offer in game %d'
                % game.number)
        if len(offers) > 0:
            o = offers[0]
            if o.a == self.a:
                if o.ply == self.ply:
                    user.write_('You are already offering to takeback the last %d half-move(s).\n',
                        (o.ply,))
                    return
                else:
                    o.withdraw(notify=False)
                    user.write(_('Updated takeback request sent.\n'))
                    self.b.write(_('\nUpdated takeback request received.\n'))
            else:
                if o.ply == self.ply:
                    yield o.accept()
                    return
                else:
                    user.write(_('You disagree on the number of half-moves to take back.\n'))
                    game.pending_offers.append(self)
                    user.write(_('Alternate takeback request sent.\n'))
                    self.b.write_('\n%s proposes a different number (%d) of half-move(s).\n',
                        (user.name, self.ply))
                    for p in self.game.observers:
                        p.write_('\nGame %d: %s proposes a different number (%d) of half-move(s) to take back.\n',
                                 (game.number, user.name, self.ply))

                    o.decline(notify=False)
                    self._register()
                    self.pendinfo('takeback', '%d' % self.ply)
                    return

        game.pending_offers.append(self)
        user.write(_('Takeback request sent.\n'))
        self.b.write_('\n%s would like to take back %d half-move(s).\n',
            (user.name, self.ply))
        for p in self.game.observers:
            p.write_('\nGame %d: %s requests to take back %d half-move(s).\n',
                (game.number, user.name, self.ply))

        self._register()
        self.pendinfo('takeback', '%d' % self.ply)

    @defer.inlineCallbacks
    def accept(self):
        Offer.accept(self)
        self.game.pending_offers.remove(self)
        yield self.game.takeback(self.ply)

    def decline(self, notify=True):
        Offer.decline(self, notify)
        self.game.pending_offers.remove(self)

    def withdraw(self, notify=True):
        Offer.withdraw(self, notify)
        self.game.pending_offers.remove(self)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
