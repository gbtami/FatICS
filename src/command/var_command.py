# -*- coding: utf-8 -*-
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

from twisted.internet import defer

from .command import ics_command, Command

import var
import trie
import admin
import global_
import find_user


@ics_command('iset', 'wS', admin.Level.user)
class Iset(Command):
    def run(self, args, conn):
        [name, val] = args
        try:
            v = global_.ivars.get(name)
            d = v.set(conn.user, val)
            # v.set() should always return a deferred that
            # is already fired for ivars
            assert(d.called)
        except trie.NeedMore as e:
            assert(len(e.matches) >= 2)
            conn.write(_('Ambiguous ivariable "%(ivname)s". Matches: %(matches)s\n') % {'ivname': name, 'matches': ' '.join([v.name for v in e.matches])})
        except KeyError:
            conn.write(_('No such ivariable "%s".\n') % name)
        except var.BadVarError:
            conn.write(_('Bad value given for ivariable "%s".\n') % v.name)


@ics_command('set', 'wT', admin.Level.user)
class Set(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        # val can be None if the user gave no value
        [name, val] = args
        try:
            v = global_.vars_.get(name)
            yield v.set(conn.user, val)
        except trie.NeedMore as e:
            assert(len(e.matches) >= 2)
            conn.write(_('Ambiguous variable "%(vname)s". Matches: %(matches)s\n') % {'vname': name, 'matches': ' '.join([v.name for v in e.matches])})
        except KeyError:
            conn.write(_('No such variable "%s".\n') % name)
        except var.BadVarError:
            conn.write(_('Bad value given for variable "%s".\n') % v.name)


@ics_command('ivariables', 'o', admin.Level.user)
class Ivariables(Command):
    def run(self, args, conn):
        if args[0] is None:
            u = conn.user
        else:
            u = find_user.online_by_prefix_for_user(args[0], conn)

        if not u:
            return

        conn.write(_("Interface variable settings of %s:\n\n") % u.name)

        conn.write('compressmove=%(compressmove)d     defprompt=%(defprompt)d        lock=%(lock)d             ms=%(ms)d\n' % u.session.ivars)
        conn.write('seekremove=%(seekremove)d       startpos=%(startpos)d         block=%(block)d            gameinfo=%(gameinfo)d\n' % u.session.ivars)
        conn.write('pendinfo=%(pendinfo)d         graph=%(graph)d            seekinfo=%(seekinfo)d         extascii=%(extascii)d\n' % u.session.ivars)
        conn.write('showserver=%(showserver)d       nohighlight=%(nohighlight)d      vthighlight=%(vthighlight)d      pin=%(pin)d\n' % u.session.ivars)
        conn.write('pinginfo=%(pinginfo)d         boardinfo=%(boardinfo)d        extuserinfo=%(extuserinfo)d      audiochat=%(audiochat)d\n' % u.session.ivars)
        conn.write('seekca=%(seekca)d           showownseek=%(showownseek)d      premove=%(premove)d          smartmove=%(smartmove)d\n' % u.session.ivars)
        conn.write('movecase=%(movecase)d         nowrap=%(nowrap)d           allresults=%(allresults)d\n' % u.session.ivars)
        conn.write('singleboard=%(singleboard)d\n' % u.session.ivars)
        conn.write('suicide=%(suicide)d          crazyhouse=%(crazyhouse)d       losers=%(losers)d           wildcastle=%(wildcastle)d\n' % u.session.ivars)
        conn.write('fr=%(fr)d               atomic=%(atomic)d\n' % u.session.ivars)
        conn.write('xml=?\n\n' % u.session.ivars)


@ics_command('variables', 'o', admin.Level.user)
class Variables(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        if args[0] is None:
            u = conn.user
        else:
            u = yield find_user.by_prefix_for_user(args[0], conn)

        if not u:
            return

        u.vars_['disp_tzone'] = u.vars_['tzone'][0:8] if (u == conn.user or
            conn.user.is_admin()) else '???'

        conn.write(_("Variable settings of %s:\n\n") % u.name)
        conn.write('time=%(time)d       private=?     shout=%(shout)d         pin=%(pin)d           style=%(style)d \n' % u.vars_)
        conn.write('inc=%(inc)d       jprivate=?    cshout=%(cshout)d        notifiedby=%(notifiedby)d    flip=?\n' % u.vars_)
        conn.write('rated=?                    kibitz=%(kibitz)d        availinfo=?     highlight=?\n' % u.vars_)
        conn.write('open=%(open)d       automail=?    kiblevel=?      availmin=?      bell=%(bell)d\n' % u.vars_)
        conn.write('pgn=?        tell=%(tell)d        availmax=?      width=%(width)d \n' % u.vars_)
        conn.write('bugopen=%(bugopen)d                  ctell=%(ctell)d         gin=%(gin)d           height=%(height)d \n' % u.vars_)
        conn.write('mailmess=%(mailmess)d                 seek=%(seek)d          ptime=%(ptime)d\n' % u.vars_)
        conn.write('tourney=?    messreply=?   chanoff=%(chanoff)d       showownseek=%(showownseek)d   tzone=%(disp_tzone)s\n' % u.vars_)
        conn.write('provshow=?                 silence=%(silence)d                       Lang=%(lang)s\n' % u.vars_)
        conn.write('autoflag=%(autoflag)d   unobserve=?   echo=?          examine=%(examine)d\n' % u.vars_)
        conn.write('minmovetime=%(minmovetime)d              tolerance=?     noescape=%(noescape)d      notakeback=%(notakeback)d\n' % u.vars_)

        if u.is_online:
            conn.write(_('\nPrompt: %s\n') % u.vars_['prompt'])
            if u.vars_['interface']:
                conn.write(_('Interface: %s\n') % u.vars_['interface'])
            if u.session.partner:
                conn.write(_('Bughouse partner: %s\n') % u.session.partner.name)
            if u.session.following:
                if u.session.pfollow:
                    conn.write(_("Following: %s's partner\n") % u.session.following)
                else:
                    conn.write(_("Following: %s\n") % u.session.following)

        for i in range(1, 10):
            fname = 'f' + str(i)
            if u.vars_[fname]:
                conn.write(' %s: %s\n' % (fname, u.vars_[fname]))
        if u.vars_['formula']:
            conn.write('Formula: %s\n' % u.vars_['formula'])
        conn.write("\n")


@ics_command('style', 'd', admin.Level.user)
class Style(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        #conn.write('Warning: the "style" command is deprecated.  Please use "set style" instead.\n')
        yield global_.vars_['style'].set(conn.user, str(args[0]))

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
