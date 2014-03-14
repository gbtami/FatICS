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

from twisted.internet import defer

import server
import find_user
import trie
import list_
import filter_
import lang
import channel
import var
import speed_variant
import db
import logger

# add a builtin to mark strings for translation that should not
# automatically be translated dynamically.
import __builtin__
# dynamically translated messages
__builtin__.__dict__['N_'] = lambda s: s
# admin messages
__builtin__.__dict__['A_'] = lambda s: s

# server messages
server_message = {}

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
var_defaults = var.Defaults()

# lists
lists = trie.Trie()
admin_lists = trie.Trie()

# filters and gaetways: will be initialized by filter_.init()
filters = None
gateways = None

# langauages
langs = lang.get_langs()

# channels; will be initialized by channels.init()
channels = None

# commands
commands = trie.Trie()
admin_commands = trie.Trie()

# map variant names to the classes that implement them
variant_class = {}

# current user whose command is being handled
curuser = None

# load commands
import command
command  # pacify pyflakes


@defer.inlineCallbacks
def init():
    db.init()
    yield server.init()
    yield channel.init()
    yield filter_.init()
    var.init_vars()
    var.init_ivars()
    yield list_.init_lists()
    yield speed_variant.init()

log = logger.log

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
