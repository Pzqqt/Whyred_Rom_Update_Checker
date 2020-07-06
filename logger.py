#!/usr/bin/env python3
# encoding: utf-8

import logging

from config import LOG_FILE, ENABLE_LOGGER

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(level=logging.INFO)

_HANDLER = logging.FileHandler(LOG_FILE)
_HANDLER.setLevel(logging.INFO)
_HANDLER.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

LOGGER.addHandler(_HANDLER)

def write_log_info(*text):
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.info(string)
def write_log_warning(*text):
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.warning(string)

_PREFIX_FUNC_DIC = {
    "info": ("-", write_log_info),
    "warning": ("!", write_log_warning),
}

def print_and_log(string, level="info", custom_prefix=""):
    prefix = custom_prefix if custom_prefix else _PREFIX_FUNC_DIC.get(level, ("-",))[0]
    log_func = _PREFIX_FUNC_DIC.get(level, (None, write_log_info))[1]
    print(prefix, string)
    log_func(string)
