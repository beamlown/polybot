# Polymarket Bot — Collected Data (Consolidated)

_Last updated: 2026-03-02 (America/Chicago)_

## 1) Mission / Operating Goal
- Build a Windows-friendly, CMD/.bat-driven Python paper-trading bot for Polymarket.
- Trade the current BTC 5m round deterministically (with broader market candidate support like BTC/SOL).
- Primary KPI: improve overall net PnL while keeping risk controls strict and operations low-noise.

## 2) Constraints & Preferences
- Paper mode now, but execution should stay realistic for eventual live transition.
- Windows-first workflow (CMD/.bat preferred).
- Minimize churn/overtrading; preserve cooldowns/caps and side-logic safeguards.
- Keep risk lifecycle always-on: TP/SL/expiry/max-hold with SL arming delay.
- Monitoring must keep all-time totals accurate even when closed rows are hidden.
- Quiet logs preferred: short BUY/SELL action lines and actionable alerts.

## 3) Current Runtime Context
- Workspace: `C:\Users\johnny\.openclaw\workspace\polymarket_bot`
- Primary engine file: `bot_v5.py`
- DB: `trades_v4.db`
- Current tags in `bot_v5.py`:
  - `BUILD_TAG = "v5.1.2026-03-02.001"`
  - `ENGINE_TAG = "v5_paper_fill_realism"`

## 4) Completed Milestones (High Level)
- v1/v2/v4 foundation completed with discovery hardening, risk lifecycle automation, signal upgrades, and anti-churn controls.
- Monitoring/tooling completed (`pnl_v4.py`, dashboards, sell/reset scripts, close-note and realized PnL handling).
- v5 introduced deterministic Top-N selection, liquidity gates redesign, quiet logs, and provenance markers.

## 5) v5.1 Work Shipped (Latest)
### Exit realism scaffolding
- Added simulated exit flow and telemetry fields:
  - `exit_trigger_price`
  - `exit_fill_price`
  - `slippage_ticks`
  - `fill_delay_ms`
  - `fill_retries`
- Added exit log sequence:
  - `EXIT_TRIGGER`
  - `EXIT_ORDER`
  - `EXIT_FILLED`
- Wired trigger→fill handling into:
  - take-profit
  - stop-loss
  - round expiry
  - expired sweep close
  - max-hold timeout close

### Pricing realism
- Main loop now attempts direct NO-token orderbook reads (`ob.read(no_token_id)`) and uses NO bid/ask when available.
- Fallback marker added:
  - `MARK_FALLBACK | reason=no_quote_for_NO`

### Bot/UI process separation
- Added atomic state writer in bot to:
  - `runtime/state_v5.json`
- Added read-only UI:
  - `ui_v5.py`
- Added launchers:
  - `run_v5_ui.bat`
  - `run_v5_all.bat`

### Validation + commit
- `py -3.14 -m py_compile` passed for `bot_v5.py` and `ui_v5.py`.
- Commit recorded:
  - `fe63c47`
  - _V5.1 paper-fill realism scaffolding: trigger/fill logs, simulated fill fields, NO token bid usage, and separate UI process via state_v5.json_

## 6) In-Progress / Remaining Work
1. Finalize true Top-N multi-slot execution (currently still effectively first selection in execution path).
2. Add strict quote freshness gate (`<=2s`) + explicit stale-skip behavior (`STALE_QUOTE_SKIP`).
3. Tighten close-reason attribution (reduce/avoid over-tagging as `expired_sweep_auto_close`).
4. Add trailing-stop remainder behavior after scale-out TP where still missing.
5. Add outbound push alerting transport (Telegram/webhook/file watcher).

## 7) Known Issues / Risks
- `.env` is gitignored; config drift risk across sessions.
- Occasional Windows process cleanup issue (`Access is denied` when killing stale python).
- Timezone dependency issue seen previously (`tzdata` / `ZoneInfoNotFoundError`).
- Intermittent market data timing mismatches can still occur (Gamma/CLOB timing windows).

## 8) Key Files
- `bot.py`, `bot_v2.py`, `bot_v4.py`, `bot_v5.py`
- `v4_discovery.py`, `v4_orderbook.py`, `v4_signal.py`
- `pnl_v4.py`, `dashboard_v4.py`, `sell_position_v4.py`
- `run_v5.bat`, `run_v5_ui.bat`, `run_v5_all.bat`
- `ui_v5.py`
- `.env` (local, gitignored)

## 9) Useful Run Commands
```bat
cd /d C:\Users\johnny\.openclaw\workspace\polymarket_bot
run_v5.bat
run_v5_ui.bat
```
Or both:
```bat
run_v5_all.bat
```

## 10) Decision Summary
- Keep architecture Windows/CMD-first.
- Optimize for net profitability (quality entries + realistic exits) over raw trade count.
- Prefer CLOB-executable pricing wherever possible.
- Keep automated risk lifecycle and concise operational logging.
- Continue v5.1 path toward full paper execution realism and cleaner operator UX.
