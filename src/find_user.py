# Copyright (C) 2010-2013  Wil Mahan <wmahan+fatics@gmail.com>
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

from twisted.internet import defer

import trie
import global_
import config
import db
import user


class AmbiguousException(Exception):
    def __init__(self, names):
        self.names = names


_username_re = re.compile('^[a-zA-Z]+$')


def check_name(name, min_len):
    """ Check whether a string is a valid user name. """
    # XXX "try again" should be specific to logging in
    if len(name) < min_len:
        raise user.UsernameException(_('Names should be at least %d characters long.  Try again.\n') % min_len)
    elif len(name) > config.max_login_name_len:
        raise user.UsernameException(_('Names should be at most %d characters long.  Try again.\n') % config.max_login_name_len)
    elif not _username_re.match(name):
        raise user.UsernameException(_('Names should only consist of lower and upper case letters.  Try again.\n'))


class Online(object):
    def __init__(self):
        self._online = trie.Trie()
        # this is redundant, but faster; it's very slow to iterate
        # over the trie
        self._online_names = {}
        self.guest_count = 0
        self.pin_ivar = set()
        self.pin_var = set()
        self.gin_var = set()
        #self.shouts_var = set()

    def add(self, u):
        name = u.name.lower()
        assert(name not in self._online_names)
        self._online[name] = u
        self._online_names[name] = u
        if u.vars['pin']:
            self.pin_var.add(u)
        if u.vars['gin']:
            self.gin_var.add(u)
        if u.is_guest:
            self.guest_count += 1

    def remove(self, u):
        if u in self.pin_ivar:
            self.pin_ivar.remove(u)
        if u in self.pin_var:
            self.pin_var.remove(u)
        if u in self.gin_var:
            self.gin_var.remove(u)
        #if u in shouts_var:
        #    shouts_var.remove(u)
        del self._online_names[u.name.lower()]
        del self._online[u.name.lower()]
        self.guest_count -= int(u.is_guest)

    def is_online(self, name):
        return name.lower() in self._online_names

    def find_exact(self, name):
        name = name.lower()
        try:
            u = self._online_names[name]
        except KeyError:
            u = None
        return u

    def find_exact_for_user(self, name, conn):
        u = self.find_exact(name)
        if not u:
            conn.write(_('No player named "%s" is online.\n') % name)
        return u

    def find_part(self, prefix):
        assert(not self.is_online(prefix))
        prefix = prefix.lower()
        try:
            ulist = self._online.all_children(prefix)
        except KeyError:
            ulist = []
        return ulist

    #def __getitem__(self, key):
    #    return self._online[key]
    def __iter__(self):
        return iter(self._online_names.values())

    def __len__(self):
        return len(self._online_names)


# XXX there is no need to return a deferred when
# online_only == True, to that case should probable
# be moved into separate functions
@defer.inlineCallbacks
def exact(name, online_only=False):
    """ async version of find_by_name_exact() """
    check_name(name, config.min_login_name_len)
    u = global_.online.find_exact(name)
    if not u and not online_only:
        dbu = yield db.user_get_async(name)
        if dbu:
            u = user.RegUser(dbu)
        else:
            u = None
    defer.returnValue(u)


@defer.inlineCallbacks
def _by_prefix_async(name, online_only):
    """ Find a user but allow the name to be abbreviated if
    it is unambiguous; prefer online users to offline. """
    check_name(name, 2)

    u = None

    # first try an exact match
    if len(name) >= config.min_login_name_len:
        u = yield exact(name, online_only=online_only)
    if not u:
        # failing that, try a prefix match
        ulist = global_.online.find_part(name)
        if len(ulist) == 1:
            u = ulist[0]
        elif len(ulist) > 1:
            # When there are multiple matching users
            # online, don't bother searching for offline
            # users who also match. We have already confirmed
            # that there are no exact matches.
            raise AmbiguousException([u.name for u in ulist])

    if not u and not online_only:
        ulist = yield db.user_get_by_prefix(name)
        if len(ulist) == 1:
            u = user.RegUser(ulist[0])
        elif len(ulist) > 1:
            raise AmbiguousException([u['user_name'] for u in ulist])
    defer.returnValue(u)


@defer.inlineCallbacks
def by_prefix_for_user(name, conn, online_only=False):
    """ async version of find_by_prefix_for_user() """

    try:
        # Original FICS interprets a name ending with ! as an exact name
        # that is not an abbreviation.  I don't see this documented anywhere
        # but Babas uses this for private tells.
        if name.endswith('!'):
            name = name[:-1]
            if not name:
                raise user.UsernameException(name)
            u = yield exact_for_user(name, conn, online_only)
            defer.returnValue(u)

        if len(name) < 2:
            conn.write(_('You need to specify at least %d characters of the name.\n') % 2)
            defer.returnValue(None)
        u = yield _by_prefix_async(name, online_only)
        #if not u:
        #    conn.write(_('No player named "%s" is online.\n') % name)
        if not u:
            if online_only:
                conn.write(_('No player matching the name "%s" is online.\n')
                    % name)
            else:
                conn.write(_('There is no player matching the name "%s".\n')
                    % name)
        defer.returnValue(u)

    except user.UsernameException as e:
        #conn.write(_('"%s" is not a valid handle: %s\n') % (name, e.reason))
        conn.write(_('"%s" is not a valid handle.\n') % name)
    except AmbiguousException as e:
        conn.write(_("""Ambiguous name "%s". Matches: %s\n""") %
            (name, ' '.join(e.names)))
    defer.returnValue(None)


@defer.inlineCallbacks
def exact_for_user(name, conn, online_only=False):
    """ Like exact(), but writes an error message on failure. """
    try:
        u = yield exact(name, online_only)
    except user.UsernameException:
        conn.write(_('"%s" is not a valid handle.\n') % name)
        defer.returnValue(None)
    if not u:
        if online_only:
            conn.write(_('No player named "%s" is online.\n') % name)
        else:
            conn.write(_('There is no player matching the name "%s".\n') % name)
    defer.returnValue(u)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
