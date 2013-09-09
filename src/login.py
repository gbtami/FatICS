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

import user
import filter_
import global_
import find_user
import config

from twisted.internet import defer


# return a user object if one exists; otherwise make a
# guest user


@defer.inlineCallbacks
def get_user(name, conn):
    u = None
    # Currently there is no way to set the langauge at the login
    # login prompt, but maybe that could change with a %lang or so.
    if name.lower() in ['g', 'guest']:
        u = user.GuestUser(None)
        conn.write(_('\nLogging you in as "%s"; you may use this name to play unrated games.\n(After logging in, do "help register" for more info on how to register.)\n\nPress return to enter the server as "%s":\n') % (u.name, u.name))
    elif name:
        try:
            u = yield find_user.exact(name)
        except find_user.UsernameException as e:
            conn.write(_('\n%s  Try again.\n') % e.reason)
        else:
            if u:
                if u.is_guest:
                    # It's theoretically possible that
                    # a new user registers but is blocked
                    # from logging in by a guest with the
                    # same name.  We ignore that case.
                    conn.write(_('Sorry, %s is already logged in. Try again.\n') % name)
                    u = None
                else:
                    conn.write(_('\n"%s" is a registered name.  If it is yours, type the password.\nIf not, just hit return to try another name.\n\npassword: ') % u.name)
            else:
                u = user.GuestUser(name)
                conn.write(_('\n"%s" is not a registered name.  You may play unrated games as a guest.\n(After logging in, do "help register" for more info on how to register.)\n\nPress return to enter the server as "%s":\n') % (name, name))

    if u:
        if u.is_guest:
            if filter_.check_filter(conn.ip):
                # not translated, since the player hasn't logged on
                conn.write('Due to abuse, guest logins are blocked from your address.\n')
                conn.loseConnection('filtered')
                u = None
            if u and global_.online.guest_count >= config.maxguest:
                conn.write(global_.server_message['full_unreg'])
                conn.loseConnection('guests full')
                u = None
        else:
            if u.is_banned:
                # not translated, since the player hasn't logged on
                conn.write('Player "%s" is banned.\n' % u.name)
                conn.loseConnection('banned')
                u = None

        if u:
            pmax = config.maxplayer if u.is_admin() else (config.maxplayer -
                config.admin_reserve)
            if len(global_.online) >= pmax:
                conn.write(global_.server_message['full'])
                conn.loseConnection('players full')
                u = None

    defer.returnValue(u)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
