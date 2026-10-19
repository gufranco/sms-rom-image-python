# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The authority above everything else is a Sega manual that a person
retyped; below it sit Sega's own boot programs, which are the code that actually
reads a header, and 2,922 distinct cartridge images.

The settled surface is 151 distinct combinations replayed from the corpus with no
failures, six properties checked on every one of 2,922 images, every constant
here held against the sentence Sega printed, and the checksum rule and size
tables held against the nine export boot programs that run the sum. What
follows is the residue.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why a library cannot close these

A retail cartridge is the strongest evidence there is about what was built, and
it says nothing about what was specified. Where neither the manual nor a boot
program speaks, a library tells you what shipped and not what the rule was.

## What would settle them

A Sega document printing the region codes and the size codes above 256K,
ideally the same manual in a printed copy rather than a retyped one.

## Where no Sega source names it

### The region codes other than 4.

**The document says.** Every size code it prints carries a high nibble of 4.

Source: Sega, _Software Reference Manual for the SEGA Mark III Console_, page 22.

**What the boot programs do.** The export one checks the sum only on region 4
and fails every other; the Japanese one never looks for a header; the Game
Gear's ignores the region. None of them names 3, 5, 6 or 7.

**What the cartridges do.** Carry 3 on 31 images and 5, 6 and 7 on 1,006 Game
Gear images.

**What this project follows.** The cartridges, read as a Japanese Master System
and the three Game Gear regions.

**Why.** Those codes appear on those cartridges and on no others.

**What would settle or reopen it.** A Sega document for the Game Gear or the
Japanese Master System that prints the region codes.

### Who retyped the manual, and from which printing.

**The document says.** Its footer reads "Sega Mk3 Hardware Reference Manual
(Rev1)". Nothing records who typed it.

**What this project follows.** The manual, at rung 1, with that caveat recorded
beside its digest in [`conformance/documents.json`](conformance/documents.json).
Where the boot programs disagree with it, they decide.

**Why.** It is the only Sega text about the header that has been located.

**What would settle or reopen it.** A scan of a Sega printing to compare the
retyped page against.

### How many banks size code 2 adds.

**The document says.** Nothing. The largest size code it prints is 256K.

Source: Sega, _Software Reference Manual for the SEGA Mark III Console_, page 22.

**What the boot programs do.** Nine declared programs run the sum, and every one
reads code 2's bank count from the first byte of the instruction after its
four-entry bank table, the one it jumps to once the sum agrees. The v1.0
prototype, v1.3, the store display unit, Sonic The Hedgehog and both Alex Kidd
in Miracle World programs read 62. Hang On v3.4, Hang On & Safari Hunt v2.4 and
Missile Defense 3-D v4.4 read 33. `python3 -m conformance.boot` reads both.

**What the cartridges do.** Two images declare code 2, and neither is long
enough for 33 and 62 banks to sum differently.

**What this project follows.** The v1.3 program: 62 banks, 1M.

**Why.** It is the program the rest of the rule was read from, and no image
separates the two counts.

**What would settle or reopen it.** A 1M image declaring code 2 under region 4
whose stored sum agrees with one count and not the other, or a Sega document
naming the bank count for 1M.

## What is not in question

So the boundary is visible rather than implied:

- **Every combination a real library contains.** 145 of them, replayed with no
  failures, measured across 2,922 distinct images.
- **Where the header sits, the string it opens with and where the checksum is
  kept.** From Sega's manual, pinned fact by fact in
  [`conformance/hardware.json`](conformance/hardware.json) with the sentence and
  the page, and held to this package's constants by
  [`conformance/hardware.test.py`](conformance/hardware.test.py).
- **Which bytes the checksum covers.** The v1.3 export boot program sums the span
  its table gives the size code and then whole 16K banks from the third on.
  [`conformance/boot.py`](conformance/boot.py) reads both tables out of it and
  out of the eight other programs that run the sum, and all nine agree on every
  first span. Read literally, the manual's sentence reproduces 0 of 2,463 stored
  values; the boot program's rule reproduces 1,011.
- **Size code 1.** Every program that runs the sum counts 30 banks for it: 512K.
- **Why 23 of 393 retail Master System cartridges do not reproduce their sum.**
  16 carry a region nibble other than 4, which no program on disk checks. The
  other 7 declare sizes where all nine programs read the same table.
- **How long the opening string is.** Eight bytes. The export and Game Gear boot
  programs both compare eight, and only 400 of 2,466 headers carry the two
  spaces the manual prints after them.
- **Whether a Game Gear checks the checksum.** It does not. Its boot program
  compares `TMR SEGA` at the three addresses and nothing else, which is why
  1,018 of the 1,105 Game Gear images with a header store zero.
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
