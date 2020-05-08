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

_PREFIX_FUNC_DIC = {
    "info": ("-", write_log_info),
    "warning": ("!", write_log_warning),
}

def print_and_log(string, level="info", custom_prefix=""):
    prefix = custom_prefix if custom_prefix else _PREFIX_FUNC_DIC.get(level, ("-",))[0]
    log_func = _PREFIX_FUNC_DIC.get(level, (None, write_log_info))[1]
    print(prefix, string)
    log_func(string)
