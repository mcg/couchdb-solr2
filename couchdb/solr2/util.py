# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import os
from ConfigParser import ConfigParser

__all__ = ['read_config']


def read_config(config_file):
    if not os.path.isfile(config_file):
        return None

    config = ConfigParser()
    config.readfp(file(config_file))

    settings = {}
    for section in config.sections():
        settings[section] = dict(config.items(section))
    return settings
