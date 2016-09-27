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
import json

from django import http
from django import shortcuts
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.exceptions import SuspiciousOperation
from django.template import loader
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.http import require_POST

import striker.labsauth.models
import striker.tools.models


logger = logging.getLogger(__name__)


def index(req):
    tools_count = cache.get('tools_count')
    if tools_count is None:
        tools_count = striker.tools.models.Tool.objects.count()
        cache.set('tools_count', tools_count, 900)

    maintainers_count = cache.get('maintainers_count')
    if maintainers_count is None:
        maintainers_count = len(
            striker.labsauth.models.PosixGroup.objects.get(
                cn=settings.TOOLS_TOOL_LABS_GROUP_NAME).members)
        cache.set('maintainers_count', maintainers_count, 900)

    ctx = {
        'tools_count': tools_count,
        'maintainers_count': maintainers_count,
    }
    return shortcuts.render(req, 'index.html', ctx)


@require_POST
@csrf_exempt
def csp_report(req):
    # Adapted from https://github.com/adamalton/django-csp-reports/
    resp = http.HttpResponse('')
    raw_report = req.body
    if isinstance(raw_report, bytes):
        raw_report = raw_report.decode('utf-8')
    try:
        report = json.loads(raw_report)
    except ValueError:
        # Ignore malformed reports
        pass
    else:
        if 'csp-report' not in report:
            return resp

        if 'line-number' not in report['csp-report']:
            return resp

        if report['csp-report']['line-number'] == 1:
            # Ignore reports of errors on line 1. This is a common signature
            # for CSP errors triggered by client controlled code (e.g. browser
            # plugins that inject CSS/JS into all pages).
            return resp

        logger.info('Content Security Policy violation: %s', raw_report)
    return resp


@requires_csrf_token
def page_not_found(request, template_name='404.html'):
    ctx = {'request_path': request.path}
    context = RequestContext(request, ctx)
    t = loader.get_template(template_name)
    return http.HttpResponseNotFound(t.render(context))


@requires_csrf_token
def server_error(request, template_name='500.html'):
    ctx = {
        'request_path': request.path,
        'request_id': request.id,
    }
    context = RequestContext(request, ctx)
    t = loader.get_template(template_name)
    return http.HttpResponseServerError(t.render(context))


@requires_csrf_token
def bad_request(request, template_name='400.html'):
    ctx = {
        'request_path': request.path,
        'request_id': request.id,
    }
    context = RequestContext(request, ctx)
    t = loader.get_template(template_name)
    return http.HttpResponseBadRequest(t.render(context))


@requires_csrf_token
def permission_denied(request, template_name='403.html'):
    ctx = {
        'request_path': request.path,
        'request_id': request.id,
    }
    context = RequestContext(request, ctx)
    t = loader.get_template(template_name)
    return http.HttpResponseBadRequest(t.render(context))


def force_400(request):
    raise SuspiciousOperation(
        'This is just a test of raising SuspiciousOperation')


def force_403(request):
    raise PermissionDenied(
        'This is just a test of raising PermissionDenied')


def force_500(request):
    raise Exception('This is just a test of raising an unhandled error.')
