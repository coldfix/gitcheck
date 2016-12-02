#!/usr/bin/env python
# encoding: utf-8
from setuptools import setup
from distutils.util import convert_path


long_description = None
try:
    long_description = open('README.rst').read()
    long_description += '\n' + open('CHANGES.rst').read()
except IOError:
    pass


setup(
    name='gitcheck',
    version='0.0.0',
    description='',
    long_description=long_description,
    author='Thomas Gläßle',
    author_email='t_glaessle@gmx.de',
    url='https://github.com/coldfix/gitcheck',
    license='GPLv3+',
    py_modules=['gitcheck'],
    install_requires=[
        'docopt',
    ],
    entry_points={
        'console_scripts': [
            'gitcheck = gitcheck:main',
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],
)
