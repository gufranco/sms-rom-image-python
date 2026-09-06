## What this changes

One or two sentences. What is different afterwards, and why it needed to be.

## How it was checked

Paste the output rather than describing it. A claim that the tests pass is not
evidence that they did.

```text
```

- [ ] `ruff format --check .` and `ruff check .` are clean
- [ ] `mypy` reports nothing
- [ ] Every test file runs, and coverage is 100% of statements and branches
- [ ] Every new check was run once against input that should fail it

## If this changes the header offsets, the checksum, or the size rule

A change here is not checked by the tests alone. Run the census over a library
you own and paste the lines that matter:

```text
  properties held on N of N images
  observations  M of N
```

A change that moves an observation down is a regression even when every test
still passes, because the properties only ask whether the code agrees with
itself, and a rule wrong the same way every time passes all of them.

Deduplicate by digest before quoting a count. A library organised by series
lists the same image several times.

## What it does not carry

- [ ] No cartridge, no fragment of one, and no digest fine enough to rebuild one
- [ ] Nothing that says where to obtain them
