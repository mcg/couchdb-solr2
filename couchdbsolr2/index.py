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

log = logging.getLogger(__name__)


def validate_amqp(amqp):
    return amqp and amqp.has_key('host') and amqp.has_key('user') \
        and amqp.has_key('password') and amqp.has_key('routing_key') \
        and amqp.has_key('realm')


def parse_opts():
    parser = OptionParser()
    parser.add_option('-l', '--log', dest='log_file',
                      metavar='FILE', default='couchdb-solr2-index.log',
                      help='Write log to FILE (default: %default)')
    parser.add_option('-c', '--couchdb', dest='couchdb_uri',
                      metavar='URI', default='http://127.0.0.1:5984/',
                      help='CouchDB URI (default: %default)')
    parser.add_option('-s', '--seq-id', dest='seqid_file',
                      metavar='FILE', default='.couchdb_seq_id',
                      help='Store CouchDB sequence id in FILE (default: %default)')
    parser.add_option('-a', '--amqp-config', dest='amqp_file',
                      metavar='FILE', default='couchdb-solr2-index.ini',
                      help='AMQP configuration (default: %default)')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    logging.basicConfig(filename=opts.log_file, level=logging.DEBUG,
                        format="%(asctime)s: %(levelname)s: %(message)s")

    config = read_config(opts.amqp_file)
    if config is None:
        print 'AMQP configuration not found'
        return 1
    if not validate_amqp(config.get('amqp')):
        print 'AMQP configuration is invalid'
        return 2

    updater = UpdateAnnouncer(config['amqp'], opts.couchdb_uri, opts.seqid_file)
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
