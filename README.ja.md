# SMS ROM Image

セガ・マスターシステム、ゲームギア、SG-1000のカートリッジイメージをファイルとして読み取ります。セガのMark IIIリファレンスマニュアルが記述している部分はそれに従い、記述していない部分は輸出版ブートプログラムと2,922本の実在のイメージに従います。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-rom-image-python)](https://github.com/gufranco/sms-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**5,425**件のアーカイブエントリから測定した**2,922**本の異なるイメージ、性質の不成立**0**件、そのうち**2,453**本で`0x7FF0`のヘッダーを読み取り、市販マスターシステムカートリッジ**393**本中**370**本で格納済みチェックサムを再現、ダイジェストで宣言したブートプログラム**14**本、テスト**791**件、ステートメントカバレッジとブランチカバレッジ**100%**、依存関係なし

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

この例では、`0x7FF0`にヘッダーを持つ32Kのイメージを作り、リージョンとサイズのバイト`0x4C`を書き込み、このパッケージが計算したチェックサムを2つのチェックサムバイトに封入します。次に、512バイトのコピー機ブロックを先頭に付けます。`strip_copier_stub`は長さだけでこのブロックを認識し、取り除きます。ヘッダーは32Kを宣言する輸出版マスターシステムカートリッジとして読み取られ、格納済みチェックサムは計算値と一致します。

## インストール

| 要件   | バージョン       |
| :----- | :--------------- |
| Python | 3.12以降         |
| git    | 任意、クローン用 |

```bash
git clone https://github.com/gufranco/sms-rom-image-python.git
cd sms-rom-image-python
python3 smsimage/doctor.py
```

このパッケージは標準ライブラリ以外を何もインポートしません。サブモジュールはないため、通常のクローンでもZIPダウンロードのリンクでも、そのまま動くチェックアウトが得られます。`pip install git+https://github.com/gufranco/sms-rom-image-python.git`はパッケージだけをインストールし、ドクターは`smsimage-doctor`コマンドとして使えます。

ドクターはマシンとチェックアウトを確認し、最後に1行を出力します。バグ報告には出力全体を貼り付けてください。

```
  9 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。すべてのリリースにはタグが付き、[リリースページ](https://github.com/gufranco/sms-rom-image-python/releases)に掲載されます。

## インターフェース

4つのモジュールが4つの問いに答えます。順序は呼び出し側が問うべき順です。

| モジュール                         | 問い                                                             |
| :--------------------------------- | :--------------------------------------------------------------- |
| [`dump`](smsimage/dump.py)         | ダンプ装置は何を付け加えたか                                     |
| [`header`](smsimage/header.py)     | カートリッジは自身について何を、どこで述べているか               |
| [`identity`](smsimage/identity.py) | このファイルをこのファイルたらしめるものは何か、どの値が決め手か |
| [`manifest`](smsimage/manifest.py) | 読み手が誤ったファイルを渡したとき、どういう誤りか               |

イメージへの問い合わせは、読み取るものがない場合、例外を送出せずに`None`を返します。ヘッダーがないのは正常な状態です。2,922本のイメージのうち456本はヘッダーを持ちません。

### ダンプの読み取り

| 呼び出し                       | 戻り値                                                                                                      |
| :----------------------------- | :---------------------------------------------------------------------------------------------------------- |
| `dump.read(path)`              | ファイルのバイト列。コピー機ブロックがあれば取り除いたもの。`path`は`str`または`Path`です                   |
| `dump.form(data)`              | `data`が512バイトより長く、その長さがキロバイト単位の整数倍より512余る場合は`"stubbed"`、それ以外は`"bare"` |
| `dump.strip_copier_stub(data)` | 形式が`"stubbed"`なら先頭512バイトを除いた`data`、それ以外は`data`をそのまま                                |

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

判定に使うのは長さだけです。512バイトのファイルは、ブロックの後ろに何も残らないためbareです。`dump.read`はすでにブロックを取り除いているので、ファイルがどの形式だったかを知るには、バイト列を自分で読んで`dump.form`に渡してください。

### ヘッダー

| 呼び出し                      | 戻り値                                                                                                   |
| :---------------------------- | :------------------------------------------------------------------------------------------------------- |
| `header.anchors_in(image)`    | `TMR SEGA`を持つ候補オフセットすべて。大きい順のタプル                                                   |
| `header.anchor_of(image)`     | そのうち最初のもの、または`None`                                                                         |
| `header.region_of(image)`     | アンカーに`0x0F`を足した位置のバイトの上位ニブルに対応する名前。ヘッダーがないか名前がない場合は`None`   |
| `header.declared_size(image)` | そのバイトの下位ニブルに対応するバイト単位のサイズ。ヘッダーがないか、解釈が知らないコードの場合は`None` |
| `header.carried(image)`       | アンカーに`0x0A`を足した位置のリトルエンディアンのワード。ヘッダーがなければ`None`                       |
| `header.checksum(image)`      | 輸出版ブートプログラムが計算する合計。`0x10000`未満の`int`。ヘッダーがないかサイズコードが不明なら`None` |
| `header.agrees(image)`        | `checksum(image) == carried(image)`。比較するチェックサムがなければ`None`                                |

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

リージョンニブル9には名前がないため、`region_of`は`None`を返しますが、サイズは読み取れます。サイズニブル3は表に項目がないため、合計する範囲がなく、比較するチェックサムもありません。ヘッダーのないイメージはすべての問い合わせに`None`を返し、空のイメージも同様です。

### 同一性

| 呼び出し                           | 戻り値                                                                                                           |
| :--------------------------------- | :--------------------------------------------------------------------------------------------------------------- |
| `identity.measure(data)`           | `size`、`crc32`、`md5`、`sha1`、`sha256`のマッピング。ダイジェストは小文字の16進数です                           |
| `identity.agrees(found, expected)` | 2つの`sha256`の値が大文字小文字を区別せずに一致するかどうか。どちらかが持っていなければ`NoAuthority`を送出します |

ファイルが目的のファイルかどうかを決めるのは1つの値だけです。より弱い値が食い違うレコードでも、その値が一致すれば一致とみなします。

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

SHA-256を持たないレコードは、手持ちのより弱い値で判定されることはなく、拒否されます。

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

### マニフェスト

`Manifest(document)`は、`artifacts`マッピングを含むマッピングを受け取ります。各アーティファクトはレコードの`accepted`リストを持ち、各レコードは`sha256`を持ちます。アーティファクトは`name`と、`sha256`と`why`を持つエントリからなる`badDumps`リストを持つこともできます。`manifest.read(path)`はJSONファイルを解析してマニフェストを作ります。

| メンバー                     | 意味                                                              |
| :--------------------------- | :---------------------------------------------------------------- |
| `Manifest.keys`              | アーティファクトのキー。タプルです                                |
| `Manifest.name(key)`         | アーティファクトの`name`。名前がないか宣言されていない場合は`key` |
| `Manifest.match(key, data)`  | バイト列`data`をアーティファクト`key`と照合した`Match`            |
| `Match.key`, `Match.verdict` | 問い合わせたキーと、下記5つの判定のいずれか                       |
| `Match.found`                | そのバイト列に対して`identity.measure`が返したもの                |
| `Match.why`                  | 一致した不良ダンプの`why`。それ以外は`None`                       |
| `bool(match)`                | `accepted`の場合のみTrue                                          |

| 判定                                  | 条件                                                               |
| :------------------------------------ | :----------------------------------------------------------------- |
| `accepted`                            | SHA-256がアーティファクトの受け入れるものである                    |
| `a known bad dump`                    | SHA-256がアーティファクトの`badDumps`に載っているものである        |
| `the right length, the wrong content` | サイズは受け入れ済みレコードと一致するが、ダイジェストは一致しない |
| `a length nothing declares`           | ダイジェストもサイズも一致しない                                   |
| `undeclared`                          | マニフェストにそのキーのアーティファクトがない                     |

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

既知の不良ダンプは受け入れ済みファイルとは別に宣言するため、破損したコピーは誤ったファイルではなく、破損したものとして診断されます。マニフェストでない文書は、構築時に拒否されます。

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

### エラー

どちらも[`smsimage/errors.py`](smsimage/errors.py)にあり、パッケージのトップレベルで公開されているため、呼び出し側はそれぞれを名前で捕捉できます。

| エラー        | 送出される条件                                                                                                                                                                               |
| :------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Malformed`   | `Manifest`に、マッピングでないもの、アーティファクトを宣言していないもの、マッピングでないアーティファクトを持つもの、`accepted`リストが欠けているか空のアーティファクトを持つものが渡された |
| `NoAuthority` | `identity.agrees`に`sha256`を持たない側が渡された、または`Manifest`に`sha256`を持たない受け入れ済みレコードが渡された                                                                        |

`manifest.read`は、読み取れないファイルや不正なJSONに対して、`pathlib`と`json`が送出するものをそのまま送出させます。

### モジュールの内容

| 名前                                               | 内容                                                                                                                                   |
| :------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `smsimage.MAGIC`                                   | `b"TMR SEGA"`。ヘッダーの先頭8バイト                                                                                                   |
| `smsimage.CANDIDATES`                              | `(0x7FF0, 0x3FF0, 0x1FF0)`。探索するオフセット、大きい順                                                                               |
| `smsimage.REGIONS`                                 | リージョンニブルから名前への対応：`0x3` `sms-japan`、`0x4` `sms-export`、`0x5` `gg-japan`、`0x6` `gg-export`、`0x7` `gg-international` |
| `smsimage.SIZES`                                   | サイズニブルからバイト数への対応：`0xA` 8K、`0xB` 16K、`0xC` 32K、`0xD` 48K、`0xE` 64K、`0xF` 128K、`0x0` 256K、`0x1` 512K、`0x2` 1M   |
| `smsimage.BARE`, `smsimage.STUBBED`                | `dump.form`が返す2つの値                                                                                                               |
| `smsimage.AUTHORITATIVE`                           | `"sha256"`。決め手となる唯一の値                                                                                                       |
| `smsimage.VERDICTS`                                | 5つの判定。`match`が試す順                                                                                                             |
| `smsimage.Manifest`, `smsimage.Match`              | マニフェストとその答え                                                                                                                 |
| `smsimage.Malformed`, `smsimage.NoAuthority`       | 2つのエラー                                                                                                                            |
| `smsimage.__version__`                             | インストールされているバージョン                                                                                                       |
| `dump.COPIER_BLOCK`                                | 512                                                                                                                                    |
| `identity.CROSS_REFERENCE`                         | `("size", "crc32", "md5", "sha1")`。測定はするが決め手にはならない値                                                                   |
| `header.CHECKSUM`, `header.REGION_AND_SIZE`        | チェックサムのワードと、リージョンとサイズのバイトの位置。アンカーからの相対で`0x0A`から`0x0B`、および`0x0F`                           |
| `header.FIRST_SPAN`, `header.BANKS_FROM_THE_THIRD` | 輸出版ブートプログラムの2つの表。サイズニブルをキーとします                                                                            |

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

### ドクター

`python3 smsimage/doctor.py`、またはpipでインストールした後の`smsimage-doctor`は、引数を取りません。マシンについて、インタプリタ、出力エンコーディングとデフォルトエンコーディング、ファイルシステムの大文字小文字の扱い、改行コード、パスの長さ、空き容量、gitを報告します。次に、自分で組み立てたイメージに対してパッケージを動かします。コピー機ブロックを取り除き、埋め込んだヘッダーを見つけ、封入したチェックサムを再現し、イメージを測定し、[`artifacts.manifest.json`](artifacts.manifest.json)を解析し、[`conformance/corpus.json`](conformance/corpus.json)を読み取ります。中身が空のコーパスは、コーパスが存在しない場合とは区別して報告します。パッケージの9つのチェックがすべて通れば0で、それ以外は1で終了します。

## 実際のライブラリに含まれるもの

セガの*Software Reference Manual for the SEGA Mark III Console*は22ページにヘッダーを掲載しており、[`conformance/hardware.json`](conformance/hardware.json)には、そこに書かれた事実がすべて、出典の文とともに収められています。このマニュアルは打ち直された写しで、打ち直した人の記録はありません。マニュアルとカートリッジが食い違う場合はカートリッジを優先し、[`conformance/divergences.json`](conformance/divergences.json)に食い違いごとの測定値を記録しています。以下の数値はすべて、全数調査を行ったマスターシステム、ゲームギア、SG-1000のライブラリ全体で測定したもので、イメージのバイト列のSHA-256をキーとしています。そのため、数はファイル名の数ではなくイメージの数です。

| 測定項目                                               |  件数 |
| :----------------------------------------------------- | ----: |
| 読み取ったアーカイブエントリ                           | 5,425 |
| 異なるイメージ                                         | 2,922 |
| 既出のイメージの重複掲載                               | 2,503 |
| `0x7FF0`のみにヘッダー                                 | 2,450 |
| `0x3FF0` / `0x1FF0`にヘッダー                          | 8 / 5 |
| `0x3FF0`と`0x7FF0`の両方にヘッダー、`0x7FF0`で読み取り |     3 |
| どの候補オフセットにもヘッダーなし                     |   456 |
| 512バイトのコピー機ブロック付き                        |    17 |

ここには、説明文から書かれたリーダーを壊すものが5つあります。

**ヘッダーは普遍的ではありません。** 456本のイメージはヘッダーを持たず、そのうち`0x7FF0`にヘッダーを置けないほど短いものは76本だけです。そのうち205本は市販のSG-1000カートリッジで、どれもヘッダーを持ちません。何にでもあると答えるヘッダー探索は、この対照群で見つかります。そのため、すべての問い合わせは例外を送出せずに`None`を返します。

**マジックはヘッダーのない場所にも現れます。** 生のファイルとして読むと、141本のイメージが3つの候補オフセット以外の場所に`TMR SEGA`を持っています。そのうち16本はコピー機ブロック付きのイメージで、ブロックを取り除くまではヘッダーが`0x81F0`にあります。残りはバンク境界にあり、これはマルチカートやオーバーダンプの特徴です。探索するのは3つの候補だけです。

**3本のイメージは2つの候補にマジックを持っています。** 大きいほうが優先され、`anchors_in`はすべての一致を報告するので、呼び出し側はその曖昧さを確認できます。

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

**マジックの後の2バイトは予約されていません。** マニュアルはこれを2つのスペース`20 20`として掲載していますが、2,466個のヘッダーのうちこの値を持つのは400個だけです。`00 00`は1,149個、`FF FF`は527個に現れ、その後に長い裾野が続きます。輸出版とゲームギアのブートプログラムはどちらも8バイト`TMR SEGA`を比較し、このパッケージも同様です。`python3 -m conformance.divergences <library>`でこれらを測定できます。

**ゲームギアのカートリッジは通常チェックサムを格納していません。** ゲームギアのセットのうちヘッダーを持つ1,105本の異なるイメージでは、1,018本が値0を格納し、48本が規則を再現します。これは`python3 -m conformance.divergences`をそのセットだけに対して実行した測定値です。ゲームギアのブートプログラムは3つのアドレスで`TMR SEGA`を探すだけで、それ以外は何も確認しないため、このゲーム機で格納値を読んだものはありませんでした。`header.agrees`はこれらに`False`を返しますが、これはファイルではなくゲーム機についての記述です。

マニュアルはサイズコードを256Kまで掲載しており、いずれもリージョンニブルは`0x4`です。輸出版ブートプログラムは512Kと1Mを含む9つのサイズコードを解釈し、合計を確認するのはリージョン`0x4`の場合だけです。その他のリージョンニブルはエミュレーションコミュニティの呼び方に従って命名しており、これを裏付けるセガの文書はありません。全数調査の結果はこの命名と一致しています。マスターシステムのイメージではリージョン`0x4`が、ゲームギアのイメージでは`0x5`から`0x7`が大半を占めます。49本のイメージはどの解釈でも説明できないリージョンニブルを、3本は同様のサイズニブルを持ち、これらは最も妥当そうな近い値ではなく`None`になります。

## チェックサムの規則

規則は輸出版ブートプログラムが実行するもので、[`artifacts.manifest.json`](artifacts.manifest.json)で宣言したv1.3のプログラムから読み取ったものです。各サイズコードは最初の範囲として`0x1FF0`、`0x3FF0`、`0x7FF0`、48Kの場合は`0xBFF0`を指定し、その手前のバイトを合計します。64K以上では、3番目以降の16Kバンク全体を加算します。64Kで2個、128Kで6個、256Kで14個、512Kで30個、1Mで62個です。下位16ビットを保持します。`python3 -m conformance.boot <program> [program ...]`は、合計を実行する宣言済みの各プログラムから2つの表、8バイトの比較、リージョンの判定を読み取り、このパッケージと照合します。該当するのは9本で、9本とも最初の範囲と512Kまでのバンク数が同じです。1Mでは分かれます。v1.3を含む6本は62バンク、Hang On v3.4、Hang On & Safari Hunt v2.4、Missile Defense 3-D v4.4は33バンクを読み、ライブラリのどのイメージもこの2つを区別しません。マニュアルは2つのチェックサムバイトだけを除外するよう指示していますが、その解釈では2,463本のイメージのどれでも格納値を再現できません。

| 対象                                                                                                                           |             再現 |
| :----------------------------------------------------------------------------------------------------------------------------- | ---------------: |
| 市販マスターシステムカートリッジ。マスターシステムのセットの4つのリージョンフォルダ、`python3 -m conformance.categories`による |     393本中370本 |
| マスターシステムのセットのうち、ヘッダーと解釈が知るサイズを持つすべてのイメージ。改変版を含む                                 |   1,331本中925本 |
| ヘッダーと解釈が知るサイズを持つすべてのイメージ                                                                               | 2,463本中1,011本 |

改変されたイメージは、改変に起因する理由で食い違います。`python3 -m conformance.categories`の測定では、翻訳版は301本中78本、ハック版は129本中33本で規則を再現します。そのため、全数調査は一致をゲートにせず、観察結果として報告します。

再現しない市販カートリッジ23本は、別のブートプログラムでも説明できません。16本はリージョンニブルが`0x4`以外で、9本のプログラムはどれもその場合に合計を確認しません。残りの7本は32K、128K、256Kを宣言しており、9本とも同じ表を読みます。

## 全数調査と、その出力を配布できる理由

[`conformance/census.py`](conformance/census.py)は、あなたが所有するライブラリを走査します。対象はディレクトリ、ZIPアーカイブ、単体の`.sms`、`.gg`、`.sg`ファイルです。

```bash
python3 -m conformance.census /path/to/library.zip /path/to/another
```

異なるイメージをSHA-256で1本ずつ数え、それぞれで6つの性質を確認し、1つの観察結果を報告し、[`conformance/corpus.json`](conformance/corpus.json)を書き出します。中身は、形式、長さ、アンカー、リージョン、宣言サイズ、格納済みチェックサムを再現したかどうかの組み合わせ151通りと、それぞれの件数です。タイトルも内容も含まないため、どのカートリッジのどの部分も、そこから再構築することはできません。

| 終了コード | 条件                                         |
| :--------- | :------------------------------------------- |
| 0          | すべてのイメージですべての性質が成り立った   |
| 1          | 性質が崩れた、または指定したパスが存在しない |
| 2          | パスが指定されなかった                       |

6つの性質は、現時点では構造上一致する関数同士の不変条件です。各テストは、守っている組の片側を置き換えて性質が発火することを確認するため、6つすべてについて、検出すべきずれを実際に検出することが確かめられています。

イメージが1本もない場合、全数調査は何も調べなかったと報告し、既存のコーパスを空のもので上書きせずにそのまま残します。

## 正しいか

マニュアルに書かれた事実のうちテストで到達できるものは、すべてコードと照合しています。[`conformance/hardware.json`](conformance/hardware.json)は各事実をその文とページとともに収め、[`conformance/hardware.test.py`](conformance/hardware.test.py)はそれをパッケージの定数と比較します。`python3 -m conformance.quotes`は、`python3 -m conformance.documents`がマニュアルを取得した後、引用した文をすべてマニュアル内で見つけます。

`python3 -m conformance.corpus`は、[`conformance/corpus.json`](conformance/corpus.json)の151通りの組み合わせを、ライブラリなしでパッケージに対して再生し、テストスイートは見出しの数値をそのファイルと照合します。`python3 -m conformance.speed`は、256Kイメージのチェックサム計算に毎秒130回の下限を課します。

読み手が必要とするかもしれないブートプログラムは、[`artifacts.manifest.json`](artifacts.manifest.json)にサイズ、CRC32、SHA-1、SHA-256で宣言しています。どれもこのリポジトリには含まれておらず、入手先もここには書いていません。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)には、セガのどの資料でも決着しない3つの事柄と、それぞれを決着させるものを挙げています。

## 開発に参加する

| 必要なもの                                               | 場所                                                                     |
| :------------------------------------------------------- | :----------------------------------------------------------------------- |
| すべてのゲートと実行順                                   | [CONTRIBUTING.md](CONTRIBUTING.md)                                       |
| コーディングエージェント向けの同じ内容                   | [AGENTS.md](AGENTS.md)                                                   |
| このリポジトリがファミリーの他のリポジトリと共有する標準 | [FAMILY.md](FAMILY.md)                                                   |
| バグ報告                                                 | [GitHub Issues](https://github.com/gufranco/sms-rom-image-python/issues) |
| セキュリティ報告                                         | [SECURITY.md](SECURITY.md)                                               |

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

各モジュールには、その名前を冠したテストファイルが隣にあり、それぞれ単独で実行できます。カバレッジはステートメントとブランチの100%を必須のゲートとしています。このREADMEの実行例はすべて[`conformance/readme.test.py`](conformance/readme.test.py)が実行し、その出力をここに掲載したものと比較します。

## 参考文献

- _Software Reference Manual for the SEGA Mark III Console_、セガ、日付なし、22ページ、氏名不明の人物による打ち直し。45ページ、184,840バイト、SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。ヘッダーの配置、先頭の文字列、チェックサムバイト、サイズコードについて参照しました。再配布はできず、このリポジトリには含まれていません。`python3 -m conformance.documents`はhttps://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf から`docs/`にダウンロードし、それ以外のファイルは拒否します。このREADME内のアドレスはすべて毎週確認しています。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
