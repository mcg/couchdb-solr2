#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, sys
from optparse import OptionParser
from couchdb.solr2 import Updater

# TODO: Throw in a config file
AMQP_HOST = '127.0.0.1'
AMQP_USER = 'couchdb-solr2-update'
AMQP_PASS = 'couchdb'
AMQP_KEY = 'x' # Routing key
AMQP_REALM = '/data'
AMQP_QUEUE = 'updates'


def parse_opts():
    parser = OptionParser()
    parser.add_option('-l', '--log', dest='log_file',
                      metavar='FILE', default='/tmp/couchdb-solr2-update.log',
                      help='Log file')
    parser.add_option('-p', '--pid', dest='pid_file',
                      metavar='FILE', default='/var/run/couchdb-solr2-update.pid',
                      help='PID file')
    parser.add_option('-n', '--no-daemonize', dest='no_daemonize',
                      action='store_true', default=False,
                      help="Don't daemonize")
    parser.add_option('-s', '--solr', dest='solr_uri',
                      metavar='URI', default='127.0.0.1:8080',
                      help='Solr URI')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    amqp = {
        'amqp_host' : AMQP_HOST,
        'amqp_user' : AMQP_USER,
        'amqp_pass' : AMQP_PASS,
        'amqp_key' : AMQP_KEY,
        'amqp_realm' : AMQP_REALM,
        'amqp_queue' : AMQP_QUEUE
    }
    updater = Updater(opts.solr_uri, amqp)
    if opts.no_daemonize is False:
        updater.daemonize(opts.pid_file)

    # File handles will be closed during daemonisation
    logging.basicConfig(filename=opts.log_file, level=logging.DEBUG,
                        format="%(asctime)s: %(levelname)s: %(message)s")

    updater.process_updates()
    return 0


if __name__ == '__main__':
    sys.exit(main())
