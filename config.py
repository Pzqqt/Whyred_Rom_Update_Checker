#!/usr/bin/env python3
# encoding: utf-8

import os

# SQLite 数据库文件名
SQLITE_FILE = "saved.db"

# 日志文件名
LOG_FILE = "log.txt"

# 是否启用多线程模式
ENABLE_MULTI_THREAD = True

# 多线程模式时使用的线程数(默认: 4, 建议不要超过8)
MAX_THREADS_NUM = 4

# 是否启用日志
ENABLE_LOGGER = True

# LESS_LOG 为 True 时, 日志文件将不再写入无更新的记录
LESS_LOG = False

# 循环检查的间隔时间(单位: 秒)(默认: 180分钟)
LOOP_CHECK_INTERVAL = 180 * 60

# 代理服务器(为空时则不使用代理)
PROXIES = "127.0.0.1:1080"

# 请求超时
TIMEOUT = 20

# 是否为 Socks5 代理
IS_SOCKS = False

# 是否启用 TG BOT 发送消息的功能
ENABLE_SENDMESSAGE = False

# TG BOT TOKEN
TG_TOKEN = os.environ.get("TG_TOKEN", "")

# 发送消息到...
TG_SENDTO = os.environ.get("TG_SENDTO", "")

if not PROXIES:
    PROXIES_DICT = {}
else:
    if IS_SOCKS:
        PROXIES_DICT = {"http": "socks5h://%s" % PROXIES, "https": "socks5h://%s" % PROXIES}
    else:
        PROXIES_DICT = {"http": PROXIES, "https": PROXIES}
