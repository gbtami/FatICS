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

import db
from twisted.internet import defer

speed_ids = {}
variant_ids = {}
speed_names = {}
variant_names = {}
variant_abbrevs = {}


class Speed(object):
    def __init__(self, id_, name, abbrev):
        self.id_ = id_
        self.name = name
        self.abbrev = abbrev
        speed_ids[id_] = self
        speed_names[name] = self

    def __eq__(self, other):
        return self.id_ == other.id_

    def __str__(self):
        return self.name


class Variant(object):
    def __init__(self, id_, name, abbrev):
        self.id_ = id_
        self.name = name
        self.abbrev = abbrev
        variant_ids[id_] = self
        variant_names[name] = self
        variant_abbrevs[abbrev] = self

    def __eq__(self, other):
        return self.id_ == other.id_

    def __str__(self):
        return self.name


class SpeedAndVariant(object):
    def __init__(self, speed, variant):
        self.speed = speed
        self.variant = variant
        # sometimes we have to abbreviate speed and variant
        # with one character for compatibility with original FICS
        if self.variant.name == 'chess':
            self.abbrev = self.speed.abbrev
        else:
            self.abbrev = self.variant.abbrev

    def __hash__(self):
        return self.speed.id_ | (self.variant.id_ << 3)

    def __eq__(self, other):
        return self.speed == other.speed and self.variant == other.variant

    def __str__(self):
        if self.variant.name == 'chess':
            # normal chess is not given explicitly, e.g. "blitz"
            return self.speed.name
        else:
            return '%s %s' % (self.speed.name, self.variant.name)

    def legacy_str(self):
        """ Unfortunately, some clients may not be able to handle
        both the speed and variant """
        if self.variant.name == 'chess':
            return self.speed.name
        else:
            return self.variant.name


def from_names(speed_name, variant_name):
    return SpeedAndVariant(speed_names[speed_name],
        variant_names[variant_name])


def from_ids(speed_id, variant_id):
    return SpeedAndVariant(speed_ids[speed_id],
        variant_ids[variant_id])


@defer.inlineCallbacks
def init():
    for row in (yield db.get_speeds()):
        Speed(row['speed_id'], row['speed_name'], row['speed_abbrev'])
    for row in (yield db.get_variants()):
        Variant(row['variant_id'], row['variant_name'], row['variant_abbrev'])
    global standard_chess, blitz_chess, lightning_chess
    global blitz_chess960, blitz_bughouse, blitz_crazyhouse, blitz_suicide
    standard_chess = from_names('standard', 'chess')
    blitz_chess = from_names('blitz', 'chess')
    lightning_chess = from_names('lightning', 'chess')
    blitz_chess960 = from_names('blitz', 'chess960')
    blitz_bughouse = from_names('blitz', 'bughouse')
    blitz_crazyhouse = from_names('blitz', 'crazyhouse')
    blitz_suicide = from_names('blitz', 'suicide')

    import variant.chess
    import variant.chess960
    import variant.crazyhouse
    import variant.bughouse
    import variant.suicide
    import global_

    global_.variant_class['chess'] = variant.chess.Chess
    global_.variant_class['crazyhouse'] = variant.crazyhouse.Crazyhouse
    global_.variant_class['chess960'] = variant.chess960.Chess960
    global_.variant_class['bughouse'] = variant.bughouse.Bughouse
    global_.variant_class['suicide'] = variant.suicide.Suicide


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
