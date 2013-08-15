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

import time
import datetime
from twisted.internet import reactor, defer

import user
import parser
import global_
import admin
import speed_variant
import db
import trie
import var
import find_user
import config

from reload import reload
from .command import Command, ics_command
from parser import BadCommandError


@ics_command('aclearhistory', 'w', admin.Level.admin)
class Aclearhistory(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.exact_for_user(args[0], conn)
        if u:
            # disallow clearing history for higher adminlevels?
            u.clear_history()
            conn.write(A_('History of %s cleared.\n') % u.name)


@ics_command('addplayer', 'WWS', admin.Level.admin)
class Addplayer(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        [name, email, real_name] = args
        try:
            u = yield find_user.exact(name)
        except user.UsernameException:
            conn.write(_('"%s" is not a valid handle.\n') % name)
            return
        if u:
            conn.write(A_('A player named %s is already registered.\n')
                % u.name)
        else:
            passwd = user.make_passwd()
            user_id = user.add_user(name, email, passwd, real_name)
            #db.add_comment(conn.user.id, user_id,
            #    'Player added by %s using addplayer.' % conn.user.name)
            conn.write(A_('Added: >%s< >%s< >%s< >%s<\n')
                % (name, real_name, email, passwd))


@ics_command('announce', 'S', admin.Level.admin)
class Announce(Command):
    def run(self, args, conn):
        count = 0
        # the announcement message isn't localized
        for u in global_.online:
            if u != conn.user:
                count = count + 1
                u.write("\n\n    **ANNOUNCEMENT** from %s: %s\n\n" %
                    (conn.user.name, args[0]))
        conn.write("(%d) **ANNOUNCEMENT** from %s: %s\n\n" %
            (count, conn.user.name, args[0]))


@ics_command('annunreg', 'S', admin.Level.admin)
class Annunreg(Command):
    def run(self, args, conn):
        count = 0
        # the announcement message isn't localized
        for u in global_.online:
            if u != conn.user and u.is_guest:
                count = count + 1
                u.write("\n\n    **UNREG ANNOUNCEMENT** from %s: %s\n\n"
                    % (conn.user.name, args[0]))
        conn.write("(%d) **UNREG ANNOUNCEMENT** from %s: %s\n\n"
            % (count, conn.user.name, args[0]))


@ics_command('areload', '', admin.Level.god)
class Areload(Command):
    def run(self, args, conn):
        reload.reload_all(conn)


@ics_command('asetadmin', 'wd', admin.Level.admin)
class Asetadmin(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        [name, level] = args
        adminuser = conn.user
        u = yield find_user.exact_for_user(name, conn)
        if u:
            # Note: it's possible to set the admin level
            # of a guest.
            if u == adminuser:
                conn.write(A_("You can't change your own adminlevel.\n"))
                return
            if not admin.check_user_operation(adminuser, u):
                conn.write(A_('You can only set the adminlevel for players below your adminlevel.\n'))
            elif not admin.check_level(adminuser.admin_level, level):
                conn.write('''You can't promote someone to or above your adminlevel.\n''')
            else:
                u.set_admin_level(level)
                conn.write('''Admin level of %s set to %d.\n''' %
                    (u.name, level))
                if u.is_online:
                    # update user's command list
                    if u.is_admin():
                        u.session.commands = global_.admin_commands
                    else:
                        u.session.commands = global_.commands
                    u.write(A_('''\n\n%s has set your admin level to %d.\n\n''') % (adminuser.name, level))


@ics_command('asetmaxplayer', 'p', admin.Level.admin)
class Asetmaxplayer(Command):
    def run(self, args, conn):
        if args[0] is not None:
            # basic sanity checks XXX
            if args[0] < 10 or args[0] > 100000:
                raise BadCommandError
            conn.write(A_("Previously %d total connections allowed....\n")
                % config.maxplayer)
            config.maxplayer = args[0]

        conn.write(A_('There are currently %d regular and %d admin connections available.\n') %
            (max(config.maxplayer - config.admin_reserve, 0), min(config.maxplayer - len(global_.online), config.admin_reserve)))
        conn.write(A_('Total allowed connections: %d.\n') % config.maxplayer)


@ics_command('asetmaxguest', 'p', admin.Level.admin)
class Asetmaxguest(Command):
    def run(self, args, conn):
        if args[0] is not None:
            if args[0] < 0:
                raise BadCommandError
            elif args[0] + config.admin_reserve > config.maxplayer:
                conn.write(A_("maxguest + admin_reserve > maxplayer (%d + %d > %d); not changing\n") % (args[0], config.admin_reserve, config.maxplayer))
                return
            conn.write(A_("Previously %d guest connections allowed....\n")
                % config.maxguest)
            config.maxguest = args[0]

        conn.write(A_('Allowed guest connections: %d.\n') % config.maxguest)


@ics_command('asetpasswd', 'wW', admin.Level.admin)
class Asetpasswd(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        (name, passwd) = args
        adminuser = conn.user
        u = yield find_user.exact_for_user(name, conn)
        if u:
            if u.is_guest:
                conn.write('You cannot set the password of an unregistered player!\n')
            elif not admin.check_user_operation(adminuser, u):
                conn.write('You can only set the password of players below your adminlevel.\n')
            elif not user.is_legal_passwd(passwd):
                conn.write('"%s" is not a valid password.\n' % passwd)
            else:
                u.set_passwd(passwd)
                conn.write('Password of %s changed to %s.\n' % (u.name, '*' * len(passwd)))
                if u.is_online:
                    u.write_('\n%s has changed your password.\n', (adminuser.name,))


@ics_command('asetrating', 'wwwddfddd', admin.Level.admin)
class Asetrating(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        (name, speed_name, variant_name, urating, rd, volatility, win,
            loss, draw) = args
        u = yield find_user.exact_for_user(name, conn)
        if not u:
            return
        if u.is_guest:
            conn.write(A_('You cannot set the rating of an unregistered player.\n'))
            return
        try:
            sv = speed_variant.from_names(speed_name, variant_name)
        except KeyError:
            conn.write(A_('Unknown speed and variant "%s %s".\n') %
                (speed_name, variant_name))
            return
        if urating == 0:
            u.del_rating(sv)
            conn.write(A_('Cleared %s %s rating for %s.\n' %
                (speed_name, variant_name, u.name)))
        else:
            u.set_rating(sv, urating, rd, volatility, win, loss, draw,
                datetime.datetime.utcnow())
            conn.write(A_('Set %s %s rating for %s.\n' %
                (speed_name, variant_name, u.name)))
        # XXX notify the user?


@ics_command('asetemail', 'ww', admin.Level.admin)
class Asetemail(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        adminuser = conn.user
        u = yield find_user.exact_for_user(args[0], conn)
        if u:
            if not admin.check_user_operation(adminuser, u):
                conn.write("You need a higher adminlevel to change the email address of %s.\n" % u.name)
                return
            if u.is_guest:
                conn.write(A_('You can only set the email for registered players.\n'))
                return

            email = args[1]
            if email is None:
                assert(False)
            else:
                if '@' not in email:
                    conn.write(A_('That does not look like an email address.\n'))
                    return
                old_email = u.email
                u.set_email(email)
                yield db.add_comment_async(adminuser.id, u.id,
                    'Changed email address from "%s" to "%s".' % (
                        old_email, email))
                if u.is_online:
                    u.write_('%(aname)s has changed your email address to "%(email)s".\n',
                        {'aname': adminuser.name, 'email': email})
                conn.write(A_('Email address of %(uname)s changed to "%(email)s".\n') %
                    {'uname': u.name, 'email': email})


@ics_command('asetrealname', 'wS', admin.Level.admin)
class Asetrealname(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        adminuser = conn.user
        u = yield find_user.exact_for_user(args[0], conn)
        if u:
            if not admin.check_user_operation(adminuser, u):
                conn.write("You need a higher adminlevel to change the real name of %s.\n" % u.name)
                return
            if u.is_guest:
                conn.write(A_('You can only set the real name of registered players.\n'))
                return

            real_name = args[1]
            if real_name is None:
                assert(False)
            else:
                old_real_name = u.real_name
                u.set_real_name(real_name)
                yield db.add_comment_async(adminuser.id, u.id,
                    'Changed real name from "%s" to "%s".' % (old_real_name, real_name))
                if u.is_online:
                    u.write_('%(aname)s has changed your real name to "%(real_name)s".\n',
                        {'aname': adminuser.name, 'real_name': real_name})
                conn.write(A_('Real name of %(uname)s changed to "%(real_name)s".\n') %
                    {'uname': u.name, 'real_name': real_name})


@ics_command('nuke', 'w', admin.Level.admin)
class Nuke(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = global_.online.find_exact_for_user(args[0], conn)
        if u:
            if not admin.check_user_operation(conn.user, u):
                conn.write("You need a higher adminlevel to nuke %s!\n"
                    % u.name)
            else:
                u.write_('\n\n**** You have been kicked out by %s! ****\n\n', (conn.user.name,))
                u.session.conn.loseConnection('nuked')
                if not u.is_guest:
                    yield db.add_comment_async(conn.user.id, u.id, 'Nuked.')
                conn.write('Nuked: %s\n' % u.name)
        defer.returnValue(None)


@ics_command('pose', 'wS', admin.Level.admin)
class Pose(Command):
    def run(self, args, conn):
        adminuser = conn.user
        u2 = global_.online.find_exact_for_user(args[0], conn)
        if u2:
            if not admin.check_user_operation(adminuser, u2):
                conn.write(A_('You can only pose as players below your adminlevel.\n'))
            else:
                conn.write(A_('Command issued as %s.\n') % u2.name)
                u2.write_('%s has issued the following command on your behalf: %s\n', (adminuser.name, args[1]))
                parser.parse(args[1], u2.session.conn)


@ics_command('asetv', 'wwS', admin.Level.admin)
class Asetv(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        adminuser = conn.user
        u = yield find_user.exact_for_user(args[0], conn)
        if not u:
            return
        if u == adminuser:
            conn.write(A_("You can't asetv yourself.\n"))
            return
        if not admin.check_user_operation(adminuser, u):
            conn.write(A_('You can only asetv players below your adminlevel.\n'))
            return
        try:
            v = global_.vars_.get(args[1])
            v.set(u, args[2])
        except trie.NeedMore as e:
            conn.write(_('Ambiguous variable "%(vname)s". Matches: %(matches)s\n') % {'vname': args[1], 'matches': ' '.join([v.name for v in e.matches])})
        except KeyError:
            conn.write(_('No such variable "%s".\n') % args[1])
        except var.BadVarError:
            conn.write(_('Bad value given for variable "%s".\n') % v.name)
        else:
            conn.write(A_("Command issued as %s.\n") % (u.name))


@ics_command('remplayer', 'w', admin.Level.admin)
class Remplayer(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        d = find_user.exact_for_user(args[0], conn)
        adminuser = conn.user
        u = yield d
        if u:
            if not admin.check_user_operation(adminuser, u):
                conn.write(A_('''You can't remove an admin with a level higher than or equal to yourself.\n'''))
            elif u.is_online:
                conn.write(A_("%s is logged in.\n") % u.name)
            else:
                u.remove()
                conn.write(A_("Player %s removed.\n") % u.name)


@ics_command('addcomment', 'wS', admin.Level.admin)
class Addcomment(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        adminuser = conn.user
        u = yield find_user.exact_for_user(args[0], conn)
        if u:
            if u.is_guest:
                conn.write(A_('Unregistered players cannot have comments.\n'))
            else:
                yield db.add_comment_async(adminuser.id, u.id, args[1])
                conn.write(A_('Comment added for %s.\n') % u.name)


@ics_command('showcomment', 'w', admin.Level.admin)
class Showcomment(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.by_prefix_for_user(args[0], conn)
        if u:
            if u.is_guest:
                conn.write(A_('Unregistered players cannot have comments.\n'))
            else:
                comments = yield db.get_comments(u.id)
                if not comments:
                    conn.write(A_('There are no comments for %s.\n') % u.name)
                else:
                    allcomments = [A_('%s at %s: %s\n') % (c['admin_name'], c['when_added'], c['txt']) for c in comments]
                    conn.write_paged('\n'.join(allcomments))


@ics_command('ftell', 'o', admin.Level.admin)
class Ftell(Command):
    def run(self, args, conn):
        ch = global_.channels[0]
        if not args[0]:
            if not conn.session.ftell:
                conn.write(A_("You were not forwarding a conversation.\n"))
            else:
                conn.write(A_("Stopping the forwarding of the conversation with %s.") % conn.session.ftell.name)
                conn.session.ftell.session.ftell_admins.remove(conn.user)
                ch.tell(A_("I will no longer be forwarding the conversation between *%s* and myself.") % conn.session.ftell.name, conn.user)
                conn.session.ftell = None
        else:
            u = user.find_by_prefix_for_user(args[0], conn)
            if u:
                if u == conn.user:
                    conn.write(A_('Nobody wants to listen to you talking to yourself! :-)\n'))
                else:
                    if conn.user not in ch.online or not conn.user.hears_channels():
                            conn.write(A_("Not forwarding because you are not listening to channel 0.\n"))
                            return
                    if conn.session.ftell:
                        conn.session.ftell.session.ftell_admins.remove(conn.user)
                        ch.tell(A_("I will no longer be forwarding the conversation between *%s* and myself.") % conn.session.ftell.name, conn.user)
                        conn.session.ftell = None
                    ch.tell(A_("I will be forwarding the conversation between *%s* and myself to channel 0.") % u.name, conn.user)
                    conn.session.ftell = u
                    u.session.ftell_admins.add(conn.user)


@ics_command('hideinfo', '', admin.Level.admin)
class Hideinfo(Command):
    def run(self, args, conn):
        global_.vars_['hideinfo'].set(conn.user, None)


@ics_command('shutdown', 'p', admin.Level.admin)
class Shutdown(Command):
    def run(self, args, conn):
        if args[0] is None:
            if reactor.shuttingDown:
                reactor.shuttingDown.cancel()
                reactor.shuttingDown = False
                for u in global_.online:
                    u.write_("\n\n    *** Server shutdown canceled by %s ***\n\n", conn.user.name)
                return
            mins = 5
        elif args[0] < 0:
            conn.write(A_('Invalid shutdown time.\n'))
            return
        else:
            mins = args[0]

        for u in global_.online:
            u.nwrite_("\n\n    *** The server is shutting down in %d minute, initiated by %s ***\n\n", "\n\n    *** The server is shutting down in %d minutes, initiated by %s ***\n\n", mins, (mins, conn.user.name))

        if reactor.shuttingDown:
            reactor.shuttingDown.cancel()
        reactor.shuttingDown = reactor.callLater(mins * 60, reactor.stop)


@ics_command('chkip', 'S', admin.Level.admin)
class Chkip(Command):
    def run(self, args, conn):
        if not args[0]:
            raise BadCommandError

        if not args[0][0].isdigit():
            u = user.find_by_prefix_for_user(args[0], conn)
            if u:
                ip_pat = u.session.conn.ip
            else:
                return
        else:
            ip_pat = args[0]

        def compare_ip(ip, pat):
            if len(pat) > len(ip):
                return False
            for i in range(1, len(pat)):
                if pat[i] == '*':
                    return True
                elif pat[i] != ip[i]:
                    return False
            return True

        #conn.write(A_("Matches the following player(s): \n\n"))
        count = 0
        for u in global_.online:
            if compare_ip(u.session.conn.ip, ip_pat):
                conn.write('%-18s %s\n' % (u.name, u.session.conn.ip))
                count += 1
                if count > 10:
                    break
        conn.write(A_("Number of players matched: %d\n") % count)


@ics_command('asetidle', 'wd', admin.Level.admin)
class Asetidle(Command):
    """ Set a player's idle time. I implemented it to help with testing, but
    maybe there could be other uses. """
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.by_prefix_for_user(args[0], conn, online_only=True)
        if args[1] < 0:
            raise BadCommandError
        if u:
            secs = 60 * args[1]
            u.session.last_command_time = time.time() - secs
            conn.write(A_('Idle time for "%s" set to %d seconds.\n') %
                (u.name, secs))
            u.write_("\n%s has set your idle time to %d seconds.\n",
                (conn.user.name, secs))

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
