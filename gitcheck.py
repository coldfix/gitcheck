#! /usr/bin/env python
"""
gitcheck - recursively check for unclean/unpushed git repositories.

Usage:
    gitcheck [PATH] [-a] [--branches] [--ignore PATH]... [--maxdepth DEPTH]
    gitcheck -h

Options:
    -a, --all                       Show all repositories, even if clean
    --branches                      Show untracked branches
    -i PATH --ignore PATH           Ignore this path
    -m LVL, --maxdepth LVL          Maximum recursion depth

    -h, --help                      Show this help
"""

import os
import subprocess
import re

from docopt import docopt


#----------------------------------------
# Constants
#----------------------------------------

# Check status of index/workdir
GIT_STATUS = ['git', 'status', '--porcelain', '--branch']
GIT_STASH = ['git', 'stash', 'list']

# Get sync status for each branch
SYNC_STATUS = ['git', 'for-each-ref', 'refs/heads',
               '--format', '%(refname:short)...%(upstream:short) %(push:track)']
SYNC_PART = re.compile(r'\[([^\[\]]*)\]$')

# Related commands:
# - List remotes for all branches:
#       git config --get-regexp ^branch\..*\.remote$
# - Get remote for a specific branch:
#       git rev-parse --symbolic-full-name --abbrev-ref master@{u}


def realpath(p):
    return os.path.normpath(os.path.realpath(p))


class GitSyncStatus:

    gone = False
    ahead = 0
    behind = 0

    def __init__(self, branch, remote, divergence):
        self.branch = branch
        self.remote = remote
        self.is_tracked = bool(remote)
        sync_status = SYNC_PART.match(divergence)
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
            try:
                remote, divergence = remote.split(maxsplit=1)
            except ValueError:
                pass
        return cls(branch.strip(), remote.strip(), divergence.strip())

    @property
    def synced(self):
        return self.ahead == 0 and self.behind == 0 and not self.gone

    def info(self):
        if self.is_tracked:
            code = '<' if self.behind > 0 else ''
            code += '>' if self.ahead > 0 else ''
            code = code or '='
        else:
            code = 'U'
        return '{:9}{:2} {}'.format(
            '', code, self.branch)


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
                self.head_sync = GitSyncStatus.parse(l[3:])
            elif l.startswith('?? '):
                self.untracked = True
            else:
                i, w = l[:2]
                index_flags.add(i)
                workdir_flags.add(w)

        self.workdir_status = GitFlags(workdir_flags)
        self.index_status = GitFlags(index_flags)

        stash_list = subprocess.check_output(GIT_STASH, cwd=folder)
        self.num_stash_entries = len(stash_list.splitlines())

        sync_output = subprocess.check_output(SYNC_STATUS, cwd=folder)
        self.branch_sync = [
            GitSyncStatus.parse(line)
            for line in sync_output.decode('utf-8').splitlines()
        ]

    @property
    def clean(self):
        return (self.workdir_status.clean and
                self.index_status.clean and
                self.synced and
                self.head_sync.is_tracked and
                self.num_untracked_branches == 0)

    @property
    def synced(self):
        return all(stat.synced for stat in self.branch_sync
                   if not stat.branch.startswith('_'))

    @property
    def num_untracked_branches(self):
        head = self.head_sync.branch
        return sum(1 for stat in self.branch_sync
                   if not stat.branch.startswith('_')
                   and stat.branch != head
                   and not stat.is_tracked)

    def code(self):
        return ''.join([
            ' ' if self.workdir_status.clean else 'W',
            ' ' if self.index_status.clean else 'I',
            'T' if self.untracked else ' ',
            ' ' if self.synced else 'L',
            ' ' if self.head_sync.is_tracked else 'H',
            ' ' if self.num_untracked_branches == 0 else 'B',
            ' ' if self.num_stash_entries == 0 else 'S',
        ])

    @classmethod
    def legend(cls):
        return '\n'.join([
            'W      ' + ' dirty work-dir',
            ' I     ' + ' Uncommited index',
            '  T    ' + ' Untracked files',
            '   L   ' + ' Local unsynchronized branches',
            '    H  ' + ' Head not tracked by remote',
            '     B ' + ' Untracked branches',
            '      S' + ' Stashed entries',
        ])


def collect_git_repositories(folder, ignore, maxdepth):
    normpath = realpath(folder)
    if normpath in ignore:
        return
    ignore.add(normpath)

    subdirs = [fname for fname in os.listdir(folder)
               if os.path.isdir(os.path.join(folder, fname))]
    if '.git' in subdirs:
        yield folder
        return
    if maxdepth == 0:
        return
    for subdir in subdirs:
        if subdir.startswith('.'):
            continue
        subfolder = os.path.join(folder, subdir)
        yield from collect_git_repositories(subfolder, ignore, maxdepth-1)


def show_repos(folder=None, ignore=(), show_branch_details=False, maxdepth=-1, show_clean=False):
    if folder is None:
        folder = '.'
    folder = os.path.realpath(folder)
    ignore = set(map(realpath, ignore))

    for folder in collect_git_repositories(folder, ignore, maxdepth):
        status = GitStatus(folder)
        if status.clean and not show_clean:
            continue
        print(status.code(), folder)

        if show_branch_details:
            for stat in status.branch_sync:
                if not stat.synced or not stat.is_tracked:
                    print(stat.info())


def main(args=None):
    opts = docopt(__doc__, args)
    print(GitStatus.legend())
    show_repos(
        opts['PATH'],
        opts['--ignore'],
        show_branch_details=opts['--branches'],
        maxdepth=int(opts['--maxdepth'] or -1),
        show_clean=opts['--all'])


if __name__ == '__main__':
    main()
