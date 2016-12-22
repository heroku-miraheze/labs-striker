# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Wikimedia Foundation and contributors.
# All Rights Reserved.
#
# This file is part of Striker.
#
# Striker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Striker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Striker.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import urls
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required


urlpatterns = [
    urls.url(
        r'^nojs/$',
        login_required(
            TemplateView.as_view(template_name='profile/nojs.html')),
        name='nojs'
    ),
    urls.url(
        r'^settings/accounts$',
        'striker.profile.views.accounts',
        name='accounts'
    ),
    urls.url(
        r'^settings/phabricator/attach$',
        'striker.profile.views.phab_attach',
        name='phabricator_attach'
    ),
    urls.url(
        r'^settings/ssh-keys$',
        'striker.profile.views.ssh_keys',
        name='ssh_keys'
    ),
    urls.url(
        r'^settings/ssh-keys/delete$',
        'striker.profile.views.ssh_key_delete',
        name='ssh_key_delete'
    ),
    urls.url(
        r'^settings/ssh-keys/add$',
        'striker.profile.views.ssh_key_add',
        name='ssh_key_add'
    ),
    urls.url(
        r'^settings/change_password$',
        'striker.profile.views.change_password',
        name='change_password'
    ),
]
