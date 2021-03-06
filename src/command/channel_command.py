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

from twisted.internet import defer

from .command import ics_command, Command, requires_registration

import admin
import find_user
import global_
import channel


@ics_command('inchannel', 'n', admin.Level.user)
class Inchannel(Command):
    def run(self, args, conn):
        if args[0] is not None:
            if isinstance(args[0], basestring):
                u = find_user.online_by_prefix_for_user(args[0], conn)
                if not u:
                    return
                conn.write(_('%s is in the following channels:\n') % u.name)
                s = ''
                for ch in u.channels:
                    s += '%-3d ' % ch
                conn.write(s + '\n')
            else:
                try:
                    ch = global_.channels[args[0]]
                except KeyError:
                    if args[0] < 0 or args[0] > channel.CHANNEL_MAX:
                        conn.write(_('Invalid channel number.\n'))
                    else:
                        conn.write(_('There are %d players in channel %d.\n') %
                            (0, args[0]))
                else:
                    on = ch.get_online()
                    if len(on) > 0:
                        conn.write("%s: %s\n" % (ch.get_display_name(), ' '.join(on)))
                    count = len(on)
                    conn.write(ngettext('There is %d player in channel %d.\n', 'There are %d players in channel %d.\n', count) % (count, args[0]))
        else:
            for ch in global_.channels:
                on = ch.get_online()
                if len(on) > 0:
                    conn.write("%s: %s\n" %
                        (ch.get_display_name(), ' '.join(on)))


@ics_command('chkick', 'dw', admin.Level.user)
class Chkick(Command):
    """ Kick a user from a channel. """
    @requires_registration
    @defer.inlineCallbacks
    def run(self, args, conn):
        (chid, name) = args
        u = yield find_user.by_prefix_for_user(name, conn)
        if not u:
            return
        try:
            ch = yield global_.channels.get(chid)
        except KeyError:
            conn.write(_('Invalid channel number.\n'))
            return
        yield ch.kick(u, conn.user)


@ics_command('chtopic', 'dT', admin.Level.user)
class Chtopic(Command):
    """ Set or view a channel topic. """
    @defer.inlineCallbacks
    def run(self, args, conn):
        (chid, topic) = args
        try:
            ch = yield global_.channels.get(chid)
        except KeyError:
            conn.write(_('Invalid channel number.\n'))
            return
        if topic is None:
            ch.show_topic(conn.user)
        else:
            yield ch.set_topic(topic, conn.user)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
