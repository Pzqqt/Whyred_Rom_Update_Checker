#!/usr/bin/env python3
# encoding: utf-8

import os
from typing import Final, Dict, Union

# SQLite 数据库文件名
SQLITE_FILE: Final = "saved.db"

# 日志文件名
LOG_FILE: Final = "log.txt"

# 是否启用多线程模式
ENABLE_MULTI_THREAD: Final = True

# 多线程模式时使用的线程数(默认: 4, 建议不要超过8)
MAX_THREADS_NUM: Final = 4

# 是否启用日志
ENABLE_LOGGER: Final = True

# LESS_LOG 为 True 时, 日志文件将不再写入无更新的记录
LESS_LOG: Final = False

# 循环检查的间隔时间(单位: 秒)(默认: 180分钟)
LOOP_CHECK_INTERVAL: Final = 180 * 60

# 代理服务器, 默认从环境变量中读取http_proxy和https_proxy, 也可以根据情况自己设置
PROXIES: Final[Dict[str, Union[str, None]]] = {
    "http": os.getenv("http_proxy", os.getenv("HTTP_PROXY", "")),
    "https": os.getenv("https_proxy", os.getenv("HTTPS_PROXY", "")),
}

# 请求超时
TIMEOUT: Final = 20

# 是否启用 TG BOT 发送消息的功能
ENABLE_SENDMESSAGE: Final = False

# TG BOT TOKEN
TG_TOKEN: Final[str] = os.getenv("TG_TOKEN", "")

# 发送消息到...
TG_SENDTO: Final[str] = os.getenv("TG_SENDTO", "")
