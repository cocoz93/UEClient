"""Run character inspection and regression suites without historical Saved/QA inputs."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
from pathlib import Path
import subprocess

from baseline import PROJECT, verify
from render_lock import render_slot
from presentation_contract import validate_contract, presentation_status, completion_status, sha256

TOOLS = Path(__file__).resolve().parent


def run_editor(engine: Path, profile: Path, baseline: Path, output: Path, suite: str, fps: int) -> dict:
    with render_slot(PROJECT):
        return _run_editor(engine, profile, baseline, output, suite, fps)


def _run_editor(engine: Path, profile: Path, baseline: Path, output: Path, suite: str, fps: int) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    job = output / 'job.json'
    job.write_text(json.dumps({'profile': str(profile), 'baseline': str(baseline),
                               'output': str(output), 'suite': suite, 'fps': fps}), encoding='utf-8')
    environment = dict(os.environ, CHARACTER_PIPELINE_JOB=str(job))
    environment['UE-LocalDataCachePath'] = str(PROJECT / 'Saved/CharacterPipelineDDC')
    script = TOOLS / (suite + '.py')
    if not script.exists():
        script = TOOLS / 'Suites' / (suite + '.py')
    log = output / 'editor.log'
    arguments = [str(engine / 'Engine/Binaries/Win64/UnrealEditor.exe'),
                 str(PROJECT / 'LearnTopDown.uproject'), '-RenderOffscreen', '-unattended',
                 '-nop4', '-nosplash', '-NoLiveCoding', '-NoAutoSave', '-windowed',
                 '-ResX=960', '-ResY=720', '-UseFixedTimeStep', '-FPS=' + str(fps),
                 '-AudioMixer', '-ddc=InstalledNoZenLocalFallback',
                 '-ShaderWorkingDir=' + str(PROJECT / 'Saved/ShaderWork'), '-abslog=' + str(log)]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    # Unreal parses ExecCmds from its raw Windows command line, before argv unescaping.
    command_line = subprocess.list2cmdline(arguments) + ' -ExecCmds="py ' + script.as_posix() + '"'
    process = subprocess.Popen(command_line, env=environment, startupinfo=startup)
    (output / 'process.json').write_text(json.dumps({'pid': process.pid, 'log': str(log)}), encoding='utf-8')
    try:
        return_code = process.wait(timeout=420)
    except subprocess.TimeoutExpired:
        # Only this pipeline's own unattended editor is stopped on timeout.
        process.terminate()
        process.wait(timeout=30)
        raise RuntimeError(f'{suite}: unattended editor timed out; log: {log}')
    report_names = {'inspect_character': 'inspection.json', 'install_profile': 'installation.json', 'countess_skills': f'runtime-skills-{fps}.json',
                    'countess_combo': 'combo-regression.json', 'countess_input': 'input-regression.json',
                    'countess_movement': f'movement-{fps}.json',
                    'sparrow_startup': f'sparrow-startup-{fps}.json',
                    'character_switch': f'character-switch-{fps}.json',
                    'sparrow_movement': f'sparrow-movement-{fps}.json',
                    'sparrow_combat': f'sparrow-combat-{fps}.json',
                    'sparrow_skills': f'sparrow-skills-{fps}.json',
                    'sparrow_field_presentation': f'sparrow-field-presentation-{fps}.json',
                    'sparrow_pose': f'sparrow-pose-{fps}.json',
                    'character_visual_quality': f'character-visual-quality-{fps}.json',
                    'sparrow_presentation': f'sparrow-presentation-{fps}.json'}
    report_path = output / report_names[suite]
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}
    result = {'suite': suite, 'fps': fps, 'return_code': return_code,
              'passed': return_code == 0 and report.get('passed', False),
              'report': str(report_path), 'log': str(log),
              'case_count': len(report.get('cases', [])), 'check_count': len(report.get('checks', []))}
    if report_path.exists():
        result['report_sha256'] = sha256(report_path)
    if not result['passed']:
        result['error'] = report.get('error', 'No successful report; inspect editor log')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('inspect', 'install', 'verify', 'review'))
    parser.add_argument('--profile', type=Path, default=TOOLS / 'Profiles/countess.json')
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--engine', type=Path, default=Path('C:/Program Files/Epic Games/UE_5.8'))
    parser.add_argument('--fps', type=int, choices=(30, 60), nargs='+', default=[30, 60])
    parser.add_argument('--suites', nargs='+', help='Run only selected profile suites, for scoped retries')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--visual-review', type=Path, help='Reviewed screenshot/asset fingerprint manifest')
    arguments = parser.parse_args()
    if arguments.action == 'review':
        if not arguments.output or not arguments.visual_review:
            raise ValueError('Review requires the existing result directory and visual review manifest')
        directory = arguments.output.resolve()
        if not directory.is_relative_to(PROJECT / 'Saved/QA'):
            raise ValueError('Review result must remain inside this project Saved/QA')
        summary_path = directory / 'summary.json'
        report = json.loads(summary_path.read_text(encoding='utf-8'))
        profile = json.loads(arguments.profile.read_text(encoding='utf-8'))
        if not report.get('functional_passed') or report.get('profile_sha256') != sha256(arguments.profile):
            raise ValueError('Functional verification failed or its profile has changed')
        if Path(report['baseline']).resolve() != arguments.baseline.resolve():
            raise ValueError('Review must use the baseline from functional verification')
        required = {(suite, fps) for suite in profile['suites']
                    if suite != 'inspect_character' for fps in [30, 60]}
        actual = {(row['suite'], row['fps']) for row in report['results']}
        inspections = {(suite, rate) for suite, rate in actual if suite == 'inspect_character'}
        if actual - inspections != required or ('inspect_character' in profile['suites'] and
                (len(inspections) != 1 or next(iter(inspections))[1] not in (30, 60))):
            raise ValueError('Completion review requires every profile suite at 30/60 FPS')
        for row in report['results']:
            path = Path(row['report']).resolve()
            if not row['passed'] or not path.is_relative_to(directory) or sha256(path) != row.get('report_sha256'):
                raise ValueError('Functional evidence missing or changed: ' + str(path))
        report['baseline_after'] = verify(arguments.baseline)
        if not report['baseline_after']['passed']:
            raise ValueError('Protected assets changed after functional verification')
        report['presentation'] = presentation_status(PROJECT, arguments.profile.resolve(), arguments.visual_review)
        report['completion_status'] = completion_status(True, report['presentation'])
        summary_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'completion_status': report['completion_status'], 'summary': str(summary_path)}), flush=True)
        return 0 if report['completion_status'] == 'complete' else 1
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    output = (arguments.output or PROJECT / 'Saved/QA/CharacterPipeline' / timestamp).resolve()
    if not output.is_relative_to(PROJECT / 'Saved/QA'):
        raise ValueError('Output must be inside this project Saved/QA')
    output.mkdir(parents=True, exist_ok=False)
    profile = json.loads(arguments.profile.read_text(encoding='utf-8'))
    available_suites = {'inspect_character', 'countess_skills', 'countess_combo', 'countess_input', 'countess_movement',
                        'character_switch', 'sparrow_startup', 'sparrow_movement', 'sparrow_combat', 'sparrow_skills', 'sparrow_presentation',
                        'sparrow_field_presentation', 'sparrow_pose', 'character_visual_quality'}
    if profile.get('schema_version') != 1 or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', profile.get('character_id', '')):
        raise ValueError('Invalid character profile schema or identifier')
    if any(suite not in available_suites for suite in profile.get('suites', [])):
        raise ValueError('Profile refers to an unregistered verification suite')
    validate_contract(profile)
    for content_root in profile['required_content_roots']:
        if not (PROJECT / 'Content' / content_root).is_dir():
            raise FileNotFoundError(f'Required content is not installed: {content_root}')
    baseline_check = verify(arguments.baseline)
    if not baseline_check['passed']:
        raise RuntimeError(f'Baseline mismatch before verification: {baseline_check["mismatches"]}')
    results = []
    suites = {'inspect': ['inspect_character'], 'install': ['install_profile']}.get(arguments.action, profile['suites'])
    if arguments.suites:
        if arguments.action != 'verify' or any(suite not in profile['suites'] for suite in arguments.suites):
            raise ValueError('Selected suites must belong to this character profile')
        suites = arguments.suites
    report = {'passed': False, 'functional_passed': False, 'completion_status': 'running',
              'character_id': profile['character_id'], 'profile_sha256': sha256(arguments.profile),
              'baseline': str(arguments.baseline.resolve()), 'results': results}
    for suite in suites:
        frame_rates = [arguments.fps[0]] if suite in ('inspect_character', 'install_profile') else arguments.fps
        for fps in frame_rates:
            print(f'START {suite} {fps} fps', flush=True)
            try:
                result = run_editor(arguments.engine, arguments.profile.resolve(), arguments.baseline.resolve(),
                                    output / f'{suite}-{fps}', suite, fps)
            except Exception as error:
                report.update(completion_status='functional_failure', error=str(error), failed_suite=suite, failed_fps=fps)
                (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                raise
            results.append(result)
            print(json.dumps(result), flush=True)
            if not result['passed']:
                report['completion_status'] = 'functional_failure'
            (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            if not result['passed']:
                raise RuntimeError(result.get('error'))
    report['baseline_after'] = verify(arguments.baseline)
    report['passed'] = all(result['passed'] for result in results) and report['baseline_after']['passed']
    report['functional_passed'] = report['passed']
    report['presentation'] = presentation_status(PROJECT, arguments.profile.resolve(), arguments.visual_review)
    report['completion_status'] = completion_status(report['functional_passed'], report['presentation'])
    report['scope'] = 'full_profile' if set(suites) == set(profile['suites']) and set(arguments.fps) == {30, 60} else 'selected_suites_or_frame_rates'
    if report['completion_status'] == 'complete' and report['scope'] != 'full_profile':
        report['completion_status'] = 'scoped_verification_complete'
    (output / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'functional_passed': report['passed'], 'completion_status': report['completion_status'],
                      'summary': str(output / 'summary.json')}), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
