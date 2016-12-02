#! /usr/bin/env python
"""
gitcheck - recursively check for unclean/unpushed git repositories.

Usage:
    gitcheck PATH
"""

import os
import sys
import subprocess
import re


#----------------------------------------
# Constants
#----------------------------------------

# Check status of index/workdir
GIT_STATUS = ['git', 'status', '--porcelain', '--branch']

# Get sync status for each branch
SYNC_PART = re.compile(r'\[([^\[\]]*)\]$')

# Related commands:
# - List remotes for all branches:
#       git config --get-regexp ^branch\..*\.remote$
# - Get remote for a specific branch:
#       git rev-parse --symbolic-full-name --abbrev-ref master@{u}


class GitSyncStatus:

    gone = False
    ahead = 0
    behind = 0

    def __init__(self, branch, remote, divergence):
        self.branch = branch
        self.remote = remote
        self.is_tracked = bool(remote)
        sync_status = SYNC_PART.search(divergence)
        if sync_status is None:
            return
        for part in sync_status.group(1).split(','):
            if part.strip() == 'gone':
                self.gone = True
                continue
            key, val = part.split()
            setattr(self, key, int(val))

    @classmethod
    def parse(cls, status_line):
        branch = status_line
        remote = divergence = ''
        if '...' in branch:
            branch, remote = branch.split('...', 1)
            if ' ' in remote:
                remote, divergence = remote.split(' ', 1)
        return cls(branch, remote, divergence)

    @property
    def synced(self):
        return self.ahead == 0 and self.behind == 0 and not self.gone


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
        self.typechange = 'T' in flags


class GitStatus:

    sync_status = None
    untracked = False

    def __init__(self, folder):
        status = subprocess.check_output(GIT_STATUS, cwd=folder)
        index_flags = set()
        workdir_flags = set()
        for l in status.decode('utf-8').splitlines():
            if l.startswith('## '):
                self.sync_status = [GitSyncStatus.parse(l[3:])]
            elif l.startswith('?? '):
                self.untracked = True
            else:
                i, w = l[:2]
                index_flags.add(i)
                workdir_flags.add(w)

        self.workdir_status = GitFlags(workdir_flags)
        self.index_status = GitFlags(index_flags)

    @property
    def clean(self):
        return (self.workdir_status.clean and
                self.index_status.clean and
                self.synced and
                self.is_tracked)

    @property
    def synced(self):
        return all(stat.synced for stat in self.sync_status)

    @property
    def is_tracked(self):
        return all(stat.is_tracked for stat in self.sync_status)

    def code(self):
        return ''.join([
            ' ' if self.workdir_status.clean else 'W',
            ' ' if self.index_status.clean else 'I',
            'T' if self.untracked else ' ',
            ' ' if self.synced else 'S',
            ' ' if self.is_tracked else 'U',
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
