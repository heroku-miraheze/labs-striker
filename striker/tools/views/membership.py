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

import logging

from django import shortcuts
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core import paginator
from django.core import urlresolvers
from django.db.utils import DatabaseError
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from notifications.signals import notify

from striker import mediawiki
from striker import openstack
from striker.tools import cache
from striker.tools.forms import AccessRequestAdminForm
from striker.tools.forms import AccessRequestForm
from striker.tools.models import AccessRequest
from striker.tools.utils import project_member


WELCOME_MSG = "== Welcome to Toolforge! ==\n{{subst:ToolsGranted}}"
WELCOME_SUMMARY = 'Welcome to Toolforge!'

logger = logging.getLogger(__name__)
openstack = openstack.Client.default_client()


class HttpResponseSeeOther(HttpResponseRedirect):
    """HTTP redirect response with 303 status code"""
    status_code = 303


def see_other(to, *args, **kwargs):
    """Redirect to another page with 303 status code."""
    return HttpResponseSeeOther(shortcuts.resolve_url(to, *args, **kwargs))


def membership(req):
    """Show access requests."""
    ctx = {
        'o': req.GET.get('o', '-created_date'),
        'cols': [
            {'field': 'created_date', 'label': 'Created'},
            {'field': 'user', 'label': 'User'},
            {'field': 'status', 'label': 'Status'},
        ],
    }
    if req.user.is_staff:
        all_requests = AccessRequest.objects.all()
    else:
        all_requests = AccessRequest.objects.filter(suppressed=False)
    all_requests = all_requests.order_by(ctx['o'])
    pager = paginator.Paginator(all_requests, 25)
    page = req.GET.get('p', 1)
    try:
        access_requests = pager.page(page)
    except paginator.PageNotAnInteger:
        access_requests = pager.page(1)
    except paginator.EmptyPage:
        access_requests = pager.page(pager.num_pages)
    ctx['access_requests'] = access_requests
    return shortcuts.render(req, 'tools/membership.html', ctx)


@login_required
def apply(req):
    """Request membership in the Tools project."""
    if project_member(req.user):
        messages.error(
            req, _('You are already a member of Toolforge'))
        return see_other(urlresolvers.reverse('tools:index'))

    pending = AccessRequest.objects.filter(
            user=req.user, status=AccessRequest.PENDING)
    if pending:
        return see_other(
            urlresolvers.reverse(
                'tools:membership_status', args=[pending[0].id]))

    form = AccessRequestForm(req.POST or None, req.FILES or None)
    if req.method == 'POST':
        if form.is_valid():
            try:
                request = form.save(commit=False)
                request.user = req.user
                request.save()
                notify.send(
                    recipient=Group.objects.get(name='tools.admin'),
                    sender=req.user,
                    verb=_('created'),
                    target=request,
                    public=False,
                    description=request.reason,
                    level='info',
                    actions=[
                        {
                            'title': _('View request'),
                            'href': request.get_absolute_url(),
                        },
                    ],
                )
                messages.info(
                    req, _("Toolforge membership request submitted"))
                return shortcuts.redirect(urlresolvers.reverse('tools:index'))
            except DatabaseError:
                logger.exception('AccessRequest.save failed')
                messages.error(
                    req,
                    _("Error updating database. [req id: {id}]").format(
                        id=req.id))
    return shortcuts.render(req, 'tools/membership/apply.html', {'form': form})


def status(req, app_id):
    """Show access request status and allow editing if authorized."""
    request = shortcuts.get_object_or_404(AccessRequest, pk=app_id)
    form = None
    as_admin = False
    if req.user == request.user and request.status == AccessRequest.PENDING:
        # An applicant can amend their own request while it is pending
        form = AccessRequestForm(
                req.POST or None, req.FILES or None, instance=request)
    elif req.user.is_staff:
        # TODO: guard condition will need changing if/when striker handles
        # more than tools
        as_admin = True
        form = AccessRequestAdminForm(
                req.POST or None, req.FILES or None, instance=request)

    if form is not None and req.method == 'POST':
        if form.is_valid() and form.has_changed():
            try:
                request = form.save(commit=False)
                if as_admin:
                    if request.status == AccessRequest.APPROVED:
                        openstack.grant_role(
                            settings.OPENSTACK_USER_ROLE,
                            request.user.shellname,
                        )
                        mwapi = mediawiki.Client.default_client()
                        talk = mwapi.user_talk_page(request.user.ldapname)
                        msg = '{}\n{}'.format(
                            talk.text(), WELCOME_MSG).strip()
                        talk.save(msg, summary=WELCOME_SUMMARY, bot=False)
                        cache.purge_openstack_users()

                    if request.status != AccessRequest.PENDING:
                        request.resolved_by = req.user
                        request.resolved_date = timezone.now()
                    else:
                        request.resolved_by = None
                        request.resolved_date = None
                request.save()

                if as_admin:
                    recipient = request.user
                    verb = _('commented on')
                    description = request.admin_notes
                    level = 'info'
                    if request.status != AccessRequest.PENDING:
                        verb = request.get_status_display().lower()
                        if request.status == AccessRequest.APPROVED:
                            level = 'success'
                        else:
                            level = 'warning'
                else:
                    recipient = Group.objects.get(name='tools.admin')
                    verb = _('updated')
                    description = request.reason
                    level = 'info'

                notify.send(
                    recipient=recipient,
                    sender=req.user,
                    verb=verb,
                    target=request,
                    public=False,
                    description=description,
                    level=level,
                    actions=[
                        {
                            'title': _('View request'),
                            'href': request.get_absolute_url(),
                        },
                    ],
                )

                messages.info(
                    req, _("Toolforge membership request updated"))
                return shortcuts.redirect(
                    urlresolvers.reverse(
                        'tools:membership_status', args=[request.id]))
            except DatabaseError:
                logger.exception('AccessRequest.save failed')
                messages.error(
                    req,
                    _("Error updating database. [req id: {id}]").format(
                        id=req.id))
    ctx = {
        'app': request,
        'form': form,
        'wikitech': settings.WIKITECH_URL,
        'meta': settings.OAUTH_MWURL,
    }
    return shortcuts.render(req, 'tools/membership/status.html', ctx)