#!/usr/bin/env python

import yaml
import json
import os
import sys

try:
    from StringIO import StringIO
except ModuleNotFoundError:
    from io import StringIO

try:
    from urllib2 import urlopen
    from urllib2 import HTTPError
except ImportError:
    from urllib.request import urlopen
    from urllib.error import HTTPError


def github_request_url(api):
    """Get authenticated URL for a GitHub API path"""
    url = "https://api.github.com{api}".format(api=api)
    try:
        access_token = os.environ['GITHUB_OAUTH_TOKEN']
        if access_token:
            url += "?access_token={access_token}".format(
                access_token=access_token)
    except KeyError:
        pass
    return url


def get_latest_version(repository):
    repository = repository.replace('_', '-')
    """Get latest release for a GitHub repository"""
    try:
        # Get tag name from the latest release
        api = "/repos/{repository}/releases/latest".format(
            repository=repository)
        url = github_request_url(api)
        response_body = urlopen(url).read()
        release = json.loads(response_body)
        return release['tag_name']
    except HTTPError as e:
        if e.code == 404:
            # No releases, get latest tag name
            api = "/repos/{repository}/tags".format(repository=repository)
            url = github_request_url(api)
            response_body = urlopen(url).read()
            tags = json.loads(response_body)
            return tags[0]['name']
        else:
            print(repository)
            raise e


def update_roles(roles):
    """Update role versions in the requirements.yml"""
    roles_updated = 0
    updated_roles = []

    for role in roles:

        repository = None

        if role['name'] == 'zzet.rbenv':
            repository = 'zzet/ansible-rbenv-role'
        elif 'src' in role:
            repository = role['src'].replace('https://github.com/', '')
        else:
            (galaxy_user, galaxy_role) = role['name'].split('.')
            if galaxy_user == 'markosamuli':
                repository = '{github_user}/{github_repo}'.format(
                    github_user=galaxy_user,
                    github_repo='ansible-%s' % galaxy_role)

        if repository:
            latest_version = get_latest_version(repository)
            if latest_version != role['version']:
                print("update {role}: {version} -> {latest_version}".format(
                    role=role['name'],
                    version=role['version'],
                    latest_version=latest_version))
                role['version'] = latest_version
                roles_updated += 1
        else:
            print('Could not find repository for role {role_name}'.format(
                role_name=role['name']))

        updated_roles.append(role)

    if roles_updated > 0:
        if len(roles) > len(updated_roles):
            print('update failed: roles missing from updated roles list')
            sys.exit(1)

        output = StringIO()
        yaml.safe_dump(updated_roles, output, default_flow_style=False)

        role_file = 'requirements.yml'
        with open(role_file, 'w+') as f:
            f.write('---\n')
            f.write(output.getvalue())

        output.close()


def ansible_roles():
    """Return Ansible roles from the requirements.yml file"""
    roles = []
    role_file = 'requirements.yml'
    with open(role_file, 'r') as f:
        required_roles = yaml.safe_load(f.read())
        for role in required_roles:
            roles.append(role)
    return sorted(roles, key=lambda role: role['name'])


def main():
    update_roles(ansible_roles())


if __name__ == '__main__':
    main()
