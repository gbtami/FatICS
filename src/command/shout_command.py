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

from .command import ics_command, Command, requires_registration

import global_


@ics_command('shout', 'S')
class Shout(Command):
    @requires_registration
    def run(self, args, conn):
        if conn.user.is_muzzled:
            conn.write(_('You are muzzled.\n'))
            return
        if conn.user.is_muted:
            conn.write(_('You are muted.\n'))
            return
        if not conn.user.vars_['shout'] or conn.user.in_silence():
            conn.write(_("(Did not shout because you are not listening to shouts)\n"))
        else:
            count = 0
            name = conn.user.name
            shouter = conn.user
            dname = conn.user.get_display_name()
            shout_str = "\n%s shouts: %s\n" % (dname, args[0])
            for u in global_.online:
                if u.vars_['shout'] and not u.in_silence() and u != shouter:
                    if name not in u.censor:
                        u.write_prompt(shout_str)
                        count += 1
            conn.write("%s shouts: %s\n" % (dname, args[0]))
            conn.write(ngettext("(shouted to %d player)\n", "(shouted to %d players)\n", count) % count)


@ics_command('it', 'S')
class It(Command):
    @requires_registration
    def run(self, args, conn):
        if conn.user.is_muzzled:
            conn.write(_('You are muzzled.\n'))
            return
        if conn.user.is_muted:
            conn.write(_('You are muted.\n'))
            return
        if not conn.user.vars_['shout'] or conn.user.in_silence():
            conn.write(_("(Did not it-shout because you are not listening to shouts)\n"))
        else:
            count = 0
            name = conn.user.name
            shouter = conn.user
            dname = conn.user.get_display_name()
            shout_str = "\n--> %s %s\n" % (dname, args[0])
            for u in global_.online:
                if u.vars_['shout'] and not u.in_silence() and u != shouter:
                    if name not in u.censor:
                        u.write_prompt(shout_str)
                        count += 1
            conn.write("--> %s %s\n" % (dname, args[0]))
            conn.write(ngettext("(it-shouted to %d player)\n", "(it-shouted to %d players)\n", count) % count)


@ics_command('cshout', 'S')
class Cshout(Command):
    @requires_registration
    def run(self, args, conn):
        # XXX maybe muzzled players shouldn't be allowed to c-shout?
        if conn.user.is_cmuzzled:
            conn.write(_('You are c-muzzled.\n'))
            return
        if conn.user.is_muted:
            conn.write(_('You are muted.\n'))
            return
        if not conn.user.vars_['cshout'] or conn.user.in_silence():
            conn.write(_("(Did not c-shout because you are not listening to c-shouts)\n"))
        else:
            count = 0
            name = conn.user.name
            shouter = conn.user
            dname = conn.user.get_display_name()
            shout_str = "\n%s c-shouts: %s\n" % (dname, args[0])
            for u in global_.online:
                if u.vars_['cshout'] and not u.in_silence() and u != shouter:
                    if name not in u.censor:
                        u.write_prompt(shout_str)
                        count += 1
            conn.write("%s c-shouts: %s\n" % (dname, args[0]))
            conn.write(ngettext("(c-shouted to %d player)\n", "(c-shouted to %d players)\n", count) % count)


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
