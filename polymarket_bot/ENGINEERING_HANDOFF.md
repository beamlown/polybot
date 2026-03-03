# Engineering Handoff — Polymarket Bot (v5.3 / v5.3.1 UI)

**Date:** 2026-03-02  
**Audience:** Engineering / maintainer handoff  
**Runtime focus:** `bot_v5.py` with v5.2+v5.3 logic and v5.3.1 UI layer

---

## 1) Current Runtime Behavior

### Architecture
- Core trading engine: `polymarket_bot/bot_v5.py`
- Discovery: `v4_discovery.py` (active round targeting for 5m markets)
- Orderbook reads: `v4_orderbook.py` (CLOB)
- Signal model: `v4_signal.py` (asset-aware BTC/SOL routing)
- Persistence: SQLite (`trades_v4.db`)
- UI state publication: atomic writer to `runtime/state_v5.json`
- UI readers: `ui_v5.py` / `ui_v531.py`

### Entry logic
- Forecast-driven side selection with directional alignment:
  - `prob > 0.5` favors YES path
  - `prob < 0.5` favors NO path
- Net-edge gating and side constraints:
  - edge computed from executable entry prices
  - fee-aware net-edge filters in v5.2+
- Regime/vote and distance guards:
  - strong regime options, vote thresholds
  - min probability distance from 50/50
- Market quality gates:
  - spread / depth
  - top-book checks
  - anti-churn cooldowns and re-entry controls
- Position sizing:
  - risk % of realized balance, then size from entry price

### Exit logic
- Automated lifecycle includes:
  - partial TP
  - full TP
  - stop loss
  - pre-expiry flatten
  - expiry close
  - stale / max-hold / sweep safety closes
- Exit realism scaffold includes:
  - trigger/fill telemetry
  - simulated fill delay/slippage/retries
  - persisted fields for trigger/fill diagnostics
- Important fix already in place:
  - TP/SL/expiry management runs across **all open slugs each loop**, not only the currently selected candidate slug.

### v5.2 behavior now active
- Side-correct liquidity handling
- USD notional liquidity metrics in orderbook model
- Fee-aware net-edge checks
- Per-asset signal routing (BTC for BTC, SOL for SOL)
- Time-stop + trailing-after-partial stop enhancements

### v5.3 behavior now active
- Scale-in group support added to schema and decision flow
- Group helpers added:
  - open group lookup
  - weighted avg-entry recompute (robust group-wide formula)
  - scale-in count updates

---

## 2) What Works Well

1. **Recent quality improvements are visible**
   - Short rolling windows show stronger W/L and positive PnL bursts.
2. **TP path is the primary positive contributor**
   - Auto TP/partial TP behavior is consistently capturing gains.
3. **Risk lifecycle automation is broad and resilient**
   - Multiple close paths reduce unmanaged residual exposure.
4. **State/UI decoupling works**
   - Atomic `state_v5.json` architecture supports read-only monitors without DB lock/contention pressure.
5. **Engineering cadence is healthy**
   - Frequent, incremental commits and backup snapshots have reduced iteration risk.

---

## 3) Known Issues / Technical Debt

1. **Version attribution is still inferred by timestamps**
   - There is no explicit engine/build snapshot per trade row at entry/close.
2. **UI stability has been iterative**
   - `ui_v531.py` had multiple rapid formatting passes; should be consolidated into one stable production monitor.
3. **State freshness guardrails can be stronger**
   - UI can appear stale if writer cadence degrades; stale-age signaling should be explicit.
4. **Scale-in behavior requires hard risk bounding**
   - Group averaging can increase exposure if market trends against entries.
5. **Fee model is approximate**
   - Net-edge fee handling is simplified and should be validated against exact fill/fee semantics.

---

## 4) Priority Changes Recommended

### P1 — Data integrity and attribution
Add immutable runtime metadata to each trade:
- `engine_tag_at_entry`
- `build_tag_at_entry`
- `config_hash_at_entry`
- and optionally `engine_tag_at_close`

This makes version performance analysis exact (not inferred).

### P1 — Marking and freshness telemetry
- Persist quote age and quote source for open/close marks.
- Show stale-state warning in UI if `state_v5.json` age exceeds threshold.

### P1 — Exit hardening
- Add optional emergency hard TP lock rule.
- Add counters for stale-quote skipped exits.

### P2 — Scale-in safety controls
- Add hard cap on incremental group notional.
- Add max adverse move / max group drawdown guard before additional scale-ins.
- Add cooldown between scale-ins.

### P2 — UI stabilization
- Freeze one canonical UI (v531 or successor) and maintain mode flags:
  - compact
  - detailed
- Reduce format churn and ensure deterministic fixed-grid output.

### P3 — Replay/backtest validation
- Build replay harness from stored trades and quote snapshots.
- Compare expectancy/drawdown before vs after v5.2 and v5.3 changes.

---

## 5) Operational Notes

- Main DB: `trades_v4.db`
- Main runtime state: `runtime/state_v5.json`
- Launchers currently in use:
  - `launch_all_v53.bat`
  - `launch_all_v531.bat`
- Full export/report artifacts available in workspace for external review.

---

## 6) Executive Engineering Summary

The bot has moved from a basic v5 setup to a materially more robust v5.2/v5.3 stack with better exit control, better liquidity realism, fee-aware gating, and scale-in group infrastructure. Recent trade windows indicate clear improvement. The next critical step is to harden attribution and risk boundaries (especially around scale-in), then stabilize one production UI and validate gains with replay-grade analysis.
