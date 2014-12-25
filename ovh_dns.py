#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ovh_dns, an Ansible module for managing OVH DNS records
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

DOCUMENTATION = '''
---
module: ovh_dns
author: Carlos Izquierdo
short_description: Manage OVH DNS records
description:
    - Manage OVH (French European hosting provider) DNS records
requirements: [ "ovh" ]
options:
    domain:
        required: true
        description:
            - Name of the domain zone.
    name:
        required: true
        description:
            - Name of the DNS record
    value:
        required: true
        description:
            - Value of the DNS record (i.e. what it points to)
    type:
        required: false
        default: A
        description:
            - Type of DNS record (A, AAAA, PTR, CNAME, etc.)
    state:
        required: false
        default: present
        choices: ['present', 'absent']
        description:
            - Determines wether the record is to be created/modified or deleted
'''

EXAMPLES = '''
# Create a typical A record
- ovh_dns: state=present domain=mydomain.com name=db1 value=10.10.10.10

# Create a CNAME record
- ovh_dns: state=present domain=mydomain.com name=dbprod type=cname value=db1

# Delete an existing record, must specify all parameters
- ovh_dns: state=absent domain=mydomain.com name=dbprod type=cname value=db1
'''

import os

try:
    import ovh
except ImportError:
    print "failed=True msg='ovh required for this module'"
    sys.exit(1)

def main():
    module = AnsibleModule(
        argument_spec = dict(
            domain = dict(required=True),
            name = dict(required=True),
            value = dict(default=None),
            type = dict(default='A'),
            state = dict(default='present', choices=['present', 'absent']),
        )
    )

    success = module.params['success']
    text = module.params['name']

    if success:
        module.exit_json(msg=text)
    else:
        module.fail_json(msg=text)

# import module snippets
from ansible.module_utils.basic import *

main()
