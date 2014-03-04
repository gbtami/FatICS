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
import copy
import random
from array import array

from game_constants import (WHITE, BLACK, valid_sq, rank, file_)
from variant.base_variant import BaseVariant, IllegalMoveError
"""
0x88 board representation; pieces are represented as ASCII,
the same as FEN. A blank square is '-'.
"""


class BadFenError(Exception):
    def __init__(self, reason=None):
        self.reason = reason

piece_moves = {
    'n': [-0x21, -0x1f, -0xe, -0x12, 0x12, 0xe, 0x1f, 0x21],
    'b': [-0x11, -0xf, 0xf, 0x11],
    'r': [-0x10, -1, 1, 0x10],
    'q': [-0x11, -0xf, 0xf, 0x11, -0x10, -1, 1, 0x10],
    'k': [-0x11, -0xf, 0xf, 0x11, -0x10, -1, 1, 0x10]
}
direction_table = array('i', [0 for i in range(0, 0x100)])


def dir(fr, to):
    """Returns the direction a queen needs to go to get from TO to FR,
    or 0 if it's not possible."""
    return direction_table[to - fr + 0x7f]

sliding_pieces = frozenset(['b', 'r', 'q', 'B', 'R', 'Q'])

# Use suicide piece values rather than those for normal chess:
piece_material = {
    '-': 0,
    'p': 1,
    'n': 1,
    'b': 1,
    'r': 1,
    'q': 1,
    'k': 1
}


def str_to_sq(s):
    return 'abcdefgh'.index(s[0]) + 0x10 * '12345678'.index(s[1])


def sq_to_str(sq):
    return 'abcdefgh'[file_(sq)] + '12345678'[rank(sq)]


def piece_is_white(pc):
    assert(len(pc) == 1)
    assert(pc in 'pnbrqkPNBRQK')
    return pc.isupper()


class Zobrist(object):
    """Zobrist keys for low-overhead repetition detection"""
    _piece_index = {
        'p': 0, 'n': 1, 'b': 2, 'r': 3, 'q': 4, 'k': 5,
        'P': 6, 'N': 7, 'B': 8, 'R': 9, 'Q': 10, 'K': 11
    }

    # Note: using 64-bit hashes, the expected number of positions
    # before a collision is 2^32.  Given that a collision has to
    # occur within one game to be meaningful, and games are no
    # longer than 5949 moves, the chance of any affect should be
    # negligible.
    def __init__(self):
        random.seed(2010)
        self.side_hash = random.getrandbits(64)
        self._piece = self._rand_list(0x10 * 0x80)
        self._ep = self._rand_list(8)
        random.seed()

    def piece_hash(self, sq, pc):
        assert((0xf << 7) & sq == 0)
        assert(valid_sq(sq))
        return self._piece[(self._piece_index[pc] << 7) | sq]

    def ep_hash(self, ep):
        return self._ep[file_(ep)]

    def _rand_list(self, len):
        return [random.getrandbits(64) for i in xrange(0, len)]

zobrist = Zobrist()


class Move(object):
    def __init__(self, pos, fr, to, prom=None, is_ep=False, new_ep=None):
        self.pos = pos
        self.fr = fr
        self.to = to
        self.pc = self.pos.board[self.fr]
        self.prom = prom
        self.capture = pos.board[to]
        self.is_capture = self.capture != '-'
        self.is_ep = is_ep
        self.new_ep = new_ep
        self.time = None
        self.clock_time = None
        self._san = None
        self._verbose_alg = None
        self.lag = 0

        # if a promotion piece is not given, assume queen
        if not self.prom:
            if self.pc == 'p' and rank(to) == 0:
                self.prom = 'q'
            elif self.pc == 'P' and rank(to) == 7:
                self.prom = 'Q'

    def __str__(self):
        s = '%s%s' % (sq_to_str(self.fr), sq_to_str(self.to))
        if self.prom:
            s += '=%s' % self.prom
        return s

    def check_pseudo_legal(self):
        """Tests if a move is pseudo-legal, that is, legal ignoring the
        fact that a capture must be made if possible. Also sets en passant
        flags for this move. This is used for long algebraic moves,
        but not san, which does these checks implicitly."""

        if self.pc == '-' or piece_is_white(self.pc) != self.pos.wtm:
            raise IllegalMoveError('can only move own pieces')

        if self.is_capture and piece_is_white(self.capture) == self.pos.wtm:
            raise IllegalMoveError('cannot capture own piece')

        diff = self.to - self.fr
        if self.pc == 'p':
            if self.pos.board[self.to] == '-':
                if diff == -0x10:
                    pass
                elif diff == -0x20 and rank(self.fr) == 6:
                    self.new_ep = self.fr - 0x10
                    if self.pos.board[self.new_ep] != '-':
                        raise IllegalMoveError('bad en passant')
                elif diff in [-0x11, -0xf] and self.to == self.pos.ep:
                    self.is_ep = True
                else:
                    raise IllegalMoveError('bad pawn push')
            else:
                if not diff in [-0x11, -0xf]:
                    raise IllegalMoveError('bad pawn capture')
        elif self.pc == 'P':
            if self.pos.board[self.to] == '-':
                if diff == 0x10:
                    pass
                elif diff == 0x20 and rank(self.fr) == 1:
                    self.new_ep = self.fr + 0x10
                    if self.pos.board[self.new_ep] != '-':
                        raise IllegalMoveError('bad en passant')
                elif diff in [0x11, 0xf] and self.to == self.pos.ep:
                    self.is_ep = True
                else:
                    raise IllegalMoveError('bad pawn push')
            else:
                if not diff in [0x11, 0xf]:
                    raise IllegalMoveError('bad pawn capture')
        else:
            if self.pc in sliding_pieces:
                d = dir(self.fr, self.to)
                if d == 0 or not d in piece_moves[self.pc.lower()]:
                    raise IllegalMoveError('piece cannot make that move')
                # now check if there are any pieces in the way
                cur_sq = self.fr + d
                while cur_sq != self.to:
                    assert(valid_sq(cur_sq))
                    if self.pos.board[cur_sq] != '-':
                        raise IllegalMoveError('sliding piece blocked')
                    cur_sq += d
            else:
                if not diff in piece_moves[self.pc.lower()]:
                    raise IllegalMoveError('piece cannot make that move')

    def check_legal(self):
        """Test whether a move ignores a possible capture.
        This test is common to all move formats."""
        if not self.is_capture and not self.is_ep:
            for (sq, pc) in self.pos:
                if (pc != '-' and
                        (self.pos.wtm != piece_is_white(pc)) and
                        self.pos.under_attack(sq, self.pos.wtm)):
                    raise IllegalMoveError('must capture')

    def to_san(self):
        if self._san is None:
            self._san = self._to_san()
        return self._san

    def _to_san(self):
        if self.pc in ['P', 'p']:
            san = ''
            if self.is_capture or self.is_ep:
                san += 'abcdefgh'[file_(self.fr)] + 'x'
            san += sq_to_str(self.to)
            if self.prom:
                san += '=' + self.prom.upper()
        else:
            assert(not self.is_ep)
            san = self.pc.upper()
            ambigs = self.pos.get_from_sqs(self.pc, self.to)
            assert(len(ambigs) >= 1)
            if len(ambigs) > 1:
                r = rank(self.fr)
                f = file_(self.fr)
                # try disambiguating with file
                if len(filter(lambda sq: file_(sq) == f, ambigs)) == 1:
                    san += 'abcdefgh'[f]
                elif len(filter(lambda sq: rank(sq) == r, ambigs)) == 1:
                    san += '12345678'[r]
                else:
                    san += sq_to_str(self.fr)
            if self.is_capture:
                san += 'x'
            san += sq_to_str(self.to)
        return san

    def to_verbose_alg(self):
        if self._verbose_alg is None:
            self._verbose_alg = self._to_verbose_alg()
        return self._verbose_alg

    def _to_verbose_alg(self):
        """convert to the verbose notation used in style12"""
        ret = self.pc.upper() + '/'
        ret += sq_to_str(self.fr)
        ret += '-'
        ret += sq_to_str(self.to)
        if self.prom:
            ret += '=' + self.prom.upper()
        return ret

    def to_smith(self):
        """ Convert to Smith notation. """
        ret = []
        ret.append(sq_to_str(self.fr))
        ret.append(sq_to_str(self.to))
        if self.is_capture:
            ret.append(self.capture.lower())
        if self.prom:
            ret.append(self.prom.upper())
        if self.is_ep:
            ret.append('E')
        return ''.join(ret)

    def is_legal(self):
        try:
            self.check_legal()
        except IllegalMoveError:
            return False
        else:
            return True


class Undo(object):
    """information needed to undo a move"""
    pass


class PositionHistory(object):
    """keeps past of past positions for repetition detection"""
    def __init__(self):
        self.hashes = [None] * 40
        self.moves = [None] * 40

    def set_hash(self, ply, hash):
        if ply >= len(self.hashes):
            self.hashes.extend([None] * (ply - len(self.hashes) + 1))
        self.hashes[ply] = hash

    def set_move(self, ply, mv):
        if ply >= len(self.moves):
            self.moves.extend([None] * (ply - len(self.moves) + 1))
        self.moves[ply] = mv

    def get_hash(self, ply):
        return self.hashes[ply]

    def get_move(self, ply):
        return self.moves[ply]


class Position(object):
    def __init__(self, fen):
        self.board = array('c', 0x80 * ['-'])
        self.history = PositionHistory()
        self.set_pos(fen)
        self.is_draw_nomaterial = False # never happens in suicide
        self.white_has_mating_material = True
        self.black_has_mating_material = True

    set_pos_re = re.compile(r'''^([1-8rnbqkpRNBQKP/]+) ([wb]) (-) ([a-h][36]|-) (\d+) (\d+)$''')
    def set_pos(self, fen):
        """Set the position from Forsyth-Fdwards notation.  The format
        is intentionally interpreted strictly; better to give the user an
        error than take in bad data."""
        try:
            # rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1
            m = self.set_pos_re.match(fen)
            if not m:
                raise BadFenError('does not look like FEN')
            (pos, side, castle_flags, ep, fifty_count, full_moves) = [
                m.group(i) for i in range(1, 7)]

            ranks = pos.split('/')
            ranks.reverse()
            self.hash = 0
            self.material = [0, 0]
            for (r, rank_str) in enumerate(ranks):
                sq = 0x10 * r
                for c in rank_str:
                    d = '12345678'.find(c)
                    if d >= 0:
                        sq += d + 1
                    else:
                        assert(valid_sq(sq))
                        self.board[sq] = c
                        self.hash ^= zobrist.piece_hash(sq, c)
                        self.material[piece_is_white(c)] += \
                            piece_material[c.lower()]
                        if c.lower() == 'p':
                            if rank(sq) in [0, 7]:
                                # pawn on 1st or 8th rank
                                raise BadFenError()
                        sq += 1
                if sq & 0xf != 8:
                    # wrong row length
                    raise BadFenError()

            self.wtm = side == 'w'
            if self.wtm:
                self.hash ^= zobrist.side_hash

            self.fifty_count = int(fifty_count, 10)
            self.ply = 2 * (int(full_moves, 10) - 1) + int(not self.wtm)
            self.start_ply = self.ply # 0 for new games

            if ep == '-':
                self.ep = None
            else:
                # only set ep if there is a legal capture
                # XXX: this is even stricter than X-FEN; maybe
                # we should not check for true legality, but only
                # whether there is an enemy pawn on an adjacent
                # square?
                self.ep = 'abcdefgh'.index(ep[0]) + \
                    0x10 * '1234567'.index(ep[1])
                if rank(self.ep) not in (2, 5):
                    raise BadFenError('bad en passant square')
                self.hash ^= zobrist.ep_hash(self.ep)

            #assert(self.hash == self._compute_hash())
            self.history.set_hash(self.ply, self.hash)

        except AssertionError:
            raise
        # Usually I don't like using a catch-all except, but it seems to
        # be the safest default action because the FEN is supplied by
        # the user.
        #except:
        #    raise BadFenError()

    def __iter__(self):
        for r in range(0, 8):
            for f in range(0, 8):
                sq = 0x10 * r + f
                yield (sq, self.board[sq])

    def make_move(self, mv):
        """make the move"""
        self.ply += 1

        mv.undo = Undo()
        mv.undo.ep = self.ep
        mv.undo.fifty_count = self.fifty_count
        mv.undo.material = self.material[:]
        mv.undo.hash = self.hash

        if self.ep:
            # clear old en passant hash
            self.hash ^= zobrist.ep_hash(self.ep)
            self.ep = None
        self.board[mv.fr] = '-'
        if not mv.prom:
            self.board[mv.to] = mv.pc
            self.hash ^= zobrist.piece_hash(mv.fr, mv.pc) ^ \
                zobrist.piece_hash(mv.to, mv.pc)
        else:
            self.board[mv.to] = mv.prom
            self.hash ^= zobrist.piece_hash(mv.fr, mv.pc) ^\
                zobrist.piece_hash(mv.to, mv.prom)
            self.material[self.wtm] += piece_material[mv.prom.lower()] \
                - piece_material['p']

        if mv.pc in ['p', 'P'] or mv.is_capture:
            self.fifty_count = 0
        else:
            self.fifty_count += 1

        if mv.is_capture:
            self.hash ^= zobrist.piece_hash(mv.to, mv.capture)
            self.material[not self.wtm] -= piece_material[mv.capture.lower()]

        if mv.is_ep:
            self.material[not self.wtm] -= piece_material['p']
            # remove the captured pawn
            if self.wtm:
                assert(self.board[mv.to - 0x10] == 'p')
                self.hash ^= zobrist.piece_hash(mv.to - 0x10, 'p')
                self.board[mv.to - 0x10] = '-'
            else:
                assert(self.board[mv.to + 0x10] == 'P')
                self.hash ^= zobrist.piece_hash(mv.to + 0x10, 'P')
                self.board[mv.to + 0x10] = '-'

        self.wtm = not self.wtm
        self.hash ^= zobrist.side_hash
        #self._check_material()

        if mv.new_ep:
            self.ep = mv.new_ep
            self.hash ^= zobrist.ep_hash(self.ep)

        self.history.set_move(self.ply - 1, mv)
        #assert(self.hash == self._compute_hash())
        self.history.set_hash(self.ply, self.hash)

    def _compute_hash(self):
        hash = 0
        if self.wtm:
            hash ^= zobrist.side_hash
        for (sq, pc) in self:
            if pc != '-':
                hash ^= zobrist.piece_hash(sq, pc)
        if self.ep:
            hash ^= zobrist.ep_hash(self.ep)
        return hash

    def undo_move(self, mv):
        """undo the move"""
        self.wtm = not self.wtm
        self.ply -= 1
        self.ep = mv.undo.ep
        self.board[mv.to] = mv.capture
        self.board[mv.fr] = mv.pc
        self.fifty_count = mv.undo.fifty_count
        self.material = mv.undo.material
        self.hash = mv.undo.hash

        if mv.is_ep:
            if self.wtm:
                assert(self.board[mv.to - 0x10] == '-')
                self.board[mv.to - 0x10] = 'p'
            else:
                assert(self.board[mv.to + 0x10] == '-')
                self.board[mv.to + 0x10] = 'P'
        #self._check_material()
        #assert(self.hash == self._compute_hash())

    def _check_material(self):
        bmat = sum([piece_material[pc.lower()]
            for (sq, pc) in self if pc != '-' and not piece_is_white(pc)])
        assert(bmat == self.material[0])
        assert(self.material[1] == sum([piece_material[pc.lower()]
            for (sq, pc) in self if pc != '-' and piece_is_white(pc)]))

    def detect_check(self):
        """detect whether the player to move is out of material
        (has committed suicide) or stalemated, or if the game
        is drawn by opposite color bishops"""
        self.is_suicide = not any(pc != '-' and
            (piece_is_white(pc) if self.wtm else not piece_is_white(pc))
            for (sq, pc) in self)

        self.is_stalemate = not self._any_legal_moves()
        if self.is_stalemate:
            white_material = sum(piece_material[pc.lower()]
                for (sq, pc) in self if pc != '-' and piece_is_white(pc))
            black_material = sum(piece_material[pc.lower()]
                for (sq, pc) in self if pc != '-' and not piece_is_white(pc))
            self.is_stalemate_white = white_material < black_material
            self.is_stalemate_black = white_material > black_material

        self.is_draw_bishops = False
        for (sq, pc) in self:
            if pc == 'B':
                if (rank(sq) ^ file_(sq)) & 1 != 0:
                    break
            elif pc == 'b':
                if (rank(sq) ^ file_(sq)) & 1 == 0:
                    break
            elif pc != '-':
                break
        else:
            self.is_draw_bishops = True
            return

        for (sq, pc) in self:
            if pc == 'B':
                if (rank(sq) ^ file_(sq)) & 1 == 0:
                    break
            elif pc == 'b':
                if (rank(sq) ^ file_(sq)) & 1 != 0:
                    break
            elif pc != '-':
                break
        else:
            self.is_draw_bishops = True

    def get_last_move(self):
        return self.history.get_move(self.ply - 1)

    def _any_legal_moves(self):
        if self.ep:
            return True
        for (sq, pc) in self:
            if pc != '-' and piece_is_white(pc) == self.wtm:
                if self._any_pc_moves(sq, pc):
                    return True
        return False

    def _pawn_cap_at(self, sq):
        if not valid_sq(sq):
            return False
        pc = self.board[sq]
        return pc != '-' and piece_is_white(pc) != self.wtm

    def _any_pc_moves(self, sq, pc):
        if pc == 'P':
            if self.board[sq + 0x10] == '-':
                return True
            if self._pawn_cap_at(sq + 0xf):
                return True
            if self._pawn_cap_at(sq + 0x11):
                return True
        elif pc == 'p':
            if self.board[sq - 0x10] == '-':
                return True
            if self._pawn_cap_at(sq - 0xf):
                return True
            if self._pawn_cap_at(sq - 0x11):
                return True
        else:
            for d in piece_moves[pc.lower()]:
                cur_sq = sq + d
                while valid_sq(cur_sq):
                    topc = self.board[cur_sq]
                    if topc == '-' or piece_is_white(topc) != self.wtm:
                        return True
                    if not pc in sliding_pieces or self.board[cur_sq] != '-':
                        break
                    cur_sq += d

    def _is_pc_at(self, pc, sq):
        return valid_sq(sq) and self.board[sq] == pc

    def under_attack(self, sq, wtm):
        """determine whether a square is attacked by the given side"""
        # pawn attacks
        if wtm:
            if (self._is_pc_at('P', sq - 0x11)
                    or self._is_pc_at('P', sq - 0xf)):
                return True
        else:
            if (self._is_pc_at('p', sq + 0x11)
                    or self._is_pc_at('p', sq + 0xf)):
                return True

        #  knight attacks
        npc = 'N' if wtm else 'n'
        for d in piece_moves['n']:
            if self._is_pc_at(npc, sq + d):
                return True

        # king attacks
        kpc = 'K' if wtm else 'k'
        for d in piece_moves['k']:
            if self._is_pc_at(kpc, sq + d):
                return True

        # bishop/queen attacks
        for d in piece_moves['b']:
            cur_sq = sq + d
            while valid_sq(cur_sq):
                if self.board[cur_sq] != '-':
                    if wtm:
                        if self.board[cur_sq] in ['B', 'Q']:
                            return True
                    else:
                        if self.board[cur_sq] in ['b', 'q']:
                            return True
                    # square blocked
                    break
                cur_sq += d

        # rook/queen attacks
        for d in piece_moves['r']:
            cur_sq = sq + d
            while valid_sq(cur_sq):
                if self.board[cur_sq] != '-':
                    if wtm:
                        if self.board[cur_sq] in ['R', 'Q']:
                            return True
                    else:
                        if self.board[cur_sq] in ['r', 'q']:
                            return True
                    # square blocked
                    break
                cur_sq += d

        return False

    lalg_re = re.compile(r'([a-h][1-8])-?([a-h][1-8])(?:=([KNBRQ]))?$', re.I)
    def move_from_lalg(self, s):
        m = self.lalg_re.match(s)
        if not m:
            return None

        fr = str_to_sq(m.group(1).lower())
        to = str_to_sq(m.group(2).lower())
        prom = m.group(3)
        if prom is None:
            mv = Move(self, fr, to)
        else:
            if self.wtm:
                mv = Move(self, fr, to, prom=prom.upper())
            else:
                mv = Move(self, fr, to, prom=prom.lower())

        if mv:
            mv.check_pseudo_legal()
            mv.check_legal()

        return mv

    san_pawn_push_re = re.compile(r'^([a-h][1-8])(?:=([KNBRQ]))?$')
    san_pawn_capture_re = re.compile(r'^([a-h])x([a-h][1-8])(?:=([KNBRQ]))?$')
    san_piece_re = re.compile(r'([KNBRQK])([a-h])?([1-8])?(x)?([a-h][1-8])$')
    decorator_re = re.compile(r'[\+#\?\!]+$')
    def move_from_san(self, s):
        s = self.decorator_re.sub('', s)
        mv = None

        # examples: e4 e8=Q
        m = self.san_pawn_push_re.match(s)
        if m:
            to = str_to_sq(m.group(1))
            if self.board[to] != '-':
                raise IllegalMoveError('pawn push blocked')
            prom = m.group(2)
            if prom:
                if self.wtm:
                    prom = m.group(2)
                    assert(prom == prom.upper())
                else:
                    prom = m.group(2).lower()
            new_ep = None
            if self.wtm:
                fr = to - 0x10
                if rank(to) == 3 and self.board[fr] == '-':
                    new_ep = fr
                    fr = to - 0x20
                if self.board[fr] != 'P':
                    raise IllegalMoveError('illegal white pawn move')
                if prom:
                    if rank(to) == 7:
                        mv = Move(self, fr, to, prom=prom)
                    else:
                        raise IllegalMoveError('illegal promotion')
                else:
                    mv = Move(self, fr, to, new_ep=new_ep)
            else:
                fr = to + 0x10
                if rank(to) == 4 and self.board[fr] == '-':
                    new_ep = fr
                    fr = to + 0x20
                if self.board[fr] != 'p':
                    raise IllegalMoveError('illegal black pawn move')
                if prom:
                    if rank(to) == 0:
                        mv = Move(self, fr, to, prom=prom)
                    else:
                        raise IllegalMoveError('illegal promotion')
                else:
                    mv = Move(self, fr, to, new_ep=new_ep)

        # examples: dxe4 dxe8=Q
        m = None
        if not mv:
            m = self.san_pawn_capture_re.match(s)
        if m:
            to = str_to_sq(m.group(2))
            prom = m.group(3)
            if prom:
                if self.wtm:
                    assert(prom == prom.upper())
                else:
                    prom = prom.lower()

            is_ep = to == self.ep
            if is_ep:
                assert(self.board[to] == '-')
            else:
                topc = self.board[to]
                if topc == '-' or piece_is_white(topc) == self.wtm:
                    raise IllegalMoveError('bad pawn capture')

            f = 'abcdefgh'.index(m.group(1))
            if f == file_(to) - 1:
                if self.wtm:
                    fr = to - 0x11
                    if self.board[fr] != 'P':
                        raise IllegalMoveError('bad pawn capture')
                else:
                    fr = to + 0xf
                    if self.board[fr] != 'p':
                        raise IllegalMoveError('bad pawn capture')
            elif f == file_(to) + 1:
                if self.wtm:
                    fr = to - 0xf
                    if self.board[fr] != 'P':
                        raise IllegalMoveError('bad pawn capture')
                else:
                    fr = to + 0x11
                    if self.board[fr] != 'p':
                        raise IllegalMoveError('bad pawn capture')
            else:
                raise IllegalMoveError('bad pawn capture file')

            mv = Move(self, fr, to, prom=prom, is_ep=is_ep)

        # examples: Nf3 Nxf3 Ng1xf3
        m = None
        if not mv:
            m = self.san_piece_re.match(s)
        if m:
            to = str_to_sq(m.group(5))
            if m.group(4):
                # capture
                if self.board[to] == '-':
                    raise IllegalMoveError('capture on blank square')
                if piece_is_white(self.board[to]) == self.wtm:
                    raise IllegalMoveError('capture own piece')
            else:
                if self.board[to] != '-':
                    raise IllegalMoveError('missing "x" to indicate capture')

            pc = m.group(1) if self.wtm else m.group(1).lower()
            # TODO: it would be faster to disambiguate first, so we
            # do not check whether moves are legal unnecessarily
            froms = self.get_from_sqs(pc, to)

            if m.group(2):
                if len(froms) <= 1:
                    raise IllegalMoveError('unnecessary disambiguation')
                f = 'abcdefgh'.index(m.group(2))
                froms = filter(lambda sq: file_(sq) == f, froms)

            if m.group(3):
                r = '12345678'.index(m.group(3))
                if len(froms) <= 1:
                    raise IllegalMoveError('unnecessary disambiguation')
                froms = filter(lambda sq: rank(sq) == r, froms)

            if len(froms) != 1:
                raise IllegalMoveError('illegal or ambiguous move %s: %d interpretations' % (s, len(froms)))

            mv = Move(self, froms[0], to)

        if mv:
            # Unlike regular chess, moves that look legal to the SAN
            # parser may be illegal due to failing to capture a piece.
            '''try:
                mv.check_pseudo_legal()
            except IllegalMoveError:
                raise RuntimeError('san inconsistency')'''
            mv.check_legal()

        return mv

    def get_from_sqs(self, pc, sq):
        '''given a piece (not including a pawn) and a destination square,
        return a list of all legal source squares'''
        ret = []
        is_sliding = pc in sliding_pieces
        for d in piece_moves[pc.lower()]:
            cur_sq = sq
            while 1:
                cur_sq += d
                if not valid_sq(cur_sq):
                    break
                if self.board[cur_sq] == pc:
                    if Move(self, cur_sq, sq).is_legal():
                        ret.append(cur_sq)
                if not (self.board[cur_sq] == '-' and is_sliding):
                    break
        return ret

    def is_draw_fifty(self):
        return self.fifty_count >= 100

    def is_draw_repetition(self, side):
        #assert(self.hash == self._compute_hash())
        """check for draw by repetition"""

        # Note that the most recent possible identical position is
        # 4 ply ago, and we only have to check every other move.
        # This is a well-known chess engine optimization.
        if self.ply < 8:
            return False
        stop = max(self.ply - self.fifty_count, self.start_ply)

        count = 0
        hash = self.history.get_hash(self.ply)
        i = self.ply - 4
        while i >= stop:
            if self.history.get_hash(i) == hash:
                count += 1
                if count == 2:
                    return True
            i -= 2

        # Also check the previous position, because unlike OTB chess,
        # we do not provide a way to write down a move and offer a draw
        # without actually executing the move.  (Well, we do: an argument to
        # the "draw" command, but few people know about it.)
        #
        # Previously, FICS allowed either player to claim a draw if the
        # current or previous position represented a threefold repetition,
        # regardless of which player's move it was.  (Note that this is
        # different from FIDE rules, which only consider the current
        # position and only allow a player to claim a draw on his or her
        # own turn.)  My idea is to only check the previous position
        # when the player making the draw offer has the move, to avoid
        # a situation like the following:
        #
        # Player A has the move.  The current position represents a
        # threefold repetition, so player A is entitled to claim a draw.
        # Instead, Player A decides to press on, and plays a blunder
        # that loses his queen.  Player A realizes the mistake before
        # the opponent has a chance to move, and claims a draw.
        #
        # The old fics grants the draw request, unreasonably in my
        # opinion.  My change should close the loophole.
        if self.ply > 8 and (side == WHITE) == self.wtm:
            count = 0
            hash = self.history.get_hash(self.ply - 1)
            i = self.ply - 5
            while i >= stop:
                if self.history.get_hash(i) == hash:
                    count += 1
                    if count == 2:
                        return True
                i -= 2

        return False

    def to_xfen(self):
        p = []
        for r in range(7, -1, -1):
            num_empty = 0
            for f in range(0, 8):
                sq = 0x10 * r + f
                pc = self.board[sq]
                if pc == '-':
                    num_empty += 1
                else:
                    if num_empty > 0:
                        p.append(str(num_empty))
                        num_empty = 0
                    p.append(pc)
            if num_empty > 0:
                p.append(str(num_empty))
                num_empty = 0
            if r != 0:
                p.append('/')
        pos_str = ''.join(p)

        stm_str = 'w' if self.wtm else 'b'

        castling = '-'

        # we follow X-FEN rather than FEN: only print an en passant
        # square if there is a legal en passant capture
        if self.ep:
            ep_str = sq_to_str(self.ep)
            assert(ep_str[1] in ['3', '6'])
        else:
            ep_str = '-'

        full_moves = self.ply // 2 + 1
        return "%s %s %s %s %d %d" % (pos_str, stm_str, castling, ep_str, self.fifty_count, full_moves)

    def check_castle_flags(self, wtm, is_oo):
        return False


class Suicide(BaseVariant):
    """suicide chess"""
    def __init__(self, game):
        self.game = game
        self.pos = copy.deepcopy(initial_pos)
        self.name = 'suicide'

    def parse_move(self, s, conn):
        """Try to parse a move.  If it looks like a move but
        is erroneous or illegal, raise an exception.  Return the move if
        parsing was sucessful, or False if it does not look like a move
        and should be processed further."""

        mv = None

        try:
            # san
            # this needs to come before long algebraic, because in a few rare
            # cases a move can be ambiguous. One example was "B5f4" (a legal
            # SAN move that occurred after a computer had promoted to give
            # itself two bishops of the same color), which was tripping up
            # the lalg parser.
            if not mv:
                mv = self.pos.move_from_san(s)

            # long algebraic
            if not mv:
                mv = self.pos.move_from_lalg(s)

        except IllegalMoveError:
            #print e.reason
            raise

        return mv

    def do_move(self, mv):
        mv.to_san()
        self.pos.make_move(mv)
        self.pos.detect_check()

    def undo_move(self):
        self.pos.undo_move(self.pos.get_last_move())

    def get_turn(self):
        return WHITE if self.pos.wtm else BLACK

    def to_deltaboard(self, user):
        """ Get the last move in the shortened format used by clients that
        set the "compressmove" ivar. """
        last_mv = self.pos.get_last_move()
        # delta boards should not be sent before the first move
        assert(last_mv is not None)
        assert(last_mv.time is not None)
        last_mv_time = int(round(1000 * last_mv.time))
        if self.pos.wtm:
            clock = int(round(1000 * self.game.clock.get_black_time()))
        else:
            clock = int(round(1000 * self.game.clock.get_white_time()))
        # <d1> 399 10 O-O e8g8c 922 168890 207
        s = '\n<d1> %d %d %s %s %d %d %d\n' % (
            self.game.number, self.pos.ply, last_mv.to_san(),
            last_mv.to_smith(), last_mv_time, clock, last_mv.lag)

        return s


def init_direction_table():
    for r in range(8):
        for f in range(8):
            sq = 0x10 * r + f
            for d in piece_moves['q']:
                cur_sq = sq + d
                while valid_sq(cur_sq):
                    assert(0 <= cur_sq - sq + 0x7f <= 0xff)
                    if direction_table[cur_sq - sq + 0x7f] != 0:
                        assert(d == direction_table[cur_sq - sq + 0x7f])
                    else:
                        direction_table[cur_sq - sq + 0x7f] = d
                    cur_sq += d
init_direction_table()

initial_pos = Position('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1')

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
