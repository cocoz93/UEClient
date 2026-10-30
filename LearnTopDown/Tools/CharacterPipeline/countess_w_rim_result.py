"""Seal the W outer-front variant against the immediately preceding dense W."""
import difflib, json
from pathlib import Path
from baseline import PROJECT, digest
from countess_q_result import e_blocks
from countess_w_result import function

BASE=PROJECT/'Saved/QA/CharacterPipeline/countess-w-rim-20261016'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def main():
    visual=read(BASE/'visual-review.json')
    assert visual['render_review_passed'] and not visual['user_style_approval']
    assets=read(BASE/'assets-02/assets.json')
    assert assets['passed'] and assets['outer_smoke']['adapted_emitters']==2
    assert assets['interior_sparks_droplets_and_hit_effect_untouched']
    reports=[];images=[];hit_times={}
    for fps,folder in ((60,'compare-60-02'),(30,'compare-30-01')):
        directory=BASE/folder
        path=directory/f'countess-w-comparison-{fps}.json'
        report=read(path);launch=read(directory/'launch-result.json');process=read(directory/'process-result.json')
        assert report['passed'] and launch['passed'] and not launch['shader_compile_errors']
        assert process['return_code']==0 and not process['timed_out']
        assert len(report['cases'])==10 and len(report['screenshots'])==48
        assert report['protected_files_match'] and report['capture_integrity']['passed']
        assert 'UnrealEditor-LearnTopDown-6158.dll' in (directory/'editor.log').read_text(errors='replace')
        cases={c['name']:c['data'] for c in report['cases']}
        a,b=cases['W_original'],cases['W_dense']
        assert a['target_healths']==b['target_healths']==[60,60,60]
        assert a['outside_health']==b['outside_health']==100
        assert abs(a['first_damage_seconds']-b['first_damage_seconds'])<=1/fps
        for left,right in zip(a['frames'],b['frames']):
            assert abs(left['elapsed']-right['elapsed'])<=1/fps
            for field in ('camera','pawn'):
                assert max(abs(x-y) for x,y in zip(left[field],right[field]))<.05
        hit_times[fps]=[a['first_damage_seconds'],b['first_damage_seconds']]
        reports.append({'path':str(path),'sha256':digest(path),'fps':fps,'cases':10,'captures':48})
        images+=report['screenshots']
    assert {i['image'] for i in images}=={i['path'] for i in visual['images']}
    assert all(digest(Path(i['path']))==i['sha256'] for i in visual['images'])
    before=read(BASE/'before-source-hashes.json')
    changed=sorted(p for p,h in before.items() if digest(PROJECT/p)!=h)
    assert changed==['Source/LearnTopDown/CountessSkillComponent.cpp','Source/LearnTopDown/CountessSkillComponent.h']
    all_source={p.relative_to(PROJECT).as_posix() for p in (PROJECT/'Source').rglob('*') if p.is_file()}
    assert all_source-set(before)=={'Source/LearnTopDown/Tests/CountessWAutomation.cpp'}
    diff=[]
    for name in ('CountessSkillComponent.cpp','CountessSkillComponent.h'):
        old=(BASE/'before-Source/LearnTopDown'/name).read_bytes()
        new=(PROJECT/'Source/LearnTopDown'/name).read_bytes()
        assert not new.startswith(b'\xef\xbb\xbf') and b'\n' not in new.replace(b'\r\n',b'')
        assert '\ufffd' not in new.decode('utf-8')
        if name.endswith('.cpp'):
            assert e_blocks(old)==e_blocks(new) and e_blocks(old)
            first,last=b'const TCHAR* Animations[]',b'ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
            assert old[old.index(first):old.index(last)]==new[new.index(first):new.index(last)]
            for method in ('BeginSkill','ExecuteAction','StartSkillVisuals','FinishSkill','CancelSkill',
                           'SpawnBlinkImpactAccent','SpawnBlinkDualSweep','TryReturn','ApproachFeast',
                           'FindFeastLanding','TickComponent','EndPlay','DamageTarget','SpawnOwnedEffect','StopCastVisuals'):
                assert function(old.decode('utf-8'),method)==function(new.decode('utf-8'),method),method
        diff+=difflib.unified_diff(old.decode('utf-8').replace('\r\n','\n').splitlines(True),new.decode('utf-8').replace('\r\n','\n').splitlines(True),fromfile='before/'+name,tofile='after/'+name)
    (BASE/'native-change.diff').write_text(''.join(diff),encoding='utf-8')
    for file in ('build-editor-02.log','build-game-02.log'):
        assert 'Result: Succeeded' in (BASE/file).read_text(errors='replace')
    next_baseline=PROJECT/'Saved/QA/CharacterPipeline/baseline-countess-w-rim-20261016/baseline.json'
    after=read(next_baseline)['protected_hashes'];prior=read(BASE/'baseline-before.json')['protected_hashes']
    assert all(after[p]==h for p,h in prior.items())
    added=sorted(set(after)-set(prior))
    assert added==['Content/TopDown/Characters/Countess/FX/P_CountessW_RimRing.uasset']
    assert digest(PROJECT/added[0])==after[added[0]]
    module='Binaries/Win64/UnrealEditor-LearnTopDown-6158.dll'
    assert read(PROJECT/'Binaries/Win64/UnrealEditor.modules')['Modules']['LearnTopDown']==Path(module).name
    result={'passed':True,'status':'textured_W_outer_front_play_view_verified','scope':'Countess W outer-front visuals only',
            'user_style_approval':False,'original_material_mesh_texture_dependencies_preserved':assets['dependencies_preserved'],
            'q_e_r_gameplay_and_assets_preserved':True,'prior_dense_W_assets_preserved':True,
            'skill_default_definitions_byte_identical':True,'E_logic_byte_identical':True,
            'core_gameplay_Q_R_and_damage_functions_byte_identical':True,'q_appearance_approval_still_pending':True,
            'damage_per_enemy':40,'damage_range_cm':240,'cooldown_seconds':6,'hit_seconds':hit_times,
            'outer_smoke_emitters':2,'outer_smoke_radius_cm':[385,415],
            'cases':20,'native_captures':96,'verification':reports,
            'changed_source_files':changed,'new_editor_only_source':'Source/LearnTopDown/Tests/CountessWAutomation.cpp',
            'other_native_source_files_unchanged':len(before)-len(changed),
            'unchanged_prior_content_config_project_files':len(prior),'new_content_files':added,
            'protected_baseline':str(next_baseline),'visual_review':str(BASE/'visual-review.json'),
            'comparison':str(BASE/'compare-60-02/review/pair-09.png'),
            'sampled_gameplay_comparison':str(BASE/'compare-60-02/review/W-before-after-sampled.gif'),
            'rejected_initial_linear_placement':'compare-60-01','editor_module':module,'editor_module_sha256':digest(PROJECT/module),
            'camera_zoom_changed':False,'continuous_video':False,'physical_OS_input_tested':False,'GPU_performance_benchmark':False,
            'source_hashes':{p:digest(PROJECT/p) for p in changed},'new_asset_hashes':{p:after[p] for p in added}}
    (BASE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'cases':20,'captures':96,'protected_files':len(after),'result':str(BASE/'result.json')}))


if __name__=='__main__':main()
