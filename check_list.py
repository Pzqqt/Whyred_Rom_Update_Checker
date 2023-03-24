#!/usr/bin/env python3
# encoding: utf-8

import json
import time
import re
import logging
import os
import datetime

from requests import exceptions as req_exceptions

from check_init import CheckUpdate, CheckUpdateWithBuildDate, GithubReleases, CHROME_UA
from tgbot import send_message as _send_message, send_photo as _send_photo
from logger import print_and_log

class Linux414Y(CheckUpdate):
    fullname = "Linux Kernel stable v4.14.y"
    tags = ("Linux", "Kernel")
    # enable_pagecache = True
    re_pattern = r'4\.14\.\d+'

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.select_one("#releases").select("tr"):
            kernel_version = tr_obj.select("td")[1].get_text()
            if re.match(self.re_pattern, kernel_version):
                self.update_info("LATEST_VERSION", kernel_version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "https://git.kernel.org/stable/h/v%s" % kernel_version
                )
                self.update_info(
                    "BUILD_CHANGELOG",
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v%s"
                    % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")

    def get_print_text(self):
        return "*Linux Kernel stable* [v%s](%s) *update*\n%s\n\n[Commits](%s)" % (
            self.info_dic["LATEST_VERSION"],
            self.info_dic["DOWNLOAD_LINK"],
            self.get_tags_text(),
            self.info_dic["BUILD_CHANGELOG"],
        )

class GoogleClangPrebuilt(CheckUpdate):
    fullname = "Google Clang Prebuilt"
    tags = ("clang",)
    BASE_URL = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self.BASE_URL + "/+log"))
        commits = bs_obj.select_one(".CommitLog").select("li")
        sp_commits = {}
        for commit in commits:
            a_tag = commit.select("a")[1]
            commit_title = a_tag.get_text()
            if commit_title.startswith("Update prebuilt Clang to"):
                release_version = commit_title.split()[4]
                if release_version.startswith("r"):
                    if release_version[-1] == ".":
                        release_version = release_version[:-1]
                    commit_url = "https://android.googlesource.com" + a_tag["href"]
                    commit_id = a_tag["href"].split("/")[-1]
                    sp_commits[commit_id] = {
                        "commit_url": commit_url,
                        "release_version": release_version,
                    }
        self.update_info("LATEST_VERSION", sp_commits)

    def get_print_text(self):
        raise NotImplemented

    def _get_print_text(self, dic: dict) -> str:
        return "*%s Update*\n%s\n\n[Commit](%s)\n\nDownload tar.gz:\n[%s](%s)" % (
            self.fullname, self.get_tags_text(), dic["BUILD_CHANGELOG"], dic["BUILD_VERSION"], dic["DOWNLOAD_LINK"],
        )

    @classmethod
    def get_detailed_version(cls, url: str) -> str:
        bs_obj_2 = cls.get_bs(cls.request_url(url))
        commit_text = bs_obj_2.find("pre").get_text().splitlines()[2]
        if commit_text[-1] == ".":
            commit_text = commit_text[:-1]
        return commit_text

    def send_message(self):
        fetch_commits = json.loads(self.info_dic["LATEST_VERSION"])
        if self.prev_saved_info is None:
            saved_commits = {}
        else:
            try:
                saved_commits = json.loads(self.prev_saved_info.LATEST_VERSION)
            except json.decoder.JSONDecodeError:
                saved_commits = {}
            if not isinstance(saved_commits, dict):
                saved_commits = {}
        for key in fetch_commits.keys() - saved_commits.keys():
            item = fetch_commits[key]
            try:
                detailed_version = self.get_detailed_version(item["commit_url"])
            except:
                detailed_version = key
            _send_message(self._get_print_text(
                dic={
                    "BUILD_CHANGELOG": item["commit_url"],
                    "BUILD_VERSION": detailed_version,
                    "DOWNLOAD_LINK": "%s/+archive/%s/clang-%s.tar.gz" % (
                        self.BASE_URL, key, item["release_version"],
                    ),
                }
            ))
            time.sleep(2)

class WireGuard(CheckUpdate):
    fullname = "WireGuard for Linux 3.10 - 5.5"

    def do_check(self):
        base_url = "https://git.zx2c4.com/wireguard-linux-compat"
        fetch_url = "https://build.wireguard.com/distros.txt"
        fetch_text = self.request_url(fetch_url)
        for line in fetch_text.splitlines():
            line = line.strip()
            if not line:
                continue
            distro, package, version = line.split()[:3]
            if distro == "upstream" and package == "linuxcompat":
                self.update_info("LATEST_VERSION", "v"+version)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "%s/snapshot/wireguard-linux-compat-%s.tar.xz" % (base_url, version)
                )
                self.update_info("BUILD_CHANGELOG", "%s/log/?h=%s" % (base_url, "v"+version))
                break
        else:
            raise Exception("Parsing failed!")

    def get_print_text(self):
        return "*%s update*\n%s\n\n[Commits](%s)\n\nDownload tar.gz:\n[%s](%s)" % (
            self.fullname,
            self.get_tags_text(),
            self.info_dic["BUILD_CHANGELOG"],
            self.info_dic["DOWNLOAD_LINK"].split("/")[-1],
            self.info_dic["DOWNLOAD_LINK"],
        )

class BeyondCompare4(CheckUpdate):
    fullname = "Beyond Compare 4"
    BASE_URL = "https://www.scootersoftware.com"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("%s/download.php?zz=dl4" % self.BASE_URL))
        p_obj = bs_obj.select_one('form[name="prog-form"] > p')
        self.update_info(
            "LATEST_VERSION",
            re.search(r'(\d+\.\d+\.\d+, build \d+),', p_obj.get_text().replace('\xa0', '')).group(1)
        )
        self.update_info("DOWNLOAD_LINK", "%s/download.php" % self.BASE_URL)
        self.update_info("BUILD_CHANGELOG", "%s/download.php?zz=v4changelog" % self.BASE_URL)

class RaspberryPiEepromStable(CheckUpdateWithBuildDate):
    fullname = "Raspberry Pi4 bootloader EEPROM Stable"
    tags = ("RaspberryPi", "eeprom")
    file_path = "firmware/stable"

    @classmethod
    def date_transform(cls, date_str: str) -> int:
        return int(date_str)

    @staticmethod
    def _get_build_date(file_name: str) -> str:
        return re.sub(r'[^\d]', '', file_name)

    def do_check(self):
        files = json.loads(
            self.request_url(
                "https://api.github.com/repos/raspberrypi/rpi-eeprom/contents/%s" % self.file_path,
                params={"ref": "master"},
            )
        )
        files = [f for f in files if re.match(r'^pieeprom-[\d-]+.bin$', f["name"])]
        files.sort(key=lambda f: self.date_transform(self._get_build_date(f["name"])))
        latest_file = files[-1]
        self.update_info("LATEST_VERSION", latest_file["name"])
        self.update_info("DOWNLOAD_LINK", latest_file["download_url"])
        self.update_info("FILE_SIZE", "%0.1f KB" % (int(latest_file["size"]) / 1024))
        self.update_info("BUILD_DATE", self._get_build_date(latest_file["name"]))
        self.update_info(
            "BUILD_CHANGELOG",
            "https://github.com/raspberrypi/rpi-eeprom/blob/master/firmware/release-notes.md"
        )

class RaspberryPiEepromBeta(RaspberryPiEepromStable):
    fullname = "Raspberry Pi4 bootloader EEPROM Beta"
    file_path = "firmware/beta"

class RaspberryPiOS64(CheckUpdate):
    fullname = "Raspberry Pi OS (64-bit)"
    tags = ("RaspberryPi", "RaspberryPiOS")

    def do_check(self):
        url = "https://downloads.raspberrypi.org/os_list_imagingutility_v3.json"
        if "os_list_imagingutility_v4.json" in self.request_url("https://downloads.raspberrypi.org"):
            print_and_log(
                "%s: There is a new version of the api interface. Please update the crawler." % self.name,
                level=logging.WARNING,
            )
        json_dic = json.loads(self.request_url(url))
        for os_ in json_dic["os_list"]:
            if os_["name"] == "Raspberry Pi OS (other)":
                for item in os_["subitems"]:
                    if item["name"] == "Raspberry Pi OS (64-bit)":
                        self.update_info("BUILD_DATE", item["release_date"])
                        self.update_info(
                            "FILE_SIZE",
                            "%0.1f MB" % (int(item["image_download_size"]) / 1024 / 1024)
                        )
                        self.update_info("DOWNLOAD_LINK", item["url"])
                        self.update_info("LATEST_VERSION", item["url"].rsplit('/', 1)[1])
                        self.update_info(
                            "BUILD_CHANGELOG",
                            "https://downloads.raspberrypi.org/raspios_arm64/release_notes.txt"
                        )
                        return
        else:
            raise Exception("Parsing failed!")

class Switch520(CheckUpdate):
    fullname = "Switch520"
    BASE_URL = "https://xxxxx520.com/"
    TG_SENDTO_SP = os.getenv("TG_SENDTO_SP")

    def do_check(self):
        if 0 <= datetime.datetime.now().hour <= 7:
            return
        req_url = self.BASE_URL + "switchyouxi"
        # try:
        #     bs_obj = self.get_bs(self.request_url(req_url, headers={"user-agent": CHROME_UA}))
        # except req_exceptions.RequestException:
        #     time.sleep(2)
        #     bs_obj = self.get_bs(self.request_url(req_url, headers={"user-agent": CHROME_UA}, proxies=None))
        bs_obj = self.get_bs(self.request_url(req_url, headers={"user-agent": CHROME_UA}, proxies=None))
        articles = bs_obj.select("article")
        if not articles:
            return
        articles_info = {}
        for article in articles:
            a_bookmark = article.select_one('a[rel="bookmark"]')
            articles_info[article["id"]] = {
                "name": a_bookmark["title"],
                "url": a_bookmark["href"],
                "image_url": article.select_one("img")["data-src"],
                "tags": [a.get_text().strip() for a in article.select('a[rel="category"]')],
                "update_time": article.select_one("time")["datetime"],
            }
        self.update_info("LATEST_VERSION", articles_info)

    def get_print_text(self):
        raise NotImplemented

    def send_message(self):
        fetch_articles_info = json.loads(self.info_dic["LATEST_VERSION"])
        if self.prev_saved_info is None:
            saved_articles_info = {}
        else:
            try:
                saved_articles_info = json.loads(self.prev_saved_info.LATEST_VERSION)
            except json.decoder.JSONDecodeError:
                saved_articles_info = {}
        new_ids = fetch_articles_info.keys() - saved_articles_info.keys()
        sorted_new_ids = sorted(new_ids, key=lambda x: fetch_articles_info[x]["update_time"])
        try:
            for id_ in sorted_new_ids:
                item = fetch_articles_info[id_]
                self.tags = item["tags"]
                _send_photo(
                    item["image_url"],
                    "\n".join([
                        '<a href="%s">%s</a>' % (item["url"], item["name"]),
                        "",
                        self.get_tags_text(allow_empty=True),
                    ]),
                    send_to=self.TG_SENDTO_SP,
                    parse_mode="html",
                )
                time.sleep(2)
        finally:
            self.tags = tuple()

class Apktool(GithubReleases):
    fullname = "Apktool"
    repository_url = "iBotPeaches/Apktool"

class ClashForWindows(GithubReleases):
    fullname = "Clash for Windows"
    repository_url = "Fndroid/clash_for_windows_pkg"
    tags = ("Clash",)

class EhviewerOverhauled(GithubReleases):
    fullname = "Ehviewer"
    repository_url = "Ehviewer-Overhauled/Ehviewer"
    tags = ("Ehviewer",)

    def is_updated(self):
        r = super().is_updated()
        if not r:
            return r
        return not bool(re.search(r'alpha|beta|rc', self.info_dic["BUILD_VERSION"]))

class Magisk(GithubReleases):
    fullname = "Magisk Stable"
    repository_url = "topjohnwu/Magisk"

class ManjaroArmRpi4Images(GithubReleases):
    fullname = "Manjaro ARM Image for Raspberry Pi 3/3+/4/400"
    repository_url = "manjaro-arm/rpi4-images"
    tags = ("RaspberryPi", "Manjaro")

    def is_updated(self):
        r = super().is_updated()
        if not r:
            return r
        try:
            actions_runs = json.loads(
                self.request_url('https://api.github.com/repos/%s/actions/runs' % self.repository_url)
            )
            for wf in actions_runs["workflow_runs"]:
                if wf["name"] == "image_build_all":
                    jobs = json.loads(self.request_url(wf["jobs_url"]))
                    # 等待所有的编译任务完成后再推送
                    if not [job for job in jobs["jobs"] if job["status"] != "completed"]:
                        return True
                    print_and_log(
                        "%s: There is a new release tag, but the action job has not been completed yet." % self.name,
                        level=logging.WARNING,
                    )
                    break
            return False
        except req_exceptions.RequestException:
            return False

class Notepad3(GithubReleases):
    fullname = "Notepad3"
    repository_url = "rizonesoft/Notepad3"

class Sandboxie(GithubReleases):
    fullname = "Sandboxie (By DavidXanatos)"
    repository_url = "sandboxie-plus/Sandboxie"

class Rufus(GithubReleases):
    fullname = "Rufus"
    repository_url = "pbatard/rufus"

class Ventoy(GithubReleases):
    fullname = "Ventoy"
    repository_url = "ventoy/Ventoy"

CHECK_LIST = (
    Linux414Y,
    GoogleClangPrebuilt,
    WireGuard,
    BeyondCompare4,
    RaspberryPiEepromStable,
    RaspberryPiEepromBeta,
    RaspberryPiOS64,
    Switch520,
    Apktool,
    ClashForWindows,
    EhviewerOverhauled,
    Magisk,
    ManjaroArmRpi4Images,
    Notepad3,
    Rufus,
    Sandboxie,
    Ventoy,
)
