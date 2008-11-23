# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, sys

try:
    import simplejson as json
except ImportError:
    import json

log = logging.getLogger(__name__)

__all__ = ['couchdb_line_protocol']


def couchdb_line_protocol():
    line = sys.stdin.readline()
    while line:
        try:
            obj = json.loads(line)
            yield obj
        except ValueError:
            log.exception("Problem with notification")
            return
        line = sys.stdin.readline()
