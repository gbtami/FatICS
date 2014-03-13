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
import re

from twisted.internet import defer


class BadCommandError(Exception):
    pass


class InternalException(Exception):
    pass


import alias
import trie
import block
import block_codes

_command_re = re.compile(r'^(\S+)(?:\s+(.*))?$')


def _do_parse(s, conn):
    """ Returns a deferred. """
    assert(conn.user.is_online)
    assert(conn.session.commands)
    assert(conn.user.censor is not None)
    s = s.strip()

    # for testing unicode cleanliness
    #s = s.decode('utf-8')

    # previously the prefix '$' was used to not expand aliases
    # and '$$' was used to not update the idle time.  But these
    # options should really be orthogonal, so I made '$$' alone
    # expand aliaes. Now if you want the old behavior of neither
    # expanding aliases nor updating idle time, use '$$$'.
    if s.startswith('$$'):
        s = s[2:].lstrip()
    else:
        conn.session.last_command_time = time.time()
        conn.user.vars_['busy'] = None
        if conn.session.idlenotified_by:
            for u in conn.session.idlenotified_by:
                u.write_('\nNotification: %s has unidled.\n',
                    (conn.user.name,))
                u.session.idlenotifying.remove(conn.user)
            conn.session.idlenotified_by.clear()

    if s.startswith('$'):
        expand_aliases = False
        s = s[1:].lstrip()
    else:
        expand_aliases = True

    if not s:
        # ignore blank line
        return defer.succeed(block_codes.BLKCMD_NULL)

    # Parse moves.  Note that this happens before aliases are
    # expanded, but leading $ are stripped (which Jin depends on).
    # This behavior mimics the original FICS.
    if conn.session.game:
        mv = conn.session.game.parse_move(s.encode('ascii'), conn)
        if mv:
            d = conn.session.game.execute_move(mv, conn)
            d.addCallback(lambda x: block_codes.BLKCMD_GAME_MOVE)
            return d
        elif mv is False:
            # illegal move or got a move when not our turn
            return defer.succeed(block_codes.BLKCMD_GAME_MOVE)

    if expand_aliases:
        try:
            s = alias.expand(s, alias.system,
                conn.user.aliases, conn.user)
        except alias.AliasError as e:
            if e.reason:
                conn.write(e.reason)
            else:
                conn.write(_("Command failed: There was an error expanding aliases.\n"))
            # no exact code
            return defer.succeed(block_codes.BLKCMD_ERROR_BADCOMMAND)

    cmd = None
    d = None
    m = _command_re.match(s)
    assert(m)
    word = m.group(1).lower()
    cmds = conn.session.commands
    try:
        cmd = cmds[word]
    except KeyError:
        conn.write(_("%s: Command not found.\n") % word)
        ret = block_codes.BLKCMD_ERROR_BADCOMMAND
    except trie.NeedMore:
        matches = cmds.all_children(word)
        assert(len(matches) > 0)
        if len(matches) == 1:
            cmd = matches[0]
        else:
            conn.write(_("""Ambiguous command "%(cmd)s". Matches: %(matches)s\n""")
                % {'cmd': word, 'matches':
                    ' '.join([c.name for c in matches])})
            ret = block_codes.BLKCMD_ERROR_AMBIGUOUS
    if cmd:
        try:
            args = parse_args(m.group(2), cmd.param_str)
            d = cmd.run(args, conn)
        except BadCommandError:
            ret = block_codes.BLKCMD_ERROR_BADCOMMAND
            cmd.usage(conn)
        else:
            ret = cmd.block_code
    if d:
        def handleErr(fail):
            if fail.check(BadCommandError):
                cmd.usage(conn)
                fail.trap(BadCommandError)
                return block_codes.BLKCMD_ERROR_BADCOMMAND
            return fail
        d.addCallback(lambda d: ret)
        d.addErrback(handleErr)
        return d
    else:
        return defer.succeed(ret)


def parse(s, conn):
    if not conn.session.ivars['block']:
        d = _do_parse(s, conn)
    else:
        (identifier, s) = block.start_block(s, conn)
        if identifier is not None:
            d = _do_parse(s, conn)
            def finish_block(code):
                block.end_block(identifier, code, conn)
            d.addCallback(finish_block)
        else:
            d = defer.succeed(block_codes.BLKCMD_ERROR_NOSEQUENCE)
    return d


def parse_args(s, param_str):
    args = []
    for c in param_str:
        if c in ['d', 'i', 'w', 'W', 'f']:
            # required argument
            if s is None:
                raise BadCommandError()
            else:
                s = s.lstrip()
                m = re.split(r'\s', s, 1)
                assert(len(m) > 0)
                param = m[0]
                if len(param) == 0:
                    raise BadCommandError()
                if c == c.lower():
                    param = param.lower()
                if c in ['i', 'd']:
                    # integer or word
                    try:
                        param = int(param, 10)
                    except ValueError:
                        if c == 'd':
                            raise BadCommandError()
                elif c == 'f':
                    try:
                        param = float(param)
                    except ValueError:
                        raise BadCommandError()
                s = m[1] if len(m) > 1 else None
        elif c in ['o', 'O', 'n', 'p']:
            # optional argument
            if s is None:
                param = None
            else:
                s = s.lstrip()
                m = re.split(r'\s', s, 1)
                assert(len(m) > 0)
                param = m[0]
                if c == c.lower():
                    param = param.lower()
                if len(param) == 0:
                    param = None
                    assert(len(m) == 1)
                elif c in ['n', 'p']:
                    try:
                        param = int(param, 10)
                    except ValueError:
                        if c == 'p':
                            raise BadCommandError()
                s = m[1] if len(m) > 1 else None
        elif c == 'S':
            # string to end
            if s is None or len(s) == 0:
                raise BadCommandError()
            param = s
            s = None
        elif c == 'T' or c == 't':
            # optional string to end
            if s is None or len(s) == 0:
                param = None
            else:
                param = s
                if c == 't':
                    param = param.lower()
            s = None
        else:
            raise InternalException()
        args.append(param)

    if not (s is None or re.match(r'^\s*$', s)):
        # extraneous data at the end
        raise BadCommandError()

    return args

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
