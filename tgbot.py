#!/usr/bin/env python3
# encoding: utf-8

import telebot

from config import TG_TOKEN, TG_SENDTO, PROXIES_DIC
from logger import write_log_warning

bot = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = PROXIES_DIC

def send_message(text, user=TG_SENDTO):
    try:
        bot.send_message(user, text)
    except Exception as error:
        print("!", error)
        print("! Error: failed to post message to Telegram!")
        write_log_warning("Failed to post message to Telegram!")
