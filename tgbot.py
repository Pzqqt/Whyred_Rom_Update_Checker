#!/usr/bin/env python3
# encoding: utf-8

import traceback
import logging
import os
from tempfile import mkstemp
from typing import Final

import telebot
from telebot.apihelper import requests
from telebot.types import InputFile

from config import TG_TOKEN, TG_SENDTO, TIMEOUT, PROXIES, ENABLE_LOGGER
from logger import print_and_log, LOGGER


BOT: Final = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = PROXIES

def _send_wrap(func):
    def _func(*args, **kwargs):
        for _ in range(10):
            try:
                func(*args, **kwargs)
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
                return
            else:
                # 成功发送
                return
        print_and_log("Fuck GFW!", level=logging.WARNING)
    return _func

@_send_wrap
def send_message(text: str, send_to: str = TG_SENDTO, parse_mode="Markdown", **kwargs):
    BOT.send_message(send_to, text, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs)

@_send_wrap
def send_photo(photo, caption: str = "", send_to: str = TG_SENDTO, parse_mode="Markdown", **kwargs):
    try:
        BOT.send_photo(send_to, photo, caption=caption, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs)
    except telebot.apihelper.ApiTelegramException as exc:
        if isinstance(photo, str) and exc.description == 'Bad Request: wrong file identifier/HTTP URL specified':
            temp_fd, temp_path = mkstemp()
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(requests.get(photo, proxies=PROXIES, timeout=TIMEOUT).content)
                BOT.send_photo(
                    send_to, InputFile(temp_path), caption=caption, parse_mode=parse_mode, timeout=TIMEOUT, **kwargs
                )
            finally:
                os.remove(temp_path)
        else:
            raise

