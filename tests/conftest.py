from __future__ import annotations

from collections.abc import Iterator
from typing import NoReturn

import pytest

LIVE_AKSHARE_MARKER = "live_akshare"


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if _live_akshare_requested(config):
        return

    skip_live = pytest.mark.skip(reason="live AKShare tests require -m live_akshare")
    for item in items:
        if LIVE_AKSHARE_MARKER in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(autouse=True)
def _disable_akshare_source_client_by_default(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    if (
        request.node.get_closest_marker(LIVE_AKSHARE_MARKER) is not None
        and _live_akshare_requested(request.config)
    ):
        yield
        return

    def blocked_fetch(*_args: object, **_kwargs: object) -> NoReturn:
        raise RuntimeError(
            "Network access disabled for default tests; mark live tests with "
            "@pytest.mark.live_akshare and run with -m live_akshare"
        )

    monkeypatch.setattr(
        "future_ledger.sources.akshare_client.ak.stock_zh_a_spot_em",
        blocked_fetch,
    )
    monkeypatch.setattr(
        "future_ledger.sources.akshare_client.ak.stock_fhps_detail_em",
        blocked_fetch,
    )
    monkeypatch.setattr(
        "future_ledger.sources.akshare_client.ak.stock_zh_a_hist",
        blocked_fetch,
    )

    yield


def _live_akshare_requested(config: pytest.Config) -> bool:
    marker_expression = str(config.option.markexpr or "")
    return LIVE_AKSHARE_MARKER in marker_expression
