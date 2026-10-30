"""Current native Countess, real input and camera; reused by baseline and final review."""
import json
import os
from pathlib import Path
import unreal

DESIGNS = {
    'Q': ('그림자 쌍검', 1.45, (360, 0)),
    'W': ('혈색 교차검', 1.35, (280, 0)),
    'E': ('심연 봉합', 1.85, (440, 0)),
    'R': ('관통 집행', 2.10, (250, 0)),
    'A': ('협공 잔영', 2.80, (300, 0)),
    'S': ('혈갑 현신', 2.0, (160, 0)),
    'D': ('삼중 절개', 1.5, (300, 0)),
    'F': ('공간 절단', 1.1, (540, 0)),
    'V': ('그림자 처형장', 4.5, (120, 0)),
    'Space': ('잔영 후퇴', 1.0, (450, 0)),
}

def sequence(rig):
    out, state = rig['OUT'], rig['STATE']
    baseline = os.environ.get('COUNTESS_REBIRTH_BASELINE') == '1'
    selected = os.environ.get('COUNTESS_REBIRTH_KEYS', ','.join(DESIGNS)).split(',')
    modes = os.environ.get('COUNTESS_REBIRTH_MODES', 'normal').split(',')
    report = {'passed': False, 'baseline': baseline, 'cases': []}
    def save():
        (out/'rebirth-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def now():return unreal.GameplayStatics.get_time_seconds(rig['world']())
    try:
        for key in selected:
            label,duration,point=DESIGNS[key]
            for mode in (['normal'] if key=='S' else modes):
                rig['switch']('sparrow');yield .16
                rig['switch']('countess');yield .65
                ds=rig['layout']([(point[0],260) if key=='F' else point,(point[0],350),(800,-350)]);yield .18
                if mode=='form':
                    rig['use']('S',ds[0]);yield 1.05
                    for d in ds:d.reset_dummy()
                rig['aim'](offset=point) if key=='F' else rig['aim'](ds[0])
                ident=key+'_'+mode
                rig['case']('Countess_rebirth_'+ident)
                start=now();origin=rig['pawn']().get_actor_location()
                state['video_clip']={'case':ident,'prefix':ident+'_video','cast_time':start,'frame_times':[]}
                rig['key']('SpaceBar' if key=='Space' else key)
                moments=[.067,.133,.233,.333,.45,.55,.7,.9,1.1,1.4,1.8,2.3,3.2,4.0]
                busy=False
                while now()-start<duration:
                    age=now()-start;busy|=rig['pawn']().is_combat_busy()
                    if moments and age>=moments[0]:
                        rig['capture'](ident+'_t'+str(round(moments.pop(0)*1000)).zfill(4))
                    yield 1./rig['FPS']
                rig['finish_video_clip']()
                row={'id':ident,'key':key,'mode':mode,'label':label,'duration':duration,
                     'accepted':busy or (key=='F' and rig['dist'](origin,rig['pawn']().get_actor_location())>100.),'health':[rig['health'](d) for d in ds],
                     'distance':rig['dist'](origin,rig['pawn']().get_actor_location())}
                report['cases'].append(row);save()
                rig['check'](row['accepted'] or (baseline and key=='W'),ident+' actual cast accepted (baseline W is empty)')
                rig['check'](not rig['pawn']().is_combat_busy(),ident+' recovered native input state')
                if not baseline and key=='W' and os.environ.get('COUNTESS_W_SOURCE_REVIEW')=='1':
                    effects=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.CountessRebirthFX) if a.actor_has_tag('CountessWSourceFX')]
                    rig['check'](len(effects)==1,ident+' uses source particle W presentation')
                    parts=effects[0].get_components_by_class(unreal.InstancedStaticMeshComponent) if effects else []
                    rig['check'](len(parts)==2 and all(c.get_instance_count()==0 and c.get_editor_property('static_mesh') is None for c in parts),ident+' no rejected procedural meshes loaded or rendered')
                if not baseline:
                    damage={'Q':35.,'W':65.,'E':55.,'R':90.,'A':60.,'S':24.,'D':54.,'F':0.,'V':84.,'Space':0.}[key]
                    if mode=='form' and key in ('W','E','R','A','D','V'):damage*=1.2
                    rig['check'](abs(row['health'][0]-max(0.,100.-damage))<.02,ident+' actual primary damage')
                    if key in ('Q','W','E','D'):
                        rig['check'](row['health'][1]==100.,ident+' excludes the lateral fixture')
                    if key=='F':rig['check'](350.<row['distance']<751.,ident+' real safe blink displacement')
                    if key=='Space':rig['check'](150.<row['distance']<225.,ident+' actual backstep displacement')
                before=rig['pawn']().get_actor_location();goal=rig['ground'](before.x,before.y+250)
                rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                yield .4
                rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                rig['check'](rig['dist'](before,rig['pawn']().get_actor_location())>40.,ident+' real mouse movement after cast')
                save()
        if not baseline and 'W' in selected:
            rig['switch']('sparrow');yield .16
            rig['switch']('countess');yield .6
            ds=rig['layout']([(280,0),(280,350),(800,-350)]);yield .18
            rig['case']('Countess_rebirth_W_cancel')
            rig['use']('W',ds[0]);yield .10
            rig['pawn']().get_editor_property('mesh').get_anim_instance().montage_stop(.01)
            yield .8
            rig['check'](rig['health'](ds[0])==100.,'cancelled W emits no scheduled damage')
            rig['check'](not rig['pawn']().is_combat_busy(),'cancelled W recovers input')
            rig['switch']('sparrow');yield .18
            rig['switch']('countess');yield .6
            ds=rig['layout']([(280,0),(280,350),(800,-350)]);yield .18
            rig['cmd']('Countess.Skills.IgnoreCooldowns 0')
            rig['case']('Countess_rebirth_W_cooldown')
            rig['use']('W',ds[0]);yield .8
            rig['use']('W',ds[0]);yield .15
            rig['check'](not rig['pawn']().is_combat_busy(),'W rejects recast during cooldown')
            rig['check']('cooldown' in rig['skills']().get_input_feedback().lower(),'W rejection identifies cooldown')
            yield 7.2
            for d in ds:d.reset_dummy()
            rig['use']('W',ds[0]);yield .8
            rig['check'](abs(rig['health'](ds[0])-35.)<.02,'W accepts a new real cast after eight seconds')
            rig['cmd']('Countess.Skills.IgnoreCooldowns 1')
        if not baseline:
            rig['switch']('sparrow');yield .20
            remaining=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.CountessRebirthFX)
            rig['check'](not remaining,'owner switch removes every CountessRebirthFX actor')
        report['passed']=True
    finally:
        rig['finish_video_clip']();save()
