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

import db


@defer.inlineCallbacks
def save_game(game, msg, result_code):
    if 'by adjudication' in msg:
        result_reason = 'Adj'
    elif 'by agreement' in msg:
        result_reason = 'Agr'
    elif 'by disconnection' in msg or 'lost connection' in msg:
        result_reason = 'Dis'
    elif 'forfeits on time' in msg:
        result_reason = 'Fla'
    elif 'checkmated' in msg:
        result_reason = 'Mat'
    elif 'either player has mating material' in msg:
        result_reason = 'NM'
    elif 'by repetition' in msg:
        result_reason = 'Rep'
    elif 'stalemate' in msg:
        result_reason = 'Sta'
    elif 'resigns' in msg:
        result_reason = 'Res'
    elif 'ran out of time' in msg:
        result_reason = 'TM'
    elif 'partner won' in msg:
        result_reason = 'PW'
    elif "Partners' game drawn" in msg:
        result_reason = 'PDr'
    # TODO add suicide PLM and WNM
    elif '50 move rule' in msg:
        result_reason = '50'
    elif 'mate on both boards' in msg:
        result_reason = 'MBB'
    else:
        raise RuntimeError('could not abbreviate result message: %s' % msg)

    data = game.tags.copy()
    data.update({
        'white_user_id': None if game.white.is_guest else game.white.id_,
        'black_user_id': None if game.black.is_guest else game.black.id_,
        'white_rating': str(game.white_rating),
        'black_rating': str(game.black_rating),
        'movetext': game.get_movetext(),
        'white_material': game.variant.pos.material[1],
        'black_material': game.variant.pos.material[0],
        'eco': (yield game.get_eco())[1],
        'ply_count': game.get_ply_count(),
        'variant_id': game.speed_variant.variant.id_,
        'speed_id': game.speed_variant.speed.id_,
        'speed_name': game.speed_variant.speed.name,
        'variant_name': game.speed_variant.variant.name,
        'clock_id': game.clock_id,
        'idn': game.idn,
        'is_rated': game.rated,
        'when_started': game.when_started,
        'when_ended': game.when_ended,
        'result': result_code,
        'result_reason': result_reason,
        'is_adjourned': 0,

        #  unused adjourned_game fields
        'adjourn_reason': None,
        'white_clock': None,  # game.clock.get_white_time(),
        'black_clock': None,  # game.clock.get_black_time(),
        'adjourn_reason': None,
        'draw_offered': None,
    })
    if game.clock_name == 'overtime':
        data.update({
            'overtime_move_num': game.overtime_move_num,
            'overtime_bonus': game.overtime_bonus
        })
    data['variant_abbrev'] = game.speed_variant.variant.abbrev
    data['speed_abbrev'] = game.speed_variant.speed.abbrev

    game_id = yield db.game_add(data)

    if game.idn is not None:
        yield db.game_add_idn(game_id, game.idn)

    flags = '%s%s%s' % (game.speed_variant.speed.abbrev,
        game.speed_variant.variant.abbrev,
        'r' if game.rated else 'u')

    if result_code == '1-0':
        white_result_char = '+'
        black_result_char = '-'
    elif result_code == '0-1':
        white_result_char = '-'
        black_result_char = '+'
    else:
        assert(result_code == '1/2-1/2')
        white_result_char = '='
        black_result_char = '='
    yield game.white.save_history(game_id, white_result_char,
        data['white_rating'], 'W', game.black.name, data['black_rating'],
        data['eco'][0:3], flags, game.white_time, game.inc, result_reason,
        game.when_ended, data['movetext'], game.idn)
    yield game.black.save_history(game_id, black_result_char,
        data['black_rating'], 'B', game.white.name, data['white_rating'],
        data['eco'][0:3], flags, game.white_time, game.inc, result_reason,
        game.when_ended, data['movetext'], game.idn)
    defer.returnValue(game_id)


@defer.inlineCallbacks
def show_for_user(user, conn):
    # XXX this is ugly and should be redesigned
    if not user.is_guest:
        yield user.load_history()
    hist = user.get_history()
    if not hist:
        conn.write(_('%s has no history games.\n') % user.name)
        return

    conn.write(_('History for %s:\n') % user.name)
    conn.write(_('                  Opponent      Type         ECO End Date\n'))
    for entry in hist:
        entry['when_ended_str'] = user.format_datetime(entry['when_ended'])
        entry['opp_str'] = entry['opp_name'][0:14]
        conn.write('%(num)2d: %(result_char)1s %(user_rating)4s %(color_char)1s %(opp_rating)4s %(opp_str)-14s[%(flags)3s%(time)3s %(inc)3s] %(eco)-3s %(result_reason)-3s %(when_ended_str)-s\n' %
            entry)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
