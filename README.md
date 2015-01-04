# ansible-ovh-dns

Ansible module for automating DNS entry creation/deletion using the [OVH API](https://eu.api.ovh.com/).

## Installation

1. Install [python-ovh](https://pypi.python.org/pypi/ovh) using PIP:

    pip install ovh

2. Add the module to Ansible's module directory or simply add the -M /route/to/ovh_dns flag when invoking Ansible.

## Usage

Create a typical A record:

    - ovh_dns: state=present domain=mydomain.com name=db1 value=10.10.10.10

Create a CNAME record:

    - ovh_dns: state=present domain=mydomain.com name=dbprod type=cname value=db1

Delete an existing record, must specify all parameters:

    - ovh_dns: state=absent domain=mydomain.com name=dbprod type=cname value=db1

# Parameters

Parameter | Required | Default | Choices        | Comments
:---------|----------|---------|----------------|:-----------------------
domain    | yes      |         |                | Name of the domain zone
name      | yes      |         |                | Name of the DNS record
value     | no       |         |                | Value of the DNS record (i.e. what it points to)
type      | no       | A       | See comments   | Type of DNS record (A, AAAA, CNAME, DKIM, LOC, MX, NAPTR, NS, PTR, SPF, SRV, SSHFP, TXT)
state     | no       | present | present,absent | Determines wether the record is to be created/modified or deleted
