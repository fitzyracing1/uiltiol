"""Tests for bang_bot."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import bang_bot
from bang_bot import DEFAULT_SOURCE, count_bangs, main, run

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(__file__).resolve().parent / "data"


def walk(source: str, max_generation: int = 8, radius: float = 1.0, growth: float = 1.5):
    return run(source, max_generation, 0.0, radius, growth)


# --- counting -------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "expected"),
    [("", 0), ("no bangs here", 0), ("!", 1), ("a!b!!c", 3), (DEFAULT_SOURCE, 4)],
)
def test_count_bangs(source: str, expected: int) -> None:
    assert count_bangs(source) == expected


# --- core behaviour -------------------------------------------------------


def test_no_bangs_forms_only_the_root(capsys: pytest.CaptureFixture[str]) -> None:
    registry = walk("abc")
    assert list(registry) == [0]
    root = registry[0]
    assert root.parent_id is None
    assert root.children == []
    assert root.left_at is None
    assert root.alive
    out = capsys.readouterr().out
    assert "[bot 0] reaches end. no more bangs. stops." in out


def test_empty_source(capsys: pytest.CaptureFixture[str]) -> None:
    registry = walk("")
    assert list(registry) == [0]
    assert "source length=0 bangs=0" in capsys.readouterr().out


def test_each_bang_spawns_a_child_with_grown_radius(capsys: pytest.CaptureFixture[str]) -> None:
    registry = walk("a!b!c", radius=2.0, growth=3.0)
    assert sorted(registry) == [0, 1, 2]

    root, first, second = registry[0], registry[1], registry[2]
    assert (root.generation, first.generation, second.generation) == (0, 1, 2)
    assert (first.parent_id, second.parent_id) == (0, 1)
    assert root.children == [1]
    assert first.children == [2]
    assert second.children == []

    assert first.start_index == 2
    assert second.start_index == 4
    # Each spawn multiplies the radius by `growth`, and every parent is then
    # synced to its child's radius.
    out = capsys.readouterr().out
    assert "[bot 0] spawns bot 1. crease radius 2.00 -> 6.00" in out
    assert "[bot 1 gen 1] enters at index 2 radius=6.00" in out
    assert "[bot 1] spawns bot 2. crease radius 6.00 -> 18.00" in out
    assert root.radius == pytest.approx(6.0)
    assert first.radius == pytest.approx(18.0)
    assert second.radius == pytest.approx(18.0)


def test_parent_syncs_with_child() -> None:
    registry = walk("ab!cd")
    parent, child = registry[0], registry[1]
    assert parent.radius == child.radius == pytest.approx(1.5)
    assert parent.crease_at == child.crease_at == 2
    assert parent.fold_count == child.fold_count == 2
    assert parent.folded and child.folded
    assert parent.synced and child.synced
    assert parent.left_at == 2
    assert not parent.alive
    assert child.alive


def test_consecutive_bangs_spawn_back_to_back() -> None:
    registry = walk("!!!")
    assert sorted(registry) == [0, 1, 2, 3]
    assert [registry[i].left_at for i in range(4)] == [0, 1, 2, None]
    assert [registry[i].start_index for i in range(4)] == [0, 1, 2, 3]


def test_generation_cap_stops_spawning(capsys: pytest.CaptureFixture[str]) -> None:
    registry = walk("!" * 10, max_generation=3)
    assert sorted(registry) == [0, 1, 2, 3]
    last = registry[3]
    assert last.generation == 3
    assert last.left_at == 3
    assert last.children == []
    out = capsys.readouterr().out
    assert "[bot 3] generation cap 3 reached. does not spawn." in out
    assert "reaches end" not in out


def test_max_gen_zero_forms_only_the_root() -> None:
    registry = walk("a!b!c", max_generation=0)
    assert list(registry) == [0]
    assert registry[0].left_at == 1


def test_newlines_are_skipped_and_spaces_shown_as_dots(
    capsys: pytest.CaptureFixture[str],
) -> None:
    walk("a b\nc")
    out = capsys.readouterr().out
    assert "reads '\u00b7' @ 1" in out
    assert "@ 3 " not in out  # the newline is not echoed
    assert "reads 'c' @ 4" in out


def test_delay_sleeps_once_per_character(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    monkeypatch.setattr(bang_bot.time, "sleep", calls.append)
    run("ab!c", 8, 0.25, 1.0, 1.5)
    # 'a' and 'b' for bot 0, 'c' for bot 1; the '!' itself does not sleep.
    assert calls == [0.25, 0.25, 0.25]


def test_default_sample_output_is_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    """Golden test: output of the built-in sample matches the pre-refactor version."""
    assert main([]) == 0
    expected = (DATA / "default_output.txt").read_text(encoding="utf-8")
    assert capsys.readouterr().out == expected


# --- regression: RecursionError ----------------------------------------------


def test_thousands_of_bangs_do_not_recurse(capsys: pytest.CaptureFixture[str]) -> None:
    """Each bot used to run inside its parent's call, so ~1000 bangs raised RecursionError."""
    bangs = 5000
    registry = walk("!" * bangs, max_generation=bangs * 2, growth=1.0)
    assert len(registry) == bangs + 1
    assert registry[bangs].generation == bangs
    assert registry[bangs].parent_id == bangs - 1
    assert "[bot 5000] reaches end. no more bangs. stops." in capsys.readouterr().out


def test_chain_depth_is_independent_of_recursion_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(200)
    try:
        registry = walk("x!" * 2000, max_generation=10_000)
    finally:
        sys.setrecursionlimit(old_limit)
    capsys.readouterr()
    assert len(registry) == 2001


def test_main_with_many_bangs_from_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "bangs.txt"
    source.write_text("!" * 3000, encoding="utf-8")
    assert main([str(source), "--max-gen", "10000"]) == 0
    assert capsys.readouterr().out.rstrip().endswith("bots formed: 3001")


# --- CLI -----------------------------------------------------------------


def test_main_reads_a_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "in.txt"
    source.write_text("hi!there", encoding="utf-8")
    assert main([str(source), "--radius", "2", "--growth", "2"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("source length=8 bangs=1 cap=8 radius=2.0 growth=2.0\n")
    assert "crease radius 2.00 -> 4.00" in out
    assert "--- lineage ---" in out
    assert out.rstrip().endswith("bots formed: 2")


def test_main_self_walks_its_own_source(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--self", "--max-gen", "1"]) == 0
    out = capsys.readouterr().out
    own = Path(bang_bot.__file__).read_text(encoding="utf-8")
    assert out.startswith(f"source length={len(own)} bangs={own.count('!')} cap=1 ")
    assert "bots formed: 2" in out


@pytest.mark.parametrize(
    "args",
    [["--max-gen", "-1"], ["--radius", "0"], ["--growth", "-2"], ["--delay", "-1"]],
)
def test_main_rejects_invalid_numbers(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "max-gen >= 0" in captured.err


def test_main_reports_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "nope.txt"
    assert main([str(missing)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cannot read" in captured.err


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"bang-bot {bang_bot.__version__}"


def test_script_runs_as_a_subprocess() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "bang_bot.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert result.stdout == (DATA / "default_output.txt").read_text(encoding="utf-8")
