#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import couchdb, logging, socket, sys, os
import amqplib.client_0_8 as amqp
from optparse import OptionParser

try:
    import simplejson as json
except ImportError:
    import json

TYPE_ATTR = 'type'

# TODO: Throw in a config file
AMQP_HOST = '127.0.0.1'
AMQP_USER = 'couchdb-solr2-index'
AMQP_PASS = 'couchdb'
AMQP_KEY = 'x' # Routing key
AMQP_REALM = '/data'

log = logging.getLogger(__name__)


class UpdateHandler(object):

    def __init__(self, couchdb_uri, seqid_file, batch_size=1000):
        self.server = couchdb.Server(couchdb_uri)
        self.seqid_file = seqid_file
        self.batch_size = batch_size

    def _announce_updates(self, updates):
        """Send updates out on message queue.

        """
        log.debug('Updates: ' + updates)
        msg = amqp.Message(updates, content_type='application/json')
        self.channel.basic_publish(msg, AMQP_KEY)

    def _set_up_amqp(self):
        self.conn = amqp.Connection(AMQP_HOST, AMQP_USER, AMQP_PASS)
        self.channel = self.conn.channel()
        self.channel.access_request(AMQP_REALM, write=True, active=True)
        self.channel.exchange_declare(AMQP_KEY, 'fanout')

    def _tear_down_amqp(self):
        self.channel.close()
        self.conn.close()

    def _normalize(self, updates, path, obj):
        if obj is None:
            log.warning("Object is None")
        elif isinstance(obj, str):
            updates.append({path : obj})
        elif isinstance(obj, list):
            self._normalize_list(updates, path, obj)
        elif isinstance(obj, dict):
            self._normalize_dict(updates, path, obj)
        else:
            log.warning("No type matched")

    def _normalize_list(self, updates, path, obj):
        for i, elem in enumerate(obj):
            if path:
                ext_path = "%s/$%d" % (path, i)
            else:
                ext_path = "$%d" % i
            self._normalize(updates, ext_path, elem)

    def _normalize_dict(self, updates, path, obj):
        for field in obj.keys():
            if path:
                ext_path = "%s/%s" % (path, field)
            else:
                ext_path = field
            self._normalize(updates, ext_path, obj[field])

    def _index_doc(self, db, doc_id):
        """Collect information on parts of document to index.

        { id : <id>, 
        """
        log.debug("Processing document %s" % doc_id)
        doc = db.get(doc_id)
        if doc is None:
            return
        fields = doc.get('solr_fields')
        if not fields:
            return
        updates = []
        for field in fields:
            if doc.has_key(field):
                self._normalize(updates, field, doc[field])
        updates.extend([{'type' : doc[TYPE_ATTR]}, {'_id' : doc_id}])
        return updates

    def _next_in_sequence(self, db, seq_id):
        log.debug("Sequence id: %d" % seq_id)
        try:
            updated_docs = db.view('_all_docs_by_seq', startkey=seq_id,
                                   count=self.batch_size)
            return updated_docs, len(updated_docs)
        except socket.error:
            log.exception('Problem connecting to database')
            return [], 0

    def update_index(self, db_name):
        """Process an update notification.

        """
        db = self.server[db_name]
        log.debug("Connected to database '%s'" % db_name)
        try:
            if not os.path.exists(self.seqid_file):
                seq_id = 0
            else:
                fp = file(self.seqid_file)
                seq_id = json.load(fp)
        except Exception:
            log.exception("Problem with sequence id file")
            return

        self._set_up_amqp()

        updated_docs, len_docs = self._next_in_sequence(db, seq_id)
        while len_docs > 0:
            seq_id = updated_docs.rows[len_docs - 1].key

            deleted_docs = [doc.id for doc in updated_docs
                            if doc.value.get('deleted', False)]
            updated_docs = [doc.id for doc in updated_docs
                            if not doc.value.get('deleted', False)]

            if deleted_docs:
                deletes = {'type' : 'deleted', 'data' : deleted_docs}
                self._announce_updates(json.dumps(deletes))

            if updated_docs:
                updates = []
                for doc_id in updated_docs:
                    doc_updates = self._index_doc(db, doc_id)
                    if doc_updates is not None:
                        doc_updates.append({'_db' : db_name})
                        updates.append(doc_updates)
                updates = {'type' : 'updated', 'data' : updates}
                self._announce_updates(json.dumps(updates))

            updated_docs, len_docs = self._next_in_sequence(db, seq_id)

        self._tear_down_amqp()

        fp = file(self.seqid_file, 'w')
        json.dump(seq_id, fp)
        fp.close()

    
def updates():
    line = sys.stdin.readline()
    while line:
        try:
            obj = json.loads(line)
            yield obj
        except ValueError:
            log.exception("Problem with notification")
            return
        line = sys.stdin.readline()


def parse_opts():
    parser = OptionParser()
    parser.add_option('-l', '--log', dest='log_file',
                      metavar='FILE', default='/tmp/couchdb-solr2-index.log',
                      help='Log file')
    parser.add_option('-c', '--couchdb', dest='couchdb_uri',
                      metavar='URI', default='http://127.0.0.1:5984/',
                      help='URI of CouchDB')
    parser.add_option('-s', '--seq-id', dest='seqid_file',
                      metavar='FILE', default='/tmp/.couchdb_seq_id',
                      help='File to store sequence id in')
    return parser.parse_args()


def main():
    opts, args = parse_opts()
    logging.basicConfig(filename=opts.log_file, level=logging.DEBUG,
                        format="%(asctime)s: %(levelname)s: %(message)s")
    updater = UpdateHandler(opts.couchdb_uri, opts.seqid_file)
    for update in updates():
        log.debug("Update notification: " + str(update))
        try:
            db = update['db']
            taipu = update['type']
        except KeyError:
            log.exception("Expected keys 'db' and 'type' not found")
            return 1

        if taipu == 'updated':
            try:
                updater.update_index(db)
            except Exception:
                log.exception("Uncaught exception")
                return 2
        elif taipu == 'deleted':
            pass
        else:
            log.error("Unknown type of update: %s" % taipu)
            return 4
    return 0


if __name__ == '__main__':
    sys.exit(main())
