#!/usr/bin/env python3
# encoding: utf-8

import logging

from config import LOG_FILE, LOGGER_ENABLE

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(level=logging.INFO)

def build_handler():
    handler = logging.FileHandler(LOG_FILE)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    return handler

LOGGER.addHandler(build_handler())

def write_log_info(text):
    if LOGGER_ENABLE:
        LOGGER.info(text)

def write_log_warning(text):
    if LOGGER_ENABLE:
        LOGGER.warning(text)