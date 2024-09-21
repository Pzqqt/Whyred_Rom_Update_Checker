# 前言

## 为什么会有这个工具？

这个问题要追溯到2018年。

那一年，我还在使用红米Note 3全网通（kenzo），那个时候是rom、内核、各种玩机资源花样百出的时代。

在那个时代，各个rom项目还没有开始在Telegram做自己的官方更新推送频道，现在已司空见惯的各种“XXX UPDATE”频道还没有蔚然成风，还有数都数不清的非官方rom开发者，基本上无时不刻都可能会有新的rom。

于是，我和 [@wloot](https://github.com/wloot) 共同维护了一个推送有关kenzo的rom和内核更新以及各种玩机资源的Telegram频道。

那么，从哪里搜集信息呢？wloot的做法是加入开发者们的讨论群组和频道，积极地与开发者们交流，拿到第一手消息。

那时的我还在上大学，我并不想花太多时间在这些事情上面，于是我就发挥自己的技能优势，用Python编写了一个名为 `Kenzo_Rom_Update_Checker` 的工具，专注于追踪这些rom的更新。

这个工具的原理也是非常的简单，就是个简单的爬虫，但不同于传统观念上的爬虫，这个工具更像是定时任务。每隔几个小时，就去请求romer发布rom的网站（那时常见的有 [SourceForge](https://sourceforge.net) 和 [AndroidFileHost](https://www.androidfilehost.com)）或者各种rom项目的官网，看看有没有rom更新，如果有就提醒我。

> 那时我刚入门Python不久，写的代码不堪入目，现在已经被我当作黑历史封存了。。。

说实话，这个工具帮了我很大的忙，我不用再一个个点开网站自己去看rom有没有更新，而是完全交给程序来做，我可以比其他人更快得知rom更新。有了这一优势，再加上我们两人的努力，我和wloot维护的kenzo更新频道吸引了大量的订阅者。

之后，在同一年，我把自己的kenzo换成了红米Note 5（whyred），wloot也由于个人原因慢慢淡出玩机圈，于是我开始自立门户，自己创建了一个频道用来推送whyred的各种rom和玩机资源的更新。

而此时我的Python编程技术也有了一定的提升，代码风格也开始趋于标准，是时候重写之前那个腐朽落后的工具并拥抱开源了。于是，这个名为 `Whyred_Rom_Update_Checker` 的工具就诞生了。

我把这个工具部署到了用学生证购买的超廉价的疼讯云服务器上面，每隔3个小时把检查清单中的所有项目检查一遍，有更新的话就调用Telegram官方的api发送更新消息到我的频道。得益于我编程技术的提升，这个工具慢慢地有了一点框架的影子，而且非常地稳定，以至于很长一段时间该项目的新提交都只是更新检查清单。

## 未来？

如今，Android玩机的黄金年代已经逝去，曾经那些百花齐放的自定义rom项目，现在依然活跃的屈指可数。这些存活下来的rom项目也开始各自做官方的更新推送频道。而且，whyred也并没有陪伴我很长时间，在2020年6月份我就把whyred换成了Redmi K30 4G（phoenix），2023年6月份又换成了Redmi Note 12 Turbo（marble）。再加上生活和工作上的压力，我没有精力再去维护这些。

因此，现在这个工具不再关注于那些自定义rom的更新，而是关注于其他一些七七八八的更新，比如：Linux上游的更新、某些我常用软件的更新、一些与树莓派有关的更新，等等。

# 使用指南

## 1. 配置

编辑 `config.py` 文件，根据注释以及自己的需要配置各项内容。

## 2. 运行

```shell
$ python3 ./main.py --help
usage: main.py [-h] [--force] [--dontpost] [-a] [-c CHECK] [-s] [-j]

optional arguments:
  -h, --help            show this help message and exit
  --force               Force to think it/they have updates
  --dontpost            Do not send message to Telegram
  -a, --auto            Automatically loop check all items
  -c CHECK, --check CHECK
                        Check one item
  -s, --show            Show saved data
  -j, --json            Show saved data as json
```

各项参数：

- `-h` 或 `--help`：打印帮助信息并退出。
- `-a` 或 `--auto`：开始循环检查 `check_list.CHECK_LIST` 中的所有项目。
- `-c NAME` 或 `--check NAME`：从 `check_list.CHECK_LIST` 中找到名为 `NAME` 的项目并进行检查，顺利完成检查则退出状态码为0（不论检查的项目有没有更新），否则为非0。
- `-s` 或 `--show`：以表格的格式在终端打印数据库中所有已保存的数据（只打印 `ID` `FULL_NAME` `LATEST_VERSION` 这几个字段），如果已经安装了 [rich](https://pypi.org/project/rich/) 库则优先使用rich。
- `-j` 或 `--json`：将数据库中所有已保存的数据序列化为json并输出。
- `--force`：存在此参数时，则强制判定被检查的项目有更新。
- `--dontpost`：存在此参数时，则强制跳过发送更新消息的步骤。

> 注意：如果你是首次运行循环检查，由于数据库中并没有保存任何数据，因此所有项目都会被判定为有更新的。所以为了避免不必要的麻烦，首次运行循环检查时请务必加上 `--dontpost` 参数。

# 开发者指南

> 注意：阅读以下内容之前，请确保你：
> 1. Python基本功扎实。
> 2. 了解Python爬虫原理，能够熟练使用requests、BeautifulSoup4、lxml等常用的网络数据采集库。
> 3. 了解有关数据库的基本知识。

## 1. 项目结构

- `config.py`：保存了各项用户配置。
- `common.py`：一些通用的函数和功能。
- `check_init.py`：
  - `CheckUpdate`：检查清单中所有项目的共同父类，所有检查项目都必须从此类继承并实现所有抽象方法。
  - `CheckUpdateWithBuildDate`：继承自 `CheckUpdate`，检查更新时同时检查 `BUILD_DATE` 字段，之后会详细介绍。
  - `CheckMultiUpdate`：继承自 `CheckUpdate`，适用于需要一次发送多个消息的情况，之后会详细介绍。
  - `SfCheck`：继承自 `CheckUpdate`，便于检查 [SourceForge](https://sourceforge.net) 中项目的更新，之后会详细介绍。
  - `PlingCheck`：继承自 `CheckUpdate`，便于检查 [Pling](https://www.pling.com) 中项目的更新，之后会详细介绍。
  - `GithubReleases`：继承自 `CheckUpdate`，便于检查 [Github](https://github.com/) 中项目的Releases更新，之后会详细介绍。
- `check_list.py`：在这里编写所有的检查项目，并将其添加到 `CHECK_LIST`。
- `database.py`：数据库以及ORM（将数据库中的数据映射为Python对象）的实现。
- `logger.py`：日志功能的实现。
- `main.py`：运行此项目的入口。
- `tgbot.py`：通过Telegram BOT发送消息的功能的实现。

## 2. CheckUpdate

`CheckUpdate` 定义于 `check_init.py`，是检查清单（`check_list.CHECK_LIST`）中所有项目的共同父类。

`CheckUpdate` 为开发者编写的所有检查项目提供了一个框架，~~避免开发者太过“放飞自我”~~，开发者只需从此类继承并重新实现一些抽象方法就可以完成一个检查项目的编写，还可以根据需要覆写 `CheckUpdate` 中已定义的方法来改变一些默认行为，同时还提供了一些实用函数。

开发者编写的继承自 `CheckUpdate` 的类，类的名字将会写入数据库的 `ID` 字段。

### 1. 类属性

- `fullname`：字符串类型，简单地描述你编写的这个检查项目，将会写入数据库的 `FULL_NAME` 字段。子类必须定义此属性。
- `enable_pagecache`：布尔类型，为True时则允许 `request_url_text` 方法使用页面缓存，默认为False。
- `tags`：字符串元组类型，为你编写的这个检查项目打上各种标签，在默认行为中这些标签会展现在更新消息的文本中，默认为空元组。开发者也可以根据需要将其改写为实例属性。
- `_skip`：布尔类型，为True时将在循环检查时跳过该项目，默认为False。

### 2. 实例属性

- `name`：字符串类型，只读，返回类的名字。
- `info_dic`：字典类型，只读，保存了爬取到并需要写入数据库的信息。键为数据库中除 `ID` 和 `FULL_NAME` 之外的其他字段，并且不允许增加或删除键，实例创建后，这些键对应的默认值均为None，开发者需要在 `do_check` 和 `after_check` 方法中调用 `update_info` 方法以将爬取到的数据写入其中。
- `prev_saved_info`：None 或 `database.Saved` 类型，只读，返回该项目在数据库中已保存的信息，如果数据库中没有找到该项目已保存的信息则为None。
- `_private_dic`：字典类型，没有特殊作用，只是便于开发者编写代码时在不同的方法间传递数据。

### 3. 类方法

- `request_url_text`：使用requests库请求url并返回解码后的响应text。timeout参数的默认值为 `config.TIMEOUT`，proxies参数的默认值为 `config.PROXIES`（当proxies参数为空时则强制禁用代理，无视系统环境变量的配置）。该方法支持使用页面缓存。
- `get_hash_from_file`：使用requests库下载哈希校验文件，读取并返回文件中的哈希值。

### 4. 静态方法

- `get_bs`：对BeautifulSoup函数进行了简单的包装，解析html并返回一个BeautifulSoup对象，默认解析器为lxml。
- `get_human_readable_file_size`：返回人类可读的文件大小。

### 5. 实例方法

#### update_info

调用此方法以更新 `info_dic` 字典。

第一个参数为要更新的字段名，与数据库中的字段对应。

第二个参数为要更新的值，由于数据库中所有的字段均为字符串类型，因此该参数只接受字符串、列表、字典或None类型，其他数据类型将强制转换为字符串并打印警告。

> 对于列表或字典类型，将使用json库序列化为字符串；None则对应数据库中的null。

#### do_check（抽象方法）

进行更新检查，包括页面请求、数据清洗、更新 `info_dic` 字典，都应该在此方法中完成。子类必须重新实现该方法。

一个标准的流程为：

1. 使用 `request_url_text` 方法请求网页页面源码或api。
2. 如果请求的是网页，则使用 `get_bs` 方法进行解析；如果请求的是api，则使用json库进行解析。
3. 对解析到的数据进行清洗，并调用 `update_info` 方法将数据更新到 `info_dic` 字典，主要是更新 `LATEST_VERSION` 字段。

什么？你说你要请求的网页采集数据很困难于是你想用selenium？当然可以，尽情发挥！

#### is_updated

> 注意：此方法只有在调用 `do_check` 方法之后才允许调用。

将 `info_dic` 字典与 `prev_saved_info` 进行比较。如果认定为有更新，则返回True，否则返回False。

`CheckUpdate` 的默认行为只比对 `LATEST_VERSION` 字段，子类可以根据需要拓展此方法。

> 注意：此方法只实际调用一次，若重复调用则立即返回首次调用返回的结果。

#### after_check

> 注意：此方法只有在调用 `do_check` 方法之后才允许调用。

在 `do_check` 之后进行一些额外的操作。

根据 `main.py` 的行为，此方法只会在 `is_updated` 方法返回True之后才执行。

> 比如：将下载哈希文件并获取哈希值的代码放在这里，可以节省一些时间（假设该项目没有检查到更新，那就没必要做这些）。

`after_check` 方法默认不做任何事情，子类可以根据需要重写此方法。

#### write_to_database

> 注意：此方法只有在调用 `do_check` 方法之后才允许调用。

将 `info_dic` 字典中的数据写入数据库。

根据 `main.py` 的行为，此方法只会在 `is_updated` 方法返回True之后才执行，如果为 `main.py` 传递了 `--force` 参数，则同样也会执行。

> 注意：为保持一致性，子类不允许重写此方法。

#### get_print_text

> 注意：此方法只有在调用 `do_check` 方法之后才允许调用。

返回更新消息的文本。

`CheckUpdate` 有一套默认的文本格式，符合Telegram的Markdown格式规范，子类可以根据需要重写此方法。

#### send_message

> 注意：此方法只有在调用 `do_check` 方法之后才允许调用。

发送更新消息。

`CheckUpdate` 默认行为为：调用 `tgbot.send_message` 方法，将 `get_print_text` 方法返回的文本发送到 `config.TG_SENDTO`。

当然，子类可以根据需要重写此方法，比如：不一定非得发送Telegram消息，发邮件也行，使用其他的软件接口发送消息到其他平台也行，什么也不做也行。

#### get_tags_text

根据 `tags` 属性返回tags文本, 生成类似 `#foo #bar` 的格式，以空格作为分隔符。

### 6. 总结

综上所述，对于开发者来说，编写一个检查项目并不困难，都将按照以下流程：

1. 编写一个类，从 `CheckUpdate` 继承，并给你的检查项目起一个独一无二的类名。
2. 定义 `fullname` 属性，简单地描述你编写的这个检查项目。
3. 编写 `do_check` 方法，在这个方法内完成页面请求、数据清洗、更新 `info_dic` 字典等操作。
4. 如果你要修改更新消息文本的格式，则重写 `get_print_text` 方法。
5. 把你编写好的类添加到 `check_list.CHECK_LIST`。

以下是一个简单的例子，这个检查项目将会请求 [The Linux Kernel Archives](https://www.kernel.org/)，并获取5.10内核的最新版本：

```python
import re

from check_init import CheckUpdate


class Linux510Y(CheckUpdate):
    fullname = "Linux Kernel stable v5.10.y"
    tags = ("Linux", "Kernel")

    def do_check(self):
        bs_obj = self.get_bs(self.request_url_text("https://www.kernel.org"))
        for tr_obj in bs_obj.select_one("#releases").select("tr"):
            kernel_version = tr_obj.select("td")[1].get_text()
            if re.match(r'5\.10\.\d+', kernel_version):
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
                return

    def get_print_text(self):
        return "\n".join([
            "*Linux Kernel stable* [v%s](%s) *update*" % (
                self.info_dic["LATEST_VERSION"], self.info_dic["DOWNLOAD_LINK"],
            ),
            self.get_tags_text(),
            "",
            "[Commits](%s)" % self.info_dic["BUILD_CHANGELOG"],
        ])
```

如何测试呢？

```shell
$ python3 ./main.py -c Linux510Y
> Linux Kernel stable v5.10.y has update: 5.10.197
$ python3 ./main.py -c Linux510Y
- Linux Kernel stable v5.10.y no update
```

## 3. CheckUpdateWithBuildDate

`CheckUpdateWithBuildDate` 继承自 `CheckUpdate`，并且重写了 `is_updated` 方法，在检查 `LATEST_VERSION` 字段的同时额外检查 `BUILD_DATE` 字段。如果 `BUILD_DATE` 比数据库中已存储数据的 `BUILD_DATE` 要早的话则认为没有更新。

为什么要这样设计呢？主要是为了应对开发者偶尔撤包的情况，避免了本工具把旧版本当做新版本发了条“更新消息”的窘状。

由于 `CheckUpdate.info_dic` 的 `LATEST_VERSION` 字段和数据库的 `LATEST_VERSION` 字段均为字符串，因此从此类继承时，必须重写 `date_transform` 方法。

`date_transform` 方法的作用是把 `LATEST_VERSION` 字段的值转为一个可以用来比较大小的类型。比如：

```python
import time

from check_init import CheckUpdateWithBuildDate


class SfCheck(CheckUpdateWithBuildDate):
    ...

    _MONTH_TO_NUMBER: Final = {
        "Jan": "01", "Feb": "02", "Mar": "03",
        "Apr": "04", "May": "05", "Jun": "06",
        "Jul": "07", "Aug": "08", "Sep": "09",
        "Oct": "10", "Nov": "11", "Dec": "12",
    }

    @classmethod
    def date_transform(cls, date_str: str) -> time.struct_time:
        # 例: "Wed, 12 Feb 2020 12:34:56 UT"
        date_str_ = date_str.rsplit(" ", 1)[0].split(", ")[1]
        date_str_month = date_str_.split()[1]
        date_str_ = date_str_.replace(date_str_month, cls._MONTH_TO_NUMBER[date_str_month])
        return time.strptime(date_str_, "%d %m %Y %H:%M:%S")
```

当然，如果 `LATEST_VERSION` 字段的值格式非常简单的话，你想直接比较字符串也是可以的：

```python
from check_init import CheckUpdateWithBuildDate


class Foo(CheckUpdateWithBuildDate):
    ...

    @classmethod
    def date_transform(cls, date_str):
        # 例: "2020-04-16.bin"
        return date_str
```

## 4. CheckMultiUpdate

假设有这么一种情况：你经常关注某个人的个人博客，于是你希望本工具能够帮助你定期检查该博客有没有新的文章。

但是博主有可能在你的工具休息的时候发了好多篇新文章，此时 `CheckUpdate` 只能保存一个数据且只能发送一条消息的弊端就暴露出来了。

你可能会想到解决方法：在 `do_check` 阶段把博客第一页的所有文章的信息保存为列表或字典，并保存到 `LATEST_VERSION` 字段，然后重写 `send_message` 方法，把新的文章各自作为一条更新消息发送：

```python
from check_init import CheckUpdate
from tgbot import send_message as _send_message


class Bar(CheckUpdate):
    ...

    def do_check(self):
        ...
        articles_info = {}
        for article in articles:
            articles_info[article["id"]] = {
                "title": article["title"],
                "url": ...,
                "summary": ...,
                "date": ...,
            }
        self.update_info("LATEST_VERSION", articles_info)

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
        for key in fetch_items.keys() - saved_items.keys():
            item = fetch_items[key]
            _send_message(
                "\n".join([
                    "[%s](%s)" % (item["title"], item["url"]),
                    item["date"],
                    "",
                    item["summary"] + " ...",
                ])
            )
            # 休息两秒
            time.sleep(2)
```

`CheckMultiUpdate` 正是这样处理的。

`CheckMultiUpdate` 统一把 `LATEST_VERSION` 字段作为字典处理，为其他类似的检查项目提供了一个框架。

由于 `send_message` 方法被重写，因此 `get_print_text` 方法作废，不再使用。

从此类继承时，必须重写 `send_message_single` 方法，`send_message_single` 方法定义了发送 `LATEST_VERSION` 中其中一条消息的行为。

若在继承时同时实现了 `messages_sort_func` 方法，则每一条更新消息会按该方法进行排序。

> 注意：`is_updated` 方法仍然把 `LATEST_VERSION` 字段当作字符串处理，并且在 `send_message` 方法中将 `info_dic` 的 `LATEST_VERSION` 字段与数据库中的 `LATEST_VERSION` 比较时也只关注字典的键。因此会出现 `is_updated` 方法返回True且 `send_message` 方法也正常调用但没有发送任何消息的情况，这是正常的。

## 5. SfCheck

很多自定义rom和个人开发者都喜欢把刷机包放到 [SourceForge](https://sourceforge.net)，因此本工具提供了 `SfCheck` 类。

`SfCheck` 在请求时请求的是RSS而不是网页，因此不会为SourceForge带来太大的压力。

从此类继承时，绝大多数情况下不需要重写任何方法，只需要定义几个类属性即可：

- `project_name`：字符串类型，项目名，必须定义。
- `sub_path`：字符串类型，子目录路径，默认为空字符串（根路径）。
- `minimum_file_size_mb`：整型，过滤小于 `minimum_file_size_mb` MB的文件，默认为500。

举个例子，我要跟踪marble的EvolutionX官方版Rom更新，链接为 [https://sourceforge.net/projects/evolution-x/files/marble/13/](https://sourceforge.net/projects/evolution-x/files/marble/13/)。

那么，只需这样编写：

```python
from check_init import SfCheck


class EvolutionX(SfCheck):
    fullname = "EvolutionX Rom Official | Android 13"
    project_name = "evolution-x"
    sub_path = "marble/13"
```

非常简单！

如果你要根据文件名过滤，可以重写 `filter_rule` 方法。

## 6. PlingCheck

和 `SfCheck` 类似，`PlingCheck` 方便开发者跟踪 [Pling](https://www.pling.com) 中项目的更新。

`PlingCheck` 在请求时请求的是api而不是网页，因此不会为Pling带来太大的压力。

从此类继承时，必须定义 `p_id` 类属性。

> 比如：你要跟踪更新的项目页面为 [https://www.pling.com/p/1932768](https://www.pling.com/p/1932768)，则 `p_id` 为 `1932768`。

如果你要根据文件名过滤，可以重写 `filter_rule` 方法。

## 7. GithubReleases

和 `SfCheck` 类似，`GithubReleases` 方便开发者跟踪 [Github](https://github.com/) 中项目的Releases更新。

`GithubReleases` 在请求时请求的是api而不是网页，因此不会为Github带来太大的压力。

从此类继承时，必须定义 `repository_url` 类属性。

> 比如：你要跟踪更新的项目页面为 [https://github.com/topjohnwu/Magisk](https://github.com/topjohnwu/Magisk)，则 `repository_url` 为 `"topjohnwu/Magisk"`。

`GithubReleases` 在检查时会跳过具有 `Pre-release` 标签的Release，如果你不想错过，请将类属性 `ignore_prerelease` 设置为False。

> 注意：对于未经认证的api请求，GitHub将配额设置为每个ip每小时最多请求60次。因此，请根据情况合理配置 `check_list.CHECK_LIST` 以及 `config.LOOP_CHECK_INTERVAL`，或者使用代理池等其他方法规避此问题。

## 8. PageCache

在前面介绍 `CheckUpdate` 的部分提到了几次“页面缓存”，那么在这里就介绍一下。

`PageCache` 的作用很简单：循环检查时，在每一轮检查中，对于 `enable_pagecache` 属性为True的项目，确保同一个url只请求一次，不必重复请求。

> 每一轮检查结束后，页面缓存都会被清空。

开发者无需关心 `PageCache` 内部实现的细节（实际上非常简单），只需要给检查项目设置 `enable_pagecache` 类属性为True即可。

多说无用，直接举例：还是前面提到的检查Linux内核更新的例子，如果我不仅需要追踪5.10内核的更新，还要同时追踪5.15内核的更新，为了避免重复请求同一页面（[https://www.kernel.org/](https://www.kernel.org/)），可以这样编写：

```python
import re

from check_init import CheckUpdate


class Linux510Y(CheckUpdate):
    fullname = "Linux Kernel stable v5.10.y"
    tags = ("Linux", "Kernel")
    enable_pagecache = True  # 允许使用页面缓存
    re_pattern = r'5\.10\.\d+'

    def do_check(self):
        bs_obj = self.get_bs(self.request_url_text("https://www.kernel.org"))
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
                return

    def get_print_text(self):
        ...

class Linux515Y(Linux510Y):  # `Linux515Y` 继承自 `Linux510Y`, 因此类属性`enable_pagecache` 默认仍然为True.
    fullname = "Linux Kernel stable v5.10.y"
    re_pattern = r'5\.15\.\d+'
```