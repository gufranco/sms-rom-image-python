# SMS ROM Image

把 Sega Master System、Game Gear 或 SG-1000 卡帶映像檔當作檔案讀取。手冊有說明之處以 Sega 的 Mark III 參考手冊為準，手冊未說明之處以出口版開機程式和 2,922 個真實映像檔為準。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-rom-image-python)](https://github.com/gufranco/sms-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2,922** 個不同的映像檔，量度自 **5,425** 個壓縮檔項目，**0** 個屬性失敗，其中 **2,453** 個在 `0x7FF0` 讀到檔頭，**393** 個零售版 Master System 卡帶中有 **370** 個重現了儲存的校驗和，**14** 個開機程式以摘要值聲明，**791** 個測試，**100%** 語句及分支覆蓋率，沒有依賴項

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

此範例建立一個 32K 的映像檔，在 `0x7FF0` 放置檔頭，寫入區域與大小位元組 `0x4C`，並把本套件計算出的校驗和封入兩個校驗和位元組。然後在前面加上一個 512 位元組的拷貝機區塊。`strip_copier_stub` 僅憑長度識別該區塊並將其移除。讀回的檔頭顯示這是一個聲明 32K 的出口版 Master System 卡帶，而儲存的校驗和與計算值相符。

## 安裝

| 需求   | 版本                     |
| :----- | :----------------------- |
| Python | 3.12 或更新              |
| git    | 任何版本，用於複製儲存庫 |

```bash
git clone https://github.com/gufranco/sms-rom-image-python.git
cd sms-rom-image-python
python3 smsimage/doctor.py
```

本套件不匯入標準函式庫以外的任何東西。沒有子模組，所以直接以 git clone 複製或使用下載 zip 的連結，都能得到可以執行的工作副本。`pip install git+https://github.com/gufranco/sms-rom-image-python.git` 只安裝套件本身，診斷腳本以 `smsimage-doctor` 指令提供。

診斷腳本檢查機器和工作副本，最後輸出一行。提交錯誤報告時，請貼上它的完整輸出。

```
  9 checks, nothing to report
```

版本發佈遵循[語義化版本](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個版本都會加上標籤，並列在[版本發佈頁面](https://github.com/gufranco/sms-rom-image-python/releases)。

## 介面

四個模組回答四個問題，排列順序就是呼叫者需要提出這些問題的順序。

| 模組                               | 問題                                   |
| :--------------------------------- | :------------------------------------- |
| [`dump`](smsimage/dump.py)         | 傾印裝置加入了甚麼                     |
| [`header`](smsimage/header.py)     | 卡帶如何描述自己，描述寫在哪裏         |
| [`identity`](smsimage/identity.py) | 甚麼令這個檔案成為它本身，由哪個值決定 |
| [`manifest`](smsimage/manifest.py) | 讀取者提供了錯誤的檔案時，是哪一種錯誤 |

對映像檔的每個查詢，在沒有可讀內容時都回答 `None`，而不會拋出例外。缺少檔頭是正常狀態：2,922 個映像檔中有 456 個沒有檔頭。

### 讀取傾印

| 呼叫                           | 回傳                                                                                        |
| :----------------------------- | :------------------------------------------------------------------------------------------ |
| `dump.read(path)`              | 檔案的位元組，若有拷貝機區塊則已移除。`path` 是 `str` 或 `Path`                             |
| `dump.form(data)`              | 當 `data` 長於 512 位元組，且長度比整數個 KB 多出 512 時回傳 `"stubbed"`，否則回傳 `"bare"` |
| `dump.strip_copier_stub(data)` | 形式為 `"stubbed"` 時回傳去掉前 512 位元組的 `data`，否則原樣回傳 `data`                    |

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

判斷依據只有長度。512 位元組的檔案屬於 bare，因為去掉區塊後甚麼都不會剩下。`dump.read` 已經剝離區塊，所以若要知道檔案原本是哪種形式，請自行讀取位元組並傳給 `dump.form`。

### 檔頭

| 呼叫                          | 回傳                                                                                   |
| :---------------------------- | :------------------------------------------------------------------------------------- |
| `header.anchors_in(image)`    | 所有含有 `TMR SEGA` 的候選偏移位置，由大到小，以 tuple 回傳                            |
| `header.anchor_of(image)`     | 其中第一個，或 `None`                                                                  |
| `header.region_of(image)`     | 錨點加 `0x0F` 處位元組的高半位元組所對應的名稱；沒有檔頭或沒有名稱時為 `None`          |
| `header.declared_size(image)` | 該位元組的低半位元組所對應的大小，以位元組計；沒有檔頭或代碼不為本解讀所知時為 `None`  |
| `header.carried(image)`       | 錨點加 `0x0A` 處的小端序字；沒有檔頭時為 `None`                                        |
| `header.checksum(image)`      | 出口版開機程式計算的總和，為小於 `0x10000` 的 `int`；沒有檔頭或大小代碼未知時為 `None` |
| `header.agrees(image)`        | `checksum(image) == carried(image)`；沒有可比較的校驗和時為 `None`                     |

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

區域半位元組 9 沒有名稱，所以 `region_of` 回答 `None`，但大小仍可讀出。大小半位元組 3 在表中沒有條目，所以沒有可加總的範圍，也沒有可比較的校驗和。沒有檔頭的映像檔對每個查詢都回答 `None`，空映像檔也一樣。

### 身份

| 呼叫                               | 回傳                                                                         |
| :--------------------------------- | :--------------------------------------------------------------------------- |
| `identity.measure(data)`           | 包含 `size`、`crc32`、`md5`、`sha1` 和 `sha256` 的映射，摘要值為小寫十六進位 |
| `identity.agrees(found, expected)` | 兩個 `sha256` 值是否相符，不分大小寫。任何一方沒有該值時拋出 `NoAuthority`   |

只有一個值決定檔案是否就是那個檔案。即使記錄中較弱的值不一致，只要這個值相符，仍然算作匹配：

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

沒有 SHA-256 的記錄會被拒絕，而不是按它碰巧帶有的較弱值來評定：

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

### 清單

`Manifest(document)` 接受一個含有 `artifacts` 映射的映射。每個構件有一個 `accepted` 記錄列表，每筆記錄帶有 `sha256`。構件也可以帶有 `name` 及 `badDumps` 列表，列表條目帶有 `sha256` 和 `why`。`manifest.read(path)` 把 JSON 檔案解析成一個清單。

| 成員                         | 意義                                            |
| :--------------------------- | :---------------------------------------------- |
| `Manifest.keys`              | 構件的鍵，以 tuple 回傳                         |
| `Manifest.name(key)`         | 構件的 `name`；構件沒有名稱或未經聲明時為 `key` |
| `Manifest.match(key, data)`  | 位元組 `data` 對照構件 `key` 的 `Match`         |
| `Match.key`, `Match.verdict` | 所查詢的鍵，以及下列五種判定之一                |
| `Match.found`                | `identity.measure` 對這些位元組的回傳值         |
| `Match.why`                  | 所匹配壞傾印的 `why`，否則為 `None`             |
| `bool(match)`                | 只有 `accepted` 時為 True                       |

| 判定                                  | 條件                                     |
| :------------------------------------ | :--------------------------------------- |
| `accepted`                            | SHA-256 是構件接受的值之一               |
| `a known bad dump`                    | SHA-256 是構件列在 `badDumps` 下的值之一 |
| `the right length, the wrong content` | 大小與某筆接受記錄相符，但摘要值不符     |
| `a length nothing declares`           | 摘要值和大小都不相符                     |
| `undeclared`                          | 清單在該鍵下沒有構件                     |

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

已知的壞傾印與接受的檔案分開聲明，所以損壞的副本會被診斷為損壞，而不是錯誤的檔案。不是清單的文件在建構時就會被拒絕：

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

### 錯誤

兩者都定義在 [`smsimage/errors.py`](smsimage/errors.py)，並在套件頂層公開，所以呼叫者可以按名稱分別捕捉。

| 錯誤          | 拋出時機                                                                                                  |
| :------------ | :-------------------------------------------------------------------------------------------------------- |
| `Malformed`   | `Manifest` 收到的不是映射、沒有聲明任何構件、有某個構件不是映射，或有某個構件的 `accepted` 列表缺失或為空 |
| `NoAuthority` | `identity.agrees` 收到沒有 `sha256` 的一方，或 `Manifest` 收到沒有 `sha256` 的接受記錄                    |

`manifest.read` 遇到無法讀取的檔案或無效的 JSON 時，由 `pathlib` 和 `json` 拋出它們本身的例外。

### 模組內容

| 名稱                                               | 內容                                                                                                                           |
| :------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| `smsimage.MAGIC`                                   | `b"TMR SEGA"`，檔頭開首的八個位元組                                                                                            |
| `smsimage.CANDIDATES`                              | `(0x7FF0, 0x3FF0, 0x1FF0)`，搜尋的偏移位置，由大到小                                                                           |
| `smsimage.REGIONS`                                 | 區域半位元組對應的名稱：`0x3` `sms-japan`、`0x4` `sms-export`、`0x5` `gg-japan`、`0x6` `gg-export`、`0x7` `gg-international`   |
| `smsimage.SIZES`                                   | 大小半位元組對應的位元組數：`0xA` 8K、`0xB` 16K、`0xC` 32K、`0xD` 48K、`0xE` 64K、`0xF` 128K、`0x0` 256K、`0x1` 512K、`0x2` 1M |
| `smsimage.BARE`, `smsimage.STUBBED`                | `dump.form` 回傳的兩個值                                                                                                       |
| `smsimage.AUTHORITATIVE`                           | `"sha256"`，唯一起決定作用的值                                                                                                 |
| `smsimage.VERDICTS`                                | 五種判定，按 `match` 嘗試的順序排列                                                                                            |
| `smsimage.Manifest`, `smsimage.Match`              | 清單及其回答                                                                                                                   |
| `smsimage.Malformed`, `smsimage.NoAuthority`       | 兩種錯誤                                                                                                                       |
| `smsimage.__version__`                             | 已安裝的版本                                                                                                                   |
| `dump.COPIER_BLOCK`                                | 512                                                                                                                            |
| `identity.CROSS_REFERENCE`                         | `("size", "crc32", "md5", "sha1")`，會量度但從不起決定作用                                                                     |
| `header.CHECKSUM`, `header.REGION_AND_SIZE`        | 校驗和字以及區域與大小位元組相對於錨點的位置：`0x0A` 至 `0x0B`，以及 `0x0F`                                                    |
| `header.FIRST_SPAN`, `header.BANKS_FROM_THE_THIRD` | 出口版開機程式的兩個表，以大小半位元組為鍵                                                                                     |

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

### 診斷腳本

`python3 smsimage/doctor.py`，或以 pip 安裝後的 `smsimage-doctor`，不接受任何參數。它報告機器的狀況：直譯器、輸出及預設編碼、檔案系統大小寫、換行符、路徑長度、可用空間和 git。然後它用自行組裝的映像檔驅動套件：剝離拷貝機區塊、找出預先放置的檔頭、重現封入的校驗和、量度映像檔、解析 [`artifacts.manifest.json`](artifacts.manifest.json)，並讀取 [`conformance/corpus.json`](conformance/corpus.json)。空的語料庫與不存在的語料庫分開報告。全部 9 項套件檢查通過時以 0 結束，否則以 1 結束。

## 真實遊戲庫實際包含甚麼

Sega 的 _Software Reference Manual for the SEGA Mark III Console_ 在第 22 頁列出檔頭，而 [`conformance/hardware.json`](conformance/hardware.json) 保存了手冊陳述的每項事實及其出處句子。這是一份重新打字的副本，打字者不詳。手冊與卡帶不一致時以卡帶為準，[`conformance/divergences.json`](conformance/divergences.json) 記錄每項不一致及其量度結果。以下每個數字都是在進行普查的 Master System、Game Gear 和 SG-1000 遊戲庫上量度所得，以映像檔位元組的 SHA-256 為鍵，所以計數是映像檔的數目，而不是檔名的數目。

| 量度項目                                          |  數目 |
| :------------------------------------------------ | ----: |
| 讀取的壓縮檔項目                                  | 5,425 |
| 不同的映像檔                                      | 2,922 |
| 重複列出已見過的映像檔                            | 2,503 |
| 檔頭只在 `0x7FF0`                                 | 2,450 |
| 檔頭在 `0x3FF0` / `0x1FF0`                        | 8 / 5 |
| 檔頭同時在 `0x3FF0` 和 `0x7FF0`，從 `0x7FF0` 讀取 |     3 |
| 任何候選偏移位置都沒有檔頭                        |   456 |
| 帶有 512 位元組拷貝機區塊                         |    17 |

其中有五件事，會令按描述編寫的讀取程式出錯。

**檔頭並非普遍存在。** 456 個映像檔沒有檔頭，其中只有 76 個短得無法在 `0x7FF0` 容納檔頭。其中 205 個是零售版 SG-1000 卡帶，沒有一個帶有檔頭：對甚麼都回答有的檔頭搜尋器，正是靠這個對照組發現的。所以每個查詢都回答 `None`，而不是拋出例外。

**沒有檔頭的地方也會出現魔術字串。** 作為原始檔案讀取時，141 個映像檔在三個候選偏移位置以外帶有 `TMR SEGA`。其中 16 個是帶拷貝機區塊的映像檔，在區塊移除之前，它們的檔頭位於 `0x81F0`。其餘位於記憶庫邊界，這正是多合一卡帶或過量傾印的特徵。只會搜尋這三個候選位置。

**有三個映像檔在兩個候選位置都帶有魔術字串。** 最大的位置優先，而 `anchors_in` 會報告每個匹配，讓呼叫者看到這種歧義。

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

**魔術字串之後的兩個位元組並非保留位元組。** 手冊把它們印作兩個空格 `20 20`，但 2,466 個檔頭中只有 400 個帶有這兩個位元組。`00 00` 出現在 1,149 個檔頭上，`FF FF` 出現在 527 個上，之後還有一長串其他值。出口版和 Game Gear 開機程式都比較八個位元組 `TMR SEGA`，本套件也一樣。`python3 -m conformance.divergences <library>` 可量度這些數值。

**Game Gear 卡帶通常不儲存校驗和。** 在 Game Gear 集合中帶有檔頭的 1,105 個不同映像檔裏，1,018 個儲存的值為零，48 個重現了規則，這是 `python3 -m conformance.divergences` 只對該集合量度的結果。Game Gear 開機程式在三個位址尋找 `TMR SEGA`，此外甚麼都不檢查，所以該遊戲機上從來沒有任何東西讀取過儲存的值。`header.agrees` 對這些映像檔回答 `False`，這是關於遊戲機的陳述，而不是關於檔案的陳述。

手冊列出的大小代碼最大到 256K，每個都配上區域半位元組 `0x4`。出口版開機程式解碼九個大小代碼，包括 512K 和 1M，並且只在區域 `0x4` 上檢查總和。其他區域半位元組採用模擬器社群的命名方式，沒有任何 Sega 文件證實這種命名。普查結果與這種命名一致：Master System 映像檔以區域 `0x4` 為主，Game Gear 映像檔則以 `0x5` 至 `0x7` 為主。49 個映像檔帶有任何解讀都無法解釋的區域半位元組，3 個帶有這樣的大小半位元組，這些都解析為 `None`，而不是最接近的合理值。

## 校驗和規則

這條規則就是出口版開機程式執行的規則，讀取自 [`artifacts.manifest.json`](artifacts.manifest.json) 中聲明的 v1.3 程式。每個大小代碼指定一個首段範圍，即 `0x1FF0`、`0x3FF0`、`0x7FF0`，或 48K 時為 `0xBFF0`，並把範圍以下的位元組加總。從 64K 起，再加上從第三個開始的完整 16K 記憶庫：64K 加 2 個，128K 加 6 個，256K 加 14 個，512K 加 30 個，1M 加 62 個。只保留低十六位。`python3 -m conformance.boot <program> [program ...]` 從每個執行加總的已聲明程式讀出兩個表、八位元組比較和區域檢查條件，並與本套件核對。這樣的程式有九個，九個的首段範圍和 512K 以內的記憶庫數目都相同。到 1M 時出現分歧：v1.3 和另外五個讀出 62 個記憶庫，Hang On v3.4、Hang On & Safari Hunt v2.4 和 Missile Defense 3-D v4.4 讀出 33 個，而遊戲庫中沒有任何映像檔能分辨兩者。手冊說只需排除兩個校驗和位元組，而按這種解讀，2,463 個映像檔中沒有一個能重現儲存的值。

| 群體                                                                                                            |                  重現 |
| :-------------------------------------------------------------------------------------------------------------- | --------------------: |
| 零售版 Master System 卡帶，即 Master System 集合中的四個地區資料夾，由 `python3 -m conformance.categories` 量度 |     393 個中的 370 個 |
| Master System 集合中所有帶有檔頭且大小為本解讀所知的映像檔，包括修改過的映像檔                                  |   1,331 個中的 925 個 |
| 所有帶有檔頭且大小為本解讀所知的映像檔                                                                          | 2,463 個中的 1,011 個 |

修改過的映像檔不一致，原因屬於修改本身：據 `python3 -m conformance.categories` 量度，翻譯版在 301 個中有 78 個重現規則，改版在 129 個中有 33 個。因此普查把一致與否作為觀察結果報告，而不以它作為關卡檢查。

沒有任何其他開機程式能解釋 23 個無法重現的零售卡帶。其中 16 個的區域半位元組不是 `0x4`，九個程式都不會對這些檢查總和。其餘 7 個聲明 32K、128K 或 256K，九個程式在這些大小上讀的是同一個表。

## 普查，以及它的輸出為何可以發佈

[`conformance/census.py`](conformance/census.py) 遍歷你擁有的遊戲庫：目錄、zip 壓縮檔，以及單獨的 `.sms`、`.gg` 和 `.sg` 檔案。

```bash
python3 -m conformance.census /path/to/library.zip /path/to/another
```

它按 SHA-256 把每個不同的映像檔只計算一次，對每個映像檔檢查六項屬性，報告一項觀察結果，並寫入 [`conformance/corpus.json`](conformance/corpus.json)：151 種由形式、長度、錨點、區域、聲明大小，以及儲存的校驗和是否重現所構成的組合，每種組合附有計數。不含標題，也不含內容，所以其中沒有任何東西能重建任何卡帶的任何部分。

| 結束代碼 | 條件                             |
| :------- | :------------------------------- |
| 0        | 每項屬性在每個映像檔上都成立     |
| 1        | 有屬性不成立，或給出的路徑不存在 |
| 2        | 沒有給出路徑                     |

這六項屬性是函數之間的不變式，這些函數目前在構造上就一致。每個測試替換它所守護的那一對中的一方，觀察屬性是否觸發，所以六項屬性都已證實能捕捉它們要防範的偏移。

沒有映像檔時，普查會說明它沒有檢查任何東西，並保留現有的語料庫，而不是用空的語料庫覆蓋它。

## 它是否正確

手冊列出的每項事實，只要測試能觸及，都會與程式碼核對。[`conformance/hardware.json`](conformance/hardware.json) 記錄每項事實及其句子和頁碼，[`conformance/hardware.test.py`](conformance/hardware.test.py) 把它們與套件中的常數比較。`python3 -m conformance.documents` 取得手冊後，`python3 -m conformance.quotes` 會在手冊中找出每個引用的句子。

`python3 -m conformance.corpus` 在沒有遊戲庫的情況下，把 [`conformance/corpus.json`](conformance/corpus.json) 中的 151 種組合對套件重播，測試套件則根據該檔案核對主要計數。`python3 -m conformance.speed` 要求 256K 映像檔的校驗和計算速度不低於每秒 130 次。

讀取者可能需要的開機程式在 [`artifacts.manifest.json`](artifacts.manifest.json) 中以大小、CRC32、SHA-1 和 SHA-256 聲明。它們都不在本儲存庫中，這裏也沒有說明從哪裏取得。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出 Sega 的資料都未能解決的 3 個問題，以及解決每個問題需要甚麼。

## 參與開發

| 需要                                 | 位置                                                                     |
| :----------------------------------- | :----------------------------------------------------------------------- |
| 每個關卡檢查及其執行順序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                       |
| 給程式碼代理的相同資料               | [AGENTS.md](AGENTS.md)                                                   |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md)                                                   |
| 錯誤報告                             | [GitHub Issues](https://github.com/gufranco/sms-rom-image-python/issues) |
| 安全問題報告                         | [SECURITY.md](SECURITY.md)                                               |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find smsimage conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

每個模組旁邊都有一個以它命名的測試檔案，每個測試檔案都可以單獨執行。覆蓋率是硬性關卡檢查，要求 100% 語句及分支覆蓋。本 README 中的每個示例都由 [`conformance/readme.test.py`](conformance/readme.test.py) 執行，並把輸出與這裏印出的內容比較。

## 參考資料

- _Software Reference Manual for the SEGA Mark III Console_，Sega，無日期，第 22 頁，由不具名者重新打字。45 頁，184,840 位元組，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。用於檔頭佈局、開首字串、校驗和位元組和大小代碼。它不可再分發，也不在本儲存庫中。`python3 -m conformance.documents` 從 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下載它到 `docs/`，並拒絕任何其他檔案。本 README 中的每個網址每週都會檢查。

## 引用本專案

[CITATION.cff](CITATION.cff) 在每次發佈時，由寫入套件版本的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
