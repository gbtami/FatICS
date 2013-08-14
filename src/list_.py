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

import channel
#import user
import filter_
import global_
import find_user

import db

""" The list design is intentionally kept simple, at the cost of
some repeated code, for example in the messages displayed to users.
Trying to factor out the common code only created a bigger mess.
The lists of original FICS were implemented a bit more concisely, but
it made some English-specific assumptions I don't want to
repeat (e.g. that system-wide lists use the same messages as personal
lists, with "your list" replaced by "the list").  Also original FICS
used a linear search to find entries, so my implementation should
be more efficient for large lists. """


class ListError(Exception):
    def __init__(self, reason):
        self.reason = reason


class MyList(object):
    """ A list as operated on by addlist, sublist, and showlist.  Subclasses
    should implement add, sub, and show methods. """
    def __init__(self, name, is_public=True):
        self.name = name
        self.is_public = is_public
        global_.admin_lists[name.lower()] = self
        if is_public:
            global_.lists[name.lower()] = self

    def _require_admin(self, user):
        if not user.is_admin():
            raise ListError(_("You don't have permission to do that.\n"))


class SystemUserList(MyList):
    def _notify_added(self, conn, u):
        """ When a user is added to a list, notify the adding and
        added users. """
        conn.write(_('%(uname)s added to the %(lname)s list.\n') %
            {'uname': u.name, 'lname': self.name})
        if u.is_online:
            u.write_('\n%(aname)s has added you to the %(lname)s list.\n',
                {'aname': conn.user.name, 'lname': self.name})

    def _notify_removed(self, conn, u):
        conn.write(_('%(uname)s removed from the %(lname)s list.\n') %
            {'uname': u.name, 'lname': self.name})
        if u.is_online:
            u.write_('\n%(aname)s has removed you from the %(lname)s list.\n',
                {'aname': conn.user.name, 'lname': self.name})

    def show(self, conn):
        if not self.is_public:
            self._require_admin(conn.user)
        names = self._get_names()
        conn.write(ngettext('-- %s list: %d name --\n',
            '-- %s list: %d names --\n', len(names)) % (self.name, len(names)))
        conn.write('%s\n' % ' '.join(names))


class TitleList(SystemUserList):
    """ A player title, like GM or WFM """
    def __init__(self, params):
        MyList.__init__(self, params['title_name'], params['title_public'])
        self.id = params['title_id']
        self.descr = params['title_descr']

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(_("Only registered users may have titles.\n"))

            try:
                yield u.add_title(self.id)
            except db.DuplicateKeyError:
                raise ListError(_('%(uname)s is already on the %(lname)s list.\n') %
                    {'uname': u.name, 'lname': self.name})
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(_("Only registered users may have titles.\n"))
            if not u.has_title(self.name):
                raise ListError(_('%(uname)s is not on the %(lname)s list.\n') %
                    {'uname': u.name, 'lname': self.name})
            yield u.remove_title(self.id)
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.title_get_users(self.id)


class NotifyList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have notify lists.\n'))
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u == conn.user:
                raise ListError(_('You cannot notify yourself.\n'))
            if u.is_guest:
                raise ListError(_('You cannot add an unregistered user to your notify list.\n'))
            if u.name in conn.user.notifiers:
                raise ListError(_('%s is already on your notify list.\n')
                    % u.name)
            yield conn.user.add_notification(u)
            conn.write(_('%s added to your notify list.\n') % u.name)
            if u.is_online and u.vars['notifiedby']:
                # new feature: inform the added user
                u.write_('\nYou have been added to the notify list of %s.\n',
                    (conn.user.name,))
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have notify lists.\n'))
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name not in conn.user.notifiers:
                raise ListError(_('%s is not on your notify list.\n') % u.name)
            yield conn.user.remove_notification(u)
            conn.write(_('%s removed from your notify list.\n') % u.name)
            # We deliberately don't notify the user, to avoid
            # embarrassment or hurt feelings.
        defer.returnValue(None)

    def show(self, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have notify lists.\n'))
        notlist = conn.user.notifiers
        conn.write(ngettext('-- notify list: %d name --\n',
            '-- notify list: %d names --\n', len(notlist)) % len(notlist))
        conn.write('%s\n' % ' '.join(notlist))


class IdlenotifyList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn, online_only=True)
        if u:
            if u == conn.user:
                raise ListError(_('You cannot idlenotify yourself.\n'))
            if conn.user in u.session.idlenotified_by:
                raise ListError(_('%s is already on your idlenotify list.\n')
                    % u.name)
            yield conn.user.add_idlenotification(u)
            conn.write(_('%s added to your idlenotify list.\n') % u.name)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn, online_only=True)
        if u:
            if conn.user not in u.session.idlenotified_by:
                raise ListError(_('%s is not on your idlenotify list.\n') % u.name)
            conn.user.remove_idlenotification(u)
            conn.write(_('%s removed from your idlenotify list.\n') % u.name)
        defer.returnValue(None)

    def show(self, conn):
        notlist = conn.session.idlenotifying
        conn.write(ngettext('-- idlenotify list: %d name --\n',
            '-- idlenotify list: %d names --\n', len(notlist)) % len(notlist))
        conn.write('%s\n' % ' '.join([u.name for u in notlist]))


class GnotifyList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have gnotify lists.\n'))
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u == conn.user:
                raise ListError(_('You cannot gnotify yourself.\n'))
            if u.is_guest:
                raise ListError(_('You cannot add an unregistered user to your gnotify list.\n'))
            if u.name in conn.user.gnotifiers:
                raise ListError(_('[%s] is already on your gnotify list.\n')
                    % u.name)
            yield conn.user.add_gnotification(u)
            conn.write(_('[%s] added to your gnotify list.\n') % u.name)
            #if u.is_online:
            #    u.write_('\nYou have been added to the gnotify list of %s.\n',
            #        (conn.user.name,))
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have gnotify lists.\n'))
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name not in conn.user.gnotifiers:
                raise ListError(_('[%s] is not on your gnotify list.\n') % u.name)
            yield conn.user.remove_gnotification(u)
            conn.write(_('[%s] removed from your gnotify list.\n') % u.name)
        defer.returnValue(None)

    def show(self, conn):
        if conn.user.is_guest:
            raise ListError(_('Only registered players can have gnotify lists.\n'))
        notlist = conn.user.gnotifiers
        conn.write(ngettext('-- gnotify list: %d name --\n',
            '-- gnotify list: %d names --\n', len(notlist)) % len(notlist))
        conn.write('%s\n' % ' '.join(notlist))


class ChannelList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        try:
            val = int(item, 10)
        except ValueError:
            raise ListError(_('The channel must be a number.\n'))

        try:
            ch = channel.chlist[val]
        except KeyError:
            raise ListError(_('Invalid channel number.\n'))

        if ch.id == 0 and not conn.user.is_admin():
            conn.write(_('Only admins can join channel 0.\n'))
        else:
            yield ch.add(conn.user)
            conn.user.write(_('[%d] added to your channel list.\n') % val)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        try:
            val = int(item, 10)
        except ValueError:
            raise ListError(_('The channel must be a number.\n'))

        try:
            ch = channel.chlist[val]
        except KeyError:
            raise ListError(_('Invalid channel number.\n'))

        yield ch.remove(conn.user)
        conn.user.write(_('[%d] removed from your channel list.\n') % val)
        defer.returnValue(None)

    def show(self, conn):
        chlist = conn.user.channels
        conn.write(ngettext('-- channel list: %d channel --\n',
            '-- channel list: %d channels --\n', len(chlist)) % len(chlist))
        conn.write('%s\n' % ' '.join([str(ch) for ch in chlist]))


class CensorList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name in conn.user.censor:
                raise ListError(_('%s is already on your censor list.\n') % u.name)
            yield conn.user.add_censor(u)
            conn.write(_('%s added to your censor list.\n') % u.name)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name not in conn.user.censor:
                raise ListError(_('%s is not on your censor list.\n') % u.name)
            yield conn.user.remove_censor(u)
            conn.write(_('%s removed from your censor list.\n') % (u.name))
        defer.returnValue(None)

    def show(self, conn):
        cenlist = conn.user.censor
        conn.write(ngettext('-- censor list: %d name --\n',
            '-- censor list: %d names --\n', len(cenlist)) % len(cenlist))
        conn.write('%s\n' % ' '.join(cenlist))


class NoplayList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name in conn.user.noplay:
                raise ListError(_('%s is already on your noplay list.\n') % u.name)
            yield conn.user.add_noplay(u)
            conn.write(_('%s added to your noplay list.\n') % u.name)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.name not in conn.user.noplay:
                raise ListError(_('%s is not on your noplay list.\n') % u.name)
            yield conn.user.remove_noplay(u)
            conn.write(_('%s removed from your noplay list.\n') % (u.name))
        defer.returnValue(None)

    def show(self, conn):
        noplist = conn.user.noplay
        conn.write(ngettext('-- noplay list: %d name --\n',
            '-- noplay list: %d names --\n', len(noplist)) % len(noplist))
        conn.write('%s\n' % ' '.join(noplist))


class BanList(SystemUserList):
    def __init__(self, name):
        super(BanList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be banned.\n'))
            if u.is_admin():
                raise ListError(A_('Admins cannot be banned.\n'))
            if u.is_banned:
                raise ListError(_('%s is already on the ban list.\n') % u.name)
            yield u.set_banned(True)
            yield db.add_comment_async(conn.user.id, u.id, 'Banned.')
            self._notify_added(conn, u)
            if u.is_online:
                conn.write(_('Note: %s is online.\n') % u.name)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be banned.\n'))
            if not u.is_banned:
                raise ListError(_('%s is not on the ban list.\n') % u.name)
            yield u.set_banned(False)
            yield db.add_comment_async(conn.user.id, u.id, 'Unbanned.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.get_banned_user_names()


class MuzzleList(SystemUserList):
    def __init__(self, name):
        super(MuzzleList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be muzzled.\n'))
            if u.is_admin():
                raise ListError(A_('Admins cannot be muzzled.\n'))
            if u.is_muzzled:
                raise ListError(_('%s is already on the muzzle list.\n') % u.name)
            yield u.set_muzzled(True)
            yield db.add_comment_async(conn.user.id, u.id, 'Muzzled.')
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be muzzled.\n'))
            if not u.is_muzzled:
                raise ListError(_('%s is not on the muzzle list.\n') % u.name)
            yield u.set_muzzled(False)
            yield db.add_comment_async(conn.user.id, u.id, 'Removed from the muzzle list.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.get_muzzled_user_names()


class CmuzzleList(SystemUserList):
    def __init__(self, name):
        super(CmuzzleList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be c-muzzled.\n'))
            if u.is_admin():
                raise ListError(A_('Admins cannot be c-muzzled.\n'))
            if u.is_cmuzzled:
                raise ListError(_('%s is already on the cmuzzle list.\n') % u.name)
            yield u.set_cmuzzled(True)
            yield db.add_comment_async(conn.user.id, u.id, 'C-muzzled.')
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be c-muzzled.\n'))
            if not u.is_cmuzzled:
                raise ListError(_('%s is not on the cmuzzle list.\n') % u.name)
            yield u.set_cmuzzled(False)
            yield db.add_comment_async(conn.user.id, u.id, 'Removed from the cmuzzle list.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.get_cmuzzled_user_names()


class MuteList(SystemUserList):
    def __init__(self, name):
        super(MuteList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_admin():
                raise ListError(A_('Admins cannot be muted.\n'))
            if u.is_muted:
                raise ListError(_('%s is already on the mute list.\n') % u.name)
            yield u.set_muted(True)
            if not u.is_guest:
                yield db.add_comment_async(conn.user.id, u.id, 'Muted.')
            self._notify_added(conn, u)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if not u.is_muted:
                raise ListError(_('%s is not on the mute list.\n') % u.name)
            yield u.set_muted(False)
            if not u.is_guest:
                yield db.add_comment_async(conn.user.id, u.id, 'Unmuted.')
            self._notify_removed(conn, u)

    def _get_names(self):
        # this is slow, but only admins can do it
        muted_guests = [u.name for u in global_.online
            if u.is_muted and u.is_guest]
        return db.get_muted_user_names() + muted_guests


class FilterList(MyList):
    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        yield filter_.add_filter(item, conn)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        yield filter_.remove_filter(item, conn)
        defer.returnValue(None)

    def show(self, conn):
        self._require_admin(conn.user)
        filterlist = db.get_filtered_ips()
        conn.write(ngettext('-- filter list: %d IP --\n',
            '-- filter list: %d IPs --\n', len(filterlist)) % len(filterlist))
        conn.write('%s\n' % ' '.join(filterlist))


class NotebanList(SystemUserList):
    def __init__(self, name):
        super(NotebanList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be notebanned.\n'))
            if u.is_admin():
                raise ListError(A_('Admins cannot be notebanned.\n'))
            if u.is_notebanned:
                raise ListError(_('%s is already on the noteban list.\n') % u.name)
            yield u.set_notebanned(True)
            yield db.add_comment_async(conn.user.id, u.id, 'Notebanned.')
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be notebanned.\n'))
            if not u.is_notebanned:
                raise ListError(_('%s is not on the noteban list.\n') % u.name)
            yield u.set_notebanned(False)
            yield db.add_comment_async(conn.user.id, u.id,
                'Removed from the noteban list.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.get_notebanned_user_names()


class RatedbanList(SystemUserList):
    def __init__(self, name):
        super(RatedbanList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be ratedbanned.\n'))
            if u.is_admin():
                raise ListError(A_('Admins cannot be ratedbanned.\n'))
            if u.is_ratedbanned:
                raise ListError(_('%s is already on the ratedban list.\n') % u.name)
            yield u.set_ratedbanned(True)
            yield db.add_comment_async(conn.user.id, u.id, 'Ratedbanned.')
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_guest:
                raise ListError(A_('Only registered players can be ratedbanned.\n'))
            if not u.is_ratedbanned:
                raise ListError(_('%s is not on the ratedban list.\n') % u.name)
            yield u.set_ratedbanned(False)
            yield db.add_comment_async(conn.user.id, u.id, 'Removed from the ratedbanned list.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        return db.get_ratedbanned_user_names()


class PlaybanList(SystemUserList):
    def __init__(self, name):
        super(PlaybanList, self).__init__(name, is_public=False)

    @defer.inlineCallbacks
    def add(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if u.is_admin():
                raise ListError(A_('Admins cannot be playbanned.\n'))
            if u.is_playbanned:
                raise ListError(_('%s is already on the playban list.\n') % u.name)
            yield u.set_playbanned(True)
            if not u.is_guest:
                yield db.add_comment_async(conn.user.id, u.id, 'Playbanned.')
            self._notify_added(conn, u)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def sub(self, item, conn):
        self._require_admin(conn.user)
        u = yield find_user.by_prefix_for_user(item, conn)
        if u:
            if not u.is_playbanned:
                raise ListError(_('%s is not on the playban list.\n') % u.name)
            yield u.set_playbanned(False)
            if not u.is_guest:
                yield db.add_comment_async(conn.user.id, u.id, 'Removed from the playbanned list.')
            self._notify_removed(conn, u)
        defer.returnValue(None)

    def _get_names(self):
        # this is slow, but only admins can do it
        playbanned_guests = [u.name for u in global_.online
            if u.is_playbanned and u.is_guest]
        return db.get_playbanned_user_names() + playbanned_guests


def init_lists():
    """ initialize lists """
    ChannelList("channel")
    NotifyList("notify")
    IdlenotifyList("idlenotify")
    GnotifyList("gnotify")
    CensorList("censor")
    NoplayList("noplay")
    BanList("ban")
    FilterList("filter")
    MuzzleList("muzzle")
    CmuzzleList("cmuzzle")
    NotebanList("noteban")
    MuteList("mute")
    RatedbanList("ratedban")
    PlaybanList("playban")

    for title in db.title_get_all():
        TitleList(title)

# Not implemented:
# removedcom, c1muzzle, c24muzzle, c46muzzle, c49muzzle,
# c50muzzle, c51muzzle, remote
# TODO: chmuzzle

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
