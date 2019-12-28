#!/usr/bin/env python3
# encoding: utf-8

import time

from check_init import CheckUpdate

KEY_TO_PRINT = {
    "BUILD_TYPE": "Build type",
    "BUILD_VERSION": "Build version",
    "BUILD_DATE": "Build date",
    "BUILD_CHANGELOG": "Changelog",
    "FILE_MD5": "MD5",
    "FILE_SHA1": "SHA1",
    "FILE_SHA256": "SHA256",
    "DOWNLOAD_LINK": "Download",
    "FILE_SIZE": "Size",
}

def gen_print_text(check_update_obj):
    assert isinstance(check_update_obj, CheckUpdate)
    print_str = "%s Update\n" % check_update_obj.fullname
    # SP
    if check_update_obj.name == "Linux44Y":
        return print_str[:-1].replace("4.4.y", check_update_obj.info_dic["LATEST_VERSION"])
    if check_update_obj.fullname.startswith("New rom release by"):
        print_str.replace(" Update", "")
    # SP END
    print_str += time.strftime("%Y-%m-%d\n", time.localtime(time.time()))
    for key, value in check_update_obj.info_dic.items():
        if key == "LATEST_VERSION":
            continue
        if value is not None:
            print_str += "\n%s:\n%s\n" % (KEY_TO_PRINT[key], value)
    return print_str
