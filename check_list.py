#!/usr/bin/env python3
# encoding: utf-8

import json
import time
import re
import logging
import os

from requests import exceptions as req_exceptions

from check_init import (
    CheckUpdate, CheckUpdateWithBuildDate, CheckMultiUpdate, SfCheck, PlingCheck, GithubReleases, CHROME_UA
)
from tgbot import send_message as _send_message, send_photo as _send_photo
from logger import print_and_log

class Linux414Y(CheckUpdate):
    fullname = "Linux Kernel stable v4.14.y"
    tags = ("Linux", "Kernel")
    # enable_pagecache = True
    re_pattern = r'4\.14\.\d+'

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url_text(url))
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

class GoogleClangPrebuilt(CheckMultiUpdate):
    fullname = "Google Clang Prebuilt"
    tags = ("clang",)
    BASE_URL = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url_text(self.BASE_URL + "/+log"))
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

    def send_message_single(self, key, item):

        def _get_detailed_version(url: str) -> str:
            bs_obj_2 = self.get_bs(self.request_url_text(url))
            commit_text = bs_obj_2.find("pre").get_text().splitlines()[2]
            if commit_text[-1] == ".":
                commit_text = commit_text[:-1]
            return commit_text

        try:
            detailed_version = _get_detailed_version(item["commit_url"])
        except:
            detailed_version = key
        _send_message(
            "*%s Update*\n%s\n\n[Commit](%s)\n\nDownload tar.gz:\n[%s](%s)" % (
                self.fullname, self.get_tags_text(), item["commit_url"], detailed_version,
                "%s/+archive/%s/clang-%s.tar.gz" % (self.BASE_URL, key, item["release_version"]),
            )
        )

class WireGuard(CheckUpdate):
    fullname = "WireGuard for Linux 3.10 - 5.5"

    def do_check(self):
        base_url = "https://git.zx2c4.com/wireguard-linux-compat"
        fetch_url = "https://build.wireguard.com/distros.txt"
        fetch_text = self.request_url_text(fetch_url)
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
        fetch_url = "%s/download" % self.BASE_URL
        bs_obj = self.get_bs(self.request_url_text(fetch_url))
        p_obj = bs_obj.select_one('#content > h2')
        self.update_info(
            "LATEST_VERSION",
            re.search(r'(\d+\.\d+\.\d+,\s*build\s*\d+),', re.sub(r'\s+', ' ', p_obj.get_text())).group(1)
        )
        self.update_info("DOWNLOAD_LINK", fetch_url)
        self.update_info("BUILD_CHANGELOG", "%s/download/v4changelog" % self.BASE_URL)

class RaspberryPiEepromStable(CheckUpdateWithBuildDate):
    fullname = "Raspberry Pi4 bootloader EEPROM Stable"
    tags = ("RaspberryPi", "eeprom")
    file_path = "firmware/stable"

    @classmethod
    def date_transform(cls, date_str: str) -> int:
        return int(date_str)

    @staticmethod
    def _get_build_date(file_name: str) -> str:
        return re.sub(r'\D', '', file_name)

    def do_check(self):
        files = json.loads(
            self.request_url_text(
                "https://api.github.com/repos/raspberrypi/rpi-eeprom/contents/%s" % self.file_path,
                params={"ref": "master"},
            )
        )
        files = [f for f in files if re.match(r'^pieeprom-[\d-]+.bin$', f["name"])]
        files.sort(key=lambda f: self.date_transform(self._get_build_date(f["name"])))
        latest_file = files[-1]
        self.update_info("LATEST_VERSION", latest_file["name"])
        self.update_info("DOWNLOAD_LINK", latest_file["download_url"])
        self.update_info("FILE_SIZE", self.get_human_readable_file_size(int(latest_file["size"])))
        self.update_info("BUILD_DATE", self._get_build_date(latest_file["name"]))
        self.update_info(
            "BUILD_CHANGELOG",
            "https://github.com/raspberrypi/rpi-eeprom/blob/master/firmware/release-notes.md"
        )

class RaspberryPiEepromBeta(RaspberryPiEepromStable):
    fullname = "Raspberry Pi4 bootloader EEPROM Beta"
    file_path = "firmware/beta"
    _skip = True

class RaspberryPiOS64(CheckUpdate):
    fullname = "Raspberry Pi OS (64-bit)"
    tags = ("RaspberryPi", "RaspberryPiOS")

    def do_check(self):
        url = "https://downloads.raspberrypi.org/os_list_imagingutility_v3.json"
        json_dic = json.loads(self.request_url_text(url))
        for os_ in json_dic["os_list"]:
            if os_["name"] == "Raspberry Pi OS (other)":
                for item in os_["subitems"]:
                    if item["name"] == "Raspberry Pi OS (64-bit)":
                        self.update_info("BUILD_DATE", item["release_date"])
                        self.update_info(
                            "FILE_SIZE",
                            self.get_human_readable_file_size(int(item["image_download_size"]))
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

class PhoronixLinuxKernelNews(CheckMultiUpdate):
    fullname = "Linux Kernel News Archives"
    BASE_URL = "https://www.phoronix.com"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url_text(
            self.BASE_URL+"/linux/Linux+Kernel", headers={"user-agent": CHROME_UA}
        ))
        articles = bs_obj.select("#main > article")
        if not articles:
            return
        articles_info = {}
        for article in articles:
            article_header = article.select_one("header > a")
            article_details_re_match = re.search(
                r'(.*?)\s+-\s+(.*?)\s+-\s+.*', article.select_one(".details").get_text()
            )
            article_date = article_details_re_match.group(1)
            article_tag = article_details_re_match.group(2)
            articles_info[self.BASE_URL + article_header["href"]] = {
                "title": article_header.get_text(),
                "image_url": article.select_one(".home_icons")["src"],
                "summary": article.select_one("p").get_text(),
                "comments_url": self.BASE_URL + article.select_one(".comments > a")["href"],
                "date": article_date,
                "tag": article_tag,
            }
        self.update_info("LATEST_VERSION", articles_info)

    def send_message_single(self, key, item):
        _send_photo(
            item["image_url"],
            "\n".join([
                "[%s](%s)" % (item["title"], key),
                item["date"] + ' - ' + '_%s_' % item["tag"],
                "",
                item["summary"],
                "",
                "[Comments](%s)" % item["comments_url"],
            ]),
            send_to=os.getenv("TG_BOT_MASTER", ""),
        )

class AckAndroid12510LTS(CheckUpdate):
    fullname = "android12-5.10-lts"

    def do_check(self):
        json_text = self.request_url_text(
            "https://android-review.googlesource.com/changes/",
            params={"n": 25, "q": "project:kernel/common branch:"+self.fullname},
        )
        if json_text.startswith(")]}'\n"):
            json_text = json_text[5:]
        json_data = json.loads(json_text)
        assert isinstance(json_data, list)
        for item in json_data:
            if item.get("status", "").upper() != "MERGED":
                continue
            if title := item.get("subject"):
                if re_match := re.search(r"^Merge 5\.10\.(\d+) into", title):
                    self.update_info("LATEST_VERSION", re_match.group(1))
                    return

    def get_print_text(self):
        return "Google already merged `5.10.%s` into [%s](%s)" % (
            self.info_dic["LATEST_VERSION"],
            self.fullname,
            "https://android-review.googlesource.com/q/project:kernel/common+branch:%s" % self.fullname,
        )

    def send_message(self):
        _send_message(self.get_print_text(), send_to=os.getenv("TG_BOT_MASTER", ""))

class XiaomiEuMultilangStable(SfCheck):
    fullname = "Xiaomi.eu Multilang MIUI ROM stable"
    project_name = "xiaomi-eu-multilang-miui-roms"
    sub_path = "xiaomi.eu/MIUI-STABLE-RELEASES/MIUIv14"
    tags = ("Marble", "XiaomiEU", "MIUI", "Stable")

    @classmethod
    def filter_rule(cls, string: str) -> bool:
        return string.endswith(".zip") and "marble" in string.lower()

class MotoWidget(PlingCheck):
    fullname = "Moto Widget"
    p_id = 1996274

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

class MagiskCanary(CheckUpdate):
    fullname = "Magisk Canary"

    def do_check(self):
        json_dic = json.loads(self.request_url_text("https://github.com/topjohnwu/magisk-files/raw/master/canary.json"))
        magisk_info = json_dic.get("magisk")
        if not magisk_info:
            return
        self.update_info("LATEST_VERSION", magisk_info["versionCode"])
        self.update_info("DOWNLOAD_LINK", "[%s](%s)" % (magisk_info["link"].rsplit('/', 1)[-1], magisk_info["link"]))
        self.update_info("BUILD_VERSION", magisk_info["versionCode"])
        self.update_info("BUILD_CHANGELOG", magisk_info["note"])

class Jadx(GithubReleases):
    fullname = "jadx (Dex to Java decompiler)"
    repository_url = "skylot/jadx"

class KernelSU(GithubReleases):
    fullname = "KernelSU"
    repository_url = "tiann/KernelSU"

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
                self.request_url_text('https://api.github.com/repos/%s/actions/runs' % self.repository_url)
            )
            for wf in actions_runs["workflow_runs"]:
                if wf["name"] == "image_build_all":
                    jobs = json.loads(self.request_url_text(wf["jobs_url"]))
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

class Scrcpy(GithubReleases):
    fullname = "Scrcpy (screen copy)"
    repository_url = "Genymobile/scrcpy"

class Shamiko(GithubReleases):
    fullname = "Shamiko"
    repository_url = "LSPosed/LSPosed.github.io"

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
    PhoronixLinuxKernelNews,
    AckAndroid12510LTS,
    XiaomiEuMultilangStable,
    MotoWidget,
    Apktool,
    ClashForWindows,
    EhviewerOverhauled,
    Jadx,
    KernelSU,
    Magisk,
    MagiskCanary,
    ManjaroArmRpi4Images,
    Notepad3,
    Rufus,
    Sandboxie,
    Scrcpy,
    Shamiko,
    Ventoy,
)
