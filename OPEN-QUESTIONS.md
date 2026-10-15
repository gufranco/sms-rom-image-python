# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The authority above everything else is a Sega manual that a person
retyped, and the second rung is 2,610 distinct cartridge images. Most of the
entries are places the manual is silent or wrong and the cartridges are not.

The settled surface is 144 distinct combinations replayed from the corpus with no
failures, six properties checked on every one of 2,610 images, and every
constant here held against the sentence Sega printed. What follows is the
residue.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why a library cannot close these

A retail cartridge is the strongest evidence there is about what was built, and
it says nothing about what was specified. Where the manual is silent, a library
tells you what shipped and not what the rule was, so a pattern that holds across
two thousand images is still a pattern rather than a rule.

## What would settle almost all of them

The boot programs. Fourteen are declared by digest in
[`artifacts.manifest.json`](artifacts.manifest.json), and a boot program is the
thing that actually reads the header: which bytes it compares, which range it
sums and which codes it accepts are in its code. Reading them is the work this
list is waiting on.

## Where the manual and the cartridges part

### Which bytes the stored checksum covers.

**The document says.** Every byte of the ROM except the two that hold the
checksum.

Source: Sega, *Software Reference Manual for the SEGA Mark III Console*, page 22.

**What the cartridges do.** Read that way, no image in the library reproduces its
stored value: 0 of 2,418. Leaving out the whole sixteen-byte header and summing
up to the declared size reproduces 965 of them, 370 of the 393 retail Master
System cartridges among them.

**What this project follows.** The cartridges.

**Why.** A rule that reproduces nothing cannot be the rule the licensees' tools
applied.

**What would settle or reopen it.** The checksum routine of an export boot
program, which names the range it sums. The 23 retail cartridges the package rule
misses are where to look first.

### The region codes other than 4.

**The document says.** Every size code it prints carries a high nibble of 4.

Source: Sega, *Software Reference Manual for the SEGA Mark III Console*, page 22.

**What the cartridges do.** Carry 3 on 31 images and 5, 6 and 7 on 1,006 Game
Gear images.

**What this project follows.** The cartridges, read as a Japanese Master System
and the three Game Gear regions.

**Why.** Those codes appear on those cartridges and on no others.

**What would settle or reopen it.** A Sega document for the Game Gear or the
Japanese Master System, or a boot program that branches on the nibble.

### The size codes above 256K.

**The document says.** Nothing above 256K.

Source: Sega, *Software Reference Manual for the SEGA Mark III Console*, page 22.

**What the cartridges do.** Carry a low nibble of 1 on 17 images and 2 on 2.

**What this project follows.** The cartridges, read as 512K and 1M, which makes
13 of the 17 and 1 of the 2 reproduce their checksum.

**Why.** No other reading of those two codes makes the sums come out.

**What would settle or reopen it.** A Sega document printing the codes, or a boot
program that decodes them.

## Where nothing has been read at all

### Whether a Game Gear checks the checksum.

**The document says.** Nothing. The manual describes the Mark III alone.

**What the cartridges do.** 1,018 of the 1,105 distinct images in the Game Gear
set that carry a header store zero where the checksum goes, and 44 reproduce the
rule.

**What this project follows.** Neither: `header.agrees` answers `False` for an
image storing zero, and the census reports agreement as an observation rather
than gating on it.

**Why.** A zero on a thousand retail cartridges is consistent with a console that
never checks, and that consistency is all the evidence there is.

**What would settle or reopen it.** The Game Gear boot program declared in the
manifest, read for a checksum comparison.

### Who retyped the manual, and from which printing.

**The document says.** Its footer reads "Sega Mk3 Hardware Reference Manual
(Rev1)". Nothing records who typed it.

**What this project follows.** The manual, at rung 1, with that caveat recorded
beside its digest in [`conformance/documents.json`](conformance/documents.json).

**Why.** It is the only Sega text about the header that has been located.

**What would settle or reopen it.** A scan of a Sega printing to compare the
retyped page against.

## What is not in question

So the boundary is visible rather than implied:

- **Every combination a real library contains.** 144 of them, replayed with no
  failures, measured across 2,610 distinct images.
- **Where the header sits, the string it opens with, where the checksum is kept,
  and the size codes up to 256K.** From Sega's manual, pinned fact by fact in
  [`conformance/hardware.json`](conformance/hardware.json) with the sentence and
  the page, and held to this package's constants by
  [`conformance/hardware.test.py`](conformance/hardware.test.py).
- **Which of the published values decides.** SHA-256, and only it.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **Copier blocks as a specified thing.** They are a product of hardware Sega did
  not sell, so there is no document to be faithful to. What this package knows
  about them came from the library.
- **The serial number and revision byte.** The manual names them and nothing in
  this package reads them.
- **Anything with a clock.** These are files.
- **Any cartridge content.** The corpus carries combinations and counts. Nothing
  in it could rebuild any part of any image.
