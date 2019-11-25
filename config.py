#!/usr/bin/env python3
# encoding: utf-8

# SQLite 数据库文件名
SQLITE_FILE = "saved.db"

# 日志文件名
LOG_FILE = "log.txt"

# 是否启用日志
LOGGER_ENABLE = True

# 循环检查的间隔时间(360分钟)
LOOP_CHECK_INTERVAL = 360 * 60

# 代理服务器
PROXIES = "127.0.0.1:1080"

# 请求超时
TIMEOUT = 20

# 是否为 Socks5 代理
IS_SOCKS = True

# 是否启用 TG BOT 发送消息的功能
SENDMESSAGE_ENABLE = False

# TG BOT TOKEN
TG_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHI"

# 发送消息到...
TG_SENDTO = "@******"

if IS_SOCKS:
    PROXIES_DIC = {"http": "socks5h://%s" % PROXIES, "https": "socks5h://%s" % PROXIES}
else:
    PROXIES_DIC = {"http": PROXIES, "https": PROXIES}
