# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

## What this project is, in one paragraph

A package that reads Master System, Game Gear and SG-1000 cartridge images as
files: it removes a copier block, finds the header at one of three addresses,
reads the region and size it declares, and computes the checksum to compare with
the one the cartridge carries. What the header means comes from Sega's reference
manual; what real cartridges contain comes from a census of 2,610 distinct
images, and the two are not the same thing.

## The interface a caller drives

Four modules, in the order a caller needs them:

- `dump.read(path)` reads a file and removes a 512-byte copier block when one is
  there. `dump.form` says which form the bytes were in.
- `header.anchor_of(image)` finds the header, the largest candidate first, and
  `header.anchors_in` reports every match so an ambiguity is visible.
  `header.region_of`, `header.declared_size`, `header.carried`,
  `header.checksum` and `header.agrees` answer `None` rather than raising when
  there is no header.
- `identity.measure(data)` publishes the size and the digests, and SHA-256 alone
  decides.
- `Manifest(document)` matches a supplied file and, on a miss, says which miss it
  is rather than printing a digest.

Everything the package raises lives in
[`smsimage/errors.py`](smsimage/errors.py) and nowhere else.

There is no clock. These are files.

## The authority ladder

1. **[`conformance/hardware.json`](conformance/hardware.json)**, Sega's
   *Software Reference Manual for the SEGA Mark III Console*, pinned by digest
   and quoted fact by fact from its page 22. It decides where the header sits,
   the string it opens with, where the checksum is kept and the size codes it
   prints.
2. **A cartridge image.** The manual is a retyped instruction to licensees, so a
   genuine cartridge can disagree with it and still be genuine. Where one does,
   the cartridge is the fact.
3. **Nothing else.**

[`conformance/divergences.json`](conformance/divergences.json) records every
place they part.

## What is settled and what is not

**Settled: every combination a real library contains.** 145 of them, replayed
from [`conformance/corpus.json`](conformance/corpus.json) with no failures, over
2,610 distinct images.

**Settled: what the manual states about the header.** Pinned in
[`conformance/hardware.json`](conformance/hardware.json) and held to this
package's constants by
[`conformance/hardware.test.py`](conformance/hardware.test.py).

**Not settled: 2 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
what would close it. Do not close one by argument.

## The manual's checksum sentence is not the rule

The manual says the checksum covers the ROM with only `$7FFA` and `$7FFB` left
out. Read that way it reproduces the stored value on 0 of 2,418 images. The rule
here is the one the v1.3 export boot program runs: a first span the size code
picks from its table, then whole 16K banks from the third on. It reproduces 971.
A 48K declaration sums through the header and stops short of its own last
sixteen bytes, because that is what the program's table says.

**If you are about to change the checksum, run
`python3 -m conformance.boot <the v1.3 program>` and
`python3 -m conformance.divergences <library>` before and after.**

## Every gate, in the order to run them

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for f in $(find smsimage conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Then the ones outside the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
python3 -m conformance.documents
python3 -m conformance.quotes
```

And, with a library present, the two that walk it:

```bash
python3 -m conformance.census <library> [library ...]
python3 -m conformance.divergences <library> [library ...]
python3 -m conformance.categories <the Master System set>
```

Everything under [`conformance/`](conformance) runs as a module. Run as a
script, its own directory goes on the import path and a file there shadows any
standard library module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source, and a docstring counts as one. Names, small functions, constants and types carry what a comment would have said |
| Test layout | `<module>.test.py` beside the module it covers |
| Test shape | Arrange, act, assert, each opened by its bare marker |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class |
| Package manager for tooling | pnpm, never npm |
| Commits | Conventional Commits, subject at most 50 characters |
| Documents | Read, quoted and pinned by digest. Never committed |
| Cartridges and boot programs | Never committed, in any form, for any reason |

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here:

- `N818`: some exceptions are control flow signals rather than failures, and
  CPython names its own that way, such as `StopIteration`. The ones that report
  a failure do end in `Error`.
- `N999` in tests: a test file is named after the module it sits beside, so its
  name carries a dot. A module and its tests are read together.
- `T201` in the conformance tools: these are command line tools and printing is
  their output. A logger would put a level and a timestamp in front of a report
  meant for a person.
- `BLE001` and `T201` in `environment.py`: it reports what a machine is, so a
  check that throws has to become a line in the report rather than end the run.
- `BLE001` and `T201` in the doctor: it has to survive whatever a check throws
  and report it. A narrower catch would let an unforeseen failure escape as a
  traceback and take the rest of the report with it.
- The optional error classes in mypy: in a model of hardware the errors that
  matter are a width, a mask or a `None` crossing a boundary, and those classes
  catch exactly that.
- `if __name__ == "__main__":` in the coverage exclusions: the guard hands argv
  to a function that is itself tested, and importing the module to cover it
  would run the tool rather than test it.
- `if TYPE_CHECKING:` in the coverage exclusions: the block never runs. Python
  3.14 drops it before coverage sees it and earlier versions do not, so
  counting it would make the gate mean one thing on the newest runtime and
  another on the oldest.
- The two ellipsis patterns in the coverage exclusions: a protocol method has no
  body to run, whether the ellipsis sits on its own line or after the
  signature. The same version split applies.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.
- `@unittest\.skipUnless\(A_PART,`,
  `@unittest\.skipUnless\(A_PART and BUILDABLE,` and
  `^def accounts_for_a_reset\(` in the coverage exclusions: this member is not a
  part, so the family tests that build a `Chip` and account for its reset are
  skipped here and their bodies never run.
- `@unittest\.skipUnless\(VARIANTS,` and `^def built\(` in the coverage
  exclusions: this package names no variants, so the family test that finds each
  one built in the readme is skipped here.
- `@unittest\.skipUnless\(SOLD_AS_A_COMPONENT,`, `^def machine_mentions\(` and
  `^def listing\(` in the coverage exclusions: this part only existed inside one
  machine, so the family sweep for machine names is skipped here.

## Layout

```
smsimage/
  dump.py        copier blocks
  header.py      the header, its region, its size and its checksum
  identity.py    size and digests, and which one decides
  manifest.py    matching a supplied file, and diagnosing a miss
  errors.py      everything this package raises
  doctor.py      what the machine and the package look like, for a report
  environment.py what the doctor reads about the machine
  version.py     rewritten by the release job and by nothing else
conformance/
  census.py         walks a library you own and checks six properties on all of it
  corpus.json       145 combinations covering 2,610 distinct images
  corpus.py         replays every combination against the package
  documents.json    the manual, by digest
  documents.py      brings it down and refuses any other file
  hardware.json     Sega's manual, pinned fact by fact
  divergences.json  every place a cartridge and the manual part
  divergences.py    measures what the corpus cannot hold
  categories.py     the same measurements per folder, and for the retail set
  boot.py           the export boot program's tables, checked against the package
  manual.py         the manual's text, laid flat for matching
  quotes.py         every quote the records carry, found in the manual word for word
  links.py          the weekly check that every cited address still answers
  speed.py          the throughput floor
  package.py        the wheel audit
  source.py         the check that no documentation string remains
  family_*.test.py  the family standard, held as tests, one topic a file
  family_member.py  what this member answers to them
  family_shared.py  what more than one of them reads
```

## Things that will bite you

**`dump.read` already strips the copier block.** To ask what form a file was in,
read the bytes yourself and pass them to `dump.form`.

**Count over stripped images.** A figure taken over raw files counts sixteen
copier-blocked headers at `0x81F0` and lands near, but not on, every other
figure. The readme once carried three such numbers.

**A Game Gear image storing zero is not a failed checksum.** 1,018 of the 1,105
Game Gear images with a header store zero, and `header.agrees` answers `False`
for every one of them. The census reports agreement as an observation for that
reason.

**The two bytes after `TMR SEGA` are not part of the match.** The manual prints
them as spaces and only 399 of 2,421 headers carry them.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them. Read it before adding a surface, and read
it again before saying a change is done.

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A census that walked no file
exits zero exactly like one that walked a library, which is why it prints what it
read and says so when the answer is nothing.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to the header reading or the
checksum also runs the census and the divergence measurement over a real
library, because the properties are internal and a rule wrong the same way every
time passes all of them.
