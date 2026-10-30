"""Seal observation evidence without treating reproduced defects as quality acceptance."""
import hashlib, json, math
from pathlib import Path
from baseline import PROJECT, digest, verify

BASE=PROJECT/'Saved/QA/CharacterPipeline/sparrow-motion-diagnostic-20261016'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    reports=[];steps={};images=[];heading={}
    for fps in (60,30):
        directory=BASE/f'verify-{fps}-01'
        report=read(directory/f'sparrow-stop-diagnostic-{fps}.json')
        analysis=read(directory/'review/motion-analysis.json')
        launch=read(directory/'launch-result.json')
        assert report['passed'] and launch['passed'] and len(report['cases'])==13
        assert report['protected_files_match'] and report['capture_integrity']['passed']
        assert not analysis['style_acceptance_decided']
        assert 'UnrealEditor-LearnTopDown-6159.dll' in (directory/'editor.log').read_text(errors='replace')
        fps_steps=[]
        for case in report['cases']:
            row=case['data']['full_simulation_trace'];path=Path(row['path'])
            assert digest(path)==row['sha256']
            samples=read(path)['samples']
            if case['name'].startswith('direction_'):
                edges=[(a,b) for a,b in zip(samples,samples[1:]) if a.get('run_weight',0)>.95 and b.get('run_weight',1)<.05]
                assert len(edges)==1
                a,b=edges[0]
                ma,mb=a['motion'],b['motion']
                bones={bone:math.dist(ma['bones_component_space'][bone]['translation'],mb['bones_component_space'][bone]['translation']) for bone in ('root','pelvis','head','foot_l','foot_r')}
                fps_steps.append({'case':case['name'],'time_before':a['time'],'time_after':b['time'],
                    'time_step_seconds':b['time']-a['time'],'actor_yaw_before':ma['actor_yaw'],'actor_yaw_after':mb['actor_yaw'],
                    'actor_position_step_cm':math.dist(a['position'],b['position']),
                    'bone_component_space_step_cm':bones,'run_weights':[a['run_weight'],b['run_weight']]})
            if case['name']=='short_reverse_110':
                leg=case['data']['legs'][-1]
                heading[fps]={k:leg[k] for k in ('stopped','last_moving_velocity_yaw','stopped_actor_yaw','post_settling_actor_yaw','final_actor_vs_last_velocity_error_degrees')}
        steps[fps]=fps_steps
        images+=report['screenshots']
        reports.append({'fps':fps,'path':str(directory/f'sparrow-stop-diagnostic-{fps}.json'),
                        'report_sha256':digest(directory/f'sparrow-stop-diagnostic-{fps}.json'),
                        'analysis_sha256':digest(directory/'review/motion-analysis.json'),
                        'cases':len(report['cases']),'captures':len(report['screenshots'])})
    assert heading[30]['final_actor_vs_last_velocity_error_degrees']>11
    assert heading[60]['final_actor_vs_last_velocity_error_degrees']<.01
    prior=read(BASE/'before-source-hashes.json')
    assert all(digest(PROJECT/p)==h for p,h in prior.items())
    baseline=PROJECT/'Saved/QA/CharacterPipeline/baseline-countess-w-rim-20261016/baseline.json'
    protection=verify(baseline)
    assert protection['passed']
    assert 'Result: Succeeded' in (BASE/'build-editor.log').read_text(errors='replace')
    result={'diagnostic_complete':True,'product_fix_applied':False,'product_style_acceptance':False,
            'scope':'Archer motion/heading/cloth diagnosis; assassin W next-step proposal only',
            'cases':26,'native_captures':len(images),'verification':reports,
            'original_gameplay_source_files_unchanged':len(prior),
            'protected_content_config_project_files_unchanged':protection['protected_files'],
            'new_editor_only_observer':'Source/LearnTopDown/Tests/SparrowMotionAutomation.cpp',
            'editor_module':'UnrealEditor-LearnTopDown-6159.dll',
            'run_to_idle_discontinuity_observations':steps,'short_reverse_heading':heading,
            'findings':[
                'Both frame rates reproduce abrupt RunWeight 1 to 0 and large component-space pose changes at natural stops.',
                'The root bone remains at the same origin; pelvis/head/feet switch between mismatched authored poses without crossfade.',
                'Sampled cloth particles also change abruptly at the same stop transition, then their remaining motion decays.',
                'The 30 FPS 110 cm reversal leaves about 11.69 degrees of heading error after rest; the matching 60 FPS case completes its turn.',
                'Pending teleport mode snapshots cannot establish whether a solver reset was consumed earlier.',
                'The reviewed 60 FPS captures do not reproduce persistent upward cloth runaway.'],
            'next_change_plan':[
                'Compare archer-only Run to Idle 0.16 to 0.20 second and Idle to Run about 0.08 second crossfades.',
                'Review authored idle/move pelvis alignment if smooth blending still leaves visible body retreat.',
                'Finish small remaining noncombat stop rotations using the last valid movement heading, without altering combat aiming.',
                'Repeat identical motion paths before adjusting any remaining archer-only cloth response.',
                'For assassin W, connect center and outer edge with several textured spiral flows and aligned fade timing.'],
            'continuous_video':False,'physical_OS_input_tested':False,'GPU_performance_benchmark':False}
    (BASE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'diagnostic_complete':True,'product_fix_applied':False,'cases':26,'captures':len(images),'protected_files':protection['protected_files']}))


if __name__=='__main__':main()
