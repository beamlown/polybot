# Polymarket Paper Bot (v1)

This is a **paper-trading** bot scaffold (safe mode by default).
It reads markets, computes simple edge, and logs virtual trades.

## What it does
- Pulls market snapshots (stub/client hook included)
- Applies a simple mispricing strategy
- Enforces bankroll + risk limits
- Logs paper trades to SQLite

## Quick start

1. Install Python 3.10+
2. Install deps:

```bash
pip install -r requirements.txt
```

3. Copy env file:

```bash
copy .env.example .env
```

4. Run in paper mode:

```bash
python bot.py
```

5. (Optional) Test authenticated CLOB SDK connection (no order placement):

```bash
python clob_sdk_test.py
```

## One-click scripts (Windows)
- `setup_bot.bat` → install deps + create `.env`
- `start_bot.bat` → run bot
- `reset_and_run.bat` → clear `trades.db` + run bot
- `status.bat` → show recent paper trades summary
- `live_monitor.bat` → auto-refresh status every 10 seconds
- `cashout.bat` → compute paper realized PnL at current marks, archive DB, reset session
- Set `MAX_DAYS_TO_RESOLUTION` in `.env` to focus only near-term events
- Or set `MAX_HOURS_TO_RESOLUTION` for tighter windows (e.g., `1` = resolves within 1 hour)
- Set `REQUIRE_STARTED=true` to skip not-yet-started markets
- Set `BTC_ONLY=true` to trade only BTC/Bitcoin markets with momentum signal
- Set `BTC_FOCUS_MODE=ultrashort` to only allow BTC “up/down in 5 minutes” style markets (`any` allows all BTC markets)
- Set `FORCE_MARKET_IDS=<id1,id2>` to trade only specific market IDs
- Or set `FORCE_MARKET_SLUG_CONTAINS=<slug-text>` to lock by URL slug text
- Clock stepping: `AUTO_FORCE_SLUG_STEP=true` with `FORCE_SLUG_STEP_SIZE=300` and `FORCE_SLUG_STEP_SECONDS=300`
- Set `AUTO_BTC_5M=true` to auto-rotate into newest BTC 5m up/down events when slugs change
- Set `AUTO_BTC_5M_CLOB_DISCOVERY=true` to discover current BTC 5m slug from CLOB when no force slug is set
- Optional fallback: `ID_STEP_FALLBACK=true` with `ID_STEP_SIZE=300` to try next slug id step (validated before use)
- Set `FORCE_EVENT_SLUG=<event-slug>` to force trading a specific event (bypasses time filters)

## Important
- Starts in `PAPER_MODE=true`.
- Do NOT enable live mode until you validate with enough paper trades.
- Never share your private key in chat; keep it only in your local `.env`.
- This is educational tooling, not financial advice.
