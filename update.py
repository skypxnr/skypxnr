#!/usr/bin/env python3
"""
Updates the age in the SVG files, then commits and pushes if anything changed.
Run daily with cron or the GitHub Actions workflow below.
Use --no-push to update the files without committing.
"""
import datetime
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
    """
    Returns the age as 'X years, X months, X days'
    """
    today = today or datetime.datetime.today()
    diff = relativedelta.relativedelta(today, birthday)
    return '{} {}, {} {}, {} {}'.format(
        diff.years, 'year' + format_plural(diff.years),
        diff.months, 'month' + format_plural(diff.months),
        diff.days, 'day' + format_plural(diff.days))


def update_svg(filename, text):
    """
    Replaces the text of the element with id 'age_data'
    """
    tree = etree.parse(filename)
    element = tree.getroot().find(".//*[@id='age_data']")
    if element is None:
        print(f'Warning: no age_data element in {filename}')
        return
    element.text = text
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
    git('push')
    print('Pushed updated age.')


def main():
    age = age_string(BIRTHDAY)
    print('Age:', age)
    for filename in SVG_FILES:
        path = REPO_DIR / filename
        if path.exists():
            update_svg(path, age)
    if '--no-push' not in sys.argv:
        commit_and_push()


if __name__ == '__main__':
    main()
