# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging

class LogHelper(object):
    """Singleton for easily logging to same destination from multiple modules"""

    instance = None
    log_file = 'log'
    level = logging.DEBUG

    def _init(self):
        logging.basicConfig(level=LogHelper.level, filename=LogHelper.log_file,
                            filemode='w',
                            format='[%(asctime)s|%(levelname)s|%(name)s|%(threadName)s|%(message)s]')

    def get_logger(self, name):
        return logging.getLogger(name)

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = LogHelper()
            cls.instance._init()
            logging.debug("Created logger")
        return cls.instance

    @classmethod
    def shutdown(cls):
        logging.shutdown()
