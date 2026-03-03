# Polymarket Bot — Full System Report (v5.4)

**Generated:** 2026-03-02  
**Scope:** Consolidated status of architecture, strategy, patches, runtime behavior, and recent engineering changes.

---

## 1) Current Live Runtime Snapshot

- **Engine tag:** `v5_stop_enforcement`
- **Build tag:** `v5.4.2026-03-02.001`
- **Primary engine file:** `polymarket_bot/bot_v5.py`
- **DB:** `polymarket_bot/trades_v4.db`
- **State writer:** `polymarket_bot/runtime/state_v5.json` (atomic)
- **UI variants:**
  - `ui_v5.py`
  - `ui_v531.py` (hybrid / compact monitor iterations)
- **Universe:** `btc-updown`, `sol-updown` (5m)

---

## 2) Architecture and Modules

- Discovery: `v4_discovery.py`
- Orderbook reader: `v4_orderbook.py`
- Signal model: `v4_signal.py`
- Runtime engine: `bot_v5.py`
- Launchers:
  - `run_v5.bat`
  - `run_v5_ui.bat`
  - `run_v531_ui.bat`
  - `launch_all_v53.bat`
  - `launch_all_v531.bat`
  - `hard_reset_v53.bat`

---

## 3) Strategy Behavior (Current)

### Signal
- Uses Binance with Coinbase fallback.
- Asset-aware routing implemented:
  - BTC markets -> BTC signal
  - SOL markets -> SOL signal
- Composite probability from momentum, EMA spread, RSI, and candle structure.
- Emits regime/votes metadata used by entry filters.

### Entry
- Fee-aware net-edge gating enabled.
- Fair-value discount and side-advantage checks enabled.
- Tightened anti-midband settings currently in env:
  - `MIN_PROB_DISTANCE=0.14`
  - `MIN_SIDE_ADVANTAGE=0.10`
  - `FAIR_VALUE_DISCOUNT_PCT=0.07`
  - `BUY_YES_MAX_ENTRY=0.52`
  - `BUY_NO_MIN_ENTRY=0.28`
- Entry window active (currently `75-200s`).

### Exit
- Portfolio-wide open position exit checks (all open slugs every loop).
- Sell-side marking and realism telemetry implemented.
- Stop enforcement upgraded in v5.4 patch set:
  - hard stop cap (`MAX_STOP_PCT`)
  - SL-specific arming delay (`STOP_LOSS_ARMING_DELAY_SECONDS_SL=0`)
  - breach diagnostics (`breach`, `breach_ticks`, `late_exit`)
  - emergency breach exit path for larger stop breaches.

---

## 4) v5.4 Patch Progress

### Patch 1 — SL enforcement / late-exit kill (implemented)
- `MAX_STOP_PCT` hard cap enforced in stop computation.
- SL arming split and reduced for SL path.
- Trigger/limit/log now tied to one stop reference.
- Added detailed SL logs including trigger mark, breach ticks, late-exit flag, and realized stop %.

### Patch 1.1 — emergency SL breach behavior (implemented)
- If breach exceeds threshold, uses more aggressive emergency paper exit behavior.
- Reduced catastrophic tail loss risk further.

### Patch 2 — deterministic house-money runner (implemented + fixups)
- Deterministic partial at trigger:
  - `TP_PRINCIPAL_TRIGGER_PCT=0.22`
  - `TP_PRINCIPAL_SELL_FRAC=0.70`
- Runner arming logs added.
- Runner expiry close wiring/fixups added:
  - `RUNNER_EXPIRY_CLOSE_SEC` integrated
  - runner-specific close note and `RUNNER_CLOSE` log for expiry path.

### Patch 3 — adaptive modes (pending)
- Not yet implemented.

### Patch 4 — kill-switches + immutable stamping (pending)
- Not yet implemented.

---

## 5) Key Env Settings Currently Active (selected)

- `AUTO_TAKE_PROFIT_PCT=0.35`
- `AUTO_STOP_LOSS_PCT=0.18`
- `MAX_STOP_PCT=0.30`
- `STOP_LOSS_ARMING_DELAY_SECONDS_SL=0`
- `STOP_LOSS_FINAL_MINUTE_ONLY=false`
- `TP_PRINCIPAL_TRIGGER_PCT=0.22`
- `TP_PRINCIPAL_SELL_FRAC=0.70`
- `RUNNER_STOP_BUFFER_PCT=0.02`
- `RUNNER_EXPIRY_CLOSE_SEC=20`
- `PENDING_ORDER_TIMEOUT_SEC=15`
- `SERIES_PREFIXES=btc-updown,sol-updown`
- `MAX_CONCURRENT_TRADES=2`

---

## 6) What Is Working Well

1. Catastrophic SL events have been materially reduced after v5.4 stop enforcement.
2. Telemetry quality is much better (breach/late-exit visibility).
3. Deterministic TP runner behavior is now explicit and auditable.
4. Portfolio-wide exit handling is active, reducing missed exits on non-selected slugs.
5. Recent short-window trade quality has improved versus earlier unstable periods.

---

## 7) Remaining Risks / Needed Changes

1. Implement adaptive mode system (Patch 3) with hysteresis.
2. Add daily-loss and consecutive-loss kill switches (Patch 4).
3. Add immutable per-trade runtime/config stamps for exact version attribution.
4. Stabilize one production UI path and reduce monitor-format churn.
5. Run controlled validation block (100–200 closes) and report:
   - expectancy
   - PF
   - drawdown
   - SL breach tick distribution.

---

## 8) Important Output/Analysis Files in Workspace

- `ALL_COLLECTED_DATA.md`
- `DATA_REPORT_2026-03-02.md`
- `VERSION_PERFORMANCE_REPORT_2026-03-02.md`
- `ENGINEERING_HANDOFF.md`
- `FULL_SYSTEM_REPORT_2026-03-02_v54.md` (this file)

---

## 9) Recommended Next Execution Order

1. Patch 3 (adaptive mode system with anti-thrash hysteresis)
2. Patch 4 (risk kill-switch + immutable stamping)
3. Validation run + v5.4 acceptance report

---

## 10) Run Commands

```bat
cd /d C:\Users\johnny\.openclaw\workspace\polymarket_bot
launch_all_v531.bat
```

Hard reset (use carefully):
```bat
hard_reset_v53.bat
```
