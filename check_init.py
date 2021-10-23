#!/usr/bin/env python3
# encoding: utf-8

import json
import re
import time
from collections import OrderedDict
from urllib.parse import unquote, urlencode

import requests
from bs4 import BeautifulSoup
from requests.packages import urllib3
from sqlalchemy.orm import exc as sqlalchemy_exc

from config import ENABLE_MULTI_THREAD, PROXIES_DICT, TIMEOUT
from database import create_dbsession, Saved
from page_cache import PageCache
from tgbot import send_message as _send_message

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
)

_KEY_TO_PRINT = {
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

PAGE_CACHE = PageCache()

class CheckUpdate:

    fullname = None
    enable_pagecache = False
    _skip = False

    def __init__(self):
        self._abort_if_missing_property("fullname")
        self.__info_dic = OrderedDict([
            ("LATEST_VERSION", None),
            ("BUILD_TYPE", None),
            ("BUILD_VERSION", None),
            ("BUILD_DATE", None),
            ("BUILD_CHANGELOG", None),
            ("FILE_MD5", None),
            ("FILE_SHA1", None),
            ("FILE_SHA256", None),
            ("DOWNLOAD_LINK", None),
            ("FILE_SIZE", None),
        ])
        self._private_dic = {}
        self.__is_checked = False
        # 在初始化实例时装饰这些方法
        # 使得实例执行self.do_check方法之后自动将self.__is_checked赋值为True
        # 并且在self.__is_checked不为True时不允许执行某些方法
        self.do_check = self.__hook_do_check(self.do_check)
        self.after_check = self.__hook_is_checked(self.after_check)
        self.write_to_database = self.__hook_is_checked(self.write_to_database)
        self.is_updated = self.__hook_is_checked(self.is_updated)
        self.get_print_text = self.__hook_is_checked(self.get_print_text)
        self.send_message = self.__hook_is_checked(self.send_message)

    def __hook_do_check(self, method):
        def hook(*args, **kwargs):
            method(*args, **kwargs)
            # 如果上一行语句抛出了异常, 将不会执行下面这行语句
            self.__is_checked = True
            # 必须返回 None
        return hook

    def __hook_is_checked(self, method):
        def hook(*args, **kwargs):
            assert self.__is_checked, "Please execute the 'do_check' method first."
            return method(*args, **kwargs)
        return hook

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def info_dic(self):
        return self.__info_dic

    def _abort_if_missing_property(self, *props):
        if None in (getattr(self, key, None) for key in props):
            raise Exception(
                "Subclasses inherited from the %s class must specify the '%s' property when defining!"
                % (self.name, "' & '".join(props))
            )

    def update_info(self, key, value):
        """ 更新info_dic字典, 在更新之前会对key和value进行检查和转换 """
        if key not in self.__info_dic.keys():
            raise KeyError("Invalid key: %s" % key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        self.__info_dic[key] = str(value) if value is not None else None

    @classmethod
    def request_url(cls, url, method="get", encoding="utf-8", **kwargs):

        """ 对requests进行了简单的包装
        timeout, proxies这两个参数有默认值, 也可以根据需要自定义这些参数
        :param url: 要请求的url
        :param method: 请求方法, 可选: "get"(默认)或"post"
        :param encoding: 文本编码, 默认为utf-8
        :param kwargs: 其他需要传递给requests的参数
        :return: url页面的源码
        """

        def _request_url(url_, method_, encoding_, **kwargs_):
            if method_ == "get":
                requests_func = requests.get
            elif method_ == "post":
                requests_func = requests.post
            else:
                raise Exception("Unknown request method: %s" % method_)
            params = kwargs_.get("params")
            if cls.enable_pagecache and method_ == "get":
                saved_page_cache = PAGE_CACHE.read(url_, params)
                if saved_page_cache is not None:
                    return saved_page_cache
            timeout = kwargs_.pop("timeout", TIMEOUT)
            proxies = kwargs_.pop("proxies", PROXIES_DICT)
            req = requests_func(
                url_, timeout=timeout, proxies=proxies, **kwargs_
            )
            req.raise_for_status()
            req.encoding = encoding_
            req_text = req.text
            if cls.enable_pagecache:
                PAGE_CACHE.save(url_, params, req_text)
            return req_text

        # 在多线程模式下, 同时只允许一个enable_pagecache属性为True的CheckUpdate对象进行请求
        # 在其他线程上的enable_pagecache属性为True的CheckUpdate对象必须等待
        # 这样才能避免重复请求, 同时避免了PAGE_CACHE的读写冲突
        if cls.enable_pagecache and ENABLE_MULTI_THREAD:
            with PAGE_CACHE.threading_lock:
                return _request_url(url, method, encoding, **kwargs)
        return _request_url(url, method, encoding, **kwargs)

    @classmethod
    def get_hash_from_file(cls, url, **kwargs):
        """
        请求哈希校验文件的url, 返回文件中的哈希值
        :param url: 哈希校验文件的url
        :param kwargs: 需要传递给self.request_url方法的参数
        :return: 哈希值字符串
        """
        return cls.request_url(url, **kwargs).strip().split()[0]

    @staticmethod
    def get_bs(url_text):
        """
        对BeautifulSoup函数进行了简单的包装
        :param url_text: url源码
        :return: BeautifulSoup对象
        """
        return BeautifulSoup(url_text, "lxml")

    @staticmethod
    def grep(text, key, delimiter=":", default=None, ignore_case=False):
        """ 类似Linux的grep命令, 默认分隔符为':' """
        for line in text.strip().splitlines():
            if delimiter not in line:
                continue
            k, v = (x.strip() for x in line.split(delimiter, 1))
            if ignore_case:
                if k.upper() == key.upper():
                    return v
            else:
                if k == key:
                    return v
        return default

    def do_check(self):
        """
        开始进行更新检查, 包括页面请求 数据清洗 info_dic更新, 都应该在此方法中完成
        :return: None
        """
        # 注意: 请不要直接修改self.__info_dic字典, 应该使用self.update_info方法
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要引用参数, 可以在继承时添加新的类属性
        raise NotImplementedError

    def after_check(self):
        """
        此方法将在确定检查对象有更新之后才会执行
        比如: 将下载哈希文件并获取哈希值的代码放在这里, 可以节省一些时间(没有更新时做这些是没有意义的)
        :return: None
        """
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要使用self.do_check方法中的部分变量, 可以借助self._private_dic进行传递
        pass

    def write_to_database(self):
        """ 将CheckUpdate实例的info_dic数据写入数据库 """
        with create_dbsession() as session:
            try:
                saved_data = session.query(Saved).filter(Saved.ID == self.name).one()
            except sqlalchemy_exc.NoResultFound:
                new_data = Saved(
                    ID=self.name,
                    FULL_NAME=self.fullname,
                    **self.__info_dic
                )
                session.add(new_data)
            else:
                saved_data.FULL_NAME = self.fullname
                for key, value in self.__info_dic.items():
                    setattr(saved_data, key, value)
            session.commit()

    def is_updated(self):
        """
        与数据库中已存储的数据进行比对, 如果有更新, 则返回True, 否则返回False
        一般情况下只需比对LATEST_VERSION字段, 子类在继承时可以根据需要拓展此方法
        """
        if self.__info_dic["LATEST_VERSION"] is None:
            return False
        try:
            saved_info = Saved.get_saved_info(self.name)
        except sqlalchemy_exc.NoResultFound:
            return True
        return self.__info_dic["LATEST_VERSION"] != saved_info.LATEST_VERSION

    def get_print_text(self):
        """ 返回更新消息文本 """
        print_str_list = [
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
        ]
        for key, value in self.info_dic.items():
            if key != "LATEST_VERSION" and value is not None:
                if key in "FILE_MD5 FILE_SHA1 FILE_SHA256 BUILD_DATE BUILD_TYPE BUILD_VERSION":
                    value = "`%s`" % value
                if key == "BUILD_CHANGELOG":
                    if value.startswith("http"):
                        value = "[%s](%s)" % (value, value)
                    else:
                        value = "`%s`" % value
                if key == "DOWNLOAD_LINK" and value.startswith("http"):
                    value = "[%s](%s)" % (self.info_dic.get("LATEST_VERSION", ""), value)
                print_str_list.append("\n%s:\n%s" % (_KEY_TO_PRINT[key], value))
        return "\n".join(print_str_list)

    def send_message(self):
        _send_message(self.get_print_text())

    def __repr__(self):
        return "%s(fullname='%s', info_dic={%s})" % (
            self.name,
            self.fullname,
            ", ".join([
                "%s='%s'" % (key, str(value).replace("\n", "\\n"))
                for key, value in self.__info_dic.items() if value is not None
            ])
        )

class SfCheck(CheckUpdate):

    project_name = None
    sub_path = ""

    _MONTH_TO_NUMBER = {
        "Jan": "01", "Feb": "02", "Mar": "03",
        "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09",
        "Oct": "10", "Nov": "11", "Dec": "12",
    }

    def __init__(self):
        self._abort_if_missing_property("project_name")
        super().__init__()

    @classmethod
    def date_transform(cls, date_str):
        """
        将sf站rss中的日期字符串转为time.struct_time类型, 以便于比较
        例： "Wed, 12 Feb 2020 12:34:56 UT"
        返回: time.struct_time(
            tm_year=2020, tm_mon=2, tm_mday=12, tm_hour=12, tm_min=34, tm_sec=56,
            tm_wday=0, tm_yday=48, tm_isdst=-1
        )
        """
        date_str_ = date_str.rsplit(" ", 1)[0].split(", ")[1]
        date_str_month = date_str_.split()[1]
        date_str_ = date_str_.replace(date_str_month, cls._MONTH_TO_NUMBER[date_str_month])
        return time.strptime(date_str_, "%d %m %Y %H:%M:%S")

    @classmethod
    def filter_rule(cls, string):
        """ 文件名过滤规则 """
        return string.endswith(".zip") and "whyred" in string.lower()

    def do_check(self):
        url = "https://sourceforge.net/projects/%s/rss" % self.project_name
        bs_obj = self.get_bs(self.request_url(url, params={"path": "/"+self.sub_path}))
        builds = list(bs_obj.select("item"))
        if not builds:
            return
        builds.sort(key=lambda x: self.date_transform(x.pubdate.string), reverse=True)
        for build in builds:
            file_size_mb = int(build.find("media:content")["filesize"]) / 1000 / 1000
            # 过滤小于500MB的文件
            if file_size_mb < 500:
                continue
            file_version = build.guid.string.split("/")[-2]
            if self.filter_rule(file_version):
                self.update_info("LATEST_VERSION", file_version)
                self.update_info("DOWNLOAD_LINK", build.guid.string)
                self.update_info("BUILD_DATE", build.pubdate.string)
                self.update_info("FILE_MD5", build.find("media:hash", {"algo": "md5"}).string)
                self.update_info("FILE_SIZE", "%0.1f MB" % file_size_mb)
                break

    def is_updated(self):
        # 对于SfCheck, 额外检查BUILD_DATE, 避免新Rom撤包后把旧Rom当作新Rom...
        result = super().is_updated()
        if not result:
            return False
        if self.info_dic["BUILD_DATE"] is None:
            return False
        try:
            saved_info = Saved.get_saved_info(self.name)
        except sqlalchemy_exc.NoResultFound:
            return True
        latest_date = self.date_transform(str(self.info_dic["BUILD_DATE"]))
        try:
            saved_date = self.date_transform(saved_info.BUILD_DATE)
        except:
            return True
        return latest_date > saved_date

class SfProjectCheck(SfCheck):

    # file name keyword: full name
    _KNOWN_ROM = OrderedDict(
        sorted(
            [
                ("aicp", "AICP"),
                ("ancient", "Ancient OS"),
                ("AOSiP", "AOSiP"),
                ("aosp", "AOSP"),
                ("aosp-forking", "AOSP Forking"),
                ("aospa", "Paranoid Android"),
                ("AospExtended", "AospExtended"),
                ("Arrow", "Arrow OS"),
                ("atom", "Atom OS"),
                ("awaken", "Awaken OS"),
                ("Bliss", "Bliss Rom"),
                ("Bootleggers", "Bootleggers Rom"),
                ("Blaze", "Blaze-AOSP Rom"),
                ("CleanDroid", "CleanDroid OS"),
                ("crDroid", "CrDroid"),
                ("DerpFest", "AOSiP DerpFest"),
                ("dotOS", "Dot OS"),
                ("ExtendedUI", "ExtendedUI"),
                ("EvolutionX", "EvolutionX"),
                ("Havoc", "Havoc OS"),
                ("ion", "ION"),
                ("Komodo", "Komodo OS"),
                ("Legion", "Legion OS"),
                ("lineage", "Lineage OS"),
                ("lineageX", "Lineage X"),
                ("MK", "Mokee Rom"),
                ("pa", "Aospa Rom"),
                ("PixelExperience", "Pixel Experience"),
                ("PixelExperience_Plus", "Pixel Experience (Plus edition)"),
                ("PixelExtended", "Pixel Extended"),
                ("potato", "POSP"),
                ("Rebellion", "Rebellion OS"),
                ("Titanium", "Titanium OS"),
                ("Stag", "Stag OS"),
                ("Superior", "Superior OS"),
                ("YAAP", "Yet Another AOSP Project"),
            ],
            key=lambda item: -len(item[0])
        )
    )
    developer = None

    def __init__(self):
        self._abort_if_missing_property("developer")
        self.fullname = "New rom release by %s" % self.developer
        super().__init__()

    def get_print_text(self):
        fullname_bak = self.fullname
        try:
            for key, value in self._KNOWN_ROM.items():
                if key.upper() in str(self.info_dic["LATEST_VERSION"]).upper():
                    self.fullname = "%s (By %s)" % (value, self.developer)
                    break
            return super().get_print_text()
        finally:
            self.fullname = fullname_bak

class H5aiCheck(CheckUpdate):

    base_url = None
    sub_url = None

    def __init__(self):
        self._abort_if_missing_property("base_url", "sub_url")
        super().__init__()

    def do_check(self):
        url = self.base_url + self.sub_url
        bs_obj = self.get_bs(self.request_url(url, verify=False))
        trs = bs_obj.select_one("#fallback").find("table").select("tr")[1:]
        trs = [tr for tr in trs if tr.select("td")[2].get_text().strip()]
        trs.sort(key=lambda x: x.select("td")[2].get_text(), reverse=True)
        builds = list(filter(lambda x: x.find("a").get_text().endswith(".zip"), trs))
        if builds:
            build = builds[0]
            self.update_info("LATEST_VERSION", build.find("a").get_text())
            self.update_info("BUILD_DATE", build.select("td")[2].get_text())
            self.update_info("DOWNLOAD_LINK", self.base_url+build.select("td")[1].find("a")["href"])
            self.update_info("FILE_SIZE", build.select("td")[3].get_text())

class AexCheck(CheckUpdate):

    sub_path = None

    def __init__(self):
        self._abort_if_missing_property("sub_path")
        super().__init__()

    def do_check(self):
        url = "https://api.aospextended.com/builds/" + self.sub_path
        json_text = self.request_url(
            url,
            headers={
                "origin": "https://downloads.aospextended.com",
                "referer": "https://downloads.aospextended.com/" + self.sub_path.split("/")[0],
                "user-agent": CHROME_UA
            },
            timeout=30,
        )
        json_dic = json.loads(json_text)[0]
        self.update_info("LATEST_VERSION", json_dic["file_name"])
        self.update_info("FILE_SIZE", "%0.2f MB" % (int(json_dic["file_size"]) / 1048576,))
        self.update_info("DOWNLOAD_LINK", json_dic["download_link"])
        self.update_info("FILE_MD5", json_dic["md5"])
        self.update_info("BUILD_DATE", json_dic["timestamp"])
        self.update_info("BUILD_CHANGELOG", json_dic.get("changelog"))

class PeCheck(CheckUpdate):

    model = None
    index = None
    tag_name = None

    _url = "https://download.pixelexperience.org"

    def __init__(self):
        self._abort_if_missing_property("model", "index", "tag_name")
        super().__init__()

    def get_real_url(self, fake_url):
        return json.loads(self.request_url(
            fake_url,
            headers={
                "referer": "%s/%s" % (self._url, self.model),
                "user-agent": CHROME_UA,
            }
        )).get("download_url")

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("%s/%s" % (self._url, self.model), headers={}))
        builds = bs_obj.select(".version__item")[self.index]
        assert builds.find("button").get_text().strip() == self.tag_name
        build = builds.select_one(".build__item")
        if build is None:
            return
        self.update_info("LATEST_VERSION", build["data-build-version"])
        self.update_info("BUILD_DATE", build.select_one(".date").get_text().strip())
        self.update_info(
            "DOWNLOAD_LINK",
            self._url + build.select_one(".download__btn")["href"]
        )
        self.update_info(
            "FILE_SIZE",
            re.search(r"\((.*?)\)", build.select_one(".download__btn").get_text()).group(1)
        )
        self.update_info(
            "FILE_MD5",
            self.grep(build.select_one(".download__meta").get_text(), "MD5 hash")
        )
        self.update_info(
            "BUILD_CHANGELOG",
            build.select_one(".changelogs__list").get_text().strip()
        )
        build_id = build.select_one(".download__btn")["data-file-uid"]
        self._private_dic = {
            "fake_download_link": "".join([self._url, "/download/", build_id]),
        }

    def after_check(self):
        real_url = self.get_real_url(self._private_dic["fake_download_link"])
        if real_url:
            self.update_info("DOWNLOAD_LINK", real_url)

class PlingCheck(CheckUpdate):

    p_id = None
    collection_id = None

    def __init__(self):
        self._abort_if_missing_property("p_id", "collection_id")
        super().__init__()

    @staticmethod
    def filter_rule(build_dic):
        """ 文件过滤规则 """
        return int(build_dic["active"])

    def do_check(self):
        url = "https://www.pling.com/p/%s/getfilesajax" % self.p_id
        params = {
            "format": "json",
            "ignore_status_code": 1,
            "status": "all",
            "collection_id": self.collection_id,
            "perpage": 1000,
            "page": 1,
        }
        json_dic = json.loads(self.request_url(url, params=params))
        if not json_dic["files"]:
            return
        json_dic_filtered_files = [f for f in json_dic["files"] if self.filter_rule(f)]
        if not json_dic_filtered_files:
            return
        latest_build = json_dic_filtered_files[-1]
        self._private_dic["latest_build"] = latest_build
        self.update_info("LATEST_VERSION", latest_build["name"])
        self.update_info("BUILD_DATE", latest_build["updated_timestamp"])
        self.update_info("FILE_MD5", latest_build["md5sum"])
        self.update_info(
            "DOWNLOAD_LINK", "https://www.pling.com/p/%s/#files-panel" % self.p_id
        )

    def after_check(self):
        latest_build = self._private_dic["latest_build"]
        if latest_build["tags"] is None:
            real_download_link = "https://www.pling.com/p/%s/startdownload?%s" % (
                self.p_id,
                urlencode({
                    "file_id": latest_build["id"],
                    "file_name": latest_build["name"],
                    "file_type": latest_build["type"],
                    "file_size": latest_build["size"],
                })
            )
            self.update_info(
                "FILE_SIZE",
                "%0.2f MB" % (int(latest_build["size"]) / 1048576,)
            )
        else:
            real_download_link = unquote(latest_build["tags"]).replace("link##", "")
        self.update_info(
            "DOWNLOAD_LINK",
            "`%s`\n[Pling](%s) | [Direct](%s)" % (
                self.info_dic["LATEST_VERSION"],
                "https://www.pling.com/p/%s/#files-panel" % self.p_id,
                real_download_link,
            )
        )

class GithubReleases(CheckUpdate):

    repository_url = None

    def __init__(self):
        self._abort_if_missing_property("repository_url")
        super().__init__()

    def do_check(self):
        url = "https://github.com/%s/releases" % self.repository_url
        bs_obj = self.get_bs(self.request_url(url))
        release_commit = bs_obj.select_one('div[data-test-selector="release-card"]')
        release_header_a = release_commit.select_one('[data-pjax="#repo-content-pjax-container"] a')
        self.update_info("BUILD_VERSION", release_header_a.get_text())
        self.update_info("LATEST_VERSION", "https://github.com" + release_header_a["href"])
        assets = "\n".join([
            "[%s%s](%s)" % (
                re.sub("\\s+", " ", div.select_one("a").get_text().strip()),
                (
                    div.select_one('[data-test-selector="asset-size-label"]')
                    and " (%s)" % div.select_one('[data-test-selector="asset-size-label"]').get_text()
                    or ""
                ),
                "https://github.com" + div.select_one("a")["href"]
            )
            for div in release_commit.select("details ul > li")
        ])
        self.update_info("DOWNLOAD_LINK", assets)

    def get_print_text(self):
        print_str_list = [
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
            "",
            "Release tag:",
            "[%s](%s)" % (self.info_dic["BUILD_VERSION"], self.info_dic["LATEST_VERSION"]),
            "",
            "Assets:",
            self.info_dic["DOWNLOAD_LINK"],
        ]
        return "\n".join(print_str_list)
