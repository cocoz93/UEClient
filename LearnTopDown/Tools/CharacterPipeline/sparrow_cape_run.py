"""Serial offscreen old/new Rogue cape comparison; never launch concurrent editors."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reused_old_evidence(directory, target_fps, baseline):
    """Revalidate completed old evidence in place; never copy or rewrite it."""
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT / 'Saved/QA'):
        raise ValueError('Reused cape evidence must remain inside project Saved/QA')
    paths = {'report': directory / f'sparrow-cape-{target_fps}.json',
             'launch': directory / 'launch-result.json', 'process_result': directory / 'process-result.json',
             'editor_log': directory / 'editor.log', 'job': directory.parent / (directory.name + '-job.json')}
    assert all(path.is_file() for path in paths.values()), 'Completed old evidence and its original job must exist.'
    report, launch, process, job = (load(paths[key]) for key in ('report', 'launch', 'process_result', 'job'))
    assert report['passed'] and report['cape_variant'] == 0 and len(report['cases']) == 13
    assert report['protected_files_match'] and report['baseline_after']['passed']
    assert not report['baseline_after']['mismatches']
    assert launch['passed'] and launch['variant'] == 0 and launch['return_code'] == 0
    assert launch['case_count'] == 13 and not launch.get('shader_compile_errors')
    assert process['return_code'] == 0 and not process['timed_out']
    assert job['fps'] == target_fps and job['cape_variant'] == 0
    original_baseline = Path(job['baseline'])
    current_baseline = Path(baseline).resolve()
    assert load(original_baseline)['protected_hashes'] == load(current_baseline)['protected_hashes'], 'Old and current protected baseline contracts differ.'
    from baseline import verify
    current_protection = verify(current_baseline)
    assert current_protection['passed'], 'Protected source assets no longer match the reused old baseline.'
    descriptors = []
    for case in report['cases']:
        assert case['passed']
        descriptor = case['data']['full_simulation_trace']
        path = Path(descriptor['path'])
        assert path.resolve().is_relative_to(directory) and digest(path) == descriptor['sha256']
        trace = load(path)
        assert trace['cape_variant'] == 0 and trace['fps'] == target_fps and trace['case'] == case['name']
        assert len(trace['samples']) == descriptor['samples']
        descriptors.append(descriptor)
    captures = []
    assert report['capture_integrity']['passed']
    assert report['capture_integrity']['checked'] == len(report['screenshots'])
    for shot in report['screenshots']:
        path = Path(shot['image'])
        assert path.resolve().is_relative_to(directory) and digest(path) == shot['sha256']
        captures.append({'path': str(path), 'sha256': shot['sha256']})
    log = paths['editor_log'].read_text(encoding='utf-8', errors='replace')
    mode_lines = [line for line in log.splitlines() if 'SparrowCape mode=0' in line]
    assert mode_lines and all('wind_applied=0' in line for line in mode_lines)
    module_lines = [line for line in log.splitlines() if "InternalLoadLibrary: 'LearnTopDown'" in line]
    modules = sorted(set(re.findall(r'UnrealEditor-LearnTopDown(?:-\d+)?\.dll', '\n'.join(module_lines))))
    assert len(modules) == 1, 'Original old module must be identifiable from its actual editor load log.'
    return {'passed': True, 'directory': str(directory), 'source_module': modules[0],
            'artifacts': {key: {'path': str(path), 'sha256': digest(path)} for key, path in paths.items()},
            'source_module_log_lines': module_lines, 'case_count': 13, 'full_traces_checked': descriptors,
            'native_captures_checked': captures, 'protected_before_contract_equal': True,
            'current_protected_source_match': current_protection,
            'original_baseline': {'path': str(original_baseline), 'sha256': digest(original_baseline)},
            'current_baseline': {'path': str(current_baseline), 'sha256': digest(current_baseline)},
            'copied_or_rewritten': False,
            'scope_limit': 'Completed mode-0 evidence is revalidated in place. New point-wind assertions were not executed by the old runner; the old binary is not represented as the new binary.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fps', type=int, choices=(30, 60), default=60)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--new-only', action='store_true', help='Run only the new variant; no paired comparison claim.')
    parser.add_argument('--reuse-old', type=Path, help='Read an existing completed old run in place, then execute only a fresh new run.')
    parser.add_argument('--wind-speed', type=float, default=None, help='Override new variant target airflow, 0..200 cm/s, at pawn spawn.')
    parser.add_argument('--damping', type=float, default=None, help='Override new variant global damping, 0.06..0.15, at pawn spawn.')
    parser.add_argument('--local-damping', type=float, default=None, help='Override new variant local damping, 0.10..0.25, at pawn spawn.')
    args = parser.parse_args()
    cvar_overrides = {}
    for option, value, cvar, minimum, maximum in (
            ('--wind-speed', args.wind_speed, 'Sparrow.Cloth.WindSpeed', 0, 200),
            ('--damping', args.damping, 'Sparrow.Cloth.Damping', .06, .15),
            ('--local-damping', args.local_damping, 'Sparrow.Cloth.LocalDamping', .10, .25)):
        if value is not None:
            if not math.isfinite(value) or not minimum <= value <= maximum:
                parser.error(f'{option} must be finite and within {minimum}..{maximum}.')
            cvar_overrides[cvar] = value
    out, baseline = args.output.resolve(), args.baseline.resolve()
    if not out.is_relative_to(ROOT / 'Saved/QA'):
        raise ValueError('Cape evidence must remain inside project Saved/QA')
    if not baseline.is_file():
        raise ValueError('A protected current project baseline is required')
    if args.new_only and args.reuse_old:
        raise ValueError('--new-only and --reuse-old describe different evidence scopes and cannot be combined.')
    reused_old = reused_old_evidence(args.reuse_old, args.fps, baseline) if args.reuse_old else None
    out.mkdir(parents=True, exist_ok=False)
    launches = []
    for mode, variant in ((('new', 1),) if args.new_only or args.reuse_old else (('old', 0), ('new', 1))):
        child = out / mode
        profile = load(TOOLS / 'Profiles/sparrow.json')
        profile['map'] = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
        profile['console_variables'].update({'r.Streaming.PoolSize': 512, 'r.Streaming.UseFixedPoolSize': 1,
            'r.Shadow.Virtual.MaxPhysicalPages': 1024, 'Sparrow.Cloth.Presentation': variant})
        applied_overrides = cvar_overrides if variant else {}
        profile['console_variables'].update(applied_overrides)
        profile_path = out / (mode + '-profile.json')
        profile_path.write_text(json.dumps(profile, indent=2), encoding='utf-8')
        job_path = out / (mode + '-job.json')
        job_path.write_text(json.dumps({'output': str(child), 'fps': args.fps, 'profile': str(profile_path),
            'baseline': str(baseline), 'cape_variant': variant}, indent=2), encoding='utf-8')
        code = subprocess.call([sys.executable, str(TOOLS / 'editor_task.py'),
            str(TOOLS / 'sparrow_cape_compare.py'), '--output', str(child), '--fps', str(args.fps), '--timeout', '900'],
            env=dict(os.environ, CHARACTER_PIPELINE_JOB=str(job_path)))
        report_path = child / f'sparrow-cape-{args.fps}.json'
        report = load(report_path) if report_path.is_file() else {}
        log_path = child / 'editor.log'
        log = log_path.read_text(encoding='utf-8', errors='replace') if log_path.is_file() else ''
        shader_errors = [line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
        descriptors = [case.get('data', {}).get('full_simulation_trace') for case in report.get('cases', [])]
        traces_passed = len(descriptors) == 13 and all(descriptor and Path(descriptor['path']).is_file()
            and hashlib.sha256(Path(descriptor['path']).read_bytes()).hexdigest() == descriptor['sha256'] for descriptor in descriptors)
        mode_lines = [line for line in log.splitlines() if 'SparrowCape mode=' + str(variant) in line]
        configuration_logged = bool(mode_lines)
        point_lines = [line for line in log.splitlines() if 'SparrowCapePointWind registered=' in line]
        point_rows = [{key: float(value) for key, value in re.findall(r'(\w+)=([+-]?\d+(?:\.\d+)?)', line)} for line in point_lines]
        point_queries_passed = None
        flutter_start_lines = [line for line in log.splitlines() if 'SparrowCapeFlutter start owner=' in line]
        flutter_stop_lines = [line for line in log.splitlines() if 'SparrowCapeFlutter stop owner=' in line]
        flutter_validation = None
        # This is the interactor's queued configuration; do not claim a solver readback.
        if variant:
            configuration_logged &= any('wind_applied=1' in line for line in mode_lines)
            if any('legacy_wind=1' in line for line in mode_lines):
                targets = [float(value) for line in mode_lines for value in re.findall(r'requested_wind_speed_cm_s=([\d.]+)', line)]
                point_queries_passed = bool(point_rows) and bool(targets) and all(
                    row.get('registered') == 1 and row.get('mesh_wind_enabled') == 1
                    and row.get('mesh_query_in_range') == 1 and row.get('mesh_query_weight', 0) > 0
                    and row.get('outside_query_in_range') == 0 and row.get('outside_query_weight', 0) == 0
                    and abs(row.get('radius_cm', 0) - 20) < .001 and abs(row.get('offset_cm', 0) - 5) < .001
                    and any(abs(row.get('source_equivalent_legacy_cm_s', -1000) - target) < .02 for target in targets)
                    and abs(row.get('source_speed_scene_m_s', -1) * .9375 * 100 * 25 - row.get('source_equivalent_legacy_cm_s', -1000)) < .02
                    for row in point_rows)
                configuration_logged &= point_queries_passed
                starts = {}
                for line in flutter_start_lines:
                    owner = re.search(r'SparrowCapeFlutter start owner=(\S+)', line).group(1)
                    values = {key: float(value) for key, value in re.findall(r'(\w+)=([+-]?\d+(?:\.\d+)?)', line)}
                    starts.setdefault(owner, []).append(values)
                stops = {}
                for line in flutter_stop_lines:
                    owner = re.search(r'SparrowCapeFlutter stop owner=(\S+)', line).group(1)
                    values = {key: float(value) for key, value in re.findall(r'(\w+)=([+-]?\d+(?:\.\d+)?)', line)}
                    stops.setdefault(owner, []).append(values)
                from sparrow_cape_compare import pulse_values, pulse_fit
                start_values_passed = bool(starts) and all(len(values) == 1 for values in starts.values())
                for owner, values in starts.items():
                    row = values[0]
                    target, lateral = pulse_values(0, row['max_wind_speed_cm_s'])
                    falloff = 1 - (25 + lateral * lateral) / 400
                    start_values_passed &= abs(row.get('interval_seconds', -1) - .05) < .000001
                    start_values_passed &= row.get('max_once_per_frame') == 1
                    start_values_passed &= abs(row.get('initial_lateral_cm', -100) - lateral) < .00001
                    start_values_passed &= abs(row.get('initial_source_equivalent_legacy_cm_s', -1000) - target) < .02
                    start_values_passed &= abs(row.get('initial_source_speed_scene_m_s', -1) * falloff * 2500 - target) < .02
                timer_cleanup_passed = bool(starts) and all(
                    owner in stops and any(row.get('active_timer_after_cleanup') == 0
                        and row.get('time', -1) >= values[0]['start_time'] for row in stops[owner])
                    for owner, values in starts.items())
                phase_checks, phase_errors, clock_deltas = 0, [], []
                for descriptor in descriptors:
                    if not descriptor or not Path(descriptor['path']).is_file():
                        continue
                    for sample in load(Path(descriptor['path']))['samples']:
                        for source in sample.get('cape_observation', {}).get('owner_wind_sources', []):
                            phase_checks += 1
                            owner = source['owner_name']
                            if owner not in starts:
                                phase_errors.append({'owner': owner, 'time': sample['time'], 'reason': 'Native pulse start log absent.'})
                                continue
                            start = starts[owner][0]
                            native_age = sample['time'] - start['start_time']
                            fit = pulse_fit(native_age, start['max_wind_speed_cm_s'],
                                source['computed_equivalent_legacy_wind_cm_per_second'], source['relative_location_cm'][0], args.fps)
                            clock_deltas.append(abs(native_age - source['pawn_creation_age_seconds']))
                            if not fit['matches']:
                                phase_errors.append({'owner': owner, 'time': sample['time'], 'fit': fit})
                phase_passed = phase_checks > 0 and not phase_errors and max(clock_deltas, default=1000) <= 1 / args.fps + .00001
                flutter_validation = {'passed': bool(start_values_passed and timer_cleanup_passed and phase_passed),
                    'native_start_owner_count': len(starts), 'native_stop_owner_count': len(stops),
                    'start_values_passed': bool(start_values_passed), 'timer_cleanup_passed': timer_cleanup_passed,
                    'native_start_clock_phase_passed': phase_passed, 'source_frame_phase_checks': phase_checks,
                    'maximum_native_start_vs_creation_clock_difference_seconds': max(clock_deltas, default=None),
                    'phase_errors': phase_errors, 'native_start_values': starts, 'native_stop_values': stops,
                    'clock_limit': 'Native start_time is exact to its six-decimal log precision. A compatible update time is inferred within 0.05 seconds plus one game-frame delay; actual timer-fire and solver timestamps are not read back.'}
                configuration_logged &= flutter_validation['passed']
        passed = code == 0 and report.get('passed', False) and traces_passed and not shader_errors and configuration_logged
        launch = {'passed': passed, 'mode': mode, 'variant': variant, 'return_code': code,
            'new_variant_cvar_overrides': cvar_overrides, 'applied_cvar_overrides': applied_overrides,
            'report': str(report_path), 'report_passed': report.get('passed', False),
            'case_count': len(report.get('cases', [])), 'full_trace_hashes_passed': traces_passed,
            'shader_compile_errors': shader_errors, 'runtime_configuration_logged': configuration_logged,
            'runtime_configuration_lines': mode_lines, 'point_wind_query_lines': point_lines,
            'point_wind_query_values': point_rows, 'point_wind_queries_passed': point_queries_passed,
            'flutter_start_log_lines': flutter_start_lines, 'flutter_stop_log_lines': flutter_stop_lines,
            'flutter_timer_validation': flutter_validation,
            'wind_query_limit': 'Native logs use component GetWindParameters. QA never calls GetWindForCloth or alters its RNG order.',
            'error': report.get('error')}
        (child / 'launch-result.json').write_text(json.dumps(launch, indent=2), encoding='utf-8')
        launches.append(launch)
        print(json.dumps({'mode': mode, 'passed': passed, 'report': str(report_path), 'error': report.get('error')}), flush=True)
        if not passed:
            (out / 'launch-result.json').write_text(json.dumps({'passed': False, 'serial_launches': launches,
                'new_variant_cvar_overrides': cvar_overrides,
                'comparison': None if args.new_only else str(out / f'sparrow-cape-comparison-{args.fps}.json'),
                'reused_old': reused_old,
                'scope': ('new30stabilityonly' if args.fps == 30 else 'new_variant_stability_only') if args.new_only else 'same_fps_old_new_comparison'}, indent=2), encoding='utf-8')
            return 1
    command = [sys.executable, str(TOOLS / 'sparrow_cape_compare.py'), '--review', str(out), '--fps', str(args.fps)]
    if args.new_only:
        command.append('--new-only')
    if args.reuse_old:
        command.extend(['--old-run', str(args.reuse_old.resolve())])
    code = subprocess.call(command)
    result = {'passed': code == 0, 'serial_launches': launches, 'comparison_return_code': code,
              'new_variant_cvar_overrides': cvar_overrides,
              'comparison': None if args.new_only else str(out / f'sparrow-cape-comparison-{args.fps}.json'),
              'stability_summary': str(out / f'sparrow-cape-stability-{args.fps}.json') if args.new_only else None,
              'reused_old': reused_old,
              'scope': ('new30stabilityonly' if args.fps == 30 else 'new_variant_stability_only') if args.new_only else 'same_fps_old_new_comparison'}
    (out / 'launch-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
