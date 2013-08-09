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

import os.path
import re

from .command import ics_command, Command
import global_
import server

import trie

help_dir = 'help/'

@ics_command('help', 'o')
class Help(Command):
    def run(self, args, conn):
        if not args[0]:
            args[0] = 'help'

        assert(args[0] == args[0].lower())

        # for legal reasons, the license help file should be in the code
        # and not in a separate file
        if args[0] in ['license', 'license', 'copying', 'copyright']:
            conn.write_paged(server.get_license())
            return

        # non-admins should not be able to see/view documentation for
        # admin commands.
        if conn.user.is_admin():
            cmds = global_.command_list.admin_cmds
        else:
            cmds = global_.command_list.cmds

        if args[0] == 'commands':
            help_cmds = [c.name for c in cmds.itervalues()]
            conn.write('Current command list:\n\n%s\n' % help_cmds)
            return

        cmd = None
        try:
            cmd = cmds[args[0]]
        except KeyError:
            conn.write(_('There is no help available for "%s".\n')
                % args[0])
        except trie.NeedMore:
            matches = cmds.all_children(args[0])
            assert(len(matches) > 0)
            if len(matches) == 1:
                cmd = matches[0]
            else:
                conn.write(_("""Ambiguous command "%(cmd)s". Matches: %(matches)s\n""")
                    % {'cmd': args[0], 'matches':
                        ' '.join([c.name for c in matches])})

        if cmd:
            cmd = cmd.name
            # Search for actual .txt help file and return text inside that file
            help_file = '%s/%s.txt' % (help_dir, cmd)
            if os.path.exists(help_file):
                # security safeguard
                assert(re.match('[a-z]+', cmd))
                help_file = open(help_file, "r")
                conn.write_paged(help_file.read())
            else:
                conn.write('It appears "%s" is a command but it has no help file. Perhaps you should volunteer to write it. ;)\n' % cmd)

# The original FICS allows paging through text files and hstat
# separately, using the optional "stats" and "text" parameters.
# I am not convinced that is useful enough to be worth the extra
# implementation complexity.
@ics_command('next', '')
class Next(Command):
    def run(self, args, conn):
        s = conn.user.session.next_lines
        if not s:
            conn.write(_('There is no more to show.\n'))
        else:
            conn.write_paged(None)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
