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

# @see: https://github.com/gheesh/ansible-ovh-dns

from __future__ import print_function

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
            - Name of the domain zone
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
        choices: ['A', 'AAAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT']
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
import sys

try:
    import ovh
except ImportError:
    print("failed=True msg='ovh required for this module'")
    sys.exit(1)

def normalize(type, subdomain, domain):
    if subdomain:
        return str(type) + " " + str(subdomain) + "." + domain
    else:
        return str(type) + " ." + domain

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
    print("Your consumer key is {}".format(validation['consumerKey']))
    print("Please visit {} to validate".format(validation['validationUrl']))

def get_domain_records(client, domain):
    """Obtain all records for a specific domain"""
    records = {}

    # List all ids and then get info for each one
    record_ids = client.get('/domain/zone/{}/record'.format(domain))
    for record_id in record_ids:
        info = client.get('/domain/zone/{}/record/{}'.format(domain, record_id))
        recordname = normalize(info['fieldType'], info['subDomain'], domain)
        if recordname in records:
            old = records[recordname]
            if isinstance(old, list):
                records[recordname].append(info)
            else: 
                records[recordname] = [ old, info ]
        else:
            records[recordname] = info

    return records


def main():
    module = AnsibleModule(
        argument_spec = dict(
            domain = dict(required=True),
            subdomain = dict(required=False),
            value = dict(default=''),
            type = dict(default='A', choices=['A', 'AAAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT']),
            state = dict(default='present', choices=['present', 'absent']),
            ttl = dict(default='3600'),
            permitduplicate = dict(default=False)
        ),
        supports_check_mode = True
    )

    # Get parameters
    domain = module.params.get('domain')
    subdomain   = module.params.get('subdomain')
    state  = module.params.get('state')
    fieldtype = module.params.get('type')

    # Connect to OVH API
    client = ovh.Client()

    # Check that the domain exists
    domains = client.get('/domain/zone')
    if not domain in domains:
        module.fail_json(msg='Domain {} does not exist'.format(domain))

    # Obtain all domain records to check status against what is demanded
    records = get_domain_records(client, domain)
    recordname = normalize(fieldtype, subdomain, domain)

    # Remove a record
    if state == 'absent':
        # Are we done yet?
        #if name not in records or records[name]['fieldType'] != fieldtype or records[name]['target'] != targetval:
        if recordname not in records:
            module.exit_json(changed=False)

        if not module.check_mode:
            # Remove the record
            # TODO: Must check parameters
            client.delete('/domain/zone/{}/record/{}'.format(domain, records[recordname]['id']))
            client.post('/domain/zone/{}/refresh'.format(domain))
        module.exit_json(changed=True)

    # Add / modify a record
    if state == 'present':
        targetval = module.params.get('value')
        ttlval = module.params.get('ttl')

        # Since we are inserting a record, we need a target
        if targetval == '':
            module.fail_json(msg='Did not specify a value')

        # Does the record exist already?
        if recordname in records:

            if isinstance(records[recordname], list):
                found = False
                for recordid in records[recordname]:
                    if recordid['target'] == targetval:
                        found = True
                if found:
                    module.exit_json(changed=False)
            else:
                if records[recordname]['target'] == targetval:
                    # The record is already as requested, no need to change anything
                    module.exit_json(changed=False)

            permitduplicate = module.params.get('permitduplicate')

            # Delete and re-create the record
            if not module.check_mode:
                if not permitduplicate:
                    client.delete('/domain/zone/{}/record/{}'.format(domain, records[recordname]['id']))

                if subdomain:
                    client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, subDomain=subdomain, target=targetval, ttl=ttlval)
                else:
                    client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, target=targetval, ttl=ttlval)

                # Refresh the zone and exit
                client.post('/domain/zone/{}/refresh'.format(domain))
            
            module.exit_json(changed=True)

        if not module.check_mode:
            # Add the record
            if subdomain:
                client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, subDomain=subdomain, target=targetval, ttl=ttlval)
            else:
                client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, target=targetval, ttl=ttlval)
            client.post('/domain/zone/{}/refresh'.format(domain))
            
            module.exit_json(changed=True)

    # We should never reach here
    module.fail_json(msg='Internal ovh_dns module error')


# import module snippets
from ansible.module_utils.basic import *

main()
