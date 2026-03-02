import json
import os
import shutil
import time
from collections import deque
from pathlib import Path

STATE = Path(__file__).parent / "runtime" / "state_v5.json"

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[90m"
RESET = "\033[0m"

DASH_LINES = 20
FEED_LINES = 8


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


def term_width() -> int:
    try:
        return max(100, min(180, shutil.get_terminal_size((120, 30)).columns))
    except Exception:
        return 120


def crop(s: str, n: int) -> str:
    return s if len(s) <= n else (s[: n - 1] + "…")


def line(n: int, ch: str = "-"):
    return ch * n


def render(d: dict, feed: deque[str]):
    width = term_width()
    pnl = d.get("pnl", {})
    net = float(pnl.get("net", 0) or 0)
    realized = float(pnl.get("realized_all", 0) or 0)
    unreal = float(pnl.get("unrealized", 0) or 0)
    s = d.get("slots", {})
    opens = d.get("open_positions", [])
    rr = d.get("rolling", {})

    out = []
    out.append(f"{CYAN}{line(width, '=')}{RESET}")
    out.append(f"{CYAN} POLYMARKET V5.3.1 HYBRID MONITOR {RESET}")
    out.append(f"{CYAN}{line(width, '=')}{RESET}")
    out.append(crop(f"ENGINE: {d.get('engine')} | BUILD: {d.get('build')} | NOW: {d.get('now')}", width))
    out.append(crop(f"BAL REALIZED: ${d.get('balance_est',0):,.2f} | REALIZED: {c(realized)} | OPEN: {c(unreal)} | LIVE: {c(net)} | LIVE BAL: ${d.get('live_balance_est', d.get('balance_est',0)):,.2f}", width))
    out.append(crop(f"SLOTS: {s.get('open',0)}/{s.get('max',0)} | TOTAL TRADES: {d.get('total_trades',0)}", width))
    out.append(line(width))
    out.append("OPEN POSITIONS")
    out.append("ID    SIDE   ENTRY    MARK     REMAIN    PNL($)    SLUG")
    if not opens:
        out.append("(none)")
    else:
        for r in opens[:6]:
            mark = r.get("mark")
            mark_t = f"{float(mark):.4f}" if mark is not None else "n/a"
            p = r.get("pnl_usd")
            ptxt = c(float(p)) if p is not None else "n/a"
            row = f"{str(r.get('id')):<5} {side(str(r.get('side'))):<6} {float(r.get('entry',0)):>7.4f}  {mark_t:>7}  {float(r.get('remaining_size',0)):>8.2f}  {ptxt:>8}  {r.get('slug')}"
            out.append(crop(row, width))

    out.append(line(width))
    r25 = rr.get("r25", {})
    r50 = rr.get("r50", {})
    r100 = rr.get("r100", {})
    out.append("ROLLING")
    out.append(crop(f"  Last 25  | W/L={r25.get('wins',0)}/{r25.get('losses',0)} | WR={float(r25.get('wr',0) or 0):.1f}% | PNL={c(float(r25.get('pnl',0) or 0))}", width))
    out.append(crop(f"  Last 50  | W/L={r50.get('wins',0)}/{r50.get('losses',0)} | WR={float(r50.get('wr',0) or 0):.1f}% | PNL={c(float(r50.get('pnl',0) or 0))}", width))
    out.append(crop(f"  Last 100 | W/L={r100.get('wins',0)}/{r100.get('losses',0)} | WR={float(r100.get('wr',0) or 0):.1f}% | PNL={c(float(r100.get('pnl',0) or 0))}", width))
    out.append(line(width))
    out.append("LIVE FEED")
    for msg in list(feed)[-FEED_LINES:]:
        out.append(crop(msg, width))

    # pad fixed screen to prevent leftover artifacts
    need = DASH_LINES + FEED_LINES + 12
    while len(out) < need:
        out.append("")

    os.system("cls" if os.name == "nt" else "clear")
    print("\n".join(out))


def main():
    feed = deque(maxlen=120)
    seen_close_ids = set()
    primed = False
    last_open_sig = None
    last_now = None
    last_status = None

    while True:
        if not STATE.exists():
            time.sleep(0.25)
            continue
        try:
            d = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            time.sleep(0.2)
            continue

        now = d.get("now")
        if now != last_now:
            last_now = now

        if not primed:
            for r in d.get("recent_closed", []):
                rid = r.get("id")
                if rid is not None:
                    seen_close_ids.add(rid)
            primed = True

        opens = d.get("open_positions", [])
        open_sig = tuple((r.get("id"), r.get("mark"), r.get("pnl_usd")) for r in opens)
        if last_open_sig is None:
            last_open_sig = open_sig
        elif open_sig != last_open_sig:
            feed.append(f"{DIM}[OPEN_UPDATE]{RESET} positions repriced | {now}")
            last_open_sig = open_sig

        # recent_closed is newest-first; add in reverse so timeline reads older->newer
        new_closes = []
        for r in reversed(d.get("recent_closed", [])):
            rid = r.get("id")
            if rid in seen_close_ids:
                continue
            seen_close_ids.add(rid)
            p = float(r.get("pnl_usd", 0) or 0)
            new_closes.append(
                f"CLOSE id={rid} {side(str(r.get('side')))} {r.get('reason')} pnl={c(p)} slug={r.get('slug')}"
            )
        for m in new_closes:
            feed.append(m)

        st = d.get("status_line", "")
        if st and st != last_status:
            feed.append(f"{DIM}status: {st}{RESET}")
            last_status = st

        render(d, feed)
        time.sleep(0.8)


if __name__ == "__main__":
    main()
