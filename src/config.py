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

port = 5001
compatibility_port = 5000
ssl_port = 5004
websocket_port = 8080

location = 'London, UK'

db_host = "localhost"
db_db = "chess"

log_directory = "./log"

# login timout in seconds
login_timeout = 30
min_login_name_len = 3
max_login_name_len = 17

# max idle time in seconds
idle_timeout = 60 * 60

# maximum number of players connected to the server at once
maxplayer = 49

# number of connections reserved for admins
admin_reserve = 5

# maximum number of guests
maxguest = 10

# limit on number of channels one user can own
max_channels_owned = 8

prompt = 'fics% '

assert(admin_reserve + maxguest <= maxplayer)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
