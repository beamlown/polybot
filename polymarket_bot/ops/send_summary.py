import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
kpi = ROOT / 'runtime' / 'kpi_latest.json'
if not kpi.exists():
    print('no kpi_latest.json; run kpi_snapshot first')
    raise SystemExit(0)

d = json.loads(kpi.read_text(encoding='utf-8'))
r25 = d.get('r25', {})
print(f"SUMMARY | ts={d.get('ts')} | open={d.get('open_positions')} | all_realized={d.get('realized_pnl_all',0):+.2f} | r25={r25.get('wins',0)}/{r25.get('losses',0)} wr={float(r25.get('wr',0) or 0):.1f}% pnl={float(r25.get('pnl',0) or 0):+.2f}")
print('Tip: wire this output into message tool send if you want push delivery from scheduler context.')
