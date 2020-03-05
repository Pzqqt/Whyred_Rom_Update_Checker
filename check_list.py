#!/usr/bin/env python3
# encoding: utf-8

import json

from check_init import UAS, CheckUpdate, SfCheck, SfProjectCheck, H5aiCheck, \
                       AexCheck, PeCheck, PlingCheck, PeCheckPageCache

PE_PAGE_BS_CACHE = PeCheckPageCache()

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
                    "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v%s" % kernel_version
                )
                break
        else:
            raise Exception("Parsing failed!")

    def get_print_text(self):
        return "*Linux Kernel stable %s update*\n\n%s" % (
            "[v%s](%s)" % (self.info_dic["LATEST_VERSION"], self.info_dic["DOWNLOAD_LINK"]),
            "[Commits](%s)" % self.info_dic["BUILD_CHANGELOG"]
        )

class GoogleClangPrebuilt(CheckUpdate):

    fullname = "Google Clang Prebuilt"

    def do_check(self):
        base_url = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"
        bs_obj = self.get_bs(self.request_url(base_url + "/+log"))
        commits = bs_obj.find("ol", {"class": "CommitLog"}).find_all("li")
        for commit in commits:
            a_tag = commit.find_all("a")[1]
            commit_title = a_tag.get_text()
            if commit_title.startswith("Update prebuilt Clang to"):
                commit_url = "https://android.googlesource.com" + a_tag["href"]
                commit_id = a_tag["href"].split("/")[-1]
                r_tag = commit_title.split()[4]
                assert r_tag.startswith("r")
                if r_tag[-1] == ".":
                    r_tag = r_tag[:-1]
                self.update_info("LATEST_VERSION", commit_id)
                self.update_info("BUILD_CHANGELOG", commit_url)
                self.update_info(
                    "DOWNLOAD_LINK",
                    "%s/+archive/%s/clang-%s.tar.gz" % (base_url, commit_id, r_tag)
                )
                break
        else:
            raise Exception("Parsing failed!")

    def after_check(self):
        bs_obj_2 = self.get_bs(self.request_url(self.info_dic["BUILD_CHANGELOG"]))
        commit_text = bs_obj_2.find("pre").get_text().splitlines()[2]
        if commit_text[-1] == ".":
            commit_text = commit_text[:-1]
        self.update_info("BUILD_VERSION", commit_text)

    def get_print_text(self):
        return "*%s Update*\n\n%s\n\nDownload tar.gz:\n%s" % (
            self.fullname,
            "[Commit](%s)" % self.info_dic["BUILD_CHANGELOG"],
            "[%s](%s)" % (
                self.info_dic.get("BUILD_VERSION", self.info_dic["DOWNLOAD_LINK"].split("/")[-1]),
                self.info_dic["DOWNLOAD_LINK"]
            )
        )

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

class Aicp(CheckUpdate):

    fullname = "AICP Official"

    def do_check(self):
        req_text = self.request_url(
            "https://cors.aicp-rom.com/http://ota.aicp-rom.com/update.php?device=whyred",
            headers={
                "Origin": "https://dwnld.aicp-rom.com",
                "Referer": "https://dwnld.aicp-rom.com/",
                "User-Agent": UAS[0]
            }
        )
        json_dic = json.loads(req_text)["updates"][0]
        self.update_info("LATEST_VERSION", json_dic["name"])
        self.update_info("BUILD_VERSION", json_dic["version"].replace("\n", " "))
        self.update_info("FILE_SIZE", json_dic["size"] + " MB")
        self.update_info("DOWNLOAD_LINK", json_dic["url"])
        self.update_info("FILE_MD5", json_dic["md5"])
        self.update_info("BUILD_CHANGELOG", json_dic["url"] + ".html")

class Aosip(H5aiCheck):

    fullname = "AOSiP Official"
    base_url = "https://get.aosip.dev"
    sub_url = "/whyred/"

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

class AosipDf(SfCheck):
    fullname = "AOSiP DerpFest (By Adi)"
    project_name = "aosipderp-fest4whyred"

class AosipDf2(SfCheck):
    fullname = "AOSiP DerpFest (By xawlw)"
    project_name = "df4whyred"

class AosipDf3(PlingCheck):
    fullname = "AOSiP DerpFest (By srfarias)"
    p_id = 1338683
    collection_id = 1574482242

class Aospa(PlingCheck):
    fullname = "Aospa Quartz (Unofficial By orges)"
    p_id = 1349975
    collection_id = 1578163970

class ArrowP(SfCheck):
    fullname = "Arrow OS Pie Official"
    project_name = "arrow-os"
    sub_path = "arrow-9.x/whyred/"

class ArrowQ(SfCheck):
    fullname = "Arrow OS Q Official"
    project_name = "arrow-os"
    sub_path = "arrow-10.0/whyred/"

class Beast(SfCheck):
    fullname = "Beast Rom Pie Official"
    project_name = "beastroms"
    sub_path = "whyred/"

class Bliss(H5aiCheck):
    fullname = "Bliss Rom Pie Official"
    base_url = "https://downloads.blissroms.com"
    sub_url = "/BlissRoms/Pie/whyred/"

class BlissQ(H5aiCheck):
    fullname = "Bliss Rom Q Official"
    base_url = "https://downloads.blissroms.com"
    sub_url = "/BlissRoms/Q/whyred/"

class BlissU1(PlingCheck):
    fullname = "Bliss Rom (Unofficial By srfarias)"
    p_id = 1354155
    collection_id = 1579789983

class Bootleggers(SfCheck):
    fullname = "Bootleggers Rom Official"
    project_name = "bootleggersrom"
    sub_path = "builds/whyred/"

class CandyP(SfCheck):
    fullname = "Candy Rom Pie Official"
    project_name = "candyroms"
    sub_path = "Official/Pie/whyred/"

class CandyQ(SfCheck):
    fullname = "Candy Rom Q Official"
    project_name = "candyroms"
    sub_path = "Official/ten/whyred/"

class Cerberus(SfCheck):
    fullname = "Cerberus OS Official"
    project_name = "cerberusos"
    sub_path = "builds/whyred/"

class Cesium(SfCheck):
    fullname = "Cesium OS Official"
    project_name = "cesiumos"
    sub_path = "whyred/"

class Colt(SfCheck):
    fullname = "Colt OS Official"
    project_name = "coltos"
    sub_path = "Whyred/"

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
    sub_path = "whyred/v6.x/"

class Cygnus(SfCheck):
    fullname = "CygnusOS Official"
    project_name = "cygnus-android"
    sub_path = "whyred/"

class DotP(SfCheck):
    fullname = "DotOS Pie Official"
    project_name = "dotos-downloads"
    sub_path = "dotp/whyred/"

class DuRex(SfCheck):
    fullname = "DU-REX Official"
    project_name = "rafiester"
    sub_path = "whyred/DuRex/"

class EvolutionX(SfCheck):
    fullname = "EvolutionX Official"
    project_name = "evolution-x"
    sub_path = "whyred/"

class Gzosp(SfCheck):
    fullname = "Gzosp Official"
    project_name = "gzosp-whyred"
    sub_path = "gzosp/"

class Havoc(SfCheck):
    fullname = "Havoc OS Official"
    project_name = "havoc-os"
    sub_path = "whyred/"

class HavocU1(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)(Include gapps)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/whyred-gapps/"

class HavocU2(SfCheck):
    fullname = "Havoc OS FAKE (Unofficial By fakeyatogod)"
    project_name = "fakehavoc"

class HavocU3(SfCheck):
    fullname = "Havoc OS (Unofficial By Ikaros)"
    project_name = "ikarosdev"
    sub_path = "HavocOS/Havoc-alpha/"

class Ion(SfCheck):
    fullname = "ION Official"
    project_name = "i-o-n"
    sub_path = "device/xiaomi/whyred/"

class KubilProject(SfProjectCheck):
    project_name = "kubilproject"
    sub_path = "Whyred/"
    developer = "kubil"

class Legion(SfCheck):
    fullname = "Legion OS Official"
    project_name = "legionrom"
    sub_path = "whyred/"

class LineageU1(PlingCheck):
    fullname = "Lineage OS (Unofficial By srfarias)"
    p_id = 1336266
    collection_id = 1573678199

class Liquid(SfCheck):
    fullname = "Liquid Remix Official"
    project_name = "liquid-remix"
    sub_path = "whyred/"

class Lotus(SfCheck):
    fullname = "Lotus OS Official"
    project_name = "lotus-os"
    sub_path = "whyred/"

class MiuiChinaStable(CheckUpdate):

    fullname = "MIUI China Stable"

    def do_check(self):
        url = "http://www.miui.com/download-341.html"
        bs_obj = self.get_bs(self.request_url(url, proxies={}))
        build = bs_obj.find("div", {"class": "content current_content"}) \
                      .find("div", {"class": "block"})
        self.update_info("DOWNLOAD_LINK", build.find("div", {"class": "to_miroute"}).find("a")["href"])
        rom_info = build.find("div", {"class": "supports"}).find("p").get_text() \
                        .replace("\n", "").replace("（", "(").replace("）", ")").split("：")
        self.update_info("FILE_SIZE", rom_info[-1])
        self.update_info("LATEST_VERSION", rom_info[2][:-2])

class MiuiChinaBeta(CheckUpdate):

    fullname = "MIUI China Developer"

    def do_check(self):
        url = "http://www.miui.com/download-341.html"
        bs_obj = self.get_bs(self.request_url(url, proxies={}))
        build = bs_obj.find("div", {"class": "content current_content"}) \
                      .find_all("div", {"class": "block"})[1]
        self.update_info("DOWNLOAD_LINK", build.find("div", {"class": "to_miroute"}).find("a")["href"])
        rom_info = build.find("div", {"class": "supports"}).find("p").get_text() \
                        .replace("\n", "").replace("（", "(").replace("）", ")").split("：")
        self.update_info("FILE_SIZE", rom_info[-1])
        self.update_info("LATEST_VERSION", rom_info[2][:-2])

class MiuiGlobalStable(CheckUpdate):

    fullname = "MIUI Global Stable"

    def do_check(self):
        url = "http://c.mi.com/oc/rom/getdevicelist?phone_id=1700341"
        json_dic = json.loads(self.request_url(url))
        rom_info = json_dic["data"]["device_data"]["device_list"]["Redmi Note 5 Pro India"]["stable_rom"]
        self.update_info("LATEST_VERSION", rom_info["version"])
        self.update_info("FILE_SIZE", rom_info["size"])
        self.update_info("DOWNLOAD_LINK", rom_info["rom_url"])

class MiuiEu(SfCheck):
    fullname = "Xiaomi.eu Multilang Developer ROM"
    project_name = "xiaomi-eu-multilang-miui-roms"
    sub_path = "xiaomi.eu/MIUI-WEEKLY-RELEASES/"

    def filter_rule(self, string):
        return "HMNote5Pro" in string

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

class Omni(CheckUpdate):

    fullname = "Omni Official"

    def do_check(self):
        url = "http://dl.omnirom.org/whyred/"
        self._private_dic = {"url": url}
        bs_obj = self.get_bs(self.request_url(url))
        files = bs_obj.find("div", {"id": "fallback"}).find("table").find_all("tr")[2:]
        files.sort(key=lambda x: x.find_all("td")[2].get_text(), reverse=True)
        for file in files:
            file_name = file.find("a").get_text()
            if file_name.endswith(".zip"):
                self.update_info("LATEST_VERSION", file_name)
                self.update_info("DOWNLOAD_LINK", url + file_name)
                self.update_info("BUILD_DATE", file.find_all("td")[2].get_text())
                self.update_info("FILE_SIZE", file.find_all("td")[3].get_text())
                break

    def after_check(self):
        self.update_info(
            "FILE_MD5",
            self.get_hash_from_file(
                self._private_dic["url"] + self.info_dic["LATEST_VERSION"] + ".md5sum"
            )
        )

class PeQ(PeCheck):
    fullname = "Pixel Experience Q Official"
    page_cache = PE_PAGE_BS_CACHE
    index = 0

class PeP(PeCheck):
    fullname = "Pixel Experience Pie Official"
    page_cache = PE_PAGE_BS_CACHE
    index = 1

class PePPe(PeCheck):
    fullname = "Pixel Experience Pie (Plus edition) Official"
    page_cache = PE_PAGE_BS_CACHE
    index = 2

class Pixys(SfCheck):
    fullname = "Pixys OS Pie Official"
    project_name = "pixys-os"
    sub_path = "pie/whyred/"

class PixysQ(SfCheck):

    fullname = "Pixys OS Q Official"
    project_name = "pixys-os"
    sub_path = "ten/whyred/"

    def filter_rule(self, string):
        return string.endswith(".zip") and "GAPP" not in string.upper()

class Posp(SfCheck):
    fullname = "POSP Official"
    project_name = "posp"
    sub_path = "whyred/"

class RaghuVarmaProject(SfProjectCheck):
    project_name = "whyred-rv"
    developer = "Raghu Varma"

class RandomRomsProject(SfProjectCheck):
    project_name = "randomroms"
    developer = "Sreekanth"

class Rebellion(SfCheck):
    fullname = "RebellionOS Official"
    project_name = "rebellion-os"
    sub_path = "whyred/"

class ResurrectionRemix(CheckUpdate):

    fullname = "Resurrection Remix OS Pie Official"

    def do_check(self):
        url = "https://get.resurrectionremix.com/?dir=whyred"
        bs_obj = self.get_bs(self.request_url(url))
        files = bs_obj.find("ul", {"id": "directory-listing"}).find_all("li")[3:-1]
        for file in files[::-1]:
            file_info = file.find("a")
            file_name = file_info["data-name"]
            if file_name.endswith(".zip"):
                self.update_info("LATEST_VERSION", file_name)
                self.update_info("DOWNLOAD_LINK", url + file_info["href"])
                self.update_info("FILE_SIZE", file_info.find_all("span")[1].get_text().strip())
                self.update_info("BUILD_DATE", file_info.find_all("span")[2].get_text().strip())
                break

    def after_check(self):
        json_str = self.request_url(
            "https://get.resurrectionremix.com/?hash=whyred/%s" % self.info_dic["LATEST_VERSION"]
        )
        if json_str is not None:
            json_dic = json.loads(json_str)
            self.update_info("FILE_MD5", json_dic.get("md5"))
            self.update_info("FILE_SHA1", json_dic.get("sha1"))

class Revenge(PlingCheck):
    fullname = "Revenge OS Official"
    p_id = 1358218
    collection_id = 1581174106

class Revolution(SfCheck):
    fullname = "Revolution OS"
    project_name = "revos"

    def filter_rule(self, string):
        return "RedmiNote5" in string

class SreekFreaksProject(SfProjectCheck):
    project_name = "sreekfreaks-unofficial-builds"
    developer = "SreekFreaks"

class SrfariasProject(SfProjectCheck):
    project_name = "whyreddev"
    developer = "srfarias"

class Stag(SfCheck):
    fullname = "Stag OS Pie Official"
    project_name = "stag-os"
    sub_path = "Whyred/"

class StagQ(SfCheck):

    fullname = "Stag OS Q Official"
    project_name = "stagos-10"
    sub_path = "whyred/"

    def do_check(self):
        super().do_check()
        self.update_info(
            "DOWNLOAD_LINK",
            [
                ("SourceForge", self.info_dic["DOWNLOAD_LINK"]),
                (
                    "Mirror",
                    "https://downloads.stag.workers.dev/whyred/%s"
                    % self.info_dic["LATEST_VERSION"]
                )
            ]
        )

class Superior(SfCheck):
    fullname = "Superior OS Official"
    project_name = "superioros"
    sub_path = "whyred/"

class SuperiorU1(SfCheck):
    fullname = "Superior OS (Unofficial By darkstar085)"
    project_name = "project-dark"
    sub_path = "whyred/superior/"

class Syberia(SfCheck):
    fullname = "Syberia OS Official"
    project_name = "syberiaos"
    sub_path = "whyred/"

class Viper(SfCheck):
    fullname = "Viper OS Official"
    project_name = "viper-project"
    sub_path = "whyred/"

class Xtended(SfCheck):
    fullname = "Xtended Official"
    project_name = "xtended"
    sub_path = "whyred/"

class XyzuanProject(SfProjectCheck):
    project_name = "xyzuan"
    developer = "xyzuan"

CHECK_LIST = (
    Linux44Y,
    GoogleClangPrebuilt,
    AexP,
    AexPGapps,
    AexQ,
    AexQGapps,
    Aicp,
    Aosip,
    AosipDf,
    AosipDf2,
    AosipDf3,
    Aospa,
    ArrowP,
    ArrowQ,
    Beast,
    Bliss,
    BlissQ,
    BlissU1,
    Bootleggers,
    CandyP,
    CandyQ,
    Cerberus,
    Cesium,
    Colt,
    Cosmic,
    CrDroid,
    CrDroidQ,
    Cygnus,
    DotP,
    DuRex,
    EvolutionX,
    Gzosp,
    Havoc,
    HavocU1,
    HavocU2,
    HavocU3,
    Ion,
    KubilProject,
    Legion,
    LineageU1,
    Liquid,
    Lotus,
    MiuiChinaStable,
    MiuiChinaBeta,
    MiuiGlobalStable,
    MiuiEu,
    Neon,
    Nitrogen,
    NitrogenU1,
    Omni,
    PeQ,
    PeP,
    PePPe,
    Pixys,
    PixysQ,
    Posp,
    RaghuVarmaProject,
    RandomRomsProject,
    Rebellion,
    ResurrectionRemix,
    Revenge,
    Revolution,
    SreekFreaksProject,
    SrfariasProject,
    Stag,
    StagQ,
    Superior,
    SuperiorU1,
    Syberia,
    Viper,
    Xtended,
    XyzuanProject,
)
