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

from .command import *

import global_

# TODO: make these commands accept a username parameter

@ics_command('accept', 'n', admin.Level.user)
class Accept(Command):
    def run(self, args, conn):
        if args[0] is None:
            if not conn.user.session.offers_received:
                conn.write(_('There are no offers to accept.\n'))
                return
            if len(conn.user.session.offers_received) > 1:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "accept n" to choose one.\n'))
                return
            conn.user.session.offers_received[0].accept()
        elif type(args[0]) == int:
            try:
                o = global_.offers[args[0]]
            except KeyError:
                o = None
            if not o or o not in conn.user.session.offers_received:
                conn.write(_('There is no offer %d to accept.\n') % args[0])
            else:
                o.accept()
        else:
            # TODO: find by user
            pass

@ics_command('decline', 'n', admin.Level.user)
class Decline(Command):
    def run(self, args, conn):
        if args[0] is None:
            if len(conn.user.session.offers_received) == 0:
                conn.write(_('There are no offers to decline.\n'))
                return
            if len(conn.user.session.offers_received) > 1 and args[0] is None:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "decline n" to choose one.\n'))
                return
            conn.user.session.offers_received[0].decline()
        elif isinstance(args[0], basestring):
            conn.write('TODO: find by user\n')
        else:
            try:
                o = global_.offers[args[0]]
            except KeyError:
                o = None
            if not o or o not in conn.user.session.offers_received:
                conn.write(_('There is no offer %d to decline.\n') % args[0])
            else:
                o.decline()

@ics_command('withdraw', 'n', admin.Level.user)
class Withdraw(Command):
    def run(self, args, conn):
        if args[0] is None:
            if len(conn.user.session.offers_sent) == 0:
                conn.write(_('There are no offers to withdraw.\n'))
                return
            if len(conn.user.session.offers_sent) > 1:
                conn.write(_('You have more than one pending offer. Use "pending" to see them and "withdraw n" to choose one.\n'))
                return
            conn.user.session.offers_sent[0].withdraw()
        elif isinstance(args[0], basestring):
            conn.write('TODO: find by user\n')
        else:
            try:
                o = global_.offers[args[0]]
            except KeyError:
                o = None
            if not o or o not in conn.user.session.offers_sent:
                conn.write(_('There is no offer %d to withdraw.\n') % args[0])
            else:
                o.withdraw()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
