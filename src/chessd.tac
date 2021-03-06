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
from twisted.internet import task, ssl
from twisted.python import log

# import the epoll reactor here instead of using the -r
# option to twistd to avoid the problem in twisted bug #3785
from twisted.internet import epollreactor
epollreactor.install()
from twisted.internet import reactor

SockJSFactory = None
try:
    from txsockjs.factory import SockJSFactory
except ImportError:
    print('Note: SockJS support not loaded')

sys.path.insert(0, 'src/')

import config
import telnet
import connection
import timer
import global_

reactor.shuttingDown = False

if os.geteuid() == 0:
    sys.path.append('.')


class IcsFactory(ServerFactory):
    def __init__(self, port):
        #ServerFactory.__init__(self)
        self.port = port

    connections = []
    def buildProtocol(self, addr):
        conn = telnet.TelnetTransport(connection.Connection)
        conn.factory = self
        conn.compatibility = self.port == config.compatibility_port
        conn.send_IAC = self.port != config.websocket_port
        return conn


def getService(port):
    """
    Return a service suitable for creating an application object.
    """
    return internet.TCPServer(port, IcsFactory(port))


def start_services(x):
    ports = [config.port, config.compatibility_port]
    if os.geteuid() == 0:
        # alternate port, for those with firewall issues
        ports.append(23)
    for port in ports:
        service = getService(port)
        service.setServiceParent(application)

    # ssl
    try:
        key = open('keys/server.key')
        cert = open('keys/server.pem')
    except IOError:
        print('Unable to read server keys; SSL support disabled')
    else:
        cert = ssl.PrivateCertificate.loadPEM(key.read() + cert.read())
        ssl_port = config.ssl_port
        service = internet.SSLServer(ssl_port, IcsFactory(ssl_port),
            cert.options())
        service.setServiceParent(application)

    # for WebSocket communication using sockjs
    if SockJSFactory:
        cf = ssl.DefaultOpenSSLContextFactory('keys/server.pem', 'keys/server.key')
        service = internet.SSLServer(config.websocket_port,
            SockJSFactory(IcsFactory(config.websocket_port)), cf)
        service.setServiceParent(application)

    lc = task.LoopingCall(timer.heartbeat)
    lc.start(timer.heartbeat_timeout)

application = service.Application("chessd")

d = global_.init()
d.addCallback(start_services)
d.addErrback(log.err)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent ft=python
