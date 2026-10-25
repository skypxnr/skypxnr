#!/usr/bin/env python3
"""
Updates the age in the SVG files, then commits and pushes if anything changed.
Use --no-push to update the files without committing.
"""
import datetime
import os
import subprocess
import sys
from pathlib import Path

from dateutil import relativedelta
from lxml import etree

BIRTHDAY = datetime.datetime(2006, 6, 1)  # Day is unknown, so 1 June is used
SVG_FILES = ['dark_mode.svg', 'light_mode.svg']
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
        'commit', '-m', f'Update age {today}')
    
    # Explicitly pull and rebase from origin main to avoid push rejections
    git('pull', '--rebase', 'origin', 'main')
    git('push', 'origin', 'main')
    print('Pushed updated age.')


def main():
    age = age_string(BIRTHDAY)
    print('Age:', age)

    values = {'age_data': age}

    for filename in SVG_FILES:
        path = REPO_DIR / filename
        if path.exists():
            update_svg(path, values)
    if '--no-push' not in sys.argv:
        commit_and_push()


if __name__ == '__main__':
    main()
