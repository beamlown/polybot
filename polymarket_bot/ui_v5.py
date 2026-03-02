import json
import time
from pathlib import Path

STATE = Path(__file__).parent / "runtime" / "state_v5.json"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def clear():
    print("\033[2J\033[H", end="")


def color_pnl(v: float) -> str:
    txt = f"{v:+.2f}"
    if v > 0:
        return f"{GREEN}{txt}{RESET}"
    if v < 0:
        return f"{RED}{txt}{RESET}"
    return txt


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

        net = float(d.get("pnl", {}).get("net", 0) or 0)
        print(f"ENGINE: {d.get('engine')} | BUILD: {d.get('build')}")
        print(f"NOW: {d.get('now')}")
        print(f"BALANCE: ${d.get('balance_est',0):,.2f} | NET: {color_pnl(net)}")
        s = d.get("slots", {})
        print(f"SLOTS: open={s.get('open',0)} / max={s.get('max',0)}")

        print("-" * 90)
        print("OPEN POSITIONS")
        opens = d.get("open_positions", [])
        if not opens:
            print("(none)")
        else:
            for r in opens:
                print(
                    f"id={r.get('id')} | {r.get('slug')} | {r.get('side')} | "
                    f"entry={r.get('entry')} | rem={r.get('remaining_size')}"
                )

        print("-" * 90)
        print("LAST 10 CLOSES")
        rec = d.get("recent_closed", [])[:10]
        if not rec:
            print("(none)")
        else:
            wins = 0
            losses = 0
            pnl10 = 0.0
            for r in rec:
                p = float(r.get("pnl_usd", 0) or 0)
                pnl10 += p
                if p > 0:
                    wins += 1
                elif p < 0:
                    losses += 1
                print(
                    f"id={r.get('id')} | {r.get('slug')} | {r.get('side')} | {r.get('reason')} | pnl={color_pnl(p)}"
                )

            decided = wins + losses
            wr = (wins / decided * 100.0) if decided > 0 else 0.0
            print("-" * 90)
            print(
                f"LAST10 STATS | W/L={wins}/{losses} | WR={wr:.1f}% | PNL={color_pnl(pnl10)}"
            )

        print("-" * 90)
        print(d.get("status_line", ""))
        time.sleep(0.2)


if __name__ == "__main__":
    main()
