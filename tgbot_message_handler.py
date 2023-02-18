#!/usr/bin/env python3
# encoding: utf-8

import re
from typing import Final

from telebot.types import Message
from sqlalchemy.orm import exc as sqlalchemy_exc

from tgbot import BOT
from config import ENABLE_LOGGER
from database import Saved
from check_list import CHECK_LIST
from main import check_one, _get_time_str
from logger import LOG_FILE_PATH


BOT_MASTER_USERNAME: Final = "Pzqqt"
CHECK_LIST_STR: Final = tuple(sorted([cls.__name__ for cls in CHECK_LIST]))

def _is_master(message: Message):
    return message.from_user.username == BOT_MASTER_USERNAME

def _edit_message(message: Message, text: str, parse_mode="Markdown", **kwargs):
    BOT.edit_message_text(text, message.chat.id, message.message_id, parse_mode=parse_mode, **kwargs)

@BOT.message_handler(commands=["start", "help"], chat_types=["private", ])
def _(message):
    message_text = """<b>Usage:</b>
/check_list - Returns all item ids in the checklist.
/get_latest - Get the latest version info for an item."""
    if _is_master(message):
        message_text += """
/check - Check for updates to an item immediately.
/log - Get the log file."""
    BOT.reply_to(message, message_text, parse_mode="html")

@BOT.message_handler(commands=["check_list", ], chat_types=["private", ])
def _(message):
    BOT.reply_to(
        message,
        "*Check list:*\n" + '\n'.join(['- `%s`' % r for r in CHECK_LIST_STR]),
        parse_mode="Markdown",
    )

@BOT.message_handler(commands=["check", ], chat_types=["private", ], func=_is_master)
def _(message):
    re_match = re.search(r'^/check\s+(.*?)$', message.text)
    if not re_match:
        BOT.reply_to(
            message,
            "<b>Usage:</b> /check &lt;item_name&gt;\n\nEnter /check_list to list all checkable items.",
            parse_mode="html",
        )
        return
    check_item_name = re_match.group(1).strip()
    if check_item_name not in CHECK_LIST_STR:
        BOT.reply_to(
            message,
            "*Error:* `%s` does not exist in the checklist!" % check_item_name,
            parse_mode="Markdown",
        )
        return

    rt = "*Checking for updates, please wait...*"
    m = BOT.reply_to(message, rt, parse_mode="Markdown")

    rt += "\n\n*Result:* "
    rc, check_update_obj = check_one(check_item_name, disable_pagecache=True)
    if not rc:
        rt += "Check failed!"
        if ENABLE_LOGGER:
            rt += " Check the cause of failure through log file."
        _edit_message(m, rt)
        return
    if check_update_obj.is_updated():
        _edit_message(m, rt + "Has update.")
    else:
        _edit_message(m, rt + "No update.")

@BOT.message_handler(commands=["get_latest", ], chat_types=["private", ])
def _(message):
    re_match = re.search(r'^/get_latest\s+(.*?)$', message.text)
    if not re_match:
        BOT.reply_to(
            message,
            "<b>Usage:</b> /get_latest &lt;item_name&gt;\n\nEnter /check_list to list all checkable items.",
            parse_mode="html",
        )
        return
    check_item_name = re_match.group(1).strip()
    if check_item_name not in CHECK_LIST_STR:
        BOT.reply_to(
            message,
            "*Error:* `%s` does not exist in the checklist!" % check_item_name,
            parse_mode="Markdown",
        )
        return
    try:
        saved = Saved.get_saved_info(check_item_name)
    except sqlalchemy_exc.NoResultFound:
        BOT.reply_to(
            message,
            "*Error:* `%s` does not exist in the database!" % check_item_name,
            parse_mode="Markdown",
        )
        return
    if saved.LATEST_VERSION is None or check_item_name in ["GoogleClangPrebuilt", "Switch520"]:
        BOT.reply_to(
            message,
            "*%s*\n\n*Sorry, this item has not been saved in the database.*" % saved.FULL_NAME,
            parse_mode="Markdown",
        )
        return
    latest_version = saved.LATEST_VERSION
    if latest_version.startswith("http"):
        latest_version = "[%s](%s)" % (latest_version, latest_version)
    else:
        latest_version = "`%s`" % latest_version
    reply_message_text = "*%s*\n\n*Latest version:*\n%s" % (saved.FULL_NAME, latest_version)
    download_link = saved.DOWNLOAD_LINK
    if download_link is not None:
        if download_link.startswith("http"):
            download_link = "[%s](%s)" % (download_link, download_link)
        reply_message_text += "\n\n*Download:*\n%s" % download_link
    BOT.reply_to(message, reply_message_text, parse_mode="Markdown")

@BOT.message_handler(commands=["log", ], chat_types=["private", ], func=_is_master)
def _(message):
    with open(LOG_FILE_PATH, 'rb') as f:
        BOT.send_document(message.chat.id, f, reply_to_message_id=message.message_id)

def update_listener(messages):
    for message in messages:
        print(_get_time_str(message.date), '-', message.from_user.username + ':', message.text)

if __name__ == "__main__":
    BOT.set_update_listener(update_listener)
    BOT.infinity_polling()
