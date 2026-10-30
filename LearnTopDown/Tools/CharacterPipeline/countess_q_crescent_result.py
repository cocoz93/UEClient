"""Seal the large Q experiment, preserved gameplay and actual gameplay-view evidence."""
import json
from pathlib import Path
from baseline import PROJECT, capture, digest
from countess_q_result import e_blocks

BASE = PROJECT/'Saved/QA/CharacterPipeline/countess-q-crescent-20261015'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    visual = read(BASE/'visual-review.json')
    assert visual['render_review_passed'] and visual['large_change_visible_at_gameplay_camera']
    assert visual['user_style_approval'] is False
    reports = []
    images = []
    hit_times = {}
    for fps, folder, count in ((60, 'compare-60-02', 6), (30, 'compare-30-01', 6), (60, 'motion-60-01', 7)):
        directory = BASE/folder
        report_path = directory/f'countess-q-comparison-{fps}.json'
        report = read(report_path)
        assert report['passed'] and read(directory/'launch-result.json')['passed']
        assert read(directory/'launch-result.json')['q_shader_compile_verified']
        process = read(directory/'process-result.json')
        assert process['return_code'] == 0 and not process['timed_out']
        assert len(report['cases']) == count and report['protected_files_match']
        assert report['capture_integrity']['passed']
        assert 'UnrealEditor-LearnTopDown-6154.dll' in (directory/'editor.log').read_text(errors='replace')
        if folder.startswith('compare'):
            cases = {c['name']: c['data'] for c in report['cases']}
            a, b = cases['Q_original'], cases['Q_enhanced']
            assert abs(a['first_damage_seconds']-b['first_damage_seconds']) <= 1/fps
            for x, y in zip(a['phases'], b['phases']):
                assert x['phase'] == y['phase'] and abs(x['elapsed']-y['elapsed']) <= 1/fps
                for key in ('camera', 'pawn'):
                    assert max(abs(v-w) for v, w in zip(x[key], y[key])) < .05
            hit_times[fps] = [a['first_damage_seconds'], b['first_damage_seconds']]
        reports.append({'path': str(report_path), 'sha256': digest(report_path), 'fps': fps,
                        'cases': count, 'native_captures': len(report['screenshots'])})
        images += report['screenshots']
    assert {i['image'] for i in images} == {i['path'] for i in visual['images']}
    for image in visual['images']:
        assert digest(Path(image['path'])) == image['sha256']
    before = read(BASE/'before-source-hashes.json')
    changed = [p for p, h in before.items() if digest(PROJECT/p) != h]
    assert changed == ['Source/LearnTopDown/CountessSkillComponent.cpp']
    old = (BASE/'before-CountessSkillComponent.cpp').read_bytes()
    source = PROJECT/changed[0]
    current = source.read_bytes()
    assert e_blocks(old) and e_blocks(old) == e_blocks(current)
    a, b = b'const TCHAR* Animations[]', b'ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
    assert old[old.index(a):old.index(b)] == current[current.index(a):current.index(b)]
    assert old.startswith(b'\xef\xbb\xbf') == current.startswith(b'\xef\xbb\xbf')
    assert b'\n' not in current.replace(b'\r\n', b'')
    for filename in ('build-editor-v2.log', 'build-game-v2.log'):
        assert 'Result: Succeeded' in (BASE/filename).read_text(errors='replace')
    assert read(BASE/'material-02/material.json')['graph_connections_verified']
    baseline_directory = PROJECT/'Saved/QA/CharacterPipeline/baseline-countess-q-crescent-20261015'
    if not baseline_directory.exists():
        capture(baseline_directory)
    after = read(baseline_directory/'baseline.json')['protected_hashes']
    prior = read(BASE/'baseline-before.json')['protected_hashes']
    assert all(after[p] == h and digest(PROJECT/p) == h for p, h in prior.items())
    additions = sorted(set(after)-set(prior))
    assert additions == ['Content/TopDown/Characters/Countess/Materials/M_CountessQCrescent.uasset']
    assert digest(PROJECT/additions[0]) == after[additions[0]]
    module = 'Binaries/Win64/UnrealEditor-LearnTopDown-6154.dll'
    assert read(PROJECT/'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown'] == Path(module).name
    result = {'passed': True, 'status': 'large_Q_preview_verified', 'scope': 'Countess Q visuals only',
        'map': '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom',
        'large_change_visible_at_gameplay_camera': True, 'user_style_approval': False,
        'camera_zoom_changed': False, 'q_damage': 35, 'q_hit_seconds': hit_times,
        'skill_default_definitions_byte_identical': True, 'E_logic_byte_identical': True,
        'other_40_native_source_files_unchanged': True, 'changed_source_files': changed,
        'source_sha256': digest(source), 'unchanged_prior_content_config_project_files': len(prior),
        'new_content_files': additions, 'new_material_sha256': after[additions[0]],
        'visual_layers': {'crescent_canvas_cm': 680, 'crescent_lifetime_seconds': .44,
                          'sweep_degrees': 100, 'sweep_seconds': .12,
                          'rush_lifetime_seconds': .28, 'impact_lifetime_seconds': .16,
                          'actor_lifetime_seconds': .48},
        'verification': reports, 'cases': sum(r['cases'] for r in reports),
        'native_captures': len(images), 'visual_review': str(BASE/'visual-review.json'),
        'visual_review_sha256': digest(BASE/'visual-review.json'),
        'editor_module': module, 'editor_module_sha256': digest(PROJECT/module),
        'next_pipeline_baseline': str(baseline_directory/'baseline.json'),
        'previous_small_preview_comparison': str(BASE/'review/previous-vs-crescent-slash.png'),
        'sampled_gameplay_comparison': str(BASE/'review/Q-gameplay-sampled-timing.gif'),
        'sampled_PIE_frames_not_continuous_video': True,
        'physical_OS_input_tested': False, 'GPU_performance_benchmark': False,
        'full_other_skills_regression': False, 'existing_user_editor_requires_restart': True,
        'tool_hashes': {p.name: digest(p) for p in (PROJECT/'Tools/CharacterPipeline').glob('countess_q*.py')}}
    (BASE/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'cases': result['cases'], 'native_captures': len(images),
                      'protected_files': len(prior), 'result': str(BASE/'result.json')}), flush=True)


if __name__ == '__main__':
    main()
