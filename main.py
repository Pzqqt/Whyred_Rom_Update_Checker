#!/usr/bin/env python3
# encoding: utf-8

from argparse import ArgumentParser
import time
import traceback
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from requests import exceptions

from config import DEBUG_ENABLE, ENABLE_SENDMESSAGE, LOOP_CHECK_INTERVAL, \
                   ENABLE_MULTI_THREAD, MAX_THREADS_NUM
from check_init import PAGE_CACHE
from check_list import CHECK_LIST
from database import create_dbsession, Saved
from tgbot import send_message
from logger import write_log_info, write_log_warning, print_and_log

# 为True时将强制将数据保存至数据库并发送消息
FORCE_UPDATE = False

if ENABLE_MULTI_THREAD:
    _THREADING_LOCK = threading.Lock()

def database_cleanup():
    """
    将数据库中存在于数据库但不存在于CHECK_LIST的项目删除掉
    :return: 被删除的项目名字的集合
    """
    with create_dbsession() as session:
        saved_ids = {x.ID for x in session.query(Saved).all()}
        checklist_ids = {x.__name__ for x in CHECK_LIST}
        drop_ids = saved_ids - checklist_ids
        for id_ in drop_ids:
            session.delete(session.query(Saved).filter(Saved.ID == id_).one())
        session.commit()
        return drop_ids

def _abort(text):
    print_and_log(str(text), level="warning", custom_prefix="-")
    sys.exit(1)

def _abort_by_user():
    return _abort("Abort by user")

def _sleep(sleep_time):
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        _abort_by_user()

def _get_time_str(time_num=None, offset=0):
    if time_num is None:
        time_num = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_num+offset))

def check_one(cls, debug_enable=DEBUG_ENABLE):
    if isinstance(cls, str):
        cls = {cls_.__name__: cls_ for cls_ in CHECK_LIST}.get(cls)
        if cls is None:
            raise Exception("Can not found '%s' from CHECK_LIST!" % cls)
    cls_obj = cls()
    try:
        cls_obj.do_check()
    except exceptions.ReadTimeout:
        print_and_log("%s check failed! Timeout." % cls_obj.fullname, level="warning")
    except (exceptions.SSLError, exceptions.ProxyError):
        print_and_log("%s check failed! Proxy error." % cls_obj.fullname, level="warning")
    except exceptions.ConnectionError:
        print_and_log("%s check failed! Connection error." % cls_obj.fullname, level="warning")
    except exceptions.HTTPError as error:
        print_and_log("%s check failed! %s." % (cls_obj.fullname, error), level="warning")
    except:
        traceback_string = traceback.format_exc()
        print(traceback_string)
        write_log_warning(*traceback_string.splitlines())
        print_and_log("%s check failed!" % cls_obj.fullname, level="warning")
    else:
        if cls_obj.is_updated() or FORCE_UPDATE:
            print_and_log(
                "%s has update: %s" % (cls_obj.fullname, cls_obj.info_dic["LATEST_VERSION"]),
                custom_prefix=">",
            )
            try:
                cls_obj.after_check()
            except:
                traceback_string = traceback.format_exc()
                print("\n%s\n! Something wrong when running after_check!" % traceback_string)
                write_log_warning(*traceback_string.splitlines())
                write_log_warning("%s: Something wrong when running after_check!" % cls_obj.fullname)
            cls_obj.write_to_database()
            if ENABLE_SENDMESSAGE:
                send_message(cls_obj.get_print_text())
        else:
            print_and_log("%s no update" % cls_obj.fullname)
        return True
    if debug_enable:
        if input("* Continue?(Y/N) ").upper() != "Y":
            _abort_by_user()
    return False

def single_thread_check():
    # 单线程模式下连续检查失败5项则判定为网络异常, 并提前终止
    req_failed_flag = 0
    check_failed_list = []
    is_network_error = False
    for cls in CHECK_LIST:
        if not check_one(cls):
            req_failed_flag += 1
            check_failed_list.append(cls)
            if req_failed_flag == 5:
                is_network_error = True
                break
        else:
            req_failed_flag = 0
        _sleep(2)
    return check_failed_list, is_network_error

def multi_thread_check():
    # 多线程模式下累计检查失败10项则判定为网络异常, 并在之后往线程池提交的任务中不再进行检查操作而是直接返回
    check_failed_list = []
    is_network_error = False

    def _check_one(cls_):
        nonlocal check_failed_list, is_network_error
        if is_network_error:
            return
        result = check_one(cls_, debug_enable=False)
        time.sleep(2)
        if not result:
            with _THREADING_LOCK:
                check_failed_list.append(cls_)
            if len(check_failed_list) >= 10:
                with _THREADING_LOCK:
                    is_network_error = True

    with ThreadPoolExecutor(MAX_THREADS_NUM) as executor:
        executor.map(_check_one, CHECK_LIST)
    return check_failed_list, is_network_error

def loop_check():
    write_log_info("Run database cleanup before start")
    drop_ids = database_cleanup()
    write_log_info("Abandoned items: {%s}" % ", ".join(drop_ids))
    loop_check_func = multi_thread_check if ENABLE_MULTI_THREAD else single_thread_check
    while True:
        start_time = _get_time_str()
        print(" - " + start_time)
        print(" - Start...")
        write_log_info("=" * 64)
        write_log_info("Start checking at %s" % start_time)
        # loop_check_func必须返回两个值,
        # 检查失败的项目的列表, 以及是否为网络错误或代理错误的Bool值
        check_failed_list, is_network_error = loop_check_func()
        if is_network_error:
            print_and_log("Network or proxy error! Sleep...", level="warning")
        else:
            # 对于检查失败的项目, 强制单线程检查
            print_and_log("Check again for failed items")
            for cls in check_failed_list:
                check_one(cls)
        PAGE_CACHE.clear()
        print(" - The next check will start at %s\n" % _get_time_str(offset=LOOP_CHECK_INTERVAL))
        write_log_info("End of check")
        _sleep(LOOP_CHECK_INTERVAL)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--force", help="Force save to database & send message to Telegram", action="store_true")
    parser.add_argument("--dontpost", help="Do not send message to Telegram", action="store_true")
    parser.add_argument("-a", "--auto", help="Automatically loop check all items", action="store_true")
    parser.add_argument("-c", "--check", help="Check one item")

    args = parser.parse_args()

    if args.force:
        FORCE_UPDATE = True
    if args.dontpost:
        ENABLE_SENDMESSAGE = False
    if args.auto:
        loop_check()
    elif args.check:
        check_one(args.check)
    else:
        parser.print_usage()
