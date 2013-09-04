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

import re
import bcrypt
import random
import string
import datetime
import pytz

import admin
import notify
import rating
import speed_variant
import global_
import server
import db
import config

from twisted.internet import defer, threads


class BaseUser(object):
    def __init__(self):
        self.is_online = False
        self.notes = {}
        self._history = None
        #self._titles = None
        self._title_str = None

    def __eq__(self, other):
        return other and (self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def log_on(self, conn):
        assert(not self.is_online)
        self.vars_.update(global_.var_defaults.get_transient_vars())
        self.aliases = {}
        self.gnotified = set()
        self.gnotifiers = set()
        self.noplay = set()
        self.session = conn.session
        self.session.set_user(self)
        notify.notify_pin(self, arrived=True)
        self.is_online = True
        global_.online.add(self)
        if not self.session.ivars['nowrap']:
            conn.transport.enableWrapping(self.vars_['width'])
        self.write(server.get_copyright_notice())
        self.write(db.get_server_message('motd'))
        for ch in self.channels:
            global_.channels[ch].log_on(self)

        d = db.user_log_add(self.name, login=True, ip=conn.ip)
        return d

    def log_off(self):
        assert(self.is_online)

        for ch in self.channels:
            global_.channels[ch].log_off(self)
        self.session.close()
        self.is_online = False
        global_.online.remove(self)
        notify.notify_pin(self, arrived=False)

        d = db.user_log_add(self.name, login=False, ip=self.session.conn.ip)
        return d

    def write(self, s):
        """ Write a string to the user. """
        assert(self.is_online)
        if self == global_.curuser:
            if s[0] == '\n':
                # XXX HACK
                s = s[1:]
            self.session.conn.write(s)
        else:
            #s = ''.join(('\n', s))
            self.write_prompt(s)

    def write_nowrap(self, s, prompt=False):
        """ Write a string to the user without word wrapping. """
        # XXX this does not obey conn.buffer_output
        self.session.conn.transport.write(s, wrap=False)
        if prompt:
            self.write_prompt()

    def write_(self, s, args={}):
        """ Like write(), but localizes for this user. """
        #assert(isinstance(args, (list, dict, tuple)))
        if self == global_.curuser:
            if s[0] == '\n':
                # XXX HACK strip off newline at the beginning
                s = s[1:]
            self.session.conn.write(s % args)
        else:
            self.session.conn.write(global_.langs[self.vars_['lang']].gettext(s) %
                args)
            self.write_prompt()

    def nwrite_(self, s1, s2, n, args={}):
        self.session.conn.write(
            global_.langs[self.vars_['lang']].ngettext(s1, s2, n) % args)
        self.write_prompt()

    def translate(self, s, args={}):
        return global_.langs[self.vars_['lang']].gettext(s) % args

    def write_prompt(self, s=None):
        assert(self.is_online)
        if s:
            self.session.conn.write(s)
        # XXX maybe we shouldn't check this for every line,
        # but instead prevent changing the prompt value when
        # defprompt is set
        if self.session.ivars['defprompt']:
            self.session.conn.write_nowrap(config.prompt)
        else:
            self.session.conn.write_nowrap(self.vars_['prompt'])

    def get_display_name(self):
        assert(self._title_str is not None)
        return '%s%s' % (self.name, self._title_str)

    def __str__(self):
        return self.name

    def has_title(self, title):
        """ Test whether the user has a given title, regardless of whether
        the title light is on or off. """
        assert(self._titles is not None)
        return title in self._titles

    def get_titles(self):
        assert(self._titles is not None)
        return self._titles

    def set_var(self, v, val):
        """ This does not notify the user. """
        # XXX maybe it should?
        if val is not None:
            self.vars_[v.name] = val
        else:
            if v.name in self.vars_:
                del self.vars_[v.name]
        return defer.succeed(None)

    def set_formula(self, v, val):
        self.vars_[v.name] = val
        return defer.succeed(None)

    def set_note(self, v, val):
        num = int(v.name, 10)
        if val is not None:
            self.notes[num] = val
        else:
            if num in self.notes:
                del self.notes[num]
        return defer.succeed(None)

    def insert_note(self, val):
        """Insert a new note as note 1."""
        assert(val is not None)
        for i in range(9, 0, -1):
            try:
                self.notes[i + 1] = self.notes[i]
                del self.notes[i]
            except KeyError:
                pass
        self.notes[1] = val

    def set_alias(self, name, val):
        if val is not None:
            self.aliases[name] = val
        else:
            del self.aliases[name]
        return defer.succeed(None)

    def add_channel(self, id_):
        assert(isinstance(id_, (int, long)))
        self.channels.append(id_)
        self.channels.sort()

    def remove_channel(self, id_):
        assert(isinstance(id_, (int, long)))
        self.channels.remove(id_)

    def set_admin_level(self, level):
        self.admin_level = level
        return defer.succeed(None)

    def is_admin(self):
        return self.admin_level >= admin.Level.admin

    def is_newbie(self):
        # 10 hours
        return self.get_total_time_online() < 36000

    def add_notification(self, user):
        assert(not self.is_guest)
        assert(not user.is_guest)
        self.notifiers.add(user.name)
        if user.is_online:
            user.notified.add(self.name)
            self.session.notifiers_online.add(user)
            user.session.notified_online.add(self)

    def remove_notification(self, user):
        self.notifiers.remove(user.name)
        if user.is_online:
            user.notified.remove(self.name)

    def add_gnotification(self, user):
        self.gnotifiers.add(user.name)
        if user.is_online:
            user.gnotified.add(self.name)

    def remove_gnotification(self, user):
        self.gnotifiers.remove(user.name)
        if user.is_online:
            user.gnotified.remove(self.name)

    def add_idlenotification(self, user):
        """ Inform this user when the given user unidles. """
        assert(self.is_online)
        assert(user.is_online)
        self.session.idlenotifying.add(user)
        user.session.idlenotified_by.add(self)

    def remove_idlenotification(self, user):
        """ Remove a notification added by add_idlenotification. """
        assert(self.is_online)
        assert(user.is_online)
        self.session.idlenotifying.remove(user)
        user.session.idlenotified_by.remove(self)

    def add_censor(self, user):
        self.censor.add(user.name)

    def remove_censor(self, user):
        self.censor.remove(user.name)

    def add_noplay(self, user):
        self.noplay.add(user.name)

    def remove_noplay(self, user):
        self.noplay.remove(user.name)

    def censor_or_noplay(self, b):
        """ Check whether either player censors or noplays the other, without
        printing any messages to the users. """
        a = self
        return (a.name in b.censor or a.name in b.noplay
            or b.name in a.censor or b.name in a.noplay)

    def save_history(self, game_id, result_char, user_rating, color_char,
            opp_name, opp_rating, eco, flags, initial_time, inc,
            result_reason, when_ended, movetext, idn):
        assert(self._history is not None)
        if len(self._history) == 0:
            num = 0
        else:
            num = (self._history[-1]['num'] + 1) % 100
            if len(self._history) == 10:
                self._history = self._history[1:]
        entry = {'game_id': game_id, 'num': num, 'result_char': result_char,
            'user_rating': user_rating, 'color_char': color_char,
            'opp_name': opp_name, 'opp_rating': opp_rating, 'eco': eco,
            'flags': flags, 'time': initial_time, 'inc': inc,
            'result_reason': result_reason, 'when_ended': when_ended,
            'movetext': movetext, 'idn': idn}
        self._history.append(entry)
        return entry

    def clear_history(self):
        self._history = []

    def get_history_game(self, num, conn):
        hist = self.get_history()
        if not hist:
            conn.write(_('%s has no history games.\n') % self.name)
        h = None
        if num < 0:
            if num < -10:
                conn.write(_('There are 10 entries maximum in history.\n'))
                return
            try:
                h = hist[num]
            except IndexError:
                pass
        else:
            matches = [h for h in hist if h['num'] == num]
            assert(len(matches) in [0, 1])
            h = matches[0] if matches else None

        if h:
            assert(h['color_char'] in ['W', 'B'])
            if h['color_char'] == 'W':
                h['white_name'] = self.name
                h['black_name'] = h['opp_name']
                if h['result_char'] == '+':
                    h['result'] = '1-0'
                elif h['result_char'] == '-':
                    h['result'] = '0-1'
                elif h['result_char'] == '=':
                    h['result'] = '1/2-1/2'
                elif h['result_char'] == '*':
                    h['result'] = '*'
                else:
                    raise RuntimeError('unknown result char %s' % h['result_char'])
            else:
                h['white_name'] = h['opp_name']
                h['black_name'] = self.name
                if h['result_char'] == '+':
                    h['result'] = '0-1'
                elif h['result_char'] == '-':
                    h['result'] = '1-0'
                elif h['result_char'] == '=':
                    h['result'] = '1/2-1/2'
                elif h['result_char'] == '*':
                    h['result'] = '*'
                else:
                    raise RuntimeError('unknown result char %s' % h['result_char'])
        else:
            conn.write(_('There is no history game %(num)d for %(name)s.\n') % {'num': num, 'name': self.name})

        return h

    def has_timeseal(self):
        return self.session.use_timeseal or self.session.use_zipseal

    def in_silence(self):
        return self.vars_['silence'] and (self.session.game
            or self.session.observed)

    def hears_channels(self):
        return not self.vars_['chanoff'] and not self.in_silence()

    def format_datetime(self, dt):
        #return dt.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d %H:%M %Z")
        #return dt.strftime("%a %b %e, %H:%M %Z %Y")
        return dt.replace(tzinfo=pytz.utc).astimezone(self.tz).strftime('%Y-%m-%d %H:%M %Z')

    def set_muted(self, val):
        """ Mute or unmute the user (affects all communications). """
        self.is_muted = val

    def set_playbanned(self, val):
        self.is_playbanned = val

# a registered user


class RegUser(BaseUser):
    def __init__(self, u):
        BaseUser.__init__(self)
        # XXX this should be renamed to self.id_
        self.id_ = u['user_id']
        self.name = u['user_name']
        self.passwd_hash = u['user_passwd']
        self.email = u['user_email']
        self.real_name = u['user_real_name']
        self.first_login = u['user_first_login']
        self.last_logout = u['user_last_logout']
        self.admin_level = u['user_admin_level']
        self.is_banned = u['user_banned']
        self.is_notebanned = u['user_notebanned']
        self.is_ratedbanned = u['user_ratedbanned']
        self.is_playbanned = u['user_playbanned']
        self.is_muzzled = u['user_muzzled']
        self.is_cmuzzled = u['user_cmuzzled']
        self.is_muted = u['user_muted']
        self._total_time_online = u['user_total_time_online']
        self.is_guest = False
        self._adjourned = None

    @defer.inlineCallbacks
    def finish_init(self):
        """ This is broken into a separate function because __init__()
        cannot be a generator. """
        self.channels = yield db.user_get_channels(self.id_)
        self.vars_ = yield db.user_get_vars(self.id_,
            global_.var_defaults.get_persistent_var_names())

        self.vars_['formula'] = None
        for num in range(1, 10):
            self.vars_['f' + str(num)] = None

        for f in (yield db.user_get_formula(self.id_)):
            if f['num'] == 0:
                self.vars_['formula'] = f['f']
            else:
                self.vars_['f' + str(f['num'])] = f['f']
        assert('formula' in self.vars_)
        for note in (yield db.user_get_notes(self.id_)):
            self.notes[note['num']] = note['txt']
        self._rating = None
        self.tz = pytz.timezone(self.vars_['tzone'])
        defer.returnValue(None)

    def _get_censor(self):
        if self._censor is None:
            self._censor = set([dbu['user_name'] for dbu in
                db.user_get_censored(self.id_)])
        return self._censor
    _censor = None
    censor = property(fget=_get_censor)

    def get_display_name(self):
        """Get the name displayed for other users, e.g. admin(*)(SR).  Titles
        for which the light is turned off are not included. """
        if self._title_str is None:
            self._load_titles()
        return BaseUser.get_display_name(self)

    def _load_titles(self):
        disp_list = []
        self._titles = set()
        self._on_duty_titles = set()
        for t in db.user_get_titles(self.id_):
            if t['title_flag'] and t['title_light']:
                disp_list.append('(%s)' % t['title_flag'])
                self._on_duty_titles.add(t['title_name'])
            self._titles.add(t['title_name'])
        self._title_str = ''.join(disp_list)

    def toggle_light(self, title_id):
        db.toggle_title_light(self.id_, title_id)
        self._load_titles()

    @defer.inlineCallbacks
    def log_on(self, conn):
        if global_.online.is_online(self.name):
            # assert(self.is_online) # XXX this shows that reorganization is needed
            conn.write(_("**** %s is already logged in; closing the other connection. ****\n" % self.name))
            u = global_.online.find_exact(self.name)
            u.session.conn.write(_("**** %s has arrived; you can't both be logged in. ****\n\n") % self.name)
            #u.session.conn.write(_("**** %s has arrived - you can't both be logged in. ****\n\n") % self.name)
            u.session.conn.loseConnection('logged in again')

        # notify
        self.notified = set([dbu['user_name']
            for dbu in (yield db.user_get_notified(self.id_))])
        self.notifiers = set([dbu['user_name']
            for dbu in (yield db.user_get_notifiers(self.id_))])

        yield BaseUser.log_on(self, conn)

        notify.notify_users(self, arrived=True)

        if not self.first_login:
            yield db.user_set_first_login(self.id_)
            self.first_login = yield db.user_get_first_login(self.id_)

        news = yield db.get_news_since(self.last_logout, is_admin=False)
        if news:
            conn.write(ngettext('There is %d new news item since your last login:\n',
                'There are %d new news items since your last login:\n', len(news))
                % len(news))
            for item in reversed(news):
                conn.write('%4d (%s) %s\n' % (item['news_id'],
                    item['news_date'], item['news_title']))
        else:
            conn.write(_('There are no new news items.\n'))
        conn.write('\n')

        (mcount, ucount) = yield db.get_message_count(self.id_)
        assert(mcount >= 0)
        assert(ucount >= 0)
        conn.write(ngettext('You have %(mcount)d message (%(ucount)d unread).\n',
            'You have %(mcount)d messages (%(ucount)d unread).\n', mcount) %
            {'mcount': mcount, 'ucount': ucount})
        conn.write(_('Use "messages u" to view unread messages and "clearmessages *" to clear all.\n'))

        # gnotify
        self.gnotifiers = set([dbu['user_name']
            for dbu in (yield db.user_get_gnotifiers(self.id_))])
        self.gnotified = set([dbu['user_name']
            for dbu in (yield db.user_get_gnotified(self.id_))])

        for a in (yield db.user_get_aliases(self.id_)):
            self.aliases[a['name']] = a['val']

        #self.censor = set([dbu['user_name'] for dbu in
        #    db.user_get_censored(self.id_)])
        for dbu in (yield db.user_get_noplayed(self.id_)):
            self.noplay.add(dbu['user_name'])

        self.get_history()
        defer.returnValue(None)

    def log_off(self):
        notify.notify_users(self, arrived=False)
        d1 = BaseUser.log_off(self)
        d2 = db.user_add_to_total_time_online(self.id_,
            int(self.session.get_online_time()))
        d3 = db.user_set_last_logout(self.id_)
        return defer.DeferredList([d1, d2, d3])

    def get_log(self):
        return db.user_get_log(self.name)

    def set_admin_level(self, level):
        BaseUser.set_admin_level(self, level)
        return db.user_set_admin_level(self.id_, level)

    @defer.inlineCallbacks
    def set_passwd(self, passwd):
        self.passwd_hash = yield bcrypt.hashpw(passwd, bcrypt.gensalt())
        yield db.user_set_passwd(self.id_, self.passwd_hash)

    def _check_passwd_thread(self, passwd):
        bhash = bcrypt.hashpw(passwd, self.passwd_hash)
        return (bhash == self.passwd_hash)

    # check if an unencrypted password is correct
    @defer.inlineCallbacks
    def check_passwd(self, passwd):
        # don't perform expensive computation on arbitrarily long data
        if not is_legal_passwd(passwd):
            defer.returnValue(False)
        else:
            ret = yield threads.deferToThread(self._check_passwd_thread, passwd)
        defer.returnValue(ret)

    def remove(self):
        return db.user_delete(self.id_)

    @defer.inlineCallbacks
    def set_var(self, v, val):
        BaseUser.set_var(self, v, val)
        if v.is_persistent:
            yield db.user_set_var(self.id_, v.name, val)
        defer.returnValue(None)

    def set_formula(self, v, val):
        BaseUser.set_formula(self, v, val)
        return db.user_set_formula(self.id_, v.name, val)

    def set_note(self, v, val):
        BaseUser.set_note(self, v, val)
        return db.user_set_note(self.id_, v.name, val)

    def insert_note(self, val):
        BaseUser.insert_note(self, val)
        return db.user_insert_note(self.id_, val)

    def set_alias(self, name, val):
        BaseUser.set_alias(self, name, val)
        return db.user_set_alias(self.id_, name, val)

    @defer.inlineCallbacks
    def add_channel(self, chid):
        BaseUser.add_channel(self, chid)
        yield db.channel_add_user(chid, self.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_channel(self, id_):
        BaseUser.remove_channel(self, id_)
        yield db.channel_del_user(id_, self.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_title(self, id_):
        yield db.user_add_title(self.id_, id_)
        self._load_titles()
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_title(self, id_):
        yield db.user_del_title(self.id_, id_)
        self._load_titles()
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_notification(self, user):
        BaseUser.add_notification(self, user)
        if not user.is_guest:
            yield db.user_add_notification(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_notification(self, user):
        BaseUser.remove_notification(self, user)
        if not user.is_guest:
            yield db.user_del_notification(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_gnotification(self, user):
        BaseUser.add_gnotification(self, user)
        if not user.is_guest:
            yield db.user_add_gnotification(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_gnotification(self, user):
        BaseUser.remove_gnotification(self, user)
        if not user.is_guest:
            yield db.user_del_gnotification(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_censor(self, user):
        BaseUser.add_censor(self, user)
        if not user.is_guest:
            yield db.user_add_censor(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_censor(self, user):
        BaseUser.remove_censor(self, user)
        if not user.is_guest:
            yield db.user_del_censor(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_noplay(self, user):
        BaseUser.add_noplay(self, user)
        if not user.is_guest:
            yield db.user_add_noplay(self.id_, user.id_)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def remove_noplay(self, user):
        BaseUser.remove_noplay(self, user)
        if not user.is_guest:
            yield db.user_del_noplay(self.id_, user.id_)
        defer.returnValue(None)

    def get_history(self):
        if self._history is None:
            self._history = [e for e in db.user_get_history(self.id_)]
        return self._history

    @defer.inlineCallbacks
    def get_adjourned(self):
        if self._adjourned is None:
            rows = yield db.get_adjourned(self.id_)
            self._adjourned = list(rows)
        defer.returnValue(self._adjourned)

    def has_title(self, title):
        if self._titles is None:
            self._load_titles()
        return BaseUser.has_title(self, title)

    def on_duty_as(self, title):
        if self._titles is None:
            self._load_titles()
        return title in self._on_duty_titles

    def get_titles(self):
        if self._titles is None:
            self._load_titles()
        return BaseUser.get_titles(self)

    def save_history(self, game_id, result_char, user_rating, color_char,
            opp_name, opp_rating, eco, flags, initial_time, inc,
            result_reason, when_ended, movetext, idn):
        entry = BaseUser.save_history(self, game_id, result_char, user_rating,
            color_char, opp_name, opp_rating, eco, flags, initial_time, inc,
            result_reason, when_ended, movetext, idn)
        db.user_add_history(entry, self.id_)

    def clear_history(self):
        BaseUser.clear_history(self)
        db.user_del_history(self.id_)

    def get_rating(self, speed_variant):
        if self._rating is None:
            self._load_ratings()
        if speed_variant in self._rating:
            return self._rating[speed_variant]
        else:
            return rating.NoRating(is_guest=False)

    def set_rating(self, speed_variant,
            rating, rd, volatility, win, loss, draw, ltime):
        db.user_set_rating(self.id_, speed_variant.speed.id_,
            speed_variant.variant.id_, rating, rd, volatility, win, loss,
            draw, win + loss + draw, ltime)
        self._load_ratings() # TODO: don't reload all ratings

    def del_rating(self, sv):
        if self._rating is not None and sv in self._rating:
            del self._rating[sv]
        return db.user_del_rating(self.id_, sv.speed.id_, sv.variant.id_)

    def _load_ratings(self):
        self._rating = {}
        for row in db.user_get_all_ratings(self.id_):
            sv = speed_variant.from_ids(row['speed_id'],
                row['variant_id'])
            self._rating[sv] = rating.Rating(row['rating'],
                row['rd'], row['volatility'], row['ltime'],
                row['win'], row['loss'], row['draw'], row['best'],
                row['when_best'])

    def set_email(self, email):
        self.email = email
        return db.user_set_email(self.id_, email)

    def set_real_name(self, real_name):
        self.real_name = real_name
        return db.user_set_real_name(self.id_, real_name)

    @defer.inlineCallbacks
    def set_banned(self, val):
        """ Ban or unban this user. """
        self.is_banned = val
        yield db.user_set_banned(self.id_, 1 if val else 0)

    @defer.inlineCallbacks
    def set_muzzled(self, val):
        """ Muzzle or unmuzzle the user (affects shouts). """
        self.is_muzzled = val
        yield db.user_set_muzzled(self.id_, 1 if val else 0)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def set_cmuzzled(self, val):
        """ Cmuzzle or un-cmuzzle the user (affects c-shouts). """
        self.is_cmuzzled = val
        yield db.user_set_cmuzzled(self.id_, 1 if val else 0)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def set_muted(self, val):
        BaseUser.set_muted(self, val)
        yield db.user_set_muted(self.id_, 1 if val else 0)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def set_notebanned(self, val):
        """ Add or remove this user from the noteban list. """
        self.is_notebanned = val
        yield db.user_set_notebanned(self.id_, 1 if val else 0)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def set_ratedbanned(self, val):
        """ Add or remove this user from the ratedban list. """
        self.is_ratedbanned = val
        yield db.user_set_ratedbanned(self.id_, 1 if val else 0)
        defer.returnValue(None)

    @defer.inlineCallbacks
    def set_playbanned(self, val):
        BaseUser.set_playbanned(self, val)
        yield db.user_set_playbanned(self.id_, 1 if val else 0)
        defer.returnValue(None)

    def get_total_time_online(self):
        tot = self._total_time_online
        if self.is_online:
            tot += self.session.get_online_time()
        return tot

    @defer.inlineCallbacks
    def get_adjourned_with(self, u):
        """Get an adjourned game with u, or None if none exists."""
        # This assumes that there is never more than one adjourned
        # game between two users.
        adj_list = yield self.get_adjourned()
        for adj in adj_list:
            if u.id_ in (adj['white_user_id'], adj['black_user_id']):
                defer.returnValue(adj)
                return
        defer.returnValue(None)

    @defer.inlineCallbacks
    def add_adjourned(self, data):
        """Add the given data to the adjourned game list. The adjourned
        game is expected to be added to the DB by the caller."""
        adj_list = yield self.get_adjourned()
        adj_list.append(data)

    @defer.inlineCallbacks
    def remove_adjourned(self, adj):
        """Remove the given game from the adjourned game list.  Raise KeyError
        if no such game."""
        adj_id = adj['adjourn_id']
        adj_list = yield self.get_adjourned()
        for i in range(len(adj_list) - 1, -1, -1):
            if adj_list[i]['adjourn_id'] == adj_id:
                del adj_list[i]
                return
        raise KeyError


class GuestUser(BaseUser):
    def __init__(self, name):
        BaseUser.__init__(self)
        self.is_guest = True
        if name is None:
            count = 0
            while True:
                self.name = 'Guest'
                for i in range(4):
                    self.name = self.name + random.choice(string.ascii_uppercase)
                if not global_.online.is_online(self.name):
                    break
                count = count + 1
                if count > 3:
                    # should not happen
                    raise Exception('Unable to create a guest account!')
            #self.autogenerated_name = True
        else:
            self.name = name
            #self.autogenerated_name = False
        self.admin_level = admin.Level.user
        self.channels = global_.channels.get_default_guest_channels()
        self.vars_ = global_.var_defaults.get_default_vars()
        assert('formula' in self.vars_)
        self.censor = set()
        self.is_muted = False
        self.is_playbanned = False
        self.tz = pytz.timezone(self.vars_['tzone'])

    def log_on(self, conn):
        self._titles = set(['unregistered'])
        self._title_str = '(U)'
        self.notifiers = set()
        self.notified = set()
        self._history = []
        return BaseUser.log_on(self, conn)

    def get_log(self):
        """ The log for a guest has just one entry: the login """
        return [{'log_who_name': self.name,
            'log_when': datetime.datetime.fromtimestamp(self.session.login_time),
            'log_which': 'login', 'log_ip': self.session.conn.ip}]

    def get_history(self):
        assert(self._history is not None)
        return self._history

    def get_rating(self, speed_variant):
        return rating.NoRating(is_guest=True)


# test whether a string meets the requirements for a password
def is_legal_passwd(passwd):
    if len(passwd) > 32:
        return False
    if len(passwd) < 3:
        return False
    # passwords may not contain spaces because they are set
    # using a command
    if not re.match(r'^\S+$', passwd):
        return False
    return True


def make_passwd():
    chars = string.letters + string.digits
    passlen = random.choice(list(range(5, 8)))
    ret = ''
    for i in range(passlen):
        ret = ret + random.choice(chars)
    return ret


@defer.inlineCallbacks
def add_user(name, email, passwd, real_name):
    pwhash = bcrypt.hashpw(passwd, bcrypt.gensalt())
    user_id = yield db.user_add(name, email, pwhash, real_name,
        admin.Level.user)
    for chid in global_.channels.get_default_channels():
        yield db.channel_add_user(chid, user_id)
    defer.returnValue(user_id)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
