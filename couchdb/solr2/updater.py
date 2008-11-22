# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, threadpool, time
import amqplib.client_0_8 as amqp
from daemon import DaemonMixin
from solr import SolrConnection

try:
    import simplejson as json
except ImportError:
    import json

try:
    import cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

__all__ = ['Updater']


class Updater(DaemonMixin):

    def __init__(self, amqp, workers=10, sleep_time=0.05):
        self.amqp = amqp
        self.pool = threadpool.ThreadPool(workers)
        self.sleep_time = sleep_time

    @classmethod
    def xml_field(cls, parent, name, value):
        field = ET.SubElement(parent, 'field')
        field.attrib['name'] = name
        field.text = value

    def _send_update(self, *args, **kwargs):
        """
["[{\"address\": \"Puerto Rico\
"}, {\"AddressDetails/CountryNameCode\": \"PR\"}, {\"type\": \"Location\"}, {\"_
id\": \"15308041f5d1dbe4ab3e41d14d8e5032\"}]"]
        """
        msg = args[0]
        updates = json.loads(msg.body)
        add = ET.Element('add')
        for update in updates:
            doc = ET.SubElement(add, 'doc')
            for fields in update:
                for k, v in fields.items(): # There should only be one pair
                    Updater.xml_field(doc, k, v)
        #solr = SolrConnection(self, solr_uri)
        #solr.doUpdateXML(ET.tostring(add))
        log.debug("Sending update to Solr: " + ET.tostring(add))

    def _on_receive(self, msg):
        """Called when an update request is retrieved from AMQP queue."""
        log.info("Received update request")
        req = threadpool.WorkRequest(self._send_update, args=[msg])
        self.pool.putRequest(req)

    def process_updates(self):
        """Main eval loop."""
        self._set_up_amqp()
        req = threadpool.WorkRequest(self.__poll_workers)
        self.pool.putRequest(req)
        self.channel.basic_consume(self.amqp['amqp_queue'],
                                   callback=self._on_receive, no_ack=True)
        log.info("Waiting for updates")
        while True:
            self.channel.wait()

    def __poll_workers(self):
        """Poll for completed worker threads."""
        log.info("Starting thread to poll workers")
        while True:
            try:
                self.pool.poll()
            except threadpool.NoResultsPending:
                pass
            time.sleep(self.sleep_time)

    def _handle_term(self, signal, frame):
        log.debug("Preparing to exit")
        self.channel.close()
        self.conn.close()
        DaemonMixin._handle_term(self, signal, frame)

    def _set_up_amqp(self):
        self.conn = amqp.Connection(self.amqp['amqp_host'],
                                    self.amqp['amqp_user'],
                                    self.amqp['amqp_pass'])
        self.channel = self.conn.channel()
        self.channel.access_request(self.amqp['amqp_realm'],
                                    read=True, active=True)
        self.channel.exchange_declare(self.amqp['amqp_key'], 'fanout')
        self.channel.queue_declare(self.amqp['amqp_queue'])
        self.channel.queue_bind(self.amqp['amqp_queue'], self.amqp['amqp_key'])
