"""Training-room six-cut E prototype: reuse the existing room runner and controller input."""
import json,os,sys,types,math
from pathlib import Path
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
job={'output':str(OUT),'profile':str(ROOT/'Tools/CharacterPipeline/Profiles/countess.json'),'fps':int(os.environ.get('SPARROW_QA_FPS','60')),'baseline':str(OUT.parent/'target-baseline.json')}
(OUT/'job.json').write_text(json.dumps(job),encoding='utf-8');os.environ['CHARACTER_PIPELINE_JOB']=str(OUT/'job.json')
if os.environ.get('COUNTESS_FLURRY_AUTHOR_DISSOLVE')=='1':
    from countess_e_shadow_material import author
    try:author(OUT)
    except Exception:
        import traceback
        (OUT/'material-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        unreal.SystemLibrary.quit_editor()
        raise
from context import fps
if os.environ.get('COUNTESS_FLURRY_AUTHOR_CUTS')=='1':
    unreal.SystemLibrary.execute_console_command(None,'r.Streaming.PoolSize 512')
    unreal.SystemLibrary.execute_console_command(None,'r.Shadow.Virtual.MaxPhysicalPages 1024')
if os.environ.get('COUNTESS_FLURRY_AUTHOR_CUTS')=='1':
    from countess_e_shadow_material import author_target_cuts
    try:author_target_cuts(OUT)
    except Exception:
        import traceback
        (OUT/'cut-material-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        unreal.SystemLibrary.quit_editor()
        raise
if os.environ.get('COUNTESS_FLURRY_AUTHOR_TRAIL')=='1':
    from countess_e_shadow_material import author_blade_trail,author_sharp_trail
    try:
        author_blade_trail(OUT)
        author_sharp_trail(OUT)
    except Exception:
        import traceback
        (OUT/'trail-material-error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        unreal.SystemLibrary.quit_editor()
        raise
from training_room_verify import TrainingRunner,select
from countess_w_speed_compare import settle_switch,statue
from sparrow_runtime import valid,xyz


def ready(rig):
    yield from select(rig,'countess')
    unreal.SystemLibrary.execute_console_command(rig.world,'Countess.Skills.IgnoreCooldowns 1')
    rig.check(rig.component.is_flurry_prototype_enabled(),'training-room E prototype is available on the real character')
    definition=rig.component.get_editor_property('skills')[2]
    rig.check(abs(definition.get_editor_property('damage')-45)<.001 and abs(definition.get_editor_property('range')-210)<.001,'prototype is melee and preserves total base damage 45')


def shadows(rig):
    return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.Actor)
            if a.actor_has_tag('CountessEFlurryShadow')]


def six_hits(rig,close=True):
    yield from ready(rig)
    target=statue(rig,0,145);outside=statue(rig,180,145)
    if os.environ.get('COUNTESS_FLURRY_AUTHOR_CUTS')=='1' and close:target.set_actor_rotation(unreal.Rotator(yaw=65),True)
    if fps==60 and close: unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Preview')
    yield .15
    rig.aim_target(target)
    start=rig.now;origin=xyz(rig.pawn.get_actor_location())
    yield from rig.skill_key('E',target.get_actor_location())
    clips=set();shadow_clips=set();poses=[];shadow_samples=[];fade_samples=[]
    capture_at=0;fx_proof=None;placement=None
    capture_30=[.35,.60,.85] if fps==30 and os.environ.get('COUNTESS_FLURRY_CAPTURE_30')=='1' else []
    while rig.now-start<2.0:
        state=rig.snapshot()
        retiring=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.Actor)
                  if a.actor_has_tag('CountessEShadowDissolving')]
        for actor in retiring:
            material=actor.get_component_by_class(unreal.SkeletalMeshComponent).get_material(0)
            fade_samples.append({'elapsed':rig.now-start,'start':material.get_scalar_parameter_value('DissolveStart'),
                                 'duration':material.get_scalar_parameter_value('DissolveDuration')})
        if state['casting']:
            clips.add(state['montage'])
            rig.check(not rig.pawn.is_attacking(),'E runs independently from the basic-attack combo')
            actors=shadows(rig)
            rig.check(len(actors)==1,'exactly one attacking shadow accompanies the real caster')
            mesh=actors[0].get_component_by_class(unreal.SkeletalMeshComponent)
            anim=mesh.get_anim_instance();montage=anim.get_current_active_montage()
            if montage:shadow_clips.add(montage.get_name())
            shadow_samples.append({'elapsed':rig.now-start,'montage':montage.get_name() if montage else None,
                                   'position':anim.montage_get_position(montage) if montage else None,
                                   'hand_l':xyz(mesh.get_socket_location('hand_l')),
                                   'hand_r':xyz(mesh.get_socket_location('hand_r'))})
            rig.check(not actors[0].get_actor_enable_collision(),'the visual shadow cannot block movement or receive collision hits')
            body=xyz(rig.pawn.get_actor_location());enemy=xyz(target.get_actor_location());shadow=xyz(mesh.get_world_location())
            toward=[enemy[i]-body[i] for i in (0,1)];behind=[shadow[i]-enemy[i] for i in (0,1)]
            alignment=sum(a*b for a,b in zip(toward,behind))/(math.hypot(*toward)*math.hypot(*behind))
            rig.check(alignment>.95,'the shadow stands beyond the target opposite the real caster')
            yaw=math.radians(mesh.get_world_rotation().yaw-rig.mesh.get_editor_property('relative_rotation').yaw)
            facing=[math.cos(yaw),math.sin(yaw)]
            rig.check(sum(a*b for a,b in zip(facing,behind))/math.hypot(*behind)<-.95,'the shadow faces back toward the target and real caster')
            placement={'body':body,'target':enemy,'shadow':shadow,'alignment':alignment,'shadow_facing_xy':facing}
            if fx_proof is None and rig.health(target)<=77.5:
                fx_proof=rig.native('CountessFXQA.State','e-pincer-fx-proof')
                if os.environ.get('COUNTESS_FLURRY_AUTHOR_CUTS')=='1':
                    rig.check(not any(e['template'] in ['p_CountessMeleeTrail','P_CountessESharpTrail','p_Countess_XSlash'] for e in fx_proof['effects']),'E no longer spawns weapon trails or the old curved cross effect')
                    cuts=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig.world,unreal.Actor) if a.actor_has_tag('CountessETargetCuts')]
                    rig.check(bool(cuts),'actual straight cut actors appear at the damaged target')
                    proof=[]
                    for a in cuts:
                        meshes=a.get_components_by_class(unreal.StaticMeshComponent)
                        rig.check(len(meshes)==2 and a.get_attach_parent_actor()==target,'each damage event produces two target-attached straight cuts')
                        center=target.get_actor_location()+unreal.Vector(0,0,10)
                        toward=rig.controller.player_camera_manager.get_camera_location()-center
                        normal=a.get_actor_up_vector()
                        dot=(toward.x*normal.x+toward.y*normal.y+toward.z*normal.z)/math.sqrt(toward.x*toward.x+toward.y*toward.y+toward.z*toward.z)
                        rig.check(dot>.999,'straight cuts remain readable when their target rotates')
                        for m in meshes:rig.check('M_CountessETargetCut' in m.get_material(0).get_path_name(),'straight cuts use their real red/white material')
                        proof.append({'actor':a.get_name(),'target':target.get_name(),'meshes':len(meshes),'position':xyz(a.get_actor_location())})
                    fx_proof['straight_cut_actors']=proof
                if os.environ.get('COUNTESS_FLURRY_AUTHOR_TRAIL')=='1':
                    actual=[]
                    for p in unreal.ObjectIterator(unreal.ParticleSystemComponent):
                        if not valid(p) or not p.component_has_tag('CountessFlurryWideTrail'):continue
                        outer=p.get_outer()
                        while outer is not None and outer!=rig.world:outer=outer.get_outer()
                        if outer==rig.world:actual.append(p.get_material(0).get_path_name())
                    rig.check(len(actual)==4 and all('M_CountessESharpBladeTrail' in p for p in actual),'all four real weapon trails use the E-only Q-palette material')
                    fx_proof['actual_E_trail_materials']=actual
        if fps==60 and rig.now-start>=capture_at and capture_at<1.85:
            poses.append({'elapsed':rig.now-start,'montage':state['montage'],'source_position':state['montage_position'],'health':rig.health(target)})
            yield rig.capture('assassin-E-sixcut-frame-'+str(len(poses)-1).zfill(2))
            capture_at+=.05
        elif capture_30 and rig.now-start>=capture_30[0]:
            capture_30.pop(0)
            poses.append({'elapsed':rig.now-start,'health':rig.health(target)})
            yield rig.capture('assassin-E-sharp-30-frame-'+str(len(poses)-1).zfill(2))
        else: yield 1/fps
    events=[e for e in rig.events if e['after'] and e['before'] and e['after'][0]<e['before'][0]]
    hits=[{'elapsed':e['time']-(start-rig.runner.case_started),'damage':e['before'][0]-e['after'][0],'health':e['after'][0]} for e in events]
    rig.check(len(hits)==6 and all(abs(h['damage']-7.5)<.001 for h in hits),'six distinct real hits each deal 7.5 damage')
    rig.check(len(clips)==3 and len(shadow_clips)==3,'the body and shadow each play three real cutting montage instances')
    rig.check(any(math.dist(a['hand_r'],b['hand_r'])>10 for a,b in zip(shadow_samples,shadow_samples[1:])),'the shadow skeleton visibly animates instead of remaining a frozen Q decoy')
    rig.check(rig.health(target)==55 and rig.health(outside)==100,'all damage stays on the selected melee target')
    expected=[.14+i*(.22/1.5) for i in range(6)]
    rig.check(all(abs(h['elapsed']-t)<3/fps for h,t in zip(hits,expected)),'each hit is synchronized to its actual cutting clip')
    rig.check(math.dist(origin,xyz(rig.pawn.get_actor_location()))<3,'the flurry does not teleport or drift through its target')
    rig.check(not shadows(rig),'natural recovery removes the attacking shadow')
    rig.check(bool(fade_samples) and all(abs(x['duration']-.45)<.001 for x in fade_samples),'the completed shadow survives briefly as a timed visual-only dissolve')
    rig.check(not retiring,'the dissolving shadow naturally expires without leaving an actor behind')
    rig.data.update(hits=hits,montages=list(clips),shadow_montages=list(shadow_clips),shadow_samples=shadow_samples,frames=poses,placement=placement,fx_proof=fx_proof,fade_samples=fade_samples,camera='motion_closeup' if close else 'approved_gameplay_quarter_view')
    if fps==60 and close: unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
    rig.assert_recovered()


def boundary(rig,mode):
    yield from ready(rig)
    target=statue(rig,0,145)
    rig.aim_target(target)
    yield from rig.skill_key('E',target.get_actor_location())
    if mode=='before':
        yield .04;rig.interrupt();expected=100
    else:
        yield rig.until(lambda:rig.health(target)==92.5,.3,'first real cut lands before boundary check')
        expected=92.5
        if mode=='cancel':rig.interrupt()
        elif mode=='owner':yield from rig.switch('sparrow',camera_settled=False)
        elif mode=='range':target.set_actor_location(rig.ground(0,600),False,False)
        elif mode=='destroy':target.destroy_actor()
        elif mode=='shadow':shadows(rig)[0].destroy_actor()
    yield 1.6
    if mode!='destroy':rig.check(abs(rig.health(target)-expected)<.001,'boundary stops every remaining scheduled E hit')
    rig.check(not shadows(rig),'cancellation or loss of the target leaves no attacking shadow behind')
    rig.assert_recovered()


def rejected(rig):
    yield from ready(rig)
    target=statue(rig,0,400)
    rig.check(not rig.component.try_use_skill(unreal.CountessSkill.DARK_TIDE,target.get_actor_location(),target),'E rejects a target outside melee range')
    rig.check(not rig.component.try_use_skill(unreal.CountessSkill.DARK_TIDE,rig.pawn.get_actor_location(),None),'E requires an explicit enemy target')
    rig.assert_recovered()


def shadow_blocked(rig):
    yield from ready(rig)
    target=statue(rig,0,145)
    wall=rig.wall(0,270,dynamic=True)
    wall.set_actor_scale3d(unreal.Vector(5,.4,3.5))
    yield .1
    rig.check(not rig.component.try_use_skill(unreal.CountessSkill.DARK_TIDE,target.get_actor_location(),target),'E rejects an obstructed opposite shadow landing instead of appearing through a wall')
    yield .35
    rig.check(rig.health(target)==100 and not shadows(rig),'blocked shadow placement creates no damage or leftover shadow')
    rig.assert_recovered()


class FlurryRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases=[('E_six_real_cuts',six_hits),('E_six_real_cuts_gameplay',lambda rig:six_hits(rig,False)),('E_cancel_before',lambda rig:boundary(rig,'before')),('E_cancel_after_first',lambda rig:boundary(rig,'cancel')),('E_target_leaves',lambda rig:boundary(rig,'range')),('E_target_destroyed',lambda rig:boundary(rig,'destroy')),('E_shadow_destroyed',lambda rig:boundary(rig,'shadow')),('E_owner_switch',lambda rig:boundary(rig,'owner')),('E_melee_rejection',rejected),('E_shadow_blocked',shadow_blocked)]
        requested=os.environ.get('COUNTESS_FLURRY_CASES')
        if requested:self.cases=[c for c in self.cases if c[0] in requested.split(',')]
        elif fps!=60:self.cases=self.cases[:1]
        self.report_name='e-sixcut-prototype.json'
        self.report.update(suite='countess_E_body_shadow_duet',verification_scope='body 3 + shadow 3 real cuts, six actual hits, melee target and related cancellation only')
    def case_generator(self,factory):
        self.rig.switch=types.MethodType(settle_switch,self.rig)
        yield from TrainingRunner.case_generator(self,factory)
runtime=FlurryRunner();runtime.start()
