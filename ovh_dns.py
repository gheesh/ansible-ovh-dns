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
        required: false
        description:
            - Value of the DNS record (i.e. what it points to)
    type:
        required: false
        description:
            - Type of DNS record (A, AAAA, PTR, CNAME, etc.)
    state:
        required: false
        description:
            - Determines wether the record is to be created/modified or deleted
'''

EXAMPLES = '''
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
            domain = dict(required=True, type='str'),
            name = dict(required=True, type='str'),
            value = dict(required=True, type='str'),
            type = dict(default='A', type='str'),
            state = dict(default='present', choices=['present', 'absent'], type='str'),
        ),
        supports_check_mode=True
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
