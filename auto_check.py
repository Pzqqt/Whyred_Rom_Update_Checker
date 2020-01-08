#!/usr/bin/env python3
# encoding: utf-8

import time
import traceback
import sys

from config import DEBUG_ENABLE, ENABLE_SENDMESSAGE, LOOP_CHECK_INTERVAL
from check_list import CHECK_LIST, PE_PAGE_BS_CACHE
from database import write_to_database, cleanup, is_updated
from tgbot import send_message
from logger import write_log_info, write_log_warning

def _abort_by_user():
    print(" - Abort by user")
    write_log_warning("Abort by user")
    sys.exit(1)

def _sleep(sleep_time=0):
    try:
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        _abort_by_user()

def _get_time_str(time_num=None, offset=0):
    if time_num is None:
        time_num = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time_num + offset))

def check_one(cls):
    cls_obj = cls()
    print("- Checking", cls_obj.fullname, "...", end="")
    try:
        cls_obj.do_check()
    except:
        traceback_string = traceback.format_exc()
        print("\n%s\n! Check failed!" % traceback_string)
        write_log_warning(*traceback_string.splitlines())
        write_log_warning("%s check failed!" % cls_obj.fullname)
        if DEBUG_ENABLE:
            if input("* Continue?(Y/N) ").upper() != "Y":
                _abort_by_user()
        return False
    if is_updated(cls_obj):
        print("\n> New build:", cls_obj.info_dic["LATEST_VERSION"])
        write_log_info("%s has updates: %s" % (cls_obj.fullname, cls_obj.info_dic["LATEST_VERSION"]))
        try:
            cls_obj.after_check()
        except:
            traceback_string = traceback.format_exc()
            print("\n%s\n! Something wrong when running after_check!" % traceback_string)
            write_log_warning(*traceback_string.splitlines())
            write_log_warning("%s: Something wrong when running after_check!" % cls_obj.fullname)
        write_to_database(cls_obj)
        if ENABLE_SENDMESSAGE:
            send_message(cls_obj.get_print_text())
    else:
        print(" no update")
        write_log_info("%s no update" % cls_obj.fullname)
    return True

def loop_check():
    write_log_info("Run database cleanup before start")
    drop_ids = cleanup()
    write_log_info("Abandoned items: {%s}" % ", ".join(drop_ids))
    while True:
        check_failed_list = []
        start_time = _get_time_str()
        print(" - " + start_time)
        print(" - Start...")
        write_log_info("=" * 64)
        write_log_info("Start checking at %s" % start_time)
        for cls in CHECK_LIST:
            result = check_one(cls)
            if not result:
                check_failed_list.append(cls)
            _sleep(2)
        print(" - Check again for failed items...")
        write_log_info("Check again for failed items")
        for cls in check_failed_list:
            check_one(cls)
            _sleep(2)
        PE_PAGE_BS_CACHE.clear()
        print(" - The next check will start at %s\n" % _get_time_str(offset=LOOP_CHECK_INTERVAL))
        write_log_info("End of check")
        _sleep(LOOP_CHECK_INTERVAL)

if __name__ == "__main__":
    loop_check()
