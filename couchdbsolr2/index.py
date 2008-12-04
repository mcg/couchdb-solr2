#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, sys
from announcer import UpdateAnnouncer
from lineprotocol import LineProtocol
from optparse import OptionParser
from util import read_config
from version import version

log = logging.getLogger(__name__)


def validate_amqp(amqp):
    return amqp and amqp.has_key('host') and amqp.has_key('user') \
        and amqp.has_key('password') and amqp.has_key('routing_key') \
        and amqp.has_key('realm')


def configure(opts):
    defaults = {
        'index' : {
            'seqid' : '.couchdb_seq_id'
        },
        'couchdb' : {
            'uri' : 'http://127.0.0.1:5984/'
        },
        'log' : {
            'file' : 'couchdb-solr2-index.log',
            'level' : 'info'
        }
    }
    config = read_config(opts.config_file, defaults)
    if config is None:
        print >> sys.stderr, 'Configuration file must be provided for connection to AMQP broker'
        return
    if not validate_amqp(config.get('amqp')):
        print >> sys.stderr, 'AMQP configuration is invalid'
        return
    return config


def parse_opts():
    parser = OptionParser(usage="%prog -c FILE",
                          version="CouchDB-Solr2 %s" % version)
    parser.add_option('-c', '--config', dest='config_file',
                      metavar='FILE', default='couchdb-solr2-index.ini',
                      help='Configuration (default: %default)')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    config = configure(opts)
    if config is None:
        return 1
    print config; return 0

    log_format = '[%(asctime)s|%(levelname)s|%(name)s|%(message)s]'
    logging.basicConfig(filename=config['log']['file'],
                        level=config['log']['level'],
                        format=log_format)

    updater = UpdateAnnouncer(config['amqp'], config['couchdb']['uri'],
                              config['index']['seqid'])
    updater.start_amqp()
    protocol = LineProtocol()
    for notify in protocol.input():
        log.debug("Update notification: " + str(notify))

        try:
            db = notify['db']
            taipu = notify['type']
        except KeyError:
            log.exception("Expected keys 'db' and 'type' not found")
            continue

        try:
            if taipu == 'updated':
                updater.update_index(db)
            elif taipu == 'deleted':
                updater.delete_database(db)
            else:
                log.error("Unknown type of update: %s" % taipu)
        except Exception:
            log.exception("Uncaught exception")
            continue
    return 0


if __name__ == '__main__':
    sys.exit(main())
