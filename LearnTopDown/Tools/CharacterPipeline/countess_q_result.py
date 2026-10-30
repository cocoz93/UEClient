"""Seal the Q-only preview and its controlled comparison, without approving user taste."""
import json
from pathlib import Path
from baseline import PROJECT, capture, digest

BASE = PROJECT/'Saved/QA/CharacterPipeline/countess-q-presentation-20261015'
SOURCE = PROJECT/'Source/LearnTopDown/CountessSkillComponent.cpp'
HEADER = PROJECT/'Source/LearnTopDown/CountessSkillComponent.h'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def e_blocks(data):
    anchor=b'else if (ActiveSkillIndex == 2)'
    offset=0
    blocks=[]
    while (offset:=data.find(anchor,offset))>=0:
        start=data.index(b'{',offset)
        depth=1
        end=start+1
        while depth:
            depth+=(data[end:end+1]==b'{')-(data[end:end+1]==b'}')
            end+=1
        blocks.append(data[offset:end])
        offset=end
    return blocks


def main():
    review=read(BASE/'visual-review.json')
    assert review['render_review_passed'] and not review['user_style_approval']
    reports=[]
    images=[]
    timings={}
    for fps,folder in ((60,'compare-60-04'),(30,'compare-30-03')):
        directory=BASE/folder
        report=read(directory/f'countess-q-comparison-{fps}.json')
        launch=read(directory/'launch-result.json')
        process=read(directory/'process-result.json')
        assert report['passed'] and launch['passed'] and launch['q_shader_compile_verified']
        assert process['return_code']==0 and not process['timed_out']
        assert len(report['cases'])==6 and report['protected_files_match'] and report['capture_integrity']['passed']
        assert 'UnrealEditor-LearnTopDown-6152.dll' in (directory/'editor.log').read_text(errors='replace')
        cases={c['name']:c for c in report['cases']}
        original=cases['Q_original']['data']
        enhanced=cases['Q_enhanced']['data']
        assert abs(original['first_damage_seconds']-enhanced['first_damage_seconds'])<=1/fps
        for a,b in zip(original['phases'],enhanced['phases']):
            assert a['phase']==b['phase'] and abs(a['elapsed']-b['elapsed'])<=1/fps
            assert max(abs(x-y) for x,y in zip(a['pawn'],b['pawn']))<.05
            assert max(abs(x-y) for x,y in zip(a['camera'],b['camera']))<.05
        timings[fps]={'original':original['first_damage_seconds'],'enhanced':enhanced['first_damage_seconds']}
        reports.append({'fps':fps,'path':str(directory/f'countess-q-comparison-{fps}.json'),
                        'sha256':digest(directory/f'countess-q-comparison-{fps}.json'),
                        'cases':len(report['cases']),'captures':len(report['screenshots'])})
        images+=report['screenshots']
    assert {i['image'] for i in images}=={i['path'] for i in review['images']}
    for image in review['images']:
        assert digest(Path(image['path']))==image['sha256']
    before=read(BASE/'before-source-hashes.json')
    changed=[p for p,h in before.items() if digest(PROJECT/p)!=h]
    assert set(changed)=={'Source/LearnTopDown/CountessSkillComponent.cpp','Source/LearnTopDown/CountessSkillComponent.h'}
    old=(BASE/'before-CountessSkillComponent.cpp').read_bytes()
    current=SOURCE.read_bytes()
    assert e_blocks(old) and e_blocks(old)==e_blocks(current)
    start=b'const TCHAR* Animations[]'
    end=b'ConstructorHelpers::FObjectFinder<UParticleSystem> Return('
    assert old[old.index(start):old.index(end)]==current[current.index(start):current.index(end)]
    for path,backup in ((SOURCE,BASE/'before-CountessSkillComponent.cpp'),(HEADER,BASE/'before-CountessSkillComponent.h')):
        data=path.read_bytes()
        assert b'\n' not in data.replace(b'\r\n',b'')
        assert data.startswith(b'\xef\xbb\xbf')==backup.read_bytes().startswith(b'\xef\xbb\xbf')
    for name in ('build-editor-v2.log','build-game-v2.log'):
        assert 'Result: Succeeded' in (BASE/name).read_text(errors='replace')
    material=read(BASE/'material-04/material.json')
    assert material['passed'] and material['graph_connections_verified']
    baseline_directory=PROJECT/'Saved/QA/CharacterPipeline/baseline-countess-q-preview-20261015'
    capture(baseline_directory)
    new_baseline=read(baseline_directory/'baseline.json')['protected_hashes']
    old_baseline=read(PROJECT/'Saved/QA/CharacterPipeline/baseline-training-room-complete-20261015/baseline.json')['protected_hashes']
    assert all(new_baseline[p]==h for p,h in old_baseline.items())
    new_files=sorted(set(new_baseline)-set(old_baseline))
    assert new_files==['Content/TopDown/Characters/Countess/Materials/M_CountessQImpactAccent.uasset']
    manifest=read(PROJECT/'Binaries/Win64/UnrealEditor.modules')
    assert manifest['Modules']['LearnTopDown']=='UnrealEditor-LearnTopDown-6152.dll'
    result={'passed':True,'status':'preview_ready','scope':'Countess Q visual presentation only',
            'user_style_approval':False,'default_enhanced_presentation':True,
            'presentation_switch':'Countess.Skills.QPresentation 0|1',
            'map':'/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom','verification':reports,
            'cases':12,'native_screenshots':42,'visual_review':str(BASE/'visual-review.json'),
            'visual_review_sha256':digest(BASE/'visual-review.json'),'q_damage':35,
            'q_hit_seconds':timings,'E_logic_byte_identical':True,'skill_definition_defaults_byte_identical':True,
            'source_files_changed':changed,'original_protected_files_unchanged':len(old_baseline),
            'new_content_files':new_files,'source_hashes':{str(p.relative_to(PROJECT)):digest(p) for p in (SOURCE,HEADER)},
            'material_sha256':new_baseline[new_files[0]],'editor_build':'build-editor-v2.log','game_build':'build-game-v2.log',
            'editor_module':'Binaries/Win64/UnrealEditor-LearnTopDown-6152.dll',
            'editor_module_sha256':digest(PROJECT/'Binaries/Win64/UnrealEditor-LearnTopDown-6152.dll'),
            'next_pipeline_baseline':str(baseline_directory/'baseline.json'),
            'preview':str(BASE/'compare-60-04/review/Q-staged-detail.gif'),
            'preview_is_staged_not_realtime_recording':True,
            'physical_OS_input_tested':False,'GPU_performance_benchmark':False,
            'full_other_skill_or_character_regression':False,
            'existing_editor_requires_restart_for_new_module':True,
            'render_judgment':'Impact is more readable; this is a focused accent preview, not a major spectacle redesign.',
            'tool_hashes':{p.name:digest(p) for p in (PROJECT/'Tools/CharacterPipeline').glob('countess_q_*.py')}}
    (BASE/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'status':result['status'],'cases':12,'screenshots':42,'result':str(BASE/'result.json')}),flush=True)


if __name__=='__main__':
    main()
