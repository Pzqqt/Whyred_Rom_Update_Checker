#!/usr/bin/env python3
# encoding: utf-8

import json
import time
from collections import OrderedDict

from check_init import (
    CHROME_UA, CheckUpdate, SfCheck, SfProjectCheck, H5aiCheck, AexCheck, PeCheck, PlingCheck
)
from database import Saved
from tgbot import send_message as _send_message

class Linux44Y(CheckUpdate):

    fullname = "Linux Kernel stable v4.4.y"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr_obj in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr_obj.find_all("td")[1].get_text()
            if kernel_version.startswith("4.4."):
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

    _base_url = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"

    def __init__(self):
        super().__init__()
        self._private_dic["sp_commits"] = OrderedDict()
        self._private_dic["extra_ids"] = []

    def do_check(self):
        bs_obj = self.get_bs(self.request_url(self._base_url+"/+log"))
        commits = bs_obj.find("ol", {"class": "CommitLog"}).find_all("li")
        for commit in commits:
            a_tag = commit.find_all("a")[1]
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
        saved_info = Saved.get_saved_info(self.name)
        if not saved_info or not saved_info.LATEST_VERSION.startswith("["):
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
        raise NotImplementedError

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
        assert self.__is_checked, "Please execute the 'do_check' method first."
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
                        self._base_url, id_, release_version,
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

class AdrarProject(SfProjectCheck):
    project_name = "unofficial-by-adrar"
    developer = "AdrarHussain"

class AexP(AexCheck):
    fullname = "AospExtended Pie Official"
    sub_path = "whyred/pie"

class AexPGapps(AexCheck):
    fullname = "AospExtended Pie (with Gapps) Official"
    sub_path = "whyred/pie_gapps"

class AexQ(AexCheck):
    fullname = "AospExtended Q Official"
    sub_path = "whyred/q"

class AexQGapps(AexCheck):
    fullname = "AospExtended Q (with Gapps) Official"
    sub_path = "whyred/q_gapps"

class AexRU1(PlingCheck):
    fullname = "AospExtended 11 (Unofficial By SakilMondal)"
    p_id = 1423583
    collection_id = 1600503087

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

class Aospa(CheckUpdate):

    fullname = "Paranoid Android Official"

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

    def is_updated(self):
        result = super().is_updated()
        if not result:
            return False
        if self.info_dic["BUILD_DATE"] is None:
            return False
        saved_info = Saved.get_saved_info(self.name)
        if saved_info is None:
            return True
        return int(self.info_dic["BUILD_DATE"]) > int(saved_info.BUILD_DATE)

class AospaU1(SfCheck):
    fullname = "Aospa Quartz (Unofficial By orges)"
    project_name = "aospa-whyred"

class ArrowQ(CheckUpdate):

    fullname = "Arrow OS Q Official"

    device_name = "whyred"
    device_version = "arrow-10.0"
    build_type_flag = "vanilla"

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
            bs_obj.find(id="%s-filename" % self.build_type_flag)["name"]
        )
        build_info_text = bs_obj.find(id="%s-filename" % self.build_type_flag).parent.get_text()
        self.update_info("FILE_SIZE", self.grep(build_info_text, "Size"))
        self.update_info("BUILD_VERSION", self.grep(build_info_text, "Version"))
        self.update_info("BUILD_DATE", self.grep(build_info_text, "Date"))
        self.update_info(
            "FILE_SHA256",
            bs_obj.find(id="%s-file_sha256" % self.build_type_flag).get_text().strip()
        )
        self.update_info(
            "BUILD_CHANGELOG",
            "# Device side changes\n%s\n# Source changelog\nhttps://arrowos.net/changelog.php"
            % bs_obj.find(id="source-changelog").parent.find("p").get_text().strip()
        )
        self.update_info("DOWNLOAD_LINK", "https://arrowos.net/download/%s" % self.device_name)

class ArrowQGapps(ArrowQ):
    fullname = "Arrow OS Q Official (Include Gapps)"
    build_type_flag = "gapps"

class ArrowR(ArrowQ):
    fullname = "Arrow OS 11 Official"
    device_version = "arrow-11.0"

class ArrowRGapps(ArrowQ):
    fullname = "Arrow OS 11 Official (Include Gapps)"
    device_version = "arrow-11.0"
    build_type_flag = "gapps"

class Atom(SfCheck):
    fullname = "Atom OS Official"
    project_name = "atom-os-project"
    sub_path = "whyred/"

class BabaProject(SfProjectCheck):
    project_name = "babarom"
    developer = "Baba Sahare"

class BlissQ(SfCheck):

    fullname = "Bliss Rom Q Official"
    project_name = "blissroms"
    sub_path = "Q/whyred/"

    def after_check(self):
        self.update_info(
            "BUILD_CHANGELOG",
            self.info_dic["DOWNLOAD_LINK"] \
                .replace(self.sub_path, self.sub_path + "Changelog-").replace(".zip", ".txt")
        )

class Bootleggers(SfCheck):
    fullname = "Bootleggers Rom Official"
    project_name = "bootleggersrom"
    sub_path = "builds/whyred/"

class CandyQ(SfCheck):
    fullname = "Candy Rom Q Official"
    project_name = "candyroms"
    sub_path = "Official/ten/whyred/"

class Carbon(CheckUpdate):

    fullname = "Carbon Rom Official"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("https://get.carbonrom.org/device-whyred.html"))
        latest_build = bs_obj.find("tbody").find("tr").find_all("td")
        self.update_info("BUILD_TYPE", latest_build[1].get_text().strip())
        self.update_info("LATEST_VERSION", latest_build[2].find("dd").get_text().strip())
        self.update_info("DOWNLOAD_LINK", latest_build[2].find("dd").find("a")["href"])
        self.update_info("FILE_MD5", latest_build[2].find_all("dd")[1].get_text().strip())
        self.update_info("FILE_SIZE", latest_build[3].get_text().strip())
        self.update_info("BUILD_DATE", latest_build[4].get_text().strip())

class CarbonU1(SfCheck):
    fullname = "Carbon Rom (Unofficial By fakeyato)"
    project_name = "fakecarbon"
    sub_path = "carbon/"

class Cesium(SfCheck):
    fullname = "Cesium OS Official"
    project_name = "cesiumos"
    sub_path = "whyred/"

class Cherish(SfCheck):

    fullname = "Cherish OS Official"
    project_name = "cherish-os"
    sub_path = "device/whyred/"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class CherishGapps(Cherish):

    fullname = "Cherish OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Colt(SfCheck):
    fullname = "Colt OS Official"
    project_name = "coltos"
    sub_path = "Whyred/"

class Corvus(PlingCheck):

    fullname = "Corvus OS Official"
    p_id = 1375302
    collection_id = 1586848776
    enable_pagecache = True

    def filter_rule(self, string):
        return "GAPPS" not in string.upper()

class CorvusGapps(Corvus):

    fullname = "Corvus OS Official (Include Gapps)"

    def filter_rule(self, string):
        return "GAPPS" in string.upper()

class Cosmic(SfCheck):
    fullname = "Cosmic OS Official"
    project_name = "cosmic-os"
    sub_path = "whyred/"

class CrDroid(SfCheck):
    fullname = "CrDroid Pie Official"
    project_name = "crdroidpie"
    sub_path = "WHYRED/"

class CrDroidQ(SfCheck):
    fullname = "CrDroid Q Official"
    project_name = "crdroid"
    sub_path = "whyred"

class Cygnus(SfCheck):
    fullname = "CygnusOS Official"
    project_name = "cygnus-android"
    sub_path = "whyred/"

class DarkstarProject(SfProjectCheck):
    project_name = "project-dark"
    developer = "Darkstar"
    sub_path = "whyred/"

class EvolutionX(SfCheck):

    fullname = "EvolutionX Official"
    project_name = "evolution-x"
    sub_path = "whyred/"

    def after_check(self):
        self.update_info(
            "BUILD_CHANGELOG",
            self.request_url(
                "https://raw.githubusercontent.com/Evolution-X-Devices/official_devices/"
                "master/changelogs/whyred/%s.txt" % self.info_dic["LATEST_VERSION"]
            ).strip()
        )

class Extended(SfCheck):
    fullname = "ExtendedUI Official"
    project_name = "extendedui"
    sub_path = "whyred/"

class ExtendedU1(PlingCheck):
    fullname = "ExtendedUI (Unofficial By Nesquirt)"
    p_id = 1374700
    collection_id = 1586685069

class GengKapakProject(SfProjectCheck):
    project_name = "gengkapak"
    developer = "GengKapak Project"
    sub_path = "ROM/whyred/"

class HarooonProject(SfProjectCheck):
    project_name = "whyded-releases"
    developer = "Harooon"

class Havoc(SfCheck):

    fullname = "Havoc OS Official"
    project_name = "havoc-os"
    sub_path = "whyred/"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class HavocGapps(Havoc):

    fullname = "Havoc OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class HavocU1(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)(Include Gapps)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/whyred-gapps/"

class HavocU3(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/Havoc-alpha/"

class Ion(SfCheck):
    fullname = "ION Official"
    project_name = "i-o-n"
    sub_path = "device/xiaomi/whyred/"

class Komodo(SfCheck):
    fullname = "Komodo OS Official"
    project_name = "komodos-rom"
    sub_path = "whyred/"

class Legion(SfCheck):

    fullname = "Legion OS Official"
    project_name = "legionrom"
    sub_path = "whyred/"
    enable_pagecache = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class LegionGapps(Legion):

    fullname = "Legion OS Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Lineage(CheckUpdate):

    fullname = "Lineage OS Official"

    def do_check(self):
        bs_obj = self.get_bs(self.request_url("https://download.lineageos.org/whyred"))
        build = bs_obj.find("tbody").find("tr")
        tds = build.find_all("td")
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

class LineageU3(CheckUpdate):

    fullname = "Lineage OS 18.0 (Unofficial By SakilMondal)"

    def do_check(self):
        base_url = "https://downloads.sakilmondal.me/Roms/LineageOS/"
        json_dic = json.loads(self.request_url(
            base_url,
            "post",
            params={"rootId": "14c0B067v_Dey0HLrjBDsppKCOv9U51oT"}
        ))
        if json_dic and json_dic["files"]:
            latest_build = json_dic["files"][-1]
            self.update_info("LATEST_VERSION", latest_build["name"])
            self.update_info("BUILD_DATE", latest_build["modifiedTime"])
            self.update_info("FILE_SIZE", "%0.2f MB" % (int(latest_build["size"]) / 1048576,))
            self.update_info("DOWNLOAD_LINK", base_url+latest_build["name"])

class Neon(SfCheck):
    fullname = "Neon OS Official"
    project_name = "neonrelease"
    sub_path = "whyred/"

class Nitrogen(SfCheck):
    fullname = "Nitrogen OS Official"
    project_name = "nitrogen-project"
    sub_path = "whyred/"

class NitrogenU1(SfCheck):
    fullname = "Nitrogen OS (Unofficial By Bagaskara815)"
    project_name = "nangis"
    sub_path = "NitrogenOS/Whyred/10/"

class Nusantara(PlingCheck):
    fullname = "Nusantara Project Official"
    p_id = 1422405
    collection_id = 1602832891

class Octavi(SfCheck):
    fullname = "Octavi OS Official"
    project_name = "octavi-os"
    sub_path = "Whyred"

class PixelExtended(SfCheck):
    fullname = "Pixel Extended Q Official"
    project_name = "pixelextended"
    sub_path = "Whyred/"

class PeQ(PeCheck):
    fullname = "Pixel Experience Q Official"
    model = "whyred"
    index = 0
    tag_name = "10"
    enable_pagecache = True

class PeQPe(PeQ):
    fullname = "Pixel Experience Q (Plus edition) Official"
    index = 1
    tag_name = "10 (Plus edition)"

class PeU2(PlingCheck):

    fullname = "Pixel Experience Q (Unofficial By SakilMondal)"
    p_id = 1406086
    collection_id = 1595519142

    def filter_rule(self, string):
        return "Plus" not in string

class PePeU2(PeU2):

    fullname = "Pixel Experience Q (Plus edition)(Unofficial By SakilMondal)"

    def filter_rule(self, string):
        return "Plus" in string

class PixelPlusUI(SfCheck):
    fullname = "PixelPlusUI Official"
    project_name = "pixelplusui-project"

class PixysQ(SfCheck):

    fullname = "Pixys OS Q Official"
    project_name = "pixys-os"
    sub_path = "ten/whyred/"
    enable_pagecache = True

    _skip = True

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" not in string.upper()

class PixysQGapps(PixysQ):

    fullname = "Pixys OS Q Official (Include Gapps)"

    def filter_rule(self, string):
        return SfCheck.filter_rule(string) and "GAPPS" in string.upper()

class Posp(SfCheck):
    fullname = "POSP Official"
    project_name = "posp"
    sub_path = "whyred/"

class RaghuVarmaProject(SfProjectCheck):
    project_name = "whyred-rv"
    developer = "Raghu Varma"

class RandomStuffProject(SfProjectCheck):

    project_name = "random-stuff-for-whyred"
    developer = "James"

    def is_updated(self):
        result = super().is_updated()
        if not result:
            return False
        # Ignore test builds
        return "/test/" not in self.info_dic["DOWNLOAD_LINK"]

class Rebellion(SfCheck):
    fullname = "RebellionOS Official"
    project_name = "rebellion-os"
    sub_path = "whyred/"

class ResurrectionRemix(CheckUpdate):

    fullname = "Resurrection Remix OS Q Official"
    enable_pagecache = True

    @staticmethod
    def filter_rule(string):
        return "VANILLA" in string.upper()

    def do_check(self):
        base_url = "https://get.resurrectionremix.com/"
        bs_obj = self.get_bs(self.request_url(base_url, params={"dir": "ten/whyred"}))
        files = bs_obj.find("ul", {"id": "directory-listing"}).find_all("li")[1:]
        files = sorted(
            files,
            key=lambda x:
                time.strptime(x.find_all("span")[2].get_text().strip(), "%Y-%m-%d %H:%M:%S")
        )
        for file in files[::-1]:
            file_info = file.find("a")
            file_name = file_info["data-name"]
            if file_name.endswith(".zip") and self.filter_rule(file_name):
                self.update_info("LATEST_VERSION", file_name)
                self.update_info("DOWNLOAD_LINK", base_url + file_info["href"])
                self.update_info("FILE_SIZE", file_info.find_all("span")[1].get_text().strip())
                self.update_info("BUILD_DATE", file_info.find_all("span")[2].get_text().strip())
                break

    def after_check(self):
        json_str = self.request_url(
            "https://get.resurrectionremix.com/",
            params={"hash": "ten/whyred/%s" % self.info_dic["LATEST_VERSION"]}
        )
        if json_str is not None:
            json_dic = json.loads(json_str)
            if json_dic.get("md5").isalnum():
                self.update_info("FILE_MD5", json_dic.get("md5"))
            if json_dic.get("sha1").isalnum():
                self.update_info("FILE_SHA1", json_dic.get("sha1"))

class ResurrectionRemixGapps(ResurrectionRemix):

    fullname = "Resurrection Remix OS Q Official (Include Gapps)"

    @staticmethod
    def filter_rule(string):
        return "VANILLA" not in string.upper()

class Revenge(CheckUpdate):

    fullname = "Revenge OS Official"

    def do_check(self):
        url = "https://osdn.net/projects/revengeos/storage/whyred/"
        bs_obj = self.get_bs(self.request_url(url))
        builds = bs_obj.find(attrs={"id": "filelist"}).find_all("tr", {"class": "file"})
        builds.sort(key=lambda tr: -int(tr.find(attrs={"class": "date"})["data-num"]))
        for build in builds:
            file_name = build.find("td", {"class": "name"})["data-name"]
            if not SfCheck.filter_rule(file_name):
                continue
            file_size = build.find("td", {"class": "size filesize"}).get_text()
            if float(file_size.split()[0]) < 500:
                continue
            self.update_info("LATEST_VERSION", file_name)
            self.update_info("FILE_SIZE", file_size)
            self.update_info("DOWNLOAD_LINK", url + file_name)
            self.update_info("BUILD_DATE", build.find(attrs={"class": "date"}).get_text())
            break

class Sakura(SfCheck):
    fullname = "Project Sakura ROM Official"
    project_name = "projectsakura"
    sub_path = "whyred/"

class ShapeShift(SfCheck):
    fullname = "ShapeShift OS Official"
    project_name = "shapeshiftos"
    sub_path = "whyred/"

class StagQ(CheckUpdate):

    fullname = "Stag OS Q Official"

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

class Superior(SfCheck):
    fullname = "Superior OS Official"
    project_name = "superioros"
    sub_path = "whyred/"

class Syberia(SfCheck):
    fullname = "Syberia OS Official"
    project_name = "syberiaos"
    sub_path = "whyred/"

class SyberiaU1(SfCheck):
    fullname = "Syberia OS (Unofficial By Orges)"
    project_name = "syberia-whyded"

class Titanium(SfCheck):

    fullname = "Titanium OS Official"
    project_name = "titaniumos"
    sub_path = "whyred/"
    enable_pagecache = True

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
    Linux44Y,
    GoogleClangPrebuilt,
    WireGuard,
    AdrarProject,
    AexP,
    AexPGapps,
    AexQ,
    AexQGapps,
    AexRU1,
    Aicp,
    Ancient,
    AncientGapps,
    Aosip,
    AosipDf,
    AosipDfGapps,
    Aospa,
    AospaU1,
    ArrowQ,
    ArrowQGapps,
    ArrowR,
    ArrowRGapps,
    Atom,
    BabaProject,
    BlissQ,
    Bootleggers,
    CandyQ,
    Carbon,
    CarbonU1,
    Cesium,
    Cherish,
    CherishGapps,
    Colt,
    Corvus,
    CorvusGapps,
    Cosmic,
    CrDroid,
    CrDroidQ,
    Cygnus,
    DarkstarProject,
    EvolutionX,
    Extended,
    ExtendedU1,
    GengKapakProject,
    HarooonProject,
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
    Neon,
    Nitrogen,
    NitrogenU1,
    Nusantara,
    Octavi,
    PixelExtended,
    PeQ,
    PeQPe,
    PeU2,
    PePeU2,
    PixelPlusUI,
    PixysQ,
    PixysQGapps,
    Posp,
    RaghuVarmaProject,
    RandomStuffProject,
    Rebellion,
    ResurrectionRemix,
    ResurrectionRemixGapps,
    Revenge,
    Sakura,
    ShapeShift,
    StagQ,
    Superior,
    Syberia,
    SyberiaU1,
    Titanium,
    TitaniumGapps,
    WhymemeProject,
    Xtended,
)
