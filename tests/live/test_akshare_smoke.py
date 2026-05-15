from __future__ import annotations

import pytest

from future_ledger.sources.akshare_client import fetch_a_share_spot

pytestmark = pytest.mark.live_akshare


def test_akshare_spot_smoke_returns_rows() -> None:
    frame = fetch_a_share_spot()

    assert not frame.empty
