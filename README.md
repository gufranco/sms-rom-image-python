# SMS ROM Image

A Sega Master System, Game Gear or SG-1000 cartridge image as a file: what the dumper added, what the header declares, and which wrong a wrong file is.

[![CI](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sms-rom-image-python/actions/workflows/ci.yml)

**2,610** distinct images measured from **5,111** archive entries, the header read at `0x7FF0` on **2,408** of them, the stored checksum reproduced on **370** of **397** retail Master System cartridges, **14** boot programs declared by digest, **441** tests, **100%** statement and branch coverage, no dependencies

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

The copier block was recognised by its length and removed, the header was found where a 32 KB cartridge keeps it, and the checksum this package computes matches the one sealed into the image.

## Install

```bash
pip install git+https://github.com/gufranco/sms-rom-image-python.git
```

Python 3.12 or newer. Nothing else at runtime. There is no submodule, so a plain clone and the download-zip link both produce a checkout that runs.

## The interface

Four modules, answering four questions in the order they have to be asked.

| Module | Question |
|:--|:--|
| [`dump`](smsimage/dump.py) | What did the dumping device add |
| [`identity`](smsimage/identity.py) | What makes this file itself, and which value decides |
| [`header`](smsimage/header.py) | What does the cartridge say about itself, and where |
| [`manifest`](smsimage/manifest.py) | When a reader supplies the wrong file, which wrong is it |

| Call | Does | Returns |
|:--|:--|:--|
| `dump.read(path)` | Reads a dump, removing a copier block when there is one | `bytes` |
| `dump.form(data)` / `dump.strip_copier_stub(data)` | Which of the two shapes a file has, and the image behind it | a name / `bytes` |
| `identity.measure(data)` | Size, CRC32, MD5, SHA-1 and SHA-256 | a mapping |
| `identity.agrees(found, expected)` | Whether the one value that decides matches | `bool` |
| `header.anchor_of(image)` / `header.anchors_in(image)` | Where the header sits, and every candidate that matched | an offset or nothing / offsets |
| `header.region_of(image)` / `header.declared_size(image)` | What the header declares, or nothing when it declares a value no reading knows | a name / bytes |
| `header.carried(image)` / `header.checksum(image)` | The checksum the cartridge stored, and the one its bytes produce | `int` or nothing |
| `header.agrees(image)` | Whether the two match, or nothing when there is nothing to compare | `bool` or nothing |
| `Manifest(document)` / `manifest.read(path)` | What a project expects a reader to supply | a `Manifest` |
| `Manifest.match(key, data)` | Which of five answers a supplied file is | a `Match` |

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

A record carrying no SHA-256 is refused with `NoAuthority` rather than graded on whichever weaker value it does carry.

Everything the package raises lives in [`smsimage/errors.py`](smsimage/errors.py): `Malformed` and `NoAuthority`. Both are published, because `except` takes a name and one that cannot be imported can only be handled by catching everything.

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

The fifth answer is a known bad dump, declared separately in a manifest so a corrupt file is diagnosed as corrupt rather than as the wrong file.

## What a real library actually contains

Sega's *Software Reference Manual for the SEGA Mark III Console* prints the header on its page 22, and [`conformance/hardware.json`](conformance/hardware.json) holds every fact it states with the sentence it came from. It is a retyped copy whose typist is not recorded, and where it and the cartridges disagree the cartridges win; [`conformance/divergences.json`](conformance/divergences.json) carries each disagreement with its measurement. Every figure below was measured across the Master System and Game Gear libraries the census was run on, keyed on the SHA-256 of the image bytes so a count is a count of images rather than of filenames.

| Measurement | Count |
|:--|--:|
| Archive entries read | 5,111 |
| Distinct images | 2,610 |
| Duplicate listings of an image already seen | 2,501 |
| Header at `0x7FF0` only | 2,406 |
| Header at `0x3FF0` / `0x1FF0` | 8 / 5 |
| Header at both `0x3FF0` and `0x7FF0`, read at `0x7FF0` | 2 |
| No header at any candidate offset | 189 |
| Carrying a 512-byte copier block | 17 |

Five things in there are traps for a reader written from a description.

**A header is not universal.** 189 images carry none, and only 18 of those are too short to hold one. An image with no header is a normal state, so every query answers nothing rather than raising.

**The magic appears where no header is.** Read as raw files, 141 images carry `TMR SEGA` outside the three candidate offsets. 16 of those are copier-blocked images whose header sits at `0x81F0` until the block is removed; the rest sit at bank boundaries, which is what a multi-cart or an overdump looks like. Only the three candidates are searched.

**Two images carry the magic at two candidates.** The largest wins, and `anchors_in` reports every match so a caller can see the ambiguity rather than have it hidden.

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

**The two bytes after the magic are not reserved.** The manual prints them as two spaces, `20 20`, and only 399 of the 2,421 headers carry them. `00 00` appears on 1,107 and `FF FF` on 525, with a long tail after that, so only the eight bytes `TMR SEGA` are looked for. `python3 -m conformance.divergences <library>` measures these.

**A Game Gear cartridge usually stores no checksum.** Of the 1,084 that carry a header, 1,001 store the value zero and 43 reproduce the rule, because its boot path does not check one. `header.agrees` answers `False` for those, and that is a statement about the console rather than about the file.

The manual prints the size codes up to 256K, each with region nibble `0x4`. The other region nibbles and the 512K and 1M size codes are read the way the emulation community reads them, which no Sega document confirms. The distribution corroborates it: region `0x4` dominates the Master System images and `0x5` to `0x7` the Game Gear ones. 49 images carry a region nibble no reading accounts for and 3 a size nibble, and those resolve to nothing rather than to the nearest plausible value.

## The checksum rule

Sum every byte up to the header, then from just past the header to the size the header declares, and keep the low sixteen bits. The manual says to leave out only the two checksum bytes, and that reading reproduces the stored value on none of the 2,418 images.

| Population | Reproduced |
|:--|--:|
| Retail Master System cartridges | 370 of 397 |
| Every Master System image, modified ones included | 922 of 1,337 |
| Every image with a header and a size the reading knows | 965 of 2,418 |

A modified image disagrees for a reason that belongs to the modification: translations reproduce the rule 31% of the time and other modified images 19%. That is why the census reports agreement as an observation rather than gating on it.

## The census, and why its output can ship

[`conformance/census.py`](conformance/census.py) walks a library you own, inside directories or zip archives:

```bash
python3 -m conformance.census /path/to/library.zip /path/to/another
```

It gates on six properties that must hold on every image, reports one observation, and writes [`conformance/corpus.json`](conformance/corpus.json): 144 combinations of form, length, anchor, region, declared size and whether the stored checksum reproduced, each with a count. No title and no content, so nothing in it could rebuild any part of any cartridge.

The six properties are invariants between functions that agree by construction today. Each test replaces one side of the pair it guards and watches the property fire, so all six have been seen to catch the drift they exist for.

Given no library, the census says it examined nothing and leaves the existing corpus alone rather than overwriting it with an empty one.

## Is it right

[`smsimage/doctor.py`](smsimage/doctor.py) looks at the machine and drives the package against an image it assembles:

```bash
python3 smsimage/doctor.py
```

It removes a copier block, finds a planted header, reproduces a sealed checksum and measures an image, then reports on the manifest and the corpus. A corpus holding nothing is told apart from a corpus that is not there. Paste its output into any issue.

The boot programs a reader may need are declared in [`artifacts.manifest.json`](artifacts.manifest.json) by size, CRC32, SHA-1 and SHA-256. None of them is in this repository and nothing here says where to obtain one.

## Working on it

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

Coverage is gated at 100% of statements and branches. Every worked example in this readme is run by [`conformance/readme.test.py`](conformance/readme.test.py) and its output compared with what is printed here.

| Path | Holds |
|:--|:--|
| [`smsimage/`](smsimage) | The package, each module with its tests beside it |
| [`conformance/`](conformance) | The census, its corpus, and the checks on this repository's own claims |
| [`artifacts.manifest.json`](artifacts.manifest.json) | The boot programs, by digest |
| [`FAMILY.md`](FAMILY.md) | The standard every member of the family is built to |

Releases are cut by semantic-release from Conventional Commit subjects. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## References

| Document | Read for | Identity |
|:--|:--|:--|
| *Software Reference Manual for the SEGA Mark III Console*, Sega, undated, page 22, retyped by an unnamed hand, at https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf | The header layout, the opening string, the checksum bytes and the size codes | SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`, 184,840 bytes |

`python3 -m conformance.documents` brings it down into `docs/` and refuses any file whose digest differs; it is never carried here. Every address in this readme is asked weekly whether it still answers.

## Citing this

See [`CITATION.cff`](CITATION.cff).

## License

MIT. See [`LICENSE`](LICENSE).
