"""Run the W rate comparison in one managed, offscreen PIE editor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
TOOLS=Path(__file__).resolve().parent
BASE=ROOT/'Saved/QA/CharacterPipeline/countess-w-speed-20261016'
parser=argparse.ArgumentParser()
parser.add_argument('--fps',type=int,choices=(30,60),default=60)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--baseline',type=Path,default=BASE/'baseline-before.json')
args=parser.parse_args()
out=args.output.resolve()
if not out.is_relative_to(BASE) or out==BASE:
    raise ValueError('A distinct W speed evidence subdirectory is required')
out.parent.mkdir(parents=True,exist_ok=True)
profile=json.loads((TOOLS/'Profiles/countess.json').read_text(encoding='utf-8'))
profile['map']='/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
profile['console_variables'].update({'r.Streaming.PoolSize':512,'r.Streaming.UseFixedPoolSize':1,
                                   'r.Shadow.Virtual.MaxPhysicalPages':1024,'Countess.Skills.WPlayRate':1.5})
profile_path=out.parent/(out.name+'-profile.json')
profile_path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
job_path=out.parent/(out.name+'-job.json')
job_path.write_text(json.dumps({'output':str(out),'fps':args.fps,'profile':str(profile_path),
                               'baseline':str(args.baseline.resolve())},indent=2),encoding='utf-8')
code=subprocess.call([sys.executable,str(TOOLS/'editor_task.py'),str(TOOLS/'countess_w_speed_compare.py'),
    '--output',str(out),'--fps',str(args.fps),'--timeout','600'],
    env=dict(os.environ,CHARACTER_PIPELINE_JOB=str(job_path)))
path=out/f'countess-w-speed-comparison-{args.fps}.json'
result=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
log=(out/'editor.log').read_text(encoding='utf-8',errors='replace') if (out/'editor.log').is_file() else ''
errors=[line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
module_lines=[line for line in log.splitlines() if "InternalLoadLibrary: 'LearnTopDown'" in line]
modules=sorted(set(re.findall(r'UnrealEditor-LearnTopDown(?:-\d+)?\.dll','\n'.join(module_lines))))
traces=[case.get('data',{}).get('full_simulation_trace') for case in result.get('cases',[])]
traces=[t for t in traces if t]
trace_hashes=len(traces)==2 and all(Path(t['path']).is_file() and
    hashlib.sha256(Path(t['path']).read_bytes()).hexdigest()==t['sha256'] for t in traces)
passed=code==0 and result.get('passed',False) and len(result.get('cases',[]))==10 and not errors and trace_hashes and len(modules)==1
launch={'passed':passed,'return_code':code,'report_passed':result.get('passed',False),
        'shader_compile_errors':errors,'loaded_modules':modules,'module_load_lines':module_lines,
        'full_trace_hashes_passed':trace_hashes,'error':result.get('error')}
(out/'launch-result.json').write_text(json.dumps(launch,indent=2),encoding='utf-8')
print(json.dumps({'passed':passed,'report':str(path),'cases':len(result.get('cases',[])),
                  'loaded_modules':modules,'error':result.get('error')}),flush=True)
raise SystemExit(0 if passed else 1)
