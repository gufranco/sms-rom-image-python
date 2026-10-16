[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

# SMS ROM Image

将 Sega Master System、Game Gear 或 SG-1000 的卡带镜像作为文件读取。Sega 的 Mark III 参考手册有所规定之处以手册为准，手册未涉及之处以出口版启动程序和 2,610 个真实镜像为准。

[![CI](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-rom-image-python)](https://github.com/gufranco/sms-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

从 **5,111** 个归档条目中测量出 **2,610** 个不同镜像，属性失败 **0** 次，其中 **2,408** 个在 `0x7FF0` 读到文件头，**393** 个零售版 Master System 卡带中有 **370** 个复现了存储的校验和，**14** 个启动程序按摘要声明，**685** 个测试，**100%** 语句和分支覆盖率，无依赖

```python
from smsimage import dump, header

image = bytearray(0x8000)
image[0x7FF0:0x7FF8] = b"TMR SEGA"
image[0x7FFF] = 0x4C
image[0x7FFA:0x7FFC] = header.checksum(bytes(image)).to_bytes(2, "little")

stubbed = bytes(512) + bytes(image)
cartridge = dump.strip_copier_stub(stubbed)

print(dump.form(stubbed), len(cartridge))
print(
    hex(header.anchor_of(cartridge)), header.region_of(cartridge), header.declared_size(cartridge)
)
print(header.agrees(cartridge))
```

```
stubbed 32768
0x7ff0 sms-export 32768
True
```

该示例构建一个 32K 镜像，在 `0x7FF0` 放置文件头，写入区域与大小字节 `0x4C`，并把本包计算出的校验和封入两个校验和字节。然后在前面加上一个 512 字节的拷贝机块。`strip_copier_stub` 仅凭长度识别出该块并将其移除。文件头读回为一个声明 32K 的出口版 Master System 卡带，存储的校验和与计算值一致。

## 安装

| 要求 | 版本 |
|:--|:--|
| Python | 3.12 或更高 |
| git | 任意版本，用于克隆 |

```bash
git clone https://github.com/gufranco/sms-rom-image-python.git
cd sms-rom-image-python
python3 smsimage/doctor.py
```

本包只导入标准库。没有子模块，因此普通克隆和下载 zip 链接都能得到可运行的检出。`pip install git+https://github.com/gufranco/sms-rom-image-python.git` 只安装本包，诊断脚本作为 `smsimage-doctor` 命令提供。

诊断脚本检查本机和检出，最后输出一行。提交缺陷报告时请粘贴其完整输出。

```
  9 checks, nothing to report
```

版本遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史发布。每个版本都打了标签，并列在[发布页面](https://github.com/gufranco/sms-rom-image-python/releases)上。

## 接口

四个模块回答四个问题，顺序就是调用方必须提问的顺序。

| 模块 | 问题 |
|:--|:--|
| [`dump`](smsimage/dump.py) | 转储设备添加了什么 |
| [`header`](smsimage/header.py) | 卡带关于自身说了什么，在哪里 |
| [`identity`](smsimage/identity.py) | 是什么使这个文件成为它本身，由哪个值决定 |
| [`manifest`](smsimage/manifest.py) | 读者提供了错误的文件时，是哪一种错误 |

对镜像的每个查询在无可读取时都返回 `None` 而不是抛出异常。缺少文件头是正常状态：2,610 个镜像中有 189 个没有文件头。

### 读取转储

| 调用 | 返回 |
|:--|:--|
| `dump.read(path)` | 文件的字节，有拷贝机块时将其移除。`path` 为 `str` 或 `Path` |
| `dump.form(data)` | 当 `data` 长于 512 字节且其长度在整数千字节之外多出 512 时为 `"stubbed"`，否则为 `"bare"` |
| `dump.strip_copier_stub(data)` | 形式为 `"stubbed"` 时为去掉前 512 字节的 `data`，否则为原样的 `data` |

```python
from smsimage import dump

for length in (512, 1536, 32768, 33280):
    print(length, dump.form(bytes(length)), len(dump.strip_copier_stub(bytes(length))))
```

```
512 bare 512
1536 stubbed 1024
32768 bare 32768
33280 stubbed 32768
```

判断只看长度，别无其他。512 字节的文件是 bare，因为块后面不会剩下任何东西。`dump.read` 已经去掉了该块，所以要知道文件原本是哪种形式，请自行读取字节并传给 `dump.form`。

### 文件头

| 调用 | 返回 |
|:--|:--|
| `header.anchors_in(image)` | 每个含有 `TMR SEGA` 的候选偏移，从大到小，以元组形式 |
| `header.anchor_of(image)` | 其中第一个，或 `None` |
| `header.region_of(image)` | 锚点加 `0x0F` 处字节高半字节对应的名称，无文件头或无名称时为 `None` |
| `header.declared_size(image)` | 该字节低半字节对应的字节大小，无文件头或代码不在已知解读中时为 `None` |
| `header.carried(image)` | 锚点加 `0x0A` 处的小端字，无文件头时为 `None` |
| `header.checksum(image)` | 出口版启动程序计算的和，为小于 `0x10000` 的 `int`，无文件头或大小代码未知时为 `None` |
| `header.agrees(image)` | `checksum(image) == carried(image)`，没有可比较的校验和时为 `None` |

```python
from smsimage import header

image = bytearray(0x8000)
image[0x7FF0:0x7FF8] = b"TMR SEGA"
image[0x7FFA:0x7FFC] = (0x1234).to_bytes(2, "little")

for nibbles in (0x6C, 0x9C, 0x63):
    image[0x7FFF] = nibbles
    held = bytes(image)
    print(
        hex(nibbles),
        header.region_of(held),
        header.declared_size(held),
        hex(header.carried(held)),
        header.checksum(held),
        header.agrees(held),
    )

print(header.region_of(bytes(0x8000)), header.carried(bytes(0x8000)), header.agrees(b""))
```

```
0x6c gg-export 32768 0x1234 0 False
0x9c None 32768 0x1234 0 False
0x63 gg-export None 0x1234 None None
None None None
```

区域半字节 9 没有名称，所以 `region_of` 返回 `None`，而大小仍可读出。大小半字节 3 在表中没有条目，所以没有可求和的范围，也没有可比较的校验和。没有文件头的镜像对每个查询都返回 `None`，空镜像也一样。

### 身份

| 调用 | 返回 |
|:--|:--|
| `identity.measure(data)` | 包含 `size`、`crc32`、`md5`、`sha1` 和 `sha256` 的映射，摘要为小写十六进制 |
| `identity.agrees(found, expected)` | 两个 `sha256` 值是否一致，忽略大小写。任一方没有该值时抛出 `NoAuthority` |

一个值决定文件是不是那个文件。一条记录即使较弱的值不一致，只要这个值一致，仍然匹配：

```python
from smsimage import identity

found = identity.measure(b"cartridge")
record = {"sha256": found["sha256"], "crc32": "00000000", "size": 1}

print(identity.AUTHORITATIVE)
print(identity.agrees(found, record))
```

```
sha256
True
```

不含 SHA-256 的记录会被拒绝，而不是按它碰巧带有的某个较弱值来判定：

```python
from smsimage import NoAuthority, identity

try:
    identity.agrees(identity.measure(b"cartridge"), {"crc32": "e9648752"})
except NoAuthority as error:
    print(error)
```

```
nothing decides: no sha256 to compare
```

### 清单

`Manifest(document)` 接受一个含有 `artifacts` 映射的映射。每个制品有一个记录列表 `accepted`，每条记录带有 `sha256`；制品还可以带有 `name` 和 `badDumps` 列表，其条目带有 `sha256` 和 `why`。`manifest.read(path)` 将 JSON 文件解析为清单。

| 成员 | 含义 |
|:--|:--|
| `Manifest.keys` | 制品键，以元组形式 |
| `Manifest.name(key)` | 制品的 `name`，没有名称或未声明时为 `key` |
| `Manifest.match(key, data)` | 字节 `data` 对照制品 `key` 的 `Match` |
| `Match.key`、`Match.verdict` | 所询问的键，以及下面五种判定之一 |
| `Match.found` | `identity.measure` 对这些字节返回的结果 |
| `Match.why` | 所匹配坏转储的 `why`，否则为 `None` |
| `bool(match)` | 仅在 `accepted` 时为 True |

| 判定 | 条件 |
|:--|:--|
| `accepted` | SHA-256 是该制品接受的值之一 |
| `a known bad dump` | SHA-256 是该制品在 `badDumps` 下列出的值之一 |
| `the right length, the wrong content` | 大小与某条已接受记录一致，而摘要不一致 |
| `a length nothing declares` | 摘要和大小都不一致 |
| `undeclared` | 清单中没有该键下的制品 |

```python
from smsimage import Manifest, identity

boot = bytes(8192)
expected = identity.measure(boot)

record = Manifest({"artifacts": {"bios": {"name": "a boot program", "accepted": [dict(expected)]}}})

print(record.match("bios", boot).verdict)
print(record.match("bios", bytes(8191) + b"\x01").verdict)
print(record.match("bios", bytes(4096)).verdict)
print(record.match("cartridge", boot).verdict)
```

```
accepted
the right length, the wrong content
a length nothing declares
undeclared
```

已知的坏转储与已接受文件分开声明，因此损坏的副本会被诊断为损坏，而不是错误的文件。不是清单的文档在构建时就会被拒绝：

```python
from smsimage import Malformed, Manifest, NoAuthority, identity

good = bytes(8192)
corrupt = bytes(8190) + b"\xff\xff"
record = Manifest(
    {
        "artifacts": {
            "bios": {
                "name": "a boot program",
                "accepted": [dict(identity.measure(good))],
                "badDumps": [{"sha256": identity.measure(corrupt)["sha256"], "why": "last word"}],
            }
        }
    }
)

found = record.match("bios", corrupt)
print(record.keys, record.name("bios"), record.name("cartridge"))
print(found, bool(found), found.why, found.found["size"])
print(bool(record.match("bios", good)))

for document in ([], {"artifacts": {}}, {"artifacts": {"bios": {"accepted": [{"size": 1}]}}}):
    try:
        Manifest(document)
    except (Malformed, NoAuthority) as error:
        print(type(error).__name__, error)
```

```
('bios',) a boot program cartridge
<Match bios: a known bad dump> False last word 8192
True
Malformed a manifest is a mapping, and this is not one
Malformed a manifest declares artifacts, and this declares none
NoAuthority bios: an accepted file with no sha256 to decide on
```

### 错误

两者都定义在 [`smsimage/errors.py`](smsimage/errors.py) 中，并在包的顶层公开，调用方可以按名称分别捕获。

| 错误 | 抛出条件 |
|:--|:--|
| `Malformed` | 传给 `Manifest` 的不是映射、未声明任何制品、有制品不是映射，或有制品的 `accepted` 列表缺失或为空 |
| `NoAuthority` | 传给 `identity.agrees` 的某一方没有 `sha256`，或传给 `Manifest` 的某条已接受记录没有 `sha256` |

`manifest.read` 对无法读取的文件或无效 JSON，直接抛出 `pathlib` 和 `json` 所抛出的异常。

### 模块内容

| 名称 | 内容 |
|:--|:--|
| `smsimage.MAGIC` | `b"TMR SEGA"`，文件头开头的八个字节 |
| `smsimage.CANDIDATES` | `(0x7FF0, 0x3FF0, 0x1FF0)`，搜索的偏移，从大到小 |
| `smsimage.REGIONS` | 区域半字节到名称：`0x3` `sms-japan`，`0x4` `sms-export`，`0x5` `gg-japan`，`0x6` `gg-export`，`0x7` `gg-international` |
| `smsimage.SIZES` | 大小半字节到字节数：`0xA` 8K，`0xB` 16K，`0xC` 32K，`0xD` 48K，`0xE` 64K，`0xF` 128K，`0x0` 256K，`0x1` 512K，`0x2` 1M |
| `smsimage.BARE`、`smsimage.STUBBED` | `dump.form` 返回的两个值 |
| `smsimage.AUTHORITATIVE` | `"sha256"`，唯一起决定作用的值 |
| `smsimage.VERDICTS` | 五种判定，按 `match` 尝试的顺序 |
| `smsimage.Manifest`、`smsimage.Match` | 清单及其答复 |
| `smsimage.Malformed`、`smsimage.NoAuthority` | 两种错误 |
| `smsimage.__version__` | 已安装的版本 |
| `dump.COPIER_BLOCK` | 512 |
| `identity.CROSS_REFERENCE` | `("size", "crc32", "md5", "sha1")`，会被测量但从不起决定作用 |
| `header.CHECKSUM`、`header.REGION_AND_SIZE` | 校验和字以及区域与大小字节相对于锚点的位置：`0x0A` 到 `0x0B`，以及 `0x0F` |
| `header.FIRST_SPAN`、`header.BANKS_FROM_THE_THIRD` | 出口版启动程序的两张表，以大小半字节为键 |

```python
import smsimage

print(smsimage.MAGIC, [hex(one) for one in smsimage.CANDIDATES])
print({hex(code): name for code, name in smsimage.REGIONS.items()})
print({hex(code): size // 1024 for code, size in smsimage.SIZES.items()})
print(smsimage.BARE, smsimage.STUBBED, smsimage.AUTHORITATIVE)
print(smsimage.VERDICTS)
```

```
b'TMR SEGA' ['0x7ff0', '0x3ff0', '0x1ff0']
{'0x3': 'sms-japan', '0x4': 'sms-export', '0x5': 'gg-japan', '0x6': 'gg-export', '0x7': 'gg-international'}
{'0x0': 256, '0x1': 512, '0x2': 1024, '0xa': 8, '0xb': 16, '0xc': 32, '0xd': 48, '0xe': 64, '0xf': 128}
bare stubbed sha256
('accepted', 'a known bad dump', 'the right length, the wrong content', 'a length nothing declares', 'undeclared')
```

### 诊断脚本

`python3 smsimage/doctor.py`，或 pip 安装后的 `smsimage-doctor`，不接受参数。它报告本机情况：解释器、输出编码和默认编码、文件系统大小写、换行符、路径长度、可用空间和 git。然后它用自己组装的镜像驱动本包：去掉拷贝机块，找到预先放置的文件头，复现封入的校验和，测量镜像，解析 [`artifacts.manifest.json`](artifacts.manifest.json)，并读取 [`conformance/corpus.json`](conformance/corpus.json)。语料为空与语料不存在会分开报告。全部 9 项包检查通过时退出码为 0，否则为 1。

## 真实游戏库实际包含什么

Sega 的 *Software Reference Manual for the SEGA Mark III Console* 在第 22 页印有文件头，[`conformance/hardware.json`](conformance/hardware.json) 收录了它陈述的每个事实及其出处原句。这是一份重新录入的副本，录入者未有记录。手册与卡带不一致时以卡带为准，[`conformance/divergences.json`](conformance/divergences.json) 记录了每处不一致及其测量值。下面的每个数字都是在执行普查的 Master System 和 Game Gear 游戏库上测得的，以镜像字节的 SHA-256 为键，因此计数是镜像的数量，而不是文件名的数量。

| 测量项 | 数量 |
|:--|--:|
| 读取的归档条目 | 5,111 |
| 不同镜像 | 2,610 |
| 已出现过的镜像的重复条目 | 2,501 |
| 仅在 `0x7FF0` 有文件头 | 2,406 |
| 在 `0x3FF0` / `0x1FF0` 有文件头 | 8 / 5 |
| 在 `0x3FF0` 和 `0x7FF0` 都有文件头，按 `0x7FF0` 读取 | 2 |
| 任何候选偏移都没有文件头 | 189 |
| 带有 512 字节拷贝机块 | 17 |

其中有五点会让按描述编写的读取器出错。

**文件头并不普遍存在。** 189 个镜像没有文件头，其中只有 18 个短到无法在 `0x7FF0` 容纳文件头。因此每个查询都返回 `None` 而不是抛出异常。

**魔数会出现在没有文件头的地方。** 按原始文件读取时，有 141 个镜像在三个候选偏移之外含有 `TMR SEGA`。其中 16 个是带拷贝机块的镜像，在移除该块之前其文件头位于 `0x81F0`。其余的位于存储体边界，这正是多合一卡带或过量转储的样子。只搜索三个候选位置。

**有两个镜像在两个候选位置都含有魔数。** 最大的偏移胜出，`anchors_in` 报告每个匹配，让调用方看到这种歧义。

```python
from smsimage import header

image = bytearray(0x40000)
image[0x3FF0:0x3FF8] = b"TMR SEGA"
image[0x7FF0:0x7FF8] = b"TMR SEGA"

print([hex(one) for one in header.anchors_in(bytes(image))])
print(hex(header.anchor_of(bytes(image))))
print(header.anchor_of(bytes(0x8000)))
```

```
['0x7ff0', '0x3ff0']
0x7ff0
None
```

**魔数之后的两个字节并非保留字节。** 手册将它们印为两个空格 `20 20`，而 2,421 个文件头中只有 399 个是这样。`00 00` 出现在 1,107 个中，`FF FF` 出现在 525 个中，之后还有一条长尾。出口版和 Game Gear 的启动程序都比较八个字节 `TMR SEGA`，本包也是如此。`python3 -m conformance.divergences <library>` 会测量这些。

**Game Gear 卡带通常不存储校验和。** Game Gear 集合中带有文件头的 1,105 个不同镜像里，有 1,018 个存储的值为零，48 个复现了该规则，这是 `python3 -m conformance.divergences` 单独在该集合上测得的。Game Gear 启动程序在三个地址查找 `TMR SEGA`，别的都不检查，因此该主机上从来没有东西读取过存储的值。`header.agrees` 对这些镜像返回 `False`，这说明的是主机，而不是文件。

手册列出的大小代码最高到 256K，每个都配区域半字节 `0x4`。出口版启动程序解码九种大小代码，其中包括 512K 和 1M，并且只在区域 `0x4` 上检查和。其他区域半字节沿用模拟器社区的命名，没有任何 Sega 文档证实。普查结果与这种命名相符：区域 `0x4` 在 Master System 镜像中占多数，`0x5` 到 `0x7` 在 Game Gear 镜像中占多数。有 49 个镜像带有任何解读都无法解释的区域半字节，3 个带有这样的大小半字节，它们都解析为 `None`，而不是最接近的看似合理的值。

## 校验和规则

该规则就是出口版启动程序运行的规则，读自 [`artifacts.manifest.json`](artifacts.manifest.json) 中声明的 v1.3 程序。每个大小代码指定一个首段范围：`0x1FF0`、`0x3FF0`、`0x7FF0`，48K 则为 `0xBFF0`，对其以下的字节求和。从 64K 起，再加上从第三个起的完整 16K 存储体：64K 为 2 个，128K 为 6 个，256K 为 14 个，512K 为 30 个，1M 为 62 个。保留低十六位。`python3 -m conformance.boot <that program>` 从该程序中读出两张表、八字节比较和区域门限，并与本包核对。手册说只排除两个校验和字节，按这种解读，2,418 个镜像中没有一个能复现存储的值。

| 群体 | 复现数 |
|:--|--:|
| 零售版 Master System 卡带，即 Master System 集合的四个区域文件夹，由 `python3 -m conformance.categories` 测得 | 393 个中 370 个 |
| Master System 集合中带有文件头且大小在已知解读中的每个镜像，包括修改过的 | 1,331 个中 925 个 |
| 带有文件头且大小在已知解读中的每个镜像 | 2,418 个中 971 个 |

修改过的镜像不一致，原因属于修改本身：据 `python3 -m conformance.categories` 测量，翻译版在 301 个中有 78 个复现该规则，改版在 129 个中有 33 个复现。这就是普查把一致性作为观察结果报告、而不以其作为门禁检查的原因。

## 普查，以及其输出为何可以随附发布

[`conformance/census.py`](conformance/census.py) 遍历你拥有的游戏库：目录、zip 归档以及单个 `.sms`、`.gg` 和 `.sg` 文件。

```bash
python3 -m conformance.census /path/to/library.zip /path/to/another
```

它按 SHA-256 对每个不同镜像只计一次，在每个镜像上检查六项属性，报告一项观察结果，并写出 [`conformance/corpus.json`](conformance/corpus.json)：形式、长度、锚点、区域、声明大小以及存储的校验和是否复现的 145 种组合，每种附有计数。不含标题，也不含内容，因此其中没有任何东西能重建任何卡带的任何部分。

| 退出码 | 条件 |
|:--|:--|
| 0 | 每项属性在每个镜像上都成立 |
| 1 | 有属性被打破，或给出的路径不存在 |
| 2 | 未给出路径 |

这六项属性是函数之间的不变式，这些函数目前在构造上就一致。每个测试替换其所守护的那对函数中的一方，并观察属性触发，因此六项属性都已被证实能捕获它们所针对的偏差。

没有给出镜像时，普查会说明它什么也没检查，并保留现有语料，而不是用空语料覆盖它。

## 它是否正确

手册中测试能触及的每个事实都与代码相互核对。[`conformance/hardware.json`](conformance/hardware.json) 记录每个事实及其原句和页码，[`conformance/hardware.test.py`](conformance/hardware.test.py) 将它们与包中的常量进行比较。在 `python3 -m conformance.documents` 获取手册之后，`python3 -m conformance.quotes` 会在手册中找到每个被引用的句子。

`python3 -m conformance.corpus` 在没有游戏库的情况下，用 [`conformance/corpus.json`](conformance/corpus.json) 中的 145 种组合对本包进行回放，测试套件还会对照该文件检查标题中的计数。`python3 -m conformance.speed` 要求 256K 镜像的校验和计算速度不低于每秒 130 次。

读取器可能需要的启动程序在 [`artifacts.manifest.json`](artifacts.manifest.json) 中按大小、CRC32、SHA-1 和 SHA-256 声明。它们都不在本仓库中，这里也没有说明从哪里获取。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出了没有任何 Sega 资料能确定的 2 个问题，以及确定每个问题需要什么。

## 参与开发

| 需要 | 位置 |
|:--|:--|
| 每项门禁检查及其运行顺序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 面向编程智能体的同样内容 | [AGENTS.md](AGENTS.md) |
| 本仓库与同系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md) |
| 缺陷报告 | [GitHub Issues](https://github.com/gufranco/sms-rom-image-python/issues) |
| 安全报告 | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
cov=(uvx --python 3.12 --from coverage==7.6.10 coverage)
"${cov[@]}" erase
for f in $(find smsimage conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

每个模块旁边都有一个以它命名的测试文件，每个都能单独运行。覆盖率是一项硬性门禁检查，要求 100% 语句和分支覆盖率。本 readme 中的每个示例都由 [`conformance/readme.test.py`](conformance/readme.test.py) 运行，其输出与此处印出的内容进行比较。

## 参考资料

- *Software Reference Manual for the SEGA Mark III Console*，Sega，未注明日期，第 22 页，由一位未具名者重新录入。共 45 页，184,840 字节，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。用于文件头布局、开头字符串、校验和字节和大小代码。它不可再分发，不在本仓库中。`python3 -m conformance.documents` 从 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下载它到 `docs/`，并拒绝任何其他文件。本 readme 中的每个地址每周检查一次。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
