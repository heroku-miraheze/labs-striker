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

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from parsley.decorators import parsleyfy

from striker.register import utils


logger = logging.getLogger(__name__)


@parsleyfy
class LDAPUsername(forms.Form):
    IN_USE = _('Username is already in use.')
    username = forms.CharField(
        label=_('Username'),
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Enter your desired username'),
                'autofocus': 'autofocus',
                # Parsley gets confused if {value} is url encoded, so wrap in
                # mark_safe().
                # FIXME: I tried everything I could think of to use
                # urlresolvers.reverse_lazy and I just couldn't get it to work
                # with mark_safe(). I would get either the URL encoded
                # property value or the __str__ of a wrapper object.
                'data-parsley-remote': mark_safe(
                    '/register/api/username/{value}'),
                'data-parsley-trigger': 'focusin focusout input',
                'data-parsley-remote-message': IN_USE,
            }
        ),
        max_length=255,
        required=True,
        # Ultimately we will validate the account name using the MediaWiki
        # API, but these rules will give the user quicker feedback on easy to
        # catch errors.
        validators=[
            validators.RegexValidator(
                regex='^\S',
                message=_('Must not start with whitespace')
            ),
            validators.RegexValidator(
                regex='\S$',
                message=_('Must not end with whitespace')
            ),
            # See MediaWikiTitleCodec::getTitleInvalidRegex()
            validators.RegexValidator(
                regex=(
                    # Any char that is not in $wgLegalTitleChars
                    r'[^'
                    r''' %!"$&'()*,\-./0-9:;=?@A-Z\^_`a-z~'''
                    '\x80-\xFF'
                    r'+]'
                    # URL percent encoding sequences
                    r'|%[0-9A-Fa-f]{2}'
                    # XML/HTML entities
                    '|&([A-Za-z0-9\x80-\xff]+|#([0-9]+|x[0-9A-Fa-f]+));'
                ),
                inverse_match=True,
                message=_(
                    'Value contains illegal characters or character sequences.'
                )
            )
        ]
    )

    def clean_username(self):
        """Validate that username is available."""
        # Make sure that username is capitalized like MW's Title would do.
        # TODO: Totally not as fancy as secureAndSplit() and friends. Do we
        # need to figure out how to actually do all of that?
        username = self.cleaned_data['username'].strip()
        username = username[0].upper() + username[1:]
        if not utils.username_available(username):
            raise forms.ValidationError(self.IN_USE)
        # TODO: check that it isn't banned by some abusefilter type rule
        return username


@parsleyfy
class ShellUsername(forms.Form):
    IN_USE = _('Shell username is already in use.')
    shellname = forms.CharField(
        label=_('Shell username'),
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Enter your desired shell account username'),
                'autofocus': 'autofocus',
                # Parsley gets confused if {value} is url encoded, so wrap in
                # mark_safe().
                # FIXME: I tried everything I could think of to use
                # urlresolvers.reverse_lazy and I just couldn't get it to work
                # with mark_safe(). I would get either the URL encoded
                # property value or the __str__ of a wrapper object.
                'data-parsley-remote': mark_safe(
                    '/register/api/shellname/{value}'),
                'data-parsley-trigger': 'focusin focusout input',
                'data-parsley-remote-message': IN_USE,
            }
        ),
        max_length=32,
        validators=[
            validators.RegexValidator(
                # Unix username regex suggested by useradd(8).
                # We don't allow a leading '_' or trailing '$' however.
                regex=r'^[a-z][a-z0-9_-]{0,31}$',
                message=_(
                    'Must start with a-z, and can only contain '
                    'lowercase a-z, 0-9, _, and - characters.')
            )
        ]
    )

    def clean_shellname(self):
        """Validate that shellname is available."""
        shellname = self.cleaned_data['shellname']
        if not utils.shellname_available(shellname):
            raise forms.ValidationError(self.IN_USE)
        # TODO: check that it isn't banned by some abusefilter type rule
        return shellname


@parsleyfy
class Email(forms.Form):
    email = forms.EmailField(
        label=_('Email address'),
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Enter a valid email address'),
                'type': 'email',
                'autofocus': 'autofocus',
            }
        ),
        max_length=255
    )

    def clean_email(self):
        """Normalize email domain to lowercase."""
        email = self.cleaned_data['email']
        email_name, domain_part = email.strip().rsplit('@', 1)
        return '@'.join([email_name, domain_part.lower()])


@parsleyfy
class Password(forms.Form):
    class Meta:
        parsley_extras = {
            'confirm': {
                'equalto': 'passwd',
                'error-message': _('Passwords do not match.'),
            }
        }

    passwd = forms.CharField(
        label=_('Password'),
        min_length=10,
        widget=forms.PasswordInput(
            attrs={
                'autofocus': 'autofocus',
            }
        )
    )
    confirm = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput
    )

    def clean(self):
        """Validate that both password entries match."""
        super(Password, self).clean()
        passwd = self.cleaned_data.get('passwd')
        confirm = self.cleaned_data.get('confirm')
        if passwd != confirm:
            self.add_error(
                'confirm', ValidationError(_('Passwords do not match.')))


@parsleyfy
class Confirm(forms.Form):
    agree = forms.BooleanField(
        label=_('I agree to comply with the Terms of Use'))
