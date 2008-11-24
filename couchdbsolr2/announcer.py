# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import couchdb, logging, signal, socket, os
import amqplib.client_0_8 as amqp

try:
    import simplejson as json
except ImportError:
    import json

TYPE_ATTR = 'type'

log = logging.getLogger(__name__)

__all__ = ['UpdateAnnouncer']


class UpdateAnnouncer(object):
    """Send updates to message queue.
    """

    def __init__(self, amqp, couchdb_uri, seqid_file, batch_size=1000):
        self.amqp = amqp
        self.server = couchdb.Server(couchdb_uri)
        self.seqid_file = seqid_file
        self.batch_size = batch_size
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())

    def _announce_updates(self, updates):
        """Send updates out on message queue.

        """
        log.debug('Announcing updates: ' + updates)
        msg = amqp.Message(updates, content_type='application/json')
        self.channel.basic_publish(msg, self.amqp['routing_key'])

    def start_amqp(self):
        self.conn = amqp.Connection(self.amqp['host'], self.amqp['user'],
                                    self.amqp['password'])
        self.channel = self.conn.channel()
        self.channel.access_request(self.amqp['realm'], write=True, active=True)
        self.channel.exchange_declare(self.amqp['routing_key'], 'fanout')

    def shutdown(self):
        self.channel.close()
        self.conn.close()

    def __normalize(self, updates, path, obj):
        if obj is None:
            pass
        elif isinstance(obj, str):
            updates.append({path : obj})
        elif isinstance(obj, list):
            self.__normalize_list(updates, path, obj)
        elif isinstance(obj, dict):
            self.__normalize_dict(updates, path, obj)
        else:
            log.warning("No type matched")

    def __normalize_list(self, updates, path, obj):
        for i, elem in enumerate(obj):
            if path:
                ext_path = "%s/$%d" % (path, i)
            else:
                ext_path = "$%d" % i
            self.__normalize(updates, ext_path, elem)

    def __normalize_dict(self, updates, path, obj):
        for field in obj.keys():
            if path:
                ext_path = "%s/%s" % (path, field)
            else:
                ext_path = field
            self.__normalize(updates, ext_path, obj[field])

    def _index_doc(self, db, doc_id):
        """Collect information on parts of document to index.

        """
        doc = db.get(doc_id)
        if doc is None:
            log.warning("Attempt to index nonexistent document: '%s'" % doc_id)
            return
        fields = doc.get('solr_fields')
        if not fields:
            log.debug("Document '%s' does not define solr_fields" % doc_id)
            return
        updates = []
        for field in fields:
            if doc.has_key(field):
                self.__normalize(updates, field, doc[field])
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

        updated_docs, len_docs = self._next_in_sequence(db, seq_id)
        while len_docs > 0:
            log.debug("Processing %d updates" % len_docs)
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
                if updates:
                    updates = {'type' : 'updated', 'data' : updates}
                    self._announce_updates(json.dumps(updates))
                else:
                    log.info("No updates to announce")

            updated_docs, len_docs = self._next_in_sequence(db, seq_id)

        fp = file(self.seqid_file, 'w')
        json.dump(seq_id, fp)
        fp.close()

    def delete_database(self, db_name):
        log.error("Delete database not yet implemented")
