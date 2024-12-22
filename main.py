#!/usr/bin/env python3
# encoding: utf-8

from argparse import ArgumentParser
import json
import time
import traceback
import sys
import logging
import typing
from typing import Optional, Union, Tuple, Final
from concurrent.futures import ThreadPoolExecutor, as_completed

from requests import exceptions as req_exceptions

from config import (
    ENABLE_SENDMESSAGE, LOOP_CHECK_INTERVAL, ENABLE_MULTI_THREAD, MAX_THREADS_NUM, LESS_LOG, ENABLE_LOGGER, PROXIES
)
from check_init import PAGE_CACHE, CheckUpdate, CheckMultiUpdate, GithubReleases
from check_list import CHECK_LIST
from common import request_url
from database import DatabaseSession, Saved
from logger import write_log_info, write_log_warning, print_and_log, LOGGER
from tgbot import retry_send_messages

# 为True时将强制将数据保存至数据库并发送消息
FORCE_UPDATE = False
PROXY_TEST_URL: Final = "https://www.google.com"

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

def _abort(text: str):
    print_and_log(str(text), level=logging.WARNING, custom_prefix="-")
    sys.exit(1)

def _abort_by_user():
    _abort("Abort by user")

def _sleep(sleep_time: int):
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        _abort_by_user()

if sys.platform == "linux":
    import signal
    signal.signal(signal.SIGTERM, lambda signum, frame: _abort("Received stop signal, aborting..."))

def check_one(cls: typing.Union[type, str], disable_pagecache: bool = False) -> Tuple[bool, CheckUpdate]:
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
    elif isinstance(cls, type):
        if not issubclass(cls, CheckUpdate):
            raise ValueError("%s is not the subclass of CheckUpdate!" % cls)
    else:
        raise ValueError("Invalid parameter: %s!" % cls)
    if disable_pagecache:
        if cls.enable_pagecache:
            cls = type(cls.__name__, (cls, ), {"enable_pagecache": False})
    cls_obj = cls()
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
            if isinstance(cls_obj, CheckMultiUpdate):
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

def single_thread_check(check_list: typing.Sequence[type]) -> Tuple[list, bool]:
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

def multi_thread_check(check_list: typing.Sequence[type]) -> Tuple[list, bool]:
    # 多线程模式下累计检查失败10项则判定为网络异常, 并取消剩下所有的任务
    check_failed_list = []
    is_network_error = False

    with ThreadPoolExecutor(MAX_THREADS_NUM) as executor:
        futures = {}
        for cls in check_list:
            future = executor.submit(check_one, cls)
            futures[future] = cls
        for future in as_completed(futures):
            is_success, _ = future.result()
            if not is_success:
                check_failed_list.append(futures[future])
                if len(check_failed_list) >= 10:
                    is_network_error = True
                    executor.shutdown(wait=True, cancel_futures=True)
                    break
        return check_failed_list, is_network_error

def loop_check():
    write_log_info("Run database cleanup before start")
    drop_ids = database_cleanup()
    write_log_info("Abandoned items: {%s}" % ", ".join(drop_ids))
    loop_check_func = multi_thread_check if ENABLE_MULTI_THREAD else single_thread_check
    check_list = [cls for cls in CHECK_LIST if not cls._skip]
    if len([x for x in check_list if issubclass(x, GithubReleases)]) / (LOOP_CHECK_INTERVAL / (60 * 60)) >= 60:
        for warm_str in (
            "#" * 72,
            "Your check list contains too many items that need to request GitHub api,",
            "which may exceed the rate limit of GitHub api (60 per hour).",
            "Please try to remove some items from the check list,",
            "or increase the time interval of loop check (LOOP_CHECK_INTERVAL).",
            "#" * 72,
        ):
            print_and_log(warm_str, level=logging.WARNING)
    if PROXIES:
        # 检查代理是否正常
        print_and_log("Check whether the proxy is working properly")
        while True:
            try:
                request_url(PROXY_TEST_URL)
                break
            except req_exceptions.RequestException:
                print_and_log(
                    "The proxy does not seem to be working properly, try again in 60 seconds...",
                    level=logging.WARNING,
                )
                _sleep(60)
        print_and_log("OK, the proxy works fine")
    while True:
        start_time = get_time_str()
        print(" - " + start_time)
        write_log_info("=" * 64)
        retry_send_messages()
        print(" - Start...")
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

def show_saved_data():
    """ 打印已保存的数据 """
    ignore_ids = {k for k, v in {cls_.__name__: cls_ for cls_ in CHECK_LIST}.items() if issubclass(v, CheckMultiUpdate)}
    with DatabaseSession() as session:
        results = session.query(Saved).with_entities(Saved.ID, Saved.FULL_NAME, Saved.LATEST_VERSION)
        kv_dic = {k: (v1, v2) for k, v1, v2 in results if k not in ignore_ids}
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
