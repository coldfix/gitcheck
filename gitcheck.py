#! /usr/bin/env python

import os
import sys
import subprocess

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

    untracked = False
    clean = True
    branch = None

    def __init__(self, folder):
        status = subprocess.check_output(self.GIT_STATUS, cwd=folder)

        index_flags = set()
        workdir_flags = set()
        for l in status.decode('utf-8').splitlines():
            if l.startswith('## '):
                if l.endswith('ahead'):
                    self.branch = 'ahead'
                elif l.endswith('behind'):
                    self.branch = 'behind'
                elif l.endswith('diverged'):
                    self.branch = 'diverged'
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
        return self.workdir_status.clean and self.index_status.clean

    def code(self):
        return ''.join([
            ' ' if self.workdir_status.clean else 'W',
            ' ' if self.index_status.clean else 'I',
            'T' if self.untracked else ' ',
            'B' if self.branch else ' ',
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
