import json, sqlite3, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'trades_v4.db'
RUNTIME = ROOT / 'runtime'
RUNTIME.mkdir(exist_ok=True)

conn = sqlite3.connect(DB)
c = conn.cursor()

def roll(n):
    rows = c.execute("SELECT COALESCE(realized_pnl,0) FROM trades WHERE closed_ts IS NOT NULL ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    vals=[float(r[0] or 0) for r in rows]
    w=sum(1 for v in vals if v>0); l=sum(1 for v in vals if v<0); b=sum(1 for v in vals if abs(v)<1e-12)
    d=w+l; wr=(w/d*100.0) if d else 0.0
    return {"n":len(vals),"wins":w,"losses":l,"breakeven":b,"wr":wr,"pnl":sum(vals)}

open_n = int(c.execute("SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0").fetchone()[0] or 0)
realized = float(c.execute("SELECT COALESCE(SUM(realized_pnl),0) FROM trades WHERE closed_ts IS NOT NULL").fetchone()[0] or 0)
conn.close()

snap = {
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "open_positions": open_n,
    "realized_pnl_all": realized,
    "r25": roll(25),
    "r50": roll(50),
    "r100": roll(100),
}

(RUNTIME / 'kpi_latest.json').write_text(json.dumps(snap), encoding='utf-8')
with (RUNTIME / 'kpi_snapshots.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(snap) + '\n')
print('kpi snapshot written')
