# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, socket, threadpool, time
import amqplib.client_0_8 as amqp
from solr import SolrConnection, SolrException

try:
    import simplejson as json
except ImportError:
    import json

try:
    import cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

__all__ = ['SolrUpdater']


class SolrUpdater(object):

    def __init__(self, amqp, solr_uri, sleep_time=0.1):
        self.amqp = amqp
        self.solr_uri = solr_uri
        self.sleep_time = sleep_time
        self.pool = None
        self.workers = 0

    @classmethod
    def xml_field(cls, parent, name, value):
        field = ET.SubElement(parent, 'field')
        field.attrib['name'] = name
        field.text = value

    def _send_update(self, *args, **kwargs):
        """Send an update message to Solr.

        Solr commits are made only after deletion.
        """
        try:
            msg = args[0]
            updates = json.loads(msg.body)
            solr = SolrConnection(self.solr_uri)
            if updates['type'] == 'updated':
                add = ET.Element('add')
                for update in updates['data']:
                    doc = ET.SubElement(add, 'doc')
                    for fields in update:
                        # There should only be one pair
                        for k, v in fields.items():
                            SolrUpdater.xml_field(doc, solr.escapeKey(k),
                                                  solr.escapeVal(v))
                log.debug("Sending update to Solr: " + ET.tostring(add))
                resp = solr.doUpdateXML(ET.tostring(add))
                log.debug("Solr response: " + resp)
            elif updates['type'] == 'deleted':
                for id in updates['data']:
                    log.debug("Deleting %s" % id)
                solr.delete(id)
                solr.commit()
            elif updates['type'] == 'deleted_db':
                solr.deleteByQuery("_db:%s" % updates['data'])
                solr.commit()
            else:
                log.warning("Unrecognized update type: '%s'" % updates['type'])
        except SolrException:
            log.exception("Exception when contacting Solr")
        except Exception:
            log.exception("Unexpected exception")

    def _on_receive(self, msg):
        """Called when an update request is retrieved from AMQP queue."""
        log.info("Received update request")
        req = threadpool.WorkRequest(self._send_update, args=[msg])
        self.pool.putRequest(req)

    def process_updates(self, workers=10):
        """Main eval loop.

        """
        self.workers = workers
        self.pool = threadpool.ThreadPool(self.workers)
        req = threadpool.WorkRequest(self.__poll_workers)
        self.pool.putRequest(req)
        self.channel.basic_consume(self.amqp['queue'],
                                   callback=self._on_receive,
                                   no_ack=True)
        log.info("Waiting for updates")
        while True:
            self.channel.wait()

    def __poll_workers(self):
        log.info("Started thread to poll workers")
        while True:
            try:
                self.pool.poll()
            except threadpool.NoResultsPending:
                pass
            time.sleep(self.sleep_time)

    def start_amqp(self):
        try:
            self.conn = amqp.Connection(self.amqp['host'],
                                        self.amqp['user'],
                                        self.amqp['password'])
            self.channel = self.conn.channel()
            self.channel.access_request(self.amqp['realm'],
                                        read=True, active=True)
            self.channel.exchange_declare(self.amqp['routing_key'], 'fanout')
            self.channel.queue_declare(self.amqp['queue'])
            self.channel.queue_bind(self.amqp['queue'], self.amqp['routing_key'])
        except socket.error:
            return False
        return True

    def shutdown(self):
        if self.pool is not None:
            self.pool.dismissWorkers(self.workers, True)
        self.channel.close()
        self.conn.close()
