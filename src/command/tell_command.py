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

from .command import Command, ics_command

import channel
import user
import global_
import admin

from game_constants import PLAYED, EXAMINED

class ToldMixin(object):
    def _told(self, u, conn):
        if u.session.game:
            if u.session.game.gtype == PLAYED:
                conn.write(_("(told %s, who is playing)\n") % u.name)
            elif u.session.game.gtype == EXAMINED:
                conn.write(_("(told %s, who is examining a game)\n") % u.name)
            else:
                assert(False)
        elif u.session.get_idle_time() >= 180:
            conn.write(_("(told %s, who has been idle for %d minutes)\n") %
                       (u.name, (u.session.get_idle_time() / 60)))
        else:
            conn.write(_("(told %s)\n") % u.name)

class TellCommand(Command, ToldMixin):
    def _do_tell(self, args, conn):
        if conn.user.is_muted:
            # mute now prevents *all* tells
            conn.write(_('You are muted.\n'))
            return (None, None)
        u = None
        ch = None
        if args[0] == '.':
            u = conn.session.last_tell_user
            if not u:
                conn.write(_("No previous tell.\n"))
            elif not u.is_online:
                # try to find the user if he or she has logged off
                # and since reconnected
                name = u.name
                u = global_.online.find_exact(name)
                if not u:
                    conn.write(_('%s is no longer online.\n') % name)
        elif args[0] == ',':
            ch = conn.session.last_tell_ch
            if not ch:
                conn.write(_('No previous channel.\n'))
        else:
            if type(args[0]) in [int, long]:
                try:
                    ch = channel.chlist[args[0]]
                except KeyError:
                    conn.write(_('Invalid channel number.\n'))
                else:
                    if conn.user not in ch.online and (
                            not conn.user.has_title('TD')):
                        conn.user.write(_('''(Not sent because you are not in channel %s.)\n''') % ch.id)
                        ch = None
            else:
                u = user.find_by_prefix_for_user(args[0], conn, online_only=True)

        if ch:
            count = ch.tell(args[1], conn.user)
            conn.write(ngettext('(told %d player in channel %d)\n', '(told %d players in channel %d)\n', count) % (count, ch.id))
        elif u:
            if conn.user.name in u.censor and not conn.user.is_admin():
                conn.write(_("%s is censoring you.\n") % u.name)
                # TODO: notify admins they are censored
            elif conn.user.is_guest and not u.vars['tell']:
                conn.write(_('''Player "%s" isn't listening to unregistered users' tells.\n''' % u.name))
            else:
                u.write_('\n%s tells you: %s\n',
                    (conn.user.get_display_name(), args[1]))
                self._told(u, conn)
                if u.session.ftell == conn.user or conn.user.session.ftell == u:
                    for adm in channel.chlist[0].online:
                        if adm.hears_channels():
                            adm.write(A_("Fwd tell: %s told %s: %s\n") % (conn.user.name, u.name, args[1]))


        return (u, ch)

@ics_command('tell', 'nS', admin.Level.user)
class Tell(TellCommand):
    def run(self, args, conn):
        (u, ch) = self._do_tell(args, conn)
        if u is not None:
            conn.session.last_tell_user = u
        else:
            conn.session.last_tell_ch = ch

@ics_command('xtell', 'nS', admin.Level.user)
class Xtell(TellCommand):
    def run(self, args, conn):
        self._do_tell(args, conn)

@ics_command('qtell', 'iS', admin.Level.user)
class Qtell(Command):
    def run(self, args, conn):
        if not conn.user.has_title('TD'):
            conn.write(_('Only TD programs are allowed to use this command\n'))
            return
        msg = args[1].replace('\\n', '\n:').replace('\\b', '\x07').replace('\\H', '\x1b[7m').replace('\\h', '\x1b[0m')
        msg = '\n:%s\n' % msg
        ret = 0 # 0 means success
        if type(args[0]) == type(1):
            # qtell channel
            try:
                ch = channel.chlist[args[0]]
            except KeyError:
                ret = 1
            else:
                ch.qtell(msg)
        else:
            # qtell user
            try:
                u = user.find_by_name_exact(args[0])
                if not u or not u.is_online:
                    ret = 1
                else:
                    args[0] = u.name
                    u.write(msg)
            except user.UsernameException:
                ret = 1
        conn.write('*qtell %s %d*\n' % (args[0], ret))

@ics_command('say', 'S')
class Say(Command, ToldMixin):
    def run(self, args, conn):
        if conn.user.is_muted:
            # mute now prevents *all* tells
            conn.write(_('You are muted.\n'))
            return

        say_to = [u for u in conn.user.session.say_to if u.is_online]
        if not say_to:
            if len(conn.user.session.say_to) == 1:
                # The common case: the opponent logged
                # out after a non-bug game
                u = iter(conn.user.session.say_to).next()
                # try to find the user if he or she has since reconnected
                name = u.name
                u = global_.online.find_exact(name)
                if u:
                    say_to = [u]
                else:
                    conn.write(_('%s is no longer online.\n') % name)
            else:
                # All other players have logged out after a bug game
                conn.write(_("I don't know whom to say that to.\n"))
        if say_to:
            g = conn.user.session.game
            if g and g.gtype == PLAYED:
                assert(g.get_opp(conn.user) in say_to)
                game_num = g.number
            else:
                game_num = None
        for p in say_to:
            # Don't bother checking for admins; they can use "tell"
            # if they want to override censor.
            if conn.user.name in p.censor:
                conn.write(_("%s is censoring you.\n") % p.name)
                continue
            if game_num:
                p.write_("\n%s[%d] says: %s\n", (conn.user.get_display_name(),
                    g.number, args[0]))
            else:
                p.write_("\n%s says: %s\n", (conn.user.get_display_name(),
                    args[0]))
            self._told(p, conn)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
