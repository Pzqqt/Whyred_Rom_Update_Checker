#!/usr/bin/env python3
# encoding: utf-8

import logging

from config import LOG_FILE, ENABLE_LOGGER

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(level=logging.INFO)

def _build_handler():
    handler = logging.FileHandler(LOG_FILE)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    return handler

_LOGGER.addHandler(_build_handler())

if ENABLE_LOGGER:
    def write_log_info(*text):
        for string in text:
            _LOGGER.info(string)
    def write_log_warning(*text):
        for string in text:
            _LOGGER.warning(string)
else:
    def write_log_info(*text): pass
    def write_log_warning(*text): pass
