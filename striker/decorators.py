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

import functools

from django import shortcuts
from django import template


def confirm_required(template_name, context_builder=None, key='__confirm__'):
    """Decorate a view that requires confirmation."""
    def decorator(f):
        @functools.wraps(f)
        def decorated(request, *args, **kwargs):
            if key in request.POST:
                return f(request, *args, **kwargs)
            if context_builder is not None:
                ctx = context_builder(request, *args, **kwargs)
            else:
                ctx = template.RequestContext(request)
            return shortcuts.render_to_response(template_name, ctx)
        return decorated
    return decorator