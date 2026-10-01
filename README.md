# uiltiol

[![CI](https://github.com/fitzyracing1/uiltiol/actions/workflows/ci.yml/badge.svg)](https://github.com/fitzyracing1/uiltiol/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

**A tiny text toy: a "bot" walks a file one character at a time, and every `!` makes it leave and hand off to a new bot.**

`bang_bot.py` is a single, dependency-free Python script. Point it at any text file (or let it walk its own source) and
it prints a play-by-play log: each bot reads characters until it hits a `!`, then leaves, spawns a child bot at the next
character, grows the "crease radius" by 1.5x, logs two folds, and syncs the parent's record with the child. When the input
runs out it prints the full lineage of every bot it formed.

It's a playful simulation that prints to your terminal. It doesn't control hardware, run code, or change the files it reads.

## Demo

A real run against [`examples/bangs.txt`](examples/bangs.txt), which contains the single line `hi! go!`:

```text
$ bang-bot examples/bangs.txt
source length=8 bangs=2 cap=8 radius=1.0 growth=1.5
[bot 0 gen 0] enters at index 0 radius=1.00 side=open synced=False (root)
[bot 0] reads 'h' @ 0 r=1.00
[bot 0] reads 'i' @ 1 r=1.00
[bot 0] HITS '!' @ 2 near 'hi!'. leaves.
[bot 0] spawns bot 1. crease radius 1.00 -> 1.50
[bot 0] folds across crease @ 2. child starts on the folded side at 3
[bot 0] folds again across crease @ 2. radius holds at 1.50
[bot 0] syncs with bot 1: radius=1.50 folds=2 crease=2
[bot 1 gen 1] enters at index 3 radius=1.50 side=folded x2 synced=True (parent 0)
[bot 1] reads '·' @ 3 r=1.50
[bot 1] reads 'g' @ 4 r=1.50
[bot 1] reads 'o' @ 5 r=1.50
[bot 1] HITS '!' @ 6 near 'hi! go!'. leaves.
[bot 1] spawns bot 2. crease radius 1.50 -> 2.25
[bot 1] folds across crease @ 6. child starts on the folded side at 7
[bot 1] folds again across crease @ 6. radius holds at 2.25
[bot 1] syncs with bot 2: radius=2.25 folds=2 crease=6
[bot 2 gen 2] enters at index 7 radius=2.25 side=folded x2 synced=True (parent 1)
[bot 2] reaches end. no more bangs. stops.

--- lineage ---
bot 0 gen 0 parent=None radius=1.50 folded=True folds=2 synced=True crease_at=2 left_at=2 children=1
bot 1 gen 1 parent=0 radius=2.25 folded=True folds=2 synced=True crease_at=6 left_at=6 children=2
bot 2 gen 2 parent=1 radius=2.25 folded=True folds=2 synced=True crease_at=6 left_at=None children=none
bots formed: 3
```

Two bangs, three bots: the root leaves at index 2, bot 1 picks up at index 3 and leaves at index 6, and bot 2 starts at
the trailing newline, finds no more bangs, and stops. Spaces are shown as `·`, and newlines are skipped in the log.

## Install

```sh
pip install git+https://github.com/fitzyracing1/uiltiol   # installs the bang-bot command
```

Or skip installing and run the script directly. It only needs the standard library:

```sh
git clone https://github.com/fitzyracing1/uiltiol && cd uiltiol
python3 bang_bot.py
```

You need Python 3.9 or newer.

## Usage

```sh
bang-bot                        # walk the built-in sample snippet
bang-bot some_code.py           # walk any UTF-8 text file
bang-bot --self --max-gen 3     # walk bang_bot.py itself, at most 3 generations
bang-bot notes.txt --delay 0.05 # slow it down so you can watch
```

(`python3 bang_bot.py ...` takes the same arguments.)

| Option | Default | What it does |
|---|---|---|
| `path` | built-in sample | Text file to walk (read as UTF-8) |
| `--self` | off | Walk this script's own source instead |
| `--max-gen N` | `8` | Generation cap. A bot at generation `N` still leaves on `!` but doesn't spawn, so the run ends there |
| `--radius R` | `1.0` | Starting crease radius (must be > 0) |
| `--growth G` | `1.5` | Radius multiplier applied on each spawn (must be > 0) |
| `--delay S` | `0` | Seconds to sleep after each character (must be >= 0) |
| `--version` | | Print the version and exit |

Exit code is `0` on success and `2` for invalid options or an unreadable file.

## How it works

Every bot is a small record (`Bot` dataclass) with an id, generation, parent, start index, radius, fold state and
children. A run goes like this:

1. **Root.** Bot 0 starts at index 0 with the starting radius, "open" (unfolded).
2. **Read.** The bot steps through the text, logging each character (newlines skipped, whitespace shown as `·`).
3. **Leave.** On a `!` the bot marks itself as left at that index and records the crease there.
4. **Spawn.** Unless the bot is at the generation cap, it creates a child that starts at the next character with
   `radius * growth` (rounded to 4 decimal places), on the "folded side" with two folds logged across the crease.
5. **Sync.** The parent copies the child's radius, crease and fold state onto its own record, and both are marked synced.
6. **Repeat.** The child takes over from step 2. When a bot reaches the end of the text it stops, and the lineage table
   is printed.

There's only ever one active bot. Each `!` ends one bot and starts the next, so the "family tree" is really a chain.
Bots run one after another in a plain loop. Earlier versions started each child from inside its parent's function call,
which hit Python's recursion limit (`RecursionError`) once a file had about 500 bangs. Now the stack depth stays the
same however many bangs there are, and `tests/test_bang_bot.py` checks this with 5,000.

### Things to know

- The radius grows geometrically. With the default `--growth 1.5` it overflows to `inf` after roughly 1,750 spawns.
  That's harmless (it's only printed), but use `--growth 1` if you want readable numbers on huge inputs.
- Output is one line per character, so large files produce a lot of output. Pipe it through `tail` or `less`.

## Development

```sh
git clone https://github.com/fitzyracing1/uiltiol && cd uiltiol
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest                      # run the test suite
ruff check . && ruff format --check .   # lint + formatting
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs ruff, then pytest on Python 3.9 to 3.13 on Linux, plus
3.13 on macOS and Windows. The tests include a golden test that pins the built-in sample's output byte-for-byte, a check
that the demo above matches a real run, and regression tests for the old `RecursionError`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for more.

## License

[MIT](LICENSE) © 2026 Joshua Almeida
