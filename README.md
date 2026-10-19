# SMS ROM Image

A Sega Master System, Game Gear or SG-1000 cartridge image read as a file, held to Sega's Mark III reference manual where it speaks and to the export boot programs and 2,922 real images where it does not.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sms-rom-image-python)](https://github.com/gufranco/sms-rom-image-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**2,922** distinct images measured from **5,425** archive entries, **0** property failures, the header read at `0x7FF0` on **2,453** of them, the stored checksum reproduced on **370** of **393** retail Master System cartridges, **14** boot programs declared by digest, **786** tests, **100%** statement and branch coverage, no dependencies

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

The example builds a 32K image with a header at `0x7FF0`, writes region and size byte `0x4C`, and seals the checksum this package computes into the two checksum bytes. It then puts a 512-byte copier block in front. `strip_copier_stub` recognises the block by the length alone and removes it. The header reads back as an export Master System cartridge declaring 32K, and the stored checksum matches the computed one.

## Install

| Requirement | Version       |
| :---------- | :------------ |
| Python      | 3.12 or newer |
| git         | Any, to clone |

```bash
git clone https://github.com/gufranco/sms-rom-image-python.git
cd sms-rom-image-python
python3 smsimage/doctor.py
```

The package imports nothing outside the standard library. There is no submodule, so a plain clone and the download-zip link both give a checkout that runs. `pip install git+https://github.com/gufranco/sms-rom-image-python.git` installs the package alone, with the doctor as the `smsimage-doctor` command.

The doctor checks the machine and the checkout and ends with one line. Paste its whole output into any bug report.

```
  9 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/sms-rom-image-python/releases).

## The interface

Four modules answer four questions, in the order a caller has to ask them.

| Module                             | Question                                                 |
| :--------------------------------- | :------------------------------------------------------- |
| [`dump`](smsimage/dump.py)         | What did the dumping device add                          |
| [`header`](smsimage/header.py)     | What does the cartridge say about itself, and where      |
| [`identity`](smsimage/identity.py) | What makes this file itself, and which value decides     |
| [`manifest`](smsimage/manifest.py) | When a reader supplies the wrong file, which wrong is it |

Every query on an image answers `None` rather than raising when there is nothing to read. A missing header is a normal state: 456 of the 2,922 images carry none.

### Reading a dump

| Call                           | Returns                                                                                                                    |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| `dump.read(path)`              | The file's bytes with a copier block removed when there is one. `path` is a `str` or a `Path`                              |
| `dump.form(data)`              | `"stubbed"` when `data` is longer than 512 bytes and its length leaves 512 over a whole number of kilobytes, else `"bare"` |
| `dump.strip_copier_stub(data)` | `data` without its first 512 bytes when the form is `"stubbed"`, else `data` unchanged                                     |

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

The test is the length and nothing else. A 512-byte file is bare because nothing would be left behind the block. `dump.read` has already stripped the block, so to ask which form a file was in, read the bytes yourself and pass them to `dump.form`.

### The header

| Call                          | Returns                                                                                                                 |
| :---------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| `header.anchors_in(image)`    | Every candidate offset holding `TMR SEGA`, largest first, as a tuple                                                    |
| `header.anchor_of(image)`     | The first of those, or `None`                                                                                           |
| `header.region_of(image)`     | The name for the high nibble of the byte at anchor plus `0x0F`, or `None` when no header or no name                     |
| `header.declared_size(image)` | The size in bytes for the low nibble of that byte, or `None` when no header or a code the reading does not know         |
| `header.carried(image)`       | The little-endian word at anchor plus `0x0A`, or `None` with no header                                                  |
| `header.checksum(image)`      | The sum the export boot program computes, as an `int` below `0x10000`, or `None` with no header or an unknown size code |
| `header.agrees(image)`        | `checksum(image) == carried(image)`, or `None` when there is no checksum to compare                                     |

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

Region nibble 9 has no name, so `region_of` answers `None` while the size still reads. Size nibble 3 has no entry in the table, so there is no span to sum and no checksum to compare. An image with no header answers `None` to every query, and so does an empty one.

### Identity

| Call                               | Returns                                                                                              |
| :--------------------------------- | :--------------------------------------------------------------------------------------------------- |
| `identity.measure(data)`           | A mapping of `size`, `crc32`, `md5`, `sha1` and `sha256`, the digests as lowercase hex               |
| `identity.agrees(found, expected)` | Whether the two `sha256` values match, ignoring case. Raises `NoAuthority` when either side has none |

One value decides whether a file is the file, and a record whose weaker values disagree still matches when that one agrees:

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

A record carrying no SHA-256 is refused rather than graded on whichever weaker value it carries:

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

### Manifests

`Manifest(document)` takes a mapping with an `artifacts` mapping. Each artifact has an `accepted` list of records, each carrying `sha256`, and may carry a `name` and a `badDumps` list whose entries carry `sha256` and `why`. `manifest.read(path)` parses a JSON file into one.

| Member                       | Meaning                                                             |
| :--------------------------- | :------------------------------------------------------------------ |
| `Manifest.keys`              | The artifact keys, as a tuple                                       |
| `Manifest.name(key)`         | The artifact's `name`, or `key` when it has none or is not declared |
| `Manifest.match(key, data)`  | A `Match` for the bytes `data` against artifact `key`               |
| `Match.key`, `Match.verdict` | The key asked about and one of the five verdicts below              |
| `Match.found`                | What `identity.measure` returned for the bytes                      |
| `Match.why`                  | The `why` of the bad dump matched, else `None`                      |
| `bool(match)`                | True only for `accepted`                                            |

| Verdict                               | When                                                        |
| :------------------------------------ | :---------------------------------------------------------- |
| `accepted`                            | The SHA-256 is one the artifact accepts                     |
| `a known bad dump`                    | The SHA-256 is one the artifact lists under `badDumps`      |
| `the right length, the wrong content` | The size matches an accepted record and the digest does not |
| `a length nothing declares`           | Neither the digest nor the size matches                     |
| `undeclared`                          | The manifest has no artifact under that key                 |

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

A known bad dump is declared apart from the accepted files, so a corrupt copy is diagnosed as corrupt rather than as the wrong file. A document that is not a manifest is refused when it is built:

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

### Errors

Both live in [`smsimage/errors.py`](smsimage/errors.py) and are published at the top of the package, so a caller can catch each by name.

| Error         | Raised when                                                                                                                                                             |
| :------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Malformed`   | `Manifest` is given something that is not a mapping, declares no artifacts, has an artifact that is not a mapping, or has one whose `accepted` list is missing or empty |
| `NoAuthority` | `identity.agrees` is given a side with no `sha256`, or `Manifest` is given an accepted record with none                                                                 |

`manifest.read` lets an unreadable file or invalid JSON raise what `pathlib` and `json` raise.

### Module contents

| Name                                               | Content                                                                                                                     |
| :------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| `smsimage.MAGIC`                                   | `b"TMR SEGA"`, the eight bytes a header opens with                                                                          |
| `smsimage.CANDIDATES`                              | `(0x7FF0, 0x3FF0, 0x1FF0)`, the offsets searched, largest first                                                             |
| `smsimage.REGIONS`                                 | Region nibble to name: `0x3` `sms-japan`, `0x4` `sms-export`, `0x5` `gg-japan`, `0x6` `gg-export`, `0x7` `gg-international` |
| `smsimage.SIZES`                                   | Size nibble to bytes: `0xA` 8K, `0xB` 16K, `0xC` 32K, `0xD` 48K, `0xE` 64K, `0xF` 128K, `0x0` 256K, `0x1` 512K, `0x2` 1M    |
| `smsimage.BARE`, `smsimage.STUBBED`                | The two values `dump.form` returns                                                                                          |
| `smsimage.AUTHORITATIVE`                           | `"sha256"`, the one value that decides                                                                                      |
| `smsimage.VERDICTS`                                | The five verdicts, in the order `match` tries them                                                                          |
| `smsimage.Manifest`, `smsimage.Match`              | The manifest and its answer                                                                                                 |
| `smsimage.Malformed`, `smsimage.NoAuthority`       | The two errors                                                                                                              |
| `smsimage.__version__`                             | The installed version                                                                                                       |
| `dump.COPIER_BLOCK`                                | 512                                                                                                                         |
| `identity.CROSS_REFERENCE`                         | `("size", "crc32", "md5", "sha1")`, measured and never deciding                                                             |
| `header.CHECKSUM`, `header.REGION_AND_SIZE`        | Where the checksum word and the region and size byte sit, relative to the anchor: `0x0A` to `0x0B`, and `0x0F`              |
| `header.FIRST_SPAN`, `header.BANKS_FROM_THE_THIRD` | The export boot program's two tables, keyed by size nibble                                                                  |

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

### The doctor

`python3 smsimage/doctor.py`, or `smsimage-doctor` after a pip install, takes no arguments. It reports on the machine: the interpreter, the output and default encodings, filesystem case, line endings, path length, free space and git. It then drives the package against an image it assembles: it strips a copier block, finds a planted header, reproduces a sealed checksum, measures the image, parses [`artifacts.manifest.json`](artifacts.manifest.json) and reads [`conformance/corpus.json`](conformance/corpus.json). A corpus holding nothing is reported apart from a corpus that is not there. It exits 0 when all 9 package checks pass and 1 otherwise.

## What a real library actually contains

Sega's _Software Reference Manual for the SEGA Mark III Console_ prints the header on its page 22, and [`conformance/hardware.json`](conformance/hardware.json) holds every fact it states with the sentence it came from. It is a retyped copy whose typist is not recorded. Where it and the cartridges disagree the cartridges win, and [`conformance/divergences.json`](conformance/divergences.json) carries each disagreement with its measurement. Every figure below was measured across the Master System, Game Gear and SG-1000 libraries the census was run on, keyed on the SHA-256 of the image bytes, so a count is a count of images rather than of filenames.

| Measurement                                            | Count |
| :----------------------------------------------------- | ----: |
| Archive entries read                                   | 5,425 |
| Distinct images                                        | 2,922 |
| Duplicate listings of an image already seen            | 2,503 |
| Header at `0x7FF0` only                                | 2,450 |
| Header at `0x3FF0` / `0x1FF0`                          | 8 / 5 |
| Header at both `0x3FF0` and `0x7FF0`, read at `0x7FF0` |     3 |
| No header at any candidate offset                      |   456 |
| Carrying a 512-byte copier block                       |    17 |

Five things in there break a reader written from a description.

**A header is not universal.** 456 images carry none, and only 76 of those are too short to hold one at `0x7FF0`. 205 of them are the retail SG-1000 cartridges, none of which carries a header: they are the control that catches a header finder saying yes to everything. So every query answers `None` rather than raising.

**The magic appears where no header is.** Read as raw files, 141 images carry `TMR SEGA` outside the three candidate offsets. 16 of those are copier-blocked images whose header sits at `0x81F0` until the block is removed. The rest sit at bank boundaries, which is what a multi-cart or an overdump looks like. Only the three candidates are searched.

**Three images carry the magic at two candidates.** The largest wins, and `anchors_in` reports every match so a caller sees the ambiguity.

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

**The two bytes after the magic are not reserved.** The manual prints them as two spaces, `20 20`, and only 400 of the 2,466 headers carry them. `00 00` appears on 1,149 and `FF FF` on 527, with a long tail after that. The export and Game Gear boot programs both compare eight bytes, `TMR SEGA`, and so does this package. `python3 -m conformance.divergences <library>` measures these.

**A Game Gear cartridge usually stores no checksum.** Of the 1,105 distinct images in the Game Gear set that carry a header, 1,018 store the value zero and 48 reproduce the rule, as `python3 -m conformance.divergences` measures over that set alone. The Game Gear boot program looks for `TMR SEGA` at the three addresses and checks nothing else, so nothing on that console ever read the stored value. `header.agrees` answers `False` for those, and that is a statement about the console rather than about the file.

The manual prints the size codes up to 256K, each with region nibble `0x4`. The export boot program decodes nine size codes, 512K and 1M among them, and checks the sum only on region `0x4`. The other region nibbles are named the way the emulation community names them, which no Sega document confirms. The census agrees with that naming: region `0x4` dominates the Master System images and `0x5` to `0x7` the Game Gear ones. 49 images carry a region nibble no reading accounts for and 3 a size nibble, and those resolve to `None` rather than to the nearest plausible value.

## The checksum rule

The rule is the one the export boot programs run, read out of the v1.3 program declared in [`artifacts.manifest.json`](artifacts.manifest.json). Each size code names a first span, `0x1FF0`, `0x3FF0`, `0x7FF0` or, for 48K, `0xBFF0`, and the bytes below it are summed. From 64K up, whole 16K banks from the third onward are added: 2 for 64K, 6 for 128K, 14 for 256K, 30 for 512K and 62 for 1M. The low sixteen bits are kept. `python3 -m conformance.boot <program> [program ...]` reads both tables, the eight-byte compare and the region gate out of each declared program that runs the sum and checks them against this package. Nine do, and all nine read the same first spans and the same bank counts up to 512K. For 1M they split: v1.3 and five others read 62 banks, while Hang On v3.4, Hang On & Safari Hunt v2.4 and Missile Defense 3-D v4.4 read 33, and no image in the library tells the two apart. The manual says to leave out only the two checksum bytes, and that reading reproduces the stored value on none of the 2,463 images.

| Population                                                                                                                |     Reproduced |
| :------------------------------------------------------------------------------------------------------------------------ | -------------: |
| Retail Master System cartridges, the four region folders of the Master System set, by `python3 -m conformance.categories` |     370 of 393 |
| Every image in the Master System set with a header and a size the reading knows, modified ones included                   |   925 of 1,331 |
| Every image with a header and a size the reading knows                                                                    | 1,011 of 2,463 |

A modified image disagrees for a reason that belongs to the modification: translations reproduce the rule on 78 of 301 and hacks on 33 of 129, as `python3 -m conformance.categories` measures. That is why the census reports agreement as an observation rather than gating on it.

No other boot program explains the 23 retail cartridges that do not reproduce. 16 of them carry a region nibble other than `0x4`, and none of the nine programs checks the sum on those. The other 7 declare 32K, 128K or 256K, where all nine read the same table.

## The census, and why its output can ship

[`conformance/census.py`](conformance/census.py) walks a library you own: directories, zip archives and single `.sms`, `.gg` and `.sg` files.

```bash
python3 -m conformance.census /path/to/library.zip /path/to/another
```

It counts each distinct image once by SHA-256, checks six properties on every one, reports one observation, and writes [`conformance/corpus.json`](conformance/corpus.json): 151 combinations of form, length, anchor, region, declared size and whether the stored checksum reproduced, each with a count. No title and no content, so nothing in it could rebuild any part of any cartridge.

| Exit code | When                                             |
| :-------- | :----------------------------------------------- |
| 0         | Every property held on every image               |
| 1         | A property broke, or a path given does not exist |
| 2         | No path was given                                |

The six properties are invariants between functions that agree by construction today. Each test replaces one side of the pair it guards and watches the property fire, so all six have been seen to catch the drift they exist for.

Given no image, the census says it examined nothing and leaves the existing corpus alone rather than overwriting it with an empty one.

## Is it right

Every fact the manual prints that a test can reach is held to the code. [`conformance/hardware.json`](conformance/hardware.json) carries each fact with its sentence and page, and [`conformance/hardware.test.py`](conformance/hardware.test.py) compares them with the constants in the package. `python3 -m conformance.quotes` finds every quoted sentence in the manual, once `python3 -m conformance.documents` has fetched it.

`python3 -m conformance.corpus` replays the 151 combinations in [`conformance/corpus.json`](conformance/corpus.json) against the package with no library present, and the suite checks the headline counts against that file. `python3 -m conformance.speed` holds the checksum of a 256K image to a floor of 130 per second.

The boot programs a reader may need are declared in [`artifacts.manifest.json`](artifacts.manifest.json) by size, CRC32, SHA-1 and SHA-256. None of them is in this repository and nothing here says where to obtain one. [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) lists the 3 things no Sega source settles, and what would settle each.

## Working on it

| Need                                                            | Where                                                                    |
| :-------------------------------------------------------------- | :----------------------------------------------------------------------- |
| Every gate and the order to run them                            | [CONTRIBUTING.md](CONTRIBUTING.md)                                       |
| The same material for a coding agent                            | [AGENTS.md](AGENTS.md)                                                   |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md)                                                   |
| Bug reports                                                     | [GitHub Issues](https://github.com/gufranco/sms-rom-image-python/issues) |
| Security reports                                                | [SECURITY.md](SECURITY.md)                                               |

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

Each module has a test file beside it, named after it, and each runs on its own. Coverage is a hard gate at 100% statement and branch. Every worked example in this readme is run by [`conformance/readme.test.py`](conformance/readme.test.py) and its output compared with what is printed here.

## References

- _Software Reference Manual for the SEGA Mark III Console_, Sega, undated, page 22, retyped by an unnamed hand. 45 pages, 184,840 bytes, SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`. Read for the header layout, the opening string, the checksum bytes and the size codes. It is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf into `docs/` and refuses any other file. Every URL in this readme is checked weekly.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
