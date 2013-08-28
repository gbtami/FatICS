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


class UsernameException(Exception):
    def __init__(self, reason):
        self.reason = reason


_username_re = re.compile('^[a-zA-Z]+$')


def check_name(name, min_len):
    """ Check whether a string is a valid user name. """
    # XXX "try again" should be specific to logging in
    if len(name) < min_len:
        raise UsernameException(_('Names should be at least %d characters long.')
            % min_len)
    elif len(name) > config.max_login_name_len:
        raise UsernameException(_('Names should be at most %d characters long.')
            % config.max_login_name_len)
    elif not _username_re.match(name):
        raise UsernameException(_('Names should only consist of lower and upper case letters.'))


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
        if u.vars_['pin']:
            self.pin_var.add(u)
        if u.vars_['gin']:
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


def online_exact(name):
    """ Find an online user, looking only for exact matches. """

    # Currently we do not check whether the username is valid
    # when looking for an exact match to an online user, because
    # it is inexpensive to just check the dict of online users.
    # But we check that the name is valid in other cases,
    # so maybe we should check it here as well for consistency.

    #check_name(name, config.min_login_name_len)

    return global_.online.find_exact(name)


def online_exact_for_user(name, conn):
    """ Find an online user, looking for exact matches only.
    Write a friendly error message to the user if none is found. """
    u = online_exact(name)
    if not u:
        conn.write(_('No player named "%s" is online.\n') % name)
    return u


def _online_by_prefix(name):
    """ Find an online user, looking for exact or prefix
    matches.  Raise an AmbiguousException if a prefix is
    ambiguous. """

    check_name(name, 2)

    u = None

    # first try an exact match
    if len(name) >= config.min_login_name_len:
        #print 'going for exact'
        u = online_exact(name)
        '''if u:
            print 'got! %s' % u.name
        else:
            print 'got NOTHING' '''
    if not u:
        # failing that, try a prefix match
        ulist = global_.online.find_part(name)
        if len(ulist) == 1:
            u = ulist[0]
        elif len(ulist) > 1:
            raise AmbiguousException([u.name for u in ulist])
    return u


def online_by_prefix_for_user(name, conn):
    """ Find an online user, looking for exact or prefix
    matches.  Write a friendly error message to the user if
    none is found.  Return a deferred that fires with the result. """

    try:
        # Original FICS interprets a name ending with ! as an exact name
        # that is not an abbreviation.  I don't see this documented anywhere
        # but Babas uses this for private tells.
        if name.endswith('!'):
            name = name[:-1]
            if not name:
                raise UsernameException(name)
            return online_exact_for_user(name, conn)

        check_name(name, 2)
        u = _online_by_prefix(name)
        if not u:
            # XXX perhaps this message should make it clear that there
            # is not even any user with a prefix match
            #conn.write(_('No player matching the name "%s" is online.\n')
            #    % name)
            conn.write(_('No player named "%s" is online.\n')
                % name)
        return u

    except UsernameException as e:
        # XXX we check the length more than once
        if len(name) < 2:
            conn.write(_('You need to specify at least %d characters of the name.\n') % 2)
            return None
        else:
            #conn.write(_('"%s" is not a valid handle: %s\n') % (name, e.reason))
            conn.write(_('"%s" is not a valid handle.\n') % name)
    except AmbiguousException as e:
        conn.write(_("""Ambiguous name "%s". Matches: %s\n""") %
            (name, ' '.join(e.names)))


@defer.inlineCallbacks
def exact(name):
    """ Find a user, offline or online, looking only for exact
    matches.  Return a deferred that fires with the result. """

    check_name(name, config.min_login_name_len)
    u = global_.online.find_exact(name)
    if not u:
        dbu = yield db.user_get_async(name)
        if dbu:
            u = user.RegUser(dbu)
            yield u.finish_init()
        else:
            u = None
    defer.returnValue(u)


@defer.inlineCallbacks
def _by_prefix(name):
    """ Find a user, offline or online, looking for exact or prefix
    matches.  Prefer online users to offline. Raise an
    AmbiguousException if name is an ambiguous prefix. Return a deferred
    that fires with the result. """

    try:
        u = _online_by_prefix(name)
    except AmbiguousException:
        # When there are multiple matching users
        # online, don't bother searching for offline
        # users who also match. We have already confirmed
        # that there are no exact matches.
        raise

    # look for offline matches
    if not u:
        ulist = yield db.user_get_by_prefix(name)
        if len(ulist) == 1:
            u = user.RegUser(ulist[0])
            yield u.finish_init()
        elif len(ulist) > 1:
            raise AmbiguousException([u['user_name'] for u in ulist])
    defer.returnValue(u)


@defer.inlineCallbacks
def exact_for_user(name, conn):
    """ Like exact(), but writes an error message on failure. """
    try:
        u = yield exact(name)
    except UsernameException:
        conn.write(_('"%s" is not a valid handle.\n') % name)
        defer.returnValue(None)
    if not u:
        conn.write(_('There is no player matching the name "%s".\n') % name)
    defer.returnValue(u)


@defer.inlineCallbacks
def by_prefix_for_user(name, conn):
    """ Find a user, offline or online, looking for exact or prefix
    matches.  Prefer online users to offline.  Print a friendly error
    message if none is found.  Return a deferred that fires with
    the result. """

    # Original FICS interprets a name ending with ! as an exact name
    # that is not an abbreviation.  I don't see this documented anywhere
    # but Babas uses this for private tells.
    if name.endswith('!'):
        name = name[:-1]
        if not name:
            raise UsernameException(name)
        u = yield exact_for_user(name, conn)
        defer.returnValue(u)

    try:
        check_name(name, 2)
        u = yield _by_prefix(name)
        #if not u:
        #    conn.write(_('No player named "%s" is online.\n') % name)
        if not u:
            conn.write(_('There is no player matching the name "%s".\n')
                    % name)
            defer.returnValue(None)
        defer.returnValue(u)

    except UsernameException as e:
        # XXX we check the length more than once
        if len(name) < 2:
            conn.write(_('You need to specify at least %d characters of the name.\n') % 2)
        else:
            #conn.write(_('"%s" is not a valid handle: %s\n') % (name, e.reason))
            conn.write(_('"%s" is not a valid handle.\n') % name)
    except AmbiguousException as e:
        conn.write(_("""Ambiguous name "%s". Matches: %s\n""") %
            (name, ' '.join(e.names)))


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
