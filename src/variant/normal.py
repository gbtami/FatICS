"""This implements routines for normal chess.  (I avoid the term
standard since that is used to describe the game speed on FICS.)
Maybe normal chess technically not a variant, but organizationally
I didn't want to privilege it over variants, so it is here. """

import re
import copy
import random
from array import array

from variant import Variant
import game

"""
0x88 board representation; pieces are represented as ASCII,
the same as FEN. A blank square is '-'.

"""

[A8, B8, C8, D8, E8, F8, G8, H8] = range(0x70, 0x78)
[A7, B7, C7, D7, E7, F7, G7, H7] = range(0x60, 0x68)
[A6, B6, C6, D6, E6, F6, G6, H6] = range(0x50, 0x58)
[A5, B5, C5, D5, E5, F5, G5, H5] = range(0x40, 0x48)
[A4, B4, C4, D4, E4, F4, G4, H4] = range(0x30, 0x38)
[A3, B3, C3, D3, E3, F3, G3, H3] = range(0x20, 0x28)
[A2, B2, C2, D2, E2, F2, G2, H2] = range(0x10, 0x18)
[A1, B1, C1, D1, E1, F1, G1, H1] = range(0x00, 0x08)

class BadFenError(Exception):
    def __init__(self, reason=None):
        self.reason = reason
class IllegalMoveError(Exception):
    def __init__(self, reason):
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

piece_material = {
    '-': 0,
    'p': 1,
    'n': 3,
    'b': 3,
    'r': 5,
    'q': 9,
    'k': 0
}

def to_castle_flags(w_oo, w_ooo, b_oo, b_ooo):
    return (w_oo << 3) + (w_ooo << 2) + (b_oo << 1) + b_ooo

def check_castle_flags(mask, wtm, is_oo):
    return bool(mask & (1 << (2 * int(wtm) + int(is_oo))))

castle_mask = array('i', [0xf for i in range(0x80)])
castle_mask[A8] = to_castle_flags(True, True, True, False)
castle_mask[E8] = to_castle_flags(True, True, False, False)
castle_mask[H8] = to_castle_flags(True, True, False, True)
castle_mask[A1] = to_castle_flags(True, False, True, True)
castle_mask[E1] = to_castle_flags(False, False, True, True)
castle_mask[H1] = to_castle_flags(False, True, True, True)

def rank(sq):
    return sq // 0x10

def file(sq):
    return sq % 8

def valid_sq(sq):
    return not (sq & 0x88)

def str_to_sq(s):
    return 'abcdefgh'.index(s[0]) + 0x10 * '12345678'.index(s[1])

def sq_to_str(sq):
    return 'abcdefgh'[file(sq)] + '12345678'[rank(sq)]

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

    # Note: using 64-bit keys, the expected number of positions
    # before a collision is 2^32.  Given that a collision has to
    # occur within one game to be meaningful, and games are no
    # longer than 5949 moves, the chance of any affect should be
    # negligible.
    def __init__(self):
        random.seed(2010)
        self.side_hash = random.getrandbits(64)
        self._piece = self._rand_list(0x10 * 0x80)
        self._ep = self._rand_list(8)
        self._castle = self._rand_list(0x10)
        random.seed()

    def piece_hash(self, sq, pc):
        assert((0xf << 7) & sq == 0)
        assert(valid_sq(sq))
        return self._piece[(self._piece_index[pc] << 7) | sq]

    def ep_hash(self, ep):
        return self._ep[file(ep)]

    def castle_hash(self, flags):
        assert(flags & ~0xf == 0)
        return self._castle[flags]

    def _rand_list(self, len):
        return [random.getrandbits(64) for i in xrange(0, len)]

zobrist = Zobrist()

class Move(object):
    def __init__(self, pos, fr, to, prom=None, is_oo=False,
            is_ooo=False, is_ep=False, new_ep=None):
        self.pos = pos
        self.fr = fr
        self.to = to
        self.pc = self.pos.board[self.fr]
        self.prom = prom
        self.is_oo = is_oo
        self.is_ooo = is_ooo
        self.capture = pos.board[to]
        self.is_capture = self.capture != '-'
        self.is_ep = is_ep
        self.new_ep = new_ep

    def __str__(self):
        s = '%s%s' % (sq_to_str(self.fr), sq_to_str(self.to))
        if self.prom:
            s += '=%s' % self.prom
        return s

    def check_pseudo_legal(self):
        """Tests if a move is pseudo-legal, that is, legal ignoring the
        fact that the king cannot be left in check. Also sets en passant
        flags for this move. This is used for long algebraic moves,
        but not san, which does these checks implicitly."""
        
        if self.pc == '-' or piece_is_white(self.pc) != self.pos.wtm:
            raise IllegalMoveError('can only move own pieces')
       
        if self.is_capture and piece_is_white(self.capture) == self.pos.wtm:
            raise IllegalMoveError('cannot capture own piece')

        if self.is_oo or self.is_ooo:
            return

        diff = self.to - self.fr
        if self.pc == 'p':
            if self.pos.board[self.to] == '-':
                if diff == -0x10:
                    pass
                elif diff == -0x20 and rank(self.fr) == 6:
                    self.new_ep = self.fr + -0x10
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
        """Test whether a move leaves the king in check, or if
        castling if blocked or otherwise unavailable.  These
        tests are grouped together because they are common
        to all move formats."""
        if self.is_oo:
            if (self.pos.in_check
                    or not check_castle_flags(self.pos.castle_flags,
                        self.pos.wtm, True)
                    or self.pos.board[self.fr + 1] != '-'
                    or self.pos.under_attack(self.fr + 1, not self.pos.wtm)
                    or self.pos.under_attack(self.to, not self.pos.wtm)):
                raise IllegalMoveError('illegal castling')
            return

        if self.is_ooo:
            if (self.pos.in_check
                    or not check_castle_flags(self.pos.castle_flags,
                        self.pos.wtm, False)
                    or self.pos.board[self.fr - 1] != '-'
                    or self.pos.under_attack(self.fr - 1, not self.pos.wtm)
                    or self.pos.under_attack(self.to, not self.pos.wtm)):
                raise IllegalMoveError('illegal castling')
            return

        self.pos.make_move(self)
        try:
            if self.pos.under_attack(self.pos.king_pos[not self.pos.wtm],
                    self.pos.wtm):
                raise IllegalMoveError('leaves king in check')
        finally:
            self.pos.undo_move(self)

    def to_san(self):
        if self.is_oo:
            san = 'O-O'
        elif self.is_ooo:
            san = 'O-O-O'
        elif self.pc in ['P', 'p']:
            san = ''
            if self.is_capture or self.is_ep:
                san += '12345678'[file(self.fr)] + 'x'
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
                f = file(self.fr)
                # try disambiguating with file
                if len(filter(lambda sq: file(sq) == f, ambigs)) == 1:
                    san += '12345678'[f]
                elif len(filter(lambda sq: rank(sq) == r, ambigs)) == 1:
                    san += 'abcdefgh'[r]
                else:
                    san += sq_to_str(self.fr)
            if self.is_capture:
                san += 'x'
            san += sq_to_str(self.to)
        return san
    
    def to_verbose_alg(self):
        """convert to the verbose notation used in style12"""
        if self.is_oo:
            # why fics, why?
            ret = 'o-o'
        elif self.is_ooo:
            ret = 'o-o-o'
        else:
            ret = self.pc.upper() + '/'
            ret += sq_to_str(self.fr)
            ret += '-'
            ret += sq_to_str(self.to)
            if self.prom:
                ret += '=' + self.prom.upper()
        return ret

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

class MoveHistory(object):
    """keeps past of previous moves and positions for repetition
    detection and undoing"""
    def __init__(self):
        self.h = [None] * 2

    def set_hash(self, ply, hash):
        if ply >= len(self.h):
            self.h.extend([None] * (ply - len(self.h) + 1))
        self.h[ply] = hash

    def get_hash(self, ply):
        return self.h[ply]

class Position(object):
    def __init__(self, fen):
        # XXX make an array
        self.board = array('c', 0x80 * ['-'])
        self.castle_flags = 0
        self.king_pos = [None, None]
        self.is_stalemate = False
        self.is_checkmate = False
        self.is_draw_nomaterial = False
        self.history = MoveHistory()
        self.set_pos(fen)

    def set_pos(self, fen):
        """Set the position from Forsyth-Fdwards notation.  The format
        is intentionally interpreted strictly; better to give the user an
        error than take in bad data."""
        try:
            # rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
            m = re.match(r'''^([1-8rnbqkpRNBQKP/]+) ([wb]) ([kqKQ]+|-) ([a-h][36]|-) (\d+) (\d+)$''', fen)
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
                    if d > 0:
                        sq += d + 1
                    else:
                        assert(valid_sq(sq))
                        self.board[sq] = c
                        self.hash ^= zobrist.piece_hash(sq, c)
                        self.material[piece_is_white(c)] += \
                            piece_material[c.lower()]
                        if c == 'k':
                            if self.king_pos[0] != None:
                                # multiple kings
                                raise BadFenError()
                            self.king_pos[0] = sq
                        elif c == 'K':
                            if self.king_pos[1] != None:
                                # multiple kings
                                raise BadFenError()
                            self.king_pos[1] = sq
                        elif c.lower() == 'p':
                            if rank(sq) in [0, 7]:
                                # pawn on 1st or 8th rank
                                raise BadFenError()
                        sq += 1
                if sq & 0xf != 8:
                    # wrong row length
                    raise BadFenError()

            if None in self.king_pos:
                # missing king
                raise BadFenError()

            self.wtm = side == 'w'
            if self.wtm:
                self.hash ^= zobrist.side_hash

            if castle_flags == '-':
                self.castle_flags = 0
            else:
                (w_oo, w_ooo, b_oo, b_ooo) = (False, False, False, False)
                for c in castle_flags:
                    if c == 'K':
                        if self.board[E1] != 'K' or self.board[H1] != 'R':
                            raise BadFenError()
                        if w_oo:
                            raise BadFenError()
                        w_oo = True
                    elif c == 'Q':
                        if self.board[E1] != 'K' or self.board[A1] != 'R':
                            raise BadFenError()
                        if w_ooo:
                            raise BadFenError()
                        w_ooo = True
                    elif c == 'k':
                        if self.board[E8] != 'k' or self.board[H8] != 'r':
                            raise BadFenError()
                        if b_oo:
                            raise BadFenError()
                        b_oo = True
                    elif c == 'q':
                        if self.board[E8] != 'k' or self.board[A8] != 'r':
                            raise BadFenError()
                        if b_ooo:
                            raise BadFenError()
                        b_ooo = True

                self.castle_flags = to_castle_flags(w_oo, w_ooo,
                    b_oo, b_ooo)

            self.hash ^= zobrist.castle_hash(self.castle_flags)

            if ep == '-':
                self.ep = None
            else:
                self.ep = ep[0].index('abcdefgh') + \
                    0x10 * ep[1].index('012345678')
                self.hash ^= zobrist.ep_hash(self.ep)

            self.fifty_count = int(fifty_count, 10)
            self.half_moves = 2 * (int(full_moves, 10) - 1) + int(not self.wtm)
            self.start_half_moves = self.half_moves
            #assert(self.hash == self._compute_hash())
            self.history.set_hash(self.half_moves, self.hash)

            self.detect_check()
            if self.is_checkmate or self.is_stalemate \
                    or self.is_draw_nomaterial:
                raise BadFenError('got a terminal position')

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
        self.half_moves += 1

        mv.undo = Undo()
        mv.undo.ep = self.ep
        mv.undo.in_check = self.in_check
        mv.undo.castle_flags = self.castle_flags
        mv.undo.fifty_count = self.fifty_count
        mv.undo.material = self.material[:]
        mv.undo.hash = self.hash

        if self.ep:
            # clear old en passant hash
            self.hash ^= zobrist.ep_hash(self.ep)

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

        if mv.pc == 'k':
            self.king_pos[0] = mv.to
        elif mv.pc == 'K':
            self.king_pos[1] = mv.to

        self.ep = mv.new_ep
        if self.ep:
            self.hash ^= zobrist.ep_hash(self.ep)

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
                assert(self.board[mv.to + -0x10] == 'p')
                self.hash ^= zobrist.piece_hash(mv.to + -0x10, 'p')
                self.board[mv.to + -0x10] = '-'
            else:
                assert(self.board[mv.to + 0x10] == 'P')
                self.hash ^= zobrist.piece_hash(mv.to + 0x10, 'P')
                self.board[mv.to + 0x10] = '-'
        elif mv.is_oo:
            # move the rook
            if self.wtm:
                assert(self.board[H1] == 'R')
                self.board[F1] = 'R'
                self.board[H1] = '-'
                self.hash ^= zobrist.piece_hash(F1, 'R') ^ \
                    zobrist.piece_hash(H1, 'R')
            else:
                assert(self.board[H8] == 'r')
                self.board[F8] = 'r'
                self.board[H8] = '-'
                self.hash ^= zobrist.piece_hash(F8, 'r') ^ \
                    zobrist.piece_hash(H8, 'r')
        elif mv.is_ooo:
            # move the rook
            if self.wtm:
                assert(self.board[A1] == 'R')
                self.board[D1] = 'R'
                self.board[A1] = '-'
                self.hash ^= zobrist.piece_hash(D1, 'R') ^ \
                    zobrist.piece_hash(A1, 'R')
            else:
                assert(self.board[A8] == 'r')
                self.board[D8] = 'r'
                self.board[A8] = '-'
                self.hash ^= zobrist.piece_hash(A8, 'r') ^ \
                    zobrist.piece_hash(D8, 'r')

        self.castle_flags &= castle_mask[mv.fr] & castle_mask[mv.to]
        if self.castle_flags != mv.undo.castle_flags:
            self.hash ^= zobrist.castle_hash(self.castle_flags) ^ \
                zobrist.castle_hash(mv.undo.castle_flags)
        self.wtm = not self.wtm
        self.hash ^= zobrist.side_hash
        #self._check_material()
        assert(self.hash == self._compute_hash())
        self.history.set_hash(self.half_moves, self.hash)

    def _compute_hash(self):
        hash = 0
        if self.wtm:
            hash ^= zobrist.side_hash
        for (sq, pc) in self:
            if pc != '-':
                hash ^= zobrist.piece_hash(sq, pc)
        if self.ep:
            hash ^= zobrist.ep_hash(self.ep)
        hash ^= zobrist.castle_hash(self.castle_flags)
        return hash
    
    def undo_move(self, mv):
        """undo the move"""
        self.wtm = not self.wtm
        self.half_moves -= 1
        self.ep = mv.undo.ep
        self.board[mv.to] = mv.capture
        self.board[mv.fr] = mv.pc
        self.in_check = mv.undo.in_check
        self.castle_flags = mv.undo.castle_flags
        self.fifty_count = mv.undo.fifty_count
        self.material = mv.undo.material
        self.hash = mv.undo.hash
        
        if mv.pc == 'k':
            self.king_pos[0] = mv.fr
        elif mv.pc == 'K':
            self.king_pos[1] = mv.fr
        
        if mv.is_ep:
            if self.wtm:
                assert(self.board[mv.to + -0x10] == '-')
                self.board[mv.to + -0x10] = 'p'
            else:
                assert(self.board[mv.to + 0x10] == '-')
                self.board[mv.to + 0x10] = 'P'
        elif mv.is_oo:
            if self.wtm:
                assert(self.board[F1] == 'R')
                self.board[H1] = 'R'
                self.board[F1] = '-'
            else:
                assert(self.board[F8] == 'r')
                self.board[H8] = 'r'
                self.board[F8] = '-'
        elif mv.is_ooo:
            if self.wtm:
                assert(self.board[D1] == 'R')
                self.board[A1] = 'R'
                self.board[D1] = '-'
            else:
                assert(self.board[D8] == 'r')
                self.board[A8] = 'r'
                self.board[D8] = '-'
        #self._check_material()
        #assert(self.hash == self._compute_hash())

    def _check_material(self):
        bmat = sum([piece_material[pc.lower()]
            for (sq, pc) in self if pc != '-' and not piece_is_white(pc)])
        assert(bmat == self.material[0])
        assert(self.material[1] == sum([piece_material[pc.lower()]   
            for (sq, pc) in self if pc != '-' and piece_is_white(pc)]))

    def detect_check(self):
        """detect whether the player to move is in check, checkmated,
        or stalemated"""
        self.in_check = self.under_attack(self.king_pos[self.wtm],
            not self.wtm)

        if self.in_check:
            self.is_checkmate = not self._any_legal_moves()
        else:
            self.is_stalemate = not self._any_legal_moves()

        self.is_draw_nomaterial = self.material[0] <= 3 and \
            self.material[1] <= 3 and self.no_pawns()

    def no_pawns(self):
        for (sq, pc) in self:
            if pc in ['P', 'p']:
                return False
        return True

    def _any_legal_moves(self):
        ksq = self.king_pos[self.wtm]
        if self._any_pc_moves(ksq, self.board[ksq]):
            return True
        for (sq, pc) in self:
            #if pc != '-' and piece_is_white(pc) == self.wtm:
            if pc not in ['-', 'K', 'k'] and piece_is_white(pc) == self.wtm:
                cur_sq = sq
                if self._any_pc_moves(sq, pc):
                    return True
        return False

    def _pawn_cap_at(self, sq, wtm):
        if not valid_sq(sq):
            return False
        pc = self.board[sq]
        return (pc != '-' and piece_is_white(pc) != wtm) or self.ep == sq

    def _any_pc_moves(self, sq, pc):
        if pc == 'P':
            if self.board[sq + 0x10] == '-':
                if Move(self, sq, sq + 0x10).is_legal():
                    return True
                if rank(sq) == 1 and self.board[sq + 0x20] == '-' and Move(
                        self, sq, sq + 0x20).is_legal():
                    return True
            if self._pawn_cap_at(sq + 0xf, self.wtm) and Move(
                    self, sq, sq + 0xf,
                    is_ep=sq + 0xf == self.ep).is_legal():
                return True
            if self._pawn_cap_at(sq + 0x11, self.wtm) and Move(
                    self, sq, sq + 0x11,
                    is_ep=sq + 0x11 == self.ep).is_legal():
                return True
        elif pc == 'p':
            if self.board[sq + -0x10] == '-':
                if Move(self, sq, sq + -0x10).is_legal():
                    return True
                if rank(sq) == 6 and self.board[sq + -0x20] == '-' and Move(
                        self, sq, sq + -0x20).is_legal():
                    return True
            if self._pawn_cap_at(sq + -0xf, self.wtm) and Move(
                    self, sq, sq + -0xf,
                    is_ep=sq + -0xf == self.ep).is_legal():
                return True
            if self._pawn_cap_at(sq + -0x11, self.wtm) and Move(
                    self, sq, sq + -0x11,
                    is_ep=sq + -0x11 == self.ep).is_legal():
                return True
        else:
            for d in piece_moves[pc.lower()]:
                cur_sq = sq + d
                # we don't need to check castling because if castling
                # is legal, some other king move must be also
                while valid_sq(cur_sq):
                    topc = self.board[cur_sq]
                    if topc == '-' or piece_is_white(topc) != self.wtm:
                        
                        mv = Move(self, sq, cur_sq)
                        if mv.is_legal():
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
            if (self._is_pc_at('P', sq + -0x11)
                    or self._is_pc_at('P', sq + -0xf)):
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
            cur_sq = sq +d
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

    def move_from_lalg(self, s):
        m = re.match(r'([a-h][1-8])([a-h][1-8])(?:=([NBRQ]))?', s)
        if not m:
            return None

        fr = str_to_sq(m.group(1))
        to = str_to_sq(m.group(2))
        prom = m.group(3)
        if prom == None:
            mv = Move(self, fr, to)
        else:
            if self.wtm:
                assert(prom == prom.upper())
                mv = Move(self, fr, to, prom=prom)
            else:
                mv = Move(self, fr, to, prom=prom.lower())
       
        if mv:
            mv.check_pseudo_legal()
            mv.check_legal()

        return mv

    def move_from_san(self, s):
        s = re.sub(r'/[\+#\?\!]+$/', '', s)
        matched = False
        mv = None
    
        # examples: e4 e8=Q
        m = re.match(r'^([a-h][1-8])(?:=([NBRQ]))?', s)
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
            m = re.match(r'^([a-h])x([a-h][1-8])(?:=([NBRQ]))?$', s)
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
            if f == file(to) - 1:
                if self.wtm:
                    fr = to + -0x11
                    if self.board[fr] != 'P':
                        raise IllegalMoveError('bad pawn capture')
                else:
                    fr = to + 0xf
                    if self.board[fr] != 'p':
                        raise IllegalMoveError('bad pawn capture')
            elif f == file(to) + 1:
                if self.wtm:
                    fr = to + -0xf
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
            m = re.match(r'([NBRQK])([a-h])?([1-8])?(x)?([a-h][1-8])', s)
        if m:
            to = str_to_sq(m.group(5))
            if m.group(4):
                if self.board[to] == '-':
                    raise IllegalMoveError('capture on blank square')
            else:
                if self.board[to] != '-':
                    raise IllegalMoveError('missing "x" to indicate capture')

            pc = m.group(1) if self.wtm else m.group(1).lower()
            froms = self.get_from_sqs(pc, to)

            if m.group(2):
                if len(froms) <= 1:
                    raise IllegalMoveError('unnecessary disambiguation')
                f = 'abcdefgh'.index(m.group(2))
                froms = filter(lambda sq: file(sq) == f, froms)

            if m.group(3):
                r = '12345678'.index(m.group(3))
                if len(froms) <= 1:
                    raise IllegalMoveError('unnecessary disambiguation')
                froms = filter(lambda sq: rank(sq) == r, froms)

            if len(froms) != 1:
                raise IllegalMoveError('illegal or ambiguous move %s: %d interpretations' % (s, len(froms)))

            mv = Move(self, froms[0], to)

        '''if mv:
            try:
                mv.check_pseudo_legal()
            except IllegalMoveError:
                raise RuntimeError('san inconsistency')
            mv.check_legal()'''

        return mv

    def move_from_castle(self, s):
        mv = None
        if not mv and s in ['O-O', 'OO', 'o-o']:
            if self.wtm:
                mv = Move(self, E1, G1, is_oo=True)
            else:
                mv = Move(self, E8, G8, is_oo=True)
        
        if not mv and s in ['O-O-O', 'OOO', 'o-o']:
            if self.wtm:
                mv = Move(self, E1, C1, is_ooo=True)
            else:
                mv = Move(self, E8, C8, is_ooo=True)

        if mv:
            mv.check_pseudo_legal()
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
        # If we checkmate comes on the move that causes the fifty-move
        # counter to reach 100, the game is not a draw.  That shouldn't
        # be a problem because if a player is checkmated, he or she
        # won't have a chance to offer a draw and trigger this check.
        return self.fifty_count >= 100

    def is_draw_repetition(self, side):
        """check for draw by repetition"""

        # Note that the most recent possible identical position is
        # 4 ply ago, and we only have to check every other move.
        # This is a well-known chess engine optimization.
        if self.half_moves < 8:
            return False
        stop = max(self.half_moves - self.fifty_count, self.start_half_moves)

        count = 0
        hash = self.history.get_hash(self.half_moves)
        i = self.half_moves - 4
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
        if self.half_moves > 8 and (side == game.WHITE) == self.wtm:
            count = 0
            hash = self.history.get_hash(self.half_moves - 1)
            i = self.half_moves - 5
            while i >= stop:
                if self.history.get_hash(i) == hash:
                    count += 1
                    if count == 2:
                        return True
                i -= 2

        return False
    
    def to_fen(self):
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

        castling = ''
        if check_castle_flags(self.castle_flags, True, True):
            castling += 'K'
        if check_castle_flags(self.castle_flags, True, False):
            castling += 'Q'
        if check_castle_flags(self.castle_flags, False, True):
            castling += 'k'
        if check_castle_flags(self.castle_flags, False, False):
            castling += 'q'
        if castling == '':
            castling = '-'

        if self.ep:
            ep_str = sq_to_str(self.ep)
            assert(ep_str[1] in ['3', '6'])
        else:
            ep_str = '-'

        full_moves = self.half_moves // 2 + 1
        return "%s %s %s %s %d %d" % (pos_str, stm_str, castling, ep_str, self.fifty_count, full_moves)

class Normal(Variant):
    """normal chess"""
    def __init__(self, game):
        self.game = game
        self.pos = copy.deepcopy(initial_pos)

    def do_move(self, s, conn):
        """Try to parse a move and execute it.  If it looks like a move but
        is erroneous or illegal, raise an exception.  Return True if
        the move was handled, or False if it does not look like a move
        and should be processed further."""

        mv = None
        illegal = False

        try:
            # castling
            mv = self.pos.move_from_castle(s)

            # long algebraic
            if not mv:
                mv = self.pos.move_from_lalg(s)
            
            # san
            if not mv:
                mv = self.pos.move_from_san(s)
        except IllegalMoveError as e:
            #print e.reason
            #raise
            illegal = True
            
        if mv or illegal:
            if (self.game.get_user_side(conn.user) == game.WHITE) != \
                    self.pos.wtm:
                #conn.write('user %d, wtm %d\n' % conn.user.session.is_white, self.pos.wtm)
                conn.write(_('It is not your move.\n'))
            elif illegal:
                conn.write('Illegal move (%s)\n' % s)
            else:
                mv.san = mv.to_san()
                self.pos.make_move(mv)
                self.pos.detect_check()
                self.game.last_move_san = mv.san
                self.game.last_move_verbose = mv.to_verbose_alg()
                self.game.next_move()

        return mv or illegal

    def get_turn(self):
        return game.WHITE if self.pos.wtm else game.BLACK

    def to_style12(self, user):
        """returns a style12 string for a given user"""
        # <12> rnbqkbnr pppppppp -------- -------- -------- -------- PPPPPPPP RNBQKBNR W -1 1 1 1 1 0 473 GuestPPMD GuestCWVQ -1 1 0 39 39 60000 60000 1 none (0:00.000) none 1 0 0
        board_str = ''
        for r in range(7, -1, -1):
            board_str += ' '
            for f in range(8):
                board_str += self.pos.board[0x10 * r + f]
        side_str = 'W' if self.pos.wtm else 'B'
        ep = -1 if not self.pos.ep else file(self.pos.ep)
        w_oo = int(check_castle_flags(self.pos.castle_flags, True, True))
        w_ooo = int(check_castle_flags(self.pos.castle_flags, True, False))
        b_oo = int(check_castle_flags(self.pos.castle_flags, False, True))
        b_ooo = int(check_castle_flags(self.pos.castle_flags, False, False))
        if self.game.white == user:
            relation = 1 if self.pos.wtm else -1
            flip = 0
        elif self.game.black == user:
            relation = 1 if not self.pos.wtm else -1
            flip = 1
        else:
            raise RuntimeError('unknown relation')
        full_moves = self.pos.half_moves // 2 + 1
        last_move_time_str = '(%d:%06.3f)' % (self.game.last_move_mins,
            self.game.last_move_secs)
        if user.ivars['ms']:
            white_clock = int(1000 * self.game.white_clock)
            black_clock = int(1000 * self.game.black_clock)
        else:
            white_clock = int(self.game.white_clock)
            black_clock = int(self.game.black_clock)

        # board_str begins with a space
        s = '\n<12>%s %s %d %d %d %d %d %d %d %s %s %d %d %d %d %d %d %d %d %s %s %s %d %d %d\n' % (
            board_str, side_str, ep, w_oo, w_ooo, b_oo, b_ooo,
            self.pos.fifty_count, self.game.number, self.game.white.name,
            self.game.black.name, relation, self.game.white_time,
            self.game.white_inc, self.pos.material[1], self.pos.material[0],
            white_clock, black_clock, full_moves, self.game.last_move_verbose,
            last_move_time_str, self.game.last_move_san, flip,
            int(self.game.clock_is_ticking), int(user.session.lag))
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

initial_pos = Position('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent