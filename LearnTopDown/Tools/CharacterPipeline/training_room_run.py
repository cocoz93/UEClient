"""Launch the room suite through the shared offscreen render lock."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent

parser = argparse.ArgumentParser()
parser.add_argument('--fps', type=int, choices=(30, 60), required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
output = args.output.resolve()
if not output.is_relative_to(ROOT / 'Saved/QA'):
    raise ValueError('Verification output must be inside this project Saved/QA')
output.parent.mkdir(parents=True, exist_ok=True)
profile = json.loads((TOOLS / 'Profiles/countess.json').read_text(encoding='utf-8'))
profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
# Keep the extra offscreen editor within a bounded texture cache while the user's
# interactive editor remains open. This changes only this process, not asset quality
# settings or the project's runtime configuration.
profile['console_variables'].update({'Sparrow.Skills.IgnoreCooldowns': 1,
                                     'r.Streaming.PoolSize': 512,
                                     'r.Streaming.UseFixedPoolSize': 1,
                                     'r.Shadow.Virtual.MaxPhysicalPages': 1024})
profile_path = output.parent / f'room-profile-{args.fps}.json'
profile_path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
job_path = output.parent / f'room-job-{args.fps}.json'
baseline = ROOT / 'Saved/QA/CharacterPipeline/baseline-training-room-complete-20261015/baseline.json'
if not baseline.is_file():
    baseline = ROOT / 'Saved/QA/CharacterPipeline/baseline-training-room-20261015/baseline.json'
job_path.write_text(json.dumps({'output': str(output), 'fps': args.fps,
    'profile': str(profile_path),
    'baseline': str(baseline)}, indent=2), encoding='utf-8')
environment = dict(os.environ, CHARACTER_PIPELINE_JOB=str(job_path))
command = [sys.executable, str(TOOLS / 'editor_task.py'), str(TOOLS / 'training_room_verify.py'),
           '--output', str(output), '--fps', str(args.fps), '--timeout', '900']
return_code = subprocess.call(command, env=environment)
report_path = output / f'training-room-{args.fps}.json'
report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
print(json.dumps({'passed': return_code == 0 and report.get('passed', False),
                  'report': str(report_path), 'cases': len(report.get('cases', [])),
                  'error': report.get('error')}), flush=True)
raise SystemExit(0 if return_code == 0 and report.get('passed', False) else 1)
