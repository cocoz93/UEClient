"""Launch read-only archer movement/cloth observation in an isolated offscreen editor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fps', type=int, choices=(30, 60), default=60)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    out, baseline = args.output.resolve(), args.baseline.resolve()
    if not out.is_relative_to(ROOT / 'Saved/QA'):
        raise ValueError('Evidence must remain inside project Saved/QA')
    if not baseline.is_file():
        raise ValueError('A current protected baseline is required')
    out.parent.mkdir(parents=True, exist_ok=True)
    profile = json.loads((TOOLS / 'Profiles/sparrow.json').read_text(encoding='utf-8'))
    profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
    profile['console_variables'].update({'r.Streaming.PoolSize': 512, 'r.Streaming.UseFixedPoolSize': 1,
                                         'r.Shadow.Virtual.MaxPhysicalPages': 1024})
    profile_path = out.parent / (out.name + '-profile.json')
    profile_path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
    job_path = out.parent / (out.name + '-job.json')
    job_path.write_text(json.dumps({'output': str(out), 'fps': args.fps, 'profile': str(profile_path),
        'baseline': str(baseline)}, indent=2), encoding='utf-8')
    code = subprocess.call([sys.executable, str(TOOLS / 'editor_task.py'),
        str(TOOLS / 'sparrow_stop_diagnostic.py'), '--output', str(out), '--fps', str(args.fps), '--timeout', '900'],
        env=dict(os.environ, CHARACTER_PIPELINE_JOB=str(job_path)))
    path = out / f'sparrow-stop-diagnostic-{args.fps}.json'
    result = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    log_path = out / 'editor.log'
    log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.is_file() else ''
    shader_errors = [line for line in log.splitlines() if 'Failed to compile Material' in line or
                     'Default Material will be used' in line]
    traces = [row.get('data', {}).get('full_simulation_trace') for row in result.get('cases', [])]
    traces_complete = len(traces) == 13 and all(row and Path(row['path']).is_file() and
        hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'] for row in traces)
    passed = code == 0 and result.get('passed', False) and traces_complete and not shader_errors
    (out / 'launch-result.json').write_text(json.dumps({'passed': passed, 'return_code': code,
        'report_passed': result.get('passed', False), 'case_count': len(result.get('cases', [])),
        'full_traces_complete': traces_complete, 'shader_compile_errors': shader_errors}, indent=2), encoding='utf-8')
    print(json.dumps({'passed': passed, 'report': str(path), 'cases': len(result.get('cases', [])),
        'error': result.get('error'), 'shader_errors': shader_errors}), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
