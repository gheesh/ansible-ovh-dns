#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ovh_reverse, an Ansible module for managing OVH DNS reverse
# Copyright (C) 2014, Carlos Izquierdo <gheesh@gheesh.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

from __future__ import print_function

DOCUMENTATION = '''
---
module: ovh_reverse
author: Laurent Almeras
short_description: Manage OVH DNS reverse
description:
    - Manage OVH (French European hosting provider) DNS reverse
requirements: [ "ovh" ]
options:
    ip:
        required: true
        description:
            - IP we want to manage
    reverse:
        required: false
        description:
            - reverse name to associate the IP with; not used if state: absent.
              For state: present and reverse is empty, only checks if a reverse
              exists else triggers a failure
    state:
        required: false
        default: present
        choices: ['present', 'absent']
        description:
            - present or absent: present checks current reverse and update it as
              needed, absent delete reverse record if present.
'''

EXAMPLES = '''
# Create a reverse
- ovh_reverse: ip=10.10.10.10 state=present reverse=myhost.mydomain.tld.

# Check a reverse exists, else triggers a failure
- ovh_reverse: ip=10.10.10.10 state=present

# Delete a reverse
- ovh_reverse: ip=10.10.10.10 state=absent
'''


import sys
import re
import yaml

try:
    import ovh
except ImportError:
    print("failed=True msg='ovh required for this module'")
    sys.exit(1)


# TODO: Try to automate this in case the supplied credentials are not valid
def get_credentials():
    """This function is used to obtain an authentication token.
    It should only be called once."""
    client = ovh.Client()
    access_rules = [
        {'method': 'GET', 'path': '/domain/*'},
        {'method': 'PUT', 'path': '/domain/*'},
        {'method': 'POST', 'path': '/domain/*'},
        {'method': 'DELETE', 'path': '/domain/*'},
    ]
    validation = client.request_consumerkey(access_rules)
    # print("Your consumer key is {}".format(validation['consumerKey']))
    # print("Please visit {} to validate".format(validation['validationUrl']))
    return validation['consumerKey']


def get_reverse(client, ip):
    """Obtain a reverse"""
    # this url works both with /32 blocks or ip as first parameter
    # may throw an APIError

    # first check ip management is accessible, throw an ApiError if not
    ip_reverses = client.get('/ip/{}%2F32/reverse'.format(ip))
    if not ip_reverses:
        # if list if empty, ip is manageable but there is no reverse
        return None
    else:
        # if ip is manageable, get reverse information
        # result is a list; only one reverse is expected
        return client.get('/ip/{}%2F32/reverse/{}'.format(ip, ip_reverses[0]))

def exc_str(ovh_exception):
    """__str__ is overloaded in ovh APIError and does not provide any insight.
    Alternative implementation to retrieve first exception parameter.
    """
    args = getattr(ovh_exception, 'args', None)
    if args:
        return args[0]
    else:
        return str(ovh_exception)


def update_reverse(check_mode, client, ip, original_reverse, reverse, results):
    """Update a reverse"""
    if original_reverse is None or original_reverse['reverse'] != reverse:
        if original_reverse:
            results['diff']['before'] = original_reverse['reverse'] + "\n"
        updated_reverse = None
        results['diff']['before'] = original_reverse['reverse'] + "\n" if original_reverse else "\n"
        if not check_mode:
            client.post('/ip/{}%2F32/reverse'.format(ip), ipReverse=ip, reverse=reverse)
            updated_reverse = get_reverse(client, ip)
            results['reverse'] = updated_reverse
            results['msg'] = 'IP reverse for {} updated from {} to {}'.format(ip, original_reverse['reverse'] if original_reverse else '<none>', updated_reverse['reverse'])
            results['diff']['after'] = updated_reverse['reverse'] + "\n"
        else:
            results['reverse'] = None
            results['msg'] = 'IP reverse for {} needs to be updated from {} to {}'.format(ip, original_reverse['reverse'] if original_reverse else '<none>', reverse)
            results['diff']['after'] = reverse + "\n"
        results['changed'] = True
    else:
        results['msg'] = 'IP reverse for {} already set to {}'.format(ip, reverse)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            ip=dict(required=True),
            reverse=dict(required=False),
            state=dict(default='present', choices=['present', 'absent'])
        ),
        supports_check_mode=True
    )
    results = dict(
        changed=False,
        msg='',
        original_reverse=None,
        reverse=None,
        diff={},
        failed=False
    )
    response = []

    # Get parameters
    ip = module.params.get('ip')
    reverse = module.params.get('reverse')
    state = module.params.get('state')

    # Connect to OVH API
    client = ovh.Client()

    # Check that the domain exists
    original_reverse = None
    try:
        original_reverse = get_reverse(client, ip)
        results['original_reverse'] = original_reverse
        results['reverse'] = original_reverse
    except Exception as e:
        module.fail_json(msg='IP reverse for {} does not seem to be manageable: {}.'.format(ip, exc_str(e)))

    try:
        if state == 'present':
            if reverse:
                # we have a value to check and set
                update_reverse(module.check_mode, client, ip, original_reverse, reverse, results)
            else:
                # we only check if reverse is set (whatever value it is)
                if original_reverse is None:
                    # no reverse to set and no reverse, failure
                    results['msg'] = 'No IP reverse for {} and not reverse provided. Failure.'.format(ip)
                    results['failed'] = True
                else:
                    results['msg'] = 'IP reverse record for {} is set to {}.'.format(ip, original_reverse['reverse'])
        elif state == 'absent' and original_reverse is None:
            results['msg'] = 'IP reverse record for {} is absent.'.format(ip)
        elif state == 'absent' and not original_reverse is None:
            if not module.check_mode:
                client.delete('/ip/{}%2F32/reverse/{}'.format(ip, original_reverse['ipReverse']))
                results['msg'] = 'IP reverse record for {} deleted.'.format(ip)
            else:
                results['msg'] = 'IP reverse record for {} needs to be deleted.'.format(ip)
            results['diff']['before'] = original_reverse['reverse'] + "\n"
            results['diff']['after'] = "\n"
            results['changed'] = True
            results['reverse'] = None

        failed = results['failed']
        results.pop('failed')
        if failed:
            module.fail_json(**results)
        else:
            module.exit_json(**results)
    except Exception as e:
        module.fail_json(msg='IP reverse for {} fails during update: {}.'.format(ip, exc_str(e)))



# import module snippets
from ansible.module_utils.basic import *

main()
