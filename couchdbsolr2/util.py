# -*- coding: utf-8 -*-
#
# Copyright (c) 2008 Jacinto Ximénez de Guzmán
#
# Code licensed under the MIT License. See COPYING or
# http://www.opensource.org/licenses/mit-license.php
# for details.

import logging, os
from ConfigParser import ConfigParser

__all__ = ['read_config', 'string2log_level']


def read_config(config_file, defaults={}):
    """Parse a configuration file.

    :param config_file: Path to configuration file
    :param defaults: Default settings (see return value for structure)
    :return: A dictionary where keys are sections of the file and
             values are dictionaries of definitions in said section.

    Returns None if file is not found.
    """
    if not os.path.isfile(config_file):
        return None

    config = ConfigParser()
    config.readfp(file(config_file))

    settings = {}
    for section in config.sections():
        settings[section] = dict(config.items(section))

    for key in defaults.keys():
        if settings.has_key(key):
            defaults[key].update(settings[key])
    keys = [key for key in settings.keys() if key not in defaults.keys()]
    for key in keys:
        defaults[key] = settings[key]
    return defaults


def string2log_level(level):
    levels = {
        'debug' : logging.DEBUG,
        'info' : logging.INFO,
        'warning' : logging.WARNING,
        'error' : logging.ERROR,
        'critical' : logging.CRITICAL
    }
    return levels.get(level, logging.NOTSET)
