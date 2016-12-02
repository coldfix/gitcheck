#! /usr/bin/env python

import os
import sys
import subprocess
import re

import operator


def alias(name):
    return property(operator.attrgetter(name))


class GitFlags:

    def __init__(self, flags):
        flags.discard(' ')
        self.flags    = flags
        self.clean    = not bool(flags)
        self.modified = 'M' in flags
        self.added    = 'A' in flags
        self.deleted  = 'D' in flags
        self.renamed  = 'R' in flags
        self.copied   = 'C' in flags
        self.unmerged = 'U' in flags


class GitStatus:

    GIT_STATUS = ['git', 'status', '--porcelain', '-b']
    DEVNULL = open(os.devnull, 'r+')
    SYNC_PART = re.compile(r'\[([^\[\]]*)\]$')

    gone = False
    untracked = False

    def __init__(self, folder):
        status = subprocess.check_output(self.GIT_STATUS, cwd=folder)
        self.sync_status = {}

        index_flags = set()
        workdir_flags = set()
        for l in status.decode('utf-8').splitlines():
            if l.startswith('## '):
                sync_status = self.SYNC_PART.search(l)
                if sync_status is not None:
                    for part in sync_status.group(1).split(','):
                        if part.strip() == 'gone':
                            self.gone = True
                        else:
                            key, val = part.split()
                            self.sync_status[key] = int(val)
            elif l.startswith('?? '):
                self.untracked = True
            else:
                i, w = l[:2]
                index_flags.add(i)
                workdir_flags.add(w)

        self.workdir_status = GitFlags(workdir_flags)
        self.index_status = GitFlags(index_flags)

        self.ahead = self.sync_status.get('ahead', 0)
        self.behind = self.sync_status.get('behind', 0)

    @property
    def clean(self):
        return self.workdir_status.clean and self.index_status.clean

    @property
    def synced(self):
        return self.ahead == 0 and self.behind == 0 and not self.gone

    def code(self):
        return ''.join([
            ' ' if self.workdir_status.clean else 'W',
            ' ' if self.index_status.clean else 'I',
            'T' if self.untracked else ' ',
            ' ' if self.synced else 'S',
        ])


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
        status = GitStatus(folder)
        if status.clean:
            continue
        print(status.code(), folder)


if __name__ == '__main__':
    main(*sys.argv[1:])
