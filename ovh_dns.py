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
    create:
        required: false
        description:
            - If 'state' == 'present' and 'replace' is not empty then create the record
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
    removes:
        required: false
        description:
            - specifies a regex pattern to match for bulk deletion
    replace:
        required: true if present and multi records found
            - Old value of the DNS record (i.e. what it points to now)
            - Accept regex
    ttl:
        required: false
        description:
            - value of record TTL value in seconds (defaults to 3600) 
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

# Delete all TXT records matching '^_acme-challenge.*$' regex
- ovh_dns: state=absent domain=mydomain.com name='' type=TXT removes='^_acme-challenge.*'
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


def get_domain_records(client, domain, fieldtype=None, subDomain=None):
    """Obtain all records for a specific domain"""
    records = {}

    params = {}

    # List all ids and then get info for each one
    if subDomain is not None:
        params['subDomain'] = subDomain
    if fieldtype is not None:
        params['fieldType'] = fieldtype

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
        argument_spec=dict(
            domain=dict(required=True),
            name=dict(required=True),
            state=dict(default='present', choices=['present', 'absent', 'append']),
            type=dict(default=None, choices=['A', 'AAAA', 'CNAME', 'CAA', 'DKIM', 'LOC', 'MX', 'NAPTR', 'NS', 'PTR', 'SPF', 'SRV', 'SSHFP', 'TXT', 'TLSA']),
            removes=dict(default=None),
            replace=dict(default=None),
            value=dict(default=None),
            create=dict(default=False, type='bool'),
            ttl=dict(default=3600, type='int'),
        ),
        supports_check_mode=True
    )
    results = dict(
        changed=False,
        msg='',
        records='',
        response='',
        original_message=module.params['name'],
        diff={}
    )
    response = []

    # Get parameters
    domain = module.params.get('domain')
    name = module.params.get('name')
    state = module.params.get('state')
    fieldtype = module.params.get('type')
    targetval = module.params.get('value')
    removes = module.params.get('removes')
    ttlval = module.params.get('ttl')
    oldtargetval = module.params.get('replace')
    create = module.params.get('create')

    # Connect to OVH API
    client = ovh.Client()

    # Check that the domain exists
    domains = client.get('/domain/zone')
    if domain not in domains:
        module.fail_json(msg='Domain {} does not exist'.format(domain))

    # Obtain all domain records to check status against what is demanded
    records = get_domain_records(client, domain, fieldtype, name)

    # Remove a record(s)
    if state == 'absent':

        if len(name) == 0 and not removes:
            module.fail_json(msg='wildcard delete not allowed')

        if not records:
            module.exit_json(changed=False)

        # Delete same target
        rn = None
        rv = None
        if removes:
            rn = re.compile(removes, re.IGNORECASE)
        else:
            rn = re.compile("^{}$".format(name), re.IGNORECASE)
        if targetval:
            rv = re.compile(targetval, re.IGNORECASE)
        else:
            rv = re.compile(r'.*')

        tmprecords = records.copy()
        for id in records:
            if not rn.match(records[id]['subDomain']) or not rv.match(records[id]['target']):
                tmprecords.pop(id)
        records = tmprecords

        results['delete'] = records
        if records:
            before_records=[]
            # Remove the ALL record
            for id in records:
                before_records.append(dict(
                    domain=domain,
                    fieldType=records[id]['fieldType'],
                    subDomain=records[id]['subDomain'],
                    target=records[id]['target'],
                    ttl=records[id]['ttl'],
                    ))
                if not module.check_mode:
                    client.delete('/domain/zone/{}/record/{}'.format(domain, id))
            if not module.check_mode:
                client.post('/domain/zone/{}/refresh'.format(domain))
            results['changed'] = True
            results['diff']['before'] = yaml.dump(before_records)
            results['diff']['after'] = ''
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
                if records[id]['target'].lower() == targetval.lower() and records[id]['ttl'] == ttlval:
                    # The record is already as requested, no need to change anything
                    module.exit_json(changed=False)

            # list records modify in end
            oldrecords = {}
            if state == 'present':
                if oldtargetval:
                    r = re.compile(oldtargetval, re.IGNORECASE)
                for id in records:
                    # update target
                    if oldtargetval:
                        if re.match(r, records[id]['target']):
                            oldrecords.update({id: records[id]})
                    # uniq update
                    else:
                        oldrecords.update({id: records[id]})
                if oldtargetval and not oldrecords and not create:
                    module.fail_json(msg='Old record not match, use append ?')

            if oldrecords:
                before_records = []
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
                newrecord = dict(
                        fieldType=fieldtype,
                        subDomain=name,
                        target=targetval,
                        ttl=ttlval
                        )
                for id in oldrecords:
                    before_records.append(dict(
                        domain=domain,
                        fieldType=oldrecords[id]['fieldType'],
                        subDomain=oldrecords[id]['subDomain'],
                        target=oldrecords[id]['target'],
                        ttl=oldrecords[id]['ttl'],
                        ))
                    if not module.check_mode:
                        client.delete('/domain/zone/{}/record/{}'.format(domain, id))
                if not module.check_mode:
                    response.append({'delete': oldrecords})

                    res = client.post('/domain/zone/{}/record'.format(domain), **newrecord)
                    response.append(res)
                    # Refresh the zone and exit
                    client.post('/domain/zone/{}/refresh'.format(domain))
                    results['response'] = response
                results['diff']['before'] = yaml.dump(before_records)
                after = [newrecord]
                after[0]['domain'] = domain
                results['diff']['after'] = yaml.dump(after)
                results['changed'] = True
                module.exit_json(**results)
        # end records exist

        # Add record
        if state == 'append' or not records:
            newrecord = dict(
                    fieldType=fieldtype,
                    subDomain=name,
                    target=targetval,
                    ttl=ttlval
                    )
            if not module.check_mode:
                # Add the record
                res = client.post('/domain/zone/{}/record'.format(domain), **newrecord)
                response.append(res)
                client.post('/domain/zone/{}/refresh'.format(domain))
            results['diff']['before'] = ''
            after = dict(newrecord)
            after['domain'] = domain
            results['diff']['after'] = yaml.dump(after)
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
