#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, signal, sys
from daemon import daemonize
from optparse import OptionParser
from updater import SolrUpdater
from util import *
from version import version


def validate_amqp(amqp):
    return amqp and amqp.has_key('host') and amqp.has_key('user') \
        and amqp.has_key('password') and amqp.has_key('routing_key') \
        and amqp.has_key('realm') and amqp.has_key('queue')


def configure(config_file):
    defaults = {
        'log' : {
            'file' : 'couchdb-solr2-update.log',
            'level' : 'info'
        },
        'solr' : {
            'uri' : 'http://127.0.0.1:8080/solr'
        }
    }
    config = read_config(config_file, defaults)
    if config is None:
        print >> sys.stderr, 'Configuration file must be provided for connection to AMQP broker'
        return
    if not validate_amqp(config.get('amqp')):
        print >> sys.stderr, 'AMQP configuration is invalid'
        return
    return config


def parse_opts():
    parser = OptionParser(usage="%prog -c FILE [-n] [-p FILE]",
                          version="CouchDB-Solr2 %s" % version)
    parser.add_option('-p', '--pid', dest='pid_file',
                      metavar='FILE', default='couchdb-solr2-update.pid',
                      help="Write daemon's PID to FILE (default: %default)")
    parser.add_option('-n', '--no-daemonize', dest='no_daemonize',
                      action='store_true', default=False,
                      help="Don't daemonize (default: daemonize)")
    parser.add_option('-c', '--config', dest='config_file',
                      metavar='FILE', default='couchdb-solr2-update.ini',
                      help='Configuration (default: %default)')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    config = configure(opts.config_file)
    if config is None:
        return 1

    if opts.no_daemonize is False:
        daemonize(opts.pid_file)

    # File handles will be closed during daemonization
    log_format = '[%(asctime)s|%(levelname)s|%(name)s|%(threadName)s|%(message)s]'
    logging.basicConfig(filename=config['log']['file'],
                        level=string2log_level(config['log']['level']),
                        format=log_format)

    updater = SolrUpdater(config['amqp'], config['solr']['uri'])
    if updater.start_amqp() is False:
        print >> sys.stderr, "Problem connecting to AMQP broker"
        return 2
    signal.signal(signal.SIGTERM, lambda s, f: updater.shutdown())
    updater.process_updates()
    return 0


if __name__ == '__main__':
    sys.exit(main())
