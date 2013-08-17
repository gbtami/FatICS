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


class AliasError(Exception):
    def __init__(self, reason=None):
        self.reason = reason

if 1:
    system = {
        'a': 'accept',
        'ame': 'allobservers $m',
        'answer': 'tell 1 (answering $1): $2-',
        'answer4': 'tell 4 (answering $1): $2-',
        'at': 'accept t $@',
        'b': 'backward $@',
        'bu': 'bugwho $@',
        'bug': 'bugwho $@',
        'bye': 'quit',
        'clearboard': 'bsetup',
        'Cls': 'help',
        'cm': 'clearmessages $@',
        'd': 'decline $@',
        'dt': 'decline t $@',
        'g': 'games $@',
        'e': 'examine $@',
        'exit': 'quit',
        'exl': 'examine $m -1',
        'f': 'finger $@',
        'fi': 'finger $@',
        'fo': 'forward $@',
        'fop': 'finger  $o $@',
        'fp': 'finger $p $@',
        'f.': 'finger $. $@',
        'gf': 'getgame $@',
        'gfm': 'getgame $@fm',
        'gm': 'getgame $@m',
        'got': 'goboard $@',
        'goto': 'goboard $@',
        'h': 'help $@',
        'hi': 'history $@',
        'ho': 'history $o',
        'hp': 'history $p',
        'hr': 'hrank $@',
        'in': 'inchannel $@',
        'i': 'it $@',
        'ivars': 'ivariables $@',
        'jl': 'jsave $1 $m -1',
        'lec': 'xtell lecturebot $@',
        'logout': 'quit',
        'm': 'match $@',
        'ma': 'match $@',
        'mailold': 'mailstored $@ -1',
        'mailoldme': 'mailstored $m -1',
        'mailoldmoves': 'mailstored $@ -1',
        'mam': 'xtell mamer! $@',
        'mb': 'xtell mailbot! $@',
        'more': 'next',
        'motd': 'help motd',
        'n': 'next $@',
        'new': 'news $@',
        'o': 'observe $@',
        'ol': 'smoves $@ -1',
        'old': 'smoves $@ -1',
        'oldme': 'smoves $m -1',
        'oldmoves': 'smoves $@ -1',
        'p': 'who a$@',
        'pl': 'who a$@',
        'player': 'who a$@',
        'players': 'who a$@',
        'q': '''tell $m The command 'quit' cannot be abbreviated.''',
        'qu': '''tell $m The command 'quit' cannot be abbreviated.''',
        'qui': '''tell $m The command 'quit' cannot be abbreviated.''',
        'r': 'refresh $@',
        're': 'refresh $@',
        'rem': 'rematch',
        'res': 'resign $@',
        #'rping': 'xtell ROBOadmin Ping',
        'saa': 'simallabort',
        'saab': 'simallabort',
        'saadj': 'simalladjourn',
        'sab': 'simabort $@',
        'sadj': 'simadjourn $@',
        'setup': 'bsetup $@',
        'sh': 'shout $@',
        'sn': 'simnext',
        'sp': 'simprev',
        'sping': 'ping $1',
        'stats': 'statistics $@',
        't': 'tell $@',
        'td': 'xtell mamer $@',
        'vars': 'variables $@',
        'w': 'who $@',
        'worst': 'rank 0 $1',
        'wt': 'withdraw t $@',
        'ungetgame': 'unseek',
        'znotl': 'znotify $@',
        '.': 'tell . $@',
        ',': 'tell , $@',
        '`': 'tell . $@',
        '!': 'shout $@',
        ':': 'it $@',
        '^': 'cshout $@',
        '?': 'help $@',
        '*': 'kibitz $@',
        '#': 'whisper $@',
        '+': 'addlist $@',
        '-': 'sublist $@',
        '=': 'showlist $@',
        'p+': 'ptell p+ $@',
        'p++': 'ptell p++ $@',
        'p+++': 'ptell p+++ $@',
        'p-': 'ptell p- $@',
        'p--': 'ptell p-- $@',
        'p---': 'ptell p--- $@',
        'n+': 'ptell n+ $@',
        'n++': 'ptell n++ $@',
        'n+++': 'ptell n+++ $@',
        'n-': 'ptell n- $@',
        'n--': 'ptell n-- $@',
        'n---': 'ptell n--- $@',
        'b+': 'ptell b+ $@',
        'b++': 'ptell b++ $@',
        'b+++': 'ptell b+++ $@',
        'b-': 'ptell b- $@',
        'b--': 'ptell b-- $@',
        'b---': 'ptell b--- $@',
        'r+': 'ptell r+ $@',
        'r++': 'ptell r++ $@',
        'r+++': 'ptell r+++ $@',
        'r-': 'ptell r- $@',
        'r--': 'ptell r-- $@',
        'r---': 'ptell r--- $@',
        'q+': 'ptell q+ $@',
        'q++': 'ptell q++ $@',
        'q+++': 'ptell q+++ $@',
        'q-': 'ptell q- $@',
        'q--': 'ptell q-- $@',
        'q---': 'ptell q--- $@',
        'h+': 'ptell h+ $@',
        'h++': 'ptell h++ $@',
        'h+++': 'ptell h+++ $@',
        'h-': 'ptell h- $@',
        'h--': 'ptell h-- $@',
        'h---': 'ptell h--- $@',
        'd+': 'ptell d+ $@',
        'd++': 'ptell d++ $@',
        'd+++': 'ptell d+++ $@',
        'd-': 'ptell d- $@',
        'd--': 'ptell d-- $@',
        'd---': 'ptell d--- $@',
        'sit': 'ptell sit! $@',
        'nosit': 'ptell go! $@',
        'mateme': 'ptell $1 mates me! $@',
        'mates': 'ptell $1 mates $o! $@',
        # not in "help system_alias"
        'unfollow': 'follow',
        # showtm is now a command
        # added by wmahan to replace commands
        'open': 'set open',
        'op': 'set open',
        'flip': 'set flip',
        'bell': 'set bell',
        'simopen': 'set simopen',
    }

    # If this ever needs optimization, punctuation could be separated
    # as part of normal command parsing instead.
    punct_re = re.compile(r'''^([@!#$%^&*\-+'"\/.,=])\s*(.*)''')
    alias_re = re.compile(r'^(\S+)(?:\s+(.*))?$')
    space_re = re.compile(r'\s+')
    def expand(s, syslist, userlist, user):
        """ Expand system and user aliases in a given command. """
        m = punct_re.match(s)
        if m:
            word = m.group(1)
            rest = m.group(2)
        else:
            m = alias_re.match(s)
            if m:
                word = m.group(1).lower()
                rest = m.group(2)

        if m:
            if word in userlist:
                s = _expand_params(userlist[word], rest, user)
            elif word in syslist:
                s = _expand_params(syslist[word], rest, user)
        return s

    def _expand_params(alias_str, rest, user):
        # unlike lasker, but like FICS, there is no implicit
        # $@ after simple aliases
        assert(alias_str is not None)
        if rest is None:
            rest = ''
        rest_split = None
        ret = []
        i = 0
        aliaslen = len(alias_str)
        while i < aliaslen:
            if alias_str[i] == '$':
                i += 1
                # raises an error if beyond the end
                try:
                    char = alias_str[i]
                except IndexError:
                    raise AliasError
                if char == '@':
                    if rest is not None:
                        ret.append(rest)
                elif char == '-':
                    if i < aliaslen - 1 and alias_str[i + 1].isdigit():
                        # $-n
                        i += 1
                        char = alias_str[i]
                        if rest_split is None:
                            rest_split = space_re.split(rest)
                        d = int(char, 10)
                        ret.append(' '.join(rest_split[:d]))
                    else:
                        ret.append('-')
                elif char.isdigit():
                    if rest_split is None:
                        rest_split = space_re.split(rest)
                    d = int(char, 10) - 1
                    if i < aliaslen - 1 and alias_str[i + 1] == '-':
                        # $n-
                        i += 1
                        ret.append(' '.join(rest_split[d:]))
                    else:
                        # $n
                        try:
                            ret.append(rest_split[d])
                        except IndexError:
                            # not fatal since parameters can be optional
                            pass
                elif char == 'm':
                    ret.append(user.name)
                elif char == 'o':
                    say_to = user.session.say_to
                    if not say_to:
                        raise AliasError(_("I don't know whom to say that to.\n"))
                    elif len(say_to) > 1:
                        raise AliasError(_('You cannot use $o in an alias after a bughouse game.\n'))
                    else:
                        # note the user may be offline, but we can still
                        # use the name in an alias
                        ret.append(list(say_to)[0].name)
                elif char == 'p':
                    p = user.session.partner
                    if not p:
                        raise AliasError(_('You do not have a partner at present.\n'))
                    else:
                        ret.append(p.name)
                elif char == '.':
                    if user.session.last_tell_user is None:
                        raise AliasError(_('No previous tell.\n'))
                    ret.append(user.session.last_tell_user.name)
                elif char == ',':
                    if user.session.last_tell_ch is None:
                        raise AliasError(_('No previous channel.\n'))
                    ret.append('%s' % user.session.last_tell_ch.id_)
                elif char == '_':
                    # from help new_features: $_ in an alias goes to -,
                    # this allows handling of '$2-' vs '$2'-
                    ret.append('-')
                elif char == '$':
                    ret.append('$')
                else:
                    # unrecognized $ variable
                    raise AliasError()
            else:
                ret.append(alias_str[i])
            i += 1

        return ''.join(ret)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
