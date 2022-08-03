#!/usr/bin/env python3
# encoding: utf-8

import json
import time
from collections import OrderedDict
from datetime import datetime
import re

from requests import exceptions as requests_exceptions
from telebot.apihelper import ApiTelegramException
from sqlalchemy.orm import exc as sqlalchemy_exc

from check_init import (
    CHROME_UA, CheckUpdate, CheckUpdateWithBuildDate,
    SfCheck, SfProjectCheck, H5aiCheck, AexCheck, PeCheck, PlingCheck, GithubReleases
)
from database import Saved
from tgbot import send_message as _send_message
from logger import print_and_log

class Linux414Y(CheckUpdate):
    fullname = "Linux Kernel stable v4.14.y"
    re_pattern = r'4\.14\.\d+'
    # enable_pagecache = True

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
        return "*Linux Kernel stable* [v%s](%s) *update*\n\n[Commits](%s)" % (
            self.info_dic["LATEST_VERSION"],
            self.info_dic["DOWNLOAD_LINK"],
            self.info_dic["BUILD_CHANGELOG"],
        )

class GoogleClangPrebuilt(CheckUpdate):
    fullname = "Google Clang Prebuilt"
    BASE_URL = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"

    def __init__(self):
        super().__init__()
        self._private_dic["sp_commits"] = OrderedDict()
        self._private_dic["extra_ids"] = []

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self.BASE_URL + "/+log"))
        commits = bs_obj.select_one(".CommitLog").select("li")
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
                    self._private_dic["sp_commits"][commit_id] = {
                        "commit_url": commit_url,
                        "commit_title": commit_title,
                        "release_version": release_version,
                    }
        self.update_info("LATEST_VERSION", list(self._private_dic["sp_commits"].keys()))

    def is_updated(self):
        if not self.info_dic["LATEST_VERSION"]:
            return False
        try:
            saved_info = Saved.get_saved_info(self.name)
        except sqlalchemy_exc.NoResultFound:
            # Forced overwrite
            self.write_to_database()
            return False
        self_ids = set(self._private_dic["sp_commits"].keys())
        saved_ids = set(json.loads(saved_info.LATEST_VERSION))
        extra_ids = self_ids - saved_ids
        if extra_ids:
            self._private_dic["extra_ids"] = extra_ids
        return bool(extra_ids)

    def get_print_text(self):
        raise NotImplemented

    @classmethod
    def _get_print_text(cls, dic):
        return "*%s Update*\n\n[Commit](%s)\n\nDownload tar.gz:\n[%s](%s)" % (
            cls.fullname, dic["BUILD_CHANGELOG"], dic["BUILD_VERSION"], dic["DOWNLOAD_LINK"],
        )

    @classmethod
    def get_detailed_version(cls, url):
        bs_obj_2 = cls.get_bs(cls.request_url(url))
        commit_text = bs_obj_2.find("pre").get_text().splitlines()[2]
        if commit_text[-1] == ".":
            commit_text = commit_text[:-1]
        return commit_text

    def send_message(self):
        for id_ in self._private_dic["extra_ids"]:
            commit_url = self._private_dic["sp_commits"][id_]["commit_url"]
            release_version = self._private_dic["sp_commits"][id_]["release_version"]
            try:
                detailed_version = self.get_detailed_version(commit_url)
            except:
                detailed_version = id_
            _send_message(self._get_print_text(
                dic={
                    "BUILD_CHANGELOG": commit_url,
                    "BUILD_VERSION": detailed_version,
                    "DOWNLOAD_LINK": "%s/+archive/%s/clang-%s.tar.gz" % (
                        self.BASE_URL, id_, release_version,
                    ),
                }
            ))

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
        return "*%s update*\n\n[Commits](%s)\n\nDownload tar.gz:\n[%s](%s)" % (
            self.fullname,
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

class RaspberryPiEepromStable(CheckUpdate):
    fullname = "Raspberry Pi4 bootloader EEPROM Stable"
    file_path = "firmware/stable"

    def do_check(self):
        files = json.loads(
            self.request_url(
                "https://api.github.com/repos/raspberrypi/rpi-eeprom/contents/%s" % self.file_path,
                params={"ref": "master"},
            )
        )
        files = [f for f in files if re.match(r'^pieeprom-[\d-]+.bin$', f["name"])]
        files.sort(key=lambda f: int(re.sub(r'[^\d]', '', f["name"])))
        latest_file = files[-1]
        self.update_info("LATEST_VERSION", latest_file["name"])
        self.update_info("DOWNLOAD_LINK", latest_file["download_url"])
        self.update_info("FILE_SIZE", "%0.1f KB" % (int(latest_file["size"]) / 1024))
        self.update_info(
            "BUILD_CHANGELOG",
            "https://github.com/raspberrypi/rpi-eeprom/blob/master/firmware/release-notes.md"
        )

class RaspberryPiEepromBeta(RaspberryPiEepromStable):
    fullname = "Raspberry Pi4 bootloader EEPROM Beta"
    file_path = "firmware/beta"

class RaspberryPiOS64(CheckUpdate):
    fullname = "Raspberry Pi OS (64-bit)"

    def do_check(self):
        url = "https://downloads.raspberrypi.org/os_list_imagingutility_v3.json"
        if "os_list_imagingutility_v4.json" in self.request_url("https://downloads.raspberrypi.org"):
            print_and_log(
                "%s: There is a new version of the api interface. Please update the crawler." % self.name,
                level="warning"
            )
        json_dic = json.loads(self.request_url(url))
        for os in json_dic["os_list"]:
            if os["name"] == "Raspberry Pi OS (other)":
                for item in os["subitems"]:
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

class WslKernel(CheckUpdate):
    fullname = "Windows Subsystem for Linux Kernel"
    URL = "https://www.catalog.update.microsoft.com/Search.aspx?q=wsl"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self.URL))
        trs = bs_obj.select('#ctl00_catalogBody_updateMatches tr')[1:]
        if not trs:
            return
        trs.sort(key=lambda tr: time.strptime(tr.select("td")[4].get_text().strip(), "%m/%d/%Y"), reverse=True)
        self._private_dic["file_list"] = [
            (
                tr["id"].rsplit('_', 1)[0],  # id
                tr.select_one("a").get_text().strip(),  # Title
                tr.select("td")[6].select_one("span").get_text().strip(),  # Size
            )
            for tr in trs
        ]
        self.update_info("LATEST_VERSION", self._private_dic["file_list"])

    def get_print_text(self):
        return "\n".join([
            "*%s Update*" % self.fullname,
            time.strftime("%Y-%m-%d", time.localtime(time.time())),
            "",
            "File list:",
            "\n".join([
                "[%s (%s)](%s)" % (item[1], item[2], self.URL) for item in self._private_dic["file_list"]
            ]),
        ])

class Apktool(GithubReleases):
    fullname = "Apktool"
    repository_url = "iBotPeaches/Apktool"

class ClashForWindows(GithubReleases):
    fullname = "Clash for Windows"
    repository_url = "Fndroid/clash_for_windows_pkg"

class Magisk(GithubReleases):
    fullname = "Magisk Stable"
    repository_url = "topjohnwu/Magisk"

class ManjaroArmRpi4Images(GithubReleases):
    fullname = "Manjaro ARM Image for Raspberry Pi 3/3+/4/400"
    repository_url = "manjaro-arm/rpi4-images"

class Notepad3(GithubReleases):
    fullname = "Notepad3"
    repository_url = "rizonesoft/Notepad3"

class Sandboxie(GithubReleases):
    fullname = "Sandboxie (By DavidXanatos)"
    repository_url = "sandboxie-plus/Sandboxie"

class Ventoy(GithubReleases):
    fullname = "Ventoy"
    repository_url = "ventoy/Ventoy"

class AdrarProject(SfProjectCheck):
    project_name = "unofficial-by-adrar"
    developer = "AdrarHussain"

class AdrarProject2(PlingCheck):
    fullname = "New rom release by AdrarHussain"
    p_id = 1459808
    enable_pagecache = True

    def filter_rule(self, build_dic):
        return all([
            PlingCheck.filter_rule(build_dic),
            not build_dic["name"].startswith("RR"),
        ])

class AexS(AexCheck):
    fullname = "AospExtended 12 Official"
    sub_path = "whyred/s"

class AexSGapps(AexCheck):
    fullname = "AospExtended 12 (with Gapps) Official"
    sub_path = "whyred/s_gapps"

class AexRU1(PlingCheck):
    fullname = "AospExtended 11 (Unofficial By SakilMondal)"
    p_id = 1423583

class AexSU1(PlingCheck):
    fullname = "AospExtended 12 (Unofficial By SakilMondal)"
    p_id = 1613676

class Aicp(CheckUpdate):
    fullname = "AICP Official"

    def do_check(self):
        req_text = self.request_url(
            "https://cors.aicp-rom.com/http://ota.aicp-rom.com/update.php?device=whyred",
            headers={
                "Origin": "https://dwnld.aicp-rom.com",
                "Referer": "https://dwnld.aicp-rom.com/",
                "User-Agent": CHROME_UA
            }
        )
        json_dic = json.loads(req_text).get("updates")
        if json_dic:
            latest_build = json_dic[0]
            self.update_info("LATEST_VERSION", latest_build["name"])
            self.update_info("BUILD_VERSION", latest_build["version"].replace("\n", " "))
            self.update_info("FILE_SIZE", latest_build["size"] + " MB")
            self.update_info("DOWNLOAD_LINK", latest_build["url"])
            self.update_info("FILE_MD5", latest_build["md5"])
            self.update_info("BUILD_CHANGELOG", latest_build["url"] + ".html")

class Ancient(SfCheck):
    fullname = "Ancient OS"
    project_name = "ancientrom"
    sub_path = "whyred"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class AncientGapps(Ancient):
    fullname = "Ancient OS (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Aosip(H5aiCheck):
    fullname = "AOSiP Official"
    base_url = "https://get.aosip.dev"
    sub_url = "/whyred/"

    _skip = True

    def do_check(self):
        super().do_check()
        self.update_info(
            "BUILD_CHANGELOG",
            "https://raw.githubusercontent.com/AOSiP-Devices/Updater-Stuff/master/whyred/changelog"
        )

    def after_check(self):
        self.update_info(
            "FILE_MD5",
            self.get_hash_from_file(self.info_dic["DOWNLOAD_LINK"] + ".md5sum")
        )

class AosipDf(H5aiCheck):
    fullname = "AOSiP DerpFest Official"
    base_url = "https://get.derpfest.org"
    sub_url = "/whyred-vanilla/builds/"

    _skip = True

    def after_check(self):
        self.update_info(
            "FILE_MD5",
            self.get_hash_from_file(
                self.base_url + "/whyred-vanilla/md5/" + self.info_dic["LATEST_VERSION"] + ".md5sum"
            )
        )

class AosipDfGapps(H5aiCheck):
    fullname = "AOSiP DerpFest Official (Include Gapps)"
    base_url = "https://get.derpfest.org"
    sub_url = "/whyred/builds/"

    _skip = True

    def after_check(self):
        self.update_info(
            "FILE_MD5",
            self.get_hash_from_file(
                self.base_url + "/whyred/md5/" + self.info_dic["LATEST_VERSION"] + ".md5sum"
            )
        )

class Aospa(CheckUpdateWithBuildDate):
    fullname = "Paranoid Android Official"
    _skip = True

    @classmethod
    def date_transform(cls, date_str):
        return int(date_str)

    def do_check(self):
        req_text = self.request_url("https://api.aospa.co/updates/whyred")
        json_dic = json.loads(req_text)
        builds = json_dic.get("updates")
        if builds:
            latest_build = sorted(builds, key=lambda x: int(x["build"]))[-1]
            self.update_info("BUILD_DATE", latest_build["build"])
            self.update_info("FILE_MD5", latest_build["md5"])
            self.update_info("LATEST_VERSION", latest_build["name"])
            self.update_info("FILE_SIZE", "%0.2f MB" % (int(latest_build["size"]) / 1000 / 1000,))
            self.update_info("DOWNLOAD_LINK", latest_build["url"])
            self.update_info("BUILD_VERSION", latest_build["version"])

class AospaU1(SfCheck):
    fullname = "Paranoid Android (Unofficial By orges)"
    project_name = "aospa-whyred"

class ArnavProject(SfProjectCheck):
    project_name = "roms-by-arnav"
    developer = "Arnav"

class ArrowQ(CheckUpdate):
    fullname = "Arrow OS Q Official"
    _skip = True

    device_name = "whyred"
    device_version = "arrow-10.0"
    build_type_flag = "vanilla"

    def __init__(self):
        super().__init__()
        try:
            saved_info = Saved.get_saved_info(self.name)
        except sqlalchemy_exc.NoResultFound:
            self.previous_changelog = ""
        else:
            self.previous_changelog = saved_info.BUILD_CHANGELOG

    def do_check(self):
        url_source = self.request_url(
            "https://arrowos.net/device.php",
            method="post",
            data={
                "device": self.device_name,
                "deviceVariant": "official",
                "deviceVersion": self.device_version,
                "supportedVersions": [self.device_version, ],
                "supportedVariants": ["official", ],
            }
        )
        bs_obj = self.get_bs(url_source)
        self.update_info(
            "LATEST_VERSION",
            bs_obj.select_one("#%s-filename" % self.build_type_flag)["name"]
        )
        build_info_text = bs_obj.select_one("#%s-filename" % self.build_type_flag).parent.get_text()
        self.update_info("FILE_SIZE", self.grep(build_info_text, "Size"))
        self.update_info("BUILD_VERSION", self.grep(build_info_text, "Version"))
        self.update_info("BUILD_DATE", self.grep(build_info_text, "Date"))
        self.update_info(
            "FILE_SHA256",
            bs_obj.select_one("#%s-file_sha256" % self.build_type_flag).get_text().strip()
        )
        self.update_info(
            "BUILD_CHANGELOG",
            "# Device side changes\n%s\n# Source changelog\nhttps://arrowos.net/changelog.php"
            % bs_obj.select_one("#source-changelog").parent.find("p").get_text().strip()
        )
        self.update_info("DOWNLOAD_LINK", "https://arrowos.net/download/%s" % self.device_name)

    def send_message(self):
        if self.previous_changelog == self.info_dic["BUILD_CHANGELOG"]:
            return
        super().send_message()

class ArrowQGapps(ArrowQ):
    fullname = "Arrow OS Q Official (Include Gapps)"
    build_type_flag = "gapps"

class ArrowR(ArrowQ):
    fullname = "Arrow OS 11 Official"
    device_version = "arrow-11.0"
    _skip = False

class ArrowRGapps(ArrowR):
    fullname = "Arrow OS 11 Official (Include Gapps)"
    device_version = "arrow-11.0"
    build_type_flag = "gapps"

class ArrowS(ArrowR):
    fullname = "Arrow OS 12 Official"
    device_version = "arrow-12.0"

class ArrowSGapps(ArrowR):
    fullname = "Arrow OS 12 Official (Include Gapps)"
    device_version = "arrow-12.0"
    build_type_flag = "gapps"

class Atom(SfCheck):
    fullname = "Atom OS Official"
    project_name = "atom-os-project"
    sub_path = "whyred/"
    _skip = True

class Awaken(PlingCheck):
    fullname = "Project Awaken Official (By SakilMondal)"
    p_id = 1446633
    _skip = True

    def do_check(self):
        super().do_check()
        self.update_info("LATEST_VERSION", self._private_dic["latest_build"]["version"])

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" not in build_dic["version"].upper()

class AwakenGapps(Awaken):
    fullname = "Project Awaken Official (Include Gapps)(By SakilMondal)"

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" in build_dic["version"].upper()

class BlissR(SfCheck):
    fullname = "Bliss Rom 11 Official"
    project_name = "blissroms"
    sub_path = "R/whyred/"

class Bootleggers(SfCheck):
    fullname = "Bootleggers Rom Official"
    project_name = "bootleggersrom"
    sub_path = "builds/whyred/"
    _skip = True

class CandyQ(SfCheck):
    fullname = "Candy Rom Q Official"
    project_name = "candyroms"
    sub_path = "Official/ten/whyred/"
    _skip = True

class Carbon(CheckUpdate):
    fullname = "Carbon Rom Official"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("https://get.carbonrom.org/device-whyred.html"))
        latest_build = bs_obj.find("tbody").find("tr").select("td")
        self.update_info("BUILD_TYPE", latest_build[1].get_text().strip())
        self.update_info("LATEST_VERSION", latest_build[2].find("dd").get_text().strip())
        self.update_info("DOWNLOAD_LINK", latest_build[2].find("dd").find("a")["href"])
        self.update_info("FILE_MD5", latest_build[2].select("dd")[1].get_text().strip())
        self.update_info("FILE_SIZE", latest_build[3].get_text().strip())
        self.update_info("BUILD_DATE", latest_build[4].get_text().strip())

class CarbonU1(SfCheck):
    fullname = "Carbon Rom (Unofficial By fakeyato)"
    project_name = "fakecarbon"
    sub_path = "carbon/"

class Cherish(PlingCheck):
    fullname = "Cherish OS Official"
    p_id = 1460395
    enable_pagecache = True

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" not in build_dic["name"].upper()

class CherishGapps(Cherish):
    fullname = "Cherish OS Official (Include Gapps)"

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" in build_dic["name"].upper()

class Colt(SfCheck):
    fullname = "Colt OS Official"
    project_name = "coltos"
    sub_path = "Whyred/"
    _skip = True

class Conquer(SfCheck):
    fullname = "Conquer OS Official"
    project_name = "conqueros"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class ConquerGapps(Conquer):
    fullname = "Conquer OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Corvus(PlingCheck):
    fullname = "Corvus OS Official"
    p_id = 1375302
    enable_pagecache = True

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" not in build_dic["name"].upper()

class CorvusGapps(Corvus):
    fullname = "Corvus OS Official (Include Gapps)"

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" in build_dic["name"].upper()

class Cosmic(SfCheck):
    fullname = "Cosmic OS Official"
    project_name = "cosmic-os"
    sub_path = "whyred/"
    _skip = True

class CrDroidP(SfCheck):
    fullname = "CrDroid Pie Official"
    project_name = "crdroidpie"
    sub_path = "WHYRED/"
    _skip = True

class CrDroid(SfCheck):
    fullname = "CrDroid Official"
    project_name = "crdroid"
    sub_path = "whyred"

class Cygnus(SfCheck):
    fullname = "CygnusOS Official"
    project_name = "cygnus-android"
    sub_path = "whyred/"
    _skip = True

class DerpFest(SfCheck):
    fullname = "DerpFest Official"
    project_name = "derpfest"
    sub_path = "whyred/"

class Descendant(CheckUpdate):
    fullname = "Descendant Official"
    _skip = True

    def do_check(self):
        base_url = "https://downloads.descendant.me"
        bs_obj = self.get_bs(self.request_url(base_url, proxies=None))
        latest_build_tr = None
        for tr_obj in bs_obj.select_one("#downloadList").select_one("tbody").select("tr"):
            if "whyred" in tr_obj.text:
                latest_build_tr = tr_obj
                break
        if latest_build_tr is None:
            return
        for index, key in enumerate("LATEST_VERSION FILE_MD5 FILE_SIZE BUILD_DATE".split()):
            self.update_info(key, latest_build_tr.select("td")[index].text.strip())
        self.update_info("DOWNLOAD_LINK", "%s%s" % (
            base_url, latest_build_tr.select_one("a")["href"]
        ))

class Dot(CheckUpdate):
    fullname = "Dot OS Official"
    build_type = "vanilla"

    def do_check(self):
        json_info = json.loads(
            self.request_url("https://api.droidontime.com/api/ota/whyred/releases/" + self.build_type)
        )
        latest_release = json_info["releases"][0]
        self.update_info("LATEST_VERSION", latest_release["fileName"])
        self.update_info("FILE_MD5", latest_release["hash"])
        self.update_info("FILE_SIZE", "%0.2f MB" % (int(latest_release["size"]) / 1048576,))
        self.update_info("BUILD_VERSION", latest_release["version"])
        self.update_info("DOWNLOAD_LINK", latest_release["url"])

    def after_check(self):
        self.update_info(
            "DOWNLOAD_LINK",
            "`%s`\n[Official](%s) | [SourceForge](%s)" % (
                self.info_dic["LATEST_VERSION"],
                self.info_dic["DOWNLOAD_LINK"],
                "https://sourceforge.net/projects/dotos-downloads/files/dot11/whyred/%s/%s/download" % (
                    self.build_type, self.info_dic["LATEST_VERSION"]
                ),
            )
        )

class DotGapps(Dot):
    fullname = "Dot OS Official (Include Gapps)"
    build_type = "gapps"

class E(CheckUpdateWithBuildDate):
    fullname = "/e/ Rom Official"
    BASE_URL = "https://images.ecloud.global/dev/whyred/"

    @classmethod
    def date_transform(cls, date_str):
        return time.strptime(date_str, "%Y%m%d")

    @staticmethod
    def parse_date_string_from_filename(filename):
        return re.search(r'\d{14}', filename)[0][:8]

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self.BASE_URL))
        files = [a_tag for a_tag in bs_obj.select("a") if a_tag["href"].endswith(".zip")]
        if not files:
            return
        try:
            files.sort(
                key=lambda a_tag: self.date_transform(self.parse_date_string_from_filename(a_tag.get_text())),
                reverse=True
            )
        except TypeError:
            pass
        latest_build = files[0]
        self.update_info("LATEST_VERSION", latest_build.get_text().strip())
        self.update_info("BUILD_DATE", self.parse_date_string_from_filename(self.info_dic["LATEST_VERSION"]))
        self.update_info("DOWNLOAD_LINK", self.BASE_URL + latest_build["href"])
        self.update_info("BUILD_CHANGELOG", "https://gitlab.e.foundation/e/os/releases/-/releases")

    def after_check(self):
        self.update_info(
            "FILE_MD5",
            self.get_hash_from_file(self.info_dic["DOWNLOAD_LINK"] + ".md5sum")
        )
        self.update_info(
            "FILE_SHA256",
            self.get_hash_from_file(self.info_dic["DOWNLOAD_LINK"] + ".sha256sum")
        )

class EvolutionX(SfCheck):
    fullname = "EvolutionX Official"
    project_name = "evolution-x"
    sub_path = "whyred/"

    def after_check(self):
        self.update_info(
            "BUILD_CHANGELOG",
            (
                "https://raw.githubusercontent.com/Evolution-X-Devices/official_devices/"
                "master/changelogs/whyred/%s.txt" % self.info_dic["LATEST_VERSION"]
            )
        )

class EvolutionXU1(PlingCheck):
    fullname = "EvolutionX (Unofficial By @The_Santy)"
    p_id = 1545610

class Extended(SfCheck):
    fullname = "ExtendedUI Official"
    project_name = "extendedui"
    sub_path = "whyred/"
    _skip = True

class ExtendedU1(PlingCheck):
    fullname = "ExtendedUI (Unofficial By Nesquirt)"
    p_id = 1374700
    _skip = True

class GengKapakProject(SfProjectCheck):
    project_name = "gengkapak"
    developer = "GengKapak Project"
    sub_path = "ROM/whyred/"

class Havoc(CheckUpdate):
    fullname = "Havoc OS Official"
    enable_pagecache = True
    base_url = "https://download.havoc-os.com/"
    dir_path = "whyred"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("".join([self.base_url, "?dir=", self.dir_path])))
        builds = bs_obj.select("#file-list > li > a")
        for build in builds:
            build_name = build.select_one(".truncate").text.strip()
            if self.filter_rule(build_name):
                self.update_info("LATEST_VERSION", build_name)
                self.update_info("DOWNLOAD_LINK", self.base_url+build["href"])
                self.update_info("FILE_SIZE", build.select("div > div")[-2].text.strip())
                self.update_info("BUILD_DATE", build.select("div > div")[-1].text.strip())
                break

    def after_check(self):
        try:
            json_text = self.request_url(
                "".join([self.base_url, "?info=", self.dir_path, "/", self.info_dic["LATEST_VERSION"]])
            )
        except requests_exceptions.HTTPError as error:
            if "too large" in str(error):
                return
            raise
        if "<script" in json_text:
            json_text = re.sub(r"<script.*?script>", "", json_text, flags=re.S).strip()
        file_info_hashes = json.loads(json_text).get("hashes", {})
        self.update_info("FILE_MD5", file_info_hashes.get("md5"))
        self.update_info("FILE_SHA1", file_info_hashes.get("sha1"))
        self.update_info("FILE_SHA256", file_info_hashes.get("sha256"))

    @staticmethod
    def filter_rule(string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class HavocGapps(Havoc):
    fullname = "Havoc OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class HavocU1(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)(Include Gapps)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/whyred-gapps/"
    _skip = True

class HavocU3(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/Havoc-alpha/"
    _skip = True

class Ion(SfCheck):
    fullname = "ION Official"
    project_name = "i-o-n"
    sub_path = "device/xiaomi/whyred/"
    _skip = True

class Komodo(SfCheck):
    fullname = "Komodo OS Official"
    project_name = "komodos-rom"
    sub_path = "whyred/"
    _skip = True

class Legion(SfCheck):
    fullname = "Legion OS Official"
    project_name = "legionrom"
    sub_path = "whyred/"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class LegionGapps(Legion):
    fullname = "Legion OS Official (Include Gapps)"
    _skip = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Lineage(CheckUpdate):
    fullname = "Lineage OS Official"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("https://download.lineageos.org/whyred"))
        build = bs_obj.find("tbody").find("tr")
        tds = build.select("td")
        if len(tds) == 7:
            build_type, build_version, build_file, build_size, _, _, build_date = tds
        elif len(tds) == 5:
            build_type, build_version, build_file, build_size, build_date = tds
        else:
            raise Exception("Parsing failed!")
        self.update_info("BUILD_TYPE", build_type.get_text().strip())
        self.update_info("BUILD_VERSION", build_version.get_text().strip())
        self.update_info("LATEST_VERSION", build_file.find("a").get_text().strip())
        self.update_info("DOWNLOAD_LINK", build_file.find("a")["href"].strip())
        self.update_info("FILE_SIZE", build_size.get_text().strip())
        self.update_info("BUILD_DATE", build_date.get_text().strip())
        self.update_info("BUILD_CHANGELOG", "https://download.lineageos.org/whyred/changes/")

    def after_check(self):
        file_sha1 = self.get_hash_from_file(self.info_dic["DOWNLOAD_LINK"] + "?sha1")
        if file_sha1 and file_sha1 != "Hash":
            self.update_info("FILE_SHA1", file_sha1)
        file_sha256 = self.get_hash_from_file(self.info_dic["DOWNLOAD_LINK"] + "?sha256")
        if file_sha256 and file_sha256 != "Hash":
            self.update_info("FILE_SHA256", file_sha256)

class LineageU3(PlingCheck):
    fullname = "Lineage OS 18.0 (Unofficial By SakilMondal)"
    p_id = 1422431

class MalfunctionProject(SfProjectCheck):
    project_name = "sp4ce"
    sub_path = "whyred/"
    developer = "Malfunction"

class Neon(SfCheck):
    fullname = "Neon OS Official"
    project_name = "neonrelease"
    sub_path = "whyred/"
    _skip = True

class Nezuko(SfCheck):
    fullname = "Nezuko OS Official"
    project_name = "nezukoos"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class NezukoGapps(Nezuko):
    fullname = "Nezuko OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Nitrogen(SfCheck):
    fullname = "Nitrogen OS Official"
    project_name = "nitrogen-project"
    sub_path = "whyred/"
    _skip = True

class NitrogenU1(SfCheck):
    fullname = "Nitrogen OS (Unofficial By Bagaskara815)"
    project_name = "nangis"
    sub_path = "NitrogenOS/Whyred/10/"
    _skip = True

class Nusantara(PlingCheck):
    fullname = "Nusantara Project Official"
    p_id = 1422405

class Octavi(PlingCheck):
    fullname = "Octavi OS Official"
    p_id = 1620047
    enable_pagecache = True

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" not in build_dic["name"].upper()

class OctaviGapps(Octavi):
    fullname = "Octavi OS Official (Include Gapps)"

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "GAPPS" in build_dic["name"].upper()

class PixelExtended(SfCheck):
    fullname = "Pixel Extended Official"
    project_name = "pixelextended"
    sub_path = "Whyred/"

class PeR(PeCheck):
    fullname = "Pixel Experience 11 Official"
    model = "whyred"
    index = 0
    tag_name = "11"
    enable_pagecache = True
    _skip = True

class PeRPe(PeR):
    fullname = "Pixel Experience 11 (Plus edition) Official"
    index = 1
    tag_name = "11 (Plus edition)"

class PeS(PeR):
    fullname = "Pixel Experience 12 Official"
    tag_name = "12"

class PeU2(PlingCheck):
    fullname = "Pixel Experience Q (Unofficial By SakilMondal)"
    p_id = 1406086
    _skip = True

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "PLUS" not in build_dic["name"].upper()

class PePeU2(PeU2):
    fullname = "Pixel Experience Q (Plus edition)(Unofficial By SakilMondal)"

    def filter_rule(self, build_dic):
        return PlingCheck.filter_rule(build_dic) and "PLUS" in build_dic["name"].upper()

class PeruBacchaProject(SfProjectCheck):
    project_name = "aosp-project"
    sub_path = "Whyred/"
    developer = "PeruBaccha"

class PixelPlusUI(PlingCheck):
    fullname = "PixelPlusUI Official"
    p_id = 1513365

    def after_check(self):
        super().after_check()
        self.update_info(
            "BUILD_CHANGELOG",
            self.request_url(
                "https://github.com/PixelPlusUI-Devices/official_devices/raw/master/changelogs/whyred/%s.txt"
                % self.info_dic["LATEST_VERSION"]
            )
        )

class PixysR(CheckUpdate):
    fullname = "Pixys OS R Official"
    enable_pagecache = True
    _skip = True

    BASE_URL = "https://pixysos.com"
    device = "whyred"
    android_version_tag = "eleven"
    tab_index = 1

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self.BASE_URL + "/" + self.device))
        div_tab = bs_obj.find("div", {"data-tab-content": self.android_version_tag})
        try:
            div_tab_outer = div_tab.select(".tab__outer")[self.tab_index]
        except IndexError:
            return
        builds = div_tab_outer.select(".build__header")
        if builds:
            latest_build = builds[0]
            self.update_info(
                "BUILD_CHANGELOG", latest_build.select_one(".clogs").get_text().strip() or None
            )
            latest_build_info = latest_build.select_one(".build__info div")
            latest_build_info_text = latest_build_info.get_text().strip().replace(":\n", ":")
            self.update_info("LATEST_VERSION", self.grep(latest_build_info_text, "File Name"))
            self.update_info("FILE_MD5", self.grep(latest_build_info_text, "md5 (hash)"))
            self.update_info("BUILD_DATE", self.grep(latest_build_info_text, "Date & Time"))
            self.update_info("FILE_SIZE", self.grep(latest_build_info_text, "Size"))
            self.update_info("BUILD_VERSION", self.grep(latest_build_info_text, "Version"))
            self.update_info("DOWNLOAD_LINK", self.BASE_URL + latest_build_info.find("a")["href"])

class PixysRGapps(PixysR):
    fullname = "Pixys OS R Official (Include Gapps)"
    tab_index = 2

class PixysSGapps(PixysRGapps):
    fullname = "Pixys OS 12 Official (Include Gapps)"
    android_version_tag = "twelve"
    _skip = False

class Posp(GithubReleases):
    fullname = "POSP Official"
    repository_url = "PotatoDevices/device_xiaomi_whyred"

class ProjectElixir(PlingCheck):
    fullname = "Project Elixir Official"
    p_id = 1673869

class ProjectRadiant(SfCheck):
    fullname = "Project Radiant Official"
    project_name = "projectradiant"

class RaghuVarmaProject(SfProjectCheck):
    project_name = "whyred-rv"
    developer = "Raghu Varma"
    _skip = True

class RandomStuffProject(SfProjectCheck):
    project_name = "random-stuff-for-whyred"
    developer = "James"
    _skip = True

    def is_updated(self):
        result = super().is_updated()
        if not result:
            return False
        # Ignore test builds
        return "/test/" not in self.info_dic["DOWNLOAD_LINK"]

class ResurrectionRemix(SfCheck):
    fullname = "Resurrection Remix OS Q Official"
    project_name = "resurrectionremix-ten"
    sub_path = "whyred/"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "VANILLA" in string.upper()

class ResurrectionRemixGapps(ResurrectionRemix):
    fullname = "Resurrection Remix OS Q Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "VANILLA" not in string.upper()

class ResurrectionRemixU1(AdrarProject2):
    fullname = "Resurrection Remix OS Q (Unofficial By AdrarHussain)"

    def filter_rule(self, build_dic):
        return all([
            PlingCheck.filter_rule(build_dic),
            build_dic["name"].startswith("RR"),
            "VANILLA" in build_dic["name"].upper(),
        ])

class ResurrectionRemixGappsU1(AdrarProject2):
    fullname = "Resurrection Remix OS Q (Unofficial By AdrarHussain)(Include Gapps)"

    def filter_rule(self, build_dic):
        return all([
            PlingCheck.filter_rule(build_dic),
            build_dic["name"].startswith("RR"),
            "VANILLA" not in build_dic["name"].upper(),
        ])


class Revenge(CheckUpdate):
    fullname = "Revenge OS Official"

    def do_check(self):
        latest_info = json.loads(self.request_url(
            "https://raw.githubusercontent.com/RevengeOS-Devices/official_devices/master/whyred/device.json"
        ))
        if not latest_info.get("error"):
            self.update_info("LATEST_VERSION", latest_info["filename"])
            self.update_info("BUILD_DATE", datetime.fromtimestamp(latest_info["datetime"]).ctime())
            self.update_info("FILE_MD5", latest_info["filehash"])
            self.update_info("FILE_SIZE", "%0.1f MB" % (int(latest_info["size"]) / 1024 / 1024))
            self.update_info("DOWNLOAD_LINK", latest_info["url"])
            self.update_info("BUILD_VERSION", latest_info["version"])

    def after_check(self):
        self.update_info(
            "BUILD_CHANGELOG",
            self.request_url("https://download.revengeos.com/download/whyred/changelog.txt").strip()
        )

    def send_message(self):
        try:
            super().send_message()
        except ApiTelegramException:
            self.update_info("BUILD_CHANGELOG", "https://download.revengeos.com/download/whyred/changelog.txt")
            super().send_message()

class Sakura(SfCheck):
    fullname = "Project Sakura ROM Official"
    project_name = "projectsakura"
    sub_path = "whyred/"

class SalmanProject(PlingCheck):
    fullname = "New rom release by Salman"
    p_id = 1420225

class ShapeShift(SfCheck):
    fullname = "ShapeShift OS Official"
    project_name = "shapeshiftos"
    sub_path = "whyred/"
    _skip = True

class StagQ(CheckUpdate):
    fullname = "Stag OS Q Official"
    _skip = True

    def do_check(self):
        base_url = "https://downloads.stag.workers.dev/whyred/"
        default_root_id = "1eTpnilGg2GMH135GYRTWdLnKEBxsKez1"
        json_text = self.request_url(base_url, method="post", params={"rootId": default_root_id})
        json_dic = json.loads(json_text)
        if not (json_dic and json_dic["files"]):
            return
        build_info = json_dic["files"][-1]
        self.update_info("BUILD_DATE", build_info["modifiedTime"])
        self.update_info("LATEST_VERSION", build_info["name"])
        self.update_info("FILE_SIZE", "%0.2f MB" % (int(build_info["size"]) / 1048576,))
        self.update_info(
            "DOWNLOAD_LINK",
            "# Official\n[{0}]({0})\n# SourceForge\n[{1}]({1})".format(
                base_url + build_info["name"],
                "https://sourceforge.net/projects/stagos-10/files/whyred/%s" % build_info["name"],
            )
        )

class StagR(SfCheck):
    fullname = "Stag OS R Official"
    project_name = "stagos-11"
    sub_path = "whyred/"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

    def after_check(self):
        self.update_info(
            "DOWNLOAD_LINK",
            "`%s`\n[SourceForge](%s) | [Mirror](%s)" % (
                self.info_dic["LATEST_VERSION"],
                self.info_dic["DOWNLOAD_LINK"],
                "https://releases.stag-os.workers.dev/%s%s" % (
                    self.sub_path, self.info_dic["LATEST_VERSION"]
                ),
            )
        )

class StagRGapps(StagR):
    fullname = "Stag OS R Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Styx(SfCheck):
    fullname = "Styx OS Official"
    project_name = "styx-os"

class Superior(SfCheck):
    fullname = "Superior OS Official"
    project_name = "superioros"
    sub_path = "whyred/"

class Syberia(SfCheck):
    fullname = "Syberia OS Official"
    project_name = "syberiaos"
    sub_path = "whyred/"
    _skip = True

class SyberiaU1(SfCheck):
    fullname = "Syberia OS (Unofficial By Orges)"
    project_name = "syberia-whyded"
    _skip = True

class TenX(SfCheck):
    fullname = "TenX OS Official"
    project_name = "tenx-os"
    sub_path = "Whyred/"

class Titanium(SfCheck):
    fullname = "Titanium OS Official"
    project_name = "titaniumos"
    sub_path = "whyred/"
    enable_pagecache = True
    _skip = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class TitaniumGapps(Titanium):
    fullname = "Titanium OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class WhymemeProject(SfProjectCheck):
    project_name = "whymeme-roms"
    developer = "jhonse02"

class Xtended(SfCheck):
    fullname = "Xtended Official"
    project_name = "xtended"
    sub_path = "whyred/"

CHECK_LIST = (
    Linux414Y,
    GoogleClangPrebuilt,
    WireGuard,
    BeyondCompare4,
    RaspberryPiEepromStable,
    RaspberryPiEepromBeta,
    RaspberryPiOS64,
    WslKernel,
    Apktool,
    ClashForWindows,
    Magisk,
    ManjaroArmRpi4Images,
    Notepad3,
    Sandboxie,
    Ventoy,
    AdrarProject,
    AdrarProject2,
    AexS,
    AexSGapps,
    AexRU1,
    AexSU1,
    Aicp,
    Ancient,
    AncientGapps,
    Aosip,
    AosipDf,
    AosipDfGapps,
    Aospa,
    AospaU1,
    ArnavProject,
    ArrowQ,
    ArrowQGapps,
    ArrowR,
    ArrowRGapps,
    ArrowS,
    ArrowSGapps,
    Atom,
    Awaken,
    AwakenGapps,
    BlissR,
    Bootleggers,
    CandyQ,
    Carbon,
    CarbonU1,
    Cherish,
    CherishGapps,
    Colt,
    Conquer,
    ConquerGapps,
    Corvus,
    CorvusGapps,
    Cosmic,
    CrDroidP,
    CrDroid,
    Cygnus,
    DerpFest,
    Descendant,
    Dot,
    DotGapps,
    E,
    EvolutionX,
    EvolutionXU1,
    Extended,
    ExtendedU1,
    GengKapakProject,
    Havoc,
    HavocGapps,
    HavocU1,
    HavocU3,
    Ion,
    Komodo,
    Legion,
    LegionGapps,
    Lineage,
    LineageU3,
    MalfunctionProject,
    Neon,
    Nezuko,
    NezukoGapps,
    Nitrogen,
    NitrogenU1,
    Nusantara,
    Octavi,
    OctaviGapps,
    PixelExtended,
    PeR,
    PeRPe,
    PeS,
    PeU2,
    PePeU2,
    PeruBacchaProject,
    PixelPlusUI,
    PixysR,
    PixysRGapps,
    PixysSGapps,
    Posp,
    ProjectElixir,
    ProjectRadiant,
    RaghuVarmaProject,
    RandomStuffProject,
    ResurrectionRemix,
    ResurrectionRemixGapps,
    ResurrectionRemixU1,
    ResurrectionRemixGappsU1,
    Revenge,
    SalmanProject,
    Sakura,
    ShapeShift,
    StagQ,
    StagR,
    StagRGapps,
    Styx,
    Superior,
    Syberia,
    SyberiaU1,
    TenX,
    Titanium,
    TitaniumGapps,
    WhymemeProject,
    Xtended,
)
