# ansible-ovh-dns

Ansible module for automating DNS entry creation/deletion using the [OVH API](https://eu.api.ovh.com/).

## Installation

1. Install [python-ovh](https://pypi.python.org/pypi/ovh) using PIP:

    pip install ovh

2. Add the module to Ansible's module directory or simply add the -M /route/to/ovh_dns flag when invoking Ansible.

## Configuration

You'll need a valid OVH application key to use this module. If you don't have one, you can follow these steps:

1. Visit [https://eu.api.ovh.com/createApp/](https://eu.api.ovh.com/createApp/) and fill all fields.
2. You'll obtain an Application Key and an Application Secret.
3. Launch python or ipython in a terminal:

    ```python
    client = ovh.Client('ovh-eu', 'YOUR_APPLICATION_KEY', 'YOUR_APPLICATION_SECRET')
    access_rules = [
      {'method': 'GET', 'path': '/domain/*'},
      {'method': 'POST', 'path': '/domain/*'},
      {'method': 'PUT', 'path': '/domain/*'},
      {'method': 'DELETE', 'path': '/domain/*'}
    ]
    client.request_consumerkey(access_rules)
    ```
4. The reply to the last command is:
    ```python
    {
        u'consumerKey': u'GENERATED_CONSUMER_KEY',
        u'state': u'pendingValidation',
        u'validationUrl': u'https://eu.api.ovh.com/auth/?credentialToken=XXXXXXXX'
    }
    ```
5. After visiting the validationUrl, the GENERATED_CONSUMER_KEY will be valid.
5. Setup your shell so it exports the following values:

    ```sh
    OVH_ENDPOINT=ovh-eu
    OVH_APPLICATION_KEY=YOUR_APPLICATION_KEY
    OVH_APPLICATION_SECRET=YOUR_APPLICATION_SECRET
    OVH_CONSUMER_KEY=GENERATED_CONSUMER_KEY
    ```

    Environment variables can also be passed through Ansible task/playbook:

    ```yaml
    - name: OVH DNS playbook
      hosts: localhost
      environment:
        OVH_ENDPOINT: ovh-eu
        OVH_APPLICATION_KEY: YOUR_APPLICATION_KEY
        OVH_APPLICATION_SECRET: YOUR_APPLICATION_SECRET
        OVH_CONSUMER_KEY: GENERATED_CONSUMER_KEY
    ```

## Usage

Create a typical A record:

    - ovh_dns: state=present domain=mydomain.com name=db1 type=A value=10.10.10.10

Replace a typical A record if as multi record found with different target/value:

    - ovh_dns: state=present domain=mydomain.com name=db1 type=A value=10.20.20.20 replace=10.10.10.10

Replace a typical A record if as multi record found with different target/value and create if not found:

    - ovh_dns: state=present domain=mydomain.com name=db1 type=A value=10.20.20.20 replace=10.10.10.[0-9]* create=true

Create a CNAME record:

    - ovh_dns: state=present domain=mydomain.com name=dbprod type=cname value=db1

Append a CNAME record:

    - ovh_dns: state=append domain=mydomain.com name=dbprod type=cname value=db2

Delete an existing record, specific record:

    - ovh_dns: state=absent domain=mydomain.com name=dbprod type=cname value=db1

Delete an existing record, all record same type:

    - ovh_dns: state=absent domain=mydomain.com name=dbprod type=cname

Delete an existing record, all record same name:

    - ovh_dns: state=absent domain=mydomain.com name=dbprod

Delete all TXT records matching ``'^_acme-challenge.*$'`` regex

    - ovh_dns: state=absent domain=mydomain.com name='' type=TXT removes='^_acme-challenge.*'

Module supports ``--diff`` switch; it displays a YAML diff between removed and added records:

```yaml
  - ovh_dns: state=present domain=mydomain.com name=db1 type=A value=10.20.20.20 replace=10.10.10.10
```
```diff
 - domain: kobalt.fr
   fieldType: A
   subDomain: db1
-  target: 10.10.10.10
+  target: 10.20.20.20
   ttl: 3600
```

# Parameters

Parameter | Required | Default | Choices               | Comments
:---------|----------|---------|-----------------------|:-----------------------
domain    | yes      |         |                       | Name of the domain zone
name      | yes      |         |                       | Name of the DNS record
value     | no       |         |                       | Value of the DNS record (i.e. what it points to)
ttl       | no       | 3600    | integer value         | DNS record TTL value in seconds (defaults to 3600)
type      | no       |         | See comments          | Type of DNS record (A, AAAA, CAA, CNAME, DKIM, LOC, MX, NAPTR, NS, PTR, SPF, SRV, SSHFP, TLSA, TXT)
state     | no       | present | present,absent,append | Determines wether the record is to be created/modified or deleted
removes   | no       |         | regex pattern         | specifies a regex pattern to match for bulk deletion
replace   | no       |         |                       | Old value of the DNS record (i.e. what it points to now)
create    | no       |         | true,false            | Used with replace for forced creation
