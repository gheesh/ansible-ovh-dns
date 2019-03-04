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

from __future__ import print_function

DOCUMENTATION = '''
---
module: ovh_dns
author: 
    - Carlos Izquierdo 
    - Marcin Jaworski (hemi@hemical.pl)
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
        required: false
        description:
            - Value of the DNS record (i.e. what it points to)
    old_value:
        required: false
        description:
            - Old value of the DNS record which we want to update
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
# Create an A record
- ovh_dns: state=present domain=mydomain.com name=db1 type=A value=10.10.10.10

# Create a CNAME record
- ovh_dns: state=present domain=mydomain.com name=dbprod type=CNAME value=db1

# Update a CNAME record
- ovh_dns: state=present domain=mydomain.com name=dbprod type=CNAME value=db1 old_value=db1old

# Delete an existing record, must specify all parameters
- ovh_dns: state=absent domain=mydomain.com name=dbprod type=CNAME value=db1

# Remove all dns records
- ovh_dns: state=absent domain=mydomain.com name="*"

# Remove all type=A records
- ovh_dns: state=absent domain=mydomain.com name="*" type=A
'''

RETURN = '''
original_message:
    description: The original name param that was passed in
    type: str
message:
    description: The output message that the module generates
'''

import os
import sys
import json
from ansible.module_utils.basic import AnsibleModule

try:
    import ovh
    HAS_OVH_LIB=True
except:
    HAS_OVH_LIB=False


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
    records = []

    # List all ids and then get info for each one
    record_ids = client.get('/domain/zone/{}/record'.format(domain))
    for record_id in record_ids:
        info = client.get('/domain/zone/{}/record/{}'.format(domain, record_id))
        records.append(info)
    return records

def check_record(records, subdomain, fieldType, target):
    for record in records:
        if record['subDomain'] == subdomain and record['fieldType'] == fieldType and record['target'] == target:
            return record['id']
        return False

def main():
    module = AnsibleModule(
        argument_spec = dict(
            domain = dict(required=True),
            name = dict(default=''),
            value = dict(default=''),
            old_value = dict(default=''),
            type = dict(default='', choices=['A', 'AAAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT']),
            state = dict(default='present', choices=['present', 'absent']),
        ),
        supports_check_mode = True
    )
    if not HAS_OVH_LIB:
        module.fail_json(msg='The "ovh" Python module is required')

    result = dict(
        changed=False,
        original_message='',
        message=''
    )

    result['original_message'] = module.params['name']

    # Get parameters
    domain = module.params.get('domain')
    name   = module.params.get('name')
    state  = module.params.get('state')
    fieldtype = module.params.get('type')
    targetval = module.params.get('value')
    old_targetval = module.params.get('old_value')

    # Connect to OVH API
    client = ovh.Client()

    # Check that the domain exists
    domains = client.get('/domain/zone')
    if not domain in domains:
        module.fail_json(msg='Domain {} does not exist'.format(domain), **result)

    # Obtain all domain records to check status against what is demanded
    records = get_domain_records(client, domain)
    current_record = check_record(records,name,fieldtype,targetval)
    old_record = check_record(records,name,fieldtype,old_targetval)
    response = [] 
    # Remove a record
    if state == 'absent':
        if not module.check_mode:
            if not current_record and name == "*":
                for record in records:
                    if record['fieldType'] != 'NS' and (fieldtype = '' or record['fieldtype'] == fieldtype):
                        response.append(client.delete('/domain/zone/{}/record/{}'.format(domain, record['id'])))
                        result['changed'] = True
            else:
                response.append(client.delete('/domain/zone/{}/record/{}'.format(domain, current_record)))
                response.append(client.post('/domain/zone/{}/refresh'.format(domain)))
                result['changed'] = True

            result['message'] = json.dumps(response)
            module.exit_json(**result)

    # Add / modify a record
    if state == 'present':

        # Since we are inserting a record, we need a target
        if targetval == '':
            module.fail_json(msg='Did not specify a value', **result)

        if current_record:
            # The record is already as requested, no need to change anything
            module.exit_json(**result)

        if not module.check_mode:
            if old_record:
                # Update record
                response.append(client.put('/domain/zone/{}/record/{}'.format(domain, old_record), target=targetval))
            else:
                # Create record
                response.append(client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, subDomain=name, target=targetval))
            # Refresh the zone and exit
            response.append(client.post('/domain/zone/{}/refresh'.format(domain)))
            result['changed'] = True
            result['message'] = json.dumps(response)
            module.exit_json(**result)

    if state == 'update':
        # Since we are updating a record, we need a target
        if targetval == '':
            module.fail_json(msg='Did not specify a value', **result)



    # We should never reach here
    module.fail_json(msg='Internal ovh_dns module error')


if __name__ == '__main__':
    main()
