"""Run the regular bow comparison in one managed offscreen PIE editor."""
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
BASE=ROOT/'Saved/QA/CharacterPipeline/sparrow-basic-natural-20261016'
parser=argparse.ArgumentParser()
parser.add_argument('--fps',type=int,choices=(30,60),default=60)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--baseline',type=Path,default=BASE/'baseline-before.json')
args=parser.parse_args()
out=args.output.resolve()
assert out.is_relative_to(BASE) and out!=BASE
profile=json.loads((TOOLS/'Profiles/countess.json').read_text(encoding='utf-8'))
profile['map']='/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
profile['console_variables'].update({'r.Streaming.PoolSize':512,'r.Streaming.UseFixedPoolSize':1,
 'r.Shadow.Virtual.MaxPhysicalPages':1024,'Sparrow.Attack.Natural':1})
profile_path=out.parent/(out.name+'-profile.json')
profile_path.write_text(json.dumps(profile,indent=2),encoding='utf-8')
job_path=out.parent/(out.name+'-job.json')
job_path.write_text(json.dumps({'output':str(out),'fps':args.fps,'profile':str(profile_path),
 'baseline':str(args.baseline.resolve())},indent=2),encoding='utf-8')
code=subprocess.call([sys.executable,str(TOOLS/'editor_task.py'),str(TOOLS/'sparrow_basic_attack_compare.py'),
 '--output',str(out),'--fps',str(args.fps),'--timeout','720'],
 env=dict(os.environ,CHARACTER_PIPELINE_JOB=str(job_path)))
report_path=out/f'sparrow-basic-natural-{args.fps}.json'
report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
log=(out/'editor.log').read_text(encoding='utf-8',errors='replace') if (out/'editor.log').is_file() else ''
errors=[line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
modules=sorted(set(re.findall(r'UnrealEditor-LearnTopDown(?:-\d+)?\.dll',
 '\n'.join(line for line in log.splitlines() if "InternalLoadLibrary: 'LearnTopDown'" in line))))
traces=[case.get('data',{}).get('full_simulation_trace') for case in report.get('cases',[])]
trace_hashes=len(traces)==14 and all(t and Path(t['path']).is_file() and
 hashlib.sha256(Path(t['path']).read_bytes()).hexdigest()==t['sha256'] for t in traces)
passed=code==0 and report.get('passed',False) and len(report.get('cases',[]))==14 and not errors and trace_hashes and len(modules)==1
result={'passed':passed,'return_code':code,'report_passed':report.get('passed',False),
 'cases':len(report.get('cases',[])),'trace_hashes_passed':trace_hashes,
 'loaded_modules':modules,'shader_compile_errors':errors,'error':report.get('error'),'failed_case':report.get('failed_case')}
(out/'launch-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
raise SystemExit(0 if passed else 1)
