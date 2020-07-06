#!/usr/bin/env python3
# encoding: utf-8

import traceback

import requests
import telebot

from config import TG_TOKEN, TG_SENDTO, TIMEOUT, PROXIES_DICT
from logger import write_log_warning

BOT = telebot.TeleBot(TG_TOKEN)
telebot.apihelper.proxy = PROXIES_DICT

def send_message(text, user=TG_SENDTO):
    for _ in range(10):
        try:
            BOT.send_message(user, text, parse_mode="Markdown", timeout=TIMEOUT)
        except (requests.exceptions.SSLError, requests.exceptions.ProxyError):
            continue
        except:
            traceback_string = traceback.format_exc()
            print("\n%s\n! Error: failed to post message to Telegram!" % traceback_string)
            write_log_warning(*traceback_string.splitlines())
            write_log_warning("Failed to post message to Telegram!")
        break
    else:
        print("! Fuck GFW!")
        write_log_warning("Fuck GFW!")
