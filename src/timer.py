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

import time

import global_
import config

from game_constants import PLAYED

heartbeat_timeout = 10


def heartbeat():
    dlist = []

    # idle timeout
    if config.idle_timeout:
        now = time.time()
        for u in global_.online:
            if (now - u.session.last_command_time > config.idle_timeout and
                    not u.is_admin() and
                    not u.has_title('TD')):
                u.session.conn.idle_timeout(config.idle_timeout // 60)

    # ping all zipseal clients
    # I wonder if it would be better to spread out the pings in time,
    # rather than sending a large number of ping requests all at once.
    # However, this method is simple, and FICS timeseal 2 seems to do it
    # this way (pinging all capable clients every 10 seconds).
    for u in global_.online:
        if u.session.use_zipseal or (u.session.use_timeseal and u.session.timeseal_version == 2):
            u.session.ping()

    # forfeit games on time
    for g in global_.games.values():
        if g.gtype == PLAYED and g.clock.is_ticking:
            u = g.get_user_to_move()
            opp = g.get_opp(u)
            if opp.vars_['autoflag']:
                # TODO: send auto-flagging message a la original fics.
                d = g.clock.check_flag(g, g.get_user_side(u))
                if d:
                    dlist.append(d)

    if dlist:
        return defer.DeferredList(dlist)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
