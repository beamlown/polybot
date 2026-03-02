import json
import time
from pathlib import Path

STATE = Path(__file__).parent / "runtime" / "state_v5.json"

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[90m"
RESET = "\033[0m"

DASH_LINES = 24

def c(v: float) -> str:
    s = f"{v:+.2f}"
    if v > 0:
        return f"{GREEN}{s}{RESET}"
    if v < 0:
        return f"{RED}{s}{RESET}"
    return s

def side(side: str) -> str:
    if side == "BUY_YES":
        return f"{GREEN}UP{RESET}"
    if side == "BUY_NO":
        return f"{RED}DOWN{RESET}"
    return side

def pad(s: str, n: int = 120) -> str:
    raw = s
    if len(raw) < n:
        return raw + " " * (n - len(raw))
    return raw[:n]

def draw_dashboard(d: dict):
    pnl = d.get("pnl", {})
    net = float(pnl.get("net", 0) or 0)
    realized = float(pnl.get("realized_all", 0) or 0)
    unreal = float(pnl.get("unrealized", 0) or 0)
    s = d.get("slots", {})
    opens = d.get("open_positions", [])
    rr = d.get("rolling", {})

    lines = []
    lines.append(f"{CYAN}POLYMARKET V5.3.1 HYBRID MONITOR{RESET}")
    lines.append(f"ENGINE: {d.get('engine')} | BUILD: {d.get('build')} | NOW: {d.get('now')}")
    lines.append(f"BAL REALIZED: ${d.get('balance_est',0):,.2f} | REALIZED: {c(realized)} | OPEN: {c(unreal)} | LIVE: {c(net)} | LIVE BAL: ${d.get('live_balance_est', d.get('balance_est',0)):,.2f}")
    lines.append(f"SLOTS: {s.get('open',0)}/{s.get('max',0)} | TOTAL TRADES: {d.get('total_trades',0)}")
    lines.append("-" * 120)
    lines.append("OPEN POSITIONS")
    lines.append("ID    SIDE   ENTRY    MARK     REMAIN    PNL($)    SLUG")
    if not opens:
        lines.append("(none)")
    else:
        for r in opens[:8]:
            mark = r.get("mark")
            mark_t = f"{float(mark):.4f}" if mark is not None else "n/a"
            p = r.get("pnl_usd")
            ptxt = c(float(p)) if p is not None else "n/a"
            lines.append(f"{str(r.get('id')):<5} {side(str(r.get('side'))):<6} {float(r.get('entry',0)):>7.4f}  {mark_t:>7}  {float(r.get('remaining_size',0)):>8.2f}  {ptxt:>8}  {r.get('slug')}")

    lines.append("-" * 120)
    lines.append("ROLLING")
    for k, lbl in (("r25", "25"), ("r50", "50"), ("r100", "100")):
        x = rr.get(k, {})
        if x:
            lines.append(f"Last {lbl}: W/L={x.get('wins',0)}/{x.get('losses',0)} | WR={float(x.get('wr',0) or 0):.1f}% | PNL={c(float(x.get('pnl',0) or 0))} | N={x.get('n',0)}")
    lines.append("-" * 120)
    lines.append("LIVE FEED (newest events append below)")

    while len(lines) < DASH_LINES:
        lines.append("")

    print("\033[H", end="")
    for i in range(DASH_LINES):
        print(pad(lines[i]))

def main():
    print("\033[2J\033[H", end="")
    seen_close_ids = set()
    last_open_sig = None
    last_state_now = None

    while True:
        if not STATE.exists():
            time.sleep(0.3)
            continue
        try:
            d = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            time.sleep(0.2)
            continue

        draw_dashboard(d)

        now = d.get("now")
        if now != last_state_now:
            last_state_now = now

        opens = d.get("open_positions", [])
        open_sig = tuple((r.get("id"), r.get("mark"), r.get("pnl_usd")) for r in opens)
        if last_open_sig is None:
            last_open_sig = open_sig
        elif open_sig != last_open_sig:
            print(f"{DIM}[OPEN_UPDATE]{RESET} positions repriced | {d.get('now')}")
            last_open_sig = open_sig

        for r in d.get("recent_closed", []):
            rid = r.get("id")
            if rid in seen_close_ids:
                continue
            seen_close_ids.add(rid)
            p = float(r.get("pnl_usd", 0) or 0)
            print(f"CLOSE id={rid} {side(str(r.get('side')))} {r.get('reason')} pnl={c(p)} slug={r.get('slug')}")

        st = d.get("status_line", "")
        if st:
            print(f"{DIM}status: {st}{RESET}")

        time.sleep(0.35)

if __name__ == "__main__":
    main()
