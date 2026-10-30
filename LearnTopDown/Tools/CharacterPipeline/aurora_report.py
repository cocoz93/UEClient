"""Summarize an aurora_skill_probe run: log lines grouped by probe step, then the snapshots (pelvis, positions).
Usage: python aurora_report.py <run folder>"""
import json
from pathlib import Path
import re
import sys

run = Path(sys.argv[1])
KEEP = re.compile(r'AURORA_(?!PROBE)|Kwang hit|Error:|Ensure|Warning: .*Aurora')
step = 'boot'
counts = {}
for line in (run / 'editor.log').read_text(encoding='utf-8', errors='replace').splitlines():
    found = re.search(r'AURORA_PROBE step=(\S+)', line)
    if found:
        step = found.group(1)
        print(f'--- {step}')
        continue
    if KEEP.search(line):
        text = line.split('LogTemp: Display: ')[-1].split('LogPython: ')[-1].strip()
        print('   ', text[:220])
        kind = 'hit' if 'Kwang hit' in text else text.split(' ')[0] + (' ' + text.split(' ')[1].split('=')[0] if ' ' in text else '')
        counts[kind] = counts.get(kind, 0) + 1
print('=== counts', json.dumps(counts, ensure_ascii=False))
data = json.loads((run / 'aurora-skills.json').read_text(encoding='utf-8'))
print('=== passed', data['passed'], (data['error'] or '')[:400])
for entry in data['log']:
    if 'pelvis' in entry:
        print(f"{entry['label']:>14} t={entry['time']:<8} pawn={entry['pawn']:<18} at={entry['pawn_location']} pelvis={entry['pelvis']}")
    else:
        print(f"{entry['label']:>14} {json.dumps({k: v for k, v in entry.items() if k != 'label'})}")
