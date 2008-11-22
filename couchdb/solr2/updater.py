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

log = logging.getLogger(__name__)

__all__ = ['Updater']


class Updater(DaemonMixin):

    def __init__(self, amqp, workers=10, sleep_time=0.05):
        self.amqp = amqp
        self.pool = threadpool.ThreadPool(workers)
        self.sleep_time = sleep_time

    def _send_update(self, *args, **kwargs):
        msg = args[0]
        log.debug("Handling update: " + msg.body)

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
