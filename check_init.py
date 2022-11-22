#!/usr/bin/env python3
# encoding: utf-8

import json
import re
import time
import typing
from typing import Union, NoReturn, Final
from collections import OrderedDict
from urllib.parse import unquote, urlencode

import requests
from bs4 import BeautifulSoup
import lxml
from requests.packages import urllib3
from sqlalchemy.orm import exc as sqlalchemy_exc

from config import ENABLE_MULTI_THREAD, PROXIES, TIMEOUT
from database import create_dbsession, Saved
from page_cache import PageCache
from tgbot import send_message as _send_message
from logger import print_and_log


del lxml

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CHROME_UA: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36"
)

_KEY_TO_PRINT: Final = {
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

PAGE_CACHE: Final = PageCache()

InfoDicKeys = typing.Literal[
    "LATEST_VERSION", "BUILD_TYPE", "BUILD_VERSION", "BUILD_DATE", "BUILD_CHANGELOG",
    "FILE_MD5", "FILE_SHA1", "FILE_SHA256", "DOWNLOAD_LINK", "FILE_SIZE",
]

class CheckUpdate:

    fullname: str = None
    enable_pagecache: bool = False
    tags: typing.Sequence[str] = ()
    _skip: bool = False

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
        try:
            self.__prev_saved_info = Saved.get_saved_info(self.name)
        except sqlalchemy_exc.NoResultFound:
            self.__prev_saved_info = None
        # 在初始化实例时装饰这些方法
        # 使得实例执行self.do_check方法之后自动将self.__is_checked赋值为True
        # 并且在self.__is_checked不为True时不允许执行某些方法
        self.do_check = self.__hook_do_check(self.do_check)
        self.after_check = self.__hook_is_checked(self.after_check)
        self.write_to_database = self.__hook_is_checked(self.write_to_database)
        self.is_updated = self.__hook_is_checked(self.is_updated)
        self.get_print_text = self.__hook_is_checked(self.get_print_text)
        self.send_message = self.__hook_is_checked(self.send_message)

    def __hook_do_check(self, method: typing.Callable) -> typing.Callable:
        def hook(*args, **kwargs):
            method(*args, **kwargs)
            # 如果上一行语句抛出了异常, 将不会执行下面这行语句
            self.__is_checked = True
            # 必须返回 None
        return hook

    def __hook_is_checked(self, method: typing.Callable) -> typing.Callable:
        def hook(*args, **kwargs):
            assert self.__is_checked, "Please execute the 'do_check' method first."
            return method(*args, **kwargs)
        return hook

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def info_dic(self) -> OrderedDict:
        return self.__info_dic.copy()

    @property
    def prev_saved_info(self) -> Union[Saved, None]:
        return self.__prev_saved_info

    def _abort_if_missing_property(self, *props: str) -> NoReturn:
        if None in (getattr(self, key, None) for key in props):
            raise Exception(
                "Subclasses inherited from the %s class must specify the '%s' property when defining!"
                % (self.name, "' & '".join(props))
            )

    def update_info(self, key: InfoDicKeys, value: Union[str, dict, list, None]) -> NoReturn:
        """ 更新info_dic字典, 在更新之前会对key和value进行检查和转换 """
        # 尽管key已经做了变量注解, 但还是要在运行时检查, 这很重要
        if key not in self.__info_dic.keys():
            raise KeyError("Invalid key: %s" % key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        if value is not None:
            if not isinstance(value, str):
                print_and_log(
                    "%s.update_info: Attempt to convert %s to strings when updating %s key." % (
                        self.name, type(value), key
                    ),
                    level="warning",
                )
                value = str(value)
        self.__info_dic[key] = value

    @classmethod
    def request_url(
            cls,
            url: str,
            method: typing.Literal["get", "post"] = "get",
            encoding: str = "utf-8",
            **kwargs
    ) -> str:

        """ 对requests进行了简单的包装
        timeout, proxies这两个参数有默认值, 也可以根据需要自定义这些参数
        :param url: 要请求的url
        :param method: 请求方法, 可选: "get"(默认)或"post"
        :param encoding: 文本编码, 默认为utf-8
        :param kwargs: 其他需要传递给requests的参数
        :return: 请求结果的text(解码后)
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
            proxies = kwargs_.pop("proxies", PROXIES)
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
    def get_hash_from_file(cls, url: str, **kwargs) -> str:
        """
        请求哈希校验文件的url, 返回文件中的哈希值
        :param url: 哈希校验文件的url
        :param kwargs: 需要传递给self.request_url方法的参数
        :return: 哈希值字符串
        """
        return cls.request_url(url, **kwargs).strip().split()[0]

    @staticmethod
    def get_bs(url_text: str, **kwargs) -> BeautifulSoup:
        """
        对BeautifulSoup函数进行了简单的包装, 默认解析器为lxml
        :param url_text: url源码
        :param kwargs: 其他需要传递给BeautifulSoup的参数
        :return: BeautifulSoup对象
        """
        features = kwargs.pop("features", "lxml")
        return BeautifulSoup(url_text, features=features, **kwargs)

    @staticmethod
    def getprop(
            text: str,
            key: str,
            delimiter: str = ":",
            default: Union[str, None] = None,
            ignore_case: bool = False
    ) -> str:
        """ 类似Shell的getprop和cut命令
        :param text: 要解析的字符串
        :param key: 要搜索的键值
        :param delimiter: 分隔符, 默认为':'
        :param default: 找不到结果时返回的值, 默认是None而不是空字符串, 请注意
        :param ignore_case: 对key是否忽略大小写
        :return:
        """
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

    def do_check(self) -> NoReturn:
        """
        开始进行更新检查, 包括页面请求 数据清洗 info_dic更新, 都应该在此方法中完成
        :return: None
        """
        # 注意: 请不要直接修改self.__info_dic字典, 应该使用self.update_info方法
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要引用参数, 可以在继承时添加新的类属性
        raise NotImplementedError

    def after_check(self) -> NoReturn:
        """
        此方法将在确定检查对象有更新之后才会执行
        比如: 将下载哈希文件并获取哈希值的代码放在这里, 可以节省一些时间(没有更新时做这些是没有意义的)
        :return: None
        """
        # 为保持一致性, 此方法不允许传入任何参数, 并且不允许返回任何值
        # 如确实需要使用self.do_check方法中的部分变量, 可以借助self._private_dic进行传递
        pass

    def write_to_database(self) -> NoReturn:
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

    def is_updated(self) -> bool:
        """
        与数据库中已存储的数据进行比对, 如果有更新, 则返回True, 否则返回False
        一般情况下只需比对LATEST_VERSION字段, 子类在继承时可以根据需要拓展此方法
        """
        if self.__info_dic["LATEST_VERSION"] is None:
            return False
        if self.__prev_saved_info is None:
            return True
        return self.__info_dic["LATEST_VERSION"] != self.__prev_saved_info.LATEST_VERSION

    def get_tags_text(self, allow_empty: bool = False) -> str:
        """ 根据self.tags返回tags文本, 生成类似`#foo #bar`的格式, 以空格作为分隔符
        allow_empty为真时, 如果self.tags为空, 则返回一个空字符串
        allow_empty为假时, 如果self.tags为空, 则tags取类的名字
        """
        _tags = self.tags
        if not _tags:
            if allow_empty:
                return ""
            _tags = (self.name,)
        return '#' + " #".join(_tags)

    def get_print_text(self) -> str:
        """ 返回更新消息文本 """
        print_str_list = [
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
            self.get_tags_text(),
        ]
        for key, value in self.__info_dic.items():
            if value is None:
                continue
            if key == "LATEST_VERSION":
                continue
            if key in "FILE_MD5 FILE_SHA1 FILE_SHA256 BUILD_DATE BUILD_TYPE BUILD_VERSION":
                value = "`%s`" % value
            if key == "BUILD_CHANGELOG":
                if value.startswith("http"):
                    value = "[%s](%s)" % (value, value)
                else:
                    value = "`%s`" % value
            if key == "DOWNLOAD_LINK" and value.startswith("http"):
                value = "[%s](%s)" % (self.__info_dic.get("LATEST_VERSION") or value, value)
            print_str_list.append("\n%s:\n%s" % (_KEY_TO_PRINT[key], value))
        return "\n".join(print_str_list)

    def send_message(self) -> NoReturn:
        _send_message(self.get_print_text())

    def __repr__(self) -> str:
        return "%s(fullname='%s', info_dic={%s})" % (
            self.name,
            self.fullname,
            ", ".join([
                "%s='%s'" % (key, str(value).replace("\n", "\\n"))
                for key, value in self.__info_dic.items() if value is not None
            ])
        )

class CheckUpdateWithBuildDate(CheckUpdate):

    """
    在执行is_updated方法时, 额外检查BUILD_DATE字段
    如果BUILD_DATE比数据库中已存储数据的BUILD_DATE要早的话则认为没有更新
    如果从此类继承, 则必须实现date_transform方法
    """

    @classmethod
    def date_transform(cls, date_str: str) -> typing.Any:
        """
        解析时间字符串, 用于比较
        :param date_str: 要解析的时间字符串
        :return: 能比较大小的对象
        """
        raise NotImplementedError

    def is_updated(self) -> bool:
        result = super().is_updated()
        if not result:
            return False
        if self.info_dic["BUILD_DATE"] is None:
            return False
        if self.prev_saved_info is None:
            return True
        latest_date = self.date_transform(str(self.info_dic["BUILD_DATE"]))
        try:
            saved_date = self.date_transform(self.prev_saved_info.BUILD_DATE)
        except:
            return True
        return latest_date > saved_date

class SfCheck(CheckUpdateWithBuildDate):
    project_name: str = None
    sub_path: str = ""

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
    def date_transform(cls, date_str: str) -> time.struct_time:
        # 例: "Wed, 12 Feb 2020 12:34:56 UT"
        date_str_ = date_str.rsplit(" ", 1)[0].split(", ")[1]
        date_str_month = date_str_.split()[1]
        date_str_ = date_str_.replace(date_str_month, cls._MONTH_TO_NUMBER[date_str_month])
        return time.strptime(date_str_, "%d %m %Y %H:%M:%S")

    @classmethod
    def filter_rule(cls, string: str) -> bool:
        """ 文件名过滤规则 """
        return string.endswith(".zip") and "whyred" in string.lower()

    def do_check(self):
        url = "https://sourceforge.net/projects/%s/rss" % self.project_name
        bs_obj = self.get_bs(
            self.request_url(url, params={"path": "/"+self.sub_path}),
            features="xml",
        )
        builds = list(bs_obj.select("item"))
        if not builds:
            return
        builds.sort(key=lambda x: self.date_transform(x.pubDate.get_text()), reverse=True)
        for build in builds:
            file_size_mb = int(build.find("media:content")["filesize"]) / 1000 / 1000
            # 过滤小于500MB的文件
            if file_size_mb < 500:
                continue
            file_version = build.guid.get_text().split("/")[-2]
            if self.filter_rule(file_version):
                self.update_info("LATEST_VERSION", file_version)
                self.update_info("DOWNLOAD_LINK", build.guid.get_text())
                self.update_info("BUILD_DATE", build.pubDate.get_text())
                self.update_info("FILE_MD5", build.find("media:hash", {"algo": "md5"}).get_text())
                self.update_info("FILE_SIZE", "%0.1f MB" % file_size_mb)
                break

class SfProjectCheck(SfCheck):
    developer: str = None

    # file name keyword: full name
    _KNOWN_ROM: Final = OrderedDict(
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
    base_url: str = None
    sub_url: str = None

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
    sub_path: str = None
    _skip = True

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
    model: str = None
    index: int = None
    tag_name: str = None

    _url: Final = "https://download.pixelexperience.org"

    def __init__(self):
        self._abort_if_missing_property("model", "index", "tag_name")
        super().__init__()

    def get_real_url(self, fake_url: str) -> str:
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
            self.getprop(build.select_one(".download__meta").get_text(), "MD5 hash")
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
    p_id: int = None

    def __init__(self):
        self._abort_if_missing_property("p_id")
        super().__init__()

    @staticmethod
    def filter_rule(build_dic: dict) -> typing.Any:
        """ 文件过滤规则 """
        return int(build_dic["active"])

    def do_check(self):
        url = "https://www.pling.com/p/%s/loadFiles" % self.p_id
        json_dic_files = json.loads(self.request_url(url)).get("files")
        if not json_dic_files:
            return
        json_dic_filtered_files = [f for f in json_dic_files if self.filter_rule(f)]
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
        else:
            real_download_link = unquote(latest_build["tags"]).replace("link##", "")
        file_size = latest_build["size"]
        if file_size:
            self.update_info(
                "FILE_SIZE",
                "%0.2f MB" % (int(file_size) / 1048576,)
            )
        self.update_info(
            "DOWNLOAD_LINK",
            "`%s`\n[Pling](%s) | [Direct](%s)" % (
                self.info_dic["LATEST_VERSION"],
                "https://www.pling.com/p/%s/#files-panel" % self.p_id,
                real_download_link,
            )
        )

class GithubReleases(CheckUpdateWithBuildDate):
    repository_url: str = None
    ignore_prerelease: bool = True

    def __init__(self):
        self._abort_if_missing_property("repository_url")
        super().__init__()

    @classmethod
    def date_transform(cls, date_str: str) -> time.struct_time:
        # 例: "2022-02-02T08:21:26Z"
        return time.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

    def do_check(self):
        url = "https://api.github.com/repos/%s/releases/latest" % self.repository_url
        latest_json = json.loads(self.request_url(url))
        if not latest_json:
            return
        if latest_json["draft"]:
            return
        if self.ignore_prerelease and latest_json["prerelease"]:
            return
        self.update_info("BUILD_VERSION", latest_json["name"] or latest_json["tag_name"])
        self.update_info("LATEST_VERSION", latest_json["html_url"])
        self.update_info("BUILD_DATE", latest_json["published_at"])
        self.update_info(
            "DOWNLOAD_LINK",
            "\n".join([
                "[%s (%s)](%s)" % (
                    # File name, File size, Download link
                    asset["name"], "%0.1f MB" % (int(asset["size"]) / 1024 / 1024), asset["browser_download_url"]
                )
                for asset in latest_json["assets"]
            ])
        )

    def get_print_text(self):
        return "\n".join([
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
            self.get_tags_text(),
            "",
            "Release tag:",
            "[%s](%s)" % (self.info_dic["BUILD_VERSION"], self.info_dic["LATEST_VERSION"]),
            "",
            "Assets:",
            self.info_dic["DOWNLOAD_LINK"],
        ])
