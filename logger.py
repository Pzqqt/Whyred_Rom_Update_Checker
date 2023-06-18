#!/usr/bin/env python3
# encoding: utf-8

import logging
import os
from typing import NoReturn, Union, Final

from config import LOG_FILE, ENABLE_LOGGER

LOGGER: Final = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

LOG_FILE_PATH: Final = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)

_HANDLER = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
_HANDLER.setLevel(logging.INFO)
_HANDLER.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

LOGGER.addHandler(_HANDLER)


def _write_log(level: int, *text: str) -> NoReturn:
    if ENABLE_LOGGER:
        for string in text:
            LOGGER.log(level, string)

def write_log_info(*text: str) -> NoReturn:
    """ 写入info级日志 """
    _write_log(logging.INFO, *text)

def write_log_warning(*text: str) -> NoReturn:
    """ 写入warning级日志 """
    _write_log(logging.WARNING, *text)

_PREFIX_DIC: Final = {
    logging.INFO: "-",
    logging.WARNING: "!",
}

def print_and_log(string: str, level: int = logging.INFO, custom_prefix: Union[str, None] = None) -> NoReturn:
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
