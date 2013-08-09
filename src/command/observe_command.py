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
from command_parser import BadCommandError

import game
import user
import global_

@ics_command('observe', 'i')
class Observe(Command):
    def run(self, args, conn):
        if args[0] in ['/l', '/b', '/s', '/S', '/w', '/z', '/B', '/L', '/x']:
            conn.write('TODO: observe flag\n')
            return
        g = game.from_name_or_number(args[0], conn)
        if g:
            if g in conn.user.session.observed:
                conn.write(_('You are already observing game %d.\n' % g.number))
            elif conn.user in g.players:
                conn.write(_('You cannot observe yourself.\n'))
            else:
                assert(conn.user not in g.observers)
                g.observe(conn.user)

@ics_command('follow', 'o')
class Follow(Command):
    def run(self, args, conn):
        if args[0] is None:
            uf = conn.user.session.following
            if not uf:
                conn.write(_("You are not following any player's games.\n"))
            else:
                assert(uf.is_online)
                uf.session.followed_by.remove(conn.user)
                conn.user.session.following = None
                # no need to change conn.user.session.pfollow
                conn.write(_("You will not follow any player's games.\n"))
        else:
            u2 = user.find_by_prefix_for_user(args[0], conn,
                online_only=True)
            if u2:
                if u2 == conn.user:
                    conn.write(_("You can't follow your own games.\n"))
                    return
                if conn.user.session.following:
                    if u2 == conn.user.session.following and not conn.user.session.pfollow:
                        conn.write(_("You are already following %s's games.\n")
                            % u2.name)
                        return
                    if conn.user.session.pfollow:
                        conn.user.write(_("You will no longer be following %s's partner's games.\n") % conn.user.session.following.name)
                    else:
                        conn.user.write(_("You will no longer be following %s's games.\n") % conn.user.session.following.name)
                    conn.user.session.following.session.followed_by.remove(conn.user)
                conn.write(_("You will now be following %s's games.\n")
                    % u2.name)
                conn.user.session.following = u2
                conn.user.session.pfollow = False
                u2.session.followed_by.add(conn.user)

                # If there is a game in progress and we are not already
                # observing it, start observing it.
                g = u2.session.game
                if (g and g not in conn.user.session.observed and
                        conn.user not in g.players):
                    g.observe(conn.user)
                    assert(g in conn.user.session.observed)

@ics_command('allobservers', 'o')
class Allobservers(Command):
    def run(self, args, conn):
        count = 0
        if args[0] is not None:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g.allobservers(conn):
                    count = 1
                else:
                    conn.write(_('No one is observing game %d.\n')
                        % g.number)
        else:
            for g in global_.games.itervalues():
                if g.allobservers(conn):
                    count += 1

        if count > 0:
            conn.write(ngettext(
                '  %(count)d game displayed (of %(total)d in progress).\n',
                '  %(count)d games displayed (of %(total)d in progress).\n',
                    count) % {'count': count, 'total': len(global_.games)})

@ics_command('pfollow', 'o')
class Pfollow(Command):
    def run(self, args, conn):
        if args[0] is None:
            uf = conn.user.session.following
            if not uf or not conn.user.session.pfollow:
                conn.write(_("You are not following any player's partner's games.\n"))
            else:
                assert(uf.is_online)

                uf.session.followed_by.remove(conn.user)
                conn.user.session.following = None
                # no need to change conn.user.session.pfollow
                conn.write(_("You will not follow any player's partner's games.\n"))
        else:
            u2 = user.find_by_prefix_for_user(args[0], conn,
                online_only=True)
            if u2:
                if conn.user.session.following:
                    if u2 == conn.user.session.following and conn.user.session.pfollow:
                        conn.write(_("You are already following %s's partner's games.\n")
                            % u2.name)
                        return
                    if conn.user.session.pfollow:
                        conn.user.write(_("You will no longer be following %s's partner's games.\n") % conn.user.session.following.name)
                    else:
                        conn.user.write(_("You will no longer be following %s's games.\n") % conn.user.session.following.name)
                    conn.user.session.following.session.followed_by.remove(conn.user)
                conn.write(_("You will now be following %s's partner's games.\n")
                    % u2.name)
                conn.user.session.following = u2
                conn.user.session.pfollow = True
                u2.session.followed_by.add(conn.user)

                # If there is a game in progress and we are not already
                # observing it, start observing it.
                g = u2.session.game
                if (g and g.variant.name == 'bughouse' and
                    g.bug_link not in conn.user.session.observed and
                    conn.user not in g.players):
                    g.bug_link.observe(conn.user)

@ics_command('unobserve', 'n')
class Unobserve(Command):
    def run(self, args, conn):
        if args[0] is not None:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g in conn.user.session.observed:
                    g.unobserve(conn.user)
                else:
                    conn.write(_('You are not observing game %d.\n')
                        % g.number)
        else:
            if not conn.user.session.observed:
                conn.write(_('You are not observing any games.\n'))
            else:
                for g in conn.user.session.observed.copy():
                    g.unobserve(conn.user)
                assert(not conn.user.session.observed)

@ics_command('primary', 'n')
class Primary(Command):
    def run(self, args, conn):
        if args[0] is None:
            if not conn.user.session.observed:
                conn.write(_('You are not observing any games.\n'))
            else:
                conn.write('TODO: primary no param\n')
        else:
            g = game.from_name_or_number(args[0], conn)
            if g:
                if g in conn.user.session.observed:
                    if g == conn.user.session.observed.primary():
                        conn.write(_('Game %d is already your primary game.\n') %
                            g.number)
                    else:
                        conn.user.session.observed.make_primary(g)
                        conn.write(_('Game %d is now your primary game.\n') %
                            g.number)

                else:
                    conn.write('You are not observing game %d.\n' % g.number)

@ics_command('games', 'no')
class Games(Command):
    def run(self, args, conn):
        if not global_.games.values():
            conn.write(_('There are no games in progress.\n'))
            return
        if args[0]:
            if not isinstance(args[0], basestring):
                try:
                    games = [global_.games[args[0]]]
                except KeyError:
                    games = []
            else:
                conn.write("TODO: games string params\n")
                raise BadCommandError
        else:
            games = global_.games.values()

        # TODO: sort games, examined first, by sum of player
        # ratings

        for g in games:
            if g.gtype == game.PLAYED:
                rated_char = 'r' if g.rated else 'u'
                line = "%3d %4s %-11.11s %4s %-10.10s [ %c%c%3d %3d]" % (
                    g.number, g.white_rating, g.white_name, g.black_rating,
                    g.black_name, g.speed_variant.abbrev, rated_char,
                    g.white_time, g.inc)

                wtime = btime = '0:00' # XXX
                line = line + "%6s -%6s (%2d-%2d) %c: %2d\n\n" % (wtime, btime,
                    g.variant.pos.material[1], g.variant.pos.material[0],
                    'W' if g.variant.get_turn() else 'B',
                    g.variant.pos.ply // 2 + 1)
            elif g.gtype == game.EXAMINED:
                if g.gtype == game.EXAMINED:
                    gtype = "Exam."
                else:
                    gtype = "Setup"
                variant_char = rated_char = 'u' # XXX
                line = "%3d (%s %4d %-11.11s %4d %-10.10s) [ %c%c%3d %3d] " % (
                    g.number, gtype, g.white_rating, g.white_name,
                    g.black_rating, g.black_name, variant_char,
                    rated_char, g.white_time, g.inc)
                line = line + "%c: %2d\n\n" % (
                    'W' if g.variant.get_turn() else 'B',
                    g.variant.pos.ply // 2 + 1)
            else:
                raise RuntimeError('unknown game type: %s' % g.gtype)
            conn.write_nowrap(line)
        conn.write(ngettext('  %(count)d game displayed (of %(total)3d in progress).\n', '  %(count)d games displayed (of %(total)3d in progress).\n', len(games)) % {'count': len(games), 'total': len(global_.games)})


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
