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

legal_chars_re = re.compile('''^[\x20-\xfd]*$''')


def check_user_utf8(s):
    ret = legal_chars_re.match(s)
    if ret:
        if type(s) == unicode:
            # already unicode
            return ret
        try:
            unicode(s, 'utf-8')
        except UnicodeDecodeError:
            ret = False
    else:
    return ret

illegal_char_re = re.compile('''[^\x20-\xfd]''')
maciejg_re = '&#x([0-9a-f]+);'
should_encode_re = re.compile(u'([^\x00-\x7e])')

# Maciej format, supported by Raptor and Yafi
def decode_maciejg(s):
    #lambda m: (unichr(int(m.group(1), 16)).encode('utf-8') if
    return re.sub(maciejg_re,
        lambda m: (unichr(int(m.group(1), 16)) if
            len(m.group(1)) <= 6 else m.group(0)), s)

def encode_maciejg(s):
    s = s.decode('utf-8')
    return re.sub(should_encode_re, lambda m: (u'&#x' +
        format(ord(m.group(1)), 'x') + u';'), s).encode('utf-8')

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
