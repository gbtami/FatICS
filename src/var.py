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

import copy
import pytz
import datetime

import formula
import global_
import partner
import config

ivar_number = {}


class BadVarError(Exception):
    pass


def _set_nowrap(user, val):
    """ Called when the nowrap ivar is set. """
    if val:
        user.session.conn.transport.disableWrapping()
    else:
        user.session.conn.transport.enableWrapping(user.vars_['width'])


def _set_pin_ivar(user, val):
    """ Called when the pin ivar is set. """
    if val:
        global_.online.pin_ivar.add(user)
    else:
        if user in global_.online.pin_ivar:
            global_.online.pin_ivar.remove(user)


def _set_pin_var(user, val):
    """ Called when the pin var is set. """
    if val:
        global_.online.pin_var.add(user)
    else:
        if user in global_.online.pin_var:
            global_.online.pin_var.remove(user)


def _set_gin_var(user, val):
    """ Called when the gin var is set. """
    if val:
        global_.online.gin_var.add(user)
    else:
        if user in global_.online.gin_var:
            global_.online.gin_var.remove(user)


def _set_open_var(u, val):
    if not val:
        for offer in u.session.offers_sent[:]:
            if offer.name == 'match offer':
                offer.withdraw_open()
        for offer in u.session.offers_received[:]:
            if offer.name == 'match offer':
                offer.decline_open()
    if u.session.partner:
        if val:
            # original FICS doesn't seem to notify in this case, but
            # it seems logical to do so
            u.session.partner.write_('\nYour partner has become available for matches.\n')
        else:
            u.session.partner.write_('\nYour partner has become unavailable for matches.\n')


def _set_bugopen_var(u, val):
    if not val:
        # end any partnerships and partnership requests
        for offer in u.session.offers_sent[:]:
            if offer.name == 'partnership request':
                offer.b.write_('\n%s, who was offering a partnership with you, has become unavailable for bughouse.\n', u.name)
                offer.withdraw(notify=False)
                u.write(_("Partnership offer to %s withdrawn.\n")
                    % offer.b.name)
                offer.b.write_("\nPartnership offer from %s removed.\n", u.name)
        for offer in u.session.offers_received[:]:
            if offer.name == 'partnership request':
                offer.a.write_('\n%s, whom you were offering a partnership with, has become unavailable for bughouse.\n', u.name)
                offer.withdraw(notify=False)
                u.write(_("Partnership offer from %s removed.\n") %
                    offer.a.name)
                offer.a.write_("\nPartnership offer to %s withdrawn.\n", u.name)
        if u.session.partner:
            u.session.partner.write_('\nYour partner has become unavailable for bughouse.\n')
            partner.end_partnership(u, u.session.partner)


class Var(object):
    """This class represents the form of a variable but does not hold
    a specific value.  For example, the server has one global instance of
    this class (actually, a subclass of this class) for the "tell" variable,
    not a separate instance for each user."""
    def __init__(self, name, default):
        assert(name == name.lower())
        self.name = name
        self.default = default
        #self.db_store = lambda user_id, name, val: None
        self.is_persistent = False
        self.is_formula_or_note = False
        self._hook = None
        # display in vars output

    def add_as_var(self):
        global_.vars_[self.name] = self
        if self.is_persistent:
            global_.var_defaults.default_vars[self.name] = self.default
            if not self.is_formula_or_note:
                global_.var_defaults.persistent_vars.add(self.name)
        else:
            global_.var_defaults.transient_vars[self.name] = self.default
        self.is_ivar = False
        return self

    def add_as_ivar(self, number=None):
        global_.ivars[self.name] = self
        global_.var_defaults.default_ivars[self.name] = self.default
        if number is not None:
            ivar_number[number] = self
        self.is_ivar = True
        return self

    def persist(self):
        """Make a variable persistent with the given key in the
        user table."""
        self.is_persistent = True
        return self

    def set_hook(self, func):
        """ Register a function to be called when this variable or ivariable
        is set or unset. """
        self._hook = func

    # XXX this should probably be renamed to set_
    @defer.inlineCallbacks
    def set(self, user, val):
        """ This checks whether the given value for a var is legal and
        sets a user's value of the var.  Returns the message to display to
        the user. On an error, raises BadVarError. """
        if self._hook:
            self._hook(user, val)


class StringVar(Var):
    def __init__(self, name, default, max_len=1023):
        Var.__init__(self, name, default)
        self.max_len = max_len

    @defer.inlineCallbacks
    def set(self, user, val):
        if val is not None and len(val) > self.max_len:
            raise BadVarError()
        if self.is_ivar:
            user.session.set_ivar(self, val)
        else:
            yield user.set_var(self, val)
        if val is None:
            user.write(_('''%s unset.\n''') % self.name)
        else:
            user.write((_('''%(name)s set to "%(val)s".\n''')
                % {'name': self.name, 'val': val}))
        if self._hook:
            self._hook(user, val)


class PromptVar(StringVar):
    @defer.inlineCallbacks
    def set(self, user, val):
        if val is not None and len(val) > self.max_len - 1:
            raise BadVarError()
        assert(not self.is_ivar)
        if val is None:
            val = config.prompt
        else:
            val += ' '

        yield user.set_var(self, val)
        user.write((_('''%(name)s set to "%(val)s".\n''') % {'name': self.name, 'val': val}))


class LangVar(StringVar):
    @defer.inlineCallbacks
    def set(self, user, val):
        if val not in global_.langs:
            raise BadVarError()
        assert(not self.is_ivar)
        yield user.set_var(self, val)
        # Start using the new language right away.
        global_.langs[val].install(names=['ngettext'])
        user.write(_('''%(name)s set to "%(val)s".\n''') % {'name': self.name, 'val': val})


class FormulaVar(Var):
    max_len = 1023

    def __init__(self, num):
        name = 'formula' if num == 0 else 'f' + str(num)
        super(FormulaVar, self).__init__(name, None)
        self.num = num
        self.is_formula_or_note = True

    @defer.inlineCallbacks
    def set(self, user, val):
        if val is None:
            yield user.set_formula(self, val)
            user.write(_('''%s unset.\n''') % self.name)
        else:
            if len(val) > self.max_len:
                raise BadVarError()
            try:
                formula.check_formula(None, val, self.num)
            except formula.FormulaError:
                raise BadVarError()
            yield user.set_formula(self, val)
            user.write((_('''%(name)s set to "%(val)s".\n''') % {'name': self.name, 'val': val}))


class NoteVar(Var):
    max_len = 1023

    def __init__(self, name, default):
        Var.__init__(self, name, default)
        self.is_formula_or_note = True

    @defer.inlineCallbacks
    def set(self, user, val):
        if val is not None and len(val) > self.max_len:
            raise BadVarError()
        if self.name == '0':
            # special case: insert note at position 1
            if val is None:
                val = ''
            yield user.insert_note(val)
            user.write(_("Inserted line 1 '%s'.\n") % val)
            return
        if val is None and int(self.name) not in user.notes:
            # XXX would it be better to raise an exception?
            user.write(_('''You do not have that many lines set.\n'''))
            return
        yield user.set_note(self, val)
        if val is None:
            user.write(_('''Note %s cleared.\n''') % self.name)
        else:
            user.write((_('''Note %(name)s set: %(val)s\n''') %
                {'name': self.name, 'val': val}))


class TzoneVar(Var):
    @defer.inlineCallbacks
    def set(self, user, val):
        if val is None:
            val = 'UTC'
        elif val not in pytz.common_timezones:
            raise BadVarError()
        user.tz = pytz.timezone(val)
        yield user.set_var(self, val)
        if val == 'UTC':
            info = ''
        else:
            info = datetime.datetime.utcnow().replace(
                tzinfo=pytz.utc).astimezone(user.tz).strftime(' (%Z, UTC%z)')
        user.write(_('''Time zone set to "%(val)s"%(info)s.\n''') %
            {'val': val, 'info': info})


class IntVar(Var):
    """An integer variable."""
    def __init__(self, name, default, min=-99999, max=99999):
        Var.__init__(self, name, default)
        self.min = min
        self.max = max

    @defer.inlineCallbacks
    def set(self, user, val):
        try:
            val = int(val, 10)
        except ValueError:
            raise BadVarError()
        if val < self.min or val > self.max:
            raise BadVarError()
        if self.is_ivar:
            user.session.set_ivar(self, val)
        else:
            yield user.set_var(self, val)
        if self.name == 'style':
            user.write(_('''Style %s set.\n''') % val)
        else:
            user.write(_("%(name)s set to %(val)s.\n") % {'name': self.name, 'val': val})
        if self._hook:
            self._hook(user, val)


class BoolVar(Var):
    """ A boolean variable. """
    def __init__(self, name, default, on_msg=None, off_msg=None):
        Var.__init__(self, name, default)

        self.on_msg = on_msg
        self.off_msg = off_msg

    @defer.inlineCallbacks
    def set(self, user, val):
        if val is None:
            # toggle
            if self.is_ivar:
                val = not user.session.ivars[self.name]
            else:
                val = not user.vars_[self.name]
        else:
            val = val.lower()
            if val == 'on':
                val = '1'
            elif val == 'off':
                val = '0'
            elif val not in ['0', '1']:
                raise BadVarError()
            val = int(val, 10)
        if self.is_ivar:
            user.session.set_ivar(self, val)
        else:
            yield user.set_var(self, val)
        if val:
            if self.on_msg is not None:
                user.write(_(self.on_msg))
            else:
                user.write(_(("%s set.\n") % self.name))
        else:
            if self.off_msg is not None:
                user.write(_(self.off_msg))
            else:
                user.write(_("%s unset.\n") % self.name)
        if self._hook:
            self._hook(user, val)


def init_vars():
    BoolVar("shout", True, N_("You will now hear shouts.\n"), N_("You will not hear shouts.\n")).persist().add_as_var()
    BoolVar("cshout", True, N_("You will now hear cshouts.\n"), N_("You will not hear cshouts.\n")).persist().add_as_var()
    BoolVar("tell", True, N_("You will now hear direct tells from unregistered users.\n"), N_("You will not hear direct tells from unregistered users.\n")).persist().add_as_var()
    BoolVar("ctell", True, N_("You will now hear channel tells from unregistered users.\n"), N_("You will not hear channel tells from unregistered users.\n")).persist().add_as_var()
    BoolVar("chanoff", False, N_("You will not hear channel tells.\n"), N_("You will now hear channel tells.\n")).persist().add_as_var()

    BoolVar("open", True, N_("You are now receiving match requests.\n"), N_("You are no longer receiving match requests.\n")).persist().add_as_var().set_hook(_set_open_var)
    BoolVar("bugopen", False, N_("You are now open for bughouse.\n"), N_("You are not open for bughouse.\n")).persist().add_as_var().set_hook(_set_bugopen_var)
    BoolVar("silence", False, N_("You will now play games in silence.\n"), N_("You will not play games in silence.\n")).persist().add_as_var()
    BoolVar("bell", True, N_("You will now hear beeps.\n"), N_("You will not hear beeps.\n")).persist().add_as_var()
    BoolVar("autoflag", True, N_("Auto-flagging enabled.\n"), N_("Auto-flagging disabled.\n")).persist().add_as_var()
    BoolVar("ptime", False, N_("Your prompt will now show the time.\n"), N_("Your prompt will now not show the time.\n")).persist().add_as_var()
    BoolVar("kibitz", True, N_("You will now hear kibitzes.\n"), N_("You will not hear kibitzes.\n")).persist().add_as_var()
    BoolVar("notifiedby", True, N_("You will now hear if people notify you, but you don't notify them.\n"), N_("You will not hear if people notify you, but you don't notify them.\n")).persist().add_as_var()
    BoolVar("minmovetime", True, N_("You will request minimum move time when games start.\n"), N_("You will not request minimum move time when games start.\n")).persist().add_as_var()
    BoolVar("noescape", True, N_("You will request noescape when games start..\n"), N_("You will not request noescape when games start.\n")).persist().add_as_var()
    BoolVar("seek", True, N_("You will now see seek ads.\n"), N_("You will not see seek ads.\n")).persist().add_as_var()
    #BoolVar("echo", True, N_("You will not hear communications echoed.\n"), N_("You will now not hear communications echoed.\n")).persist().add_as_var()
    BoolVar("examine", False, N_("You will now enter examine mode after a game.\n"), N_("You will now not enter examine mode after a game.\n")).persist().add_as_var()
    BoolVar("mailmess", False, N_("Your messages will be mailed to you.\n"), N_("Your messages will not be mailed to you.\n")).persist().add_as_var()
    BoolVar("messreply", False, N_("Players can now respond to your messages by email.\n"), N_("Players cannot respond to your messages by email.\n")).persist().add_as_var()
    BoolVar("showownseek", False, N_("You will now see your own seeks.\n"), N_("You will not see your own seeks.\n")).persist().add_as_var()
    BoolVar("pin", False, N_("You will now hear logins/logouts.\n"), N_("You will not hear logins/logouts.\n")).persist().add_as_var().set_hook(_set_pin_var)
    BoolVar("gin", False, N_("You will now hear game results.\n"), N_("You will not hear game results.\n")).persist().add_as_var().set_hook(_set_gin_var)
    BoolVar("notakeback", False, N_("You will not allow takebacks.\n"), N_("You will now allow takebacks.\n")).persist().add_as_var()
    # TODO: highlight

    # not persistent
    BoolVar("tourney", False, N_("Your tournament variable is now set.\n"), N_("Your tournament variable is no longer set.\n")).add_as_var()
    BoolVar("flip", False, N_("Flip on.\n"), N_("Flip off.\n")).add_as_var()
    BoolVar("hideinfo", False, N_("Private user information now not shown.\n"), N_("Private user information now shown.\n")).persist().add_as_var()

    IntVar("time", 2, min=0).persist().add_as_var()
    IntVar("inc", 12, min=0).persist().add_as_var()
    IntVar("height", 24, min=5, max=240).persist().add_as_var()
    IntVar("width", 79, min=32, max=240).persist().add_as_var()

    IntVar("style", 1, min=1, max=12).persist().add_as_var()
    IntVar("kiblevel", 0, min=0, max=9999).add_as_var()
    StringVar("interface", None).add_as_var()
    StringVar("busy", None).add_as_var()
    PromptVar("prompt", config.prompt).add_as_var()

    LangVar("lang", "en").persist().add_as_var()

    for i in range(0, 10):
        FormulaVar(i).persist().add_as_var()

    # 0 is a pseudo-var used to insert new notes
    NoteVar('0', None).add_as_var()
    for i in range(1, 11):
        NoteVar(str(i), None).persist().add_as_var()

    TzoneVar("tzone", "UTC").persist().add_as_var()


def init_ivars():
    # "help iv_list" on original FICS has this list
    BoolVar("compressmove", False).add_as_ivar(0)
    BoolVar("audiochat", False).add_as_ivar(1)
    BoolVar("seekremove", False).add_as_ivar(2)
    BoolVar("defprompt", False).add_as_ivar(3)
    BoolVar("lock", False).add_as_ivar(4)
    BoolVar("startpos", False).add_as_ivar(5)
    BoolVar("block", False).add_as_ivar(6)
    BoolVar("gameinfo", False).add_as_ivar(7)
    BoolVar("xdr", False).add_as_ivar(8)  # ignored, possibly related to xml
    BoolVar("pendinfo", False).add_as_ivar(9)
    BoolVar("graph", False).add_as_ivar(10)
    BoolVar("seekinfo", False).add_as_ivar(11)
    BoolVar("extascii", False).add_as_ivar(12)
    BoolVar("nohighlight", False).add_as_ivar(13)
    BoolVar("vthighlight", False).add_as_ivar(14)
    BoolVar("showserver", False).add_as_ivar(15)
    BoolVar("pin", False).add_as_ivar(16).set_hook(_set_pin_ivar)
    BoolVar("ms", False).add_as_ivar(17)
    BoolVar("pinginfo", False).add_as_ivar(18)
    BoolVar("boardinfo", False).add_as_ivar(19)
    BoolVar("extuserinfo", False).add_as_ivar(20)
    BoolVar("seekca", False).add_as_ivar(21)
    BoolVar("showownseek", True).add_as_ivar(22)
    BoolVar("premove", False).add_as_ivar(23)
    BoolVar("smartmove", False).add_as_ivar(24)
    BoolVar("movecase", False).add_as_ivar(25)
    BoolVar("suicide", False).add_as_ivar(26)
    BoolVar("crazyhouse", False).add_as_ivar(27)
    BoolVar("losers", False).add_as_ivar(28)
    BoolVar("wildcastle", False).add_as_ivar(29)
    BoolVar("fr", False).add_as_ivar(30)
    BoolVar("nowrap", False).add_as_ivar(31).set_hook(_set_nowrap)
    BoolVar("allresults", False).add_as_ivar(32)
    BoolVar("obsping", False).add_as_ivar(33)  # ignored
    BoolVar("singleboard", False).add_as_ivar(34)

    # This one does not seem to have a number.
    BoolVar("atomic", True).add_as_ivar()

    # The original FICS ivariables command displays "xml=0", but
    # does not allow setting an xml ivariable.


class Defaults(object):
    default_ivars = {}
    default_vars = {}
    transient_vars = {}
    persistent_vars = set()

    def get_persistent_var_names(self):
        """ For reading a user's vars from the database;
        does not include formula variables. """
        return copy.copy(self.persistent_vars)

    def get_default_vars(self):
        return copy.copy(self.default_vars)

    def get_transient_vars(self):
        return copy.copy(self.transient_vars)

    def get_default_ivars(self):
        return copy.copy(self.default_ivars)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
