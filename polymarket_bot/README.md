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

## Important
- Starts in `PAPER_MODE=true`.
- Do NOT enable live mode until you validate with enough paper trades.
- This is educational tooling, not financial advice.
