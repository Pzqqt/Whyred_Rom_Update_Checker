#!/usr/bin/env python3
# encoding: utf-8

import traceback

import telebot

from config import TG_TOKEN, TG_SENDTO, _PROXIES_DIC
from logger import write_log_warning

BOT = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = _PROXIES_DIC

def send_message(text, user=TG_SENDTO):
    try:
        BOT.send_message(user, text)
    except:
        # try again
        try:
            BOT.send_message(user, text)
        except:
            traceback_string = traceback.format_exc()
            print(traceback_string)
            print("! Error: failed to post message to Telegram!")
            write_log_warning(*traceback_string.splitlines())
            write_log_warning("Failed to post message to Telegram!")
