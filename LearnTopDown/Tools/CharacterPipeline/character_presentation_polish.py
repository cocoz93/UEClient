"""Reuse one room PIE for selected presentation changes and related timing checks."""
import json
import math
import os
from pathlib import Path
import sys
import traceback
import types
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
job={'output':str(OUT),'profile':str(ROOT/'Tools/CharacterPipeline/Profiles/sparrow.json'),
     'fps':int(os.environ.get('SPARROW_QA_FPS','60')),'baseline':str(OUT.parent/'target-baseline.json')}
(OUT/'job.json').write_text(json.dumps(job),encoding='utf-8')
os.environ['CHARACTER_PIPELINE_JOB']=str(OUT/'job.json')

try:
    if os.environ.get('PRESENTATION_WER_VISIBLE')=='1':
        from sparrow_w_axial_materials import author_materials,author_volley_fan
        assert len(author_materials(OUT))==3
        assert author_volley_fan(OUT)['passed']
    if os.environ.get('PRESENTATION_CRISP_Q')=='1':
        from sparrow_w_axial_materials import author_hail_indicator
        assert author_hail_indicator(OUT)['passed']
    from sparrow_ivory_hood_assets import author,HOOD_SLOT,DESTINATION
    requested=os.environ.get('PRESENTATION_CASES','')
    if 'ivory_hood' in requested:
        assert author(OUT)['passed']
    from countess_qw_refine_assets import author_refinements,Q_TARGET,W_TARGET
    if os.environ.get('PRESENTATION_REUSE_ASSETS')!='1':
        assert author_refinements(OUT,q_only=requested=='assassin_Q_short_body')['passed']
    else:
        assert unreal.load_asset(Q_TARGET) and unreal.load_asset(W_TARGET)
    if os.environ.get('PRESENTATION_INSPECT_RAPID')=='1':
        candidates=[]
        for name in ('Primary_Fire_Fast','R_Ability_Fast_Fire','Primary_Fire_Med'):
            path='/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/'+name
            animation=unreal.load_asset(path)
            candidates.append({'asset':path,'exists':animation is not None,
                'length_seconds':animation.get_play_length() if animation else None,
                'skeleton':animation.get_editor_property('skeleton').get_path_name() if animation else None})
        (OUT/'archer-rapid-candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
except Exception:
    (OUT/'asset-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
else:
    from context import fps
    from training_room_verify import TrainingRunner,select
    from countess_w_speed_compare import settle_switch,statue
    from sparrow_pose import close_capture
    from sparrow_runtime import valid,xyz

    def material_source(material):
        while isinstance(material,unreal.MaterialInstanceDynamic): material=material.get_editor_property('parent')
        return material.get_path_name()
    def materials(rig): return [material_source(rig.mesh.get_material(i)) for i in range(rig.mesh.get_num_materials())]

    def assassin_w(rig):
        yield from select(rig,'countess')
        target=statue(rig,0,170)
        rig.aim_target(target)
        start=rig.now
        yield from rig.skill_key('W',target.get_actor_location())
        yield max(1/fps,.38-(rig.now-start))
        ring=[]
        for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not valid(particle) or not particle.component_has_tag('CountessWTexturedVortex'): continue
            template=particle.get_editor_property('template')
            if template and template.get_path_name().startswith(W_TARGET): ring.append(particle)
        rig.check(bool(ring) and all(max(abs(v-1) for v in xyz(p.get_world_scale()))<.001 for p in ring),
                  'W lighter smoke retains its original full spatial size')
        rig.check(all(abs(p.get_editor_property('custom_time_dilation')-.85*1.95)<.001 for p in ring),
                  'lighter W particles follow the accelerated animation')
        rig.snapshot()
        if fps==60: yield rig.capture('assassin-W-light-full-size')
        yield rig.idle(3)
        rig.check(rig.health(target)==60,'W damage remains 40')
        hit=min(row['time']-start for row in rig.trace if row['healths'] and row['healths'][0]<100)
        rig.check(abs(hit-.55/1.95)<=3/fps,'W damage follows its faster 1.95 playback rate')
        rig.data.update(first_hit_seconds=hit,expected_hit_seconds=.55/1.95)
        rig.assert_recovered()

    def assassin_w_cancel(rig):
        yield from select(rig,'countess')
        target=statue(rig,0,170)
        yield from rig.skill_key('W',target.get_actor_location())
        yield .08
        rig.interrupt()
        yield .6
        rig.check(rig.health(target)==100,'cancelling faster W before its hit prevents damage')
        rig.assert_recovered()

    def assassin_w_preview(rig, variant):
        yield from select(rig,'countess')
        unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.WPreview '+str(variant))
        unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 1')
        target=statue(rig,0,170)
        rig.aim_target(target)
        start=rig.now
        yield from rig.skill_key('W',target.get_actor_location())
        for at in (.04,.11,.18,.25,.32,.39,.46,.60):
            yield max(1/fps,at-(rig.now-start))
            rig.snapshot()
            if fps==60: yield rig.capture('assassin-W-preview-'+str(variant)+'-'+str(at))
        yield rig.idle(3)
        rig.check(rig.health(target)==60,'W preview preserves its original 40 damage')
        rig.assert_recovered()
        unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.WPreview 0')

    def assassin_e_rollback(rig):
        yield from select(rig,'countess')
        definition=rig.component.get_editor_property('skills')[2]
        for field,expected in (('damage',45),('range',900),('action_time',.36),('recovery_time',.8)):
            rig.check(abs(definition.get_editor_property(field)-expected)<.001,'restored E '+field)
        target=rig.dummy(0,600)
        side=rig.dummy(250,400)
        start=rig.now
        yield from rig.skill_key('E',target.get_actor_location())
        yield .43
        rig.check(bool(unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.CountessDarkTide)),
                  'restored E launches its original traveling Dark Tide')
        yield rig.until(lambda:rig.health(target)<100,2,'restored E reaches its distant target')
        rig.check(rig.health(target)==55 and rig.health(side)==100,'restored E deals 45 once in its forward corridor')
        yield rig.idle(3)
        rig.assert_recovered()

    def assassin_e_cancel(rig):
        yield from select(rig,'countess')
        unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 1')
        target=rig.dummy(0,600)
        yield from rig.skill_key('E',target.get_actor_location())
        yield .1
        rig.interrupt()
        yield 1.2
        rig.check(rig.health(target)==100 and not unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.CountessDarkTide),
                  'interrupt before original E release prevents its wave and damage')
        rig.assert_recovered()

    def assassin_q(rig):
        yield from select(rig,'countess')
        target=statue(rig,0,400)
        start=rig.now
        yield from rig.skill_key('Q',target.get_actor_location())
        yield max(1/fps,.24-(rig.now-start))
        sources=[]
        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.Actor):
            if actor.actor_has_tag('CountessQDualSweep'):
                sources += [material_source(m.get_material(0)) for m in actor.get_components_by_class(unreal.StaticMeshComponent)]
        rig.check(sources and all(s.startswith(Q_TARGET) for s in sources),'Q uses the body-only compact shader')
        rig.snapshot()
        yield rig.capture('assassin-Q-short-body')
        yield rig.idle(3)
        rig.check(rig.health(target)==65,'shorter solid Q keeps its 35 damage')
        rig.assert_recovered()

    def hood(rig):
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Appearance.IvoryHood 0')
        yield from select(rig,'sparrow')
        rig.pawn.set_actor_rotation(unreal.Rotator(yaw=215),True)
        original=materials(rig)
        index=rig.mesh.get_material_index(HOOD_SLOT)
        rig.check(index>=0,'verified named hood slot exists')
        yield from close_capture(rig,'hood-original')
        yield from rig.switch('countess')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Appearance.IvoryHood 1')
        yield from rig.switch('sparrow')
        rig.pawn.set_actor_rotation(unreal.Rotator(yaw=215),True)
        yield .3
        changed=materials(rig)
        rig.data.update(hood_slot=index,original_materials=original,current_materials=changed,
                        enabled=unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Appearance.IvoryHood'))
        rig.check(changed[index].startswith(DESTINATION),'real pawn uses the private ivory hood')
        rig.check(len(original)==len(changed) and all(a==b for i,(a,b) in enumerate(zip(original,changed)) if i!=index),
                  'face, bow, cape and every other material slot remain unchanged')
        yield from close_capture(rig,'hood-ivory')
        rig.data.update(hood_slot=index,original_materials=original,current_materials=changed)

    def assassin_r_original(rig):
        yield from select(rig,'countess')
        unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 1')
        target=statue(rig,0,440)
        rig.aim_target(target)
        origin=rig.pawn.get_actor_location()
        start=rig.now
        yield from rig.skill_key('R',target.get_actor_location())
        rows=[]
        for at in (.2,.85,1.1,1.5,1.85,2.3):
            yield max(1/fps,at-(rig.now-start))
            state=rig.snapshot()
            distance=unreal.MathLibrary.vector_distance2d(origin,rig.pawn.get_actor_location())
            rows.append({'elapsed':rig.now-start,'distance':distance,'health':rig.health(target),'source_position':state['montage_position']})
            if at==.2: rig.check(abs(state['montage_position']-.2)<3/fps,'original R starts at source zero and plays at 1x')
            if at==.85: rig.check(distance<3,'original R retains its full initial preparation')
            if at==1.1: rig.check(3<distance<300,'original R travels during the source jump section')
            if at==1.5: rig.check(distance>250 and rig.health(target)==100,'original R reaches melee range before its stab')
            if fps==60: yield rig.capture('assassin-R-original-'+str(at))
        rig.check(rig.health(target)==20,'original R keeps its 1.8s single 80-damage stab')
        rig.data['original_R_timeline']=rows
        rig.assert_recovered()

    def archer_r_fan(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        aim=rig.pawn.get_actor_location()+unreal.Vector(0,1400,0)
        yield from rig.skill_key('R',aim)
        yield rig.until(rig.component.is_inner_fire_active,1,'R buff activates')
        activated=rig.now
        rig.check(rig.component.get_buff_remaining()>9.8,'R starts with the requested ten seconds')
        yield rig.idle(2)
        rig.mouse('Press','Left',aim)
        groups=[]; seen=set()
        start=rig.now
        captures=[.08,.2,.35,.8,1.05,1.5,1.9]
        while rig.now-start<3:
            new=[a for a in rig.arrows() if a.get_name() not in seen]
            if new:
                for a in new: seen.add(a.get_name())
                headings=sorted(round(math.degrees(math.atan2(a.get_flight_direction().y,a.get_flight_direction().x)),3) for a in new)
                groups.append({'elapsed':rig.now-start,'headings':headings,'count':len(new)})
                rig.check(len(new)==5 and all(abs((a-headings[2])-b)<.02 for a,b in zip(headings,[-24,-12,0,12,24])),'each R release emits five arrows in a 48-degree fan')
                rig.check(all(a.is_piercing() and not a.passes_world() for a in new),'fan arrows retain target piercing and solid wall blocking')
            if fps==60 and captures and rig.now-start>=captures[0]:
                at=captures.pop(0);yield rig.capture('archer-R-fan-'+str(at))
            else: yield 1/fps
        rig.mouse('Release','Left',aim)
        rig.check(len(groups)>=4,'R held attack has a faster visible release cadence')
        intervals=[b['elapsed']-a['elapsed'] for a,b in zip(groups,groups[1:])]
        rig.check(all(.65<v<.95 for v in intervals),'R cadence is faster while preserving the normal attack cooldown rule')
        yield rig.idle(2)
        rig.check(rig.component.is_inner_fire_active(),'ten-second R stays active after several volleys')
        yield max(1/fps,10.2-(rig.now-activated))
        rig.check(not rig.component.is_inner_fire_active(),'R expires and clears its buff after ten seconds')
        rig.check(not rig.anim.get_editor_property('HoldInnerFireReady'),'R expiry clears the tilted ready overlay')
        rig.data.update(releases=groups,intervals=intervals)
        rig.assert_recovered()

    def archer_e_fx_preview(rig,index):
        yield from rapid_ready(rig)
        target=statue(rig,0,700)
        rig.aim_target(target)
        start=rig.now
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.ArcherEPreview '+str(index)+' '+target.get_name())
        rig.data.update(preview_index=index,preview_started=start,preview_only=True)
        for frame in range(20):
            yield max(1/fps,frame*.075-(rig.now-start))
            yield rig.capture('archer-E-FX-'+str(index)+'-frame-'+str(frame).zfill(2))
        yield .4
        rig.check(abs(rig.health(target)-37.375)<.03,'FX preview retains the six real E arrows and their existing total passive damage')
        rig.assert_recovered()

    def assassin_r_readable(rig):
        yield from select(rig,'countess')
        target=statue(rig,0,440)
        rig.aim_target(target)
        origin=rig.pawn.get_actor_location()
        start=rig.now
        yield from rig.skill_key('R',target.get_actor_location())
        observations=[]
        for at in (.12,.25,.34,.44,.54):
            yield max(1/fps,at-(rig.now-start))
            state=rig.snapshot()
            distance=unreal.MathLibrary.vector_distance2d(origin,rig.pawn.get_actor_location())
            observations.append({'time':rig.now-start,'distance':distance,'health':rig.health(target),'montage_position':state.get('montage_position')})
            if at==.12: rig.check(distance<3,'R shows its jump preparation before moving')
            if at==.25: rig.check(3<distance<330,'R approaches through intermediate positions instead of teleporting')
            if at==.44: rig.check(distance>250 and rig.health(target)==100,'R reaches the target before the distinct stab impact')
            if fps==60: yield rig.capture('assassin-R-readable-'+str(at))
        yield rig.idle(2)
        rig.check(rig.health(target)==20,'R keeps its single 80-damage stab')
        rig.data['approach_observations']=observations
        rig.assert_recovered()

    def assassin_r_cancel(rig,at):
        yield from select(rig,'countess')
        target=statue(rig,0,440)
        start=rig.now
        yield from rig.skill_key('R',target.get_actor_location())
        yield max(1/fps,at-(rig.now-start))
        rig.interrupt()
        stopped=rig.pawn.get_actor_location()
        yield .9
        rig.check(rig.health(target)==100,'R interruption prevents the stab')
        rig.check(unreal.MathLibrary.vector_distance2d(stopped,rig.pawn.get_actor_location())<3,'interrupted R stops its approach without delayed movement')
        rig.assert_recovered()

    def assassin_r_blocked(rig):
        yield from select(rig,'countess')
        target=statue(rig,0,440)
        start=rig.now
        yield from rig.skill_key('R',target.get_actor_location())
        yield max(1/fps,.27-(rig.now-start))
        wall=rig.wall(0,230)
        wall.set_actor_scale3d(unreal.Vector(5,.4,3.5))
        yield 1.1
        rig.check(rig.health(target)==100,'wall introduced during preparation prevents R damage and arrival')
        rig.assert_recovered()

    def archer_q_dense(rig):
        yield from select(rig,'sparrow')
        target=statue(rig,0,650)
        outside=statue(rig,330,650)
        yield from rig.skill_key('Q',target.get_actor_location())
        yield .55
        markers=[a for a in unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator') if valid(a)]
        rig.check(len(markers)==1,'active Q has one persistent golden range circle')
        mesh=markers[0].get_component_by_class(unreal.StaticMeshComponent)
        rig.check(mesh is not None and mesh.get_collision_enabled()==unreal.CollisionEnabled.NO_COLLISION,'Q range marker has no collision')
        rig.data['indicator_scale']=xyz(mesh.get_world_scale())
        rig.data['indicator_material']=material_source(mesh.get_material(0))
        yield rig.capture('archer-Q-dense-gold-range')
        yield 4.1
        rig.check(abs(rig.health(target)-60)<.01 and rig.health(outside)==100,'denser Q retains total 40 damage and 300cm gameplay radius')
        rig.check(not unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator'),'Q range circle expires with its zone')
        rig.assert_recovered()

    def archer_q_owner(rig):
        yield from select(rig,'sparrow')
        target=statue(rig,0,650)
        yield from rig.skill_key('Q',target.get_actor_location())
        yield .6
        rig.check(bool(unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator')),'Q indicator exists before owner switch')
        yield from rig.switch('countess')
        yield .3
        rig.check(not unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator'),'owner switch removes the active Q indicator')
        rig.assert_recovered()

    def archer_w(rig):
        yield from select(rig,'sparrow')
        target=statue(rig,0,550)
        rig.aim_target(target)
        start=rig.now
        yield from rig.skill_key('W',target.get_actor_location())
        yield max(1/fps,.45-(rig.now-start))
        rig.check(not rig.arrows(),'shortened W still holds its arrow until the release cue')
        for at in (.68,.77,.84):
            yield max(1/fps,at-(rig.now-start))
            waves=unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave)
            rig.check(bool(waves),'enlarged W air waves are live at release')
            sizes=[]
            for mesh in waves[0].get_components_by_class(unreal.StaticMeshComponent):
                if mesh.is_visible():
                    if not mesh.get_name().startswith('AirWave'): continue
                    distance=mesh.get_editor_property('relative_location').x
                    scale=mesh.get_editor_property('relative_scale3d').x
                    progress=max(0,min(1,(distance-35)/(1300*.28)))
                    expected=(3.25+(0.85-3.25)*progress)*1.65*.5
                    rig.check(abs(scale-expected)<.01,'each W ring shrinks as it travels forward')
                    sizes.append((distance,scale))
            sizes.sort()
            rig.check(all(a[1]>b[1] for a,b in zip(sizes,sizes[1:])),
                      'rings near the bow are larger than the rings farther away')
            rig.data.setdefault('wave_distance_and_size',[]).append(sizes)
            all_meshes=waves[0].get_components_by_class(unreal.StaticMeshComponent)
            meshes={m.get_name():m for m in all_meshes if m.get_name().startswith('AirWave')}
            rig.check(len(meshes)==3,'W retains exactly three original ring surfaces')
            accents=[m for m in all_meshes if m.get_name().startswith('ShotAccent')]
            rig.check(len(accents)==3,'W adds two crossing wind sheets and one bow flash')
            rig.check(all('M_SparrowShotAirStrong' in material_source(mesh.get_material(0)) for mesh in meshes.values()),
                      'W restores its previous visible textured ring material')
            rig.snapshot()
            if fps==60: yield rig.capture('archer-W-half-ring-'+str(at))
        yield rig.idle(4)
        rig.check(rig.health(target)==65,'enlarged W retains the original 35 damage')
        release=min(row['time']-start for row in rig.trace if row.get('projectiles'))
        rig.check(abs(release-.62)<=3/fps,'W release follows its 0.5 second charge plus 0.12 second fire cue')
        rig.data['release_seconds']=release
        rig.check(not unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave),
                  'larger visual waves still expire without residual surfaces')
        rig.assert_recovered()

    def archer_w_cancel(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        target=statue(rig,0,550)
        yield from rig.skill_key('W',target.get_actor_location())
        yield .35
        rig.interrupt()
        yield 1.1
        rig.check(rig.health(target)==100 and not unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave),
                  'cancelled charge produces no damage or ring actor')
        rig.assert_recovered()

    def archer_w_owner(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        target=statue(rig,0,900)
        yield from rig.skill_key('W',target.get_actor_location())
        yield rig.until(lambda:bool(unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave)),
                        1.5,'release actor exists before selection changes')
        wave=unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave)[0]
        rig.key('Press','One')
        yield 1/fps
        rig.key('Release','One')
        yield .6
        rig.hero('countess')
        rig.check(not valid(wave),'switch clears restored ring actor')
        rig.check(abs(rig.controller.player_camera_manager.get_fov_angle()-55)<.001,'camera recoil ends after owner switch')

    def moving_cape(rig):
        yield from select(rig,'sparrow')
        yield from rig.click('Right',rig.ground(0,1100))
        for delay,label in ((.5,'moving-a'),(.5,'moving-b')):
            yield delay
            rig.snapshot()
            velocity=rig.pawn.get_velocity()
            rig.check(math.hypot(velocity.x,velocity.y)>200,'cape preview uses actual running movement')
            wind=rig.pawn.get_component_by_class(unreal.WindDirectionalSourceComponent)
            rig.check(wind is not None and abs(wind.get_editor_property('relative_location').z)<.001,'cape airflow stays horizontal')
            rig.data.setdefault('wind_samples',[]).append({'time':rig.now,'source_offset':xyz(wind.get_editor_property('relative_location')),
                'speed':wind.get_editor_property('speed'),'cloth':rig.latest['cloth']})
            if label=='moving-b':
                rig.check(abs(wind.get_editor_property('relative_location').x)<.3,
                          'running cape settles toward centered airflow without forced sideways oscillation')
            if fps==60: yield rig.capture('archer-cape-'+label)
        turn=rig.pawn.get_actor_location()+unreal.Vector(-400,0,0)
        yield from rig.click('Right',turn)
        yield .4
        if fps==60:
            rig.snapshot()
            yield rig.capture('archer-cape-turn')
        rig.controller.stop_movement()
        yield .9
        rig.snapshot()
        velocity=rig.pawn.get_velocity()
        rig.check(math.hypot(velocity.x,velocity.y)<1,'cape preview returns to a stopped character')
        if fps==60: yield rig.capture('archer-cape-stopped')
        rig.assert_recovered()

    def cape_stop_close(rig):
        yield from select(rig,'sparrow')
        yield from rig.click('Right',rig.ground(0,1100))
        yield .28
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Rear')
        yield .25
        rig.snapshot()
        if fps==60: yield rig.capture('cape-rear-running')
        yield .30
        rig.controller.stop_movement()
        stopped=rig.now
        for at in (.08,.22,.5,.9):
            yield max(1/fps,at-(rig.now-stopped))
            rig.snapshot()
            if fps==60: yield rig.capture('cape-rear-stop-'+str(at))
        rig.check(math.hypot(rig.pawn.get_velocity().x,rig.pawn.get_velocity().y)<1,'rear close-up reaches a real stop')
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
        yield 2/fps
        goal=rig.pawn.get_actor_location()+unreal.Vector(-400,0,0)
        yield from rig.click('Right',goal)
        yield .25
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Rear')
        yield .2
        if fps==60: yield rig.capture('cape-rear-turn-moving')
        rig.controller.stop_movement()
        yield .3
        rig.snapshot()
        if fps==60: yield rig.capture('cape-rear-turn-stopped')
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
        yield 2/fps
        rig.assert_recovered()
        previous=rig.pawn
        yield from rig.switch('countess')
        rig.check(not valid(previous),'cape collision owner is destroyed on numeric selection change')
        yield from rig.switch('sparrow')
        yield .4
        rig.snapshot()
        rig.check(not rig.latest['cloth_disabled'] and not rig.latest['cloth_suspended'],
                  'new cape simulation remains active after collision-source owner cleanup')
        rig.assert_recovered()

    def rapid_ready(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        rig.check(not rig.latest['slots'][2]['passive'],'E HUD advertises an active Rapid Shot')

    def observe_rapid(rig,seconds,seen,captures=False):
        start=rig.now
        capture_times=[.18,.54,.94] if captures and (fps==60 or os.environ.get('RAPID_CLOSE')=='1') else []
        while rig.now-start<seconds:
            for arrow in rig.arrows():
                name=arrow.get_name()
                if name not in seen:
                    seen[name]=rig.now
                    rig.check(not arrow.is_piercing() and not arrow.passes_world() and arrow.applies_relentless_bonus(),
                              'each E arrow is non-piercing, wall-blocked and retains passive damage')
            if capture_times and rig.now-start>=capture_times[0]:
                at=capture_times.pop(0)
                rig.snapshot()
                yield rig.capture('archer-E-rapid-'+str(at))
            else:
                yield 1/fps

    def rapid_release(rig):
        yield from rapid_ready(rig)
        target=rig.dummy(0,700)
        behind=rig.dummy(0,1000)
        rig.aim_target(target)
        start=rig.now
        yield from rig.skill_key('E',target.get_actor_location())
        if os.environ.get('RAPID_CLOSE')=='1':
            unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Close')
        seen={}
        yield from observe_rapid(rig,1.6,seen,True)
        if os.environ.get('RAPID_CLOSE')=='1':
            unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
            yield 2/fps
        times=sorted(t-start for t in seen.values())
        rig.check(len(times)==6,'actual E input releases exactly six separate arrows')
        rig.check(all(.16-2/fps-.001<=b-a<=.16+2/fps+.001 for a,b in zip(times,times[1:])),
                  'E maintains distinct rapid-fire intervals at the current FPS')
        rig.check(times[-1]-times[0]<=1.0,'six-shot release completes within the approved rapid-fire window')
        rig.check(abs(rig.health(target)-37.375)<.02 and rig.health(behind)==100,
                  'six hits keep passive increments while no arrow pierces the first target')
        rig.check(rig.component.get_relentless_stacks(target)==6,'six E collisions create six passive stacks')
        rig.data.update(release_seconds=times,target_health=rig.health(target),rear_health=rig.health(behind))
        rig.assert_recovered()
        rig.check(rig.pawn.try_basic_attack(target.get_actor_location()),'accepted basic attack remains usable after E')
        yield rig.until(lambda:rig.component.get_relentless_stacks(target)==7,1.5,'basic attack keeps the six existing E stacks')
        rig.check(abs(rig.health(target)-15.275)<.03,'retained passive applies to a normal basic attack after E')
        yield rig.idle(3)
        rig.assert_recovered()

    def archer_e_one_ring(rig):
        yield from rapid_ready(rig)
        target=statue(rig,0,700)
        yield from rig.skill_key('E',target.get_actor_location())
        seen=set();values=[]
        start=rig.now
        for frame in range(16):
            yield .07
            actors=unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowRapidRing')
            rig.check(len(actors)<=1,'E never stacks a second bow ring')
            if actors:
                actor=actors[0];seen.add(actor.get_name())
                meshes=actor.get_components_by_class(unreal.StaticMeshComponent)
                rig.check(len(meshes)==1,'E owns one ring surface')
                envelope=meshes[0].get_material(0).get_scalar_parameter_value('Envelope')
                values.append({'time':rig.now-start,'envelope':envelope})
                rig.check(unreal.MathLibrary.vector_distance(actor.get_actor_location(),rig.component.get_arrow_origin())<50,'single E ring follows the live bow origin')
                rig.check(abs(meshes[0].get_up_vector().dot(rig.pawn.get_actor_forward_vector()))>.999,'E ring faces forward from the bow')
            if fps==60 and frame in (2,4,6,8,10,12): yield rig.capture('archer-E-one-ring-'+str(frame))
        rig.check(len(seen)==1 and max(v['envelope'] for v in values)>.9,'six shots reuse one visibly pulsing ring')
        yield .5
        rig.check(not unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowRapidRing'),'E ring is removed when its skill ends')
        rig.check(abs(rig.health(target)-37.375)<.03,'E keeps its original six shots and total passive damage')
        rig.data['single_ring_envelopes']=values
        rig.assert_recovered()

    def rapid_cancel(rig,after_first=False):
        yield from rapid_ready(rig)
        target=rig.dummy(0,700)
        yield from rig.skill_key('E',target.get_actor_location())
        if after_first:
            yield rig.until(lambda:bool(rig.arrows()),.3,'first E arrow exists before interruption')
        else:
            yield .04
        rig.interrupt()
        yield 1.1
        rig.check(abs(rig.health(target)-(90 if after_first else 100))<.01,
                  'E interruption cancels every unreleased arrow')
        rig.check(not rig.arrows(),'released arrows finish without leaving a projectile behind')
        rig.check(not unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowRapidRing'),'cancelled E cleans its pulsing ring')
        rig.assert_recovered()

    def rapid_wall(rig):
        yield from rapid_ready(rig)
        target=rig.dummy(0,700)
        wall=rig.wall(0,300)
        wall.set_actor_scale3d(unreal.Vector(5,.4,3.5))
        yield from rig.skill_key('E',target.get_actor_location())
        seen={}
        yield from observe_rapid(rig,1.2,seen)
        rig.check(len(seen)==6 and rig.health(target)==100,'solid wall blocks all six E arrows')
        rig.assert_recovered()

    def rapid_move(rig,preheld=False):
        yield from rapid_ready(rig)
        target=rig.dummy(0,700)
        goal=rig.ground(350,0)
        if preheld:
            rig.mouse('Press','Right',goal)
            yield 1/fps
        yield from rig.skill_key('E',target.get_actor_location())
        if preheld:
            seen={}
            yield from observe_rapid(rig,1.3,seen)
            rig.mouse('Release','Right',goal)
            yield .4
            rig.check(len(seen)==6 and abs(rig.health(target)-37.375)<.02,
                      'movement held before E does not immediately cancel the approved burst')
        else:
            yield rig.until(lambda:bool(rig.arrows()),.3,'first E arrow exists before new move input')
            rig.mouse('Press','Right',goal)
            yield .16
            rig.mouse('Release','Right',goal)
            yield 1
            rig.check(abs(rig.health(target)-90)<.01,'new right-click cancels remaining E shots and preserves the released arrow')
        rig.assert_recovered()

    def rapid_owner(rig):
        yield from rapid_ready(rig)
        target=rig.dummy(0,1100)
        yield from rig.skill_key('E',target.get_actor_location())
        yield rig.until(lambda:bool(rig.arrows()),.3,'E owner has an in-flight arrow before switching')
        previous=rig.pawn
        arrows=list(rig.arrows())
        yield from rig.switch('countess')
        yield .9
        rig.check(not valid(previous) and all(not valid(a) for a in arrows) and not rig.arrows(),
                  'owner selection clears E timers and the old owners arrows')
        rig.check(rig.health(target)==100,'owner switch before impact prevents later E damage')
        rig.assert_recovered()

    def rapid_with_R(rig):
        yield from rapid_ready(rig)
        target=rig.dummy(0,700)
        yield from rig.skill_key('R',target.get_actor_location())
        yield rig.idle(2)
        rig.check(rig.component.is_inner_fire_active(),'R buff is active before E integration check')
        yield from rig.skill_key('E',target.get_actor_location())
        seen={}
        yield from observe_rapid(rig,1.2,seen)
        rig.check(len(seen)==6 and abs(rig.health(target)-37.375)<.02,
                  'E remains six ordinary arrows during R instead of invoking the three-arrow basic attack')
        rig.check(rig.component.is_inner_fire_active(),'E preserves the independent R buff')
        rig.assert_recovered()

    def assassin_e_candidate(rig,index):
        yield from select(rig,'countess')
        target=statue(rig,0,115 if index==4 else 145)
        rig.aim_target(target)
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Preview')
        yield .2
        start=rig.now
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.CountessEPreview '+str(index)+' '+target.get_name())
        rig.data.update(preview_index=index,preview_started=start,preview_only=True,damage_implemented=False)
        for frame in range(22):
            at=frame/12
            yield max(1/fps,at-(rig.now-start))
            rig.snapshot()
            yield rig.capture('assassin-E-candidate-'+str(index)+'-frame-'+str(frame).zfill(2))
        yield max(1/fps,2.4-(rig.now-start))
        rig.check(rig.health(target)==100,'rough E concept preview applies no gameplay damage')
        definition=rig.component.get_editor_property('skills')[2]
        rig.check(str(definition.get_editor_property('name'))=='DarkTide','preview keeps the installed original E definition')
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
        yield .25
        rig.assert_recovered()

    def archer_q_fade(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        target=statue(rig,0,650)
        yield from rig.skill_key('Q',target.get_actor_location())
        yield rig.until(lambda:bool(unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator')),1,'Q range indicator appears')
        marker=unreal.GameplayStatics.get_all_actors_with_tag(rig.world,'SparrowHailRangeIndicator')[0]
        mesh=marker.get_component_by_class(unreal.StaticMeshComponent)
        material=mesh.get_material(0)
        original_scale=xyz(mesh.get_world_scale())
        born=rig.now
        values=[]
        for at in (.2,3.5,3.65,3.8,3.92):
            yield max(1/fps,at-(rig.now-born))
            value=material.get_scalar_parameter_value('Envelope')
            values.append({'elapsed':rig.now-born,'envelope':value})
            rig.check(xyz(mesh.get_world_scale())==original_scale,'Q range fade keeps the exact gameplay circle size')
            if fps==60 and at>=3.5: yield rig.capture('archer-Q-fade-'+str(at))
        rig.check(abs(values[0]['envelope']-.55)<.001 and abs(values[1]['envelope']-.55)<.01,'Q range circle stays at full visibility until its final phase')
        rig.check(all(a['envelope']>b['envelope'] for a,b in zip(values[1:],values[2:])) and values[-1]['envelope']<.08,'Q range circle fades continuously over its last 0.4 seconds')
        yield .3
        rig.check(not valid(marker) and abs(rig.health(target)-60)<.01,'Q expiry removes the faded circle and keeps total damage 40')
        rig.data['fade_values']=values
        rig.assert_recovered()

    def attack_target(rig,x,y):
        target=statue(rig,x,y)
        return target

    def held_bow_pose(rig,inner_fire=False):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        rig.check('HeldAim' in rig.anim.get_class().get_name(),'new owned held-aim graph is installed')
        target=attack_target(rig,0,550)
        rig.aim_target(target)
        if inner_fire:
            yield from rig.skill_key('R',target.get_actor_location())
            yield rig.idle(2)
            rig.check(rig.component.is_inner_fire_active(),'R is active before held-pose sampling')
        start=rig.now
        rig.mouse('Press','Left',target.get_actor_location())
        rows=[]
        for frame in range(38):
            yield .1
            if rig.health(target)<=40: target.reset_dummy()
            bow=rig.mesh.get_socket_transform('bow_base',unreal.RelativeTransformSpace.RTS_COMPONENT)
            montage=rig.anim.get_current_active_montage()
            row={'elapsed':rig.now-start,'bow':xyz(bow.translation),
                 'montage':montage.get_name() if montage else None,
                 'position':rig.anim.montage_get_position(montage) if montage else None,
                 'sequence':rig.latest.get('montage_sequence'),
                 'slot':rig.latest.get('montage_slot'),
                 'hold_ready':rig.anim.get_editor_property('HoldBowReady'),
                 'hold_R':rig.anim.get_editor_property('HoldInnerFireReady'),
                 'R_active':rig.component.is_inner_fire_active()}
            rows.append(row)
            if fps==60 and frame in (10,12,14,16,18,20,22,24,26):
                yield rig.capture(('archer-R-held-' if inner_fire else 'archer-primary-held-')+str(frame))
        rig.mouse('Release','Left',target.get_actor_location())
        rig.data['bow_samples']=rows
        rig.check(any((r['sequence']=='R_Ability_Fast_Fire' and r['slot']=='SparrowUpperBody') if inner_fire else (r['montage']=='HeldPrimary') for r in rows),'later held attacks use the raised-bow montage')
        steady=[r for r in rows if r['elapsed']>1.2 and (not inner_fire or r['R_active'])]
        rig.check(steady and all(r['bow'][2]>125 for r in steady),'held inter-shot bow stays above the lowered idle pose')
        rig.check(all(r['hold_ready'] for r in rows),'held ready pose remains active between attacks')
        if inner_fire: rig.check(any(r['hold_R'] for r in rows),'R selects its tilted ready pose')
        yield rig.idle(3)
        yield .5
        rig.check(not rig.anim.get_editor_property('HoldBowReady'),'release clears the held aim overlay')
        rig.data['bow_samples']=rows
        rig.assert_recovered()

    def archer_single_click(rig):
        yield from select(rig,'sparrow')
        target=attack_target(rig,0,550)
        rig.aim_target(target)
        yield from rig.click('Left',target.get_actor_location())
        yield .08
        montage=rig.anim.get_current_active_montage()
        rig.check(montage and montage.get_name()=='AM_Sparrow_PrimaryNatural','a standalone click retains the approved natural attack animation')
        yield rig.idle(3)
        yield .5
        rig.check(abs(rig.health(target)-80)<.01,'one standalone click still releases exactly one 20-damage arrow')
        rig.check(not rig.anim.get_editor_property('HoldBowReady'),'standalone click returns to normal movement pose')
        rig.assert_recovered()

    def held_attack(rig,hero):
        yield from select(rig,hero)
        target=attack_target(rig,0,145 if hero=='countess' else 550)
        rig.aim_target(target)
        start=rig.now
        rig.mouse('Press','Left',target.get_actor_location())
        steps=[]
        total_damage=0.0
        previous_health=100.0
        for _ in range(40):
            yield .1
            steps.append(rig.pawn.get_combo_attack_number())
            current=rig.health(target)
            total_damage+=max(0,previous_health-current)
            if current<=40:
                target.reset_dummy()
                previous_health=100.0
            else:
                previous_health=current
        held_for=rig.now-start
        rig.mouse('Release','Left',target.get_actor_location())
        rig.check(total_damage>=80,'held left click repeatedly attacks without additional presses')
        if hero=='countess':
            rig.check(all(i in steps for i in (1,2,3)),'held Countess follows the existing three-step combo')
            rig.check(sum(v==1 and (i==0 or steps[i-1]!=1) for i,v in enumerate(steps))>=2,'held Countess restarts after its last-step cooldown')
        yield rig.idle(3)
        yield .5
        settled=rig.health(target)
        yield .9
        rig.check(rig.health(target)==settled and not rig.pawn.is_attacking(),'release stops later attacks after the current strike finishes')
        rig.data.update(health_after_hold=settled,combo_steps=steps,hold_seconds=held_for,total_damage_during_hold=total_damage)
        rig.assert_recovered()

    def manual_combo_preserved(rig):
        yield from select(rig,'countess')
        target=attack_target(rig,0,145)
        rig.aim_target(target)
        yield from rig.click('Left',target.get_actor_location())
        yield rig.idle(3)
        yield .4
        rig.check(abs(rig.health(target)-80)<.01,'one short manual click still produces exactly one hit')
        yield from rig.click('Left',target.get_actor_location())
        yield 1/fps
        yield from rig.click('Left',target.get_actor_location())
        yield rig.idle(4)
        yield .5
        rig.check(abs(rig.health(target)-40)<.01,'two quick manual clicks still preserve their queued two-hit combo after release')
        rig.assert_recovered()

    def held_aim(rig):
        yield from select(rig,'sparrow')
        first=attack_target(rig,0,550)
        second=attack_target(rig,260,550)
        rig.aim_target(first)
        rig.mouse('Press','Left',first.get_actor_location())
        yield 1.3
        rig.mouse('Move','Left',second.get_actor_location())
        yield 1.8
        rig.mouse('Release','Left',second.get_actor_location())
        yield rig.idle(3)
        yield .5
        rig.check(rig.health(first)<100 and rig.health(second)<100,'held archer attacks update their aim to the current cursor target')
        rig.assert_recovered()

    def held_skill(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        target=attack_target(rig,0,550)
        rig.aim_target(target)
        rig.mouse('Press','Left',target.get_actor_location())
        yield .08
        yield from rig.skill_key('E',target.get_actor_location())
        yield .2
        rig.check(rig.component.is_casting() and not rig.pawn.is_attacking(),'skill cast interrupts held basic attacks without overlapping their animation')
        yield rig.until(lambda:not rig.component.is_casting(),2,'held E completes')
        yield rig.until(lambda:rig.pawn.is_attacking(),1,'basic attack resumes only while the left button remains held')
        rig.mouse('Release','Left',target.get_actor_location())
        yield rig.idle(3)
        yield .5
        rig.assert_recovered()

    def held_skill_release(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        target=attack_target(rig,0,550)
        rig.aim_target(target)
        yield from rig.skill_key('E',target.get_actor_location())
        rig.check(rig.component.is_casting(),'E actually starts before testing a press and release during its cast')
        yield .15
        rig.mouse('Press','Left',target.get_actor_location())
        yield .1
        rig.mouse('Release','Left',target.get_actor_location())
        yield rig.idle(3)
        yield 1
        rig.check(abs(rig.health(target)-(100-62.625))<.03 and not rig.pawn.is_attacking(),'left press and release during E does not schedule a basic attack after the skill')
        rig.assert_recovered()

    def held_boundary(rig,kind):
        yield from select(rig,'countess')
        target=attack_target(rig,0,145)
        rig.aim_target(target)
        rig.mouse('Press','Left',target.get_actor_location())
        yield .08
        if kind=='switch':
            yield from rig.switch('sparrow')
            yield .7
            rig.check(not rig.pawn.is_attacking() and not rig.arrows(),'character switch does not inherit the prior held attack')
        elif kind=='focus':
            unreal.SystemLibrary.execute_console_command(rig.world,'CountessComboQA.FlushInput')
            yield rig.idle(3)
            settled=rig.health(target)
            yield 1
            rig.check(not rig.pawn.is_attacking() and rig.health(target)==settled,'focus-loss key flush clears held attack and prevents a stuck repeat')
        else:
            goal=rig.ground(400,0)
            begin=rig.now
            rig.mouse('Press','Right',goal)
            yield 1.4
            rig.mouse('Release','Right',goal)
            rig.check(any(row['time']>=begin and row['speed']>100 for row in rig.trace),'new right-click movement takes priority over the prior held attack')
            yield .7
            rig.check(not rig.pawn.is_attacking(),'left key still down does not revive an attack cancelled by movement')
        rig.mouse('Release','Left',target.get_actor_location())
        yield rig.idle(3)
        rig.assert_recovered()

    def archer_w_horizontal(rig):
        yield from select(rig,'sparrow')
        unreal.SystemLibrary.execute_console_command(rig.world,'Sparrow.Skills.IgnoreCooldowns 1')
        for index,offset in enumerate((unreal.Vector(0,550,350),unreal.Vector(0,180,-70))):
            aim=rig.pawn.get_actor_location()+offset
            rig.check(rig.component.try_use_skill(unreal.SparrowSkill.PIERCING_SHOT,aim,None),'W accepts a distinct vertical aiming point')
            yield rig.until(lambda:bool(unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave)),1,'W visible ring exists at release')
            wave=unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.SparrowShotWave)[0]
            rotation=wave.get_actor_rotation()
            arrows=rig.arrows()
            rig.check(arrows and abs(arrows[0].get_flight_direction().z)>.1,'the real W arrow retains its upward or downward aiming pitch')
            rig.check(abs(rotation.pitch)<.001 and abs(rotation.roll)<.001 and abs((rotation.yaw-rig.pawn.get_actor_rotation().yaw+180)%360-180)<.001,'W ring remains aligned with the character horizontal forward direction')
            rig.data.setdefault('directions',[]).append({'wave_rotation':str(rotation),'arrow_direction':xyz(arrows[0].get_flight_direction())})
            if fps==60:
                yield .07
                yield rig.capture('archer-W-horizontal-'+str(index))
            yield rig.idle(4)
            yield .5
        rig.assert_recovered()

    class PresentationRunner(TrainingRunner):
        def __init__(self):
            super().__init__()
            self.cases=[('archer_single_click',archer_single_click),('archer_held_pose',held_bow_pose),('archer_R_held_pose',lambda rig:held_bow_pose(rig,True)),('assassin_E_candidate_4',lambda rig:assassin_e_candidate(rig,4)),('archer_Q_fade',archer_q_fade),('assassin_held_primary',lambda rig:held_attack(rig,'countess')),
                        ('archer_held_primary',lambda rig:held_attack(rig,'sparrow')),
                        ('manual_combo_preserved',manual_combo_preserved),('archer_held_aim',held_aim),
                        ('held_skill',held_skill),('held_skill_release',held_skill_release),('held_switch',lambda rig:held_boundary(rig,'switch')),
                        ('held_focus',lambda rig:held_boundary(rig,'focus')),('held_move',lambda rig:held_boundary(rig,'move')),
                        ('archer_W_horizontal',archer_w_horizontal),('assassin_E_candidate_1',lambda rig:assassin_e_candidate(rig,1)),
                        ('assassin_E_candidate_2',lambda rig:assassin_e_candidate(rig,2)),
                        ('assassin_E_candidate_3',lambda rig:assassin_e_candidate(rig,3)),
                        ('assassin_R_original',assassin_r_original),('archer_R_fan',archer_r_fan),
                        ('archer_E_FX_1',lambda rig:archer_e_fx_preview(rig,1)),
                        ('archer_E_FX_2',lambda rig:archer_e_fx_preview(rig,2)),
                        ('archer_E_FX_3',lambda rig:archer_e_fx_preview(rig,3)),
                        ('assassin_R_cancel_prepare',lambda rig:assassin_r_cancel(rig,.1)),
                        ('assassin_R_cancel_approach',lambda rig:assassin_r_cancel(rig,1.1)),
                        ('assassin_R_blocked',assassin_r_blocked),('archer_Q_dense',archer_q_dense),('archer_Q_owner',archer_q_owner),
                        ('assassin_Q_short_body',assassin_q),('assassin_W_light_fast',assassin_w),
                        ('assassin_W_preview_before',lambda rig:assassin_w_preview(rig,0)),
                        ('assassin_W_preview_after',lambda rig:assassin_w_preview(rig,1)),
                        ('assassin_E_rollback',assassin_e_rollback),('assassin_E_cancel',assassin_e_cancel),
                        ('archer_cape_stop_close',cape_stop_close),
                        ('archer_E_one_ring',archer_e_one_ring),('archer_E_release',rapid_release),
                        ('archer_E_cancel_before',lambda rig:rapid_cancel(rig,False)),
                        ('archer_E_cancel_after',lambda rig:rapid_cancel(rig,True)),
                        ('archer_E_wall',rapid_wall),('archer_E_move',lambda rig:rapid_move(rig,False)),
                        ('archer_E_preheld',lambda rig:rapid_move(rig,True)),
                        ('archer_E_owner',rapid_owner),('archer_E_R',rapid_with_R),
                        ('archer_W_reverse',archer_w),('archer_cape_move',moving_cape),
                        ('archer_W_cancel',archer_w_cancel),('archer_W_owner',archer_w_owner)]
            requested=os.environ.get('PRESENTATION_CASES')
            if requested: self.cases=[case for case in self.cases if case[0] in requested.split(',')]
            elif fps!=60: self.cases=[('archer_W_reverse',archer_w)]
            self.report_name='presentation-polish.json'
            self.report.update(suite='scoped_presentation_refinement',verification_scope='requested cases only; input and animation state, cancellation, and related presentation')
        def case_generator(self,factory):
            self.rig.switch=types.MethodType(settle_switch,self.rig)
            yield from TrainingRunner.case_generator(self,factory)
    runtime=PresentationRunner()
    runtime.start()
