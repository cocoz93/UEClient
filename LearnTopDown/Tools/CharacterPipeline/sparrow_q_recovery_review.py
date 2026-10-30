"""Focused actual-input review of Q recovery and the independent S/F slots."""
import json
import os
import unreal

def sequence(rig):
    if os.environ.get('SPARROW_RECOVERY_PART')=='a':
        yield from native_a_sequence(rig)
        return
    now=lambda:unreal.GameplayStatics.get_time_seconds(rig['world']())
    rows=[]
    rig['switch']('sparrow');yield .7
    rig['case']('Q_short_recovery')
    targets=rig['layout']([(500,0),(500,100),(900,-350)]);yield .2
    initial=[rig['health'](t) for t in targets]
    start=now();rig['use']('Q',offset=(500,0))
    rig['STATE']['video_clip']={'case':'Q_short_recovery','prefix':'Q_short_recovery_video','cast_time':start,'frame_times':[]}
    released=None;shots=[.18,.28,.40,.60,.85]
    while now()-start<1.05:
        age=now()-start
        if released is None and age>.1 and not rig['skills']().is_casting():released=age
        if shots and age>=shots[0]:rig['capture']('Q_short_t'+str(round(shots.pop(0)*100)).zfill(3))
        yield 1/rig['FPS']
    rig['finish_video_clip']()
    rig['check'](released is not None and .32<released<.44,'Q ends near .36 seconds after its .24-second release')
    rig['check'](rig['health'](targets[0])<initial[0],'Q still starts native hail damage')
    before=rig['pawn']().get_actor_location()
    point=rig['ground'](before.x+280.,before.y-250.)
    rig['cmd'](f'CountessComboQA.Mouse Press Right {point.x} {point.y} {point.z}')
    yield .55
    rig['cmd'](f'CountessComboQA.Mouse Release Right {point.x} {point.y} {point.z}')
    distance=rig['dist'](before,rig['pawn']().get_actor_location())
    rig['check'](distance>100.,'Q permits actual mouse movement after recovery')
    yield 2.9
    damage=[a-rig['health'](t) for a,t in zip(initial,targets)]
    rig['check'](abs(damage[0]-40.)<.03 and abs(damage[1]-40.)<.03 and damage[2]==0.,'short Q recovery preserves the full four-second area damage')
    rig['recovered']()
    rows.append({'case':'normal','released':released,'movement_cm':distance,'damage':damage})

    rig['case']('Q_cancel_before_release')
    targets=rig['layout']([(500,0),(500,100),(900,-350)]);yield .2
    rig['use']('Q',offset=(500,0));yield .10
    rig['cmd']('SparrowSanctuaryQA.Cancel');yield .50
    rig['check'](all(rig['health'](t)==100. for t in targets),'Q cancelled before release creates no hail damage')
    rig['recovered']()

    rig['case']('S_sharp_F_preserved')
    rig['use']('S',offset=(600,0));yield .12
    rig['check'](len(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowSharpVolley))==1,'S starts the restored Sharp Shooter actor')
    rig['check'](rig['skills']().is_casting() and rig['skills']().get_active_skill_number()==10,'S uses its own casting slot')
    yield .85
    rig['recovered']()
    rig['use']('F',offset=(600,0));yield .35
    guards=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowSanctuary)
    rig['check'](len(guards)==1,'independent F counter ward still spawns')
    yield 2.7
    rig['recovered']()
    (rig['OUT']/'q-recovery-review.json').write_text(json.dumps({'passed':True,'fps':rig['FPS'],'cases':rows},indent=2),encoding='utf-8')

def native_a_sequence(rig):
    rig['switch']('sparrow');yield .6
    rig['case']('A_restored')
    targets=rig['layout']([(260,0),(480,0),(550,350)]);yield .2
    start=unreal.GameplayStatics.get_time_seconds(rig['world']())
    rig['use']('A',targets[0])
    rig['STATE']['video_clip']={'case':'A_restored','prefix':'A_restored_video','cast_time':start,'frame_times':[]}
    moments=[.3,.7,1.3,2.2]
    while unreal.GameplayStatics.get_time_seconds(rig['world']())-start<4.4:
        age=unreal.GameplayStatics.get_time_seconds(rig['world']())-start
        if moments and age>=moments[0]:rig['capture']('A_restored_t'+str(round(moments.pop(0)*100)).zfill(3))
        yield 1/rig['FPS']
    rig['check'](abs(rig['health'](targets[0])-10.)<.03 and abs(rig['health'](targets[1])-10.)<.03,'restored A retains 90 damage to both pierced targets')
    rig['recovered']()
