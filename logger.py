#!/usr/bin/env python3
# encoding: utf-8

import logging
import logging.handlers
import os
import traceback
from typing import Union, Final

from config import LOG_FILE, LOG_FILE_MAX_BYTES, LOG_FILE_BACKUP_COUNT, ENABLE_LOGGER


if not os.path.isabs(LOG_FILE):
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)

LOGGER: Final = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

_HANDLER = logging.handlers.RotatingFileHandler(
    LOG_FILE,
    encoding="utf-8",
    maxBytes=LOG_FILE_MAX_BYTES,
    backupCount=LOG_FILE_BACKUP_COUNT,
)
_HANDLER.setLevel(logging.INFO)
_HANDLER.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

LOGGER.addHandler(_HANDLER)


def _write_log(level: int, *text: str):
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.log(level, string)

def write_log_info(*text: str):
    """ 写入info级日志 """
    _write_log(logging.INFO, *text)

def write_log_warning(*text: str):
    """ 写入warning级日志 """
    _write_log(logging.WARNING, *text)

def record_exceptions(warning_string: str):
    """ 记录异常 """
    if ENABLE_LOGGER:
        LOGGER.exception(warning_string)
        print("!", warning_string, "See exception details through log file.")
    else:
        print(traceback.format_exc())
        print("!", warning_string)

_PREFIX_DIC: Final = {
    logging.INFO: "-",
    logging.WARNING: "!",
}

def print_and_log(string: str, level: int = logging.INFO, custom_prefix: Union[str, None] = None):
    """ 打印到terminal的同时写入日志
    :param string: 要打印的字符串
    :param level: 日志级别
    :param custom_prefix: 自定义字符串前缀, 前缀只在terminal显示, 不写入日志
    """
    prefix = _PREFIX_DIC.get(level) if custom_prefix is None else custom_prefix
    if prefix:
        print(prefix, string)
    else:
        print(string)
    _write_log(level, string)
