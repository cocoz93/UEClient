"""Narrow preservation baseline for existing training map, shared assets, and source."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/QA/TrialTower/session-20261029'
BASE = OUT / 'protected-before.json'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def files():
    groups = ['Source', 'Config', 'Content/TopDown/TrainingRoom',
              'Content/__ExternalActors__/TopDown/TrainingRoom', 'Content/__ExternalObjects__/TopDown/TrainingRoom',
              'Content/TopDown/Blueprints']
    return {p.relative_to(ROOT).as_posix(): digest(p) for name in groups for p in (ROOT/name).rglob('*') if p.is_file()}
OUT.mkdir(parents=True, exist_ok=True)
if sys.argv[1] == 'before':
    if BASE.exists():
        raise RuntimeError('Baseline already exists')
    data = files()
    BASE.write_text(json.dumps(data,indent=2),encoding='utf-8')
    source = ROOT / 'Content/TopDown/Blueprints/BP_CountessGameMode.uasset'
    shutil.copy2(source, OUT / 'BP_CountessGameMode.before.uasset')
    print(json.dumps({'protected_files':len(data),'baseline':str(BASE)}))
else:
    before=json.loads(BASE.read_text(encoding='utf-8'))
    current=files()
    changed=[p for p,h in before.items() if current.get(p)!=h]
    allowed=['Content/TopDown/Blueprints/BP_CountessGameMode.uasset']
    unexpected=[p for p in changed if p not in allowed]
    result={'passed':not unexpected,'changed':changed,'unexpected':unexpected,'checked':len(before),'new':[p for p in current if p not in before]}
    (OUT/'protected-after.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
