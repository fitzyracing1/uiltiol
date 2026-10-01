# Contributing to uiltiol

Thanks for taking a look! uiltiol is meant to stay small: **one script, standard library only, predictable output**.
Every change should keep those three things true.

## Setup

```sh
git clone https://github.com/fitzyracing1/uiltiol && cd uiltiol
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
bang-bot --help
```

Python 3.9+ is required. There are no runtime dependencies, so please don't add any. The dev extras are just `pytest`
and `ruff`.

## Layout

| Path | What lives there |
|---|---|
| `bang_bot.py` | The whole program: the `Bot` dataclass, the `run()` loop, the lineage `report()`, and the CLI (`main()`) |
| `tests/test_bang_bot.py` | pytest suite |
| `tests/data/default_output.txt` | Golden output for the built-in sample (`bang-bot` with no arguments) |
| `examples/bangs.txt` | Input for the README demo. A test checks that the README shows its real output |
| `.github/workflows/ci.yml` | Ruff, then pytest on Python 3.9 to 3.13 (Linux) and 3.13 (macOS, Windows) |

## Making changes

1. Keep the bot chain **iterative**. `Bot.run()` returns the next bot and `run()` loops over them. Don't go back to
   bots calling each other, because that's how the old `RecursionError` happened.
2. If you change what gets printed on purpose, regenerate the golden file and say so in your PR:

   ```sh
   python3 bang_bot.py > tests/data/default_output.txt
   ```

   If you change how `examples/bangs.txt` renders, update the demo block in `README.md` too.
3. Add or update tests for any behavior change.
4. Before you push, run:

   ```sh
   ruff check . && ruff format --check .
   pytest
   ```

## Pull requests

- Keep PRs focused. One fix or feature per PR is ideal.
- CI must pass on every Python version in the matrix.
- By contributing you agree that your contributions are licensed under the MIT License.
