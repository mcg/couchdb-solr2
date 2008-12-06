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
from solr import SolrConnection
from lineprotocol import LineProtocol

try:
    import simplejson as json
except ImportError:
    import json

log = logging.getLogger(__name__)


def query_failed():
    ret = {
        'code' : 500,
        'body' : 'Bad query'
    }
    return ret


def build_query(request):
    try:
        db_name = request['db']
        search = request['query']
        query = search['q']

        doctype = search.get('type')
        count = search.get('count', 25)
        offset = search.get('offset', 0)

        if 'type' in search: del search['type']
        if 'count' in search: del search['count']
        if 'offset' in search: del search['offset']

        queries = ['_db:%s' % db_name]
        if doctype is not None:
            queries.append('type:%s' % doctype)
        queries.append(query)

        params = {
            'q' : ' AND '.join(queries),
            'rows' : count,
            'start' : offset,
            'wt' : 'json',
        }
        for key in [key for key in search.keys() if key not in params]:
            params[key] = search[key]
        return params
    except KeyError:
        log.exception("Missing expected parameter")
        return


def parse_opts():
    parser = OptionParser()
    parser.add_option('-l', '--log', dest='log_file',
                      metavar='FILE', default='couchdb-solr2-query.log',
                      help='Write log to FILE (default: %default)')
    parser.add_option('-s', '--solr', dest='solr_uri',
                      metavar='URI', default='http://127.0.0.1:8080/solr',
                      help='Solr URI (default: %default)')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    logging.basicConfig(filename=opts.log_file, level=logging.DEBUG,
                        format='[%(asctime)s|%(levelname)s|%(name)s|%(threadName)s|%(message)s]')

    solr = SolrConnection(opts.solr_uri)
    protocol = LineProtocol()
    for request in protocol.input():
        try:
            query = build_query(request)
            if query is None:
                protocol.output(query_failed(), True)
                continue
            log.debug("Running query: " + str(query))
            resp = json.loads(solr.search(**query))
            ret = {
                'code' : 200,
                'json' : resp['response']
            }
            protocol.output(ret, True)
        except Exception:
            log.exception("Uncaught exception")
    return 0


if __name__ == '__main__':
    sys.exit(main())
