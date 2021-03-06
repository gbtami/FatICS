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

import match
import admin
import find_user
import speed_variant
import global_

from .command import Command, ics_command

from game_constants import EXAMINED
from twisted.internet import defer


@ics_command('match', 'wt', admin.Level.user)
class Match(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if conn.user.session.game:
            if conn.user.session.game.gtype == EXAMINED:
                conn.write(_("You can't challenge while you are examining a game.\n"))
            else:
                conn.write(_("You can't challenge while you are playing a game.\n"))
            return
        u = find_user.online_by_prefix_for_user(args[0], conn)
        if not u:
            return
        if u == conn.user:
            conn.write(_("You can't match yourself.\n"))
            return

        c = match.Challenge()
        yield c.finish_init(conn.user, u, args[1])


# TODO: parameters?


@ics_command('rematch', '')
class Rematch(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        # note that rematch uses history to determine the previous opp,
        # so unlike "say", it works after logging out and back in, and
        # ignores aborted games
        hist = conn.user.get_history()
        if not hist:
            conn.write(_('You have no previous opponent.\n'))
            return
        h = hist[-1]
        opp = global_.online.find_exact(h['opp_name'])
        if not opp:
            conn.write(_('Your last opponent, %s, is not logged in.\n') % h['opp_name'])
            return
        variant_name = speed_variant.variant_abbrevs[h['flags'][1]]
        assert(h['flags'][2] in ['r', 'u'])
        match_str = '%d %d %s %s' % (h['time'], h['inc'], h['flags'][2],
            variant_name)
        c = match.Challenge()
        yield c.finish_init(conn.user, opp, match_str)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
