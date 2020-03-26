#!/usr/bin/env python3
# encoding: utf-8

from argparse import ArgumentParser
import time
import traceback
import sys

from requests import exceptions

from config import DEBUG_ENABLE, ENABLE_SENDMESSAGE, LOOP_CHECK_INTERVAL
from check_init import ErrorCode, PAGE_CACHE
from check_list import CHECK_LIST
from database import DBSession, Saved
from tgbot import send_message
from logger import write_log_info, write_log_warning

# 为True时将强制将数据保存至数据库并发送消息
FORCE_UPDATE = False
# 为True时将强制禁止发送消息(注意: 优先级低于FORCE_UPDATE)
DONT_POST = False

def database_cleanup():
    """
    将数据库中存在于数据库但不存在于CHECK_LIST的项目删除掉
    :return: 被删除的项目名字的集合
    """
    session = DBSession()
    try:
        saved_ids = {x.ID for x in session.query(Saved).all()}
        checklist_ids = {x.__name__ for x in CHECK_LIST}
        drop_ids = saved_ids - checklist_ids
        for id_ in drop_ids:
            session.delete(session.query(Saved).filter(Saved.ID == id_).one())
        session.commit()
        return drop_ids
    finally:
        session.close()

def _abort(text):
    print(" - %s" % text)
    write_log_warning(str(text))
    sys.exit(1)

def _abort_by_user():
    return _abort("Abort by user")

def _sleep(sleep_time=0):
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        _abort_by_user()

def _get_time_str(time_num=None, offset=0):
    if time_num is None:
        time_num = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_num+offset))

def check_one(cls):
    if isinstance(cls, str):
        for item in CHECK_LIST:
            if item.__name__ == cls:
                cls = item
                break
        else:
            raise Exception("Can not found '%s' from CHECK_LIST!" % cls)
    cls_obj = cls()
    print("- Checking", cls_obj.fullname, "...", end="")
    try:
        cls_obj.do_check()
    except Exception as error:
        if isinstance(error, exceptions.ReadTimeout):
            print("\n! Check failed! Timeout.")
            write_log_warning("%s check failed! Timeout." % cls_obj.fullname)
        elif isinstance(error, (exceptions.SSLError, exceptions.ProxyError)):
            print("\n! Check failed! Proxy error.")
            write_log_warning("%s check failed! Proxy error." % cls_obj.fullname)
        elif isinstance(error, ErrorCode):
            print("\n! Check failed! Error code: %s." % error)
            write_log_warning("%s check failed! Error code: %s." % (cls_obj.fullname, error))
        else:
            traceback_string = traceback.format_exc()
            print("\n%s\n! Check failed!" % traceback_string)
            write_log_warning(*traceback_string.splitlines())
            write_log_warning("%s check failed!" % cls_obj.fullname)
        if DEBUG_ENABLE:
            if input("* Continue?(Y/N) ").upper() != "Y":
                _abort_by_user()
        return False
    if cls_obj.is_updated() or FORCE_UPDATE:
        print("\n> New build:", cls_obj.info_dic["LATEST_VERSION"])
        write_log_info("%s has updates: %s" % (cls_obj.fullname, cls_obj.info_dic["LATEST_VERSION"]))
        try:
            cls_obj.after_check()
        except:
            traceback_string = traceback.format_exc()
            print("\n%s\n! Something wrong when running after_check!" % traceback_string)
            write_log_warning(*traceback_string.splitlines())
            write_log_warning("%s: Something wrong when running after_check!" % cls_obj.fullname)
        cls_obj.write_to_database()
        if (ENABLE_SENDMESSAGE and not DONT_POST) or FORCE_UPDATE:
            send_message(cls_obj.get_print_text())
    else:
        print(" no update")
        write_log_info("%s no update" % cls_obj.fullname)
    return True

def loop_check():
    write_log_info("Run database cleanup before start")
    drop_ids = database_cleanup()
    write_log_info("Abandoned items: {%s}" % ", ".join(drop_ids))
    check_failed_list = []
    req_failed_flag = 0
    while True:
        start_time = _get_time_str()
        print(" - " + start_time)
        print(" - Start...")
        write_log_info("=" * 64)
        write_log_info("Start checking at %s" % start_time)
        for cls in CHECK_LIST:
            result = check_one(cls)
            if not result:
                req_failed_flag += 1
                check_failed_list.append(cls)
            else:
                req_failed_flag = 0
            if req_failed_flag == 5:
                req_failed_flag = 0
                print(" - Network or proxy error! Sleep...")
                write_log_warning("Network or proxy error! Sleep...")
                break
            _sleep(2)
        else:
            print(" - Check again for failed items...")
            write_log_info("Check again for failed items")
            for cls in check_failed_list:
                check_one(cls)
                _sleep(2)
        check_failed_list.clear()
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
    elif args.dontpost:
        DONT_POST = True
    if args.auto:
        loop_check()
    elif args.check:
        check_one(args.check)
    else:
        parser.print_usage()
