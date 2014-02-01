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

from .command import ics_command, Command
from parser_ import BadCommandError

import time_format
import speed_variant
import global_

from game_constants import PLAYED, EXAMINED


@ics_command('showadmins', '')
class Showadmins(Command):
    def run(self, args, conn):
        conn.write('Admins:\n')
        conn.write('Name              Status       Idle time\n')
        # TD programs should not be displayed in showadmins (e.g. ROBOadmin)
        admins = [u for u in global_.online if u.is_admin() and not u.has_title('TD')]
        for u in admins:
            if u.session.game and u.session.game.gtype == PLAYED:
                status = 'Playing'
            elif not u.on_duty_as('admin'):
                status = 'Off_duty'
            elif u.session.get_idle_time() >= 300:
                status = 'Idle'
            else:
                status = 'Available'
            idle = time_format.hms_words(u.session.get_idle_time())
            conn.write('%-17s %-12s %s\n' % (u.name, status, idle))
        conn.write(ngettext('\n%d admin logged in.\n',
            '\n%d admins logged in.\n', len(admins)) % len(admins))


@ics_command('showsrs', '')
class Showsrs(Command):
    def run(self, args, conn):
        conn.write('SRs:\n')
        conn.write('Name              Status       Idle time\n')
        srs = [u for u in global_.online if u.has_title('SR')]
        for u in srs:
            if u.session.game and u.session.game.gtype == PLAYED:
                status = 'Playing'
            elif not u.on_duty_as('SR'):
                status = 'Off_duty'
            elif u.session.get_idle_time() >= 300:
                status = 'Idle'
            else:
                status = 'Available'
            idle = time_format.hms_words(u.session.get_idle_time())
            conn.write('%-17s %-12s %s\n' % (u.name, status, idle))
        conn.write(ngettext('\n%d SR logged in.\n',
            '\n%d SRs logged in.\n', len(srs)) % len(srs))


@ics_command('showtms', '')
class Showtms(Command):
    def run(self, args, conn):
        conn.write('TMs:\n')
        conn.write('Name              Status       Idle time\n')
        tms = [u for u in global_.online if u.has_title('TM')]
        for u in tms:
            if u.session.game and u.session.game.gtype == PLAYED:
                status = 'Playing'
            elif not u.on_duty_as('TM'):
                status = 'Off_duty'
            elif u.session.get_idle_time() >= 300:
                status = 'Idle'
            else:
                status = 'Available'
            idle = time_format.hms_words(u.session.get_idle_time())
            conn.write('%-17s %-12s %s\n' % (u.name, status, idle))
        conn.write(ngettext('\n%d TM logged in.\n',
            '\n%d TMs logged in.\n', len(tms)) % len(tms))


@ics_command('who', 'T')
class Who(Command):
    # number of spaces between columns
    MULTICOL_SPACE = 2

    def _multicol_print(self, items, max_len, conn):
        """Print a list of items in columns."""
        assert(max_len > 0)
        max_len += self.MULTICOL_SPACE
        num_cols = max(conn.user.vars_['width'] // max_len, 1)
        num_rows = len(items) // num_cols
        if num_rows * num_cols < len(items):
            num_rows += 1
        assert(num_rows * num_cols >= len(items))

        #print 'multicol items %d, rows %d, cols %d' % (len(items), num_rows, num_cols)

        out = []
        for row in range(0, num_rows):
            for col in range(0, num_cols):
                try:
                    item = items[col * num_rows + row]
                except IndexError:
                    # reached end
                    break
                out.append(item)
                if col != num_cols - 1:
                    len_space = max_len - len(item)
                    assert(len_space > 0)
                    out.append(' ' * len_space)
            out.append('\n')
        out.append('\n')

        conn.write_nowrap(''.join(out))

    def run(self, args, conn):
        users = [u for u in global_.online]

        sort_order = 'b'
        fmt = 't'
        if args[0]:
            param = args[0]
            i = 0
            while i < len(param):
                if param[i] == 'o':
                    users = [u for u in users if u.vars_['open']]
                # r for rated not implemented (it's obsolete)
                elif param[i] == 'f':
                    users = [u for u in users if not u.session.game]
                elif param[i] == 'a':
                    users = [u for u in users if u.vars_['open'] and not u.session.game]
                elif param[i] == 'R':
                    users = [u for u in users if not u.is_guest]
                elif param[i] == 'U':
                    users = [u for u in users if u.is_guest]
                elif param[i] in ['s', 'b', 'w', 'z', 'L', 'S', 'B', 'A', 'l']:
                    if sort_order != 'b' and sort_order != param[i]:
                        # conflicting sort orders given
                        raise BadCommandError
                    sort_order = param[i]
                elif param[i] in ['t', 'v', 'n', 'I']:
                    # XXX what does n do?
                    if fmt != 't' and fmt != param[i]:
                        # conflicting formats given
                        raise BadCommandError
                    fmt = param[i]
                elif param[i].isdigit():
                    if i + 1 >= len(param) or not param[i + 1].isdigit():
                        # only one digit given; default to 3 parts
                        page = int(param[i])
                        if page < 1 or page > 3:
                            raise BadCommandError
                        divs = 3
                    else:
                        page = int(param[i])
                        divs = int(param[i + 1])
                        if page > divs:
                            raise BadCommandError
                else:
                    raise BadCommandError

                i += 1

        #standard = speed_variant.from_names('standard', 'chess')
        #blitz = speed_variant.from_names('blitz', 'chess')
        #lightning = speed_variant.from_names('lightning', 'chess')
        #zh = speed_variant.from_names('blitz', 'crazyhouse')
        #fr = speed_variant.from_names('blitz', 'chess960')
        #suicide = speed_variant.from_names('blitz', 'chess960')
        #bughouse = speed_variant.from_names('blitz', 'bughouse')
        if sort_order == 's':
            compare = lambda p: int(p.get_rating(speed_variant.standard_chess))
        elif sort_order == 'b':
            compare = lambda p: int(p.get_rating(speed_variant.blitz_chess))
        elif sort_order == 'L':
            compare = lambda p: int(p.get_rating(speed_variant.lightning_chess))
        elif sort_order == 'z':
            compare = lambda p: int(p.get_rating(speed_variant.blitz_crazyhouse))
        elif sort_order == 'B':
            compare = lambda p: int(p.get_rating(speed_variant.blitz_bughouse))
        elif sort_order == 'w':
            # hack: in original fics this means wild, but it now means chess960
            compare = lambda p: int(p.get_rating(speed_variant.blitz_chess960))
        elif sort_order == 'S':
            # XXX suicide
            conn.write('TODO: suicide\n')
            return
        elif sort_order == 'A':
            compare = lambda p: p.name
        elif sort_order == 'l':
            compare = lambda p: p.name
        else:
            assert(False)
        users.sort(key=compare)

        if fmt == 't':
            items = []
            max_len = 0
            for u in users:
                if sort_order == 'A':
                    rating = '     '
                elif sort_order == 'l':
                    rating = '%4d  ' % u.get_rating(speed_variant.blitz_chess)
                else:
                    rating = '%4d  ' % compare(u)
                if u.vars_['tourney']:
                    status = '&'
                elif u.session.game:
                    # XXX ~ means simul
                    if u.session.game.gtype == PLAYED:
                        status = '^'
                    elif u.session.game.gtype == EXAMINED:
                        status = '#'
                    else:
                        # XXX
                        assert(False)
                elif u.vars_['busy'] or u.session.get_idle_time() > 300:
                    status = '.'
                elif not u.vars_['open']:
                    status = ':'
                else:
                    status = ' '
                item = ''.join((rating, status, u.get_display_name()))
                max_len = max(len(item), max_len)
                items.append(item)
            self._multicol_print(items, max_len, conn)

            count = len(items)
            conn.write(ngettext('%d player displayed.\n\n',
                '%d players displayed.\n\n', count) % count)
        else:
            conn.write('TODO: unsupported format\n')

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
