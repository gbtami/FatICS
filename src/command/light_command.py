from twisted.internet import defer

import global_
import admin

from .command import Command, ics_command, requires_registration


@ics_command('admin', '', admin.Level.admin)
class Admin(Command):
    # requires registration because I did not implement light toggling
    # for guest admins; the concept of a guest admin is a weird case
    @requires_registration
    @defer.inlineCallbacks
    def run(self, args, conn):
        title_id = global_.lists['admin'].id_
        yield conn.user.toggle_light(title_id)
        # ugly hack
        if '(*)' in conn.user.get_display_name():
            conn.write(A_('Admin mode (*) is now shown.\n'))
        else:
            conn.write(A_('Admin mode (*) is now not shown.\n'))


@ics_command('sr', '', admin.Level.user)
class Sr(Command):
    @requires_registration
    @defer.inlineCallbacks
    def run(self, args, conn):
        if not conn.user.has_title('SR'):
            conn.write('You do not have permission to access that command.\n')
            return
        title_id = global_.lists['sr'].id_
        yield conn.user.toggle_light(title_id)
        if '(SR)' in conn.user.get_display_name():
            conn.write(A_('Service Representative mode (SR) is now shown.\n'))
        else:
            conn.write(A_('Service Representative mode (SR) is now not shown.\n'))


@ics_command('tm', '', admin.Level.user)
class Tm(Command):
    @requires_registration
    @defer.inlineCallbacks
    def run(self, args, conn):
        if not conn.user.has_title('TM'):
            conn.write('You do not have permission to access that command.\n')
            return
        title_id = global_.lists['tm'].id_
        yield conn.user.toggle_light(title_id)
        if '(TM)' in conn.user.get_display_name():
            conn.write(A_('Tournament Manager mode (TM) is now shown.\n'))
        else:
            conn.write(A_('Tournament Manager mode (TM) is now not shown.\n'))

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
