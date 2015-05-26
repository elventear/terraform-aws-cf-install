#!/usr/bin/env python

from __future__ import print_function

import sys
import os
import warnings

import requests 

class RequestError(Exception): pass

AF_API_ROOT = 'https://wwws.appfirst.com/api'

def api_url(root, *s):
    url = '{0}/{1}'.format(root, '/'.join(s))
    return url

af_api = lambda *s: api_url(AF_API_ROOT, *s)
bosh_api = lambda *s: api_url(BOSH_URL, *s)

def check_200(r):
    if r.status_code != 200:
        raise RequestError(r)
    return r

def get_tagged_server_ids(tag):
    r = check_200(requests.get(af_api('server_tags/'), auth=(AF_USER, AF_API_KEY),
        headers={'Accept': 'application/json'}))
    for t in r.json()['data']:
        if t['name'] == tag:
            return t['servers']
    return []

def get_bosh_releases_with_collector():
    r = check_200(requests.get(bosh_api('deployments'), auth=(BOSH_USER, BOSH_PASS),
        verify=False))
    o = []
    for deployment in r.json():
        if 'appfirst' in set(x['name'] for x in deployment['releases']) or \
                'appfirst' in set(x['name'] for x in deployment['stemcells']):
            o.append(deployment['name'])
    return o

def get_bosh_vm_agent_ids(releases):
    o = {}
    for release in releases:
        r = check_200(requests.get(bosh_api('deployments', release, 'vms'), 
            auth=(BOSH_USER, BOSH_PASS), verify=False))
        o.update((x['agent_id'], '{0[job]}/{0[index]}'.format(x)) for x in r.json())
    return o

def update_nickname(server_id, host_map):
    url = af_api('servers', '%s/' % server_id)
    r = check_200(requests.get(url, auth=(AF_USER, AF_API_KEY), 
        headers={'Accept': 'application/json'}))
    server = r.json()

    if server['hostname'] in host_map:
        if host_map[server['hostname']] != server['nickname']:
            server['nickname'] = host_map[server['hostname']]
            if server['description'] == '':
                server['description'] = ' '
            r = check_200(requests.put(url, json=server, auth=(AF_USER, AF_API_KEY), 
                headers={'Accept': 'application/json'}))
            print('Server {0} has been updated ({1}).'.format(server['nickname'], url))
        else:
            print('Server {0} is up to date ({1}).'.format(server['nickname'], url))

def read_env():
    global BOSH_URL
    global BOSH_USER
    global BOSH_PASS
    global AF_USER
    global AF_API_KEY


    env = os.environ
    try:
        BOSH_URL   =  env['BOSH_URL']
        BOSH_USER  =  env['BOSH_USER']
        BOSH_PASS  =  env['BOSH_PASS']
        AF_USER    =  env['AF_USER']
        AF_API_KEY = env['AF_API_KEY']
    except KeyError as e:
        print("Error: missing enviroment variable '%s'" % e.args)
        sys.exit(1)

def main():
    read_env()
    to_tag_hosts = get_bosh_vm_agent_ids(get_bosh_releases_with_collector())
    bosh_server_ids = get_tagged_server_ids('bosh')
    for server_id in bosh_server_ids:
        update_nickname(server_id, to_tag_hosts)


if __name__ == '__main__':
    main()