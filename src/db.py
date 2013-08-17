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

from MySQLdb import connect, cursors, IntegrityError, OperationalError
import config

from twisted.internet import defer
from twisted.enterprise import adbapi


class DuplicateKeyError(Exception):
    pass


class DeleteError(Exception):
    pass


class UpdateError(Exception):
    pass

# pacify pyflakes
db = None
adb = None

if 1:
    def _init():
        global db
        db = connect(host=config.db_host, db=config.db_db,
            read_default_file="~/.my.cnf")
        db.autocommit(True) # XXX necessary to coexist with adbapi
        cursor = db.cursor()
        cursor = query(cursor, """SET time_zone='+00:00'""")
        db.set_character_set('utf8')
        cursor.close()

        def openfun(adbconn):
            cursor = adbconn.cursor()
            cursor.execute("""SET time_zone='+00:00'""")
            cursor.execute("""SET charset utf8""")
            cursor.close()
        global adb
        adb = adbapi.ConnectionPool("MySQLdb",
            host=config.db_host, db=config.db_db,
            read_default_file="~/.my.cnf", cursorclass=cursors.DictCursor,
            cp_reconnect=True, cp_min=1, cp_max=3, cp_openfun=openfun)

    def query(cursor, *args):
        try:
            cursor.execute(*args)
            return cursor
        except (AttributeError, OperationalError):
            # the connection may have timed out, so try again
            cursor.close()
            db.close()
            adb.close()
            _init()
            # the new cursor needs to be the same type as the old one
            cursor = db.cursor(cursor.__class__)
            cursor.execute(*args)
            return cursor

    def user_get_async(name):
        d = adb.runQuery("""SELECT
                user_id,user_name,user_passwd,user_first_login,user_last_logout,
                user_admin_level, user_email,user_real_name,user_banned,
                user_muzzled,user_cmuzzled,user_muted,user_notebanned,
                user_ratedbanned,user_playbanned,user_total_time_online
            FROM user WHERE user_name=%s""", (name,))
        def gotRows(rows):
            if rows:
                assert(len(rows) == 1)
                return rows[0]
            else:
                return None
        d.addCallback(gotRows)
        return d

    @defer.inlineCallbacks
    def user_get_vars(user_id, vnames):
        rows = yield adb.runQuery(("SELECT %s" % ','.join(vnames)) +
            " FROM user WHERE user_id=%s", (user_id,))
        defer.returnValue(rows[0])

    def user_set_var(user_id, name, val):
        up = """UPDATE user SET %s""" % name
        d = adb.runOperation(up + """=%s WHERE user_id=%s""",
            (val, user_id))
        return d

    def user_get_formula(user_id):
        return adb.runQuery("""SELECT num,f FROM formula WHERE user_id=%s ORDER BY num ASC""",
            (user_id,))

    def user_set_formula(user_id, name, val):
        # ON DUPLICATE KEY UPDATE is probably not very portable to
        # other databases, but this shouldn't be hard to rewrite
        dbkeys = {'formula': 0, 'f1': 1, 'f2': 2, 'f3': 3, 'f4': 4, 'f5': 5,
            'f6': 6, 'f7': 7, 'f8': 8, 'f9': 9}
        assert(name in dbkeys)
        num = dbkeys[name]
        if val is not None:
            d = adb.runQuery("""INSERT INTO formula SET user_id=%s,num=%s,f=%s ON DUPLICATE KEY UPDATE f=%s""",
                (user_id, num, val, val))
        else:
            # It is OK to not actually delete any rows; in that
            # case we are just unsetting an already unset variable.
            d = adb.runOperation("""DELETE FROM formula WHERE user_id=%s AND num=%s""",
                (user_id, num))
        return d

    # notes
    def user_get_notes(user_id):
        return adb.runQuery("""SELECT num,txt FROM note WHERE user_id=%s ORDER BY num ASC""", (user_id,))

    def user_set_note(user_id, name, val):
        num = int(name, 10)
        assert(num >= 1 and num <= 10)
        if val is not None:
            d = adb.runOperation("""INSERT INTO note SET user_id=%s,num=%s,txt=%s ON DUPLICATE KEY UPDATE txt=%s""",
                    (user_id, num, val, val,))
        else:
            def do_del(txn):
                txn.execute("""DELETE FROM note WHERE user_id=%s AND num=%s""",
                    (user_id, num))
                if txn.rowcount != 1:
                    raise DeleteError()
            d = adb.runInteraction(do_del)
        return d

    @defer.inlineCallbacks
    def user_insert_note(user_id, val):
        """Insert a new note as note 1."""
        assert(val is not None)
        yield adb.runOperation("""DELETE FROM note WHERE user_id=%s AND num=10""",
            (user_id))
        # We can't simply increment the note numbers, sincne that would
        # tempoarily violate the UNIQUE constraint. Instead, cleverly
        # use two statements.
        yield adb.runOperation("""UPDATE note SET num=num+10 WHERE user_id=%s""",
            (user_id))
        yield adb.runOperation("""UPDATE note SET num=num-9 WHERE user_id=%s""",
            (user_id))
        yield adb.runOperation("""INSERT INTO note SET user_id=%s,num=1,txt=%s""",
            (user_id, val))
        defer.returnValue(None)

    def user_set_alias(user_id, name, val):
        cursor = db.cursor()
        if val is not None:
            cursor = query(cursor, """INSERT INTO user_alias SET user_id=%s,name=%s,val=%s ON DUPLICATE KEY UPDATE val=%s""", (user_id, name, val, val))
        else:
            cursor = query(cursor, """DELETE FROM user_alias WHERE user_id=%s AND name=%s""", (user_id, name))
            if cursor.rowcount != 1:
                cursor.close()
                raise DeleteError()
        cursor.close()

    def user_get_aliases(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT name,val FROM user_alias WHERE user_id=%s ORDER BY name ASC""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    '''def user_get_aliases(user_id):
        return  adb.runQuery("""SELECT name,val FROM user_alias WHERE user_id=%s ORDER BY name ASC""", (user_id,))'''

    def user_get_matching(prefix, limit=8):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_id,user_name,user_passwd,
                user_first_login,user_last_logout,user_admin_level,
                user_email,user_real_name,
                user_banned,user_muzzled,user_cmuzzled,user_muted,
                user_notebanned,user_ratedbanned,user_playbanned,
                user_total_time_online
            FROM user WHERE user_name LIKE %s""" + " LIMIT %s" % limit,
                (prefix + '%',))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_get_by_prefix(prefix, limit=8):
        d = adb.runQuery("""SELECT user_id,user_name,user_passwd,
                user_first_login,user_last_logout,user_admin_level,
                user_email,user_real_name,
                user_banned,user_muzzled,user_cmuzzled,user_muted,
                user_notebanned,user_ratedbanned,user_playbanned,
                user_total_time_online
            FROM user WHERE user_name LIKE %s LIMIT %s""",
                (prefix + '%', limit))
        return d

    @defer.inlineCallbacks
    def user_add(name, email, passwd, real_name, admin_level):
        def do_insert(txn):
            txn.execute("""INSERT INTO user
                SET user_name=%s,user_email=%s,user_passwd=%s,
                    user_real_name=%s,user_admin_level=%s""",
                (name, email, passwd, real_name, admin_level))
            return txn.lastrowid
        user_id = yield adb.runInteraction(do_insert)
        assert(user_id > 0)
        defer.returnValue(user_id)

    def user_set_passwd(uid, passwd):
        d = adb.runOperation("""UPDATE user SET user_passwd=%s
            WHERE user_id=%s""", (passwd, uid))
        return d

    def user_set_admin_level(uid, level):
        return adb.runOperation("""UPDATE user
            SET user_admin_level=%s WHERE user_id=%s""", (str(level), uid))

    def user_set_first_login(uid):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user
            SET user_first_login=NOW() WHERE user_id=%s""", (uid,))
        cursor.close()

    def user_get_first_login(uid):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_first_login
            FROM user WHERE user_id=%s""", (uid,))
        ret = cursor.fetchone()[0]
        cursor.close()
        return ret

    def user_set_last_logout(uid):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user
            SET user_last_logout=NOW() WHERE user_id=%s""", (uid,))
        cursor.close()

    def user_add_to_total_time_online(uid, secs):
        """ Expects secs to be an integer. """
        assert(secs >= 0)
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user
            SET user_total_time_online=user_total_time_online+%s WHERE user_id=%s""", (secs, uid))
        cursor.close()

    def user_log(user_name, login, ip):
        cursor = db.cursor()

        # delete old log entry, if necessary
        cursor = query(cursor, """SELECT COUNT(*) FROM user_log
            WHERE log_who_name=%s""", (user_name,))
        count = cursor.fetchone()[0]
        if count >= 10:
            assert(count == 10)
            cursor = query(cursor, """DELETE FROM user_log
                WHERE log_who_name=%s ORDER BY log_when DESC LIMIT 1""",
                    (user_name,))
        cursor.close()
        cursor = db.cursor()

        which = 'login' if login else 'logout'
        cursor = query(cursor, """INSERT INTO user_log
            SET log_who_name=%s,log_which=%s,log_ip=%s,log_when=NOW()""",
                (user_name, which, ip))

        cursor.close()

    def user_get_log(user_name):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT log_who_name,log_when,
                log_which,log_ip
            FROM user_log
            WHERE log_who_name=%s
            ORDER BY log_when DESC""", (user_name,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_log_all(limit):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT log_who_name,log_when,
                log_which,log_ip
            FROM user_log
            ORDER BY log_when DESC
            LIMIT %s""", (limit,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_muted_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_muted=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    def user_set_banned(uid, val):
        assert(val in [0, 1])
        d = adb.runOperation("""UPDATE user
            SET user_banned=%s WHERE user_id=%s""", (val, uid))
        return d

    def get_banned_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_banned=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def user_set_muzzled(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_muzzled=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    def get_muzzled_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_muzzled=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def user_set_cmuzzled(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_cmuzzled=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    def get_cmuzzled_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_cmuzzled=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def user_set_muted(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_muted=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    @defer.inlineCallbacks
    def user_set_notebanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_notebanned=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    def get_notebanned_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_notebanned=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def user_set_ratedbanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_ratedbanned=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    def get_ratedbanned_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_ratedbanned=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def user_set_playbanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_playbanned=%s WHERE user_id=%s""", (val, uid))
        defer.returnValue(None)

    def get_playbanned_user_names():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user
            WHERE user_playbanned=1 LIMIT 500""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    def user_delete(uid):
        """ Permanently delete a user from the database.  In normal use
        this shouldn't be used, but it's useful for testing. """
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM user_log WHERE log_who_name=(SELECT user_name FROM user WHERE user_id=%s)""", (uid,))
        cursor = query(cursor, """DELETE FROM user WHERE user_id=%s""", (uid,))
        if cursor.rowcount != 1:
            cursor.close()
            raise DeleteError()
        cursor = query(cursor, """DELETE FROM user_comment WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM user_title WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM user_notify
            WHERE %s IN (notifier, notified)""", (uid))
        cursor = query(cursor, """DELETE FROM user_gnotify
            WHERE %s IN (gnotifier, gnotified)""", (uid))
        cursor = query(cursor, """DELETE FROM censor WHERE %s IN (censorer, censored)""", (uid))
        cursor = query(cursor, """DELETE FROM noplay WHERE %s IN (noplayer, noplayed)""", (uid))
        cursor = query(cursor, """DELETE FROM formula WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM note WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM channel_user WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM channel_owner WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM history WHERE user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM rating WHERE user_id=%s""", (id,))
        cursor = query(cursor, """DELETE FROM message WHERE to_user_id=%s""", (uid,))
        cursor = query(cursor, """DELETE FROM adjourned_game WHERE %s IN (white_user_id, black_user_id)""", (uid))
        cursor.close()

    # filtered ips
    def get_filtered_ips():
        cursor = db.cursor()
        cursor = query(cursor, """SELECT filter_pattern FROM ip_filter LIMIT 8192""")
        ret = [r[0] for r in cursor.fetchall()]
        cursor.close()
        return ret

    @defer.inlineCallbacks
    def add_filtered_ip(filter_pattern):
        yield adb.runOperation("""INSERT INTO ip_filter SET filter_pattern=%s""",
            (filter_pattern,))

    def del_filtered_ip(filter_pattern):
        def do_del(txn):
            txn.execute("""DELETE FROM ip_filter WHERE filter_pattern=%s""",
                (filter_pattern,))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    # comments
    @defer.inlineCallbacks
    def add_comment_async(admin_id, user_id, txt):
        yield adb.runOperation("""INSERT INTO user_comment
            SET admin_id=%s,user_id=%s,when_added=NOW(),txt=%s""",
                (admin_id, user_id, txt))
        defer.returnValue(None)

    @defer.inlineCallbacks
    def get_comments(user_id):
        rows = yield adb.runQuery("""
            SELECT user_name AS admin_name,when_added,txt FROM user_comment
                LEFT JOIN user ON (user.user_id=user_comment.admin_id)
                WHERE user_comment.user_id=%s
                ORDER BY when_added DESC""", (user_id,))
        defer.returnValue(rows)

    # channels
    def user_get_channels(id):
        cursor = db.cursor() #cursors.DictCursor)
        cursor = query(cursor, """SELECT channel_id FROM channel_user
            WHERE user_id=%s""", (id,))
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]

    def channel_new(chid, name):
        cursor = db.cursor()
        if name is not None:
            cursor = query(cursor, """INSERT INTO channel SET channel_id=%s,name=%s""", (chid, name,))
        else:
            cursor = query(cursor, """INSERT INTO channel SET channel_id=%s""", (chid,))
        cursor.close()

    def channel_add_user(chid, user_id):
        cursor = db.cursor()
        cursor = query(cursor, """INSERT INTO channel_user
            SET user_id=%s,channel_id=%s""", (user_id, chid))
        cursor.close()

    def channel_set_topic(args):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE channel
            SET topic=%(topic)s,topic_who=%(topic_who)s,
                topic_when=%(topic_when)s
            WHERE channel_id=%(channel_id)s""", args)
        assert(cursor.rowcount == 1)
        cursor.close()

    def channel_del_topic(chid):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE channel SET topic=NULL
            WHERE channel_id=%s""", chid)
        assert(cursor.rowcount == 1)
        cursor.close()

    def channel_del_user(ch_id, user_id):
        def do_del(txn):
            txn.execute("""DELETE FROM channel_user
                WHERE user_id=%s AND channel_id=%s""", (user_id, ch_id))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def channel_list():
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT channel_id,name,descr,
            topic,user_name AS topic_who_name,topic_when
            FROM channel LEFT JOIN user ON(channel.topic_who=user.user_id)""")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    '''def channel_get_members(id):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM channel_user
            LEFT JOIN user USING (user_id)
            WHERE channel_id=%s""", (id,))
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]'''

    def user_in_channel(user_id, chid):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT 1 FROM channel_user
            WHERE channel_id=%s AND user_id=%s LIMIT 1""", (chid, user_id))
        row = cursor.fetchone()
        cursor.close()
        return bool(row)

    @defer.inlineCallbacks
    def channel_user_count(chid):
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c FROM channel_user
            WHERE channel_id=%s""", (chid,))
        defer.returnValue(rows[0]['c'])

    def channel_is_owner(chid, user_id):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT 1 FROM channel_owner
            WHERE channel_id=%s AND user_id=%s LIMIT 1""", (chid, user_id))
        row = cursor.fetchone()
        cursor.close()
        return bool(row)

    @defer.inlineCallbacks
    def channel_add_owner(chid, user_id):
        yield adb.runQuery("""INSERT INTO channel_owner
            SET channel_id=%s,user_id=%s""", (chid, user_id))
        defer.returnValue(None)

    def channel_del_owner(chid, user_id):
        def do_del(txn):
            txn.execute("""DELETE FROM channel_owner
            WHERE channel_id=%s AND user_id=%s""", (chid, user_id))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    @defer.inlineCallbacks
    def user_channels_owned(user_id):
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c FROM channel_owner
            WHERE user_id=%s""", (user_id,))
        defer.returnValue(rows[0]['c'])

    @defer.inlineCallbacks
    def user_add_title(user_id, title_id):
        try:
            yield adb.runOperation("""INSERT INTO user_title SET user_id=%s,title_id=%s""",
                (user_id, title_id))
        except IntegrityError:
            raise DuplicateKeyError()
        defer.returnValue(None)

    def user_del_title(user_id, title_id):
        def do_del(txn):
            txn.execute("""DELETE FROM user_title WHERE user_id=%s AND title_id=%s""",
            (user_id, title_id))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_titles(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT title_name,title_flag,title_light FROM user_title LEFT JOIN title USING (title_id) WHERE user_id=%s ORDER BY title_id ASC""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def toggle_title_light(user_id, title_id):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user_title
            SET title_light=NOT title_light
            WHERE title_id=%s AND user_id=%s""", (title_id, user_id))
        cursor.close()

    # notifications
    @defer.inlineCallbacks
    def user_add_notification(notified, notifier):
        try:
            yield adb.runOperation("""INSERT INTO user_notify SET notified=%s,notifier=%s""",
                (notified, notifier))
        except IntegrityError:
            raise DuplicateKeyError()
        defer.returnValue(None)

    def user_del_notification(notified, notifier):
        def do_del(txn):
            txn.execute("""DELETE FROM user_notify WHERE notified=%s AND notifier=%s""",
            (notified, notifier))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_notified(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notified) WHERE notifier=%s""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_get_notifiers(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notifier) WHERE notified=%s""", (user_id,))
        rows = cursor.fetchall()
        return rows

    '''
    def user_get_notified(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notified) WHERE notifier=%s""",
            (user_id,))

    def user_get_notifiers(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notifier) WHERE notified=%s""",
            (user_id,))'''

    # game notifications
    @defer.inlineCallbacks
    def user_add_gnotification(gnotified, gnotifier):
        try:
            yield adb.runOperation("""INSERT INTO user_gnotify
                SET gnotified=%s,gnotifier=%s""", (gnotified, gnotifier))
        except IntegrityError:
            raise DuplicateKeyError()
        defer.returnValue(None)

    def user_del_gnotification(notified, notifier):
        def do_del(txn):
            txn.execute("""DELETE FROM user_gnotify
                WHERE gnotified=%s AND gnotifier=%s""", (notified, notifier))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_gnotified(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user
            LEFT JOIN user_gnotify ON (user.user_id=user_gnotify.gnotified)
            WHERE gnotifier=%s""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_get_gnotifiers(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user
            LEFT JOIN user_gnotify ON (user.user_id=user_gnotify.gnotifier)
            WHERE gnotified=%s""", (user_id,))
        rows = cursor.fetchall()
        return rows

    # censor
    #@defer.inlineCallbacks
    def user_add_censor(censorer, censored):
        try:
            d = adb.runOperation("""INSERT INTO censor SET censored=%s,censorer=%s""",
                (censored, censorer))
        except IntegrityError:
            raise DuplicateKeyError()
        return d
        #defer.returnValue(None)

    def user_del_censor(censorer, censored):
        def do_del(txn):
            txn.execute("""DELETE FROM censor WHERE censored=%s AND censorer=%s""",
                (censored, censorer))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    @defer.inlineCallbacks
    def user_get_censored_async(user_id):
        rows = yield adb.runQuery("""SELECT user_name FROM user LEFT JOIN censor ON (user.user_id=censor.censored) WHERE censorer=%s""", (user_id,))
        defer.returnValue(rows)

    def user_get_censored(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user LEFT JOIN censor ON (user.user_id=censor.censored) WHERE censorer=%s""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    # noplay
    @defer.inlineCallbacks
    def user_add_noplay(noplayer, noplayed):
        try:
            yield adb.runOperation("""INSERT INTO noplay SET noplayed=%s,noplayer=%s""", (noplayed, noplayer))
        except IntegrityError:
            raise DuplicateKeyError()
        defer.returnValue(None)

    def user_del_noplay(noplayer, noplayed):
        def do_del(txn):
            txn.execute("""DELETE FROM noplay WHERE noplayed=%s AND noplayer=%s""",
            (noplayed, noplayer))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_noplayed(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT user_name FROM user LEFT JOIN noplay ON (user.user_id=noplay.noplayed) WHERE noplayer=%s""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def title_get_all():
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT title_id,title_name,title_descr,title_flag,title_public FROM title""")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def title_get_users(title_id):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT user_name FROM user LEFT JOIN user_title USING(user_id) WHERE title_id=%s""", (title_id,))
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]

    # eco
    def get_eco(hash):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT eco,long_ FROM eco WHERE hash=%s""", (hash,))
        row = cursor.fetchone()
        cursor.close()
        return row

    def get_nic(hash):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT nic FROM nic WHERE hash=%s""", (hash,))
        row = cursor.fetchone()
        cursor.close()
        return row

    def look_up_eco(eco):
        if len(eco) == 3:
            # match all subvariations
            eco = '%s%%' % eco
        d = adb.runQuery("""SELECT eco,nic,long_,eco.fen AS fen FROM eco LEFT JOIN nic USING(hash) WHERE eco LIKE %s LIMIT 100""", (eco,))
        return d

    def look_up_nic(nic):
        d = adb.runQuery("""SELECT eco,nic,long_,nic.fen AS fen FROM nic LEFT JOIN eco USING(hash) WHERE nic = %s LIMIT 100""", (nic,))
        return d

    # game
    def game_add(white_name, white_rating, black_name, black_rating,
            eco, variant_id, speed_id, time, inc, rated, result, result_reason,
            ply_count, movetext, when_started, when_ended):
        cursor = db.cursor()
        cursor = query(cursor, """INSERT INTO game SET white_name=%s,white_rating=%s,black_name=%s,black_rating=%s,eco=%s,variant_id=%s,speed_id=%s,time=%s,inc=%s,rated=%s,result=%s,result_reason=%s,ply_count=%s,movetext=%s,when_started=%s,when_ended=%s""", (white_name,
            white_rating, black_name, black_rating, eco, variant_id,
            speed_id, time, inc, rated, result, result_reason, ply_count,
            movetext, when_started, when_ended))
        game_id = cursor.lastrowid
        cursor.close()
        return game_id

    # adjourned games
    def adjourned_game_add(g):
        cursor = db.cursor()
        cursor = query(cursor, """INSERT INTO adjourned_game
            SET white_user_id=%(white_user_id)s,
                white_clock=%(white_clock)s,
                black_user_id=%(black_user_id)s,
                black_clock=%(black_clock)s,
                eco=%(eco)s,variant_id=%(variant_id)s,speed_id=%(speed_id)s,
                time=%(time)s,inc=%(inc)s,rated=%(rated)s,
                adjourn_reason=%(adjourn_reason)s,ply_count=%(ply_count)s,
                movetext=%(movetext)s,when_started=%(when_started)s,
                when_adjourned=%(when_adjourned)s""", g)
        adjourn_id = cursor.lastrowid
        cursor.close()
        return adjourn_id

    def get_adjourned(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT adjourn_id,white_user_id,black_user_id,
                white.user_name as white_name, black.user_name as black_name
            FROM adjourned_game
                LEFT JOIN user AS white
                    ON (white.user_id = white_user_id)
                LEFT JOIN user AS black
                    ON (black.user_id = black_user_id)
            WHERE white_user_id=%s or black_user_id=%s""",
            (user_id, user_id))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_adjourned_between(id1, id2):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT adjourn_id,white_user_id,
                white_clock,black_user_id,black_clock,
                eco,speed_name,variant_name,
                clock_name,time,inc,rated,adjourn_reason,ply_count,movetext,
                when_started,when_adjourned,idn,overtime_move_num,
                overtime_bonus
            FROM adjourned_game LEFT JOIN variant USING(variant_id)
                LEFT JOIN speed USING(speed_id)
            WHERE (white_user_id=%s AND black_user_id=%s)
                OR (white_user_id=%s AND black_user_id=%s)""",
            (id1, id2, id2, id1))
        row = cursor.fetchone()
        cursor.close()
        return row

    def delete_adjourned(adjourn_id):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM adjourned_game WHERE adjourn_id=%s""",
            adjourn_id)
        cursor.close()

    def user_get_history(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT game_id, num, result_char, user_rating,
                color_char, opp_name, opp_rating, h.eco, flags, h.time,
                h.inc, h.result_reason, h.when_ended, movetext, idn
            FROM history AS h LEFT JOIN game USING(game_id)
                LEFT JOIN game_idn USING (game_id)
            WHERE user_id=%s
            ORDER BY when_ended ASC
            LIMIT 10""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_add_history(entry, user_id):
        cursor = db.cursor()
        entry.update({'user_id': user_id})
        cursor = query(cursor, """DELETE FROM history WHERE user_id=%s AND num=%s""", (user_id, entry['num']))
        cursor = query(cursor, """INSERT INTO history SET user_id=%(user_id)s,game_id=%(game_id)s, num=%(num)s, result_char=%(result_char)s, user_rating=%(user_rating)s, color_char=%(color_char)s, opp_name=%(opp_name)s, opp_rating=%(opp_rating)s, eco=%(eco)s, flags=%(flags)s, time=%(time)s, inc=%(inc)s, result_reason=%(result_reason)s, when_ended=%(when_ended)s""", entry)
        cursor.close()

    def user_del_history(user_id):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM history WHERE user_id=%s""", (user_id,))
        cursor.close()

    def user_get_ratings(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT * FROM (SELECT rating.variant_id as variant_id,rating.speed_id as speed_id,variant_name,speed_name,rating,rd,volatility,win,loss,draw,total,best,when_best,ltime FROM rating LEFT JOIN variant USING (variant_id) LEFT JOIN speed USING (speed_id) WHERE user_id=%s ORDER BY total DESC LIMIT 5) as tmp ORDER BY variant_id,speed_id""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_get_all_ratings(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT variant_id,speed_id,rating,rd,volatility,win,loss,draw,total,best,when_best,ltime FROM rating WHERE user_id=%s""", (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def user_set_rating(user_id, speed_id, variant_id,
            rating, rd, volatility, win, loss, draw, total, ltime):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE rating SET rating=%s,rd=%s,volatility=%s,win=%s,loss=%s,draw=%s,total=%s,ltime=%s WHERE user_id = %s AND speed_id = %s and variant_id = %s""", (rating, rd, volatility, win, loss, draw, total, ltime, user_id, speed_id, variant_id))
        if cursor.rowcount == 0:
            cursor = query(cursor, """INSERT INTO rating SET rating=%s,rd=%s,volatility=%s,win=%s,loss=%s,draw=%s,total=%s,ltime=%s,user_id=%s,speed_id=%s,variant_id=%s""", (rating, rd, volatility, win, loss, draw, total, ltime, user_id, speed_id, variant_id))
        assert(cursor.rowcount == 1)
        cursor.close()

    def user_del_rating(user_id, speed_id, variant_id):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM rating WHERE user_id = %s AND speed_id = %s and variant_id = %s""", (user_id, speed_id, variant_id))
        cursor.close()

    def user_set_email(user_id, email):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user
            SET user_email=%s WHERE user_id=%s""", (email, user_id))
        cursor.close()

    def user_set_real_name(user_id, real_name):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE user SET user_real_name=%s WHERE user_id=%s""",
                       (real_name, user_id))
        cursor.close()

    def get_variants():
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT variant_id,variant_name,variant_abbrev FROM variant""")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_speeds():
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT speed_id,speed_name,speed_abbrev FROM speed""")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    # news
    def add_news(title, user, is_admin):
        is_admin = '1' if is_admin else '0'
        cursor = db.cursor()
        cursor = query(cursor, """INSERT INTO news_index SET news_title=%s,news_poster=%s,news_when=NOW(),news_is_admin=%s""", (title, user.name, is_admin))
        news_id = cursor.lastrowid
        cursor.close()
        return news_id

    def delete_news(news_id):
        cursor = db.cursor()
        try:
            cursor = query(cursor, """DELETE FROM news_index WHERE news_id=%s LIMIT 1""", (news_id,))
            if cursor.rowcount != 1:
                raise DeleteError()
            cursor = query(cursor, """DELETE FROM news_line WHERE news_id=%s""", (news_id,))
        finally:
            cursor.close()

    def get_recent_news(is_admin):
        is_admin = '1' if is_admin else '0'
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """
            SELECT news_id,news_title,DATE(news_when) AS news_date,news_poster
            FROM news_index WHERE news_is_admin=%s
            ORDER BY news_id DESC LIMIT 10""", (is_admin,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_news_since(when, is_admin):
        is_admin = '1' if is_admin else '0'
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """
            SELECT news_id,news_title,DATE(news_when) as news_date,news_poster
            FROM news_index WHERE news_is_admin=%s AND news_when > %s
            ORDER BY news_id DESC LIMIT 10""", (is_admin, when))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_news_item(news_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """
            SELECT news_id,news_title,DATE(news_when) AS news_date,news_poster
            FROM news_index WHERE news_id=%s""", (news_id,))
        row = cursor.fetchone()
        if not row:
            return None

        cursor = query(cursor, """SELECT txt FROM news_line
            WHERE news_id=%s
            ORDER BY num ASC""", (news_id,))
        lines = cursor.fetchall()
        row['text'] = '\n'.join([line['txt'] for line in lines])
        cursor.close()
        return row

    def add_news_line(news_id, text):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT MAX(num) FROM news_line WHERE news_id=%s""",
            (news_id,))
        row = cursor.fetchone()
        if row[0] is None:
            num = 1
        else:
            num = row[0] + 1
        cursor = query(cursor, """INSERT INTO news_line
            SET news_id=%s,num=%s,txt=%s""", (news_id, num, text))
        cursor.close()

    def del_last_news_line(news_id):
        """ Delete the last line of a news item.  Returns False if there
        is no such item, and raises DeleteError if the item exists
        but has no lines. """
        cursor = db.cursor()
        cursor = query(cursor, """SELECT MAX(num) FROM news_line WHERE news_id=%s""",
            (news_id,))
        num = cursor.fetchone()[0]
        try:
            if num is None:
                raise DeleteError
            cursor = query(cursor, """DELETE FROM news_line
                WHERE news_id=%s AND num=%s""", (news_id, num))
            if cursor.rowcount != 1:
                raise DeleteError
        finally:
            cursor.close()

    def set_news_poster(news_id, u):
        """ Set the poster of a news item. """
        try:
            cursor = db.cursor()
            cursor = query(cursor, """UPDATE news_index SET news_poster=%s WHERE news_id=%s""",
                (u.name, news_id))
            if cursor.rowcount != 1:
                raise UpdateError
        finally:
            cursor.close()

    def set_news_title(news_id, title):
        """ Set the title of a news item. """
        try:
            cursor = db.cursor()
            cursor = query(cursor, """UPDATE news_index SET news_title=%s WHERE news_id=%s""",
                (title, news_id))
            if cursor.rowcount != 1:
                raise UpdateError
        finally:
            cursor.close()

    # messages
    def _get_next_message_id(cursor, uid):
        cursor = query(cursor, """SELECT MAX(num)
            FROM message
            WHERE to_user_id=%s""", (uid,))
        row = cursor.fetchone()
        return (row[0] + 1) if row[0] is not None else 1

    def _renumber_messages(cursor, uid):
        """ Renumber the messages for a given user, which is necessary
        when messages are deleted, possibly leaving a gap in the
        existing enumeration. """
        cursor = query(cursor, """SET @i=0""")
        cursor = query(cursor, """UPDATE message
            SET num=(@i := @i + 1)
            WHERE to_user_id=%s
            ORDER BY when_sent ASC,message_id ASC""",
            (uid,))

    def get_message(message_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,
                when_sent,txt,unread
            FROM message LEFT JOIN user AS sender ON
                (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE message_id=%s""",
            (message_id,))
        row = cursor.fetchone()
        cursor.close()
        return row

    def get_message_count(uid):
        """ Get counts of total and unread messages for a given user. """
        cursor = db.cursor()
        cursor = query(cursor, """SELECT COUNT(*),SUM(unread)
            FROM message
            WHERE to_user_id=%s""",
            (uid,))
        ret = cursor.fetchone()
        if ret[0] == 0:
            ret = (0, 0)
        cursor.close()
        return ret

    def get_messages_all(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender
                ON (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s
            ORDER BY num ASC""",
            (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_messages_unread(user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender
                ON (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s AND unread=1
            ORDER BY num ASC""",
            (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_messages_range(user_id, start, end):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT
                message_id,num,from_user_id,
                sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender ON
                (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s AND num BETWEEN %s AND %s
            ORDER BY num ASC""",
            (user_id, start, end))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_messages_from_to(from_user_id, to_user_id):
        cursor = db.cursor(cursors.DictCursor)
        cursor = query(cursor, """SELECT
                message_id,num,from_user_id,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender ON
                (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s AND from_user_id=%s
            ORDER BY num ASC""",
            (to_user_id, from_user_id))
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def send_message(from_user_id, to_user_id, txt):
        cursor = db.cursor()
        num = _get_next_message_id(cursor, to_user_id)
        cursor = query(cursor, """INSERT INTO message
            SET from_user_id=%s,to_user_id=%s,num=%s,txt=%s,when_sent=NOW(),
                unread=1""",
            (from_user_id, to_user_id, num, txt))
        message_id = cursor.lastrowid
        cursor.close()
        return message_id

    def forward_message(forwarder_user_id, to_user_id, message_id):
        cursor = db.cursor()
        num = _get_next_message_id(cursor, to_user_id)
        cursor = query(cursor, """INSERT INTO message
            (from_user_id,forwarder_user_id,to_user_id,num,txt,when_sent,unread)
            (SELECT from_user_id,%s,%s,%s,txt,when_sent,1 FROM message
                WHERE message_id=%s)""",
            (forwarder_user_id, to_user_id, num, message_id))
        message_id = cursor.lastrowid
        cursor.close()
        return message_id

    def set_messages_read_all(uid):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE message
            SET unread=0
            WHERE to_user_id=%s""", (uid))
        cursor.close()

    def set_message_read(message_id):
        cursor = db.cursor()
        cursor = query(cursor, """UPDATE message
            SET unread=0
            WHERE message_id=%s""", (message_id))
        cursor.close()

    def clear_messages_all(user_id):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM message WHERE to_user_id=%s""",
            (user_id,))
        ret = cursor.rowcount
        cursor.close()
        return ret

    def clear_messages_range(uid, start, end):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM message
            WHERE to_user_id=%s AND num BETWEEN %s AND %s""",
            (uid, start, end))
        ret = cursor.rowcount
        _renumber_messages(cursor, uid)
        cursor.close()
        return ret

    def clear_messages_from_to(from_user_id, to_user_id):
        cursor = db.cursor()
        cursor = query(cursor, """DELETE FROM message
            WHERE from_user_id=%s AND to_user_id=%s""",
            (from_user_id, to_user_id))
        ret = cursor.rowcount
        _renumber_messages(cursor, to_user_id)
        cursor.close()
        return ret

    # chess960
    def fen_from_idn(idn):
        assert(0 <= idn <= 959)
        cursor = db.cursor()
        cursor = query(cursor, """SELECT fen FROM chess960_pos
            WHERE idn=%s""", (idn,))
        row = cursor.fetchone()
        assert(row)
        cursor.close()
        return row[0]

    def idn_from_fen(fen):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT idn FROM chess960_pos
            WHERE fen=%s""", (fen,))
        row = cursor.fetchone()
        cursor.close()
        if row:
            return row[0]
        else:
            return None

    def game_add_idn(game_id, idn):
        cursor = db.cursor()
        cursor = query(cursor, """INSERT INTO game_idn VALUES(%s,%s)""",
            (game_id, idn))
        cursor.close()

    def get_server_message(name):
        cursor = db.cursor()
        cursor = query(cursor, """SELECT server_message_text FROM server_message
            WHERE server_message_name = %s""", (name,))
        row = cursor.fetchone()
        cursor.close()
        return row[0]

_init()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
