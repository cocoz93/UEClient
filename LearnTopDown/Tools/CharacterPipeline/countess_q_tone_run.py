"""Launch one Q comparison with a unique job and serialized offscreen rendering."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent
BASE = ROOT/'Saved/QA/CharacterPipeline/q-tone-cape-20261016'
parser = argparse.ArgumentParser()
parser.add_argument('--fps',type=int,choices=(30,60),default=60)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--script',choices=('countess_q_tone_compare.py',),default='countess_q_tone_compare.py')
args = parser.parse_args()
out = args.output.resolve()
assert out.is_relative_to(BASE)
out.parent.mkdir(exist_ok=True,parents=True)
profile = json.loads((TOOLS/'Profiles/countess.json').read_text())
profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
profile['console_variables'].update({'r.Streaming.PoolSize':512,'r.Streaming.UseFixedPoolSize':1,'r.Shadow.Virtual.MaxPhysicalPages':1024})
profile_path = out.parent/(out.name+'-profile.json')
profile_path.write_text(json.dumps(profile,indent=2))
job_path = out.parent/(out.name+'-job.json')
job_path.write_text(json.dumps({'output':str(out),'fps':args.fps,'profile':str(profile_path),'baseline':str(BASE/'baseline-before.json')},indent=2))
code = subprocess.call([sys.executable,str(TOOLS/'editor_task.py'),str(TOOLS/args.script),
    '--output',str(out),'--fps',str(args.fps),'--timeout','600'],
    env=dict(os.environ,CHARACTER_PIPELINE_JOB=str(job_path)))
path = out/f'countess-q-comparison-{args.fps}.json'
result = json.loads(path.read_text()) if path.is_file() else {}
log_path = out/'editor.log'
log = log_path.read_text(encoding='utf-8',errors='replace') if log_path.is_file() else ''
shader_errors = [line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
passed = code==0 and result.get('passed',False) and not shader_errors
(out/'launch-result.json').write_text(json.dumps({'passed':passed,'return_code':code,'report_passed':result.get('passed',False),
    'q_material_compile_errors':shader_errors,'q_shader_compile_verified':not shader_errors},indent=2))
print(json.dumps({'passed':passed,'report':str(path),'cases':len(result.get('cases',[])),'error':result.get('error'),'shader_errors':shader_errors}),flush=True)
raise SystemExit(0 if passed else 1)
