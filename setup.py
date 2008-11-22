#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

from setuptools import setup

setup(
    name='CouchDB Solr2',
    version='0.1',
    description='',
    author='Jacinto Ximénez de Guzmán',
    author_email='x.de.guzman.j@gmail.com',
    license='MIT',
    install_requires=['amqplib', 'threadpool >= 1.2.4'],
    packages=['couchdb.solr2'],
    namespace_packages=['couchdb'],
    entry_points={
        'console_scripts' : [
            'couchdb-solr2-index = couchdb.solr2.index:main',
            'couchdb-solr2-update = couchdb.solr2.update:main',
        ]
    }
)
