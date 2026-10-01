#!/usr/bin/env python3
"""bang_bot.py — leave, spawn, increase radius, fold, fold again, sync.

On each '!' the current bot leaves, spawns a child, increases the crease
radius, folds, folds again across the same crease, then syncs the child
radius and crease back onto the parent record.

Bots run one after another in a flat loop (no recursion), so a source with
thousands of bangs and a high --max-gen does not hit Python's recursion limit.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field

__version__ = "0.1.0"

DEFAULT_SOURCE = """
def greet():
    print("hello!")
    if ready!:
        launch!()
    return "done!"
"""


@dataclass
class Bot:
    bot_id: int
    generation: int
    parent_id: int | None
    start_index: int
    source: str
    max_generation: int
    delay: float
    radius: float = 1.0
    growth: float = 1.5
    folded: bool = False
    fold_count: int = 0
    synced: bool = False
    crease_at: int | None = None
    children: list[int] = field(default_factory=list)
    left_at: int | None = None
    alive: bool = True

    def run(self, registry: dict[int, Bot], next_id: list[int]) -> Bot | None:
        """Walk the source from ``start_index``.

        Returns the child bot to run next if this bot spawned one on a ``!``,
        otherwise ``None``. The caller drives the chain; bots never call each
        other, so the stack depth stays constant however many bangs there are.
        """
        i = self.start_index
        n = len(self.source)
        side = f"folded x{self.fold_count}" if self.folded else "open"
        print(
            f"[bot {self.bot_id} gen {self.generation}] "
            f"enters at index {i} radius={self.radius:.2f} side={side} "
            f"synced={self.synced}"
            + (f" (parent {self.parent_id})" if self.parent_id is not None else " (root)")
        )
        while i < n and self.alive:
            ch = self.source[i]
            if ch == "!":
                return self.leave_spawn_increase_fold(i, registry, next_id)
            if ch not in "\n\r":
                shown = ch if ch.strip() else "\u00b7"
                print(f"[bot {self.bot_id}] reads '{shown}' @ {i} r={self.radius:.2f}")
            if self.delay:
                time.sleep(self.delay)
            i += 1
        print(f"[bot {self.bot_id}] reaches end. no more bangs. stops.")
        return None

    def leave_spawn_increase_fold(
        self,
        bang_index: int,
        registry: dict[int, Bot],
        next_id: list[int],
    ) -> Bot | None:
        self.alive = False
        self.left_at = bang_index
        self.crease_at = bang_index
        snippet = self.source[max(0, bang_index - 12) : bang_index + 1]
        print(f"[bot {self.bot_id}] HITS '!' @ {bang_index} near {snippet!r}. leaves.")
        if self.generation >= self.max_generation:
            print(
                f"[bot {self.bot_id}] generation cap {self.max_generation} reached. does not spawn."
            )
            return None

        child_id = next_id[0]
        next_id[0] += 1
        new_radius = round(self.radius * self.growth, 4)
        print(
            f"[bot {self.bot_id}] spawns bot {child_id}. "
            f"crease radius {self.radius:.2f} -> {new_radius:.2f}"
        )
        print(
            f"[bot {self.bot_id}] folds across crease @ {bang_index}. "
            f"child starts on the folded side at {bang_index + 1}"
        )
        print(
            f"[bot {self.bot_id}] folds again across crease @ {bang_index}. "
            f"radius holds at {new_radius:.2f}"
        )
        child = Bot(
            bot_id=child_id,
            generation=self.generation + 1,
            parent_id=self.bot_id,
            start_index=bang_index + 1,
            source=self.source,
            max_generation=self.max_generation,
            delay=self.delay,
            radius=new_radius,
            growth=self.growth,
            folded=True,
            fold_count=2,
            crease_at=bang_index,
        )
        self.children.append(child_id)
        registry[child_id] = child
        self.sync(child)
        return child

    def sync(self, child: Bot) -> None:
        self.radius = child.radius
        self.crease_at = child.crease_at
        self.fold_count = child.fold_count
        self.folded = child.folded
        self.synced = True
        child.synced = True
        print(
            f"[bot {self.bot_id}] syncs with bot {child.bot_id}: "
            f"radius={self.radius:.2f} folds={self.fold_count} crease={self.crease_at}"
        )


def count_bangs(source: str) -> int:
    """Return the number of ``!`` characters in ``source``."""
    return source.count("!")


def run(
    source: str,
    max_generation: int,
    delay: float,
    radius: float,
    growth: float,
) -> dict[int, Bot]:
    """Run the root bot and every bot it spawns; return them keyed by id."""
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
        radius=radius,
        growth=growth,
    )
    registry[0] = root
    print(
        f"source length={len(source)} bangs={count_bangs(source)} "
        f"cap={max_generation} radius={radius} growth={growth}"
    )
    bot: Bot | None = root
    while bot is not None:
        bot = bot.run(registry, next_id)
    return registry


def report(registry: dict[int, Bot]) -> None:
    """Print one lineage line per bot, in id order."""
    print("\n--- lineage ---")
    for bot_id in sorted(registry):
        bot = registry[bot_id]
        kids = ", ".join(str(k) for k in bot.children) or "none"
        print(
            f"bot {bot.bot_id} gen {bot.generation} "
            f"parent={bot.parent_id} radius={bot.radius:.2f} "
            f"folded={bot.folded} folds={bot.fold_count} synced={bot.synced} "
            f"crease_at={bot.crease_at} left_at={bot.left_at} children={kids}"
        )
    print(f"bots formed: {len(registry)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bang-bot",
        description="Leave, spawn, increase radius, fold, fold again, sync.",
    )
    parser.add_argument("path", nargs="?", help="file to walk (default: a built-in sample)")
    parser.add_argument("--self", action="store_true", help="walk this script")
    parser.add_argument(
        "--max-gen",
        type=int,
        default=8,
        help="generation cap; bots at the cap do not spawn (default: 8)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="seconds to sleep after each character (default: 0)",
    )
    parser.add_argument("--radius", type=float, default=1.0, help="starting crease radius")
    parser.add_argument("--growth", type=float, default=1.5, help="radius multiplier on each spawn")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    if args.max_gen < 0 or args.radius <= 0 or args.growth <= 0 or args.delay < 0:
        print("max-gen >= 0, radius > 0, growth > 0, delay >= 0", file=sys.stderr)
        return 2

    path = os.path.abspath(__file__) if args.self else args.path
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"bang-bot: cannot read {path}: {exc}", file=sys.stderr)
            return 2
    else:
        source = DEFAULT_SOURCE

    registry = run(source, args.max_gen, args.delay, args.radius, args.growth)
    report(registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
