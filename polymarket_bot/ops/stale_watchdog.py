import json, os, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'runtime' / 'state_v5.json'
THRESHOLD_SEC = int(os.getenv('STATE_STALE_SEC', '15'))
AUTO_RESTART = os.getenv('WATCHDOG_AUTO_RESTART', 'false').lower() in ('1','true','yes','on')

if not STATE.exists():
    print('watchdog: state file missing')
    raise SystemExit(0)

age = time.time() - STATE.stat().st_mtime
if age <= THRESHOLD_SEC:
    print(f'watchdog: ok age={age:.1f}s')
    raise SystemExit(0)

print(f'watchdog: STALE age={age:.1f}s threshold={THRESHOLD_SEC}s')
if AUTO_RESTART:
    bat = ROOT / 'launch_all_v531.bat'
    subprocess.Popen(['cmd','/c',str(bat)], cwd=str(ROOT))
    print('watchdog: relaunched')
