# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The authority above everything else is a Sega manual that a person
retyped; below it sit Sega's own boot programs, which are the code that actually
reads a header, and 2,610 distinct cartridge images.

The settled surface is 145 distinct combinations replayed from the corpus with no
failures, six properties checked on every one of 2,610 images, every constant
here held against the sentence Sega printed, and the checksum rule and size
tables held against the export boot program they were read from. What follows
is the residue.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Why a library cannot close these

A retail cartridge is the strongest evidence there is about what was built, and
it says nothing about what was specified. Where neither the manual nor a boot
program speaks, a library tells you what shipped and not what the rule was.

## What would settle both of them

A Sega document printing the region codes, ideally the same manual in a printed
copy rather than a retyped one.

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

## What is not in question

So the boundary is visible rather than implied:

- **Every combination a real library contains.** 145 of them, replayed with no
  failures, measured across 2,610 distinct images.
- **Where the header sits, the string it opens with and where the checksum is
  kept.** From Sega's manual, pinned fact by fact in
  [`conformance/hardware.json`](conformance/hardware.json) with the sentence and
  the page, and held to this package's constants by
  [`conformance/hardware.test.py`](conformance/hardware.test.py).
- **Which bytes the checksum covers.** The v1.3 export boot program sums the span
  its table gives the size code and then whole 16K banks from the third on.
  [`conformance/boot.py`](conformance/boot.py) reads both tables out of it.
  Read literally, the manual's sentence reproduces 0 of 2,418 stored values;
  the boot program's rule reproduces 971.
- **The size codes above 256K.** The same program's bank table counts 30 banks
  for code 1 and 62 for code 2: 512K and 1M.
- **How long the opening string is.** Eight bytes. The export and Game Gear boot
  programs both compare eight, and only 399 of 2,421 headers carry the two
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
