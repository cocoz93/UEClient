"""Seal successful room evidence and activate its default map only after visual review."""
import hashlib
import json
from pathlib import Path
import sys

from baseline import PROJECT, capture, verify, digest

BASE = PROJECT / 'Saved/QA/CharacterPipeline/training-room-20261015'
BASELINE = PROJECT / 'Saved/QA/CharacterPipeline/baseline-training-room-20261015/baseline.json'
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    inventory = read(BASE / 'inspect/inventory.json')
    final_lighting = read(BASE / 'final-lighting/finalize.json')
    texture_budget = read(BASE / 'budget-04/budget.json')
    review = read(BASE / 'visual-review.json')
    if not inventory['passed'] or not final_lighting['passed'] or not texture_budget['passed'] or not review.get('approved'):
        raise RuntimeError('Missing successful asset load, lighting installation, or visual review')
    before = verify(BASELINE)
    if not before['passed']:
        raise RuntimeError('Protected files changed before activation: ' + str(before['mismatches']))
    reports, captures = [], []
    for fps in (30, 60):
        directory = BASE / f'verify-release-{fps}'
        path = directory / f'training-room-{fps}.json'
        report = read(path)
        process = read(directory / 'process-result.json')
        if not report['passed'] or process['return_code'] != 0 or process['timed_out']:
            raise RuntimeError('Room verification failed at ' + str(fps))
        if len(report['cases']) != 15 or not report['capture_integrity']['passed'] or not report['protected_files_match']:
            raise RuntimeError('Incomplete final verification evidence')
        if report.get('offscreen_texture_pool_mb') != 512 or report.get('offscreen_virtual_shadow_cache_pages') != 1024:
            raise RuntimeError('Final verification did not use the documented offscreen resource limits')
        reports.append({'fps': fps, 'report': str(path), 'sha256': digest(path),
                        'cases': len(report['cases']), 'checks': len(report['checks']),
                        'captures': len(report['screenshots'])})
        for row in report['screenshots']:
            image = Path(row['image'])
            if digest(image) != row['sha256']:
                raise RuntimeError('Captured image changed: ' + str(image))
            captures.append({'path': str(image), 'sha256': row['sha256']})
    if {c['path'] for c in captures} != {c['path'] for c in review['images']}:
        raise RuntimeError('Visual review does not cover every final screenshot')
    for row in review['images']:
        if digest(Path(row['path'])) != row['sha256']:
            raise RuntimeError('Reviewed image changed')
    old_source = BASELINE.parent / 'before/Source'
    native_changes = [p.relative_to(old_source).as_posix() for p in old_source.rglob('*')
                      if p.is_file() and digest(p) != digest(PROJECT / 'Source' / p.relative_to(old_source))]
    if native_changes:
        raise RuntimeError('Native character code changed: ' + str(native_changes))
    roots = [PROJECT / 'Content/TopDown/TrainingRoom',
             PROJECT / 'Content/__ExternalActors__/TopDown/TrainingRoom',
             PROJECT / 'Content/__ExternalObjects__/TopDown/TrainingRoom']
    assets = {p.relative_to(PROJECT).as_posix(): digest(p) for folder in roots for p in folder.rglob('*') if p.is_file()}
    if not assets:
        raise RuntimeError('Missing saved training room content')
    # Preserve bytes/BOM/newlines and change only the two requested default-map entries.
    config = PROJECT / 'Config/DefaultEngine.ini'
    old_config = config.read_bytes()
    old_map = b'/Game/TopDown/Lvl_TopDown.Lvl_TopDown'
    new_map = (MAP + '.Lvl_DarkTrainingRoom').encode('ascii')
    new_config = old_config
    for key in (b'EditorStartupMap=', b'GameDefaultMap='):
        anchor = key + old_map
        if new_config.count(anchor) != 1:
            raise RuntimeError('Default map entry is not the expected preserved value: ' + key.decode())
        new_config = new_config.replace(anchor, key + new_map)
    (BASE / 'DefaultEngine.before.ini').write_bytes(old_config)
    config.write_bytes(new_config)
    after = verify(BASELINE)
    if after['mismatches'] != ['Config/DefaultEngine.ini']:
        raise RuntimeError('Unexpected protected change during activation: ' + str(after))
    next_baseline = BASELINE.parent.parent / 'baseline-training-room-complete-20261015'
    capture(next_baseline)
    result = {'passed': True, 'status': 'complete', 'scope': 'dark_training_room_both_heroes',
        'map': MAP, 'engine': inventory['engine'], 'imported_packages_loaded': len(inventory['assets']),
        'original_demo_map_loaded': inventory['demo_actor_count'] > 0,
        'original_demo_full_playthrough_tested': False,
        'cases': sum(r['cases'] for r in reports), 'checks': sum(r['checks'] for r in reports),
        'screenshots': len(captures), 'verification': reports,
        'visual_review': str(BASE / 'visual-review.json'), 'visual_review_sha256': digest(BASE / 'visual-review.json'),
        'protected_before_activation': before, 'protected_after_activation': after,
        'authorized_config_change': {'path': str(config), 'before_sha256': hashlib.sha256(old_config).hexdigest(),
            'after_sha256': digest(config), 'fields': ['EditorStartupMap', 'GameDefaultMap']},
        'protected_content_and_original_pack_unchanged': True, 'native_source_files_changed': native_changes,
        'next_pipeline_baseline': str(next_baseline / 'baseline.json'),
        'new_asset_hashes': assets,
        'tool_hashes': {p.name: digest(p) for p in (PROJECT / 'Tools/CharacterPipeline').glob('training_room_*.py')},
        'physical_OS_input_tested': False, 'full_original_character_profiles_reverified': False,
        'fixed_simulation_fps': [30, 60], 'GPU_performance_benchmark': False,
        'offscreen_texture_pool_mb': 512, 'texture_pool_override_saved_to_project': False,
        'offscreen_virtual_shadow_cache_pages': 1024, 'shadow_cache_override_saved_to_project': False,
        'controls': {'One': 'Countess', 'Two': 'Sparrow', 'RightMouse': 'Move', 'LeftMouse': 'Basic attack',
                     'skills': 'QWER (Sparrow E remains passive)'},
        'skill_effects_or_audio_changed': False,
        'environment_texture_limit': 2048, 'environment_budget_report': str(BASE / 'budget-04/budget.json'),
        'known_preexisting_log_items': ['Countess LevelStart_Montage references absent Shinbi intro packages',
                                      'NavigationSystem CDO ensure also occurs in prior original-field QA'],
        'network_services_required_for_local_play': False}
    (BASE / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'cases': result['cases'], 'screenshots': len(captures),
                       'result': str(BASE / 'result.json')}), flush=True)


if __name__ == '__main__':
    main()
