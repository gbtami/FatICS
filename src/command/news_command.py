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

import admin
import db

from .command import ics_command, Command


@ics_command('news', 'p', admin.Level.user)
class News(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is not None:
            # TODO? range parameter
            item = yield db.get_news_item(args[0])
            if not item:
                conn.write(_('News item %d not found.\n') % args[0])
            else:
                conn.write('%4d (%s) %s\n' % (item['news_id'],
                    item['news_date'], item['news_title']))
                conn.write('\n%s\n\n' % item['text'])
                conn.write(_('Posted by %s.\n' % item['news_poster']))
        else:
            news = yield db.get_recent_news(is_admin=False)
            if len(news) == 0:
                conn.write(_('There is no news.\n'))
            else:
                conn.write(_('Index of the last few news items:\n'))
                for item in reversed(news):
                    conn.write('%4d (%s) %s\n' % (item['news_id'],
                        item['news_date'], item['news_title']))


@ics_command('cnewsd', 'd', admin.Level.admin)
class Cnewsd(Command):
    """ Delete the last line of a news item's text. """
    @defer.inlineCallbacks
    def run(self, args, conn):
        news_id = args[0]
        try:
            yield db.del_last_news_line(news_id)
        except db.DeleteError:
            conn.write(A_('News item %d not found or already has no lines.\n') % news_id)
        else:
            conn.write(A_('Deleted last line of news item %d.\n') % news_id)


@ics_command('cnewse', 'dp', admin.Level.admin)
class Cnewse(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        exp = args[1]
        if exp is None:
            exp = 0
        if exp != 0:
            conn.write(A_('News expiration dates are not currently supported.\n'))
            return
        try:
            yield db.delete_news(args[0])
        except db.DeleteError:
            conn.write(A_('News item %d not found.\n') % args[0])
        else:
            conn.write(A_('Deleted news item %d.\n') % args[0])


@ics_command('cnewsf', 'dT', admin.Level.admin)
class Cnewsf(Command):
    """ Add a line to a news item's text. """
    @defer.inlineCallbacks
    def run(self, args, conn):
        news_id = args[0]
        line = args[1] if args[1] is not None else ''
        yield db.add_news_line(news_id, line)
        conn.write(A_('News item %d updated.\n') % news_id)


@ics_command('cnewsi', 'S', admin.Level.admin)
class Cnewsi(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if len(args[0]) > 45:
            conn.write(A_('The news title exceeds the 45-character maximum length; not posted.\n'))
            return
        news_id = yield db.add_news(args[0], conn.user, is_admin=False)
        conn.write(A_('Created news item %d.\n') % news_id)


@ics_command('cnewsp', 'd', admin.Level.admin)
class Cnewsp(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        try:
            yield db.set_news_poster(args[0], conn.user)
        except db.UpdateError:
            conn.write(A_('News item %d not found or not changed.\n') % args[0])
        else:
            conn.write(A_('News item %d updated.\n') % args[0])


@ics_command('cnewst', 'dS', admin.Level.admin)
class Cnewst(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        try:
            yield db.set_news_title(args[0], args[1])
        except db.UpdateError:
            conn.write(A_('News item %d not found or not changed.\n') % args[0])
        else:
            conn.write(A_('News item %d updated.\n') % args[0])

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
