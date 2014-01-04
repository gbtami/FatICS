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

import re

from twisted.internet import defer

import offer
import game
import block_codes
import db

from .command import ics_command, Command
from game_constants import opp, PLAYED


class GameMixin(object):
    def _get_played_game(self, conn):
        g = conn.user.session.game
        if not g or g.gtype != PLAYED:
            g = None
            conn.write(_("You are not playing a game.\n"))
        return g

    def _game_param(self, param, conn):
        """ Find a game from a command argument, currently being
        played, examined, or observed, prioritized in that order. """
        if param is not None:
            g = game.from_name_or_number(param, conn)
        else:
            if conn.user.session.game:
                g = conn.user.session.game
            elif conn.user.session.observed:
                g = conn.user.session.observed.primary()
            else:
                conn.write(_("You are not playing, examining, or observing a game.\n"))
                g = None
        return g


@ics_command('abort', 'n')
class Abort(Command, GameMixin):
    def run(self, args, conn):
        g = self._get_played_game(conn)
        if not g:
            return
        '''if len(conn.user.session.games) > 1:
            conn.write(_('Please use "simabort" for simuls.\n'))
            return'''
        g = conn.user.session.game
        if g.variant.pos.ply < 2:
            d = g.result('Game aborted on move 1 by %s' % conn.user.name, '*')
            # g.result() returns a deferred in case it needs to access
            # the db, but when aborting it should not need to
            assert(d.called)
        else:
            offer.Abort(g, conn.user)


@ics_command('adjourn', '')
class Adjourn(Command, GameMixin):
    def run(self, args, conn):
        g = self._get_played_game(conn)
        if not g:
            return
        g = conn.user.session.game
        if conn.user.is_guest or g.get_opp(conn.user).is_guest:
            conn.write(_('All players must be registered to adjourn a game.  Use "abort".\n'))
            return
        offer.Adjourn(g, conn.user)


@ics_command('draw', 'o')
class Draw(Command, GameMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is None:
            g = self._get_played_game(conn)
            if not g:
                return
            o = offer.Draw(g, conn.user)
            yield o.finish_init(g, conn.user)
        else:
            conn.write('TODO: DRAW PARAM\n')


@ics_command('resign', 'o')
class Resign(Command, GameMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            conn.write('TODO: RESIGN PLAYER\n')
            return
        g = self._get_played_game(conn)
        if g:
            yield g.resign(conn.user)


@ics_command('eco', 'oo')
class Eco(Command, GameMixin):
    eco_pat = re.compile(r'[a-e][0-9][0-9][a-z]?')
    nic_pat = re.compile(r'[a-z][a-z]\.[0-9][0-9]')

    @defer.inlineCallbacks
    def run(self, args, conn):
        g = None
        if args[1] is not None:
            assert(args[0] is not None)
            rows = []
            if args[0] == 'e':
                if not self.eco_pat.match(args[1]):
                    conn.write(_("You haven't specified a valid ECO code.\n"))
                else:
                    rows = yield db.look_up_eco(args[1])
            elif args[0] == 'n':
                if not self.nic_pat.match(args[1]):
                    conn.write(_("You haven't specified a valid NIC code.\n"))
                else:
                    rows = yield db.look_up_nic(args[1])
            else:
                self.usage(conn)
                defer.returnValue(block_codes.BLKCMD_ERROR_BADCOMMAND)
            first = True
            for row in rows:
                if not first:
                    conn.write('\n')
                else:
                    first = False
                if row['eco'] is None:
                    row['eco'] = 'A00'
                if row['nic'] is None:
                    row['nic'] = '-----'
                if row['long_'] is None:
                    row['long_'] = 'Unknown / not matched'
                assert(row['fen'] is not None)
                conn.write('  ECO: %s\n' % row['eco'])
                conn.write('  NIC: %s\n' % row['nic'])
                conn.write(' LONG: %s\n' % row['long_'])
                conn.write('  FEN: %s\n' % row['fen'])
        else:
            g = self._game_param(args[0], conn)

        if g:
            (ply, eco, long_) = yield g.get_eco()
            (nicply, nic) = yield g.get_nic()
            conn.write(_('Eco for game %d (%s vs. %s):\n') % (g.number, g.white_name, g.black_name))
            conn.write(_(' ECO[%3d]: %s\n') % (ply, eco))
            conn.write(_(' NIC[%3d]: %s\n') % (nicply, nic))
            conn.write(_('LONG[%3d]: %s\n') % (ply, long_))


@ics_command('moves', 'n')
class Moves(Command, GameMixin):
    def run(self, args, conn):
        g = self._game_param(args[0], conn)
        if g:
            g.write_moves(conn)


@ics_command('moretime', 'd')
class Moretime(Command, GameMixin):
    def run(self, args, conn):
        g = self._get_played_game(conn)
        if g:
            secs = args[0]
            if secs < 1 or secs > 36000:
                conn.write(_('Invalid number of seconds.\n'))
            else:
                g.moretime(secs, conn.user)


@ics_command('takeback', 'p')
class Takeback(Command, GameMixin):
    @defer.inlineCallbacks
    def run(self, args, conn):
        g = self._get_played_game(conn)
        if g:
            ply = args[0]
            if ply is None:
                ply = 1
            elif ply < 1:
                conn.write(_("You can't takeback less than 1 move.\n"))
                return
            o = offer.Takeback(g, conn.user, ply)
            yield o.finish_init(g, conn.user, ply)


@ics_command('flag', '')
class Flag(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if not conn.user.session.game:
            conn.write(_("You are not playing a game.\n"))
            return
        g = conn.user.session.game
        flagged = yield g.clock.check_flag(g, opp(g.get_user_side(conn.user)))
        if not flagged:
            conn.write(_('Your opponent is not out of time.\n'))


@ics_command('refresh', 'n')
class Refresh(Command, GameMixin):
    def run(self, args, conn):
        g = self._game_param(args[0], conn)
        if g:
            g.send_board(conn.user, isolated=True)


@ics_command('time', 'n')
class Time(Command, GameMixin):
    def run(self, args, conn):
        g = self._game_param(args[0], conn)
        if g:
            (white_clock, black_clock) = g.clock.as_str()
            g.send_info_str(conn.user)
            conn.write(_('White Clock : %s\n') % white_clock)
            conn.write(_('Black Clock : %s\n') % black_clock)


@ics_command('ginfo', 'n')
class Ginfo(Command, GameMixin):
    def run(self, args, conn):
        g = self._game_param(args[0], conn)
        if g:
            g.ginfo(conn)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
