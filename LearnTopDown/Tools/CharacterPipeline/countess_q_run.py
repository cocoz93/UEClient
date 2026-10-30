"""Launch the Q-only A/B presentation comparison without taking OS input."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--fps', type=int, choices=(30,60), default=60)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--script', default='countess_q_compare.py')
parser.add_argument('--material', default='M_CountessQImpactAccent')
parser.add_argument('--baseline', type=Path, default=ROOT/'Saved/QA/CharacterPipeline/baseline-training-room-complete-20261015/baseline.json')
args = parser.parse_args()
script = (TOOLS/args.script).resolve()
if script.parent != TOOLS or not script.is_file():
    raise ValueError('Select an existing CharacterPipeline comparison script')
out = args.output.resolve()
if not out.is_relative_to(ROOT/'Saved/QA'):
    raise ValueError('Output must be inside project Saved/QA')
out.parent.mkdir(parents=True, exist_ok=True)
profile = json.loads((TOOLS/'Profiles/countess.json').read_text())
profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
profile['console_variables'].update({'r.Streaming.PoolSize':512,'r.Streaming.UseFixedPoolSize':1,
                                     'r.Shadow.Virtual.MaxPhysicalPages':1024})
profile_path = out.parent/f'Q-profile-{args.fps}.json'
profile_path.write_text(json.dumps(profile,indent=2))
job_path = out.parent/f'Q-job-{args.fps}.json'
job_path.write_text(json.dumps({'output':str(out),'fps':args.fps,'profile':str(profile_path),
    'baseline':str(args.baseline.resolve())}))
code = subprocess.call([sys.executable,str(TOOLS/'editor_task.py'),str(script),
                       '--output',str(out),'--fps',str(args.fps),'--timeout','600'],
                      env=dict(os.environ,CHARACTER_PIPELINE_JOB=str(job_path)))
path = out/f'countess-q-comparison-{args.fps}.json'
result = json.loads(path.read_text()) if path.is_file() else {}
log=(out/'editor.log').read_text(encoding='utf-8',errors='replace') if (out/'editor.log').is_file() else ''
shader_errors=[line for line in log.splitlines() if args.material in line and
               ('Failed to compile Material' in line or 'Default Material will be used' in line)]
passed = code == 0 and result.get('passed',False) and not shader_errors
launch_result={'passed':passed,'return_code':code,'report_passed':result.get('passed',False),
               'q_material_compile_errors':shader_errors,'q_shader_compile_verified':not shader_errors}
(out/'launch-result.json').write_text(json.dumps(launch_result,indent=2),encoding='utf-8')
print(json.dumps({'passed':passed,'report':str(path),'cases':len(result.get('cases',[])),
                  'error':result.get('error'),'shader_errors':shader_errors}),flush=True)
raise SystemExit(0 if passed else 1)
