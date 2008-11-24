#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, sys
from daemon import daemonize
from optparse import OptionParser
from updater import SolrUpdater
from util import read_config


def validate_amqp(amqp):
    return amqp and amqp.has_key('host') and amqp.has_key('user') \
        and amqp.has_key('password') and amqp.has_key('routing_key') \
        and amqp.has_key('realm') and amqp.has_key('queue')


def parse_opts():
    parser = OptionParser()
    parser.add_option('-l', '--log', dest='log_file',
                      metavar='FILE', default='couchdb-solr2-update.log',
                      help='Write log to FILE (default: %default)')
    parser.add_option('-p', '--pid', dest='pid_file',
                      metavar='FILE', default='couchdb-solr2-update.pid',
                      help="Write daemon's PID to FILE (default: %default)")
    parser.add_option('-n', '--no-daemonize', dest='no_daemonize',
                      action='store_true', default=False,
                      help="Don't daemonize (default: daemonize)")
    parser.add_option('-s', '--solr', dest='solr_uri',
                      metavar='IF', default='127.0.0.1:8080',
                      help='Solr interface (default: %default)')
    parser.add_option('-a', '--amqp-config', dest='amqp_file',
                      metavar='FILE', default='couchdb-solr2-index.ini',
                      help='AMQP configuration (default: %default)')
    return parser.parse_args()


def main():
    opts, args = parse_opts()

    config = read_config(opts.amqp_file)
    if config is None:
        print 'AMQP configuration not found'
        return 1
    if not validate_amqp(config.get('amqp')):
        print 'AMQP configuration is invalid'
        return 1

    if opts.no_daemonize is False:
        daemonize(opts.pid_file)

    # File handles will be closed during daemonisation
    logging.basicConfig(filename=opts.log_file, level=logging.DEBUG,
                        format='[%(asctime)s|%(levelname)s|%(name)s|%(threadName)s|%(message)s]')

    updater = SolrUpdater(config['amqp'], opts.solr_uri)
    updater.process_updates()
    return 0


if __name__ == '__main__':
    sys.exit(main())
