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

from test import *

import time

class CommandTest(Test):
    def test_addplayer_and_remplayer(self):
        t = self.connect_as_admin()

        t.write('addplayer TestPlayer1 nobody@example.com Foo Bar\n')
        self.expect('"TestPlayer1" is not a valid handle.', t)

        t.write('addplayer TestPlayer nobody@example.com Foo Bar\n')
        self.expect('Added: >TestPlayer< >Foo Bar< >nobody@example.com<', t)
        t.write('addplayer testplayer nobody@example.com Foo Bar\n')
        self.expect('already registered', t)

        t.write('finger testplayer\n')
        self.expect('Finger of TestPlayer:', t)

        t.write('raisedead testplayer\n')
        self.expect('already registered', t)

        t.write('remplayer testplayer\n')
        self.expect('Player TestPlayer removed.', t)

        t.write('finger testplayer\n')
        self.expect('There is no player matching the name', t)

        t.write('raisedead testplayer\n')
        # XXX capitalization
        self.expect('Player testplayer raised.', t)

        t.write('finger testplayer\n')
        self.expect('Finger of TestPlayer:', t)

        t.write('remplayer testplayer\n')
        self.expect('Player TestPlayer removed.', t)

        self.close(t)

    def test_announce(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()

        t.write("announce This is a test announcement; please ignore. ♟\n")
        m = self.expect_re(r'\((\d+)\) \*\*ANNOUNCEMENT\*\* from admin: This is a test announcement; please ignore. ♟', t)
        self.assert_(m.group(1) >= 1)
        self.expect('**ANNOUNCEMENT** from admin: This is a test announcement; please ignore. ♟', t2)
        self.close(t)
        self.close(t2)

    @with_player('testplayer')
    def test_annunreg(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest()
        t3 = self.connect_as_guest()
        t4 = self.connect_as('testplayer')

        t.write("annunreg Test please ignore\n")
        m = self.expect_re(r'\((\d+)\) \*\*UNREG ANNOUNCEMENT\*\* from admin: Test please ignore', t)
        self.assert_(m.group(1) >= 2)
        self.expect('**UNREG ANNOUNCEMENT** from admin: Test please ignore', t2)
        self.expect('**UNREG ANNOUNCEMENT** from admin: Test please ignore', t3)
        self.expect_not('**UNREG ANNOUNCEMENT**', t4)
        self.close(t)
        self.close(t2)
        self.close(t3)
        self.close(t4)

    def test_nuke(self):
        t = self.connect_as_admin()

        t.write('nuke 123\n')
        self.expect('No player named', t)

        t.write('nuke guesttest\n')
        self.expect('No player named', t)

        t2 = self.connect_as_guest('GuestTest')
        t.write('nuke guesttest\n')
        self.expect('You have been kicked out', t2)
        self.expect_EOF(t2)
        self.expect('Nuked: GuestTest', t)
        t2.close()

        t.write('nuke guesttest\n')
        self.expect('No player named "guesttest" is online.', t)

        t2 = self.connect_as_guest('GuestTest')
        t.write('asetadmin guesttest 100\n')
        t2.write('nuke admin\n')
        self.expect('need a higher adminlevel', t2)
        self.close(t2)

        self.close(t)

    @with_player('TestPlayer')
    def test_nuke_registered(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')

        t.write('nuke testplayer\n')
        self.expect('You have been kicked out by admin', t2)
        self.expect('Nuked: TestPlayer', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Nuked', t)

        self.close(t)
        self.expect_EOF(t2)

    @with_player('testplayer')
    def test_asetpass(self):
        t = self.connect_as_admin()

        t2 = self.connect_as_guest('GuestTest')
        t.write('asetpass GuestTest pass\n')
        self.expect('cannot set the password', t)
        self.close(t2)

        t2 = self.connect_as('testplayer')
        t.write('asetpass testplayer blah\n')
        self.expect("Password of testplayer changed", t)
        self.expect("admin has changed your password", t2)
        self.close(t)
        self.close(t2)

        t2 = self.connect()
        t2.write('testplayer\nblah\n')
        self.expect('fics%', t2)
        self.close(t2)

    @with_player('testplayer')
    @with_player('testtwo')
    def test_asetadmin(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')
        t.write('asetadmin testplayer 100\n')
        self.expect('Admin level of testplayer set to 100.', t)
        self.close(t)

        self.expect('admin has set your admin level to 100.', t2)
        t2.write('asetadmin admin 100\n')
        self.expect('You can only set the adminlevel for players below', t2)
        t2.write('asetadmin testplayer 1000\n')
        self.expect("You can't change your own", t2)

        t2.write('asetadmin testtwo 100\n')
        self.expect('''You can't promote''', t2)

        t2.write('asetadmin testtwo 50\n')
        self.expect('Admin level of testtwo set', t2)
        self.close(t2)

    def test_asetemail(self):
        t = self.connect_as_admin()
        t.write('addplayer TestPlayer nobody@example.com Foo Bar\n')
        m = self.expect_re(r'Added: >TestPlayer< >Foo Bar< >nobody@example.com< >(.*)<\r\n', t)
        t2 = self.connect_as('testplayer', passwd=m.group(1))

        t.write('f testplayer\n')
        self.expect('nobody@example.com', t)

        t.write('asetemail testplayer new@example.org\n')
        self.expect('Email address of TestPlayer changed to "new@example.org".', t)
        self.expect('admin has changed your email address to "new@example.org".', t2)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Changed email address from "nobody@example.com" to "new@example.org".', t)

        t.write('f testplayer\n')
        self.expect_re('Email: +new@example.org', t)

        self.close(t2)

        # check again to be sure the change was committed to the DB
        t.write('f testplayer\n')
        self.expect('new@example.org', t)
        t.write('remplayer testplayer\n')
        self.expect('Player TestPlayer removed.', t)

        self.close(t)

    @with_player('TestPlayer')
    def test_asetrealname(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('testplayer')

        t.write('asetrealname testplayer John Doe\n')
        self.expect('Real name of TestPlayer changed to "John Doe".', t)

        t.write('f testplayer\n')
        self.expect_re('Real name: +John Doe', t)

        self.expect('admin has changed your real name to "John Doe".', t2)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Changed real name from .* to "John Doe".', t)

        self.close(t2)
        self.close(t)

    @with_player('TestPlayer')
    def test_asetemail_bad(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')

        t.write('asetemail guestabcd nobody@example.org\n')
        self.expect('You can only set the email for registered', t)
        t.write('asetemail admin test@example.com\n')
        self.expect('You need a higher adminlevel', t)
        t.write('asetemail testplayer test\n')
        self.expect('That does not look like an email address.', t)

        self.close(t)
        self.close(t2)

    def test_asetrating(self):
        t = self.connect_as_admin()
        t.write('asetrating admin blitz chess 2000 200 .005 100 75 35\n')
        self.expect('Set blitz chess rating for admin.\r\n', t)
        self.close(t)

        t = self.connect_as_admin()
        t.write('finger admin\n')
        self.expect('blitz                    2000   200  0.005000     210', t)
        t.write('asetrating admin blitz chess 0 0 0 0 0 0\n')
        self.expect('Cleared blitz chess rating for admin.\r\n', t)
        t.write('finger admin\n')
        self.expect_not('blitz chess', t)
        self.close(t)

    def test_aclearhistory(self):
        t = self.connect_as_guest('GuestABCD')
        t2 = self.connect_as_admin()
        self.set_style_12(t)
        self.set_style_12(t2)
        t.write('match admin white 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)
        t.write('e4\n')
        self.expect('e4', t2)
        t2.write('e5\n')
        self.expect('e5', t)
        t2.write('resign\n')
        self.expect('admin resigns', t)
        self.expect('admin resigns', t2)

        t.write('history admin\n')
        self.expect('History for admin:', t)

        t2.write('aclearhist admin\n')
        self.expect('History of admin cleared.', t2)

        t.write('history admin\n')
        self.expect('admin has no history games.', t)

        t2.write('aclearhist guestabcd\n')
        self.expect('History of GuestABCD cleared.', t2)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_pose(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')

        t.write('pose testplayer test\n')
        self.expect('No player named "testplayer" is online', t)

        t.write('pose guestabcd finger testplay\n')
        self.expect('Command issued as GuestABCD.', t)
        self.expect('admin has issued the following command on your behalf: finger testplay', t2)
        self.expect('Finger of TestPlayer:', t2)

        t.write('pose guestabcd badcommand\n')
        self.expect('badcommand: Command not found', t2)
        self.close(t2)

        t2 = self.connect_as('testplayer')
        t.write('pose testplayer shout Test; please ignore\n')
        self.expect('TestPlayer shouts: Test; please ignore', t)

        self.close(t)
        self.close(t2)

    def test_admin(self):
        t = self.connect_as_admin()
        t.write('admin\n')
        self.expect('(*) is now not shown', t)
        t.write('f admin\n')
        self.expect('Finger of admin:', t)
        self.close(t)

        t = self.connect_as_admin()
        t.write('f admin\n')
        self.expect('Finger of admin:', t)
        t.write('admin\n')
        self.expect('(*) is now shown', t)
        t.write('f admin\n')
        self.expect('Finger of admin(*):', t)

        self.close(t)

    def test_asetv(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')

        t.write('asetv guestabcd pin\n')
        self.expect('Usage:', t)

        t.write('asetv doesnotexist pin 1\n')
        self.expect('There is no player matching the name "doesnotexist".', t)

        t.write('asetv guestabcd pin foo\n')
        self.expect('Bad value', t)

        t.write('asetv guestabcd t foo\n')
        self.expect('Ambiguous', t)

        t.write('asetv guestabcd pin 1\n')
        self.expect('Command issued as GuestABCD', t)
        self.expect('You will now hear logins/logouts.', t2)
        self.close(t)

        self.expect('[admin has disconnected.]', t2)

        self.close(t2)

class PermissionsTest(Test):
    def test_permissions(self):
        t = self.connect_as_guest()
        t.write('asetpass admin test\n')
        self.expect('asetpass: Command not found', t)
        self.close(t)

class CommentTest(Test):
    @with_player('TestPlayer')
    def test_comment(self):
        t = self.connect_as_admin()

        t.write('showcomment testplayer\n')
        self.expect('There are no comments for TestPlayer.', t)

        t.write('addcomment testplayer This is a test comment.\n')
        self.expect('Comment added for TestPlayer.', t)
        time.sleep(1)
        t.write('addcomment testplay Partial names not accepted.\n')
        self.expect('no player matching the name', t)

        t.write('addcomment testplayer Comment #2\n')
        self.expect('Comment added for TestPlayer.', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: This is a test comment.', t)
        self.expect_re('2. admin at .*: Comment #2.', t)

        t.write('showcomment testplayer /r\n')
        self.expect_re('2. admin at .*: Comment #2.', t)
        self.expect_re('1. admin at .*: This is a test comment.', t)

        self.close(t)

    def test_comment_bad(self):
        t = self.connect_as_admin()
        t.write('addcomment nosuchplayer test\n')
        self.expect('There is no player matching the name "nosuchplayer".', t)
        t.write('showcomment nosuchplayer\n')
        self.expect('There is no player matching the name "nosuchplayer".', t)

        t.write('addcomment admin\n')
        self.expect('Usage:', t)

        t2 = self.connect_as_guest('GuestABCD')
        t.write('addcomment  guestabcd test\n')
        self.expect('Unregistered players cannot have comments.', t)
        t.write('showcomment guestabcd\n')
        self.expect('Unregistered players cannot have comments.', t)
        self.close(t2)

        self.close(t)

class BanTest(Test):
    @with_player('TestPlayer')
    def test_ban(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+ban testplayer\n')
        self.expect('TestPlayer added to the ban list.', t)
        self.expect('Note: TestPlayer is online.', t)
        # XXX original FICS also sends "You have been added to the ban list by admin."
        t.write('+ban testplayer\n')
        self.expect('TestPlayer is already on the ban list.', t)
        t.write('nuke testplayer\n')
        self.expect('Nuked: TestPlayer', t)

        self.expect('You have been kicked out by admin', t2)
        t2.close()

        t.write('=ban\n')
        self.expect('-- ban list: 1 name --\r\nTestPlayer\r\n', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Banned', t)
        self.expect_re('2. admin at .*: Nuked', t)

        t2 = self.connect()
        t2.write('testplayer\n')
        self.expect('Player "TestPlayer" is banned.', t2)
        self.expect_EOF(t2)

        t.write('-ban testplayer\n')
        self.expect('TestPlayer removed from the ban list.', t)

        t2 = self.connect_as('testplayer')

        t.write('-ban testplayer\n')
        self.expect('TestPlayer is not on the ban list.', t)

        t2.write('+ban admin\n')
        self.expect('"ban" does not match any list name', t2)
        t2.write('=ban\n')
        self.expect('"ban" does not match any list name', t2)

        self.close(t)
        self.close(t2)

    def test_ban_bad(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')
        t.write('+ban nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+ban admin\n')
        self.expect('Admins cannot be banned.', t)
        t.write('+ban guestabcd\n')
        self.expect('Only registered players can be banned.', t)
        self.close(t)
        self.close(t2)

    def test_hideinfo(self):
        t = self.connect_as_admin()
        t.write('set hideinfo 1\n')
        self.expect('Private user information now not shown.', t)
        t.write('f\n')
        self.expect_not('Host:', t)
        t.write('log\n')
        self.expect_not(' from %s' % LOCAL_IP, t)
        self.close(t)

        # should be preseved across logouts
        t = self.connect_as_admin()
        t.write('f\n')
        self.expect_not('Host:', t)

        t.write('set hideinfo\n')
        self.expect('Private user information now shown.', t)
        t.write('f\n')
        self.expect('Host:', t)
        t.write('log\n')
        self.expect(' from %s' %  LOCAL_IP, t)

        t.write('hideinfo\n')
        self.expect('Private user information now not shown.', t)
        t.write('hideinfo\n')
        self.expect('Private user information now shown.', t)

        self.close(t)

class FilterTest(Test):
    def test_filter_ip(self):
        t = self.connect_as_admin()
        t.write('+filter foobar\n')
        self.expect('Invalid filter pattern.', t)

        t.write('+filter 127.0.0.1\n')
        self.expect('127.0.0.1/32 added to the filter list.', t)
        t.write('+filter 127.0.0.1\n')
        self.expect('127.0.0.1/32 is already on the filter list.', t)

        t2 = self.connect()
        t2.write('g\n')
        self.expect('guest logins are blocked', t2)
        self.expect_EOF(t2)

        t.write('-filter 127.0.0.1\n')
        self.expect('127.0.0.1/32 removed from the filter list.', t)
        t.write('-filter 127.0.0.1\n')
        self.expect('127.0.0.1/32 is not on the filter list.', t)

        self.close(self.connect_as_guest())

        self.close(t)

    def test_filter_cidr(self):
        t = self.connect_as_admin()

        t.write('+filter 127.0.7.7/16\n')
        self.expect('127.0.0.0/16 added to the filter list.', t)
        t.write('-filter 127.0.0.1\n')
        self.expect('127.0.0.1/32 is not on the filter list.', t)

        t2 = self.connect()
        t2.write('g\n')
        self.expect('guest logins are blocked', t2)
        self.expect_EOF(t2)

        t.write('-filter 127.0.0.0/16\n')
        self.expect('127.0.0.0/16 removed from the filter list.', t)

        self.close(self.connect_as_guest())

        self.close(t)

    '''def test_implicit_prefix(self):
        t = self.connect_as_admin()

        t.write('+filter 168.50\n')
        self.expect('168.50.0.0/16 added to the filter list.', t)
        t.write('+filter 168.50.3.1/16\n')
        self.expect('168.50.0.0/16 is already on the filter list.', t)
        t.write('-filter 168.50/16\n')
        self.expect('168.50.0.0/16 removed from the filter list.', t)

        t.write('+filter 192.168.2\n')
        self.expect('192.168.2.0/24 added to the filter list.', t)
        t.write('-filter 192.168.2.0/24\n')
        self.expect('192.168.2.0/24 removed from the filter list.', t)

        self.close(t)'''


class GatewayTest(Test):
    def test_gateway(self):
        t = self.connect_as_admin()
        t.write('+gateway foobar\n')
        self.expect('Invalid gateway IP.', t)

        t.write('+gateway 127.0.0.1\n')
        self.expect('127.0.0.1 added to the gateway list.', t)

        t.write('+gateway 127.0.0.1\n')
        self.expect('127.0.0.1 is already on the gateway list.', t)

        t.write('-gateway 127.0.0.1\n')
        self.expect('127.0.0.1 removed from the gateway list.', t)

        t.write('-gateway 127.0.0.1\n')
        self.expect('127.0.0.1 is not on the gateway list.', t)

        t.write('+gateway 127.0.0.1\n')
        self.expect('127.0.0.1 added to the gateway list.', t)

        t2 = self.connect()
        t2.write('%i192.168.0.1\n')
        t2.write('GuestLocal\n')
        self.expect('is not a registered name', t2)
        t2.write('\n')
        self.expect('fics%', t2)

        t.write('f guestlocal\n')
        self.expect_re('Host: +192.168.0.1', t)

        self.close(t2)

        t.write('-gateway 127.0.0.1\n')
        self.expect('127.0.0.1 removed from the gateway list.', t)

        t2 = self.connect()
        t2.write('%i192.168.0.1\n')
        t2.write('GuestLocal\n')
        self.expect('is not a registered name', t2)
        t2.write('\n')
        self.expect('fics%', t2)

        t.write('f guestlocal\n')
        self.expect_re('Host: +127.0.0.1', t)

        self.close(t)
        self.close(t2)

class MuzzleTest(Test):
    @with_player('TestPlayer')
    def test_muzzle(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+muzzle testplayer\n')
        self.expect('TestPlayer added to the muzzle list.', t)
        self.expect('admin has added you to the muzzle list.', t2)
        t.write('+muzzle testplayer\n')
        self.expect('TestPlayer is already on the muzzle list.', t)
        t2.write('shout test\n')
        self.expect('You are muzzled.', t2)
        t2.write('it test\n')
        self.expect('You are muzzled.', t2)
        t2.close()

        t.write('=muzzle\n')
        self.expect('-- muzzle list: 1 name --\r\nTestPlayer\r\n', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Muzzled', t)

        t2 = self.connect_as('TestPlayer')
        t2.write('shout test\n')
        self.expect('You are muzzled.', t2)
        t.write('-muzzle testplayer\n')
        self.expect('TestPlayer removed from the muzzle list.', t)
        self.expect('admin has removed you from the muzzle list.', t2)
        t2.write('shout test\n')
        self.expect('TestPlayer shouts: test', t)
        self.expect('TestPlayer shouts: test', t2)

        t.write('-muzzle testplayer\n')
        self.expect('TestPlayer is not on the muzzle list.', t)

        t.write('showcomment testplayer\n')
        # the order of the comments is undefined since
        # they were added less than 1 second apart
        self.expect('Removed from the muzzle list.', t)

        t2.write('+muzzle admin\n')
        self.expect('"muzzle" does not match any list name', t2)
        t2.write('=muzzle\n')
        self.expect('"muzzle" does not match any list name', t2)

        self.close(t)
        self.close(t2)

    def test_muzzle_bad(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')
        t.write('+muzzle nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+muzzle admin\n')
        self.expect('Admins cannot be muzzled.', t)
        t.write('+muzzle guestabcd\n')
        self.expect('Only registered players can be muzzled.', t)
        self.close(t)
        self.close(t2)


class LoginQuitTest(Test):
    def test_login_invalid_command(self):
        t = self.connect()
        self.expect('login: ', t)
        t.write('%a\n')
        self.expect('login: ', t)
        t.close()

    def test_login_quit(self):
        t = self.connect()
        self.expect('login: ', t)
        t.write('%q\n')
        self.expect_EOF(t)


class CmuzzleTest(Test):
    @with_player('TestPlayer')
    def test_cmuzzle(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+cmuzzle testplayer\n')
        self.expect('TestPlayer added to the cmuzzle list.', t)
        self.expect('admin has added you to the cmuzzle list.', t2)
        t.write('+cmuzzle testplayer\n')
        self.expect('TestPlayer is already on the cmuzzle list.', t)
        t2.write('cshout test\n')
        self.expect('You are c-muzzled.', t2)
        t2.close()

        t.write('=cmuzzle\n')
        self.expect('-- cmuzzle list: 1 name --\r\nTestPlayer\r\n', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: C-muzzled', t)

        t2 = self.connect_as('TestPlayer')
        t2.write('cshout test\n')
        self.expect('You are c-muzzled.', t2)
        t.write('-cmuzzle testplayer\n')
        self.expect('TestPlayer removed from the cmuzzle list.', t)
        self.expect('admin has removed you from the cmuzzle list.', t2)
        t2.write('cshout test\n')
        self.expect('TestPlayer c-shouts: test', t)
        self.expect('TestPlayer c-shouts: test', t2)

        t.write('-cmuzzle testplayer\n')
        self.expect('TestPlayer is not on the cmuzzle list.', t)

        t.write('showcomment testplayer\n')
        self.expect('Removed from the cmuzzle list.', t)

        t2.write('+cmuzzle admin\n')
        self.expect('"cmuzzle" does not match any list name', t2)

        self.close(t)
        self.close(t2)

    def test_cmuzzle_bad(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')
        t.write('+cmuzzle nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+cmuzzle admin\n')
        self.expect('Admins cannot be c-muzzled.', t)
        t.write('+cmuzzle guestabcd\n')
        self.expect('Only registered players can be c-muzzled.', t)
        t.write('-cmuzzle guestabcd\n')
        self.expect('Only registered players can be c-muzzled.', t)
        self.close(t)
        self.close(t2)

class MuteTest(Test):
    @with_player('TestPlayer')
    def test_mute(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+mute testplayer\n')
        self.expect('TestPlayer added to the mute list.', t)
        self.expect('admin has added you to the mute list.', t2)
        t.write('+mute testplayer\n')
        self.expect('TestPlayer is already on the mute list.', t)

        t2.write('t 1 test\n')
        self.expect('You are muted.', t2)
        t2.write('t testplayer test\n')
        self.expect('You are muted.', t2)
        t2.write('shout test\n')
        self.expect('You are muted.', t2)
        t2.write('mess testplayer test\n')
        self.expect('You are muted.', t2)

        t2.close()

        t.write('=mute\n')
        self.expect('-- mute list: 1 name --\r\nTestPlayer\r\n', t)

        t.write('showcomment testplayer\n')
        self.expect_re('1. admin at .*: Muted', t)

        t2 = self.connect_as('TestPlayer')
        t2.write('t 1 test\n')
        self.expect('You are muted.', t2)
        t.write('-mute testplayer\n')
        self.expect('TestPlayer removed from the mute list.', t)
        self.expect('admin has removed you from the mute list.', t2)

        t2 = self.connect_as('testplayer')

        t.write('-mute testplayer\n')
        self.expect('TestPlayer is not on the mute list.', t)

        t2.write('+mute admin\n')
        self.expect('"mute" does not match any list name', t2)
        t2.write('=mute\n')
        self.expect('"mute" does not match any list name', t2)

        self.close(t)
        self.close(t2)

    def test_mute_guest(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')

        t.write('+mute GuestABCD\n')
        self.expect('GuestABCD added to the mute list.', t)
        self.expect('admin has added you to the mute list.', t2)
        t2.write('t 4 test\n')
        # try tell to self, but could be any non-admin
        self.expect('You are muted.', t2)
        t2.write('t guestabcd test\n')
        self.expect('You are muted.', t2)

        t.write('=mute\n')
        self.expect('-- mute list: 1 name --', t)
        self.expect('GuestABCD', t)

        t.write('-mute guestabcd\n')
        self.expect('GuestABCD removed from the mute list.', t)
        self.expect('admin has removed you from the mute list.', t2)

        self.close(t)
        self.close(t2)

    def test_mute_bad(self):
        t = self.connect_as_admin()
        t.write('+mute nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+mute admin\n')
        self.expect('Admins cannot be muted.', t)
        self.close(t)

class TestPlayban(Test):
    def test_playban_guest(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')

        t.write('+playban guestabcd\n')
        self.expect('GuestABCD added to the playban list.', t)
        self.expect('admin has added you to the playban list.', t2)
        t.write('+playban guestabcd\n')
        self.expect('GuestABCD is already on the playban list.', t)

        t.write('=playban\n')
        self.expect('-- playban list: 1 name --\r\nGuestABCD', t)

        t2.write('see 3+0\n')
        self.expect('You may not play games.', t2)
        t2.write('match admin 5+0\n')
        self.expect('You may not play games.', t2)

        t.write('match guestabcd\n')
        self.expect('GuestABCD may not play games.', t)

        t.write('see 1+0 u\n')
        m = self.expect_re(r'Your seek has been posted with index (\d+)\.', t)
        n = int(m.group(1))
        t2.write('play %d\n' % n)
        self.expect('You may not play games.', t2)

        t.write('-playban guestabcd\n')
        self.expect('GuestABCD removed from the playban list.', t)
        self.expect('admin has removed you from the playban list.', t2)
        t.write('-playban guestabcd\n')
        self.expect('GuestABCD is not on the playban list.', t)
        t2.write('=playban\n')
        self.expect('"playban" does not match any list name', t2)
        t2.write('match admin 1+0\n')
        self.expect('Issuing:', t2)

        self.close(t)
        self.close(t2)

    @with_player('TestPlayer')
    def test_playban(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+playban testplayer\n')
        self.expect('TestPlayer added to the playban list.', t)
        self.expect('admin has added you to the playban list.', t2)
        t.write('+playban testplayer\n')
        self.expect('TestPlayer is already on the playban list.', t)
        self.close(t2)

        t.write('=playban\n')
        self.expect('-- playban list: 1 name --\r\nTestPlayer', t)

        t2 = self.connect_as('TestPlayer')
        t2.write('see 3+0\n')
        self.expect('You may not play games.', t2)
        t2.write('match admin 5+0\n')
        self.expect('You may not play games.', t2)

        t.write('match TestPlayer\n')
        self.expect('TestPlayer may not play games.', t)

        t.write('see 1+0\n')
        m = self.expect_re(r'Your seek has been posted with index (\d+)\.', t)
        n = int(m.group(1))
        t2.write('play %d\n' % n)
        self.expect('You may not play games.', t2)

        t.write('-playban TestPlayer\n')
        self.expect('TestPlayer removed from the playban list.', t)
        self.expect('admin has removed you from the playban list.', t2)
        t.write('-playban TestPlayer\n')
        self.expect('TestPlayer is not on the playban list.', t)
        t2.write('=ratedban\n')
        self.expect('"ratedban" does not match any list name', t2)
        t2.write('see 3+0\n')
        self.expect_re(r'Your seek has been posted with index (\d+)\.', t2)

        self.close(t)
        self.close(t2)

    def test_playban_bad(self):
        t = self.connect_as_admin()
        t.write('+playban nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+playban admin\n')
        self.expect('Admins cannot be playbanned.', t)
        self.close(t)

class TestRatedban(Test):
    @with_player('TestPlayer')
    def test_ratedban(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t.write('+ratedban testplayer\n')
        self.expect('TestPlayer added to the ratedban list.', t)
        self.expect('admin has added you to the ratedban list.', t2)
        t.write('+ratedban testplayer\n')
        self.expect('TestPlayer is already on the ratedban list.', t)
        self.close(t2)

        t.write('=ratedban\n')
        self.expect('-- ratedban list: 1 name --\r\nTestPlayer', t)

        t2 = self.connect_as('TestPlayer')
        t2.write('see 3+0\n')
        self.expect('You may not play rated games.', t2)
        t2.write('match admin 5+0\n')
        self.expect('You may not play rated games.', t2)
        t2.write('see 3+0 u\n')
        self.expect('Your seek has been posted', t2)
        t2.write('match admin 5+0 u\n')
        self.expect('Issuing:', t2)

        t.write('match TestPlayer\n')
        self.expect('TestPlayer may not play rated games.', t)

        t.write('see 1+0\n')
        m = self.expect_re(r'Your seek has been posted with index (\d+)\.', t)
        n = int(m.group(1))
        t2.write('play %d\n' % n)
        self.expect('You may not play rated games.', t2)

        t.write('-ratedban TestPlayer\n')
        self.expect('TestPlayer removed from the ratedban list.', t)
        self.expect('admin has removed you from the ratedban list.', t2)
        t.write('-ratedban TestPlayer\n')
        self.expect('TestPlayer is not on the ratedban list.', t)
        t2.write('=ratedban\n')
        self.expect('"ratedban" does not match any list name', t2)

        t.write('showcomment TestPlayer\n')
        self.expect('Removed from the ratedbanned list.', t)

        self.close(t)
        self.close(t2)

    def test_ratedban_bad(self):
        t = self.connect_as_admin()
        t.write('+ratedban nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+ratedban admin\n')
        self.expect('Admins cannot be ratedbanned.', t)

        t2 = self.connect_as_guest('GuestABCD')
        t.write('+ratedban guestabcd\n')
        self.expect('Only registered players can be ratedbanned.', t)
        self.close(t2)

        self.close(t)

class TestNoteban(Test):
    @with_player('TestPlayer')
    def test_noteban(self):
        t = self.connect_as_admin()
        t2 = self.connect_as('TestPlayer')

        t2.write('set 1 Some abusive note\n')
        self.expect("Note 1 set: Some abusive note", t2)

        t.write('+noteban testplayer\n')
        self.expect('TestPlayer added to the noteban list.', t)
        self.expect('admin has added you to the noteban list.', t2)
        t.write('+noteban testplayer\n')
        self.expect('TestPlayer is already on the noteban list.', t)
        self.close(t2)

        t.write('=noteban\n')
        self.expect('-- noteban list: 1 name --\r\nTestPlayer', t)

        t2 = self.connect_as('TestPlayer')
        t3 = self.connect_as_guest()
        t3.write('f TestPlayer!\n')
        self.expect_not('1: Some abusive note', t3)

        # can still read own notes
        t2.write('f TestPlayer!\n')
        self.expect('1: Some abusive note', t2)

        t.write('-noteban TestPlayer\n')
        self.expect('TestPlayer removed from the noteban list.', t)
        self.expect('admin has removed you from the noteban list.', t2)
        t.write('-noteban TestPlayer\n')
        self.expect('TestPlayer is not on the noteban list.', t)
        t2.write('=noteban\n')
        self.expect('"noteban" does not match any list name', t2)

        t3.write('f TestPlayer!\n')
        self.expect('1: Some abusive note', t3)

        t.write('showcomment TestPlayer\n')
        self.expect('Removed from the noteban list.', t)

        self.close(t)
        self.close(t2)
        self.close(t3)

    def test_noteban_bad(self):
        t = self.connect_as_admin()
        t.write('+noteban nosuchplayer\n')
        self.expect('no player matching the name "nosuchplayer"', t)
        t.write('+noteban admin\n')
        self.expect('Admins cannot be notebanned.', t)

        t2 = self.connect_as_guest('GuestABCD')
        t.write('+noteban guestabcd\n')
        self.expect('Only registered players can be notebanned.', t)
        self.close(t2)

        self.close(t)

class TestLight(Test):
    def test_admin_light(self):
        t = self.connect_as_admin()
        t.write('admin\n')
        self.expect("Admin mode (*) is now not shown.", t)
        t.write('admin\n')
        self.expect("Admin mode (*) is now shown.", t)
        self.close(t)

class AreloadTest(Test):
    def test_areload(self):
        self._skip('not stable')
        t = self.connect_as_admin()
        t.write('areload\n')
        self.expect('reloaded online', t, timeout=10)
        self.close(t)

class ShutdownTest(Test):
    def test_shutdown(self):
        t = self.connect_as_admin()
        t.write('shutdown -1\n')
        self.expect('nvalid shutdown time', t)
        t.write('shutdown 1\n')
        self.expect('The server is shutting down in 1 minute, initiated by admin', t)
        t.write('shutdown\n')
        self.expect('shutdown canceled by admin', t)
        t.write('shutdown 2\n')
        self.expect('The server is shutting down in 2 minutes, initiated by admin', t)
        t.write('shutdown\n')
        self.expect('shutdown canceled by admin', t)
        self.close(t)

    def test_shutdown_for_real(self):
        self._skip('prevents other tests')
        t = self.connect_as_admin()
        t.write('shutdown 0\n')
        self.expect('The server is shutting down in 0 minutes, initiated by admin', t)
        self.expect_EOF(t)

class FtellTest(Test):
    @with_player('TestAdmin')
    def test_ftell(self):
        t = self.connect_as_admin()
        t2 = self.connect_as_guest('GuestABCD')
        t3 = self.connect_as_guest('GuestEFGH')

        t.write('asetadmin testadmin 100\n')
        self.expect('Admin level of TestAdmin set', t)
        t4 = self.connect_as('TestAdmin')

        self.set_nowrap(t)
        self.set_nowrap(t4)

        t.write("+ch 0\n")
        self.expect('[0] added', t)
        t4.write("+ch 0\n")
        self.expect('[0] added', t4)

        t.write('ftell\n')
        self.expect('You were not forwarding a conversation.', t)

        t.write('ftell doesnotexist\n')
        self.expect('No player named "doesnotexist" is online', t)

        t.write('ftell admin\n')
        self.expect('talking to yourself', t)

        t.write('ftell guestabcd\n')
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestABCD* and myself', t)
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestABCD* and myself', t4)

        t.write('t guestabcd Hello there.\n')
        self.expect('Fwd tell: admin told GuestABCD: Hello there.', t4)
        self.expect_not('Fwd tell:', t)

        t2.write('t admin Hello yourself.\n')
        self.expect('Fwd tell: GuestABCD told admin: Hello yourself.', t4)
        self.expect_not('Fwd tell:', t)

        t.write('ftell\n')
        self.expect('Stopping the forwarding of the conversation with GuestABCD.', t)
        self.expect('admin(*)(0): I will no longer be forwarding the conversation between *GuestABCD* and myself.', t)
        self.expect('admin(*)(0): I will no longer be forwarding the conversation between *GuestABCD* and myself.', t4)

        t.write('ftell guestabcd\n')
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestABCD* and myself', t)
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestABCD* and myself', t4)
        t.write('ftell guestefgh\n')
        self.expect('admin(*)(0): I will no longer be forwarding the conversation between *GuestABCD* and myself.', t)
        self.expect('admin(*)(0): I will no longer be forwarding the conversation between *GuestABCD* and myself.', t4)
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestEFGH* and myself', t)
        self.expect('admin(*)(0): I will be forwarding the conversation between *GuestEFGH* and myself', t4)

        t.write("-ch 0\n")
        self.expect('[0] removed', t)
        t4.write("-ch 0\n")
        self.expect('[0] removed', t4)

        self.close(t)
        self.close(t2)
        self.close(t3)
        self.close(t4)

    @with_player('TestAdmin')
    def test_ftell_logout(self):
        t = self.connect_as_admin()
        t.write('+ch 0\n')
        t.write('asetadmin testadmin 100\n')
        self.expect('Admin level of TestAdmin set', t)

        t2 = self.connect_as('TestAdmin')
        t3 = self.connect_as_guest('GuestABCD')

        self.set_nowrap(t)
        self.set_nowrap(t2)

        t2.write('+ch 0\n')
        t2.write('ftell guestabcd\n')
        self.expect('TestAdmin(0): I will be forwarding the conversation between *GuestABCD*', t)
        self.expect('TestAdmin(0): I will be forwarding the conversation between *GuestABCD*', t2)
        t2.write('quit\n')
        self.expect('TestAdmin(0): I am logging out now - conversation forwarding stopped.', t)
        self.expect_EOF(t2)

        t2 = self.connect_as('TestAdmin')
        t2.write('ftell guestabcd\n')
        self.expect('TestAdmin(0): I will be forwarding the conversation between *GuestABCD* and myself', t)
        t3.close()
        self.expect('TestAdmin(0): *GuestABCD* has logged out - conversation forwarding stopped.', t)
        self.expect('TestAdmin(0): *GuestABCD* has logged out - conversation forwarding stopped.', t2)
        self.expect('GuestABCD, whose tells you were forwarding, has logged out.', t2)

        t.write('-ch 0\n')
        self.expect('[0] removed', t)

        self.close(t2)
        self.close(t)

class ChkipTest(Test):
    def test_chkip(self):
        t = self.connect_as_admin()

        t.write('chkip\n')
        self.expect('Usage:', t)
        t.write('chkip doesnotexist\n')
        self.expect('No player named "doesnotexist" is online', t)
        t.write('chkip admin\n')
        self.expect_re('admin +%s' % LOCAL_IP, t)
        t.write('chkip %s\n' % LOCAL_IP)
        self.expect_re('admin +%s' % LOCAL_IP, t)
        t.write('chkip %s*\n' % LOCAL_IP[0:5])
        self.expect_re('admin +%s' % LOCAL_IP, t)
        t.write('chkip 123.123.123.123\n')
        self.expect_not('admin', t)

        self.close(t)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
