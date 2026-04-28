from __future__ import annotations

import akshare as ak  # type: ignore[import-untyped]
import pandas as pd  # type: ignore[import-untyped]


def fetch_a_share_spot() -> pd.DataFrame:
    return ak.stock_zh_a_spot_em()


def fetch_dividend_detail(symbol: str) -> pd.DataFrame:
    return ak.stock_fhps_detail_em(symbol=symbol)


def fetch_price_history(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    return ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
    )
