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

import global_


def notify_users(user, arrived):
    """ Send a message to all users notified about the given user. """

    assert(not user.is_guest)
    name = user.name
    # notify of adjourned games
    adjourned_opps = []
    if arrived:
        nlist = user.session.notifiers_online
        if nlist:
            user.write(_('Present company includes: %s\n')
                % ' '.join((n.name for n in nlist)))

        # XXX don't call DB here
        for adj in user.adjourned:
            if adj['white_user_id'] == user.id:
                opp_name = adj['black_name']
            else:
                assert(adj['black_user_id'] == user.id)
                opp_name = adj['white_name']
            assert(opp_name)
            opp = global_.online.find_exact(opp_name)
            if opp:
                opp.write_('\nNotification: %s, who has an adjourned game with you, has arrived.\n', (name,))
                adjourned_opps.append(opp_name)
        if adjourned_opps:
            user.nwrite_('%d player who has an adjourned game with you is online: %s\n',
            '%d players who have an adjourned game with you are online: %s\n',
            len(adjourned_opps), (len(adjourned_opps), ' '.join(adjourned_opps)))

    nlist = user.session.notified_online
    for u in nlist:
        if arrived:
            if u.name not in adjourned_opps:
                u.write_("\nNotification: %s has arrived.\n", name)
        else:
            u.write_("\nNotification: %s has departed.\n", name)

    if user.vars_['notifiedby']:
        if arrived:
            user.write(_('The following players were notified of your arrival: %s\n')
                % ' '.join((n.name for n in nlist)))
        else:
            user.write(_('The following players were notified of your departure: %s\n')
                % ' '.join((n.name for n in nlist)))

    for u in user.session.notifiers_online - nlist:
        if u.vars_['notifiedby']:
            if arrived:
                u.write_("\nNotification: %s has arrived and isn't on your notify list.\n", name)
            else:
                u.write_("\nNotification: %s has departed and isn't on your notify list.\n", name)


def notify_pin(user, arrived):
    """ Notify users who have the pin variable or ivariable set. """
    if global_.online.pin_ivar:
        if arrived:
            pin_ivar_str = '\n<wa> %s 001222 1326P1169P0P0P0P0P0P0P\n' % user.name
        else:
            pin_ivar_str = '\n<wd> %s\n' % user.name
        for u in global_.online.pin_ivar:
            u.write_nowrap(pin_ivar_str, prompt=True)

    if global_.online.pin_var:
        if arrived:
            pin_var_str = '\n[%s has connected.]\n' % user.name
            if user.is_guest:
                reg_flag = 'U'
            else:
                reg_flag = 'R'
            admin_pin_var_str = '\n[%s (%s: %s) has connected.]\n' % (user.name, reg_flag, user.session.conn.ip)
        else:
            pin_var_str = '\n[%s has disconnected.]\n' % user.name
        for u in global_.online.pin_var:
            if u.is_admin() and arrived:
                u.write_nowrap(admin_pin_var_str, prompt=True)
            else:
                u.write_nowrap(pin_var_str, prompt=True)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
