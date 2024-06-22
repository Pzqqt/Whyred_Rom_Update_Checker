#!/usr/bin/env python3
# encoding: utf-8

import json
import time
import logging
import typing
import urllib3
from typing import Union, Final, final, Optional, ClassVar
from collections import OrderedDict
from urllib.parse import unquote, urlencode
from functools import wraps

from bs4 import BeautifulSoup
import lxml
from sqlalchemy.orm import exc as sqlalchemy_exc

from config import ENABLE_MULTI_THREAD
from database import DatabaseSession, Saved
from common import PageCache, request_url as _request_url
from tgbot import send_message as _send_message
from logger import print_and_log


del lxml

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CHROME_UA: Final = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
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
    fullname: str
    enable_pagecache: ClassVar[bool] = False
    tags: typing.Sequence[str] = tuple()
    _skip: ClassVar[bool] = False

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
        self.__is_updated = None
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
        self.get_print_text = self.__hook_is_checked(self.get_print_text)
        self.send_message = self.__hook_is_checked(self.send_message)
        self.is_updated = self.__hook_is_updated(self.__hook_is_checked(self.is_updated))

    def __hook_do_check(self, method: typing.Callable) -> typing.Callable:
        @wraps(method)
        def hook(*args, **kwargs):
            method(*args, **kwargs)
            # 如果上一行语句抛出了异常, 将不会执行下面这行语句
            self.__is_checked = True
            # 必须返回 None
        return hook

    def __hook_is_checked(self, method: typing.Callable) -> typing.Callable:
        @wraps(method)
        def hook(*args, **kwargs):
            assert self.__is_checked, "Please execute the 'do_check' method first."
            return method(*args, **kwargs)
        return hook

    def __hook_is_updated(self, method: typing.Callable) -> typing.Callable:
        @wraps(method)
        def hook(*args, **kwargs):
            if self.__is_updated is None:
                self.__is_updated = method(*args, **kwargs)
            return self.__is_updated
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

    def _abort_if_missing_property(self, *props: str):
        if None in (getattr(self, key, None) for key in props):
            raise Exception(
                "Subclasses inherited from the %s class must specify the '%s' property when defining!"
                % (self.name, "' & '".join(props))
            )

    @final
    def update_info(self, key: InfoDicKeys, value: Union[str, dict, list, None]):
        """ 更新info_dic字典, 在更新之前会对key和value进行检查和转换 """
        # 尽管key已经做了变量注解, 但还是要在运行时检查, 这很重要
        if key not in self.__info_dic.keys():
            raise KeyError("Invalid key: %s" % key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        if value is not None:
            if not isinstance(value, str):
                print_and_log(
                    "%s.update_info: Attempt to convert %s to strings when updating %s key." % (
                        self.name, type(value), key
                    ),
                    level=logging.WARNING,
                )
                value = str(value)
        self.__info_dic[key] = value

    @classmethod
    @final
    def request_url_text(
            cls,
            url: str,
            *,
            method: typing.Literal["get", "post"] = "get",
            raise_for_status: bool = True,
            encoding: Optional[str] = None,
            **kwargs
    ) -> str:
        """ 使用requests库请求url并返回解码后的响应text
        timeout, proxies这两个参数有默认值, 也可以根据需要自定义这些参数
        该方法支持使用页面缓存(PageCache)
        :param url: 要请求的url
        :param method: 请求方法, 可选: "get"(默认)或"post"
        :param raise_for_status: 为True时, 如果请求返回的状态码是4xx或5xx则抛出异常
        :param encoding: 文本编码, 默认由requests自动识别
        :param kwargs: 其他需要传递给requests的参数
        :return: 响应的text(解码后)
        """

        def _request_url_text():
            params = kwargs.get("params")
            if cls.enable_pagecache and method == "get":
                saved_page_cache = PAGE_CACHE.read(url, params)
                if saved_page_cache is not None:
                    return saved_page_cache
            req = _request_url(url, method=method, raise_for_status=raise_for_status, **kwargs)
            if encoding is not None:
                req.encoding = encoding
            req_text = req.text
            if cls.enable_pagecache:
                PAGE_CACHE.save(url, params, req_text)
            return req_text

        # 在多线程模式下, 同时只允许一个enable_pagecache属性为True的CheckUpdate对象进行请求
        # 在其他线程上的enable_pagecache属性为True的CheckUpdate对象必须等待
        # 这样才能避免重复请求, 同时避免了PAGE_CACHE的读写冲突
        if cls.enable_pagecache and ENABLE_MULTI_THREAD:
            with PAGE_CACHE.threading_lock:
                return _request_url_text()
        return _request_url_text()

    # 向后兼容
    request_url = request_url_text

    @classmethod
    @final
    def get_hash_from_file(cls, url: str, **kwargs) -> str:
        """
        请求哈希校验文件的url, 返回文件中的哈希值
        :param url: 哈希校验文件的url
        :param kwargs: 需要传递给self.request_url_text方法的参数
        :return: 哈希值字符串
        """
        return cls.request_url_text(url, **kwargs).strip().split()[0]

    @staticmethod
    @final
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
    @final
    def get_human_readable_file_size(file_size: int, decimal_system: bool = False, decimal_places: int = 1) -> str:
        """
        返回人类可读的文件大小
        :param file_size: 文件大小(单位: bytes)
        :param decimal_system: 为True时按十进制计算(1MB == 1000KB), 否则按二进制计算(1MB == 1024KB)(默认)
        :param decimal_places: 保留的小数位数(默认保留1位)
        :return: 人类可读的文件大小字符串
        """
        divisor = 1000 if decimal_system else 1024
        template = "%%0.%df" % decimal_places
        if file_size < divisor:
            return "%s bytes" % (file_size, )
        if file_size < (divisor * divisor):
            return template % (file_size / divisor, ) + " KB"
        if file_size < (divisor * divisor * divisor):
            return template % (file_size / divisor / divisor, ) + " MB"
        return template % (file_size / divisor / divisor / divisor, ) + " GB"

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

    @final
    def write_to_database(self):
        """ 将CheckUpdate实例的info_dic数据写入数据库 """
        with DatabaseSession() as session:
            if (saved_data := session.query(Saved).filter_by(ID=self.name).one_or_none()) is None:
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

    @final
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

    def send_message(self):
        """ 发送更新消息 """
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

class CheckMultiUpdate(CheckUpdate):

    """
    把LATEST_VERSION字段当作字典处理
    在发送更新消息时, 将LATEST_VERSION中每个新的元素(与数据库中已保存的相比)各自作为一条更新消息发送
    如果从此类继承, 则必须实现`send_message_single`方法
    子类若实现了messages_sort_func方法, 则每一条更新消息会按messages_sort_func方法进行排序
    """

    messages_sort_func = None

    def get_print_text(self):
        raise NotImplemented

    def send_message_single(self, key, item):
        """
        发送一条更新消息
        参数key和item对应LATEST_VERSION中元素的键和值
        """
        raise NotImplementedError

    def send_message(self):
        fetch_items = json.loads(self.info_dic["LATEST_VERSION"])
        assert isinstance(fetch_items, dict)
        if self.prev_saved_info is None:
            saved_items = {}
        else:
            try:
                saved_items = json.loads(self.prev_saved_info.LATEST_VERSION)
            except json.decoder.JSONDecodeError:
                saved_items = {}
        new_keys = fetch_items.keys() - saved_items.keys()
        if self.messages_sort_func is not None and callable(self.messages_sort_func):
            new_keys = sorted(new_keys, key=lambda x: self.messages_sort_func(fetch_items[x]))
        for key in new_keys:
            self.send_message_single(key, fetch_items[key])
            # 休息两秒
            time.sleep(2)

class SfCheck(CheckUpdateWithBuildDate):
    project_name :ClassVar[str]
    sub_path: ClassVar[str] = ""
    minimum_file_size_mb: ClassVar[int] = 500

    _MONTH_TO_NUMBER: Final = {
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
        return True

    def do_check(self):
        url = "https://sourceforge.net/projects/%s/rss" % self.project_name
        bs_obj = self.get_bs(
            self.request_url_text(url, params={"path": "/"+self.sub_path}),
            features="xml",
        )
        builds = list(bs_obj.select("item"))
        if not builds:
            return
        builds.sort(key=lambda x: self.date_transform(x.pubDate.get_text()), reverse=True)
        for build in builds:
            file_size = int(build.find("media:content")["filesize"])
            # 过滤小于`minimum_file_size_mb`的文件
            if file_size / 1000 / 1000 < self.minimum_file_size_mb:
                continue
            file_version = build.guid.get_text().split("/")[-2]
            if self.filter_rule(file_version):
                self.update_info("LATEST_VERSION", file_version)
                self.update_info("DOWNLOAD_LINK", build.guid.get_text())
                self.update_info("BUILD_DATE", build.pubDate.get_text())
                self.update_info("FILE_MD5", build.find("media:hash", {"algo": "md5"}).get_text())
                self.update_info("FILE_SIZE", self.get_human_readable_file_size(file_size, decimal_system=True))
                break

class SfProjectCheck(SfCheck):
    developer: ClassVar[str]

    def __init__(self):
        self._abort_if_missing_property("developer")
        self.fullname = "New rom release by %s" % self.developer
        super().__init__()

class PlingCheck(CheckUpdateWithBuildDate):
    p_id: ClassVar[int]

    def __init__(self):
        self._abort_if_missing_property("p_id")
        super().__init__()
        self.latest_build = {}

    @classmethod
    def date_transform(cls, date_str: str) -> str:
        # 例: "2023-01-02 12:34:56"
        return date_str

    @staticmethod
    def filter_rule(build_dic: dict) -> typing.Any:
        """ 文件过滤规则 """
        return int(build_dic["active"])

    def do_check(self):
        url = "https://www.pling.com/p/%s/loadFiles" % self.p_id
        json_dic_files = json.loads(self.request_url_text(url)).get("files")
        if not json_dic_files:
            return
        json_dic_filtered_files = [f for f in json_dic_files if self.filter_rule(f)]
        if not json_dic_filtered_files:
            return
        latest_build = json_dic_filtered_files[-1]
        self.latest_build = latest_build
        self.update_info("LATEST_VERSION", latest_build["name"])
        self.update_info("BUILD_DATE", latest_build["updated_timestamp"])
        self.update_info("BUILD_VERSION", latest_build["version"] or None)
        self.update_info("FILE_MD5", latest_build["md5sum"])
        self.update_info(
            "DOWNLOAD_LINK", "https://www.pling.com/p/%s/#files-panel" % self.p_id
        )

    def after_check(self):
        if self.latest_build.get("tags") is None:
            real_download_link = "https://www.pling.com/p/%s/startdownload?%s" % (
                self.p_id,
                urlencode({
                    "file_id": self.latest_build["id"],
                    "file_name": self.latest_build["name"],
                    "file_type": self.latest_build["type"],
                    "file_size": self.latest_build["size"],
                })
            )
        else:
            real_download_link = unquote(self.latest_build["tags"]).replace("link##", "")
        file_size = self.latest_build["size"]
        if file_size:
            self.update_info(
                "FILE_SIZE",
                self.get_human_readable_file_size(int(file_size), decimal_places=2)
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
    repository_url: ClassVar[str]
    ignore_prerelease: ClassVar[bool] = True

    def __init__(self):
        self._abort_if_missing_property("repository_url")
        super().__init__()
        self.response_json_dic = {}

    @classmethod
    def date_transform(cls, date_str: str) -> time.struct_time:
        # 例: "2022-02-02T08:21:26Z"
        return time.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

    def do_check(self):
        url = "https://api.github.com/repos/%s/releases/latest" % self.repository_url
        latest_json = json.loads(self.request_url_text(url))
        if not latest_json:
            return
        self.response_json_dic = latest_json
        if latest_json["draft"]:
            return
        if self.ignore_prerelease and latest_json["prerelease"]:
            return
        self.update_info("BUILD_VERSION", latest_json["name"] or latest_json["tag_name"])
        self.update_info("LATEST_VERSION", latest_json["html_url"])
        self.update_info("BUILD_DATE", latest_json["published_at"])
        if len(latest_json["assets"]) >= 10:
            self.update_info("DOWNLOAD_LINK", "[There are too many, see here](%s)" % latest_json["html_url"])
        else:
            self.update_info(
                "DOWNLOAD_LINK",
                "\n".join([
                    "[%s (%s)](%s)" % (
                        # File name, File size, Download link
                        asset["name"],
                        self.get_human_readable_file_size(int(asset["size"])),
                        asset["browser_download_url"],
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
