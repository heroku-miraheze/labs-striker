# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Wikimedia Foundation and contributors.
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

import functools
import logging

from keystoneauth1 import session as keystone_session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client

from django.conf import settings


logger = logging.getLogger(__name__)


class Client(object):
    """OpenStack client"""
    _default_instance = None

    @classmethod
    def default_client(cls):
        """Get an OpenStack client using the default credentials."""
        if cls._default_instance is None:
            logger.debug('Creating default instance')
            cls._default_instance = cls(
                url=settings.OPENSTACK_URL,
                username=settings.OPENSTACK_USER,
                password=settings.OPENSTACK_PASSWORD,
                project=settings.OPENSTACK_PROJECT,
            )
        return cls._default_instance

    def __init__(self, url, username, password, project):
        self.url = url
        self.username = username
        self.password = password
        self.project = project
        self.roles = None

    @functools.lru_cache(maxsize=None)
    def _session(self, project=None):
        project = project or self.project
        auth = v3.Password(
            auth_url=self.url,
            password=self.password,
            username=self.username,
            project_id=project,
            user_domain_name='Default',
            project_domain_name='Default',
        )
        return keystone_session.Session(auth=auth)

    @functools.lru_cache(maxsize=None)
    def _client(self, project=None):
        project = project or self.project
        return client.Client(
            session=self._session(project),
            interface='public',
            timeoute=2,
        )

    def role(self, name):
        if self.roles is None:
            keystone = self._client()
            self.roles = {r.name: r for r in keystone.roles.list()}
        return self.roles[name]

    def grant_role(self, role, user, project=None):
        project = project or self.project
        keystone = self._client(project)
        keystone.roles.grant(self.role(role), user, project=project)

    def revoke_role(self, role, user, project=None):
        project = project or self.project
        keystone = self._client(project)
        keystone.roles.revoke(role, user, project=project)
