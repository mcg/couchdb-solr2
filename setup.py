#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

from setuptools import setup
from couchdbsolr2.version import version


setup(
    name='CouchDB-Solr2',
    description='Integrates full-text indexing and searching with CouchDB',
    url='http://github.com/deguzman/couchdb-solr2/tree/master',
    version=version,
    author='Jacinto Ximénez de Guzmán',
    author_email='x.de.guzman.j@gmail.com',
    license='MIT',
    install_requires=['amqplib', 'threadpool >= 1.2.4'],
    packages=['couchdbsolr2'],
    entry_points={
        'console_scripts' : [
            'couchdb-solr2-index = couchdbsolr2.index:main',
            'couchdb-solr2-update = couchdbsolr2.update:main',
            'couchdb-solr2-query = couchdbsolr2.query:main',
        ]
    },
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Text Processing :: Indexing',
    ],
)
