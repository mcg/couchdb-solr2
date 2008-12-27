# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import couchdb, logging, socket, os
import amqplib.client_0_8 as amqp

try:
    import simplejson as json
except ImportError:
    import json

TYPE_ATTR = 'type'

log = logging.getLogger(__name__)

__all__ = ['UpdateAnnouncer']


class UpdateAnnouncer(object):
    """Send notification of database updates to AMQP broker.

    """

    def __init__(self, amqp, couchdb_uri, seqid_file, batch_size=1000):
        """Constructor.

        :param amqp: AMQP configuration
        :param couchdb_uri: CouchDB URI
        :param seqid_file: Path to file containing last sequence id
        :param batch_size: Max updated documents to pull at once
        """
        self.amqp = amqp
        self.server = couchdb.Server(couchdb_uri)
        self.seqid_file = seqid_file
        self.batch_size = batch_size

    def _announce_updates(self, updates):
        """Send updates out on message queue.

        :param updates: Update structure to be serialized and sent
        """
        serialized = json.dumps(updates)
        log.debug('Sending serialized message: ' + serialized)
        msg = amqp.Message(serialized, content_type='application/json')
        self.channel.basic_publish(msg, self.amqp['routing_key'])

    def start_amqp(self):
        """Connect to AMQP broker.

        """
        try:
            self.conn = amqp.Connection(self.amqp['host'], self.amqp['user'],
                                        self.amqp['password'])
            self.channel = self.conn.channel()
            self.channel.access_request(self.amqp['realm'], write=True, active=True)
            self.channel.exchange_declare(self.amqp['routing_key'], 'fanout')
        except socket.error:
            return False
        return True

    def shutdown(self):
        """Clean up AMQP resources.

        """
        self.channel.close()
        self.conn.close()

    def __normalize(self, updates, path, obj):
        if obj is None:
            pass
        elif isinstance(obj, str) or isinstance(obj, int) or isinstance(obj, float):
            updates.append({path : obj})
        elif isinstance(obj, list):
            self.__normalize_list(updates, path, obj)
        elif isinstance(obj, dict):
            self.__normalize_dict(updates, path, obj)
        else:
            log.error("Unhandled field type: " + str(type(obj)))

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
        """Collect document fields to be indexed by Solr.

        """
        doc = db.get(doc_id)
        if doc is None:
            log.warning("Unable to find document in database: '%s'" % doc_id)
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

    def next_in_sequence(self, db, seq_id):
        try:
            updated_docs = db.view('_all_docs_by_seq', startkey=seq_id,
                                   count=self.batch_size)
            len_docs = len(updated_docs)
            while len_docs > 0:
                seq_id = updated_docs.rows[len_docs - 1].key
                yield (updated_docs, len_docs, seq_id)
                updated_docs = db.view('_all_docs_by_seq', startkey=seq_id,
                                       count=self.batch_size)
                len_docs = len(updated_docs)
        except socket.error:
            log.exception('Problem connecting to database')

    def read_sequence_ids(self):
        if os.path.fexists(self.seqid_file):
            try:
                return json.load(file(self.seqid_file))
            except Exception:
                log.exception('Error reading sequence id file')
        return {}

    def write_sequence_ids(self, seqids):
        json.dump(seqids, file(self.seqid_file, 'w'))

    def update_index(self, db_name):
        """Announce updates to a database

        For messages announcing deleted documents, the type is 'deleted'
        and data is a list of the ids of the deleted documents.

        For updated documents, the type is 'updated'. FIXME: list
        of lists of dictionaries should be made into a list of dictionaries.

        :param db_name: Name of updated database
        """
        db = self.server[db_name]
        log.debug("Connected to database '%s'" % db_name)

        seqids = self.read_sequence_ids()
        seqid = seqids.get(db_name, 0)
        for updated_docs, len_docs, new_seqid in self.next_in_sequence(db, seqid):
            log.info("Processing %d update(s)" % len_docs)
            seqid = new_seqid

            deleted_docs = [doc.id for doc in updated_docs
                            if doc.value.get('deleted', False)]
            updated_docs = [doc.id for doc in updated_docs
                            if not doc.value.get('deleted', False)]

            if deleted_docs:
                deletes = {'type' : 'deleted', 'data' : deleted_docs}
                self._announce_updates(deletes)

            if updated_docs:
                updates = []
                for doc_id in updated_docs:
                    doc_updates = self._index_doc(db, doc_id)
                    if doc_updates is not None:
                        doc_updates.append({'_db' : db_name})
                        updates.append(doc_updates)
                if updates:
                    self._announce_updates({'type' : 'updated', 'data' : updates})

        seqids.update({db_name : seqid})
        self.write_sequence_ids(seqids)

    def delete_database(self, db_name):
        """Announce that database was deleted.

        Message type is 'deleted_db' and data is the name of the deleted
        database.

        :param db_name: Name of deleted database
        """
        seqids = self.read_sequence_ids()
        if seqids.has_key(db_name):
            del seqids[db_name]
            self.write_sequence_ids(seqids)
        self._announce_updates({'type' : 'deleted_db', 'data' : db_name})
