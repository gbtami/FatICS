# -*- coding: utf-8 -*-
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

""" Server-wide global state. """

import find_user
import trie
import list_
import var
import filter_
import lang
import channel

# bughouse partners
partners = []

# all offers
offers = {}

# all games
games = {}

# online players
online = find_user.Online()

# seeks
seeks = {}

# player variables and ivariables
vars_ = trie.Trie()
ivars = trie.Trie()
varlist = var.VarList()

# lists
lists = trie.Trie()
admin_lists = trie.Trie()
list_.init_lists()

# filters
filters = filter_.get_initial_filters()

# langauages
langs = lang.get_langs()

# channels
channels = channel.ChannelList()

# commands
commands = trie.Trie()
admin_commands = trie.Trie()

# load commands
from command import *

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
