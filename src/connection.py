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
import re

from twisted.protocols import basic
from twisted.internet import reactor, defer, task, interfaces
from zope.interface import implements

import telnet
import parser
import global_
import db
import login
import utf8
import session

import config
from timeseal import timeseal, TIMESEAL_PONG


#class QuitException(Exception):
#    pass


class Connection(basic.LineReceiver):

    """Represents a connection between a client and the server."""

    implements(interfaces.IProtocol)
    # inherited from parent class:
    # the telnet transport changes all '\r\n' to '\n',
    # so we can just use '\n' here
    delimiter = '\n'
    MAX_LENGTH = 1022

    state = 'prelogin'
    user = None
    logged_in_again = False
    buffer_output = False
    ivar_pat = re.compile(r'%b([01]{32})')
    timeout_check = None
    # current defer.Deferred in progress
    d = None

    def connectionMade(self):
        global_.langs['en'].install(names=['ngettext'])
        self.session = session.Session(self)
        self.factory.connections.append(self)
        self.write(db.get_server_message('welcome'))
        self.login()
        self.session.login_last_command = time.time()
        self.ip = self.transport.getPeer().host
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)

    def login_timeout(self):
        assert(self.state in ['login', 'passwd'])
        self.timeout_check = None
        self.write(_("\n**** LOGIN TIMEOUT ****\n"))
        self.loseConnection('login timeout')

    def idle_timeout(self, mins):
        if self.state not in ['prompt']:
            print('error: got idle timeout in %s state' % self.state)
        assert(self.state in ['prompt'])
        self.write(_("\n**** Auto-logout because you were idle more than %d minutes. ****\n") % mins)
        self.loseConnection('idle timeout')

    def login(self):
        """ Enter the login state, waiting for a username. """
        self.state = 'login'
        self.claimed_user = None
        self.write(db.get_server_message('login'))
        if self.transport.compatibility:
            # the string "freechess.org" must appear somewhere in this message;
            # otherwise, Babas will refuse to connect
            self.write('You are connected to the backwards-compatibility port for old FICS clients.\nYou will not be able to use zipseal or international characters.\nThis server is not endorsed by freechess.org.\n\n')
        self.write("login: ")

    def lineLengthExceeded(self, line):
        name = self.user.name if self.user else self.ip
        print('command ignored: line too long from %s' % name)
        self.write(_("Command ignored: line too long.\n"))

    def lineReceived(self, line):
        #print('((%s,%s))\n' % (self.state, repr(line)))

        #if len(line) > self.MAX_LENGTH:
        #    line = line[:self.MAX_LENGTH - 1]
        assert(len(line) <= self.MAX_LENGTH)

        if self.session.use_timeseal:
            (t, dline) = timeseal.decode_timeseal(line)
        elif self.session.use_zipseal:
            (t, dline) = timeseal.decode_zipseal(line)
        else:
            t = None
            dline = line
        if t is not None and t < 0:
            self.log('timeseal/zipseal error on line: {%r} {%r}' % (line, dline))
            self.write('timeseal error\n')
            self.loseConnection('timeseal error')
            return
        elif t == 0:
            # it seems the Jin application's timeseal sometimes sends
            # a timestamp of 0, but still expects the command
            # to be executed
            self.log('warning: got timeseal/zipseal 0 on line: {%r} {%s}' % (line, line))

        self.session.timeseal_last_timestamp = t
        if self.state:
            self.d = getattr(self, "handleLine_" + self.state)(dline)
            if self.d:
                # if we get a deferred, pause this connection until
                # it fires
                self.pauseProducing()
                def unpause(x):
                    self.d = None
                    self.resumeProducing()
                def err(e):
                    if e.check(defer.CancelledError):
                        e.trap(defer.CancelledError)
                        return None
                    print('last line was: %s\n' % line)
                    e.printTraceback()
                    self.d = None
                    self.write('\nIt appears you have found a bug in FatICS. Please notify wmahan.\n')
                    self.write_nowrap('Error info: exception %s; line was "%s"\n' %
                        (e.getErrorMessage(), line))

                    assert(False)
                    self.loseConnection('error')
                self.d.addCallback(unpause)
                if self.d:
                    self.d.addErrback(err)

    def handleLine_prelogin(self, line):
        """ Shouldn't happen normally. """
        self.log('got line in prelogin state: %s' % line)

    def handleLine_quitting(self, line):
        # ignore
        self.log('got line in quitting state: %s' % line)

    @defer.inlineCallbacks
    def handleLine_login(self, line):
        self.session.login_last_command = time.time()
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout,
            self.login_timeout)
        if self.session.check_for_timeseal:
            self.session.check_for_timeseal = False
            (t, dec) = timeseal.decode_timeseal(line)
            if t > 0:
                if timeseal.check_hello(dec, self):
                    return
                else:
                    self.write("unknown timeseal version\n")
                    self.loseConnection('timeseal error')
            else:
                (t, dec) = timeseal.decode_zipseal(line)
                if t > 0:
                    if timeseal.check_hello_zipseal(dec, self):
                        if self.transport.compatibility:
                            self.loseConnection('Sorry, you cannot use zipseal with the compatibility port.')
                        return
                    else:
                        self.write("unknown zipseal version\n")
                        self.loseConnection('zipseal error')

        m = self.ivar_pat.match(line)
        if m:
            self.session.set_ivars_from_str(m.group(1))
            return
        name = line.strip()
        u = yield login.get_user(name, self)
        if self.state != 'quitting':
            if self.state != 'login':
                print('expected login state, but got %s' % self.state)
            assert(self.state == 'login')
            if u:
                self.claimed_user = u
                self.state = 'passwd'
                # hide password
                self.transport.will(telnet.ECHO)
            else:
                self.write("\nlogin: ")
        defer.returnValue(None)

    @defer.inlineCallbacks
    def handleLine_passwd(self, line):
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout,
            self.login_timeout)
        self.session.login_last_command = time.time()
        self.transport.wont(telnet.ECHO)
        self.write('\n')
        if self.claimed_user.is_guest:
            # ignore whatever was entered in place of a password
            yield self.prompt()
        else:
            passwd = line.strip()
            if not passwd:
                self.login()
            else:
                ret = yield self.claimed_user.check_passwd(passwd)
                if ret:
                    # password was correct
                    yield self.prompt()
                else:
                    print('wrong password from %s for user %s' % (self.ip,
                        self.claimed_user.name))
                    self.write('\n**** Invalid password! ****\n\n')
                    def resume():
                        self.login()
                    yield task.deferLater(reactor, 3, resume)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def prompt(self):
        """ Enter the prompt state, running commands from the client. """
        self.timeout_check.cancel()
        self.timeout_check = None
        self.user = self.claimed_user
        global_.langs[self.user.vars_['lang']].install(names=['ngettext'])
        global_.curuser = self.user
        assert(self.user)
        if self.user.is_admin():
            self.session.commands = global_.admin_commands
        else:
            self.session.commands = global_.commands
        d = self.user.log_on(self)
        #def handleQuit(x):
        #    if self.state == 'quitting':
        #        raise QuitException
        #    else:
        #        return x
        #d.addCallback(handleQuit)
        yield d
        if self.state == 'quitting':
            defer.returnValue(None)
        assert(self.user)
        assert(self.user.is_online)

        self.state = 'prompt'
        self.user.write_prompt()
        defer.returnValue(None)

    @defer.inlineCallbacks
    def handleLine_prompt(self, line):
        if line == TIMESEAL_PONG:
            self.session.pong(self.session.timeseal_last_timestamp)
            return

        if not utf8.check_user_utf8(line):
            print('command from %s ignored: invalid chars: %r' %
                (self.user.name, line))
            self.write(_("Command ignored: invalid characters.\n"))
            return

        global_.langs[self.user.vars_['lang']].install(names=['ngettext'])
        global_.curuser = self.user
        yield parser.parse(line, self)
        if self.state != 'quitting':
            assert(self.user)
            if self.user:
                self.user.write_prompt()
        defer.returnValue(None)

    def loseConnection(self, reason):
        if self.state == 'quitting':
            # already quitting
            return
        if self.d:
            self.d.cancel()
            self.d = None
        self.state = 'quitting'
        if self.timeout_check:
            self.timeout_check.cancel()
            self.timeout_check = None
        if reason == 'logged in again':
            # As a special case, we don't want to remove a user
            # from the online list if we are losing this connection
            # because the same user is logging in from another connection.
            # This approach is necessary because when the user re-logs in,
            # we don't want to have to wait for the first connection
            # to finish closing before logging in.
            self.logged_in_again = True
        # We prefer to call log_off() before the connection is closed so
        # we can print messages such as forfeit by disconnection,
        # but if the user disconnects abruptly then log_off() will be
        # called in connectionLost() instead.
        if self.user:
            assert(self.user.is_online)
            self.user.log_off()
            self.user = None
        self.transport.loseConnection()
        if reason == 'quit':
            #timeseal.print_stats()
            self.write(db.get_server_message('logout'))

    def connectionLost(self, reason):
        basic.LineReceiver.connectionLost(self, reason)
        if self.d:
            self.d.cancel()
            self.d = None
        if self.user:
            assert(self.user.is_online)
            if self.logged_in_again:
                self.logged_in_again = False
            else:
                # abrupt disconnection
                self.user.log_off()
                self.user = None
                self.state = 'quitting'
        self.factory.connections.remove(self)

    def write_paged(self, s):
        """ Write text, but split up long text into pages that can
        be read using the "next" command. If the parameter is None,
        continue previous long output."""
        assert(self.state == 'prompt')
        height = self.user.vars_['height']
        assert(height >= 5)
        if s is None:
            s = self.session.next_lines
        lines = s.split('\n', height - 2)
        if len(lines) == height - 1:
            self.session.next_lines = lines.pop()
            s = '\n'.join(lines)
            s = '%s\nType [next] to see next page.\n' % s
        else:
            self.session.next_lines = ''
        self.write(s)

    def write(self, s):
        # XXX check that we are connected?
        if self.buffer_output:
            self.output_buffer += s
        else:
            self.transport.write(s)

    def write_nowrap(self, s):
        if self.buffer_output:
            self.output_buffer += s
        else:
            self.transport.write(s, wrap=False)

    def log(self, s):
        # log to stdout
        print(s)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
