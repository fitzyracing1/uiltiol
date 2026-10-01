#!/usr/bin/env python3
"""bang_bot.py — a bot that leaves and forms another bot every time it hits '!'.

Walks source text one character at a time. On each '!' the current bot
stops consuming that branch (leaves) and spawns a child bot that continues
from the character after the bang. Children do the same, so every '!'
is a split point.

Generation is capped so a file full of bangs cannot fork forever.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field


DEFAULT_SOURCE = '''
def greet():
    print("hello!")
    if ready!:
        launch!()
    return "done!"
'''


@dataclass
class Bot:
    bot_id: int
    generation: int
    parent_id: int | None
    start_index: int
    source: str
    max_generation: int
    delay: float
    children: list[int] = field(default_factory=list)
    left_at: int | None = None
    alive: bool = True

    def run(self, registry: dict[int, "Bot"], next_id: list[int]) -> None:
        i = self.start_index
        n = len(self.source)
        print(
            f"[bot {self.bot_id} gen {self.generation}] "
            f"enters at index {i}"
            + (f" (parent {self.parent_id})" if self.parent_id is not None else " (root)")
        )
        while i < n and self.alive:
            ch = self.source[i]
            if ch == "!":
                self.leave_and_form(i, registry, next_id)
                return
            if ch not in "\n\r":
                shown = ch if ch.strip() else "\u00b7"
                print(f"[bot {self.bot_id}] reads '{shown}' @ {i}")
            if self.delay:
                time.sleep(self.delay)
            i += 1
        print(f"[bot {self.bot_id}] reaches end. no more bangs. stops.")

    def leave_and_form(
        self,
        bang_index: int,
        registry: dict[int, "Bot"],
        next_id: list[int],
    ) -> None:
        self.alive = False
        self.left_at = bang_index
        snippet = self.source[max(0, bang_index - 12) : bang_index + 1]
        print(
            f"[bot {self.bot_id}] HITS '!' @ {bang_index} near {snippet!r}. "
            f"leaves."
        )
        if self.generation >= self.max_generation:
            print(
                f"[bot {self.bot_id}] generation cap {self.max_generation} "
                f"reached. does not form another bot."
            )
            return
        child_id = next_id[0]
        next_id[0] += 1
        child = Bot(
            bot_id=child_id,
            generation=self.generation + 1,
            parent_id=self.bot_id,
            start_index=bang_index + 1,
            source=self.source,
            max_generation=self.max_generation,
            delay=self.delay,
        )
        self.children.append(child_id)
        registry[child_id] = child
        print(
            f"[bot {self.bot_id}] forms bot {child_id} "
            f"(gen {child.generation}) starting at {child.start_index}"
        )
        child.run(registry, next_id)


def count_bangs(source: str) -> int:
    return source.count("!")


def run(source: str, max_generation: int, delay: float) -> dict[int, Bot]:
    registry: dict[int, Bot] = {}
    next_id = [1]
    root = Bot(
        bot_id=0,
        generation=0,
        parent_id=None,
        start_index=0,
        source=source,
        max_generation=max_generation,
        delay=delay,
    )
    registry[0] = root
    print(f"source length={len(source)} bangs={count_bangs(source)} cap={max_generation}")
    root.run(registry, next_id)
    return registry


def report(registry: dict[int, Bot]) -> None:
    print("\n--- lineage ---")
    for bot_id in sorted(registry):
        bot = registry[bot_id]
        kids = ", ".join(str(k) for k in bot.children) or "none"
        print(
            f"bot {bot.bot_id} gen {bot.generation} "
            f"parent={bot.parent_id} left_at={bot.left_at} children={kids}"
        )
    print(f"bots formed: {len(registry)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bot that leaves and forms another bot on every '!'."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="file to walk (default: built-in sample with bangs)",
    )
    parser.add_argument(
        "--self",
        action="store_true",
        help="walk this script's own source",
    )
    parser.add_argument(
        "--max-gen",
        type=int,
        default=8,
        help="stop forming children after this generation (default 8)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="seconds to pause after each non-bang character",
    )
    args = parser.parse_args(argv)

    if args.self:
        with open(os.path.abspath(__file__), encoding="utf-8") as handle:
            source = handle.read()
    elif args.path:
        with open(args.path, encoding="utf-8") as handle:
            source = handle.read()
    else:
        source = DEFAULT_SOURCE

    if args.max_gen < 0:
        print("max-gen must be >= 0", file=sys.stderr)
        return 2

    registry = run(source, args.max_gen, args.delay)
    report(registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
