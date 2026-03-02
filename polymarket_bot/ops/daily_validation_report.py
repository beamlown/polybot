import sqlite3, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'trades_v4.db'
RUNTIME = ROOT / 'runtime'
RUNTIME.mkdir(exist_ok=True)

def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute("SELECT COALESCE(realized_pnl,0) FROM trades WHERE closed_ts IS NOT NULL").fetchall()
    vals=[float(r[0] or 0) for r in rows]
    w=sum(1 for v in vals if v>0); l=sum(1 for v in vals if v<0)
    aw=(sum(v for v in vals if v>0)/w) if w else 0.0
    al=(sum(v for v in vals if v<0)/l) if l else 0.0
    pf=(sum(v for v in vals if v>0)/abs(sum(v for v in vals if v<0))) if l else 0.0
    exp=(sum(vals)/len(vals)) if vals else 0.0
    wr=(w/(w+l)*100.0) if (w+l) else 0.0
    conn.close()

    d = datetime.date.today().isoformat()
    p = RUNTIME / f'daily_report_{d}.md'
    p.write_text(
f'''# Daily Validation Report ({d})\n\n- Closed trades: {len(vals)}\n- W/L: {w}/{l} (WR {wr:.1f}%)\n- Avg win: {aw:+.2f}\n- Avg loss: {al:+.2f}\n- Profit factor: {pf:.3f}\n- Expectancy: {exp:+.3f}\n- Net PnL: {sum(vals):+.2f}\n''', encoding='utf-8')
    print(str(p))

if __name__ == '__main__':
    main()
