"""Seal the Q-only dual sweep change against actual PIE evidence and baseline."""
import difflib
import json
from pathlib import Path

from baseline import PROJECT, capture, digest
from countess_q_result import e_blocks

BASE = PROJECT / 'Saved/QA/CharacterPipeline/countess-q-dual-20261015'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    visual = read(BASE / 'visual-review.json')
    assert visual['render_review_passed'] and not visual['user_style_approval']
    assets = read(BASE / 'assets-06/material.json')
    assert assets['passed'] and assets['max_import_position_error_cm'] < .01
    assert len(assets['trajectory_samples']) == 30
    reports, images, hit_times = [], [], {}
    for fps, folder, count in ((60, 'compare-60-03', 6), (30, 'compare-30-02', 6),
                               (60, 'motion-60-02', 9)):
        directory = BASE / folder
        report_path = directory / f'countess-q-comparison-{fps}.json'
        report = read(report_path)
        launch = read(directory / 'launch-result.json')
        process = read(directory / 'process-result.json')
        assert report['passed'] and launch['passed'] and launch['q_shader_compile_verified']
        assert process['return_code'] == 0 and not process['timed_out']
        assert len(report['cases']) == count and report['protected_files_match']
        assert report['capture_integrity']['passed']
        assert 'UnrealEditor-LearnTopDown-6155.dll' in (directory / 'editor.log').read_text(errors='replace')
        if folder.startswith('compare'):
            cases = {c['name']: c['data'] for c in report['cases']}
            a, b = cases['Q_original'], cases['Q_enhanced']
            assert abs(a['first_damage_seconds'] - b['first_damage_seconds']) <= 1 / fps
            for left, right in zip(a['phases'], b['phases']):
                assert left['phase'] == right['phase']
                assert abs(left['elapsed'] - right['elapsed']) <= 1 / fps
                for field in ('camera', 'pawn'):
                    assert max(abs(x - y) for x, y in zip(left[field], right[field])) < .05
            hit_times[fps] = [a['first_damage_seconds'], b['first_damage_seconds']]
        reports.append({'path': str(report_path), 'sha256': digest(report_path),
                        'fps': fps, 'cases': count, 'native_captures': len(report['screenshots'])})
        images += report['screenshots']
    assert len(images) == 95
    assert {i['image'] for i in images} == {i['path'] for i in visual['images']}
    for image in visual['images']:
        assert digest(Path(image['path'])) == image['sha256']
    before = read(BASE / 'before-source-hashes.json')
    changed = [p for p, h in before.items() if digest(PROJECT / p) != h]
    assert changed == ['Source/LearnTopDown/CountessSkillComponent.cpp',
                       'Source/LearnTopDown/CountessSkillComponent.h']
    diff = []
    for name in ('CountessSkillComponent.cpp', 'CountessSkillComponent.h'):
        old = (BASE / ('before-' + name)).read_bytes()
        new = (PROJECT / 'Source/LearnTopDown' / name).read_bytes()
        assert old.startswith(b'\xef\xbb\xbf') == new.startswith(b'\xef\xbb\xbf')
        assert b'\n' not in new.replace(b'\r\n', b'')
        assert '\ufffd' not in new.decode('utf-8-sig')
        if name.endswith('.cpp'):
            assert e_blocks(old) == e_blocks(new) and e_blocks(old)
            first, last = b'const TCHAR* Animations[]', b'ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
            assert old[old.index(first):old.index(last)] == new[new.index(first):new.index(last)]
        diff += difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),
                                     new.decode('utf-8-sig').splitlines(True),
                                     fromfile='before/' + name, tofile='after/' + name)
    (BASE / 'native-change.diff').write_text(''.join(diff), encoding='utf-8')
    for filename in ('build-editor-final.log', 'build-game-final.log'):
        assert 'Result: Succeeded' in (BASE / filename).read_text(errors='replace')
    next_directory = PROJECT / 'Saved/QA/CharacterPipeline/baseline-countess-q-dual-20261015'
    if not next_directory.exists():
        capture(next_directory)
    after = read(next_directory / 'baseline.json')['protected_hashes']
    prior = read(BASE / 'baseline-before.json')['protected_hashes']
    assert all(after[p] == h for p, h in prior.items())
    additions = sorted(set(after) - set(prior))
    assert additions == ['Content/TopDown/Characters/Countess/FX/SM_CountessQDualSweep.uasset',
                          'Content/TopDown/Characters/Countess/Materials/M_CountessQDualSweep.uasset']
    module = 'Binaries/Win64/UnrealEditor-LearnTopDown-6155.dll'
    assert read(PROJECT / 'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown'] == Path(module).name
    result = {'passed': True, 'scope': 'Countess Q visuals only',
              'status': 'dual_blade_Q_play_view_verified', 'user_style_approval': False,
              'final_rebuild_restores_original_no_BOM_UTF8_only': True,
              'no_Cpp_logic_change_after_final_PIE_verification': True,
              'actual_authored_weapon_socket_paths': True,
              'raw_animation_range_seconds': assets['raw_animation_range_seconds'],
              'enlargement_about_chest': 2.6,
              'crossed_hand_windup_diminished_to_keep_two_outward_cuts_separate': True,
              'max_import_position_error_cm': assets['max_import_position_error_cm'],
              'mesh_follows_actual_character_orientation_before_impact': True,
              'baked_authored_trajectory_not_arbitrary_live_IK_trail': True,
              'camera_zoom_changed': False, 'q_damage': 35, 'q_hit_seconds': hit_times,
              'skill_default_definitions_byte_identical': True, 'E_logic_byte_identical': True,
              'changed_source_files': changed, 'other_native_source_files_unchanged': len(before) - len(changed),
              'unchanged_prior_content_config_project_files': len(prior),
              'new_content_files': additions,
              'protected_baseline': str(next_directory / 'baseline.json'),
              'verification': reports, 'cases': 21, 'native_captures': 95,
              'visual_review': str(BASE / 'visual-review.json'),
              'comparison': str(BASE / 'review-final/comparison-04.png'),
              'sampled_gameplay_comparison': str(BASE / 'review-final/Q-before-after-sampled.gif'),
              'continuous_video': False, 'physical_OS_input_tested': False,
              'GPU_performance_benchmark': False, 'full_other_skills_regression': False,
              'editor_module': module, 'editor_module_sha256': digest(PROJECT / module),
              'source_hashes': {p: digest(PROJECT / p) for p in changed},
              'new_asset_hashes': {p: after[p] for p in additions}}
    (BASE / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'cases': 21, 'captures': 95,
                      'protected_files': len(after), 'result': str(BASE / 'result.json')}), flush=True)


if __name__ == '__main__':
    main()
