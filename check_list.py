#!/usr/bin/env python3
# encoding: utf-8

import json

from check_init import UAS, CheckUpdate, SfCheck, H5aiCheck, AexCheck, PeCheck, PlingCheck, PeCheckPageCache

PE_PAGE_BS_CACHE = PeCheckPageCache()

class Linux44Y(CheckUpdate):

    fullname = "Linux Kernel v4.4.y"

    def do_check(self):
        url = "https://www.kernel.org"
        bs_obj = self.get_bs(self.request_url(url))
        for tr in bs_obj.find("table", {"id": "releases"}).find_all("tr"):
            kernel_version = tr.find_all("td")[1].get_text()
            if kernel_version.startswith("4.4."):
                self.update_info("LATEST_VERSION", kernel_version)
                break
        else:
            raise Exception("Parsing failed!")

class AexP(AexCheck):
    fullname = "AospExtended Pie Official"
    sub_path = "whyred/pie"

class Aicp(CheckUpdate):

    fullname = "AICP Official"

    def do_check(self):
        req_text = self.request_url(
            "https://cors.aicp-rom.com/http://ota.aicp-rom.com/update.php?device=whyred",
            custom_headers={
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

class AosipBeta(H5aiCheck):
    fullname = "AOSiP Official"
    base_url = "https://get.aosip.dev"
    sub_url = "/whyred/"

class AosipDf(SfCheck):
    fullname = "AOSiP DerpFest (By Adi)"
    project_name = "aosipderp-fest4whyred"

class AosipDf2(SfCheck):
    fullname = "AOSiP DerpFest (By xawlw)"
    project_name = "df4whyred"

class AosipDf3(PlingCheck):
    fullname = "AOSiP DerpFest (By srfarias)"
    p_id = 1338683

class Aosmp(SfCheck):
    fullname = "AOSmP Official"
    project_name = "aosmp"
    sub_path = "whyred"

class ArrowP(SfCheck):
    fullname = "Arrow OS Pie Official"
    project_name = "arrow-os"
    sub_path = "arrow-9.x/whyred/"

class ArrowQ(SfCheck):
    fullname = "Arrow OS Q Official"
    project_name = "arrow-os"
    sub_path = "arrow-10.0/whyred/"

class AtomQ(SfCheck):
    fullname = "Atom OS Official"
    project_name = "atom-os-project"
    sub_path = "Ten/whyred/"

class Beast(SfCheck):
    fullname = "BeastRom Pie Official"
    project_name = "beastroms"
    sub_path = "whyred/"

class Bliss(H5aiCheck):
    fullname = "Bliss Rom Official"
    base_url = "https://downloads.blissroms.com"
    sub_url = "/BlissRoms/Pie/whyred/"

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

class Cosp(H5aiCheck):
    fullname = "COSP Official"
    base_url = "https://mirror.codebucket.de"
    sub_url = "/cosp/whyred/"

class Cosmic(SfCheck):
    fullname = "Cosmic OS Official"
    project_name = "cosmic-os"
    sub_path = "whyred/"

class CrDroid(SfCheck):
    fullname = "CrDroid Official"
    project_name = "crdroidpie"
    sub_path = "WHYRED/"

class CrDroidU1(SfCheck):
    fullname = "CrDroid Q (Unofficial By AncientProject)"
    project_name = "ancientproject"
    sub_path = "whyred/rom/crdroid/"

class DotP(SfCheck):
    fullname = "DotOS Pie Official"
    project_name = "dotos-downloads"
    sub_path = "dotp/whyred/"

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

class Ion(SfCheck):
    fullname = "ION Pie Official"
    project_name = "i-o-n"
    sub_path = "device/xiaomi/whyred/"

class Legion(SfCheck):
    fullname = "Legion Official"
    project_name = "legionrom"
    sub_path = "whyred/"

# class LineageU1(SfCheck):
#     fullname = "Lineage OS (Unofficial By srfarias)"
#     project_name = "whyreddev"
#     sub_path = "LineageOS17/"

class LineageU1(PlingCheck):
    fullname = "Lineage OS (Unofficial By srfarias)"
    p_id = 1336266

class Liquid(SfCheck):
    fullname = "Liquid Remix Official"
    project_name = "liquid-remix"
    sub_path = "whyred/"

class Nitrogen(SfCheck):
    fullname = "Nitrogen Official"
    project_name = "nitrogen-project"
    sub_path = "whyred/"

class MiuiChinaStable(CheckUpdate):

    fullname = "MIUI China Stable"

    def do_check(self):
        url = "http://www.miui.com/download-341.html"
        bs_obj = self.get_bs(self.request_url(url, disable_proxy=True))
        build = bs_obj.find("div", {"class": "content current_content"}).find("div", {"class": "block"})
        self.update_info("DOWNLOAD_LINK", build.find("div", {"class": "to_miroute"}).find("a")["href"])
        rom_info = build.find("div", {"class": "supports"}).find("p").get_text() \
                        .replace("\n", "").replace("（", "(").replace("）", ")").split("：")
        self.update_info("FILE_SIZE", rom_info[-1])
        self.update_info("LATEST_VERSION", rom_info[2][:-2])

class MiuiChinaBeta(CheckUpdate):

    fullname = "MIUI China Developer"

    def do_check(self):
        url = "http://www.miui.com/download-341.html"
        bs_obj = self.get_bs(self.request_url(url, disable_proxy=True))
        build = bs_obj.find("div", {"class": "content current_content"}).find_all("div", {"class": "block"})[1]
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

class MiuiPolska(CheckUpdate):

    fullname = "MIUI Polska Developer ROM"

    def do_check(self):
        url = "https://miuipolska.pl/download/"
        bs_obj = self.get_bs(self.request_url(url))
        build = bs_obj.find("div", {"id": "redmi-note-5pro"}).find_next().find("div", {"class": "col-sm-9"})
        dl_link1 = build.find("ul", {"class": "dwnl-b"}).find("li").find("a")["href"]
        dl_link2 = build.find("ul", {"class": "dwnl-b"}).find_all("li")[1].find("a")["href"]
        dl_link3 = build.find_all("ul", {"class": "dwnl-b"})[1].find("li").find("a")["href"]
        rom_info = build.find("div", {"class": "dwnl-m"})
        self.update_info("LATEST_VERSION", rom_info.find("ul").find("li").get_text().split()[-1])
        rom_info_2 = rom_info.find("i").get_text().split(" ")
        self.update_info("FILE_SIZE", rom_info.find("ul").find_all("li")[-1].get_text().split()[-1])
        self.update_info("FILE_MD5", rom_info_2[1])
        self.update_info("BUILD_DATE", rom_info_2[-1])
        self.update_info(
            "DOWNLOAD_LINK",
            "# Main server(sourceforge)\n%s\n"
            "# Spare 1(AFH)\n%s\n"
            "# Spare 2\n%s"
            % (dl_link1, dl_link2, dl_link3)
        )

class Omni(CheckUpdate):

    fullname = "Omni Official"

    def do_check(self):
        url = "http://dl.omnirom.org/whyred/"
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
        else:
            self.update_info("LATEST_VERSION", "Looks like there is no Rom file right now")
            return
        for file in files:
            file_name = file.find("a").get_text()
            if file_name == self.info_dic["LATEST_VERSION"] + ".md5sum":
                self.update_info("FILE_MD5", self.get_hash_from_file(url + file_name))

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
    fullname = "Pixys OS Official"
    project_name = "pixys-os"
    sub_path = "pie/whyred/"

class Posp(SfCheck):
    fullname = "POSP Official"
    project_name = "posp"
    sub_path = "whyred/"

class Revenge(SfCheck):
    fullname = "Revenge OS Official(By srfarias)"
    project_name = "whyreddev"
    sub_path = "RevengeOS/"

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
                try:
                    hash_dic = json.loads(self.request_url(
                        "https://get.resurrectionremix.com/?hash=whyred/" + self.info_dic["LATEST_VERSION"]
                    ))
                except:
                    pass
                else:
                    self.update_info("FILE_MD5", hash_dic["md5"])
                    self.update_info("FILE_SHA1", hash_dic["sha1"])
                break
        else:
            self.update_info("LATEST_VERSION", "Looks like there is no Rom file right now")

class ResurrectionRemixU1(SfCheck):
    fullname = "Resurrection Remix OS(Unofficial By srfarias)"
    project_name = "whyreddev"
    sub_path = "ResurrectionRemixOS/"

class Stag(SfCheck):
    fullname = "Stag OS Official"
    project_name = "stag-os"
    sub_path = "Whyred/"

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

CHECK_LIST = (
    Linux44Y,
    AexP,
    Aicp,
    AosipBeta,
    AosipDf,
    AosipDf2,
    AosipDf3,
    Aosmp,
    ArrowP,
    ArrowQ,
    AtomQ,
    Beast,
    Bliss,
    Bootleggers,
    CandyP,
    CandyQ,
    Cerberus,
    Cosp,
    Cosmic,
    CrDroid,
    CrDroidU1,
    DotP,
    EvolutionX,
    Gzosp,
    Havoc,
    HavocU1,
    HavocU2,
    Ion,
    Legion,
    LineageU1,
    Liquid,
    Nitrogen,
    MiuiChinaStable,
    MiuiChinaBeta,
    MiuiGlobalStable,
    MiuiPolska,
    Omni,
    PeQ,
    PeP,
    PePPe,
    Pixys,
    Posp,
    Revenge,
    ResurrectionRemix,
    ResurrectionRemixU1,
    Stag,
    Superior,
    SuperiorU1,
    Syberia,
    Viper,
    Xtended,
)
