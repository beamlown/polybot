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

        pnl = d.get("pnl", {})
        net = float(pnl.get("net", 0) or 0)
        realized = float(pnl.get("realized_all", 0) or 0)
        unreal = float(pnl.get("unrealized", 0) or 0)
        print(f"ENGINE: {d.get('engine')} | BUILD: {d.get('build')}")
        print(f"NOW: {d.get('now')}")
        print(f"BALANCE (REALIZED): ${d.get('balance_est',0):,.2f} | REALIZED PNL: {color_pnl(realized)}")
        print(f"LIVE PNL EST (incl open): {color_pnl(net)} | OPEN PNL: {color_pnl(unreal)} | LIVE BAL EST: ${d.get('live_balance_est', d.get('balance_est',0)):,.2f}")
        s = d.get("slots", {})
        print(f"SLOTS: open={s.get('open',0)} / max={s.get('max',0)}")

        print("-" * 90)
        print("OPEN POSITIONS")
        opens = d.get("open_positions", [])
        if not opens:
            print("(none)")
        else:
            for r in opens:
                pnl = r.get('pnl_usd', None)
                pnl_txt = color_pnl(float(pnl)) if pnl is not None else "n/a"
                mark = r.get('mark', None)
                mark_txt = f"{float(mark):.4f}" if mark is not None else "n/a"
                print(
                    f"id={r.get('id')} | {r.get('slug')} | {r.get('side')} | "
                    f"entry={r.get('entry')} | mark={mark_txt} | rem={r.get('remaining_size')} | pnl={pnl_txt}"
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
        print("ROLLING STATS")
        rr = d.get("rolling", {})
        for k, label in (("r25", "25"), ("r50", "50"), ("r100", "100")):
            x = rr.get(k, {})
            if not x:
                continue
            print(
                f"Last {label}: W/L={x.get('wins',0)}/{x.get('losses',0)} "
                f"WR={float(x.get('wr',0) or 0):.1f}% "
                f"PNL={color_pnl(float(x.get('pnl',0) or 0))} "
                f"N={x.get('n',0)}"
            )

        print("-" * 90)
        print(d.get("status_line", ""))
        time.sleep(0.2)


if __name__ == "__main__":
    main()
