# -*- coding: utf-8 -*-
# Copyright (C) 2013  Andreas Grob <vilarion@illarion.org>
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

"""Unified logging"""

import config
import logging
import os
import errno

facilities = set(['admin'])

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


try:
    os.makedirs(config.log_directory, 0o750)
except OSError as e:
    if e.errno == errno.EACCES:
        print("Warning: could not create log directory (", config.log_directory, "), using current directory")
        config.log_directory = "."
    elif e.errno != errno.EEXIST:
        raise

_logger = {}

for facility in facilities:
    _logger[facility] = logging.getLogger(facility)
    _logger[facility].setLevel(logging.INFO)
    _handler = logging.FileHandler(config.log_directory + "/" + facility + '.log')
    _formatter = logging.Formatter('%(asctime)s - %(message)s')
    _handler.setFormatter(_formatter)
    _logger[facility].addHandler(_handler)


def log(facility, level, message):
    if facility in facilities:
        _logger[facility].log(level, message)
    else:
        print("Unknown log facilitiy used: ", facility)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
