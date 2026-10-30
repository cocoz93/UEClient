"""Seal completed functional evidence; visual judgment remains a separate review."""
from __future__ import annotations

import difflib
import json
from pathlib import Path
import re
import struct
import traceback
import zlib

from baseline import PROJECT, digest, verify

BASE = PROJECT / 'Saved/QA/CharacterPipeline/dual-character-polish-20261016'
NEXT_BASELINE = PROJECT / 'Saved/QA/CharacterPipeline/baseline-dual-character-polish-20261016/baseline.json'
MODULE = 'Binaries/Win64/UnrealEditor-LearnTopDown-6163.dll'
AUTHORED_SOURCE = {
    'Source/LearnTopDown/CountessSkillComponent.cpp',
    'Source/LearnTopDown/CountessSkillComponent.h',
    'Source/LearnTopDown/SparrowCharacter.cpp',
    'Source/LearnTopDown/SparrowCharacter.h',
}
NEW_HELPERS = {
    'Source/LearnTopDown/Tests/CountessWSpiralAutomation.cpp',
    'Source/LearnTopDown/Tests/SparrowStopAutomation.cpp',
}
EXTERNAL_SOURCE = {'Source/LearnTopDown/CharacterSkillHUD.cpp'}
NEW_CONTENT = {
    'Content/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing.uasset',
    'Content/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_SmoothStop.uasset',
    'Content/TopDown/Characters/Sparrow/Animations/A_Sparrow_TravelIdle.uasset',
}
RUNS = (
    ('w-60-03', 'countess-w-spiral-comparison-60.json', 60, 10, 48, 'assassin_W'),
    ('w-30-03', 'countess-w-spiral-comparison-30.json', 30, 10, 48, 'assassin_W'),
    ('sparrow-30-02', 'sparrow-stop-diagnostic-30.json', 30, 13, 62, 'archer_observation'),
    ('sparrow-60-01', 'sparrow-stop-diagnostic-60.json', 60, 13, 62, 'archer_observation'),
    ('regression-30-02', 'dual-character-regression-30.json', 30, 11, None, 'combat_and_selection'),
    ('regression-60-01', 'dual-character-regression-60.json', 60, 11, None, 'combat_and_selection'),
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def fingerprint(path: Path) -> dict:
    require(path.is_file(), 'Missing evidence: ' + str(path))
    return {'path': str(path), 'sha256': digest(path), 'bytes': path.stat().st_size}


def png_integrity(shot: dict) -> dict:
    path = Path(shot['image']).resolve()
    require(path.is_relative_to(BASE.resolve()), 'Capture is outside this task: ' + str(path))
    evidence = fingerprint(path)
    require(evidence['sha256'] == shot['sha256'], 'Native capture hash changed: ' + str(path))
    data = path.read_bytes()
    require(data.startswith(b'\x89PNG\r\n\x1a\n'), 'Invalid PNG signature: ' + str(path))
    position, dimensions, ended = 8, None, False
    while position < len(data):
        require(position + 12 <= len(data), 'Truncated PNG chunk: ' + str(path))
        length = struct.unpack_from('>I', data, position)[0]
        kind = data[position + 4:position + 8]
        end = position + 12 + length
        require(end <= len(data), 'Truncated PNG payload: ' + str(path))
        payload = data[position + 8:position + 8 + length]
        checksum = struct.unpack_from('>I', data, position + 8 + length)[0]
        require(zlib.crc32(kind + payload) & 0xffffffff == checksum, 'PNG CRC mismatch: ' + str(path))
        if kind == b'IHDR':
            dimensions = list(struct.unpack_from('>II', payload))
        if kind == b'IEND':
            require(length == 0 and end == len(data), 'PNG has an invalid final chunk: ' + str(path))
            ended = True
            break
        position = end
    require(ended and dimensions == [shot['width'], shot['height']], 'PNG dimensions/end mismatch: ' + str(path))
    evidence.update(width=dimensions[0], height=dimensions[1], case=shot.get('case'),
                    native_capture_integrity_passed=True, visual_review_automatically_approved=False)
    return evidence


def method(source: str, name: str) -> str:
    start = source.index('UCountessSkillComponent::' + name + '(')
    first, depth = source.index('{', start), 0
    for index in range(first, len(source)):
        depth += (source[index] == '{') - (source[index] == '}')
        if depth == 0:
            return source[start:index + 1]
    raise ValueError('Unclosed Countess method: ' + name)


def protected_hashes() -> dict:
    files = [PROJECT / 'LearnTopDown.uproject']
    for folder in ('Content', 'Config'):
        files += [p for p in (PROJECT / folder).rglob('*') if p.is_file()]
    return {p.relative_to(PROJECT).as_posix(): digest(p) for p in sorted(files)}


def native_evidence() -> dict:
    before = read(BASE / 'before-source-hashes.json')
    require(len(before) == 43, 'Expected the preserved 43-file native baseline')
    for relative, expected in before.items():
        backup = BASE / 'before-Source' / Path(relative).relative_to('Source')
        require(backup.is_file() and digest(backup) == expected, 'Native backup mismatch: ' + relative)
        require((PROJECT / relative).is_file(), 'Preserved native file was removed: ' + relative)
    current = {p.relative_to(PROJECT).as_posix(): digest(p)
               for p in (PROJECT / 'Source').rglob('*') if p.is_file()}
    added = set(current) - set(before)
    require(added == NEW_HELPERS, 'Unexpected new native files: ' + repr(sorted(added)))
    changed = {p for p, h in before.items() if current[p] != h}
    require(changed - EXTERNAL_SOURCE == AUTHORED_SOURCE,
            'Unexpected authored native changes: ' + repr(sorted(changed)))
    for relative in AUTHORED_SOURCE | NEW_HELPERS:
        data = (PROJECT / relative).read_bytes()
        require(not data.startswith(b'\xef\xbb\xbf') and b'\n' not in data.replace(b'\r\n', b''),
                'Native UTF-8/no-BOM/CRLF contract failed: ' + relative)
        data.decode('utf-8')
    original = (BASE / 'before-Source/LearnTopDown/CountessSkillComponent.cpp').read_text(encoding='utf-8')
    final = (PROJECT / 'Source/LearnTopDown/CountessSkillComponent.cpp').read_text(encoding='utf-8')
    anchors = ('const TCHAR* Animations[]', 'ConstructorHelpers::FObjectFinder<UParticleSystem> Return(')
    require(original[original.index(anchors[0]):original.index(anchors[1])] ==
            final[final.index(anchors[0]):final.index(anchors[1])], 'Countess skill defaults changed')
    unchanged_methods = ('BeginSkill', 'ExecuteAction', 'StartSkillVisuals', 'FinishSkill', 'CancelSkill',
                         'SpawnBlinkImpactAccent', 'SpawnBlinkDualSweep', 'TryReturn', 'ApproachFeast',
                         'FindFeastLanding', 'TickComponent', 'EndPlay', 'DamageTarget',
                         'SpawnOwnedEffect', 'StopCastVisuals')
    for name in unchanged_methods:
        require(method(original, name) == method(final, name), 'Protected Countess method changed: ' + name)
    diff = []
    for relative in sorted(AUTHORED_SOURCE):
        old = (BASE / 'before-Source' / Path(relative).relative_to('Source')).read_text(encoding='utf-8')
        new = (PROJECT / relative).read_text(encoding='utf-8')
        diff += difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile='before/' + relative, tofile='after/' + relative)
    (BASE / 'native-change.diff').write_text(''.join(diff), encoding='utf-8')
    external = [{'path': p, 'before_sha256': before[p], 'current_sha256': current[p],
                 'attribution': 'observed concurrent external delta; not edited by this task',
                 'included_in_authored_changes': False} for p in sorted(changed & EXTERNAL_SOURCE)]
    return {'baseline_files': len(before), 'authored_changed_files': sorted(AUTHORED_SOURCE),
            'new_editor_only_helpers': sorted(NEW_HELPERS), 'external_deltas': external,
            'other_native_files_unchanged': len(before) - len(changed),
            'countess_skill_defaults_preserved': True, 'countess_protected_methods_preserved': list(unchanged_methods),
            'archer_skill_implementation_unchanged': all(p not in changed for p in before if '/SparrowSkillComponent.' in p),
            'current_source_hashes': dict(sorted(current.items())), 'before_source_hashes': before,
            'source_fingerprints_are_at_seal_time': True}


def run_evidence(folder, name, fps, case_count, capture_count, kind) -> tuple[dict, list]:
    directory = BASE / folder
    path = directory / name
    report, launch, process = read(path), read(directory / 'launch-result.json'), read(directory / 'process-result.json')
    require(report.get('passed') is True and launch.get('passed') is True, 'Failed QA report/launch: ' + folder)
    require(process.get('return_code') == 0 and process.get('timed_out') is False, 'Failed editor process: ' + folder)
    require(not launch.get('shader_compile_errors'), 'Shader fallback errors: ' + folder)
    require(report.get('fixed_simulation_fps') == fps, 'Unexpected simulation FPS: ' + folder)
    require(len(report['cases']) == case_count and all(c.get('passed') is True for c in report['cases']),
            'Unexpected case count or failure: ' + folder)
    require(report.get('protected_files_match') is True, 'Protected content mismatch: ' + folder)
    require(report.get('capture_integrity', {}).get('passed') is True, 'Capture integrity failure: ' + folder)
    baseline_after = report.get('baseline_after', {})
    require(baseline_after.get('passed') is True and baseline_after.get('protected_files') == 7014,
            'QA baseline did not verify all original 7014 files: ' + folder)
    log = (directory / 'editor.log').read_text(encoding='utf-8', errors='replace')
    loaded_modules = sorted(set(re.findall(r'UnrealEditor-LearnTopDown-(\d+)\.dll', log)))
    allowed_modules = {'6163'} if kind == 'assassin_W' else {'6162', '6163'}
    require(bool(set(loaded_modules) & allowed_modules), 'QA did not load the accepted native module: ' + folder)
    shots = report['screenshots']
    require(capture_count is None or len(shots) == capture_count, 'Unexpected native capture count: ' + folder)
    require(bool(shots), 'QA must contain actual native captures: ' + folder)
    images = [png_integrity(shot) for shot in shots]
    traces = []
    for case in report['cases']:
        full = case.get('data', {}).get('full_simulation_trace')
        if full:
            trace = fingerprint(Path(full['path']))
            require(trace['sha256'] == full['sha256'], 'Full motion trace changed: ' + case['name'])
            traces.append(trace | {'case': case['name'], 'reported_samples': full.get('samples')})
    cases = {c['name']: c.get('data', {}) for c in report['cases']}
    if kind == 'assassin_W':
        previous, spiral = cases['W_rim'], cases['W_spiral']
        require(previous['target_healths'] == spiral['target_healths'] == [60, 60, 60], 'W damage changed')
        require(previous['outside_health'] == spiral['outside_health'] == 100, 'W damage range changed')
        require(abs(previous['first_damage_seconds'] - spiral['first_damage_seconds']) <= 1 / fps, 'W hit timing changed')
        require(len(previous['frames']) == len(spiral['frames']) == 16, 'W comparison frame count changed')
        for a, b in zip(previous['frames'], spiral['frames']):
            require(abs(a['elapsed'] - b['elapsed']) <= 1 / fps, 'W simulation sample times differ')
            for field in ('camera', 'pawn'):
                require(max(abs(x - y) for x, y in zip(a[field], b[field])) < .05, 'W comparison ' + field + ' differs')
    if kind == 'archer_observation':
        require(len(traces) == 13 and report.get('diagnostic_only') is True,
                'Archer observation must preserve all 13 raw diagnostic traces')
    if kind == 'combat_and_selection':
        for case_name in ('stop_attack_interruption', 'stop_new_navigation', 'stop_Q_interruption', 'stop_owner_selection'):
            reservation = cases[case_name]['interruption_window']['reservation']
            require(reservation['pending'] and reservation['deadline'] > reservation['time'],
                    'Stop interruption did not exercise an actual pending reservation: ' + case_name)
        for case_name in ('stop_attack_interruption', 'stop_Q_interruption'):
            frames = cases[case_name]['combat_aim_frames']
            surface_bound = cases[case_name]['combat_aim_surface_bound_degrees']
            require(surface_bound > 0 and len(frames) >= (fps + 3) // 4 and
                    all(f['heading_drift_degrees'] < .1 and f['aim_error_degrees'] < surface_bound for f in frames),
                    'Combat aim is not verified throughout the stop window: ' + case_name)
        require(len(cases['stop_new_navigation']['new_navigation_heading_frames']) >= (fps + 3) // 4,
                'New navigation lacks frame-by-frame heading evidence')
    return ({'kind': kind, 'fps': fps, 'report': fingerprint(path),
             'launch': fingerprint(directory / 'launch-result.json'),
             'process': fingerprint(directory / 'process-result.json'),
             'editor_log': fingerprint(directory / 'editor.log'),
             'logged_native_module_suffixes': loaded_modules,
             'cases': len(report['cases']), 'captures': len(images), 'full_traces': traces,
             'case_data': cases, 'diagnostic_only': report.get('diagnostic_only', False),
             'diagnostic_pass_does_not_imply_visual_acceptance': kind == 'archer_observation'}, images)


def main():
    original = read(BASE / 'baseline-before.json')
    require(len(original['protected_hashes']) == 7014, 'Expected original 7014-file content baseline')
    baseline_verification = verify(BASE / 'baseline-before.json')
    require(baseline_verification['passed'], 'Original content/config/project files changed')
    countess_path, sparrow_path = BASE / 'countess-assets-04/assets.json', BASE / 'sparrow-assets-03/sparrow-stop-assets.json'
    countess, sparrow = read(countess_path), read(sparrow_path)
    require(countess.get('passed') is True and sparrow.get('passed') is True, 'Asset authoring failed')
    adaptation = countess['adaptation']
    require(adaptation['passed'] and len(adaptation['arms']) == 4, 'Expected four authored textured W arms')
    require(adaptation['module_outers_and_gpu_cached_references_valid'] and not adaptation['invalid_references'],
            'W private module/outer references failed validation')
    require(adaptation['gpu_emitter_info_rebuilt'] and adaptation['original_sampler_graph_and_emitter_subuv_state_preserved'],
            'W shader or GPU cache preservation failed')
    require(adaptation['spiral_expected_spawns'] <= adaptation['preserved_rim_smoke_expected_spawns'] + .001,
            'The four new W arms exceeded one preserved outer-smoke spawn budget')
    require(adaptation['exterior_smoke_preserved'] is True and adaptation['original_exterior_emitter_count'] == 2,
            'The two previous outer-smoke emitters must remain alongside the new arms')
    expected_total = adaptation['preserved_rim_smoke_expected_spawns'] + adaptation['spiral_expected_spawns']
    require(abs(adaptation['total_smoke_expected_spawns'] - expected_total) < .001 and
            adaptation['total_smoke_expected_spawns'] <= 2 * adaptation['preserved_rim_smoke_expected_spawns'] + .001,
            'Preserved outer smoke plus new spiral arms exceeded the explicit double-budget bound')
    for key in ('original_abp_unchanged', 'original_idle_unchanged'):
        require(sparrow[key] is True, 'Original archer asset changed: ' + key)
    require(sparrow['baseline_before']['passed'] and sparrow['baseline_after']['passed'], 'Archer asset baseline mismatch')
    builds = []
    for name in ('build-editor-04.log', 'build-editor-06.log', 'build-game-02.log'):
        path = BASE / name
        require('Result: Succeeded' in path.read_text(encoding='utf-8', errors='replace'), 'Native build failed: ' + name)
        builds.append(fingerprint(path))
    require(read(PROJECT / 'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown'] == Path(MODULE).name,
            'Current native module manifest no longer points to the final 6163 build')
    runs, images = [], []
    for spec in RUNS:
        run, captures = run_evidence(*spec)
        runs.append(run)
        images += captures
    require(len({image['path'] for image in images}) == len(images), 'Duplicate capture paths across accepted runs')
    native = native_evidence()
    current = protected_hashes()
    require(len(current) == 7017, 'Expected current 7017 protected content/config/project files')
    require(all(current.get(p) == h for p, h in original['protected_hashes'].items()), 'Original protected hashes differ')
    require(set(current) - set(original['protected_hashes']) == NEW_CONTENT, 'Unexpected new content/config/project files')
    next_baseline = {'schema_version': 1, 'project': str(PROJECT), 'protected_hashes': current,
                     'baseline_kind': 'hashes_only', 'content_backup_created_by_this_seal': False,
                     'parent_baseline': fingerprint(BASE / 'baseline-before.json'),
                     'source_hashes_at_seal': native['current_source_hashes']}
    if NEXT_BASELINE.exists():
        require(read(NEXT_BASELINE)['protected_hashes'] == current, 'Existing final baseline differs; refusing to replace it')
    else:
        NEXT_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        NEXT_BASELINE.write_text(json.dumps(next_baseline, indent=2), encoding='utf-8')
    review_path = BASE / 'visual-review.json'
    result = {
        'passed': True, 'status': 'functional_evidence_sealed_visual_judgment_separate',
        'scope': 'assassin W textured spiral; archer travel idle and arrival heading',
        'user_style_approval': False, 'visual_review_automatically_approved': False,
        'visual_review_evidence': fingerprint(review_path) if review_path.is_file() else None,
        'visual_review_status': 'separate explicit image review and user style judgment required',
        'cases': sum(run['cases'] for run in runs), 'native_captures': len(images),
        'functional_regression_cases_passed': sum(run['cases'] for run in runs if run['kind'] != 'archer_observation'),
        'motion_diagnostic_cases_completed': sum(run['cases'] for run in runs if run['kind'] == 'archer_observation'),
        'motion_diagnostic_pass_is_not_a_cloth_style_acceptance': True,
        'verification': runs, 'native_images': images, 'native_source': native,
        'builds': builds, 'editor_module': fingerprint(PROJECT / MODULE),
        'editor_module_manifest': fingerprint(PROJECT / 'Binaries/Win64/UnrealEditor.modules'),
        'original_7014_baseline_verification': baseline_verification,
        'current_baseline': fingerprint(NEXT_BASELINE), 'current_protected_files': len(current),
        'new_content_files': sorted(NEW_CONTENT),
        'new_content_hashes': {p: current[p] for p in sorted(NEW_CONTENT)},
        'authoring': {'countess': fingerprint(countess_path), 'sparrow': fingerprint(sparrow_path)},
        'original_W_material_mesh_texture_dependencies': countess['dependencies_preserved'],
        'countess_authoring_contract': {k: adaptation[k] for k in (
            'uses_particle_color', 'uses_subuv_expression', 'uses_texture_sample', 'uses_texture_coordinate',
            'original_emitter_8x8_subuv_state_confirmed', 'spiral_expected_spawns', 'preserved_rim_smoke_expected_spawns',
            'exterior_smoke_preserved', 'original_exterior_emitter_count', 'total_smoke_expected_spawns')},
        'W_smoke_budget_scope': 'new spiral-arm expected spawns versus one preserved rim-smoke budget; retained outer smoke is additional',
        'W_whole_effect_budget_is_unchanged': False,
        'game_build_precedes_final_editor_only_W_authoring_helper_change': True,
        'sparrow_authoring_evidence': {k: sparrow[k] for k in (
            'changes', 'idle_copy', 'idle_configuration', 'original_abp_unchanged', 'original_idle_unchanged')},
        'physical_OS_input_tested': False, 'continuous_video': False, 'GPU_performance_benchmark': False,
    }
    (BASE / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'cases': result['cases'], 'captures': len(images),
                      'protected_files': len(current), 'result': str(BASE / 'result.json')}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        failure = {'passed': False, 'status': 'seal_failed', 'error': traceback.format_exc(),
                   'user_style_approval': False, 'visual_review_automatically_approved': False}
        (BASE / 'result.json').write_text(json.dumps(failure, indent=2), encoding='utf-8')
        raise
