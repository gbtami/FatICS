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

from twisted.internet import defer

import admin
import rating
import history
import time_format
import db
import find_user
import global_
import speed_variant

import admin_command

from .command import ics_command, Command
from parser_ import BadCommandError

from game_constants import EXAMINED, PLAYED


class LogMixin(object):
    def _display_log(self, log, conn):
        out = []
        for a in reversed(log):
            if conn.user.is_admin() and not conn.user.vars_['hideinfo']:
                ip = _(' from %s') % a['log_ip']
            else:
                ip = ''
            when = conn.user.format_datetime(a['log_when'])
            out.append('%s: %-20s %-6s%s' %
                (when, a['log_who_name'], a['log_which'], ip))
        if out:
            out.append('')
            conn.write('\n'.join(out))


@ics_command('finger', 'oOo')
class Finger(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        out = []

        # defaults
        show_notes = True
        show_ratings = True
        show_comments = False
        rating_variants = None

        if args[0] is None:
            u = conn.user
        else:
            u = yield find_user.by_prefix_for_user(args[0], conn)
            if u:
                if args[1] and args[1][0] == '/':
                    # original FICS excepts things like 'b' here for blitz,
                    # but since we separate the speed and variant
                    # we only allow specifying the variant
                    try:
                        rating_variants = [speed_variant.variant_abbrevs[c] for c in args[1][1:]]
                    except KeyError:
                        # unknown variant
                        raise BadCommandError

                    flags = args[2]
                else:
                    flags = args[1]
                    if flags:
                        flags = flags.lower()

                if flags:
                    # specify notes, ratings, or comments
                    show_ratings = False
                    show_notes = False
                    show_comments = False
                    for f in flags:
                        if f == 'r':
                            show_ratings = True
                        elif f == 'n':
                            show_notes = True
                        elif f == 'c' and conn.user.is_admin():
                            show_comments = True
                        else:
                            raise BadCommandError

        if u:
            show_admin_info = (conn.user.is_admin() and
                not conn.user.vars_['hideinfo'])
            out.append(_('Finger of %s:\n\n') % u.get_display_name())

            if u.is_online:
                out.append(_('On for: %s   Idle: %s\n')
                    % (time_format.hms_words(u.session.get_online_time()),
                        time_format.hms_words(u.session.get_idle_time())))
                if u.vars_['busy']:
                    out.append(_('(%(name)s %(busy)s)\n' % {
                        'name': u.name, 'busy': u.vars_['busy']}))
                if u.vars_['silence']:
                    out.append(_('%s is in silence mode.\n') % u.name)

                if u.session.game:
                    g = u.session.game
                    if g.gtype == PLAYED:
                        out.append(_('(playing game %d: %s vs. %s)\n') % (g.number, g.white.name, g.black.name))
                    elif g.gtype == EXAMINED:
                        out.append(_('(examining game %d)\n') % (g.number))
                    else:
                        assert(False)
            else:
                assert(not u.is_guest)
                if u.last_logout is None:
                    out.append(_('%s has never connected.\n') % u.name)
                else:
                    out.append(_('Last disconnected: %s\n') %
                        u.last_logout.replace(tzinfo=pytz.utc).astimezone(conn.user.tz).strftime('%Y-%m-%d %H:%M %Z'))

            out.append('\n')

            if u.is_guest:
                # The open source release of FICS, Lasker, and BICS print
                # this message, but more recent versions of FICS do not.
                out.append(_('%s is NOT a registered player.\n') % u.name)
            if show_ratings and not u.is_guest:
                ratings = yield rating.show_ratings(u, conn, rating_variants)
                out.extend(ratings)
            if u.admin_level > admin.Level.user:
                out.append(A_('Admin level: %s\n') % admin.level.to_str(u.admin_level))
            if show_admin_info:
                if not u.is_guest:
                    out.append(A_('Real name:   %s\n') % u.real_name)
                if u.is_online:
                    out.append(A_('Host:        %s\n') % u.session.conn.ip)
                if not u.is_guest:
                    count = yield db.count_comments(u.id_)
                    out.append(A_('Comments:    %s\n') % count)

            if u == conn.user or show_admin_info:
                if not u.is_guest:
                    out.append(_('Email:       %s\n\n') % u.email)
                    if u.first_login:
                        total = u.get_total_time_online()
                        first = calendar.timegm(u.first_login.timetuple()) + (
                            1e-6 * u.first_login.microsecond)
                        perc = round(100 * total // (time.time() - first), 1)
                        out.append(_('Total time online: %s\n') % time_format.hms_words(total, round_secs=True))
                        since = time.strftime("%a %b %e, %H:%M %Z %Y", time.gmtime(first))
                        # should be equivalent: since = u.first_login.replace(tzinfo=pytz.utc).astimezone(conn.user.tz).strftime('%a %b %e, %H:%M %Z %Y')
                        out.append(_('%% of life online:  %3.1f (since %s)\n\n') % (perc, since))

            if u.is_online:
                if u.session.use_zipseal:
                    out.append(_('Zipseal:     On\n'))
                elif u.session.use_timeseal:
                    if u.session.timeseal_version == 1:
                        out.append(_('Timeseal 1:  On\n'))
                    elif u.session.timeseal_version == 2:
                        out.append(_('Timeseal 2:  On\n'))
                else:
                    out.append(_('Zipseal:     Off\n'))
                if show_admin_info and (u.session.use_timeseal or
                        u.session.use_zipseal):
                    out.append(A_('Acc:         %s\n') % u.session.timeseal_acc)
                    out.append(A_('System:      %s\n') % u.session.timeseal_system)

            notes = u.notes
            if (not u.is_guest and u.is_notebanned and u != conn.user
                    and not show_admin_info):
                # hide notes
                notes = []
            if notes and show_notes:
                out.append('\n')
                prev_max = 0
                for (num, txt) in sorted(notes.iteritems()):
                    num = int(num)
                    assert(num >= prev_max + 1)
                    assert(num <= 10)
                    if num > prev_max + 1:
                        # fill in blank lines
                        for j in range(prev_max + 1, num):
                            out.append(_("%2d: %s\n") % (j, ''))
                    out.append(_("%2d: %s\n") % (num, txt))
                    prev_max = num
                out.append('\n')

            conn.write(''.join(out))

            if show_comments:
                yield admin_command.show_comments(conn, u)


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
            u = yield find_user.by_prefix_for_user(args[0], conn)
        else:
            u = conn.user
        if u:
            yield history.show_for_user(u, conn)


@ics_command('stored', 'o')
class Stored(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = None

        if args[0] is not None:
            u = yield find_user.by_prefix_for_user(args[0], conn)
        else:
            u = conn.user
        if u:

            if u.is_guest:
                conn.write(_('Only registered players may have stored games.\n'))
            else:
                adjourned = yield u.get_adjourned()

                if not adjourned:
                    conn.write(_('%s has no adjourned games.\n') % u.name)
                    return

                conn.write(_('Stored games for %s:\n') % u.name)
                conn.write(_('    C Opponent       On Type          Str  M    ECO Date\n'))

                i = 1

                for entry in adjourned:
                    entry['id'] = i

                    is_white = entry['white_user_id'] == u.id_
                    entry['user_color'] = is_white and 'W' or 'B'

                    opp_name = (entry['black_name'] if is_white
                        else entry['white_name'])
                    entry['opp_str'] = opp_name[:15]

                    entry['online'] = "Y" if global_.online.is_online(opp_name) else "N"

                    flags = entry['speed_abbrev'] + entry['variant_abbrev']
                    entry['flags'] = flags + 'r' if entry['is_rated'] else 'u'

                    half_moves = entry['movetext'].count(' ') + 1
                    next_move_color = "B" if half_moves % 2 else "W"
                    next_move_number = half_moves // 2 + 1
                    entry['next_move'] = "%s%d" % (next_move_color,
                        next_move_number)

                    entry['eco'] = entry['eco'][:3]
                    entry['when_adjourned_str'] = u.format_datetime(entry['when_ended'])
                    conn.write('%(id)2d: %(user_color)1s %(opp_str)-15s %(online)s [%(flags)3s%(time)3s %(inc)3s] %(white_material)2s-%(black_material)-2s %(next_move)-4s %(eco)s %(when_adjourned_str)-s\n' %
                        entry)
                    i = i + 1


@ics_command('logons', 'o')
class Logons(Command, LogMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            u2 = yield find_user.by_prefix_for_user(args[0], conn)
        else:
            u2 = conn.user
        if u2:
            log = yield u2.get_log()
            if not log:
                conn.write('%s has not logged on.\n' % u2.name)
            else:
                self._display_log(log, conn)


@ics_command('llogons', 'p')
class Llogons(Command, LogMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            if args[0] < 0:
                raise BadCommandError
            limit = min(args[0], 200)
        else:
            limit = 200

        rows = yield db.get_log_all(limit)
        self._display_log(rows, conn)


@ics_command('handles', 'w')
class Handles(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if len(args[0]) < 2:
            conn.write(_('You need to specify at least two characters of the name.\n'))
        else:
            ulist = yield db.user_get_by_prefix(args[0], limit=100)
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
