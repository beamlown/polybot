import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
kpi = ROOT / 'runtime' / 'kpi_latest.json'
if not kpi.exists():
    print('no kpi_latest.json; run kpi_snapshot first')
    raise SystemExit(0)

d = json.loads(kpi.read_text(encoding='utf-8'))
r25 = d.get('r25', {})
msg = (
    f"PolyBot Summary\n"
    f"ts={d.get('ts')}\n"
    f"open={d.get('open_positions')}\n"
    f"all_realized={d.get('realized_pnl_all',0):+.2f}\n"
    f"r25 W/L={r25.get('wins',0)}/{r25.get('losses',0)} WR={float(r25.get('wr',0) or 0):.1f}% PNL={float(r25.get('pnl',0) or 0):+.2f}"
)
print(msg)

# Optional direct Telegram push (set env vars)
# TELEGRAM_BOT_TOKEN=123:abc
# TELEGRAM_CHAT_ID=5204669508
bot = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
chat = os.getenv('TELEGRAM_CHAT_ID', '').strip()
if bot and chat:
    url = f"https://api.telegram.org/bot{bot}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode('utf-8')
    try:
        with urllib.request.urlopen(url, data=data, timeout=10) as r:
            _ = r.read()
        print('telegram push sent')
    except Exception as e:
        print(f'telegram push failed: {e}')
else:
    print('telegram push skipped (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)')
