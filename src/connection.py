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
import twisted.internet.interfaces

from twisted.protocols import basic
from twisted.internet import reactor
from zope.interface import implements

import telnet
import parser
import lang
import global_

from config import config
from db import db
from timeseal import timeseal, TIMESEAL_PONG
from session import Session
from login import login

class Connection(basic.LineReceiver):
    implements(twisted.internet.interfaces.IProtocol)
    # the telnet transport changes all '\r\n' to '\n',
    # so we can just use '\n' here
    delimiter = '\n'
    MAX_LENGTH = 1024
    state = 'prelogin'
    user = None
    logged_in_again = False
    buffer_output = False
    ivar_pat = re.compile(r'%b([01]{32})')
    timeout_check = None

    def connectionMade(self):
        lang.langs['en'].install(names=['ngettext'])
        self.session = Session(self)
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

    def lineReceived(self, line):
        #print '((%s,%s))\n' % (self.state, repr(line))
        assert(not self.transport.paused)

        if self.session.use_timeseal:
            (t, dline) = timeseal.decode_timeseal(line)
        elif self.session.use_zipseal:
            (t, dline) = timeseal.decode_zipseal(line)
        else:
            t = None
            dline = line
        if t != None and t < 0:
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
            getattr(self, "handleLine_" + self.state)(dline)

    def handleLine_prelogin(self, line):
        """ Shouldn't happen normally. """
        self.log('got line in prelogin state')

    def handleLine_quitting(self, line):
        # ignore
        pass

    def handleLine_login(self, line):
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)
        self.session.login_last_command = time.time()
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
        # hide password
        self.transport.will(telnet.ECHO)
        self.claimed_user = login.get_user(name, self)
        if self.claimed_user:
            self.state = 'passwd'
        else:
            if self.state != 'quitting':
                self.transport.wont(telnet.ECHO)
                self.write("\nlogin: ")

    def handleLine_passwd(self, line):
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)
        self.session.login_last_command = time.time()
        self.transport.wont(telnet.ECHO)
        self.write('\n')
        if self.claimed_user.is_guest:
            # ignore whatever was entered in place of a password
            self.prompt()
        else:
            passwd = line.strip()
            if len(passwd) == 0:
                self.login()
            elif self.claimed_user.check_passwd(passwd):
                self.prompt()
            else:
                print('wrong password from %s for user %s' % (self.ip,
                    self.claimed_user.name))
                self.write('\n**** Invalid password! ****\n\n')
                self.pauseProducing()
                def resume():
                    self.login()
                    self.resumeProducing()
                reactor.callLater(3, resume)

    def prompt(self):
        """ Enter the prompt state, running commands from the client. """
        self.timeout_check.cancel()
        self.timeout_check = None
        self.user = self.claimed_user
        self.user.log_on(self)
        assert(self.user.is_online)
        if self.user.is_admin():
            self.session.commands = global_.admin_commands
        else:
            self.session.commands = global_.commands

        self.state = 'prompt'
        self.user.write_prompt()

    def handleLine_prompt(self, line):
        if line == TIMESEAL_PONG:
            self.session.pong(self.session.timeseal_last_timestamp)
            return

        lang.langs[self.user.vars['lang']].install(names=['ngettext'])
        self.d = parser.parse(line, self)
        if self.d:
            self.pauseProducing()
            def resume(d):
                self.user.write_prompt()
                self.resumeProducing()
            self.d.addCallback(resume)
            def err(e):
                self.loseConnection()
            self.d.addErrback(err)
            #self.buffer_input = True
        else:
            if self.user:
                self.user.write_prompt()

    def loseConnection(self, reason):
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
        if self.user: #and self.user.is_online:
            assert(self.user.is_online)
            self.user.log_off()
            self.user = None
        self.transport.loseConnection()
        if reason == 'quit':
            #timeseal.print_stats()
            self.write(db.get_server_message('logout'))

    def connectionLost(self, reason):
        basic.LineReceiver.connectionLost(self, reason)
        if self.user: # and self.user.is_online:
            assert(self.user.is_online)
            if self.logged_in_again:
                self.logged_in_again = False
            else:
                # abrupt disconnection
                self.user.log_off()
                self.user = None
        self.factory.connections.remove(self)

    def write_paged(self, s):
        """ Write text, but split up long text into pages that can
        be read using the "next" command. If the parameter is None,
        continue previous long output."""
        assert(self.state == 'prompt')
        height = self.user.vars['height']
        assert(height >= 5)
        if s is None:
            s = self.session.next_lines
        lines = s.split('\n', height - 2)
        if len(lines) ==  height - 1:
            self.session.next_lines = lines.pop()
            s = '\n'.join(lines)
            s = '%s\nType [next] to see next page.\n' % s
        else:
            self.session.next_lines = ''
        self.write(s)

    def write(self, s):
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
