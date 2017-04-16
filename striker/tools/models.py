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

from django.conf import settings
from django.core import urlresolvers
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from ldapdb.models import fields
import ldapdb.models


class Maintainer(ldapdb.models.Model):
    """A tool maintainer."""
    base_dn = settings.TOOLS_MAINTAINER_BASE_DN
    object_classes = ['posixAccount']

    username = fields.CharField(db_column='uid', primary_key=True)
    full_name = fields.CharField(db_column='cn')

    def __str__(self):
        return self.username


class ToolManager(models.Manager):
    def get_queryset(self):
        return super(ToolManager, self).get_queryset().filter(
            cn__startswith='tools.')


class Tool(ldapdb.models.Model):
    """A tool is a specially named LDAP group."""
    base_dn = settings.TOOLS_TOOL_BASE_DN
    object_classes = ['posixGroup', 'groupOfNames']

    objects = ToolManager()

    cn = fields.CharField(
        db_column='cn', max_length=200, primary_key=True)
    gid_number = fields.IntegerField(db_column='gidNumber', unique=True)
    members = fields.ListField(db_column='member')

    @property
    def name(self):
        return self.cn[6:]

    @name.setter
    def name(self, value):
        self.cn = 'tools.{0!s}'.format(value)

    def maintainers(self):
        # OMG, this is horrible. You can't search LDAP by dn.
        return Maintainer.objects.filter(
            username__in=(
                dn.split(',')[0].split('=')[1] for dn in self.members))

    def __str__(self):
        return self.name


class DiffusionRepo(models.Model):
    """Associate diffusion repos with Tools."""
    tool = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    phid = models.CharField(max_length=64)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)
    created_date = models.DateTimeField(
        default=timezone.now, blank=True, editable=False)

    def __str__(self):
        return self.name


class AccessRequest(models.Model):
    """Request to join Tools project."""
    PENDING = 'p'
    APPROVED = 'a'
    DECLINED = 'd'
    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (APPROVED, _('Approved')),
        (DECLINED, _('Declined')),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='requestor+', db_index=True)
    reason = models.TextField()
    created_date = models.DateTimeField(
        default=timezone.now, blank=True, editable=False, db_index=True)
    admin_notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=1, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='resolver+',
        blank=True, null=True)
    resolved_date = models.DateTimeField(blank=True, null=True)
    suppressed = models.BooleanField(blank=True, default=False, db_index=True)

    def __str__(self):
        return _('Access request {id}').format(id=self.id)

    def get_absolute_url(self):
        return urlresolvers.reverse(
            'tools:membership_status', args=[str(self.id)])
