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
        required: true if present/append
        description:
            - Value of the DNS record (i.e. what it points to)
            - If None with 'present' then deletes ALL records at 'name'
    replace:
        required: true if present and multi records found
            - Old value of the DNS record (i.e. what it points to now)
    type:
        required: true if present/append
        choices: ['A', 'AAAA', 'CAA', 'CNAME', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TLSA', 'TXT']
        description:
            - Type of DNS record (A, AAAA, PTR, CNAME, etc.)
    state:
        required: false
        default: present
        choices: ['present', 'absent', 'append']
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

def get_domain_records(client, domain, fieldtype=None, subDomain=None):
    """Obtain all records for a specific domain"""
    records = {}

    params = {
        'subDomain': subDomain,
        'fieldType': fieldtype,
    }

    # List all ids and then get info for each one
    if not subDomain:
        params.pop('subDomain')
    if not fieldtype:
        params.pop('fieldType')

    record_ids = client.get('/domain/zone/{}/record'.format(domain),
                            **params)
    for record_id in record_ids:
        info = client.get('/domain/zone/{}/record/{}'.format(domain, record_id))
        records[record_id] = info

    return records

def count_type(records, fieldtype=['A', 'AAAA']):
    i = 0
    for id in records:
        if records[id]['fieldType'] in fieldtype:
            i+=1
    return i

def main():
    module = AnsibleModule(
        argument_spec = dict(
            domain = dict(required=True),
            name = dict(required=True),
            state = dict(default='present', choices=['present', 'absent', 'append']),
            type = dict(default=None, choices=['A', 'AAAA', 'CNAME', 'CAA', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT', 'TLSA']),
            replace = dict(default=None),
            value = dict(default=None),
        ),
        supports_check_mode = True
    )
    results = dict(
        changed=False,
        msg='',
        records='',
        response='',
        original_message=module.params['name'],
    )
    response = []

    # Get parameters
    domain = module.params.get('domain')
    name   = module.params.get('name')
    state  = module.params.get('state')
    fieldtype = module.params.get('type')
    targetval = module.params.get('value')
    oldtargetval = module.params.get('replace')

    # Connect to OVH API
    client = ovh.Client()

    # Check that the domain exists
    domains = client.get('/domain/zone')
    if not domain in domains:
        module.fail_json(msg='Domain {} does not exist'.format(domain))

    # Obtain all domain records to check status against what is demanded
    records = get_domain_records(client, domain, fieldtype, name)

    # Remove a record(s)
    if state == 'absent':
        if not records:
            module.exit_json(changed=False)

        # Delete same tagert
        if targetval:
            tmprecords = records.copy()
            for id in records:
                if targetval.lower() != records[id]['target'].lower():
                    tmprecords.pop(id)
            records = tmprecords

        results['records'] = records
        if records:
            if not module.check_mode:
                # Remove the ALL record
                for id in records.keys():
                    client.delete('/domain/zone/{}/record/{}'.format(domain, id))
                client.post('/domain/zone/{}/refresh'.format(domain))
            results['changed'] = True
        results['response'] = response
        module.exit_json(**results)

    # Add / modify a record
    elif state in ['present', 'append']:

        # Since we are inserting a record, we need a target
        if targetval is None:
            module.fail_json(msg='Did not specify a value')
        if fieldtype is None:
            module.fail_json(msg='Did not specify a type')

        # Does the record exist already? Yes
        if records:
            for id in records:
                if records[id]['target'].lower() == targetval.lower():
                    # The record is already as requested, no need to change anything
                    module.exit_json(changed=False)

            # TODO: oldtargetval(replace) in regex
            # list records modify in end
            oldrecords = {}
            if state == 'present':
                for id in records:
                    # update target
                    if oldtargetval:
                        if oldtargetval.lower() == records[id]['target'].lower():
                            oldrecords.update({id: records[id]})
                    # uniq update
                    else:
                        oldrecords.update({id: records[id]})

            # TODO: failed: old record not found if oldtargetval
            if oldrecords:
                if fieldtype in ['A', 'AAAA', 'CNAME'] and len(oldrecords) > 1 and not oldtargetval:
                    module.fail_json(msg='Too many record match, use replace')

                # FIXME: check if all records as same fieldType not A/AAAA and CNAME
                # if fieldtype in ['A', 'AAAA', 'CNAME']:
                #     oldA = count_type(records)
                #     oldC = count_type(records, 'CNAME')
                #     newA = count_type(oldrecords)
                #     newC = count_type(oldrecords, 'CNAME')
                #     check = True
                #     if oldA > 0 and newC > 0 and oldA != newC:
                #         check = False
                #     if oldC > 0 and newA > 0 and oldC != newA:
                #         check = False
                #     if not check:
                #         module.fail_json(msg='The subdomain already uses a DNS record.  You can not register a {} field because of an incompatibility.'.format(fieldType))

                # Delete all records and re-create the record
                if not module.check_mode:
                    for id in oldrecords:
                        client.delete('/domain/zone/{}/record/{}'.format(domain, id))
                    response.append({'delete': oldrecords})

                    res = client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, subDomain=name, target=targetval)
                    response.append(res)
                    # Refresh the zone and exit
                    client.post('/domain/zone/{}/refresh'.format(domain))
                results['changed'] = True
        # end records exist

        # Add record
        if state == 'append' or not records:
            if not module.check_mode:
                # Add the record
                res = client.post('/domain/zone/{}/record'.format(domain), fieldType=fieldtype, subDomain=name, target=targetval)
                response.append(res)
                client.post('/domain/zone/{}/refresh'.format(domain))
            results['changed'] = True

        results['response'] = response
        module.exit_json(**results)
        # end state == 'present'

    # We should never reach here
    results['msg'] = 'Internal ovh_dns module error'
    module.fail_json(**results)


# import module snippets
from ansible.module_utils.basic import *

main()
