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

from test import *

from block_codes import *

class TestBlock(Test):
    def test_block(self):
        t = self.connect_as_guest()
        t.write('iset block 1\n')
        self.expect('block set.', t)

        t.write('\n')
        # 519  == BLK_ERROR_NOSEQUENCE
        # 0x15 == BLOCK_START
        # 0x16 == BLOCK_SEPARATOR
        # 0x17 == BLOCK_END
        self.expect('%c0%c519%c%c\r\n' % (0x15, 0x16, 0x16, 0x17), t)

        t.write('3 finger\n')
        self.expect('%c3%c%s%cFinger of ' % (0x15, 0x16, BLKCMD_FINGER, 0x16), t)
        self.expect('\r\n%c' % 0x17, t)

        t.write('4 eco e e48\n')
        self.expect('%c4%c%s%c  ECO: E48' % (0x15, 0x16, BLKCMD_ECO, 0x16), t)
        self.expect('\r\n%c' % 0x17, t)

        t.write('5 set style 12\n')
        self.expect('%c5%c%s%cStyle 12 set.' % (0x15, 0x16, BLKCMD_SET, 0x16), t)
        self.expect('\r\n%c' % 0x17, t)

        t.write('6 e\n')
        self.expect('%c6%c%s%cStarting a game in examine (scratch) mode.\r\n\r\n<12>' % (0x15, 0x16, BLKCMD_EXAMINE, 0x16), t)
        self.expect('\r\n%c' % 0x17, t)

        t.write('1 iset block 0\n')
        self.expect('block unset.', t)

        self.close(t)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
