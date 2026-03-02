import json
import os
import time
from pathlib import Path

STATE = Path(__file__).parent / "runtime" / "state_v5.json"


def clear():
    print("\033[2J\033[H", end="")


def main():
    while True:
        clear()
        if not STATE.exists():
            print("WAITING FOR BOT... (no state file)")
            time.sleep(0.2)
            continue
        try:
            d = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            print("WAITING FOR BOT... (state updating)")
            time.sleep(0.2)
            continue

        print(f"ENGINE: {d.get('engine')} | BUILD: {d.get('build')}")
        print(f"NOW: {d.get('now')}")
        print(f"BALANCE: ${d.get('balance_est',0):,.2f} | NET: {d.get('pnl',{}).get('net',0):+.2f}")
        s = d.get('slots', {})
        print(f"SLOTS: open={s.get('open',0)} / max={s.get('max',0)}")
        print("-"*90)
        print("OPEN POSITIONS")
        opens = d.get('open_positions', [])
        if not opens:
            print("(none)")
        else:
            for r in opens:
                print(f"id={r.get('id')} | {r.get('slug')} | {r.get('side')} | entry={r.get('entry')} | rem={r.get('remaining_size')}")
        print("-"*90)
        print("RECENT CLOSES")
        rec = d.get('recent_closed', [])
        if not rec:
            print("(none)")
        else:
            for r in rec:
                print(f"id={r.get('id')} | {r.get('slug')} | {r.get('side')} | {r.get('reason')} | pnl={r.get('pnl_usd'):+.2f}")
        print("-"*90)
        print(d.get('status_line',''))
        time.sleep(0.2)


if __name__ == '__main__':
    main()
