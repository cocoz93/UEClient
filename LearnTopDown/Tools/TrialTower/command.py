"""Queue one Python file for the owned editor; result is written asynchronously."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
out = ROOT / 'Saved/QA/TrialTower/session-20261029/queue'
out.mkdir(parents=True, exist_ok=True)
identifier, file = sys.argv[1:3]
destination = out / (identifier + '.request.json')
if destination.exists() or (out / (identifier + '.result.json')).exists():
    raise RuntimeError('Use a new command ID')
destination.write_text(json.dumps({'id': identifier, 'code': Path(file).read_text(encoding='utf-8-sig')}), encoding='utf-8')
print(destination)
