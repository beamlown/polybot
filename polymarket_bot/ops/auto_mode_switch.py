import datetime
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KPI = ROOT / 'runtime' / 'kpi_latest.json'
PROFILES = ROOT / 'profiles'
ENV = ROOT / '.env'
BACKUPS = ROOT / 'backups'
BACKUPS.mkdir(exist_ok=True)

if not KPI.exists():
    print('auto_mode: no kpi_latest.json')
    raise SystemExit(0)

d = json.loads(KPI.read_text(encoding='utf-8'))
r25 = d.get('r25', {})
wr = float(r25.get('wr', 0) or 0)
pnl = float(r25.get('pnl', 0) or 0)

# Decision policy based on last 25 closes
if wr < 35.0 and pnl < 0:
    mode = 'conservative'
elif wr > 60.0 and pnl > 10.0:
    mode = 'aggressive'
else:
    mode = 'neutral'

src = PROFILES / f'{mode}.env'
if not src.exists():
    print(f'auto_mode: missing profile {src}')
    raise SystemExit(1)

ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
if ENV.exists():
    shutil.copy2(ENV, BACKUPS / f'env_auto_{ts}.env')
shutil.copy2(src, ENV)

status = {
    'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'mode': mode,
    'wr25': wr,
    'pnl25': pnl,
}
(ROOT / 'runtime' / 'mode_decision.json').write_text(json.dumps(status), encoding='utf-8')
print(f"auto_mode: applied {mode} (wr25={wr:.1f} pnl25={pnl:+.2f})")

# Optional auto-restart to apply mode immediately
if os.getenv('AUTO_MODE_RESTART', 'false').lower() in ('1','true','yes','on'):
    bat = ROOT / 'launch_all_v531.bat'
    subprocess.Popen(['cmd', '/c', str(bat)], cwd=str(ROOT))
    print('auto_mode: relaunched')
