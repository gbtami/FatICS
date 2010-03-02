import time
from twisted.protocols import basic
import twisted.internet.interfaces
from twisted.internet import reactor
from zope.interface import implements

import telnet
import user
import command
import lang
from config import config
from timeseal import timeseal
from session import Session
from login import login

class Connection(basic.LineReceiver):
    implements(twisted.internet.interfaces.IProtocol)
    # the telnet transport changes all '\r\n' to '\n',
    # so we can just use '\n' here
    delimiter = '\n'
    MAX_LENGTH = 1024
    state = 'login'
    user = None

    def connectionMade(self):
        lang.langs['en'].install(names=['ngettext'])

        self.factory.connections.append(self)
        f = open("messages/welcome.txt")
        self.write(f.read())
        self.login()
        self.session = Session(self)
        self.session.login_last_command = time.time()
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)

    def login_timeout(self):
        assert(self.state in ['login', 'passwd'])
        self.write(_("\n**** LOGIN TIMEOUT ****\n"))
        self.loseConnection('login timeout')

    def login(self):
        #assert(self.state == 'login')
        self.state = 'login'
        f = open("messages/login.txt")
        self.write(f.read())
        self.write("login: ")

    def lineReceived(self, line):
        #print '((%s,%s))\n' % (self.state, repr(line))
        if self.session.use_timeseal:
            (t, line) = timeseal.decode_timeseal(line)
            assert(t != 0)
        elif self.session.use_zipseal:
            (t, line) = timeseal.decode_zipseal(line)
            assert(t != 0)
        if self.state:
            getattr(self, "lineReceived_" + self.state)(line)

    def lineReceived_login(self, line):
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)
        self.session.login_last_command = time.time()
        if self.session.check_for_timeseal:
            self.session.check_for_timeseal = False
            (t, dec) = timeseal.decode_timeseal(line)
            if t != 0:
                if dec[0:10] == 'TIMESTAMP|':
                    self.session.use_timeseal = True
                    return
                elif dec[0:10] == 'TIMESEAL2|':
                    self.session.use_timeseal = True
                    return
            (t, dec) = timeseal.decode_zipseal(line)
            if t != 0:
                if dec[0:8] == 'zipseal|':
                    self.session.use_zipseal = True
                    return
            # no timeseal; continue
        name = line.strip()
        self.user = login.get_user(name, self)
        if self.user:
            self.transport.will(telnet.ECHO)
            self.state = 'passwd'
        else:
            self.write("login: ")

    def lineReceived_passwd(self, line):
        self.timeout_check.cancel()
        self.timeout_check = reactor.callLater(config.login_timeout, self.login_timeout)
        self.session.login_last_command = time.time()
        self.transport.wont(telnet.ECHO)
        self.write('\n')
        if self.user.is_guest:
            # ignore whatever was entered in place of a password
            self.prompt()
        else:
            passwd = line.strip()
            if len(passwd) == 0:
                self.login()
            elif self.user.check_passwd(passwd):
                self.prompt()
            else:
                self.write('\n\n**** Invalid password! ****\n\n')
                self.login()
        assert(self.state != 'passwd')

    def prompt(self):
        self.timeout_check.cancel()
        self.user.log_on(self)
        assert(self.user.is_online)
        self.write('fics% ')
        self.state = 'online'

    def lineReceived_online(self, line):
        lang.langs[self.user.vars['lang']].install(names=['ngettext'])
        try:
            command.parser.run(line, self)
            self.write('fics% ')
        except command.QuitException:
            f = open("messages/logout.txt")
            self.write(f.read())
            self.loseConnection('quit')

    def loseConnection(self, reason):
        if self.user and self.user.is_online:
            self.user.log_off()
        self.transport.loseConnection()

    def connectionLost(self, reason):
        basic.LineReceiver.connectionLost(self, reason)
        try:
            if self.user.is_online:
                self.user.log_off()
            self.session.close()
        except AttributeError:
            pass
        self.factory.connections.remove(self)


    def write(self, s):
        self.transport.write(s)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
