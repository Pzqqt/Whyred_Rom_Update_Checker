#!/usr/bin/env python3
# encoding: utf-8

import traceback
import logging
import os
import threading
from tempfile import mkstemp
from typing import Final, ContextManager
from functools import wraps
from contextlib import contextmanager

import telebot
from telebot.apihelper import requests
from telebot.types import InputFile

from common import request_url
from config import TG_TOKEN, TG_SENDTO, TIMEOUT, PROXIES, ENABLE_LOGGER
from logger import print_and_log, LOGGER


BOT: Final = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = PROXIES

__send_failed_list = list()
__send_failed_list_lock = threading.RLock()

def _send_wrap(func):
    # 注意: 被`_send_wrap`装饰的函数将忽略函数原本的返回值
    @wraps(func)
    def _func(*args, **kwargs) -> bool:
        for _ in range(10):
            try:
                func(*args, **kwargs)
                # 成功发送
                return True
            except (requests.exceptions.SSLError, requests.exceptions.ProxyError, requests.exceptions.ReadTimeout):
                # 由于网络或代理问题没能发送成功, 就再试一次, 最多尝试10次
                continue
            except:
                # 由于其他原因没能发送成功(比如消息文本的格式不对), 则把异常记录下来, 并放弃发送
                warning_string = "Failed to post message to Telegram!"
                if ENABLE_LOGGER:
                    LOGGER.exception(warning_string)
                    print("!", warning_string, "See exception details through log file.")
                else:
                    print(traceback.format_exc())
                    print("!", warning_string)
                return False
        print_and_log("Fuck GFW!", level=logging.WARNING)
        with __send_failed_list_lock:
            __send_failed_list.append((func, (args, kwargs)))
        return False
    return _func

def retry_send_messages():
    """ 尝试重新发送之前由于网络或代理问题没能发送成功的消息 """
    with __send_failed_list_lock:
        send_failed_list_copy = __send_failed_list.copy()
        __send_failed_list.clear()
    if not send_failed_list_copy:
        return
    send_success_count = 0
    for _func, _arg in send_failed_list_copy:
        _args, _kwargs = _arg
        if _send_wrap(_func)(*_args, **_kwargs):
            send_success_count += 1
    print_and_log("retry_send_messages: %d messages were successfully resent." % send_success_count)
    with __send_failed_list_lock:
        if __send_failed_list:
            print_and_log(
                "retry_send_messages: But there are still %d messages that have not been successfully sent."
                % len(__send_failed_list)
            )

@contextmanager
def _mkstemp(*args, **kwargs) -> ContextManager:
    _temp_fd, _temp_path = mkstemp(*args, **kwargs)
    try:
        yield _temp_fd, _temp_path
    finally:
        os.remove(_temp_path)

@_send_wrap
def send_message(text: str, send_to: str = TG_SENDTO, parse_mode="Markdown", **kwargs):
    BOT.send_message(send_to, text, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs)

@_send_wrap
def send_photo(photo, caption: str = "", send_to: str = TG_SENDTO, parse_mode="Markdown", **kwargs):
    try:
        BOT.send_photo(send_to, photo, caption=caption, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs)
    except telebot.apihelper.ApiTelegramException as exc:
        if isinstance(photo, str) and exc.error_code == 400:
            with _mkstemp() as (temp_fd, temp_path):
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(request_url(photo).content)
                BOT.send_photo(
                    send_to, InputFile(temp_path), caption=caption, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs
                )
        else:
            raise
