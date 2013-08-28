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

import time
import subprocess

location = "Fremont, California, USA"
try:
    #version = subprocess.check_output(["hg", "parents", "--template",
    #    "r{rev} ({date|isodate})"])
    version = subprocess.Popen(["hg", "parents", "--template",
        "r{rev} ({date|isodate})"],
        stdout=subprocess.PIPE).communicate()[0]
except:
    raise
    version = "unknown"

start_time = time.time()


def get_copyright_notice():
    return """Copyright (C) 2010-2013 Wil Mahan
This server is free software licensed under the GNU Affero General Public
License, version 3 or any later version.  Type "help license" for details.
The source code for the version of the server you are using is
available here: %s

""" % get_server_link()


def get_license():
    f = open('COPYING', 'r')
    return 'Copyright(C) 2010-2013 Wil Mahan\n\n%s\nThe source code for the version of the server you are using is available here:\n%s\n\n' % (f.read(), get_server_link())


def get_server_link():
    return 'https://bitbucket.org/wmahan/fatics'

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
