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

import re

from block_codes import (BLOCK_START, BLOCK_SEPARATOR,
    BLOCK_END, BLKCMD_ERROR_NOSEQUENCE)

if 1:
    def send_block(identifier, code, output, conn):
        if not conn.user or not conn.user.is_online:
            return
        conn.write('%c%s%c%d%c%s%c\n' %
            (BLOCK_START, identifier, BLOCK_SEPARATOR, code, BLOCK_SEPARATOR,
            output, BLOCK_END))

    block_re = re.compile('^(\d+) (.*)')
    def start_block(s, conn):
        m = block_re.match(s)
        if not m:
            send_block(0, BLKCMD_ERROR_NOSEQUENCE, '', conn)
            return (None, s)
        assert(not conn.buffer_output)
        conn.output_buffer = ''
        conn.buffer_output = True
        return (m.group(1), m.group(2))

    def end_block(identifier, code, conn):
        conn.buffer_output = False
        send_block(identifier, code, conn.output_buffer, conn)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
