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

from twisted.internet import defer

import global_
import list_
import trie

from .command import ics_command, Command


@ics_command('addlist', 'ww')
class Addlist(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if conn.user.is_admin():
            ulists = global_.admin_lists
        else:
            ulists = global_.lists
        try:
            ls = ulists.get(args[0])
        except KeyError:
            conn.write(_('''\"%s\" does not match any list name.\n''' % args[0]))
        except trie.NeedMore as e:
            conn.write(_('''Ambiguous list \"%s\". Matches: %s\n''') % (args[0], ' '.join([r.name for r in e.matches])))
        else:
            try:
                yield ls.add(args[1], conn)
            except list_.ListError as e:
                conn.write(e.reason)
        defer.returnValue(None)


@ics_command('showlist', 'o')
class Showlist(Command):
    def run(self, args, conn):
        if args[0] is None:
            for c in global_.lists.itervalues():
                conn.write('%s\n' % c.name)
            return

        if conn.user.is_admin():
            ulists = global_.admin_lists
        else:
            ulists = global_.lists
        try:
            ls = ulists.get(args[0])
        except KeyError:
            conn.write(_('''\"%s\" does not match any list name.\n''' % args[0]))
        except trie.NeedMore as e:
            conn.write(_('''Ambiguous list \"%s\". Matches: %s\n''') % (args[0], ' '.join([r.name for r in e.matches])))
        else:
            try:
                ls.show(conn)
            except list_.ListError as e:
                conn.write(e.reason)


@ics_command('sublist', 'ww')
class Sublist(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if conn.user.is_admin():
            ulists = global_.admin_lists
        else:
            ulists = global_.lists
        try:
            ls = ulists.get(args[0])
        except KeyError:
            conn.write(_('''\"%s\" does not match any list name.\n''' % args[0]))
        except trie.NeedMore as e:
            conn.write(_('''Ambiguous list \"%s\". Matches: %s\n''') % (args[0], ' '.join([r.name for r in e.matches])))
        else:
            try:
                yield ls.sub(args[1], conn)
            except list_.ListError as e:
                conn.write(e.reason)
        defer.returnValue(None)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
