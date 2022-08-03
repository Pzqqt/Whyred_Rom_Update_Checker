#!/usr/bin/env python3
# encoding: utf-8

import traceback

import telebot
from telebot.apihelper import requests

from config import TG_TOKEN, TG_SENDTO, TIMEOUT, PROXIES
from logger import print_and_log

BOT = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = PROXIES

def send_message(text, user=TG_SENDTO):
    for _ in range(10):
        try:
            BOT.send_message(user, text, parse_mode="Markdown", timeout=TIMEOUT)
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            # 由于网络或代理问题没能发送成功, 就再试一次, 最多尝试10次
            continue
        except:
            # 由于其他原因没能发送成功(比如消息文本的格式不对), 则把异常记录下来, 并放弃发送
            for line in traceback.format_exc().splitlines():
                print_and_log(line, level="warning")
            print_and_log("Failed to post message to Telegram!", level="warning")
            return
        else:
            # 成功发送消息
            return
    print_and_log("Fuck GFW!", level="warning")
