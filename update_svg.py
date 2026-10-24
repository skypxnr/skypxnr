#!/usr/bin/env python3
"""
Updates the age and GitHub stats in the SVG files, then commits and pushes if anything changed.
Use --no-push to update the files without committing.
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path

import requests
from dateutil import relativedelta
from lxml import etree

BIRTHDAY = datetime.datetime(2006, 6, 1)  # Day is unknown, so 1 June is used
SVG_FILES = ['dark_mode.svg', 'light_mode.svg']
USER_NAME = os.environ.get('USER_NAME', 'skypxnr')
HEADERS = {'authorization': 'token ' + os.environ['ACCESS_TOKEN']}
GIT_USER_NAME = 'github-actions[bot]'
GIT_USER_EMAIL = 'github-actions[bot]@users.noreply.github.com'
REPO_DIR = Path(__file__).resolve().parent


def format_plural(unit):
    return 's' if unit != 1 else ''


def age_string(birthday, today=None):
    today = today or datetime.datetime.today()
    diff = relativedelta.relativedelta(today, birthday)
    return '{} {}, {} {}, {} {}'.format(
        diff.years, 'year' + format_plural(diff.years),
        diff.months, 'month' + format_plural(diff.months),
        diff.days, 'day' + format_plural(diff.days))


def gql(query, variables):
    response = requests.post('https://api.github.com/graphql',
                             json={'query': query, 'variables': variables}, headers=HEADERS)
    if response.status_code != 200:
        raise Exception('GitHub API failed', response.status_code, response.text)
    data = response.json()
    if 'errors' in data:
        raise Exception('GraphQL error', data['errors'])
    return data['data']


def get_stats():
    user_query = '''
    query($login: String!, $owner: [RepositoryAffiliation], $all: [RepositoryAffiliation]) {
        user(login: $login) {
            createdAt
            followers { totalCount }
            owned: repositories(first: 100, ownerAffiliations: $owner) {
                totalCount
                edges { node { ... on Repository { stargazers { totalCount } } } }
            }
            contributed: repositories(ownerAffiliations: $all) { totalCount }
        }
    }'''
    user = gql(user_query, {'login': USER_NAME, 'owner': ['OWNER'],
                            'all': ['OWNER', 'COLLABORATOR', 'ORGANIZATION_MEMBER']})['user']

    stars = sum(edge['node']['stargazers']['totalCount'] for edge in user['owned']['edges'])

    # Commits: sum yearly contribution totals from account creation to now
    commit_query = '''
    query($login: String!, $start: DateTime!, $end: DateTime!) {
        user(login: $login) {
            contributionsCollection(from: $start, to: $end) {
                contributionCalendar { totalContributions }
            }
        }
    }'''
    start_year = int(user['createdAt'][:4])
    now = datetime.datetime.utcnow()
    commits = 0
    for year in range(start_year, now.year + 1):
        start = f'{year}-01-01T00:00:00Z'
        end = f'{year}-12-31T23:59:59Z' if year < now.year else now.strftime('%Y-%m-%dT%H:%M:%SZ')
        result = gql(commit_query, {'login': USER_NAME, 'start': start, 'end': end})
        commits += result['user']['contributionsCollection']['contributionCalendar']['totalContributions']

    return {
        'repo_data': user['owned']['totalCount'],
        'contrib_data': user['contributed']['totalCount'],
        'star_data': stars,
        'commit_data': commits,
        'follower_data': user['followers']['totalCount'],
    }


def update_svg(filename, values):
    """
    Sets the text of each element whose id matches a key in values
    """
    tree = etree.parse(filename)
    root = tree.getroot()
    for element_id, value in values.items():
        element = root.find(f".//*[@id='{element_id}']")
        if element is None:
            print(f'Warning: no {element_id} element in {filename}')
            continue
        element.text = value
    tree.write(filename, encoding='utf-8', xml_declaration=True)


def git(*args, capture=False):
    return subprocess.run(['git', *args], cwd=REPO_DIR, check=True,
                          capture_output=capture, text=True)


def commit_and_push():
    status = git('status', '--porcelain', '--', *SVG_FILES, capture=True).stdout.strip()
    if not status:
        print('No changes to commit.')
        return
    today = datetime.date.today().isoformat()
    git('add', '--', *SVG_FILES)
    git('-c', f'user.name={GIT_USER_NAME}', '-c', f'user.email={GIT_USER_EMAIL}',
        'commit', '-m', f'Update stats {today}')
    git('pull', '--rebase')
    git('push')
    print('Pushed updated stats.')


def main():
    age = age_string(BIRTHDAY)
    print('Age:', age)
    stats = get_stats()
    print('Stats:', stats)

    values = {'age_data': age}
    values.update({key: f'{value:,}' for key, value in stats.items()})

    for filename in SVG_FILES:
        path = REPO_DIR / filename
        if path.exists():
            update_svg(path, values)
    if '--no-push' not in sys.argv:
        commit_and_push()


if __name__ == '__main__':
    main()
