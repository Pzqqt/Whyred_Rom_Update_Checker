#!/usr/bin/env python3
# encoding: utf-8

import logging
import os

from config import LOG_FILE, ENABLE_LOGGER

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(level=logging.INFO)

_HANDLER = logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE))
_HANDLER.setLevel(logging.INFO)
_HANDLER.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

LOGGER.addHandler(_HANDLER)

def write_log_info(*text):
    """ 写入info级日志 """
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.info(string)

def write_log_warning(*text):
    """ 写入warning级日志 """
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.warning(string)

_PREFIX_FUNC_DIC = {
    "info": ("-", write_log_info),
    "warning": ("!", write_log_warning),
}

def print_and_log(string, level="info", custom_prefix=None):
    """ 打印到terminal的同时写入日志
    :param string: 要打印的字符串
    :param level: 日志级别
    :param custom_prefix: 自定义字符串前缀
    """
    prefix, log_func = _PREFIX_FUNC_DIC.get(level, ("-", write_log_info))
    if custom_prefix is not None:
        prefix = custom_prefix
    if prefix:
        print(prefix, string)
    else:
        print(string)
    log_func(string)
