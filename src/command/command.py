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

import admin
import channel
import global_
import config

from twisted.internet import defer

# parameter format (taken from Lasker)
# w - a word
# o - an optional word
# d - integer
# p - optional integer
# i - word or integer
# n - optional word or integer
# s - string to end
# t - optional string to end
# lowercase <-> case-insensitive


class Command(object):
    def __init__(self, name, param_str, admin_level):
        assert(hasattr(self, 'run'))
        self.name = name
        self.param_str = param_str
        self.admin_level = admin_level
        global_.admin_commands[name] = self
        if admin_level <= admin.Level.user:
            global_.commands[name] = self

    def help(self, conn):
        conn.write("help for %s\n" % self.name)

    def usage(self, conn):
        conn.write("Usage: TODO for %s\n" % self.name)


class ics_command(object):
    def __init__(self, name, param_str, admin_level=admin.Level.user):
        self.name = name
        self.param_str = param_str
        self.admin_level = admin_level

    def __call__(self, f):
        # just a check that the naming convention is correct
        import inspect
        assert(inspect.getmro(f)[0].__name__ == self.name.capitalize())
        # instantiate the decorated class at decoration time
        f(self.name, self.param_str, self.admin_level)
        #def wrapped_f(*args):
        #    raise RuntimeError('command objects should not be instantiated directly')
        return wrapped_f

# hack around bug in twisted.python.rebuild that occurs when this is a
# nested function


def wrapped_f(*args):
    raise RuntimeError('command objects should not be instantiated directly')


def requires_registration(f):
    def check_reg(self, args, conn):
        if conn.user.is_guest:
            conn.write(_("Only registered players can use the %s command.\n") % self.name)
        else:
            f(self, args, conn)
    return check_reg


@ics_command('limits', '')
class Limits(Command):
    def run(self, args, conn):
        conn.write(_('Current hardcoded limits:\n'))
        conn.write(_('  Server:\n'))
        conn.write(_('    Channels: %d\n') % channel.CHANNEL_MAX)
        conn.write(_('    Players: %d\n') % config.maxplayer)
        conn.write(_('    Connections: %(umax)d users (+ %(amax)d admins)\n') %
            {'umax': config.maxplayer - config.admin_reserve,
                'amax': config.admin_reserve})


@ics_command('password', 'WW')
class Password(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if conn.user.is_guest:
            conn.write(_("Setting a password is only for registered players.\n"))
        else:
            [oldpass, newpass] = args
            passed = yield conn.user.check_passwd(oldpass)
            if not passed:
                conn.write(_("Incorrect password; password not changed!\n"))
            else:
                yield conn.user.set_passwd(newpass)
                conn.write(_("Password changed to %s.\n") % ('*' * len(newpass)))


@ics_command('quit', '', admin.Level.user)
class Quit(Command):
    def run(self, args, conn):
        conn.loseConnection('quit')


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
