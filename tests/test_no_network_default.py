from __future__ import annotations

import ast
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pytest
from tenacity import wait_none

from future_ledger.sources import akshare_client
from future_ledger.sources.akshare_client import fetch_a_share_spot

TEST_ROOT = Path("tests")
LIVE_ROOT = TEST_ROOT / "live"


def test_live_akshare_marker_is_registered() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"].get("markers", [])

    assert any(marker.startswith("live_akshare:") for marker in markers)


def test_default_tests_do_not_use_live_akshare_marker() -> None:
    marked_paths = {
        path
        for path in TEST_ROOT.rglob("test_*.py")
        if any(mark == "live_akshare" for mark in _pytest_mark_names(path))
    }

    assert marked_paths <= set(LIVE_ROOT.rglob("test_*.py"))


def test_live_tests_are_marked_live_akshare() -> None:
    for path in LIVE_ROOT.rglob("test_*.py"):
        marks = set(_pytest_mark_names(path))
        assert "live_akshare" in marks, f"Live test file lacks marker: {path}"


def test_default_tests_block_directly_imported_akshare_source_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(akshare_client, "_RETRY_WAIT", wait_none())

    result = fetch_a_share_spot()

    assert result.frame.empty
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.symbol == "all_a"
    assert result.error is not None
    assert result.error.stage == "spot_fetch"
    assert result.error.stock_code == "all_a"
    assert result.error.message.startswith("RuntimeError: Network access disabled")


def _pytest_mark_names(path: Path) -> Iterable[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            yield from _decorator_mark_names(node.decorator_list)
    yield from _module_marker_names(tree)


def _decorator_mark_names(decorators: list[ast.expr]) -> Iterable[str]:
    for decorator in decorators:
        mark_name = _mark_name_from_decorator(decorator)
        if mark_name is not None:
            yield mark_name


def _module_marker_names(tree: ast.Module) -> Iterable[str]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "pytestmark"
            for target in node.targets
        ):
            continue
        yield from _mark_names_from_value(node.value)


def _mark_names_from_value(value: ast.expr) -> Iterable[str]:
    if isinstance(value, ast.List | ast.Tuple):
        for element in value.elts:
            mark_name = _mark_name_from_decorator(element)
            if mark_name is not None:
                yield mark_name
        return

    mark_name = _mark_name_from_decorator(value)
    if mark_name is not None:
        yield mark_name


def _mark_name_from_decorator(decorator: ast.expr) -> str | None:
    candidate = decorator.func if isinstance(decorator, ast.Call) else decorator
    if (
        isinstance(candidate, ast.Attribute)
        and candidate.attr != "parametrize"
        and isinstance(candidate.value, ast.Attribute)
        and candidate.value.attr == "mark"
        and isinstance(candidate.value.value, ast.Name)
        and candidate.value.value.id == "pytest"
    ):
        return candidate.attr
    return None
