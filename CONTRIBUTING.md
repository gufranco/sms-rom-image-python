# Contributing

## The short version

Evidence over assertion. A change that claims something is correct carries the
run that shows it, and a claim that cannot be checked is not ready.

## Before you open a pull request

Run every gate. The exit code decides; the output says what was found:

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 coverage)
"${cov[@]}" erase
for f in $(find smsimage conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$f" || echo "FAILED $f"
done
"${cov[@]}" report
```

Run them at the versions the pipeline pins rather than whatever `python3` resolves to. A machine whose default interpreter moved on reports every suite as failing for want of a tool, which reads as broken code. The search is limited to the two source directories so a stale `build/` copy of the package is never collected.

There is no submodule. A plain clone runs as it stands, and the download-zip link
on the repository page produces a checkout that works.

Coverage is a hard gate at 100% statement and branch. A branch with no test fails
the build rather than lowering the number. `mypy` is strict and its findings are
errors.

## If you touch the header offsets, the checksum, or the size rule

Two more things run, and neither is optional.

`conformance/hardware.test.py` holds this package's constants to the record, so a
citation in the documentation is a check that can fail rather than a claim in
prose. It needs no cartridges and runs in CI.

The census needs a library you own, so it runs on your machine and not on a
runner:

```bash
python3 -m conformance.census "/path/to/your/library"
```

Paste the lines that matter. A change that leaves every test passing and moves an
observation down is still a regression, because the properties only ask whether
the code agrees with itself, and a rule wrong the same way every time passes all
of them.

Deduplicate by digest before reporting a count. A library organised by series
lists the same image several times, and a file count reported as an image count
is a number that is not a measurement.

## Tests

A test file sits beside the module it covers and is named after it. Test bodies
carry no comments: arrange, act and assert are separated by one blank line each,
and the test name says what behaviour is being pinned.

Tests that need a file nobody can distribute are skipped rather than passed when
that file is absent, and they live apart from the rest so the coverage gate stays
meaningful on a runner that has nothing.

## Commits

Conventional Commits, subject under fifty characters, imperative mood. The body
explains what changed and why, wrapped at seventy two columns. Releases are cut
by semantic-release from those subjects, so the type is what decides the version.

## What will be sent back

- A file nobody can legally redistribute, or a digest of one fine enough to
  reconstruct it. Whole-file digests are welcome; per-block ones are not.
- A number in a document that no run produced.
- A behaviour changed without the corpus or the pinned digests moving with it.
- A test that asserts what the code does rather than what the hardware does.

## What is welcome without asking

Measurements. If you have cartridges or hardware this has not been run against,
the most useful contribution is a run and what it found, especially a
disagreement.
