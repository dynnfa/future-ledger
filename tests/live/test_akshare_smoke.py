from __future__ import annotations

import pytest

from future_ledger.sources.akshare_client import fetch_a_share_spot

pytestmark = pytest.mark.live_akshare


def test_live_fetch_a_share_spot_smoke() -> None:
    result = fetch_a_share_spot()

    assert result.error is None
    assert result.metadata.stage == "spot_fetch"
    assert result.metadata.source_name == "akshare"
    assert result.metadata.row_count == len(result.frame.index)
    assert not result.frame.empty
