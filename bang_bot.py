#!/usr/bin/env python3
"""bang_bot.py — leave, spawn, increase radius, then fold.

Walks source one character at a time. On each '!' the current bot leaves,
spawns a child, increases the crease radius, then folds the remaining walk
across that crease. The child continues on the folded side.
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
    radius: float = 1.0
    growth: float = 1.5
    folded: bool = False
    crease_at: int | None = None
    children: list[int] = field(default_factory=list)
    left_at: int | None = None
    alive: bool = True

    def run(self, registry: dict[int, "Bot"], next_id: list[int]) -> None:
        i = self.start_index
        n = len(self.source)
        side = "folded" if self.folded else "open"
        print(
            f"[bot {self.bot_id} gen {self.generation}] "
            f"enters at index {i} radius={self.radius:.2f} side={side}"
            + (f" (parent {self.parent_id})" if self.parent_id is not None else " (root)")
        )
        while i < n and self.alive:
            ch = self.source[i]
            if ch == "!":
                self.leave_spawn_increase_fold(i, registry, next_id)
                return
            if ch not in "\n\r":
                shown = ch if ch.strip() else "\u00b7"
                print(
                    f"[bot {self.bot_id}] reads '{shown}' @ {i} "
                    f"r={self.radius:.2f}"
                )
            if self.delay:
                time.sleep(self.delay)
            i += 1
        print(f"[bot {self.bot_id}] reaches end. no more bangs. stops.")

    def leave_spawn_increase_fold(
        self,
        bang_index: int,
        registry: dict[int, "Bot"],
        next_id: list[int],
    ) -> None:
        self.alive = False
        self.left_at = bang_index
        self.crease_at = bang_index
        snippet = self.source[max(0, bang_index - 12) : bang_index + 1]
        print(
            f"[bot {self.bot_id}] HITS '!' @ {bang_index} near {snippet!r}. leaves."
        )
        if self.generation >= self.max_generation:
            print(
                f"[bot {self.bot_id}] generation cap {self.max_generation} "
                f"reached. does not spawn."
            )
            return

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
            crease_at=bang_index,
        )
        self.children.append(child_id)
        registry[child_id] = child
        child.run(registry, next_id)


def count_bangs(source: str) -> int:
    return source.count("!")


def run(
    source: str,
    max_generation: int,
    delay: float,
    radius: float,
    growth: float,
) -> dict[int, Bot]:
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
    root.run(registry, next_id)
    return registry


def report(registry: dict[int, Bot]) -> None:
    print("\n--- lineage ---")
    for bot_id in sorted(registry):
        bot = registry[bot_id]
        kids = ", ".join(str(k) for k in bot.children) or "none"
        print(
            f"bot {bot.bot_id} gen {bot.generation} "
            f"parent={bot.parent_id} radius={bot.radius:.2f} "
            f"folded={bot.folded} crease_at={bot.crease_at} "
            f"left_at={bot.left_at} children={kids}"
        )
    print(f"bots formed: {len(registry)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Leave, spawn, increase radius, then fold on every '!'."
    )
    parser.add_argument("path", nargs="?", help="file to walk")
    parser.add_argument("--self", action="store_true", help="walk this script")
    parser.add_argument("--max-gen", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--radius", type=float, default=1.0, help="starting crease radius")
    parser.add_argument("--growth", type=float, default=1.5, help="radius multiplier on each spawn")
    args = parser.parse_args(argv)

    if args.self:
        with open(os.path.abspath(__file__), encoding="utf-8") as handle:
            source = handle.read()
    elif args.path:
        with open(args.path, encoding="utf-8") as handle:
            source = handle.read()
    else:
        source = DEFAULT_SOURCE

    if args.max_gen < 0 or args.radius <= 0 or args.growth <= 0:
        print("max-gen >= 0, radius > 0, growth > 0", file=sys.stderr)
        return 2

    registry = run(source, args.max_gen, args.delay, args.radius, args.growth)
    report(registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
