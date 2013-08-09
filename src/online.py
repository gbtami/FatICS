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

import trie

#class AmbiguousException(Exception):
#        def __init__(self, matches):
#                self.matches = matches

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

    def find_part(self, prefix):
        assert(not self.is_online(prefix))
        prefix = prefix.lower()
        try:
            ulist = self._online.all_children(prefix)
        except KeyError:
            ulist = []
        return ulist

    def __iter__(self):
        return iter(self._online_names.values())

    def __len__(self):
        return len(self._online_names)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
