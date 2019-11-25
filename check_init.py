#!/usr/bin/env python3
# encoding: utf-8

import random
from collections import OrderedDict
import json
import re
from urllib.parse import unquote
import urllib3

import requests
from bs4 import BeautifulSoup

from config import DEBUG_ENABLE, PROXIES_DIC, TIMEOUT

# 禁用安全请求警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UAS = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"),
    ("Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 "
     "(KHTML, like Gecko) Version/5.1 Safari/534.50"),
    "Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1"
]

def select_bs4_parser():
    try:
        import lxml
        del lxml
        return "lxml"
    except ModuleNotFoundError:
        try:
            import html5lib
            del html5lib
            return "html5lib"
        except ModuleNotFoundError:
            raise Exception(
                "No bs4 parser available. "
                "Please install at least one parser in 'lxml' and 'html5lib'!"
            )

BS4_PARSER = select_bs4_parser()

class CheckUpdate:

    proxies_dic = PROXIES_DIC
    bs4_parser = BS4_PARSER

    fullname = None

    def __init__(self):
        self.name = self.__class__.__name__
        self.info_dic = OrderedDict([
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
        if self.fullname is None:
            self.raise_missing_property("fullname")

    def raise_missing_property(self, prop):
        raise Exception(
            "Subclasses inherited from the %s class must specify the '%s' property when defining!"
            % (self.name, prop)
        )

    def request_url(self, url, disable_ssl_verify=False, disable_proxy=False, custom_headers=None):
        """ 请求 url 并返回页面源码 若请求失败 则返回空字符串
        :param url: 要请求的 url
        :param disable_ssl_verify: 是否禁用 SSL 检查
        :param disable_proxy: 是否强制禁用代理
        :param custom_headers: 使用自定义的请求头
        :return: 页面源码
        """
        headers = custom_headers if custom_headers else {"user-agent": random.choice(UAS)}
        proxies = {} if disable_proxy else self.proxies_dic
        try:
            req = requests.get(
                url,
                proxies=proxies,
                timeout=TIMEOUT,
                headers=headers,
                verify=not disable_ssl_verify,
            )
        except:
            if DEBUG_ENABLE:
                raise
            return ""
        if req.ok:
            req.encoding = "utf-8"
            return req.text
        return ""

    def get_hash_from_file(self, url, **kwargs):
        return self.request_url(url, **kwargs).strip().split()[0]

    def get_bs(self, url_text):
        return BeautifulSoup(url_text, self.bs4_parser)

    def do_check(self):
        raise NotImplementedError

    def update_info(self, key, value):
        assert key in self.info_dic.keys()
        self.info_dic[key] = value

class SfCheck(CheckUpdate):

    project_name = None
    sub_path = ""

    def __init__(self):
        super().__init__()
        if self.project_name is None:
            self.raise_missing_property("project_name")

    def do_check(self):
        if self.sub_path:
            sub_path = "?path=/%s" % self.sub_path
        else:
            sub_path = ""
        url = "https://sourceforge.net/projects/%s/rss%s" % (self.project_name, sub_path)
        bs_obj = self.get_bs(self.request_url(url))
        builds = list(bs_obj.find_all("item"))
        if not builds:
            self.update_info("LATEST_VERSION", "Looks like there is no Rom file right now")
            return
        builds.sort(key=lambda x: -int(x.find("files:sf-file-id").get_text()))
        for build in builds:
            file_version = build.guid.string.split("/")[-2]
            if file_version.endswith(".zip"):
                self.update_info("LATEST_VERSION", file_version)
                self.update_info("DOWNLOAD_LINK", build.guid.string)
                self.update_info("BUILD_DATE", build.pubdate.string)
                self.update_info("FILE_MD5", build.find("media:hash", {"algo": "md5"}).string)
                self.update_info("FILE_SIZE", "%0.1f MB" % (int(build.find("media:content")["filesize"]) / 1000 / 1000,))
                break
        else:
            self.update_info("LATEST_VERSION", "Looks like there is no Rom file right now")

class H5aiCheck(CheckUpdate):

    base_url = None
    sub_url = None

    def __init__(self):
        super().__init__()
        if self.base_url is None or self.sub_url is None:
            self.raise_missing_property("base_url' & 'sub_url")

    def do_check(self):
        url = self.base_url + self.sub_url
        bs_obj = self.get_bs(self.request_url(url, disable_ssl_verify=True))
        trs = bs_obj.find("div", {"id": "fallback"}).find("table").find_all("tr")[1:]
        trs.sort(key=lambda x: x.find_all("td")[2].get_text(), reverse=True)
        build = list(filter(lambda x: x.find("a").get_text().endswith(".zip"), trs))[0]
        self.update_info("LATEST_VERSION", build.find("a").get_text())
        self.update_info("BUILD_DATE", build.find_all("td")[2].get_text())
        self.update_info("DOWNLOAD_LINK", self.base_url + build.find_all("td")[1].find("a")["href"])
        self.update_info("FILE_SIZE", build.find_all("td")[3].get_text())

class AexCheck(CheckUpdate):

    sub_path = None

    def __init__(self):
        super().__init__()
        if self.sub_path is None:
            self.raise_missing_property("sub_path")

    def do_check(self):
        url = "https://api.aospextended.com/builds/" + self.sub_path
        json_text = self.request_url(
            url,
            custom_headers={
                "origin": "https://downloads.aospextended.com",
                "referer": "https://downloads.aospextended.com/" + self.sub_path.split("/")[0],
                "user-agent": UAS[0]
            }
        )
        json_dic = json.loads(json_text)[0]
        self.update_info("LATEST_VERSION", json_dic["file_name"])
        self.update_info("FILE_SIZE", "%0.2f MB" % (int(json_dic["file_size"]) / 1048576,))
        self.update_info("DOWNLOAD_LINK", json_dic["download_link"])
        self.update_info("BUILD_DATE", json_dic["timestamp"])
        try:
            self.update_info("BUILD_CHANGELOG", json_dic["changelog"])
        except KeyError:
            pass

class PeCheckPageCache:

    def __init__(self):
        self.cache = None

    clear = __init__

class PeCheck(CheckUpdate):

    index = None
    page_cache = None

    def __init__(self):
        super().__init__()
        if self.index is None:
            self.raise_missing_property("index")
        if self.page_cache is None:
            self.raise_missing_property("page_cache")
        if not isinstance(self.page_cache, PeCheckPageCache):
            raise Exception(
                "'page_cache' property must be a PeCheckPageCache object!"
            )

    def do_check(self):
        url = "https://download.pixelexperience.org"
        if self.page_cache.cache is None:
            bs_obj = self.get_bs(self.request_url(url + "/whyred"))
            self.page_cache.cache = bs_obj
        else:
            bs_obj = self.page_cache.cache
        build = bs_obj.find_all("div", {"class": "panel panel-collapse"})[self.index]
        build_info = build.find("tbody").find("tr").find_all("td")
        self.update_info("BUILD_DATE", build_info[0].get_text())
        self.update_info("LATEST_VERSION", build_info[1].get_text().strip())
        build_id = build_info[1].find("a")["data-modal-id"]
        build_info_sp = bs_obj.find("div", {"id": build_id}).find("div", {"class": "modal-body"}).get_text()
        build_changelog = ""
        changelog_start = False
        for line in build_info_sp.splitlines():
            if changelog_start:
                build_changelog += line.strip() + "\n"
                continue
            if "Changelog" in line:
                changelog_start = True
                continue
            if "MD5 hash: " in line:
                self.update_info("FILE_MD5", line.strip().split(": ")[1])
            if "File size: " in line:
                self.update_info("FILE_SIZE", line.strip().split(": ")[1])
        self.update_info("BUILD_CHANGELOG", build_changelog)

class PlingCheck(CheckUpdate):

    p_id = None

    def __init__(self):
        super().__init__()
        if self.p_id is None:
            raise Exception(
                "Subclasses inherited from the PlingCheck class must specify the 'p_id' property!"
            )

    def do_check(self):
        url = "https://www.pling.com/p/%s/#files-panel" % self.p_id
        req_text = self.request_url(url)
        json_text = re.search(r"filesJson..=.(.*?);\n", req_text).group(1)
        json_dic = json.loads(json_text)
        if len(json_dic):
            latest_build = json_dic[0]
            self.update_info("LATEST_VERSION", latest_build["name"])
            self.update_info("BUILD_DATE", latest_build["updated_timestamp"])
            self.update_info("FILE_MD5", latest_build["md5sum"])
            self.update_info("DOWNLOAD_LINK", unquote(latest_build["url"]))
        else:
            self.update_info("LATEST_VERSION", "Looks like there is no Rom file right now")
