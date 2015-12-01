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

    {u'consumerKey': u'GENERATED_CONSUMER_KEY',
    u'state': u'pendingValidation',
    u'validationUrl': u'https://eu.api.ovh.com/auth/?credentialToken=XXXXXXXX'}

5. After visiting the validationUrl, the GENERATED_CONSUMER_KEY will be valid.
5. Setup your shell so it exports the following values:

    ```
    OVH_ENDPOINT=ovh-eu
    OVH_APPLICATION_KEY=YOUR_APPLICATION_KEY
    OVH_APPLICATION_SECRET=YOUR_APPLICATION_SECRET
    OVH_CONSUMER_KEY=GENERATED_CONSUMER_KEY
    ```

#Managing DNS records
## Usage

Create a typical A record:

    - ovh_dns: state=present domain=mydomain.com name=db1 value=10.10.10.10

Create a CNAME record:

    - ovh_dns: state=present domain=mydomain.com name=dbprod type=cname value=db1

Delete an existing record, must specify all parameters:

    - ovh_dns: state=absent domain=mydomain.com name=dbprod type=cname value=db1

## Parameters

Parameter | Required | Default | Choices        | Comments
:---------|----------|---------|----------------|:-----------------------
domain    | yes      |         |                | Name of the domain zone
name      | yes      |         |                | Name of the DNS record
value     | no       |         |                | Value of the DNS record (i.e. what it points to)
type      | no       | A       | See comments   | Type of DNS record (A, AAAA, CNAME, DKIM, LOC, MX, NAPTR, NS, PTR, SPF, SRV, SSHFP, TXT)
state     | no       | present | present,absent | Determines wether the record is to be created/modified or deleted



#Manager Load Balancer IP
## Usage

Adds or Update an ip to a Load Balancer:

    - ovh_ip_loadbalancer name=ip-1.1.1.1 ip=212.1.1.1 state=present probe=none weight=8 endpoint=ovh-eu application_key=yourkey application_secret=yoursecret consumer_key=yourconsumerkey

Removes an an ip from a Load Balancer:

    - ovh_ip_loadbalancer name=ip-1.1.1.1 ip=212.1.1.1 state=absent endpoint=ovh-eu application_key=yourkey application_secret=yoursecret consumer_key=yourconsumerkey

## Parameters

Parameter 			| Required | Default | Choices        | Comments
:-------------------|----------|---------|----------------|:-----------------------
name				| yes      |         |                | Name of load balancer to update
ip        			| yes      |         |                | Name of the backend IP to manager
probe     			| no       |         |                | Value of the probe parameter of the backend (none http icmp oco)
weight          	| no       |         |                | Value of the weight parameter ( a number between 1 and 100 )
endpoint       		| yes      |         |                | The endpoint to use  for OVH api
application_key 	| yes      |         | See comments   | The application key to use for OVH api
application_secret	| yes      |         | See comments   | The application secret to use for OVH api
state		   		| yes      | present | present,absent | Determines wether the IP backend is to be created/modified or deleted
