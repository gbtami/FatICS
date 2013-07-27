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

"""
a twisted application for chessd
"""

import os
import sys
from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory
from twisted.internet import task, reactor, ssl

try:
    from txsockjs.factory import SockJSFactory
except ImportError:
    SockJSFactory = None

sys.path.insert(0, 'src/')

# add a builtin to mark strings for translation that should not
# automatically be translated dynamically.
import __builtin__
# dynamically translated messages
__builtin__.__dict__['N_'] = lambda s: s
# admin messages
__builtin__.__dict__['A_'] = lambda s: s

from config import config
import telnet
import connection
import var
import timer

reactor.shuttingDown = False

if os.geteuid() == 0:
    sys.path.append('.')

class IcsFactory(ServerFactory):
    def __init__(self, port):
        #ServerFactory.__init__(self)
        self.port = port
        pass

    connections = []
    def buildProtocol(self, addr):
        conn = telnet.TelnetTransport(connection.Connection)
        conn.factory = self
        conn.compatibility = self.port == config.compatibility_port
        return conn

def getService(port):
    """
    Return a service suitable for creating an application object.
    """
    return internet.TCPServer(port, IcsFactory(port))

ports = [config.port, config.zipseal_port, config.compatibility_port]
if os.geteuid() == 0:
    # alternate port, for those with firewall issues
    ports.append(23)

application = service.Application("chessd")

for port in ports:
    service = getService(port)
    service.setServiceParent(application)

# for WebSocket communication using sockjs
if SockJSFactory:
    service = internet.TCPServer(8080, SockJSFactory(IcsFactory(8080)))
    service.setServiceParent(application)
    #reactor.listenTCP(8080, SockJSFactory(IcsFactory(8080)))

# ssl
try:
    keyAndCert = open('keys/fatics.pem')
except IOError:
    # no ssl
    pass
else:
    cert = ssl.PrivateCertificate.loadPEM(keyAndCert.read())
    ssl_port = config.ssl_port
    service = internet.SSLServer(ssl_port, IcsFactory(ssl_port),
        cert.options())
    service.setServiceParent(application)

lc = task.LoopingCall(timer.heartbeat)
lc.start(timer.heartbeat_timeout)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent ft=python
