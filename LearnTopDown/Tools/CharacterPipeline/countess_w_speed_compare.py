"""Compare real W animation/FX timing at 1x and 1.5x, preserving gameplay contracts."""
import hashlib
import json
import math
from pathlib import Path
import sys
import types

import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
from context import fps,qa
from training_room_verify import TrainingRunner,room,select,skill
from character_switch import FieldRig
from sparrow_runtime import xyz,valid

CAPTURE_TIMES=(.10,.20,.30,.40,.55,.70,.90,1.20)


def particle_settings(rig):
    rows=[]
    for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
        if not valid(particle) or not particle.component_has_tag('CountessSkillFX') or not particle.is_active():
            continue
        outer=particle.get_outer()
        while outer is not None and outer!=rig.world:
            outer=outer.get_outer()
        if outer!=rig.world:
            continue
        template=particle.get_editor_property('template')
        if template:
            rows.append({'component':particle.get_path_name(),'template':template.get_path_name(),
                         'custom_time_dilation':particle.get_editor_property('custom_time_dilation'),
                         'weapon_trail':particle.component_has_tag('CountessSkillWeaponTrail')})
    return rows


def record(rig):
    previous=len(rig.trace)
    FieldRig.record(rig)
    if len(rig.trace)==previous or rig.latest['pawn_class']!='BP_CountessCharacter_C':
        return
    rig.latest['countess_native']=rig.native('CountessSkillsQA.State','w-speed-native-state')
    rig.latest['owned_fx']=particle_settings(rig)


def settle_switch(rig,name,moving=False,camera_settled=True):
    if not moving and camera_settled:
        started=rig.now
        previous_time=rig.now
        previous=xyz(rig.controller.player_camera_manager.get_camera_location())
        stable=None
        while rig.now-started<=5:
            yield 1/fps
            now=rig.now
            camera=xyz(rig.controller.player_camera_manager.get_camera_location())
            dt=now-previous_time
            speed=math.dist(camera,previous)/dt if dt>0 else float('inf')
            stopped=math.sqrt(sum(v*v for v in xyz(rig.pawn.get_velocity())))<1
            if stopped and speed<=.1:
                stable=previous_time if stable is None else stable
                if now-stable>=.2-.00001:
                    break
            else:
                stable=None
            previous,previous_time=camera,now
        rig.check(stable is not None and rig.now-stable>=.2-.00001,
                  'W-suite-only switch waits for the actual camera to settle before shared 1cm checks')
    yield from FieldRig.switch(rig,name,moving=moving,camera_settled=camera_settled)


def rate(rig,value,ignore=True):
    for command in ('Countess.Skills.WPresentation 3','Countess.Skills.WPlayRate '+str(value),
                    'Countess.Skills.IgnoreCooldowns '+str(int(ignore))):
        unreal.SystemLibrary.execute_console_command(rig.world,command)
    rig.check(unreal.SystemLibrary.get_console_variable_int_value('Countess.Skills.WPresentation')==3,
              'both speed variants use the same current textured spiral W')
    rig.check(abs(unreal.SystemLibrary.get_console_variable_float_value('Countess.Skills.WPlayRate')-value)<.001,
              'the requested real W playback-rate control is active')


def statue(rig,x,y):
    target=rig.dummy(x,y)
    source=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.KwangTrainingDummy)
                if 'TrainingRoomTarget' in [str(t) for t in a.tags]).get_component_by_class(unreal.StaticMeshComponent)
    mesh=target.get_component_by_class(unreal.StaticMeshComponent)
    mesh.set_static_mesh(source.get_editor_property('static_mesh'))
    mesh.set_relative_location(unreal.Vector(0,0,-90),False,False)
    mesh.set_relative_scale3d(unreal.Vector(.8,.8,.85))
    for slot in range(source.get_num_materials()):
        mesh.set_material(slot,source.get_material(slot))
    return target


def finished(rig):
    yield rig.idle(6)
    yield rig.until(lambda:not any(e['active'] and e['particles']>0 for e in rig.latest['effects']),
                    12,'W effects naturally expire without forced fixture cleanup')
    rig.assert_recovered()


def warm(rig):
    yield from select(rig,'countess')
    for value in (1,1.5):
        rate(rig,value)
        yield from rig.skill_key('W',rig.ground(0,170))
        yield from finished(rig)


def effect_kind(template):
    for label,needle in (('ring','P_CountessW_SpiralRing'),('trails','P_CountessW_DenseTrails'),
                         ('hit','P_CountessW_DenseHit'),('weapon','p_CountessMeleeTrail'),('smoke','p_SmokeyBlade')):
        if needle in template:
            return label
    return None


def trial(value):
    def run(rig):
        yield from select(rig,'countess')
        rate(rig,value)
        definition=rig.component.get_editor_property('skills')[1]
        for field,expected in (('damage',40),('range',240),('cooldown',6),('action_time',.55),('recovery_time',.95)):
            rig.check(abs(definition.get_editor_property(field)-expected)<.001,'W configured '+field+' remains unchanged')
        targets=[statue(rig,x,y) for x,y in ((0,170),(-145,50),(130,-70))]
        outside=statue(rig,0,400)
        rig.aim_target(targets[0])
        started=rig.now
        yield from rig.skill_key('W',targets[0].get_actor_location())
        rig.check(rig.component.is_casting(),'W starts through actual controller input')
        index=0
        while rig.now-started<1.2+2/fps:
            elapsed=rig.now-started
            if index<len(CAPTURE_TIMES) and elapsed>=CAPTURE_TIMES[index]-.00001:
                rig.snapshot()
                current=rig.native('CountessSkillsQA.State','w-speed-native-state')
                rig.data.setdefault('frames',[]).append({'index':index,'elapsed':elapsed,'native':current,
                    'effects':particle_settings(rig),'pawn':xyz(rig.pawn.get_actor_location()),
                    'camera':rig.latest['view_location'],'healths':[rig.health(t) for t in targets]})
                yield rig.capture(f'W-rate-{value:g}-{index:02}')
                index+=1
            else:
                yield 1/fps
        rig.check(index==len(CAPTURE_TIMES),'all eight actual-time comparison frames were captured')
        rows=[r for r in rig.trace if r['time']>=started-.00001]
        hits=[r['time']-started for r in rows if r['healths'] and r['healths'][0]<100]
        recovered=[r['time']-started for r in rows if r['time']>started+1/fps and not r['casting']]
        tolerance=3/fps+.0001
        rig.check(hits and abs(min(hits)-.55/value)<=tolerance,'actual W hit time follows .55 divided by animation rate')
        rig.check(recovered and abs(min(recovered)-.95/value)<=tolerance,'actual W recovery follows .95 divided by animation rate')
        rig.check(all(rig.health(t)==60 for t in targets) and rig.health(outside)==100,
                  'each nearby target receives one 40-damage hit and the outside target remains unharmed')
        animation=[r['countess_native'] for r in rows if r.get('countess_native',{}).get('casting')
                   and r['countess_native']['active_skill']==2 and r['countess_native']['montage']]
        rig.check(animation and all(abs(r['montage_play_rate']-value)<.001 for r in animation),
                  'the actual live W montage plays at the requested rate')
        onset={}
        dilations={}
        for row in rows:
            for particle in row.get('owned_fx',[]):
                kind=effect_kind(particle['template'])
                if kind:
                    onset.setdefault(kind,row['time']-started)
                    dilations.setdefault(kind,[]).append(particle['custom_time_dilation'])
        for kind,base in (('ring',.85),('trails',.85),('hit',.9),('weapon',1),('smoke',1)):
            rig.check(kind in dilations and all(abs(v-base*value)<.001 for v in dilations[kind]),
                      'actual '+kind+' particle simulation speed tracks the W playback rate')
        for kind,at in (('weapon',.12),('smoke',.12),('ring',.30),('trails',.30),('hit',.55)):
            rig.check(abs(onset[kind]-at/value)<=tolerance,'actual '+kind+' cue follows its scaled animation time')
        positions=[r for r in rows if r.get('countess_native',{}).get('casting') and r['time']-started<.45/value]
        if len(positions)>=2:
            first,last=positions[0],positions[-1]
            measured=(last['countess_native']['montage_position']-first['countess_native']['montage_position'])/(last['time']-first['time'])
            rig.check(abs(measured-value)<.08,'observed montage-position progression matches its actual playback rate')
        else:
            raise AssertionError('W montage progression requires at least two actual samples')
        rig.data.update(play_rate=value,first_damage_seconds=min(hits),recovery_seconds=min(recovered),
                        expected_hit_seconds=.55/value,expected_recovery_seconds=.95/value,
                        target_healths=[rig.health(t) for t in targets],outside_health=rig.health(outside),
                        effect_onset_seconds=onset,effect_simulation_rates=dilations,measured_montage_position_rate=measured)
        trace_path=qa/f'W-rate-{value:g}-full-trace.json'
        trace_path.write_text(json.dumps({'fps':fps,'play_rate':value,'samples':rows},indent=2),encoding='utf-8')
        rig.data['full_simulation_trace']={'path':str(trace_path),'sha256':hashlib.sha256(trace_path.read_bytes()).hexdigest(),'samples':len(rows)}
        yield from finished(rig)
    return run


def unchanged(key,health,index):
    def run(rig):
        rate(rig,1.5)
        yield from skill('countess',key)(rig)
        rig.check(rig.data['target_health_minimum']==health,key+' damage is unchanged')
        animation=[r['countess_native'] for r in rig.trace if r.get('countess_native',{}).get('casting')
                   and r['countess_native']['active_skill']==index and r['countess_native']['montage']]
        rig.check(animation and all(abs(r['montage_play_rate']-1)<.001 for r in animation),
                  key+' actual montage rate remains 1 while W is configured to 1.5')
        rig.data['observed_montage_rates']=sorted(set(r['montage_play_rate'] for r in animation))
    return run


def early_cancel(rig):
    yield from select(rig,'countess')
    rate(rig,1.5)
    target=statue(rig,0,170)
    yield from rig.skill_key('W',target.get_actor_location())
    yield .20
    rig.anim.montage_stop(.01)
    yield .6
    rig.check(rig.health(target)==100,'cancelling accelerated W before its real hit prevents delayed damage')
    yield from finished(rig)
    rig.snapshot()
    yield rig.capture('W-speed-cancelled')


def owner_cleanup(rig):
    yield from select(rig,'countess')
    rate(rig,1.5)
    target=statue(rig,0,170)
    yield from rig.skill_key('W',target.get_actor_location())
    yield .28
    rig.snapshot()
    rig.check(any('CountessW_' in e['template'] and e['particles']>0 for e in rig.latest['effects']),
              'accelerated textured W is visibly active before numeric selection')
    previous=rig.pawn
    rig.key('Press','Two')
    yield 1/fps
    rig.key('Release','Two')
    rig.hero('sparrow')
    yield .6
    rig.snapshot()
    rig.check(not valid(previous) and not particle_settings(rig),'numeric Two destroys the previous owner and its W particles')
    yield rig.capture('W-speed-owner-cleanup')


def cooldown(rig):
    yield from rig.switch('sparrow')
    yield from rig.switch('countess')
    rate(rig,1.5,False)
    target=statue(rig,0,170)
    started=rig.now
    yield from rig.skill_key('W',target.get_actor_location())
    yield .85
    rig.check(rig.health(target)==60 and not rig.component.is_casting(),'accelerated W completes once with normal cooldowns')
    state=rig.native('CountessSkillsQA.State','w-speed-native-state')
    remaining=state['cooldowns'][1]
    rig.check(abs(remaining-(6-(rig.now-started)))<=2/fps+.001,'the actual W cooldown still counts down from six seconds')
    yield from rig.skill_key('W',target.get_actor_location())
    rig.check(not rig.component.is_casting() and rig.component.get_input_feedback()=='Cooldown','accelerated W cannot bypass its normal cooldown')
    yield max(1/fps,6.15-(rig.now-started))
    yield from rig.skill_key('W',target.get_actor_location())
    rig.check(rig.component.is_casting(),'W becomes available again after its unchanged six-second cooldown')
    yield from finished(rig)
    rig.check(rig.health(target)==20,'the accepted post-cooldown cast adds exactly one further 40-damage hit')
    rig.data.update(configured_cooldown=6,observed_remaining_cooldown=remaining)
    rig.snapshot()
    yield rig.capture('W-speed-cooldown')


class WSpeedRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases=[('room',room),('W_renderer_warmup',warm),('W_rate_1',trial(1)),('W_rate_1_5',trial(1.5)),
                    ('Q_unchanged',unchanged('Q',65,1)),('E_unchanged',unchanged('E',55,3)),
                    ('R_unchanged',unchanged('R',20,4)),('W_early_cancel',early_cancel),
                    ('W_normal_cooldown',cooldown),('W_owner_cleanup',owner_cleanup)]
        self.report_name=f'countess-w-speed-comparison-{fps}.json'
        self.report.update(suite='countess_W_actual_animation_and_all_FX_speed',physical_input_tested=False,
                           capture_kind='native fixed-viewport actual-time paused PIE samples, not continuous video',
                           compared_W_presentation=3,play_rates=[1,1.5],native_fixed_viewport_size=[700,330])

    def case_generator(self,factory):
        self.rig.record=types.MethodType(record,self.rig)
        self.rig.switch=types.MethodType(settle_switch,self.rig)
        if not getattr(self,'fixed_viewport_configured',False):
            unreal.SystemLibrary.execute_console_command(self.rig.world,'CharacterVisualQA.ViewportSize 700 330')
            yield 2/fps
            self.rig.snapshot()
            self.rig.check(self.rig.latest['viewport_size']==[700,330],'actual native PIE render size is fixed before the first capture')
            self.fixed_viewport_configured=True
        yield from TrainingRunner.case_generator(self,factory)
        self.rig.check(all(s['width']==700 and s['height']==330 for s in self.report['screenshots']),
                       'every native screenshot retains the fixed 700x330 framing')


if __name__=='__main__':
    runtime=WSpeedRunner()
    runtime.start()
