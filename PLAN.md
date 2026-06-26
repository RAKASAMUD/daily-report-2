# Stage 1 — Data Layer Implementation Plan

> **For the implementer (Claude Code):** This plan is intentionally **skeletal**. The
> *contracts* are exact and must not drift: file layout, function names, parameter and
> return types, and the list of tests each task must pass. Function **bodies are stubs** —
> complete them so the listed tests pass. Follow the execution rhythm below for every task.
> Steps use `- [ ]` checkboxes for tracking.

**Goal:** A self-running service that pulls closed spot candles for 5 coins × 4 timeframes
from Binance on a schedule and stores them clean and duplicate-free in SQLite, ready for the
Signal layer to read.

**Architecture:** Pure decision logic (which timeframes just closed, gap detection, resume
point) is split from all side effects (network, clock, DB) behind thin seams, so the core is
unit-testable without internet. One unified 5-minute tick drives everything; one fetch routine
serves backfill, incremental update, and gap-fill identically (it always fetches *from the last
stored candle forward*).

**Tech Stack:** Python 3.11+, `ccxt`, `pandas`, `pytest`. SQLite (stdlib `sqlite3`).
Standard-library `logging`, `fcntl`, `time`. No web framework, no ORM.

## Global Constraints
- Market: **spot**. Symbols (config-driven): `BTC/USDT ETH/USDT SOL/USDT SUI/USDT AVAX/USDT`.
- Timeframes: `5m 15m 1h 4h`.
- Time is stored as **integer epoch milliseconds, UTC** (`open_time` = candle start).
- Table holds **only closed candles**; rows are **insert-only** (never updated).
- Scheduling: **one** trigger every 5 minutes, **one** process; `now` is floored to the
  5-minute boundary before computing due timeframes.
- Single SQLite table `candles`, PK `(symbol, timeframe, open_time)`, `WITHOUT ROWID`, WAL mode.
- Writes idempotent (`INSERT OR IGNORE`); single-instance lock via `fcntl.flock`.
- Runs on a 2 GB VPS beside Hermes: trigger is short-lived; reads always use a bounded window.
- Code + comments in **English**.

## Execution Rhythm (every task)
1. Write the failing test(s) listed under the task.
2. Run them, confirm they fail for the expected reason.
3. Fill the stub(s) with the minimal code to pass.
4. Run the test file, confirm green.
5. `git commit` with the message given.

## Test Seams (used throughout)
- **Clock**: pass `now_ms: int` into logic; never call `time.time()` inside decision functions.
- **Binance**: all `ccxt` calls live in `BinanceAdapter`, constructed with an injected exchange
  object. Tests inject a fake that returns canned rows.
- **DB**: tests open SQLite at `":memory:"` and run the real schema.
- **Fixtures**: hand-written rows for *exact-answer* tests; seeded `random_walk_candles` for
  *property* tests (no duplicates, time strictly increasing, idempotent re-insert) and for
  generating large synthetic histories to check speed/memory.

---

## Task A1: Project skeleton + config

**Files:**
- Create: `pyproject.toml` (or `requirements.txt`), `data_layer/__init__.py`, `data_layer/config.py`
- Create: `tests/__init__.py`, `tests/test_config.py`

**Interfaces — Produces:**
```python
# config.py
SYMBOLS: list[str]
TIMEFRAMES: list[str]                 # ["5m","15m","1h","4h"]
TIMEFRAME_MS: dict[str, int]          # {"5m":300_000,"15m":900_000,"1h":3_600_000,"4h":14_400_000}
BACKFILL_DAYS: int                    # 730
DB_PATH: str                          # "data/candles.db"
```

- [ ] **Tests:** `TIMEFRAME_MS` has an entry for every item in `TIMEFRAMES`; values match the
  durations above; `SYMBOLS` are all `*/USDT`.
- [ ] **Stub → implement** the constants. No logic.
- [ ] **Commit:** `chore: project skeleton and config`

---

## Task A2: Database schema + connection

**Files:**
- Create: `data_layer/db.py`
- Create: `tests/test_db_schema.py`

**Interfaces — Produces:**
```python
def connect(db_path: str) -> sqlite3.Connection   # sets PRAGMA journal_mode=WAL
def init_schema(conn: sqlite3.Connection) -> None  # CREATE TABLE IF NOT EXISTS candles (...)
```
Schema (verbatim): table `candles(symbol TEXT, timeframe TEXT, open_time INTEGER, open REAL,
high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY(symbol,timeframe,open_time)) WITHOUT ROWID`.

- [ ] **Tests (in-memory):** after `init_schema`, table `candles` exists with the 8 expected
  columns; calling `init_schema` twice does not error; `journal_mode` is `wal` on a file DB.
- [ ] **Stub → implement.**
- [ ] **Commit:** `feat: candles schema and connection`

---

## Task B1: Storage read/write (dedup, resume point, read door)

**Files:**
- Modify: `data_layer/db.py`
- Create: `tests/test_db_io.py`

**Interfaces — Consumes:** `connect`, `init_schema` (A2).
**Interfaces — Produces:**
```python
Row = tuple[int, float, float, float, float, float]   # (open_time, open, high, low, close, volume)

def write_candles(conn, symbol: str, timeframe: str, rows: list[Row]) -> int   # INSERT OR IGNORE; returns rows actually inserted
def get_last_open_time(conn, symbol: str, timeframe: str) -> int | None         # MAX(open_time) for that pair, or None
def get_candles(conn, symbol: str, timeframe: str, limit: int = 500) -> pandas.DataFrame
    # most recent `limit` rows, returned ascending by open_time; columns: open_time, open, high, low, close, volume
```

- [ ] **Tests (in-memory, hand-written rows):**
  - inserting the same row twice → second `write_candles` returns 0, table count unchanged (dedup).
  - `get_last_open_time` returns the max for the queried pair only (insert two symbols, check isolation); returns `None` when empty.
  - `get_candles(..., limit=3)` on 10 rows returns the latest 3, **ascending** by `open_time`.
- [ ] **Stub → implement** (parametrized SQL; `INSERT OR IGNORE`).
- [ ] **Commit:** `feat: candle write/read with dedup and resume point`

---

## Task B2: "Which timeframes just closed" (pure, clock injected)

**Files:**
- Create: `data_layer/schedule.py`
- Create: `tests/test_schedule.py`

**Interfaces — Produces:**
```python
def due_timeframes(now_ms: int, timeframes: list[str]) -> list[str]
    # a tf is due when now_ms is an exact multiple of TIMEFRAME_MS[tf]
    # (the prior candle of that tf has just closed at this boundary)
```

- [ ] **Tests (exact answers; build now_ms from a known UTC instant):**
  - `now` = a 4h boundary (e.g. 04:00:00 UTC) → returns all of `["5m","15m","1h","4h"]`.
  - `now` = 04:05:00 UTC → returns `["5m"]`.
  - `now` = 04:15:00 UTC → returns `["5m","15m"]`.
  - order of the returned list matches the order of `timeframes` input.
- [ ] **Stub → implement** (single comprehension on the modulo rule).
- [ ] **Commit:** `feat: due-timeframe boundary logic`

---

## Task B3: Gap detection (pure)

**Files:**
- Create: `data_layer/gaps.py`
- Create: `tests/test_gaps.py`

**Interfaces — Produces:**
```python
def find_missing(open_times: list[int], timeframe: str) -> list[int]
    # given sorted open_times, return the open_times that *should* exist between
    # first and last (step = TIMEFRAME_MS[timeframe]) but are absent
```

- [ ] **Tests:**
  - contiguous series → returns `[]` (no false alarms).
  - one hole punched in the middle → returns exactly the missing open_time(s).
  - property test with seeded `random_walk_candles`: a fully contiguous generated series always yields `[]`.
- [ ] **Stub → implement.**
- [ ] **Commit:** `feat: gap detection over open_time continuity`

---

## Task C1: Binance adapter (thin seam; drops unclosed candle)

**Files:**
- Create: `data_layer/binance.py`
- Create: `tests/test_binance_adapter.py`
- Create: `data_layer/testkit.py` (test helpers: fake exchange + `random_walk_candles`)

**Interfaces — Produces:**
```python
class BinanceAdapter:
    def __init__(self, exchange):   # exchange: a ccxt-like object with fetch_ohlcv(symbol, timeframe, since, limit)
        ...
    def fetch_closed_ohlcv(self, symbol: str, timeframe: str, since_ms: int, now_ms: int) -> list[Row]
        # paginate forward from since_ms up to now_ms; convert ccxt's [ts,o,h,l,c,v] -> Row;
        # DROP the final candle if it is not yet closed: open_time + TIMEFRAME_MS[tf] > now_ms
```
```python
# testkit.py
class FakeExchange:                    # returns preloaded rows for fetch_ohlcv; lets tests script normal/empty/unclosed/error
    ...
def random_walk_candles(start_open_time: int, timeframe: str, n: int, seed: int, start_price: float = 100.0) -> list[Row]
    # deterministic given seed; open_time strictly increasing by TIMEFRAME_MS[tf]
```

- [ ] **Tests (FakeExchange, no network):**
  - normal page → rows converted in correct field order and types.
  - last candle not yet closed (`open_time + tf_ms > now_ms`) → it is **excluded**; the prior one is kept.
  - empty response → returns `[]`.
  - `random_walk_candles(seed=1)` called twice → identical output (determinism).
- [ ] **Stub → implement** adapter + testkit helpers (pagination loop may be minimal; Claude Code completes paging detail).
- [ ] **Commit:** `feat: binance adapter dropping unclosed candle + test kit`

---

## Task C2: Retry-with-backoff wrapper

**Files:**
- Modify: `data_layer/binance.py`
- Modify: `tests/test_binance_adapter.py`

**Interfaces — Produces:**
```python
def with_retry(fn, attempts: int = 3, base_delay: float = 0.5):
    # retry on transient exceptions with exponential backoff; re-raise after `attempts`
```
(`fetch_closed_ohlcv` wraps its network call in `with_retry`.)

- [ ] **Tests:** a fake that fails twice then succeeds → returns the success (assert call count = 3,
  with `time.sleep` patched/injected so the test is instant); a fake that always fails → raises after
  `attempts`.
- [ ] **Stub → implement.**
- [ ] **Commit:** `feat: transient-failure retry with backoff`

---

## Task D1: Sync routine (backfill = incremental = gap-fill)

**Files:**
- Create: `data_layer/pipeline.py`
- Create: `tests/test_pipeline.py`

**Interfaces — Consumes:** `get_last_open_time`, `write_candles` (B1); `BinanceAdapter` (C1); `TIMEFRAME_MS`, `BACKFILL_DAYS` (A1).
**Interfaces — Produces:**
```python
def sync_pair(conn, adapter: BinanceAdapter, symbol: str, timeframe: str,
              now_ms: int, backfill_days: int) -> int
    # since = (last + TIMEFRAME_MS[tf]) if last else (now_ms - backfill_days*86_400_000)
    # rows = adapter.fetch_closed_ohlcv(symbol, timeframe, since, now_ms)
    # return write_candles(conn, symbol, timeframe, rows)
```

- [ ] **Tests (in-memory DB + FakeExchange):**
  - empty DB → `since` equals the backfill start (≈ `now - backfill_days`); all returned rows written.
  - DB already has data → `since` is `last + tf_ms`; only newer rows fetched/written.
  - re-running the same sync writes 0 new rows (idempotent).
  - a tail gap (DB stops several candles before now) is filled in one call (self-healing).
- [ ] **Stub → implement** (thin orchestration).
- [ ] **Commit:** `feat: unified sync_pair (backfill/incremental/gapfill)`

---

## Task D2: The tick runner (lock, due timeframes, isolated loop)

**Files:**
- Create: `data_layer/runner.py`
- Create: `tests/test_runner.py`

**Interfaces — Consumes:** `due_timeframes` (B2), `sync_pair` (D1), `connect`/`init_schema` (A2), config (A1).
**Interfaces — Produces:**
```python
def floor_to_5min(now_ms: int) -> int
def run_tick(conn, adapter, now_ms: int, symbols: list[str], timeframes: list[str], backfill_days: int) -> dict
    # now = floor_to_5min(now_ms); due = due_timeframes(now, timeframes)
    # for symbol in symbols: for tf in due: try sync_pair(...) except Exception: log + continue
    # return per-pair summary {(symbol,tf): inserted_or_error}
def main() -> None
    # acquire fcntl.flock on a lockfile (exit if already held);
    # build real ccxt.binance() with enableRateLimit=True; connect+init_schema; run_tick(now=time.time*1000); log summary
```

- [ ] **Tests (injected now + FakeExchange):**
  - at a 4h boundary → all four timeframes processed for every symbol.
  - at a 5m-only boundary → only `5m` processed.
  - one symbol/tf raised an error → it is logged and the loop **continues**; other pairs still succeed (assert via summary dict).
- [ ] **Stub → implement.** (`main` wiring is not unit-tested; covered by E2.)
- [ ] **Commit:** `feat: single-instance tick runner with per-pair isolation`

---

## Task D3: Logging

**Files:**
- Create: `data_layer/logging_setup.py`
- Modify: `data_layer/runner.py` (call setup in `main`; log a one-line summary per tick)

**Interfaces — Produces:**
```python
def setup_logging(logfile: str = "data/data_layer.log") -> None   # file + stream handlers; INFO normal, WARNING on failure/gap
```

- [ ] **Test:** `setup_logging` is idempotent (no duplicate handlers when called twice).
- [ ] **Stub → implement;** add INFO summary line in `run_tick`, WARNING on per-pair failure.
- [ ] **Commit:** `feat: logging setup and tick summary`

---

## Task E1: First backfill against real Binance (manual)

**Files:** Create: `scripts/backfill.py` (calls `sync_pair` for every symbol×timeframe once with real `ccxt.binance()`).

- [ ] **Run:** `python -m scripts.backfill`
- [ ] **Verify (manual, on-demand):** row counts per pair are plausible (≈ `backfill_days` of candles, e.g. ~210k at 5m, ~4.4k at 4h per symbol); spot-check a few `close` values against Binance's chart; no exceptions.
- [ ] **Commit:** `chore: backfill script + seeded 2y history`

---

## Task E2: Install the 5-minute trigger; observe

**Files:** Create: `scripts/run_tick.sh` (invokes `python -m data_layer.runner`); a crontab line `*/5 * * * *`.

- [ ] **Install** the cron entry.
- [ ] **Verify:** after ~15–20 min, new candles appear for the timeframes whose boundaries passed
  (check `get_last_open_time` advanced); log is clean; only one process ever runs (lock holds).
- [ ] **Commit:** `chore: cron trigger for 5-min tick`

---

## Task E3: On-demand integrity tool

**Files:** Create: `scripts/verify.py` (for each symbol×timeframe: read all `open_time`s, `find_missing`, refetch+write any holes, print a report). Create: `tests/test_verify.py`.

**Interfaces — Consumes:** `find_missing` (B3), `get_candles`/read (B1), `sync_pair` or adapter (C1/D1).

- [ ] **Test (in-memory):** seed a contiguous series with a hole punched → tool reports the hole and, after running, the hole is filled and a second run reports zero gaps.
- [ ] **Run** once on the seeded DB; expect zero gaps on healthy data.
- [ ] **Commit:** `feat: on-demand integrity verify tool`

---

## Self-Review Checklist (run after implementing)
- Every locked decision maps to a task: schema/WAL (A2), dedup+resume (B1), due-tf (B2),
  gap detect (B3), unclosed-drop (C1), retry (C2), unified sync (D1), lock+isolation (D2),
  on-demand verify (E3). ✔ if all present.
- Type consistency: `Row` is the same 6-tuple everywhere; `open_time` is int ms throughout;
  `get_candles` returns a DataFrame ascending. No function references a name not defined above.
- No live-Binance calls inside the pytest suite (only FakeExchange); the only real-network steps
  are E1 and E2, run by hand.
