### Task 3: Implement Deterministic Raw Cache Read/Write

**Files:**
- Modify: `src/future_ledger/cache.py`
- Test: `tests/test_cache.py`

- [ ] **Step 1: Write failing cache tests**

```python
from pathlib import Path

import pandas as pd

from future_ledger.cache import cache_key, read_cache, write_cache


def test_cache_key_nests_stage_and_symbol():
    assert cache_key("dividend_detail", "600000") == "dividend_detail/600000.csv"


def test_write_cache_creates_parent_dirs_and_round_trips(tmp_path: Path):
    cache_dir = tmp_path / "cache"
    frame = pd.DataFrame([{"col": "value", "num": 1}])

    write_cache(cache_dir, cache_key("dividend_detail", "600000"), frame)
    loaded = read_cache(cache_dir, cache_key("dividend_detail", "600000"))

    assert loaded is not None
    assert loaded.to_dict(orient="records") == [{"col": "value", "num": 1}]
```

- [ ] **Step 2: Run tests to verify cache functions are unimplemented**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement cache read/write**

```python
def read_cache(cache_dir: Path, key: str) -> pd.DataFrame | None:
    path = cache_dir / key
    if not path.exists():
        return None
    return pd.read_csv(path)


def write_cache(cache_dir: Path, key: str, df: pd.DataFrame) -> None:
    path = cache_dir / key
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
```

- [ ] **Step 4: Run tests to verify round-trip behavior**

Run: `pytest tests/test_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/future_ledger/cache.py tests/test_cache.py
git commit -m "feat: add deterministic dataframe cache"
```
