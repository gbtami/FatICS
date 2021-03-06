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
import parser_
import global_
import admin
import speed_variant
import db
import trie
import var
import find_user
import config
import logger

from reload import reload
from .command import Command, ics_command
from parser_ import BadCommandError


def log_admin(admin, action):
    logger.log('admin', logger.INFO, admin.name + "(" + admin.session.conn.ip + ") " + action)


@defer.inlineCallbacks
def show_comments(conn, u, reverse=False):
    log_admin(conn.user, 'lists comments for %s' % u.name)
    comments = yield db.get_comments(u.id_)
    if not comments:
        conn.write(A_('There are no comments for %s.\n') % u.name)
        return
    comments = enumerate(comments, start=1)
    if reverse:
        comments = reversed(list(comments))
    conn.write(A_('Comments for %s:\n' % u.name))
    allcomments = [A_('%d. %s at %s: %s\n') % (i, c['admin_name'], c['when_added'], c['txt']) for (i, c) in comments]
    conn.write_paged(''.join(allcomments))


@ics_command('aclearhistory', 'w', admin.Level.admin)
class Aclearhistory(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.exact_for_user(args[0], conn)
        if u:
            # disallow clearing history for higher adminlevels?
            yield u.clear_history()
            conn.write(A_('History of %s cleared.\n') % u.name)
            log_admin(conn.user, "clears history of %s" % u.name)


@ics_command('addplayer', 'WWS', admin.Level.admin)
class Addplayer(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        [name, email, real_name] = args
        try:
            u = yield find_user.exact(name)
        except find_user.UsernameException:
            conn.write(_('"%s" is not a valid handle.\n') % name)
            return
        if u:
            conn.write(A_('A player named %s is already registered.\n')
                % u.name)
        else:
            passwd = user.make_passwd()
            user_id = yield user.add_user(name, email, passwd, real_name)
            # disabled just to speed up testing
            if False:
                yield db.add_comment(conn.user.id_, user_id,
                    'Player added by %s using addplayer.' % conn.user.name)
            conn.write(A_('Added: >%s< >%s< >%s< >%s<\n')
                % (name, real_name, email, passwd))
            log_admin(conn.user, "adds player >%s< >%s< >%s<"
                % (name, real_name, email))


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
        log_admin(conn.user, "announces: %s" % args[0])


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
        log_admin(conn.user, "unreg announces: %s" % args[0])


@ics_command('areload', '', admin.Level.god)
class Areload(Command):
    def run(self, args, conn):
        reload.reload_all(conn)
        log_admin(conn.user, "reloads all")


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
                yield u.set_admin_level(level)
                conn.write('''Admin level of %s set to %d.\n''' %
                    (u.name, level))
                log_admin(adminuser, "set admin level of %s to %d" % (u.name, level))
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
            old_maxplayer = config.maxplayer
            conn.write(A_("Previously %d total connections allowed....\n")
                % old_maxplayer)
            config.maxplayer = args[0]
            log_admin(conn.user, "changes allowed connections from %d to %d" % (old_maxplayer, config.maxplayer))

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
            old_maxguest = config.maxguest
            conn.write(A_("Previously %d guest connections allowed....\n")
                % old_maxguest)
            config.maxguest = args[0]
            log_admin(conn.user, "changes allowed guest connections from %d to %d" % (old_maxguest, config.maxguest))

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
                yield u.set_passwd(passwd)
                conn.write('Password of %s changed to %s.\n' % (u.name, '*' * len(passwd)))
                log_admin(adminuser, "changed password of %s" % u.name)
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
            yield u.del_rating(sv)
            conn.write(A_('Cleared %s %s rating for %s.\n' %
                (speed_name, variant_name, u.name)))
            log_admin(conn.user, "clears %s %s rating for %s" %
                (speed_name, variant_name, u.name))
        else:
            yield u.set_rating(sv, urating, rd, volatility, win, loss, draw,
                datetime.datetime.utcnow())
            conn.write(A_('Set %s %s rating for %s.\n' %
                (speed_name, variant_name, u.name)))
            log_admin(conn.user, "sets %s %s rating for %s" %
                (speed_name, variant_name, u.name))
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
                yield u.set_email(email)
                yield db.add_comment(adminuser.id_, u.id_,
                    'Changed email address from "%s" to "%s".' % (
                        old_email, email))
                if u.is_online:
                    u.write_('%(aname)s has changed your email address to "%(email)s".\n',
                        {'aname': adminuser.name, 'email': email})
                conn.write(A_('Email address of %(uname)s changed to "%(email)s".\n') %
                    {'uname': u.name, 'email': email})
                log_admin(adminuser, 'changes email address of %s to "%s"' %
                    (u.name, email))


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
                yield u.set_real_name(real_name)
                yield db.add_comment(adminuser.id_, u.id_,
                    'Changed real name from "%s" to "%s".' % (old_real_name, real_name))
                if u.is_online:
                    u.write_('%(aname)s has changed your real name to "%(real_name)s".\n',
                        {'aname': adminuser.name, 'real_name': real_name})
                conn.write(A_('Real name of %(uname)s changed to "%(real_name)s".\n') %
                    {'uname': u.name, 'real_name': real_name})
                log_admin(adminuser, 'changes real name of %s to "%s"' %
                    (u.name, real_name))


@ics_command('nuke', 'w', admin.Level.admin)
class Nuke(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = find_user.online_exact_for_user(args[0], conn)
        if u:
            if not admin.check_user_operation(conn.user, u):
                conn.write("You need a higher adminlevel to nuke %s!\n"
                    % u.name)
            else:
                u.write_('\n\n**** You have been kicked out by %s! ****\n\n', (conn.user.name,))
                yield u.session.conn.loseConnection('nuked')
                if not u.is_guest:
                    yield db.add_comment(conn.user.id_, u.id_, 'Nuked.')
                conn.write('Nuked: %s\n' % u.name)
                log_admin(conn.user, 'nukes %s' % u.name)


@ics_command('pose', 'wS', admin.Level.admin)
class Pose(Command):
    def run(self, args, conn):
        adminuser = conn.user
        u2 = find_user.online_exact_for_user(args[0], conn)
        if u2:
            assert(u2.is_online)
            assert(u2.session.commands)
            if not admin.check_user_operation(adminuser, u2):
                conn.write(A_('You can only pose as players below your adminlevel.\n'))
            else:
                conn.write(A_('Command issued as %s.\n') % u2.name)
                log_admin(adminuser, 'issues command as %s: %s' % (u2.name, args[1]))
                u2.write_('%s has issued the following command on your behalf: %s\n', (adminuser.name, args[1]))
                parser_.parse(args[1], u2.session.conn)


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
            yield v.set(u, args[2])
        except trie.NeedMore as e:
            conn.write(_('Ambiguous variable "%(vname)s". Matches: %(matches)s\n') % {'vname': args[1], 'matches': ' '.join([v.name for v in e.matches])})
        except KeyError:
            conn.write(_('No such variable "%s".\n') % args[1])
        except var.BadVarError:
            conn.write(_('Bad value given for variable "%s".\n') % v.name)
        else:
            conn.write(A_("Command issued as %s.\n") % (u.name))
            log_admin(adminuser, 'sets variable %s to %s for %s' % (v.name, args[2], u.name))


@ics_command('remplayer', 'w', admin.Level.admin)
class Remplayer(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.exact_for_user(args[0], conn)
        adminuser = conn.user
        if u:
            if not admin.check_user_operation(adminuser, u):
                conn.write(A_('''You can't remove an admin with a level higher than or equal to yourself.\n'''))
            elif u.is_online:
                conn.write(A_("%s is logged in.\n") % u.name)
            else:
                yield u.remove()
                conn.write(A_("Player %s removed.\n") % u.name)
                log_admin(adminuser, 'removes player %s' % u.name)


@ics_command('raisedead', 'wo', admin.Level.admin)
class Raisedead(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.exact(args[0])
        if u:
            conn.write(A_('A player named %s is already registered or online.\n')
                % u.name)
            return

        if args[1]:
            conn.write(A_('Reincarnating a user to a different name is not supported.\n'))
            return

        # XXX it is currently possible to raise a player with a
        # higher adminlevel than yourself
        try:
            yield db.user_undelete(args[0])
        except db.DeleteError:
            conn.write(A_('Raisedead failed.\n'))
        else:
            # XXX should we query the database again
            # to get the correct capitalization?
            conn.write(A_('Player %s raised.\n') % args[0])
            log_admin(conn.user, 'raises player %s' % args[0])


'''@ics_command('burydead', 'w', admin.Level.admin)
class Burydead(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        try:
            yield db.user_delete_forever(args[0])
        except db.DeleteError:
            conn.write(A_('Burydead failed.\n'))
        else:
            conn.write(A_('Player %s deleted permanently.\n') % args[0])
            log_admin(conn.user, 'deletes player %s permanently' % args[0])'''


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
                yield db.add_comment(adminuser.id_, u.id_, args[1])
                conn.write(A_('Comment added for %s.\n') % u.name)
                log_admin(adminuser, 'adds comment for %s: %s' % (u.name, args[1]))


@ics_command('showcomment', 'wo', admin.Level.admin)
class Showcomment(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        u = yield find_user.by_prefix_for_user(args[0], conn)
        reverse = False
        if args[1]:
            if args[1] == '/r':
                reverse = True
            else:
                raise BadCommandError
        if u:
            if u.is_guest:
                conn.write(A_('Unregistered players cannot have comments.\n'))
            else:
                yield show_comments(conn, u, reverse)


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
                log_admin(conn.user, 'stops forwarding conversation with %s' % conn.session.ftell.name)
                conn.session.ftell = None
        else:
            u = find_user.online_by_prefix_for_user(args[0], conn)
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
                        log_admin(conn.user, 'stops forwarding conversation with %s' % conn.session.ftell.name)
                        conn.session.ftell = None
                    ch.tell(A_("I will be forwarding the conversation between *%s* and myself to channel 0.") % u.name, conn.user)
                    log_admin(conn.user, 'starts forwarding conversation with %s' % u.name)
                    conn.session.ftell = u
                    u.session.ftell_admins.add(conn.user)


@ics_command('hideinfo', '', admin.Level.admin)
class Hideinfo(Command):
    @defer.inlineCallbacks
    def run(self, args, conn):
        yield global_.vars_['hideinfo'].set(conn.user, None)
        log_admin(conn.user, 'toggles private user info display')


@ics_command('shutdown', 'p', admin.Level.admin)
class Shutdown(Command):
    def run(self, args, conn):
        if args[0] is None:
            if reactor.shuttingDown:
                reactor.shuttingDown.cancel()
                reactor.shuttingDown = False
                for u in global_.online:
                    u.write_("\n\n    *** Server shutdown canceled by %s ***\n\n",
                        (conn.user.name,))
                log_admin(conn.user, 'cancels server shutdown')
                return
            mins = 5
        elif args[0] < 0:
            conn.write(A_('Invalid shutdown time.\n'))
            return
        else:
            mins = args[0]

        for u in global_.online:
            u.nwrite_("\n\n    *** The server is shutting down in %d minute, initiated by %s ***\n\n", "\n\n    *** The server is shutting down in %d minutes, initiated by %s ***\n\n", mins, (mins, conn.user.name))
        log_admin(conn.user, 'issues the server to shut down in %d minute(s)' % mins)

        if reactor.shuttingDown:
            reactor.shuttingDown.cancel()
        reactor.shuttingDown = reactor.callLater(mins * 60, reactor.stop)


@ics_command('chkip', 'S', admin.Level.admin)
class Chkip(Command):
    def run(self, args, conn):
        if not args[0]:
            raise BadCommandError

        if not args[0][0].isdigit():
            u = find_user.online_by_prefix_for_user(args[0], conn)
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
        log_admin(conn.user, 'issues an ip check of %s' % ip_pat)


@ics_command('asetidle', 'wd', admin.Level.admin)
class Asetidle(Command):
    """ Set a player's idle time. I implemented it to help with testing, but
    maybe there could be other uses. """
    def run(self, args, conn):
        u = find_user.online_by_prefix_for_user(args[0], conn)
        if args[1] < 0:
            raise BadCommandError
        if u:
            secs = 60 * args[1]
            u.session.last_command_time = time.time() - secs
            conn.write(A_('Idle time for "%s" set to %d seconds.\n') %
                (u.name, secs))
            u.write_("\n%s has set your idle time to %d seconds.\n",
                (conn.user.name, secs))
            log_admin(conn.user, 'sets idle time for %s to %d seconds' % (u.name, secs))

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
