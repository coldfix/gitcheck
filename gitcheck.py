#! /usr/bin/env python

import os
import sys
import subprocess

command = ['git', 'diff', '--quiet', '--ignore-submodules=dirty']
DEVNULL = open(os.devnull, 'r+')

def is_clean(folder):
    return 0 == subprocess.call(command, cwd=folder,
                                stdout=DEVNULL, stderr=DEVNULL)


def collect_git_repositories(folder):
    subdirs = [fname for fname in os.listdir(folder)
               if os.path.isdir(os.path.join(folder, fname))]
    if '.git' in subdirs:
        yield folder
        return
    for subdir in subdirs:
        if subdir.startswith('.'):
            continue
        yield from collect_git_repositories(os.path.join(folder, subdir))


def main(folder=None):
    if folder is None:
        folder = '.'
    folder = os.path.realpath(folder)

    for folder in collect_git_repositories(folder):
        if is_clean(folder):
            continue
        print(folder)


if __name__ == '__main__':
    main(*sys.argv[1:])
