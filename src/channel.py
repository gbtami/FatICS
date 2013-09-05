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

from datetime import datetime
from twisted.internet import defer

import list_
import admin
import db
import global_
import config

USER_CHANNEL_START = 1024


class ChannelError(Exception):
    pass


class Channel(object):
    def __init__(self, params):
        self.id_ = params['channel_id']
        assert(isinstance(self.id_, (int, long)))
        self.name = params['name']
        #self.desc = params['descr']
        if params['topic'] is None:
            self.topic = None
        else:
            self.topic = params['topic']
            self.topic_who_name = params['topic_who_name']
            self.topic_when = params['topic_when']
        self.online = []

    def tell(self, msg, user):
        #if user.is_chmuzzled:
        #    user.write(_('You are muzzled in all channels.\n'))
        if (self.id_ == 1 and not user.is_guest and user.is_newbie()
                and user.vars_['interface']):
            # show interface string in ch 1 for newbies
            msg = '[%s] %s' % (user.vars_['interface'], msg)
        msg = '\n%s(%d): %s\n' % (user.get_display_name(), self.id_, msg)
        is_guest = user.is_guest
        count = 0
        name = user.name
        for u in self.online:
            if is_guest and not u.vars_['ctell']:
                continue
            if not u.hears_channels():
                continue
            if not name in u.censor:
                u.write(msg)
                count += 1
        return count

    def qtell(self, msg):
        for u in self.online:
            if not u.hears_channels():
                continue
            u.write(msg)

    def log_on(self, user):
        self.online.append(user)
        if self.topic:
            if user.last_logout is None or self.topic_when > user.last_logout:
                self.show_topic(user)

    def show_topic(self, user):
        if self.topic:
            user.write_('\nTOPIC(%d): *** %s (%s at %s) ***\n',
                (self.id_, self.topic, self.topic_who_name,
                user.format_datetime(self.topic_when)))
        else:
            user.write(_('There is no topic for channel %d.\n') % (self.id_,))

    @defer.inlineCallbacks
    def _check_owner(self, user):
        """ Check whether a user is an owner of the channel allowed to
        perform operations on it, and if not, send an error message. """
        # XXX maybe this could be done without checking the DB
        if not user.is_admin():
            if not (yield db.channel_is_owner(self.id_, user.id_)):
                user.write(_("You don't have permission to do that.\n"))
                defer.returnValue(False)

        if not (yield self._has_member(user)):
            user.write(_("You are not in channel %d.\n") % (self.id_,))
            defer.returnValue(False)

        if not user.hears_channels():
            user.write(_('You are not listening to channels.\n'))
            defer.returnValue(False)

        defer.returnValue(True)

    @defer.inlineCallbacks
    def set_topic(self, topic, owner):
        if not (yield self._check_owner(owner)):
            return

        if topic in ['-', '.']:
            # clear the topic
            self.topic = None
            yield db.channel_del_topic(self.id_)
            for u in self.online:
                if u.hears_channels():
                    u.write_('\n%s(%d): *** Cleared topic. ***\n',
                        (owner.get_display_name(), self.id_))
        else:
            # set a new topic
            self.topic = topic
            self.topic_who_name = owner.name
            self.topic_when = datetime.utcnow()
            yield db.channel_set_topic({'channel_id': self.id_,
                'topic': topic, 'topic_who': owner.id_,
                'topic_when': self.topic_when})
            for u in self.online:
                if u.hears_channels():
                    self.show_topic(u)

    def log_off(self, user):
        self.online.remove(user)

    def is_user_owned(self):
        return self.id_ >= USER_CHANNEL_START

    def _has_member(self, user):
        """Check if a user is in a channel. Queries the database if the
        user is offline. Returns a deferred."""
        if user.is_online:
            return defer.succeed(user in self.online)
        else:
            assert(not user.is_guest)
            return db.user_in_channel(user.id_, self.id_)

    @defer.inlineCallbacks
    def add(self, user):
        """Add a user to this channel."""
        if user in self.online:
            raise list_.ListError(_('[%s] is already on your channel list.\n') %
                self.id_)

        self.online.append(user)
        yield user.add_channel(self.id_)

        # channels above 1024 may be claimed by a user simply
        # by joining
        if self.is_user_owned():
            if user.is_guest:
                raise list_.ListError(_('Only registered players can join channels %d and above.\n') % USER_CHANNEL_START)
            count = yield db.channel_user_count(self.id_)
            if count == 1:
                owned_count = yield db.user_channels_owned(user.id_)
                if (owned_count >= config.max_channels_owned
                        and not user.has_title('TD')):
                    raise list_.ListError(_('You cannot own more than %d channels.\n') % config.max_channels_owned)
                yield db.channel_set_owner(self.id_, user.id_, 1)
                user.write(_('You are now the owner of channel %d.\n') % self.id_)

        if self.topic:
            self.show_topic(user)

    @defer.inlineCallbacks
    def remove(self, user):
        if user not in self.online:
            raise list_.ListError(_('[%s] is not on your channel list.\n') %
                self.id_)

        assert(user.is_online)
        was_owner = not user.is_guest and (yield db.channel_is_owner(self.id_,
            user.id_))
        self.online.remove(user)
        yield user.remove_channel(self.id_)

        if was_owner:
            user.write(_('You are no longer an owner of channel %d.\n') % self.id_)
            # TODO? what if channel no longer has an owner?

    @defer.inlineCallbacks
    def kick(self, u, owner):
        if not (yield self._check_owner(owner)):
            return

        if not (yield self._has_member(u)):
            owner.write(_("%(name)s is not in channel %(chid)d.\n") % {
                'name': u.name, 'chid': self.id_
                })
            return

        if not owner.is_admin():
            if (yield db.channel_is_owner(self.id_, u.id_)):
                owner.write(_("You cannot kick out a channel owner.\n"))
                return
            if u.is_admin():
                owner.write(_("You cannot kick out an admin.\n"))
                return
        else:
            if not admin.check_user_operation(owner, u):
                owner.write(A_('You need a higher adminlevel to do that.\n'))
                return

        u.remove_channel(self.id_)
        if u.is_online:
            self.online.remove(u)
            u.write_('*** You have been kicked out of channel %(chid)d by %(owner)s. ***\n' %
                {'owner': owner.name, 'chid': self.id_})

        for p in self.online:
            if p.hears_channels():
                p.write_('\n%s(%d): *** Kicked out %s. ***\n',
                    (owner.get_display_name(), self.id_, u.name))

    def get_display_name(self):
        if self.name is not None:
            return '''%d "%s"''' % (self.id_, self.name)
        else:
            return "%d" % self.id_

    def get_online(self):
        return [(u.get_display_name() if u.hears_channels() else
                '{%s}' % u.get_display_name())
            for u in self.online]

""" The channel ID is stored in a 32-bit column in the database. """
CHANNEL_MAX = 1 << 31


class ChannelList(object):
    all_ = {}
    def __init__(self, rows):
        for ch in rows:
            id_ = ch['channel_id']
            self.all_[id_] = Channel(ch)

    def __getitem__(self, key):
        assert(isinstance(key, (int, long)))
        if key < 0 or key > CHANNEL_MAX:
            raise KeyError
        try:
            return self.all_[key]
        except KeyError:
            self.all_[key] = self._make_ch(key)
            return self.all_[key]

    def __iter__(self):
        return iter(self.all_.values())

    def _make_ch(self, key):
        name = None
        db.channel_new(key, name)
        return Channel({'channel_id': key, 'name': None, 'descr': None,
            'topic': None})

    def get_default_channels(self):
        return [1]

    def get_default_guest_channels(self):
        return [4, 53]


@defer.inlineCallbacks
def init():
    rows = yield db.get_channel_list()
    global_.channels = ChannelList(rows)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
