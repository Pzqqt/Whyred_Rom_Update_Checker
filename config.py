#!/usr/bin/env python3
# encoding: utf-8

import os

# 是否启用调试 若启用 将不再忽略检查过程中发生的任何异常
# 建议在开发环境中启用 在生产环境中禁用
DEBUG_ENABLE = False

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

# 循环检查的间隔时间(默认: 180分钟)
LOOP_CHECK_INTERVAL = 180 * 60

# 代理服务器
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

if IS_SOCKS:
    _PROXIES_DIC = {"http": "socks5h://%s" % PROXIES, "https": "socks5h://%s" % PROXIES}
else:
    _PROXIES_DIC = {"http": PROXIES, "https": PROXIES}
