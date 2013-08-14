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

import time
import traceback

import var
import timeseal
import partner
import channel
import global_

from game_list import GameList

# user state that is per-session and not saved to persistent storage


class Session(object):
    def __init__(self, conn):
        """ Created when a connection is made. """
        self.conn = conn
        self.use_timeseal = False
        self.use_zipseal = False
        self.check_for_timeseal = True
        self.ivars = var.varlist.get_default_ivars()
        self.closed = False

    def set_user(self, user):
        """ Called when a reg. player or guest has passed the login step. """
        self.user = user
        self.login_time = time.time()
        self.last_command_time = time.time()
        self.last_tell_user = None
        self.last_tell_ch = None
        self.move_sent_timestamp = None
        self.say_to = set()
        self.lag = 0
        self.following = None
        self.ping_sent = []
        self.ping_time = []
        self.followed_by = set()
        self.ftell = None
        self.ftell_admins = set()
        self.next_lines = ''
        self.offers_sent = []
        self.game = None
        self.offers_received = []
        self.idlenotifying = set()
        self.idlenotified_by = set()
        self.seeks = []
        self.observed = GameList()
        self.partner = None
        self.conn.write(_('**** Starting FICS session as %s ****\n\n') % user.get_display_name())
        # XXX could use set comprehensions for Python 2.7+
        self.notifiers_online = set([u for u in
            (global_.online.find_exact(name) for name in self.user.notifiers)
            if u])
        for u in self.notifiers_online:
            u.session.notified_online.add(self.user)
        self.notified_online = set([u for u in
            (global_.online.find_exact(name) for name in self.user.notified)
            if u])
        for u in self.notified_online:
            u.session.notifiers_online.add(self.user)

    def get_idle_time(self):
        """ returns seconds """
        assert(self.last_command_time is not None)
        return time.time() - self.last_command_time

    def get_online_time(self):
        """ returns seconds """
        assert(self.login_time is not None)
        return time.time() - self.login_time

    def close(self):
        assert(not self.closed)
        self.closed = True
        # XXX this will not remove draw offers; game-related offers
        # should probably be saved when a game is adjourned
        for v in self.offers_sent[:]:
            assert(v.a == self.user)
            v.withdraw_logout()
        for v in self.offers_received[:]:
            assert(v.b == self.user)
            v.decline_logout()
        if self.partner:
            #self.conn.write(_('Removing partnership with %s.\n') %
            #    partner.name)
            self.partner.write_('\nYour partner, %s, has departed.\n',
                self.user.name)
            partner.end_partnership(self.user, self.partner)

        if self.game:
            try:
                self.game.leave(self.user)
                assert(self.game is None)
            except:
                print('exception ending game due to logout')
                traceback.print_exc()
        del self.offers_received[:]
        del self.offers_sent[:]

        for u in self.idlenotified_by:
            u.write_("\nNotification: %s, whom you were idlenotifying, has departed.\n", (self.user.name,))
            u.session.idlenotifying.remove(self.user)
        self.idlenotified_by.clear()
        for u in self.idlenotifying:
            u.session.idlenotified_by.remove(self.user)

        if self.followed_by:
            for p in self.followed_by.copy():
                assert(p.session.following == self.user)
                if p.session.pfollow:
                    p.write_("\n%s, whose partner's games you were following, has logged out.\n", self.user.name)
                else:
                    p.write_("\n%s, whose games you were following, has logged out.\n", self.user.name)
                p.session.following = None
            self.followed_by = set()
        if self.following:
            # stop following
            self.following.session.followed_by.remove(self.user)

        # unobserve games
        assert(self.user.session == self)
        for g in self.observed.copy():
            g.unobserve(self.user)
        assert(not self.observed)

        # remove seeks
        if self.seeks:
            for s in self.seeks[:]:
                s.remove()
            self.conn.write(_('Your seeks have been removed.\n'))
        assert(not self.seeks)

        # remove ftells
        if self.ftell:
            self.ftell.session.ftell_admins.remove(self.user)
            channel.chlist[0].tell("I am logging out now - conversation forwarding stopped.", self.user)

        if self.ftell_admins:
            ch = channel.chlist[0]
            for adm in self.ftell_admins:
                ch.tell(A_("*%s* has logged out - conversation forwarding stopped.") % self.user.name, adm)
                adm.write(A_("%s, whose tells you were forwarding, has logged out.\n") % self.user.name)
                adm.session.ftell = None
            self.ftell_admins = []

        for u in self.notified_online:
            u.session.notifiers_online.remove(self.user)
        for u in self.notifiers_online:
            u.session.notified_online.remove(self.user)
        self.notifiers_online = None
        self.notified_online = None

    def set_ivars_from_str(self, s):
        """Parse a %b string sent by Jin to set ivars before logging in."""
        for (i, val) in enumerate(s):
            self.ivars[var.ivar_number[i].name] = int(val)
        self.conn.write("#Ivars set.\n")

    def set_ivar(self, v, val):
        if val is not None:
            self.ivars[v.name] = val
        else:
            if v.name in self.ivars:
                del self.ivars[v.name]

    def ping(self, for_move=False):
        # don't send another ping if one is already pending
        assert(self.use_timeseal or self.use_zipseal)
        # Always send a ping with a move in a game being played.
        # Otherwise, send a ping if one is not already pending.
        if for_move or not self.ping_sent:
            if self.use_zipseal:
                self.conn.write(timeseal.ZIPSEAL_PING)
            elif self.timeseal_version == 2:
                self.conn.write(timeseal.TIMESEAL_2_PING)
            else:
                self.conn.write(timeseal.TIMESEAL_1_PING)
            self.ping_sent.append((time.time(), for_move))

    def pong(self, t):
        assert(self.ping_sent)
        sent_time, for_move = self.ping_sent.pop(0)
        reply_time = time.time() - sent_time

        if len(self.ping_time) > 9:
            self.ping_time.pop(0)
        self.ping_time.append(reply_time)

        if for_move:
            self.move_sent_timestamp = t

    def get_timeseal_move_time(self):
        if self.move_sent_timestamp is None:
            self.conn.write('timeseal error: your timeseal did not reply to the server ping\n')
            print('client of %s failed to reply to timeseal ping for move' % self.conn.user.name)
            self.conn.loseConnection('timeseal error')
            return
        elapsed_ms = (self.timeseal_last_timestamp -
            self.move_sent_timestamp)
        return elapsed_ms


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
