"""Run the textured W comparison in a separate offscreen editor."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--fps', type=int, choices=(30, 60), default=60)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
if not out.is_relative_to(ROOT / 'Saved/QA'):
    raise ValueError('Evidence must stay inside project Saved/QA')
out.parent.mkdir(parents=True, exist_ok=True)
profile = json.loads((TOOLS / 'Profiles/countess.json').read_text(encoding='utf-8'))
profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
profile['console_variables'].update({'r.Streaming.PoolSize': 512, 'r.Streaming.UseFixedPoolSize': 1,
                                     'r.Shadow.Virtual.MaxPhysicalPages': 1024})
profile_path = out.parent / (out.name + '-profile.json')
profile_path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
job_path = out.parent / (out.name + '-job.json')
job_path.write_text(json.dumps({'output': str(out), 'fps': args.fps, 'profile': str(profile_path),
    'baseline': str(out.parent / 'baseline-before.json')}, indent=2), encoding='utf-8')
code = subprocess.call([sys.executable, str(TOOLS / 'editor_task.py'),
                       str(TOOLS / 'countess_w_compare.py'), '--output', str(out),
                       '--fps', str(args.fps), '--timeout', '600'],
                       env=dict(os.environ, CHARACTER_PIPELINE_JOB=str(job_path)))
path = out / f'countess-w-comparison-{args.fps}.json'
result = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
log = (out / 'editor.log').read_text(encoding='utf-8', errors='replace')
errors = [line for line in log.splitlines() if 'Failed to compile Material' in line or
          'Default Material will be used' in line]
passed = code == 0 and result.get('passed', False) and not errors
(out / 'launch-result.json').write_text(json.dumps({'passed': passed, 'return_code': code,
    'shader_compile_errors': errors, 'report_passed': result.get('passed', False)}, indent=2), encoding='utf-8')
print(json.dumps({'passed': passed, 'report': str(path), 'cases': len(result.get('cases', [])),
                  'error': result.get('error'), 'shader_errors': errors}), flush=True)
raise SystemExit(0 if passed else 1)
