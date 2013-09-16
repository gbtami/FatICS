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

from MySQLdb import cursors, IntegrityError
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
adb = None

if 1:
    def init():
        def openfun(adbconn):
            cursor = adbconn.cursor()
            cursor.execute("""SET time_zone='+00:00'""")
            cursor.execute("""SET charset utf8""")
            cursor.execute("""SET wait_timeout=604800""") # 1 week
            cursor.close()
        global adb
        adb = adbapi.ConnectionPool("MySQLdb",
            host=config.db_host, db=config.db_db,
            read_default_file="~/.my.cnf", cursorclass=cursors.DictCursor,
            cp_reconnect=True, cp_min=1, cp_max=3, cp_openfun=openfun)

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
            d = adb.runOperation("""INSERT INTO formula SET user_id=%s,num=%s,f=%s ON DUPLICATE KEY UPDATE f=%s""",
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

    def user_set_alias(user_id, name, val):
        if val is not None:
            d = adb.runOperation("""INSERT INTO user_alias SET user_id=%s,name=%s,val=%s ON DUPLICATE KEY UPDATE val=%s""",
                (user_id, name, val, val))
        else:
            def do_del(txn):
                txn.execute("""DELETE FROM user_alias WHERE user_id=%s AND name=%s""",
                    (user_id, name))
                if txn.rowcount != 1:
                    raise DeleteError()
            d = adb.runInteraction(do_del)
        return d

    def user_get_aliases(user_id):
        return adb.runQuery("""SELECT name,val FROM user_alias WHERE user_id=%s ORDER BY name ASC""",
            (user_id,))

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
            # XXX probably we should instead fail with an error
            # if the player is in removed_user
            txn.execute("""DELETE FROM removed_user
                WHERE user_name=%s""", (name,))
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
        return adb.runOperation("""UPDATE user
            SET user_first_login=NOW() WHERE user_id=%s""", (uid,))

    @defer.inlineCallbacks
    def user_get_first_login(uid):
        rows = yield adb.runQuery("""SELECT user_first_login
            FROM user WHERE user_id=%s""", (uid,))
        defer.returnValue(rows[0]['user_first_login'])

    def user_set_last_logout(uid):
        return adb.runOperation("""UPDATE user
            SET user_last_logout=NOW() WHERE user_id=%s""", (uid,))

    def user_add_to_total_time_online(uid, secs):
        """ Expects secs to be an integer. """
        assert(secs >= 0)
        return adb.runOperation("""UPDATE user
            SET user_total_time_online=user_total_time_online+%s
            WHERE user_id=%s""", (secs, uid))

    @defer.inlineCallbacks
    def user_log_add(user_name, login, ip):
        """Add an entry to a user's log."""
        # delete old log entry, if necessary
        # XXX it would probably be more efficient to periodically
        # delete extra entries
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c FROM user_log
            WHERE log_who_name=%s""", (user_name,))
        count = rows[0]['c']
        if count >= 10:
            #assert(count == 10)
            limit = count - 9
            yield adb.runOperation("""DELETE FROM user_log
                WHERE log_who_name=%s ORDER BY log_when DESC LIMIT %s""",
                    (user_name, limit))

        which = 'login' if login else 'logout'
        yield adb.runOperation("""INSERT INTO user_log
            SET log_who_name=%s,log_which=%s,log_ip=%s,log_when=NOW()""",
                (user_name, which, ip))

    def user_get_log(user_name):
        return adb.runQuery("""SELECT log_who_name,log_when,
                log_which,log_ip
            FROM user_log
            WHERE log_who_name=%s
            ORDER BY log_when DESC LIMIT 10""", (user_name,))

    def get_log_all(limit):
        return adb.runQuery("""SELECT log_who_name,log_when,
                log_which,log_ip
            FROM user_log
            ORDER BY log_when DESC
            LIMIT %s""", (limit,))

    @defer.inlineCallbacks
    def get_muted_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_muted=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    def user_set_banned(uid, val):
        assert(val in [0, 1])
        d = adb.runOperation("""UPDATE user
            SET user_banned=%s WHERE user_id=%s""", (val, uid))
        return d

    @defer.inlineCallbacks
    def get_banned_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_banned=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def user_set_muzzled(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_muzzled=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def get_muzzled_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_muzzled=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def user_set_cmuzzled(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_cmuzzled=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def get_cmuzzled_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_cmuzzled=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def user_set_muted(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_muted=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def user_set_notebanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_notebanned=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def get_notebanned_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_notebanned=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def user_set_ratedbanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_ratedbanned=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def get_ratedbanned_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_ratedbanned=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def user_set_playbanned(uid, val):
        assert(val in [0, 1])
        yield adb.runOperation("""UPDATE user
            SET user_playbanned=%s WHERE user_id=%s""", (val, uid))

    @defer.inlineCallbacks
    def get_playbanned_user_names():
        rows = yield adb.runQuery("""SELECT user_name FROM user
            WHERE user_playbanned=1 LIMIT 500""")
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    def user_delete(uid):
        """ Move a user to the removed_user table.  Currently this
        removes all adjourned games, messages, comments, logs, lists,
        ratings, titles, and variables for the user, although maybe that
        should be changed in the future. """
        def do_del(txn):
            txn.execute("INSERT INTO removed_user SELECT * FROM user WHERE user_id=%s",
                (uid,))
            # this needs to be done before deleting the row from user
            txn.execute("""DELETE FROM user_log WHERE log_who_name=(
                SELECT user_name FROM user WHERE user_id=%s)""", (uid,))
            txn.execute("""DELETE FROM user WHERE user_id=%s""", (uid,))
            if txn.rowcount != 1:
                raise DeleteError

            txn.execute("""DELETE FROM user_comment WHERE user_id=%s""", (uid,))
            txn.execute("""DELETE FROM user_title WHERE user_id=%s""", (uid,))
            txn.execute("""DELETE FROM user_notify
                WHERE %s IN (notifier, notified)""", (uid,))
            txn.execute("""DELETE FROM user_gnotify
                WHERE %s IN (gnotifier, gnotified)""", (uid,))
            txn.execute("""DELETE FROM censor WHERE %s IN
                (censorer, censored)""", (uid,))
            txn.execute("""DELETE FROM noplay WHERE %s IN
                (noplayer, noplayed)""", (uid,))
            txn.execute("""DELETE FROM formula WHERE user_id=%s""", (uid,))
            txn.execute("""DELETE FROM note WHERE user_id=%s""", (uid,))
            txn.execute("""DELETE FROM channel_user WHERE user_id=%s""",
                (uid,))
            txn.execute("""DELETE FROM history WHERE game_id IN
                (SELECT game_id FROM game WHERE %s IN
                    (white_user_id, black_user_id))""", (uid,))
            txn.execute("""DELETE FROM rating WHERE user_id=%s""", (uid,))
            txn.execute("""DELETE FROM message WHERE to_user_id=%s""", (uid,))
            txn.execute("""DELETE FROM game WHERE %s IN
                (white_user_id, black_user_id)""", (uid,))
        return adb.runInteraction(do_del)

    def user_undelete(name):
        """Move a user from the removed_user table back to user."""
        def do_undel(txn):
            txn.execute("SELECT user_id FROM removed_user WHERE user_name=%s",
                (name,))
            row = txn.fetchone()
            if not row:
                raise DeleteError
            uid = row['user_id']
            txn.execute("INSERT INTO user SELECT * FROM removed_user WHERE user_id=%s",
                (uid,))
            if txn.rowcount != 1:
                raise DeleteError
            txn.execute("""DELETE FROM removed_user WHERE user_id=%s""",
                (uid,))
            if txn.rowcount != 1:
                raise DeleteError
        return adb.runInteraction(do_undel)

    # filtered ips
    @defer.inlineCallbacks
    def get_filtered_ips():
        rows = yield adb.runQuery("""SELECT filter_pattern FROM ip_filter LIMIT 8192""")
        ret = [r['filter_pattern'] for r in rows]
        defer.returnValue(ret)

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

    @defer.inlineCallbacks
    def get_comments(user_id):
        rows = yield adb.runQuery("""
            SELECT user_name AS admin_name,when_added,txt FROM user_comment
                LEFT JOIN user ON (user.user_id=user_comment.admin_id)
                WHERE user_comment.user_id=%s
                ORDER BY when_added DESC""", (user_id,))
        defer.returnValue(rows)

    # channels
    @defer.inlineCallbacks
    def user_get_channels(id_):
        rows = yield adb.runQuery("""SELECT channel_id FROM channel_user
            WHERE user_id=%s""", (id_,))
        defer.returnValue([r['channel_id'] for r in rows])

    def channel_new(chid, name):
        """Create a new channel entry in the database."""
        if name is not None:
            return adb.runOperation("""INSERT INTO channel SET channel_id=%s,name=%s""", (chid, name,))
        else:
            return adb.runOperation("""INSERT INTO channel SET channel_id=%s""", (chid,))

    def channel_add_user(chid, user_id):
        return adb.runOperation("""INSERT INTO channel_user
            SET user_id=%s,channel_id=%s""", (user_id, chid))

    def channel_set_topic(args):
        def do_update(txn):
            txn.execute("""UPDATE channel
                SET topic=%(topic)s,topic_who=%(topic_who)s,
                    topic_when=%(topic_when)s
                WHERE channel_id=%(channel_id)s""", args)
            assert(txn.rowcount == 1)
        return adb.runInteraction(do_update)

    def channel_del_topic(chid):
        def do_update(txn):
            txn.execute("""UPDATE channel SET topic=NULL
                WHERE channel_id=%s""", chid)
            assert(txn.rowcount == 1)
        return adb.runInteraction(do_update)

    def channel_del_user(ch_id, user_id):
        def do_del(txn):
            txn.execute("""DELETE FROM channel_user
                WHERE user_id=%s AND channel_id=%s""", (user_id, ch_id))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def get_channel_list():
        """Get a list of all channels and their descriptions and topics."""
        return adb.runQuery("""SELECT channel_id,name,descr,
            topic,user_name AS topic_who_name,topic_when
            FROM channel LEFT JOIN user ON(channel.topic_who=user.user_id)""")

    @defer.inlineCallbacks
    def user_in_channel(user_id, chid):
        """Check whether a user is in a given channel."""
        rows = yield adb.runQuery("""SELECT 1 FROM channel_user
            WHERE channel_id=%s AND user_id=%s LIMIT 1""", (chid, user_id))
        defer.returnValue(bool(rows))

    @defer.inlineCallbacks
    def channel_user_count(chid):
        """Find how many users are in a channel."""
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c FROM channel_user
            WHERE channel_id=%s""", (chid,))
        defer.returnValue(rows[0]['c'])

    @defer.inlineCallbacks
    def channel_is_owner(chid, user_id):
        """Check whether the given user is an owner of the given channel."""
        """ TODO this should probably be cached somewhere,
        rather than querying the DB every time. """
        rows = yield adb.runQuery("""SELECT 1 FROM channel_user
             WHERE channel_id=%s AND user_id=%s AND is_owner=1""",
             (chid, user_id))
        defer.returnValue(bool(rows))

    def channel_set_owner(chid, user_id, val):
        """Add or remove an owner of a channel."""
        assert(val in [0, 1])
        def do(txn):
            txn.execute("""UPDATE channel_user
                SET is_owner=%s WHERE channel_id=%s AND user_id=%s""",
                (val, chid, user_id))
            if txn.rowcount != 1:
                raise UpdateError
        return adb.runInteraction(do)

    @defer.inlineCallbacks
    def user_channels_owned(user_id):
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c FROM channel_user
            WHERE user_id=%s AND is_owner=1""", (user_id,))
        defer.returnValue(rows[0]['c'])

    @defer.inlineCallbacks
    def user_add_title(user_id, title_id):
        try:
            yield adb.runOperation("""INSERT INTO user_title SET user_id=%s,title_id=%s""",
                (user_id, title_id))
        except IntegrityError:
            raise DuplicateKeyError()

    def user_del_title(user_id, title_id):
        def do_del(txn):
            txn.execute("""DELETE FROM user_title WHERE user_id=%s AND title_id=%s""",
            (user_id, title_id))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_titles(user_id):
        """Get a list of a player's titles, such as TM, admin, or abuser."""
        return adb.runQuery("""SELECT title_name,title_flag,title_light FROM user_title LEFT JOIN title USING (title_id) WHERE user_id=%s ORDER BY title_id ASC""",
            (user_id,))

    def toggle_title_light(user_id, title_id):
        """Toggle the light that appears after a player's
        name and marks the player as on or off duty, e.g. (*) for
        admins or (TM) for tourney managers."""
        return adb.runOperation("""UPDATE user_title
            SET title_light=NOT title_light
            WHERE title_id=%s AND user_id=%s""", (title_id, user_id))

    # notifications
    @defer.inlineCallbacks
    def user_add_notification(notified, notifier):
        try:
            yield adb.runOperation("""INSERT INTO user_notify SET notified=%s,notifier=%s""",
                (notified, notifier))
        except IntegrityError:
            raise DuplicateKeyError()

    def user_del_notification(notified, notifier):
        def do_del(txn):
            txn.execute("""DELETE FROM user_notify WHERE notified=%s AND notifier=%s""",
            (notified, notifier))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_notified(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notified) WHERE notifier=%s""",
            (user_id,))

    def user_get_notifiers(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN user_notify ON (user.user_id=user_notify.notifier) WHERE notified=%s""",
            (user_id,))

    # game notifications
    @defer.inlineCallbacks
    def user_add_gnotification(gnotified, gnotifier):
        try:
            yield adb.runOperation("""INSERT INTO user_gnotify
                SET gnotified=%s,gnotifier=%s""", (gnotified, gnotifier))
        except IntegrityError:
            raise DuplicateKeyError()

    def user_del_gnotification(notified, notifier):
        def do_del(txn):
            txn.execute("""DELETE FROM user_gnotify
                WHERE gnotified=%s AND gnotifier=%s""", (notified, notifier))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_gnotified(user_id):
        return adb.runQuery("""SELECT user_name FROM user
            LEFT JOIN user_gnotify ON (user.user_id=user_gnotify.gnotified)
            WHERE gnotifier=%s""", (user_id,))

    def user_get_gnotifiers(user_id):
        return adb.runQuery("""SELECT user_name FROM user
            LEFT JOIN user_gnotify ON (user.user_id=user_gnotify.gnotifier)
            WHERE gnotified=%s""", (user_id,))

    # censor list
    def user_add_censor(censorer, censored):
        try:
            d = adb.runOperation("""INSERT INTO censor SET censored=%s,censorer=%s""",
                (censored, censorer))
        except IntegrityError:
            raise DuplicateKeyError()
        return d

    def user_del_censor(censorer, censored):
        def do_del(txn):
            txn.execute("""DELETE FROM censor WHERE censored=%s AND censorer=%s""",
                (censored, censorer))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    '''@defer.inlineCallbacks
    def user_get_censored_async(user_id):
        rows = yield adb.runQuery("""SELECT user_name FROM user LEFT JOIN censor ON (user.user_id=censor.censored) WHERE censorer=%s""", (user_id,))
        defer.returnValue(rows)'''

    def user_get_censored(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN censor ON (user.user_id=censor.censored) WHERE censorer=%s""",
            (user_id,))

    # noplay list
    @defer.inlineCallbacks
    def user_add_noplay(noplayer, noplayed):
        try:
            yield adb.runOperation("""INSERT INTO noplay SET noplayed=%s,noplayer=%s""", (noplayed, noplayer))
        except IntegrityError:
            raise DuplicateKeyError()

    def user_del_noplay(noplayer, noplayed):
        def do_del(txn):
            txn.execute("""DELETE FROM noplay WHERE noplayed=%s AND noplayer=%s""",
            (noplayed, noplayer))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_noplayed(user_id):
        return adb.runQuery("""SELECT user_name FROM user LEFT JOIN noplay ON (user.user_id=noplay.noplayed) WHERE noplayer=%s""", (user_id,))

    def title_get_all():
        return adb.runQuery("""SELECT title_id,title_name,title_descr,title_flag,title_public FROM title""")

    @defer.inlineCallbacks
    def title_get_users(title_id):
        rows = yield adb.runQuery("""SELECT user_name FROM user LEFT JOIN user_title USING(user_id) WHERE title_id=%s""",
            (title_id,))
        ret = [r['user_name'] for r in rows]
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def get_eco(hash_):
        rows = yield adb.runQuery("""SELECT eco,long_ FROM eco WHERE hash=%s""",
            (hash_,))
        ret = rows[0] if rows else None
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def get_nic(hash_):
        rows = yield adb.runQuery("""SELECT nic FROM nic WHERE hash=%s""",
            (hash_,))
        ret = rows[0] if rows else None
        defer.returnValue(ret)

    def look_up_eco(eco):
        if len(eco) == 3:
            # match all subvariations
            eco = '%s%%' % eco
        d = adb.runQuery("""SELECT eco,nic,long_,eco.fen AS fen FROM eco LEFT JOIN nic USING(hash) WHERE eco LIKE %s LIMIT 100""", (eco,))
        return d

    def look_up_nic(nic):
        d = adb.runQuery("""SELECT eco,nic,long_,nic.fen AS fen FROM nic LEFT JOIN eco USING(hash) WHERE nic = %s LIMIT 100""", (nic,))
        return d

    def game_add(g):
        """Add a completed or adjourned game to the main game table."""
        def do(txn, g):
            txn.execute("""INSERT INTO game SET
                white_user_id=%(white_user_id)s,
                black_user_id=%(black_user_id)s,
                white_clock=%(white_clock)s,
                black_clock=%(black_clock)s,
                white_rating=%(white_rating)s,
                black_rating=%(black_rating)s,
                eco=%(eco)s,variant_id=%(variant_id)s,speed_id=%(speed_id)s,
                time=%(time)s,inc=%(inc)s,is_rated=%(is_rated)s,
                adjourn_reason=%(adjourn_reason)s,ply_count=%(ply_count)s,
                movetext=%(movetext)s,
                white_material=%(white_material)s,
                black_material=%(black_material)s,
                when_started=%(when_started)s,
                when_ended=%(when_ended)s,
                clock_id=%(clock_id)s,
                result=%(result)s,
                result_reason=%(result_reason)s,
                draw_offered=%(draw_offered)s,
                is_adjourned=%(is_adjourned)s
                """, g)
                #overtime_move_num=%(overtime_move_num),
                #overtime_bonus=%(overtime_bonus),
            return txn.lastrowid
        return adb.runInteraction(do, g)

    @defer.inlineCallbacks
    def get_clock_id(clock_name):
        """Get the ID of a clock type, given the name."""
        rows = yield adb.runQuery("""SELECT clock_id FROM clock
            WHERE clock_name=%s""", (clock_name,))
        row = rows[0]
        defer.returnValue(row['clock_id'])

    def get_adjourned(user_id):
        """ Look up adjourned games by the given user."""
        return adb.runQuery("""SELECT game_id,white_user_id,black_user_id,
                white_clock,black_clock,eco,speed_name,speed_abbrev,
                variant_name,variant_abbrev,clock.clock_name AS clock_name,
                game.time AS time,game.inc AS inc,is_rated,
                adjourn_reason,ply_count,movetext,white_material,black_material,
                when_started,when_ended,idn,overtime_move_num,
                overtime_bonus,white.user_name as white_name,
                black.user_name as black_name
            FROM game
                LEFT JOIN user AS white
                    ON (white.user_id = white_user_id)
                LEFT JOIN user AS black
                    ON (black.user_id = black_user_id)
                LEFT JOIN variant USING(variant_id)
                LEFT JOIN speed USING(speed_id)
                LEFT JOIN game_idn USING(game_id)
                LEFT JOIN clock USING(clock_id)
            WHERE %s IN (white_user_id, black_user_id)
            AND is_adjourned=1""", (user_id,))

    def delete_adjourned(game_id):
        """Delete an adjourned game."""
        def do_del(txn):
            txn.execute("""DELETE FROM game WHERE game_id=%s
                AND is_adjourned=1""",
                (game_id,))
            if txn.rowcount != 1:
                raise DeleteError()
        return adb.runInteraction(do_del)

    def user_get_history(user_id):
        """Get recent game history for the given user.  In the future
        this function could be extended to allow looking farther back."""
        return adb.runQuery("""SELECT h.game_id AS game_id,
                white_user_id, black_user_id, white.user_name AS white_name,
                black.user_name AS black_name, white_rating, black_rating,
                num, eco, game.time AS time, game.inc AS inc, result_reason,
                when_ended, movetext, idn, result, speed_id, variant_id,
                is_rated, guest_opp_name
            FROM history AS h
                LEFT JOIN game USING(game_id)
                LEFT JOIN user AS white ON(game.white_user_id = white.user_id)
                LEFT JOIN user AS black ON(game.black_user_id = black.user_id)
                LEFT JOIN game_idn USING (game_id)
            WHERE h.user_id=%s
            ORDER BY when_ended ASC
            LIMIT 10""", (user_id,))

    def user_add_history(entry, user_id):
        """Add a history entry for a user, removing old entries if
        necessary."""
        entry.update({'user_id': user_id})
        def do(txn):
            txn.execute("""DELETE FROM history WHERE user_id=%s AND num=%s""", (user_id, entry['num']))
            txn.execute("""INSERT INTO history SET user_id=%(user_id)s,game_id=%(game_id)s, num=%(num)s, guest_opp_name=%(guest_opp_name)s""", entry)
        return adb.runInteraction(do)

    def user_del_history(user_id):
        """Delete all entries from a user's history."""
        return adb.runOperation("""DELETE FROM history WHERE user_id=%s""",
            (user_id,))

    def user_get_ratings_for_finger(user_id):
        """Get a list of ratings suitable for display in finger notis."""
        return adb.runQuery("""
            SELECT * FROM (
                SELECT rating.variant_id AS variant_id,rating.speed_id AS speed_id,variant_name,speed_name,rating,rd,volatility,win,loss,draw,total,best,when_best,ltime
                FROM rating
                LEFT JOIN variant USING (variant_id)
                LEFT JOIN speed USING (speed_id) WHERE user_id=%s
                ORDER BY total DESC LIMIT 5)
            AS tmp ORDER BY variant_id,speed_id""",
        (user_id,))

    def user_get_all_ratings(user_id):
        """Get all of a user's ratings for all variants and speeds."""
        return adb.runQuery("""SELECT variant_id,speed_id,rating,rd,volatility,win,loss,draw,total,best,when_best,ltime FROM rating WHERE user_id=%s""",
            (user_id,))

    def user_set_rating(user_id, speed_id, variant_id,
            rating, rd, volatility, win, loss, draw, total, ltime):
        def do(txn):
            txn.execute("""UPDATE rating SET rating=%s,rd=%s,volatility=%s,win=%s,loss=%s,draw=%s,total=%s,ltime=%s WHERE user_id = %s AND speed_id = %s and variant_id = %s""",
                (rating, rd, volatility, win, loss, draw, total, ltime,
                user_id, speed_id, variant_id))
            if txn.rowcount == 0:
                txn.execute("""INSERT INTO rating SET rating=%s,rd=%s,volatility=%s,win=%s,loss=%s,draw=%s,total=%s,ltime=%s,user_id=%s,speed_id=%s,variant_id=%s""",
                    (rating, rd, volatility, win, loss, draw, total, ltime,
                    user_id, speed_id, variant_id))
            if txn.rowcount != 1:
                raise UpdateError
        return adb.runInteraction(do)

    def user_del_rating(user_id, speed_id, variant_id):
        return adb.runOperation("""DELETE FROM rating WHERE user_id = %s AND speed_id = %s and variant_id = %s""",
            (user_id, speed_id, variant_id))

    def user_set_email(user_id, email):
        return adb.runOperation("""UPDATE user
            SET user_email=%s WHERE user_id=%s""", (email, user_id))

    def user_set_real_name(user_id, real_name):
        return adb.runOperation("""UPDATE user SET user_real_name=%s WHERE user_id=%s""",
            (real_name, user_id))

    def get_variants():
        return adb.runQuery("""SELECT variant_id,variant_name,variant_abbrev FROM variant""")

    def get_speeds():
        return adb.runQuery("""SELECT speed_id,speed_name,speed_abbrev FROM speed""")

    # news
    def add_news(title, user, is_admin):
        is_admin = '1' if is_admin else '0'
        def do_insert(txn):
            txn.execute("""INSERT INTO news_index SET news_title=%s,news_poster=%s,news_when=NOW(),news_is_admin=%s""",
                (title, user.name, is_admin))
            news_id = txn.lastrowid
            return news_id
        return adb.runInteraction(do_insert)

    def delete_news(news_id):
        def do_del(txn):
            txn.execute("""DELETE FROM news_index WHERE news_id=%s LIMIT 1""",
                (news_id,))
            if txn.rowcount != 1:
                raise DeleteError()
            txn.execute("""DELETE FROM news_line WHERE news_id=%s""",
                (news_id,))
        return adb.runInteraction(do_del)

    def get_recent_news(is_admin):
        is_admin = '1' if is_admin else '0'
        return adb.runQuery("""
            SELECT news_id,news_title,DATE(news_when) AS news_date,news_poster
            FROM news_index WHERE news_is_admin=%s
            ORDER BY news_id DESC LIMIT 10""", (is_admin,))

    def get_news_since(when, is_admin):
        is_admin = '1' if is_admin else '0'
        return adb.runQuery("""
            SELECT news_id,news_title,DATE(news_when) as news_date,news_poster
            FROM news_index WHERE news_is_admin=%s AND news_when > %s
            ORDER BY news_id DESC LIMIT 10""", (is_admin, when))

    @defer.inlineCallbacks
    def get_news_item(news_id):
        rows = yield adb.runQuery("""
            SELECT news_id,news_title,DATE(news_when) AS news_date,news_poster
            FROM news_index WHERE news_id=%s""", (news_id,))
        if not rows:
            return
        row = rows[0]

        lines = yield adb.runQuery("""SELECT txt FROM news_line
            WHERE news_id=%s
            ORDER BY num ASC""", (news_id,))
        row['text'] = '\n'.join([line['txt'] for line in lines])
        defer.returnValue(row)

    @defer.inlineCallbacks
    def add_news_line(news_id, text):
        rows = yield adb.runQuery("""SELECT MAX(num) AS m FROM news_line WHERE news_id=%s""",
            (news_id,))
        row = rows[0]
        if row['m'] is None:
            num = 1
        else:
            num = row['m'] + 1
        yield adb.runOperation("""INSERT INTO news_line
            SET news_id=%s,num=%s,txt=%s""", (news_id, num, text))

    @defer.inlineCallbacks
    def del_last_news_line(news_id):
        """ Delete the last line of a news item.  Raise DeleteError if
        there is no such item, or if the item exists but has no lines. """
        rows = yield adb.runQuery("""
            SELECT MAX(num) AS m FROM news_line WHERE news_id=%s""",
            (news_id,))
        num = rows[0]['m']
        if num is None:
            raise DeleteError
        def do_del(txn):
            txn.execute("""DELETE FROM news_line
                WHERE news_id=%s AND num=%s""", (news_id, num))
            if txn.rowcount != 1:
                raise DeleteError
        yield adb.runInteraction(do_del)

    @defer.inlineCallbacks
    def set_news_poster(news_id, u):
        """ Set the poster of a news item. """
        def do_update(txn):
            txn.execute("""UPDATE news_index SET news_poster=%s WHERE news_id=%s""",
                (u.name, news_id))
            if txn.rowcount != 1:
                raise UpdateError
        yield adb.runInteraction(do_update)

    @defer.inlineCallbacks
    def set_news_title(news_id, title):
        """ Set the title of a news item. """
        def do_update(txn):
            txn.execute("""UPDATE news_index SET news_title=%s WHERE news_id=%s""",
                (title, news_id))
            if txn.rowcount != 1:
                raise UpdateError
        yield adb.runInteraction(do_update)

    # messages
    @defer.inlineCallbacks
    def _get_next_message_id(uid):
        rows = yield adb.runQuery("""SELECT MAX(num) AS m
            FROM message
            WHERE to_user_id=%s""", (uid,))
        max_ = rows[0]['m']
        if max_:
            mid = max_ + 1
        else:
            mid = 1
        defer.returnValue(mid)

    def _renumber_messages(uid):
        """ Renumber the messages for a given user, which is necessary
        when messages are deleted, possibly leaving a gap in the
        existing enumeration. """
        def do_renum(txn):
            txn.execute("""SET @i=0""")
            txn.execute("""UPDATE message
                SET num=(@i := @i + 1)
                WHERE to_user_id=%s
                ORDER BY when_sent ASC,message_id ASC""",
                (uid,))
        return adb.runInteraction(do_renum)

    @defer.inlineCallbacks
    def get_message(message_id):
        rows = yield adb.runQuery("""SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,
                when_sent,txt,unread
            FROM message LEFT JOIN user AS sender ON
                (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE message_id=%s""",
            (message_id,))
        if rows:
            ret = rows[0]
        else:
            ret = None
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def get_message_count(uid):
        """ Get counts of total and unread messages for a given user. """
        rows = yield adb.runQuery("""SELECT COUNT(*) AS c,
            SUM(unread) AS s
            FROM message
            WHERE to_user_id=%s""",
            (uid,))
        ret = rows[0]
        if ret['c'] == 0:
            ret = (0, 0)
        else:
            ret = (ret['c'], ret['s'])
        defer.returnValue(ret)

    def get_messages_all(user_id):
        return adb.runQuery("""SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender
                ON (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s
            ORDER BY num ASC""",
            (user_id,))

    def get_messages_unread(user_id):
        return adb.runQuery("""SELECT
                message_id,num,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender
                ON (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s AND unread=1
            ORDER BY num ASC""",
            (user_id,))

    def get_messages_range(user_id, start, end):
        return adb.runQuery("""SELECT
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

    def get_messages_from_to(from_user_id, to_user_id):
        return adb.runQuery("""SELECT
                message_id,num,from_user_id,sender.user_name AS sender_name,
                forwarder.user_name AS forwarder_name,when_sent,txt,unread
            FROM message LEFT JOIN user AS sender ON
                (message.from_user_id = sender.user_id)
            LEFT JOIN user AS forwarder ON
                (message.forwarder_user_id = forwarder.user_id)
            WHERE to_user_id=%s AND from_user_id=%s
            ORDER BY num ASC""",
            (to_user_id, from_user_id))

    @defer.inlineCallbacks
    def send_message(from_user_id, to_user_id, txt):
        """Send a message and return the resulting message_id."""
        num = yield _get_next_message_id(to_user_id)
        def do_insert(txn):
            txn.execute("""INSERT INTO message
                SET from_user_id=%s,to_user_id=%s,num=%s,txt=%s,when_sent=NOW(),
                    unread=1""",
                (from_user_id, to_user_id, num, txt))
            return txn.lastrowid
        message_id = yield adb.runInteraction(do_insert)
        defer.returnValue(message_id)

    @defer.inlineCallbacks
    def forward_message(forwarder_user_id, to_user_id, message_id):
        """Forward a message and return the resulting message_id."""
        num = yield _get_next_message_id(to_user_id)
        def do_insert(txn):
            txn.execute("""INSERT INTO message
                (from_user_id,forwarder_user_id,to_user_id,num,txt,when_sent,unread)
                (SELECT from_user_id,%s,%s,%s,txt,when_sent,1 FROM message
                    WHERE message_id=%s)""",
                (forwarder_user_id, to_user_id, num, message_id))
            return txn.lastrowid
        message_id = yield adb.runInteraction(do_insert)
        defer.returnValue(message_id)

    def set_messages_read_all(uid):
        return adb.runOperation("""UPDATE message
            SET unread=0
            WHERE to_user_id=%s""", (uid,))

    def set_message_read(message_id):
        return adb.runOperation("""UPDATE message
            SET unread=0
            WHERE message_id=%s""", (message_id,))

    def clear_messages_all(user_id):
        def do_del(txn):
            txn.execute("""DELETE FROM message WHERE to_user_id=%s""",
                (user_id,))
            return txn.rowcount
        return adb.runInteraction(do_del)

    @defer.inlineCallbacks
    def clear_messages_range(uid, start, end):
        def do_del(txn):
            txn.execute("""DELETE FROM message
                WHERE to_user_id=%s AND num BETWEEN %s AND %s""",
                (uid, start, end))
            return txn.rowcount
        ret = yield adb.runInteraction(do_del)
        yield _renumber_messages(uid)
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def clear_messages_from_to(from_user_id, to_user_id):
        def do_del(txn):
            txn.execute("""DELETE FROM message
                WHERE from_user_id=%s AND to_user_id=%s""",
                (from_user_id, to_user_id))
            return txn.rowcount
        ret = yield adb.runInteraction(do_del)
        yield _renumber_messages(to_user_id)
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def fen_from_idn(idn):
        """Get the FEN representing a chess960 position, given an idn."""
        assert(0 <= idn <= 959)
        rows = yield adb.runQuery("""SELECT fen FROM chess960_pos
            WHERE idn=%s""", (idn,))
        fen = rows[0]['fen']
        defer.returnValue(fen)

    '''@defer.inlineCallbacks
    def idn_from_fen(fen):
        """Get the idn representing a chess960 position, given a FEN."""
        rows = yield adb.runQuery("""SELECT idn FROM chess960_pos
            WHERE fen=%s""", (fen,))
        row = rows[0]
        if row:
            defer.returnValue(row['idn'])
        else:
            defer.returnValue(None)'''

    def game_add_idn(game_id, idn):
        """Save the idn representing the starting position of a specified
        chess960 game."""
        return adb.runOperation("""INSERT INTO game_idn VALUES(%s,%s)""",
            (game_id, idn))

    def get_server_messages():
        """Fetch all dynamic server messages in the DB."""
        return adb.runQuery("""SELECT server_message_name,server_message_text
            FROM server_message""")

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
