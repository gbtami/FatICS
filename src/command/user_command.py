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

import time
import pytz
import calendar # for timegm

import admin
import rating
import history
import time_format
import db
import find_user

from twisted.internet import defer

from .command import ics_command, Command
from parser import BadCommandError

from game_constants import EXAMINED, PLAYED


class LogMixin(object):
    def _display_log(self, log, conn):
        for a in reversed(log):
            if conn.user.is_admin() and not conn.user.vars['hideinfo']:
                ip = _(' from %s') % a['log_ip']
            else:
                ip = ''
            when = conn.user.format_datetime(a['log_when'])
            conn.write('%s: %-20s %-6s%s\n' %
                (when, a['log_who_name'], a['log_which'], ip))


@ics_command('finger', 'ooo')
class Finger(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            u = yield find_user.by_prefix_for_user(args[0], conn)
            flags = args[1:]
        else:
            u = conn.user
            flags = []
        if u:
            show_notes = True
            show_ratings = True
            show_comments = False
            show_admin_info = (conn.user.is_admin() and
                not conn.user.vars['hideinfo'])
            for f in flags:
                if f is None:
                    continue
                elif f[0] == '/':
                    # XXX TODO
                    pass
                elif f == 'r':
                    show_notes = False
                elif f == 'n':
                    show_ratings = False
                elif f == 'c' and conn.user.is_admin():
                    show_comments = True
                else:
                    raise BadCommandError
            conn.write(_('Finger of %s:\n\n') % u.get_display_name())

            if u.is_online:
                conn.write(_('On for: %s   Idle: %s\n')
                    % (time_format.hms_words(u.session.get_online_time()),
                        time_format.hms_words(u.session.get_idle_time())))
                if u.vars['busy']:
                    conn.write(_('(%(name)s %(busy)s)\n' % {
                        'name': u.name, 'busy': u.vars['busy']}))
                if u.vars['silence']:
                    conn.write(_('%s is in silence mode.\n') % u.name)

                if u.session.game:
                    g = u.session.game
                    if g.gtype == PLAYED:
                        conn.write(_('(playing game %d: %s vs. %s)\n') % (g.number, g.white.name, g.black.name))
                    elif g.gtype == EXAMINED:
                        conn.write(_('(examining game %d)\n') % (g.number))
                    else:
                        assert(False)
            else:
                assert(not u.is_guest)
                if u.last_logout is None:
                    conn.write(_('%s has never connected.\n') % u.name)
                else:
                    conn.write(_('Last disconnected: %s\n') %
                        u.last_logout.replace(tzinfo=pytz.utc).astimezone(conn.user.tz).strftime('%Y-%m-%d %H:%M %Z'))

            conn.write('\n')

            #if u.is_guest:
            #    conn.write(_('%s is NOT a registered player.\n') % u.name)
            if show_ratings and not u.is_guest:
                rating.show_ratings(u, conn)
            if u.admin_level > admin.Level.user:
                conn.write(A_('Admin level: %s\n') % admin.level.to_str(u.admin_level))
            if show_admin_info:
                if not u.is_guest:
                    conn.write(A_('Real name:   %s\n') % u.real_name)
                if u.is_online:
                    conn.write(A_('Host:        %s\n') % u.session.conn.ip)

            if u == conn.user or show_admin_info:
                if not u.is_guest:
                    conn.write(_('Email:       %s\n\n') % u.email)
                    if u.first_login:
                        total = u.get_total_time_online()
                        first = calendar.timegm(u.first_login.timetuple()) + (
                            1e-6 * u.first_login.microsecond)
                        perc = round(100 * total / (time.time() - first), 1)
                        conn.write(_('Total time online: %s\n') % time_format.hms_words(total, round_secs=True))
                        since = time.strftime("%a %b %e, %H:%M %Z %Y", time.gmtime(first))
                        # should be equivalent: since = u.first_login.replace(tzinfo=pytz.utc).astimezone(conn.user.tz).strftime('%a %b %e, %H:%M %Z %Y')
                        conn.write(_('%% of life online:  %3.1f (since %s)\n\n') % (perc, since))

            if u.is_online:
                if u.session.use_zipseal:
                    conn.write(_('Zipseal:     On\n'))
                elif u.session.use_timeseal:
                    if u.session.timeseal_version == 1:
                        conn.write(_('Timeseal 1:  On\n'))
                    elif u.session.timeseal_version == 2:
                        conn.write(_('Timeseal 2:  On\n'))
                else:
                    conn.write(_('Zipseal:     Off\n'))
                if show_admin_info and (u.session.use_timeseal or
                    u.session.use_zipseal):
                    conn.write(A_('Acc:         %s\n') % u.session.timeseal_acc)
                    conn.write(A_('System:      %s\n') % u.session.timeseal_system)

            notes = u.notes if show_notes else []
            if (not u.is_guest and u.is_notebanned and u != conn.user and
                not conn.user.is_admin()):
                # hide notes
                # XXX should hideinfo apply here?
                notes = []
            if notes:
                conn.write('\n')
                prev_max = 0
                for (num, txt) in sorted(notes.iteritems()):
                    num = int(num)
                    assert(num >= prev_max + 1)
                    assert(num <= 10)
                    if num > prev_max + 1:
                        # fill in blank lines
                        for j in range(prev_max + 1, num):
                            conn.write(_("%2d: %s\n") % (j, ''))
                    conn.write(_("%2d: %s\n") % (num, txt))
                    prev_max = num
                conn.write('\n')

            if show_comments:
                # XXX TODO
                pass


@ics_command('ping', 'o')
class Ping(Command):
    def run(self, args, conn):
        if args[0] is not None:
            u2 = find_user.online_by_prefix_for_user(args[0], conn)
        else:
            u2 = conn.user

        if u2:
            assert(u2.is_online)
            pt = u2.session.ping_time
            if not u2.has_timeseal():
                conn.write(_('Ping time not available; %s is not using zipseal.\n') %
                    u2.name)
            elif len(pt) < 2:
                conn.write(_('Ping time not available; please wait.\n'))
            else:
                conn.write(_('Ping time for %s, based on %d samples:\n') %
                    (u2.name, len(pt)))
                avg = 1000.0 * sum(pt) / len(pt)
                conn.write(_('Average: %.3fms\n') % (avg))


@ics_command('history', 'o')
class History(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = None
        if args[0] is not None:
            u = yield find_user.by_prefix_for_user(args[0], conn) #, min_len=2)
        else:
            u = conn.user
        if u:
            history.show_for_user(u, conn)
        defer.returnValue(None)


@ics_command('logons', 'o')
class Logons(Command, LogMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            u2 = yield find_user.by_prefix_for_user(args[0], conn)
        else:
            u2 = conn.user
        if u2:
            log = u2.get_log()
            if not log:
                conn.write('%s has not logged on.\n' % u2.name)
            else:
                self._display_log(log, conn)
        defer.returnValue(None)


@ics_command('llogons', 'p')
class Llogons(Command, LogMixin):
    def run(self, args, conn):
        if args[0] is not None:
            if args[0] < 0:
                raise BadCommandError
            limit = min(args[0], 200)
        else:
            limit = 200

        self._display_log(db.get_log_all(limit), conn)


@ics_command('handles', 'w')
class Handles(Command):
    def run(self, args, conn):
        if len(args[0]) < 2:
            conn.write(_('You need to specify at least two characters of the name.\n'))
        else:
            ulist = db.user_get_matching(args[0], limit=100)
            if not ulist:
                conn.write(_('There is no player matching the name %s.\n') %
                    args[0])
            else:
                conn.write(ngettext('-- Matches: %d player --\n',
                    '-- Matches: %d players --\n', len(ulist)) % len(ulist))
                # XXX should print in columns
                for u in ulist:
                    conn.write('%s\n' % u['user_name'])

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
