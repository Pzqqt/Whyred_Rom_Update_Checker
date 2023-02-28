#!/usr/bin/env python3
# encoding: utf-8

from argparse import ArgumentParser
import json
import time
import traceback
import sys
import threading
import logging
import typing
from typing import NoReturn, Optional, Final, Union
from concurrent.futures import ThreadPoolExecutor

from requests import exceptions as req_exceptions

from config import (
    ENABLE_SENDMESSAGE, LOOP_CHECK_INTERVAL, ENABLE_MULTI_THREAD, MAX_THREADS_NUM, LESS_LOG, ENABLE_LOGGER
)
from check_init import PAGE_CACHE, CheckUpdate
from check_list import CHECK_LIST
from database import DatabaseSession, Saved
from logger import write_log_info, write_log_warning, print_and_log, LOGGER

# 为True时将强制将数据保存至数据库并发送消息
FORCE_UPDATE = False

_THREADING_LOCK: Final = threading.Lock()

def database_cleanup() -> set[str]:
    """
    将数据库中存在于数据库但不存在于CHECK_LIST的项目删除掉
    :return: 被删除的项目名字的集合
    """
    with DatabaseSession() as session:
        saved_ids = {x.ID for x in session.query(Saved).all()}
        checklist_ids = {x.__name__ for x in CHECK_LIST}
        drop_ids = saved_ids - checklist_ids
        for id_ in drop_ids:
            session.delete(session.query(Saved).filter(Saved.ID == id_).one())
        session.commit()
        return drop_ids

def get_time_str(time_num: Optional[Union[int, float]] = None, offset: int = 0) -> str:
    """
    返回给定时间的字符串形式
    :param time_num: Unix时间, 整型或浮点型, 默认取当前时间
    :param offset: time_num的偏移量
    :return: 格式化后的时间字符串
    """
    if time_num is None:
        time_num = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_num+offset))

def _abort(text: str) -> NoReturn:
    print_and_log(str(text), level=logging.WARNING, custom_prefix="-")
    sys.exit(1)

def _abort_by_user() -> NoReturn:
    _abort("Abort by user")

def _sleep(sleep_time: int) -> NoReturn:
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        _abort_by_user()

def check_one(cls: typing.Union[type, str], disable_pagecache: bool = False) -> (bool, CheckUpdate):
    """ 对CHECK_LIST中的一个项目进程更新检查

    :param cls: 要检查的CheckUpdate类或类名
    :param disable_pagecache: 为True时强制禁用页面缓存
    :return: (<bool值, 顺利完成检查为True, 否则为False>, <CheckUpdate对象>)
    """
    if isinstance(cls, str):
        cls_str = cls
        cls = {cls_.__name__: cls_ for cls_ in CHECK_LIST}.get(cls_str)
        if not cls:
            raise Exception("Can not found '%s' from CHECK_LIST!" % cls_str)
    cls_obj = cls()
    if disable_pagecache:
        cls_obj.enable_pagecache = False
    try:
        cls_obj.do_check()
    except req_exceptions.ReadTimeout:
        print_and_log("%s check failed! Timeout." % cls_obj.fullname, level=logging.WARNING)
    except (req_exceptions.SSLError, req_exceptions.ProxyError):
        print_and_log("%s check failed! Proxy error." % cls_obj.fullname, level=logging.WARNING)
    except req_exceptions.ConnectionError:
        print_and_log("%s check failed! Connection error." % cls_obj.fullname, level=logging.WARNING)
    except req_exceptions.HTTPError as error:
        print_and_log("%s check failed! %s." % (cls_obj.fullname, error), level=logging.WARNING)
    except:
        if ENABLE_LOGGER:
            LOGGER.exception("Error while checking %s:" % cls_obj.fullname)
            write_log_warning("%s check failed!" % cls_obj.fullname)
            print("! %s check failed! See exception details through log file." % cls_obj.fullname)
        else:
            print(traceback.format_exc())
            print("! %s check failed!" % cls_obj.fullname)
    else:
        if FORCE_UPDATE or cls_obj.is_updated():
            if cls_obj.name in ["GoogleClangPrebuilt", "Switch520"]:
                latest_version_string = "..."
            else:
                latest_version_string = cls_obj.info_dic["LATEST_VERSION"]
            print_and_log(
                "%s has update: %s" % (cls_obj.fullname, latest_version_string),
                custom_prefix=">",
            )
            try:
                cls_obj.after_check()
            except:
                warning_string = "Something wrong when running after_check!"
                if ENABLE_LOGGER:
                    LOGGER.exception("%s: %s" % (cls_obj.fullname, warning_string))
                    print("!", cls_obj.fullname, warning_string, "See exception details through log file.")
                else:
                    print(traceback.format_exc())
                    print("!", cls_obj.fullname, warning_string)
            cls_obj.write_to_database()
            if ENABLE_SENDMESSAGE:
                cls_obj.send_message()
        else:
            print("- %s no update" % cls_obj.fullname)
            if not LESS_LOG:
                write_log_info("%s no update" % cls_obj.fullname)
        return True, cls_obj
    return False, cls_obj

def single_thread_check(check_list: typing.Sequence[type]) -> (list, bool):
    # 单线程模式下连续检查失败5项则判定为网络异常, 并提前终止
    req_failed_flag = 0
    check_failed_list = []
    is_network_error = False
    for cls in check_list:
        rc, _ = check_one(cls)
        if not rc:
            req_failed_flag += 1
            check_failed_list.append(cls)
            if req_failed_flag == 5:
                is_network_error = True
                break
        else:
            req_failed_flag = 0
        _sleep(2)
    return check_failed_list, is_network_error

def multi_thread_check(check_list: typing.Sequence[type]) -> (list, bool):
    # 多线程模式下累计检查失败10项则判定为网络异常, 并在之后往线程池提交的任务中不再进行检查操作而是直接返回
    check_failed_list = []
    is_network_error = False

    def _check_one(cls_):
        nonlocal check_failed_list, is_network_error
        with _THREADING_LOCK:
            if is_network_error:
                return
        rc, _ = check_one(cls_)
        time.sleep(2)
        if not rc:
            with _THREADING_LOCK:
                check_failed_list.append(cls_)
                if len(check_failed_list) >= 10:
                    is_network_error = True

    with ThreadPoolExecutor(MAX_THREADS_NUM) as executor:
        executor.map(_check_one, check_list)
    return check_failed_list, is_network_error

def loop_check() -> NoReturn:
    write_log_info("Run database cleanup before start")
    drop_ids = database_cleanup()
    write_log_info("Abandoned items: {%s}" % ", ".join(drop_ids))
    loop_check_func = multi_thread_check if ENABLE_MULTI_THREAD else single_thread_check
    check_list = [cls for cls in CHECK_LIST if not cls._skip]
    while True:
        start_time = get_time_str()
        print(" - " + start_time)
        print(" - Start...")
        write_log_info("=" * 64)
        write_log_info("Start checking at %s" % start_time)
        # loop_check_func必须返回两个值,
        # 检查失败的项目的列表, 以及是否为网络错误或代理错误的Bool值
        check_failed_list, is_network_error = loop_check_func(check_list)
        if is_network_error:
            print_and_log("Network or proxy error! Sleep...", level=logging.WARNING)
        else:
            if check_failed_list:
                # 对于检查失败的项目, 强制单线程检查
                print_and_log("Check again for failed items")
                single_thread_check(check_failed_list)
        PAGE_CACHE.clear()
        print(" - The next check will start at %s\n" % get_time_str(offset=LOOP_CHECK_INTERVAL))
        write_log_info("End of check")
        _sleep(LOOP_CHECK_INTERVAL)

def get_saved_json() -> str:
    """ 以json格式返回已保存的数据 """
    with DatabaseSession() as session:
        return json.dumps(
            [
                result.get_kv()
                for result in sorted(session.query(Saved), key=lambda x: x.FULL_NAME)
            ],
            # ensure_ascii=False,
        )

def show_saved_data() -> NoReturn:
    """ 打印已保存的数据 """
    with DatabaseSession() as session:
        results = session.query(Saved).with_entities(Saved.ID, Saved.FULL_NAME, Saved.LATEST_VERSION)
        kv_dic = {k: (v1, v2) for k, v1, v2 in results if k not in ["GoogleClangPrebuilt", "Switch520"]}
    try:
        # 可以的话, 使用rich库
        import rich
    except ImportError:
        # 以MySQL命令行风格打印
        id_maxlen = len(max(kv_dic.keys(), key=len))
        fn_maxlen = max([len(x[0]) for x in kv_dic.values()])
        lv_maxlen = max([len(x[1]) for x in kv_dic.values()])
        print("+%s+%s+%s+" % ("-" * id_maxlen, "-" * fn_maxlen, "-" * lv_maxlen))
        print("|%s|%s|%s|" % (
            "ID".ljust(id_maxlen), "Full Name".ljust(fn_maxlen), "Latest Version".ljust(lv_maxlen)
        ))
        print("+%s+%s+%s+" % ("-" * id_maxlen, "-" * fn_maxlen, "-" * lv_maxlen))
        for id_ in sorted(kv_dic.keys()):
            fn, lv = kv_dic[id_]
            print("|%s|%s|%s|" % (
                id_.ljust(id_maxlen), fn.ljust(fn_maxlen), lv.ljust(lv_maxlen)
            ))
        print("+%s+%s+%s+" % ("-" * id_maxlen, "-" * fn_maxlen, "-" * lv_maxlen))
    else:
        del rich
        from rich.console import Console
        from rich.table import Table

        console = Console()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Full Name")
        table.add_column("Latest Version")
        for id_ in sorted(kv_dic.keys()):
            table.add_row(id_, *kv_dic[id_])

        console.print(table)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--force", help="Force to think it/they have updates", action="store_true")
    parser.add_argument("--dontpost", help="Do not send message to Telegram", action="store_true")
    parser.add_argument("-a", "--auto", help="Automatically loop check all items", action="store_true")
    parser.add_argument("-c", "--check", help="Check one item")
    parser.add_argument("-s", "--show", help="Show saved data", action="store_true")
    parser.add_argument("-j", "--json", help="Show saved data as json", action="store_true")

    args = parser.parse_args()

    if args.force:
        FORCE_UPDATE = True
    if args.dontpost:
        ENABLE_SENDMESSAGE = False
    if args.auto:
        loop_check()
    elif args.check:
        if not check_one(args.check, disable_pagecache=True)[0]:
            sys.exit(1)
    elif args.show:
        show_saved_data()
    elif args.json:
        print(get_saved_json())
    else:
        parser.print_usage()
