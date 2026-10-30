"""Full original-field cloth and skill timelines at the actual controller bindings."""
from pathlib import Path
import sys
import unreal
sys.path[:0]=[str(Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline'),str(Path(__file__).resolve().parent)]
from context import fps, profile, root, job
from presentation_contract import sha256
from sparrow_runtime import Runner, valid
from character_switch import SwitchRunner, ORIGINAL_MAP, field_meshes
from sparrow_pose import close_capture
from visual_quality import check_quality

HERO=profile['character_id']

def capture_samples(rig):
    # Preserve every simulated frame; the generic runner's smaller trace is for summaries only.
    rows=[]
    for s in rig.trace:
        rows.append({k:s[k] for k in ('time','cloth','cloth_suspended','cloth_disabled','cloth_lod','cloth_lod_has_data','effects','casting','active_skill')})
    rig.data['quality_samples']=rows

def select(rig):
    if HERO=='sparrow':
        yield from rig.switch(HERO,camera_settled=False)
    rig.hero(HERO)
    yield .8
    yield from close_capture(rig,HERO+'-idle')

def locomotion(rig):
    # Actual path input: initial acceleration, sharp corner, reversal, stop and settling.
    origin=rig.pawn.get_actor_location()
    for index,(x,y) in enumerate(((0,650),(-400,100),(350,100),(0,-300))):
        goal=rig.ground_absolute(origin.x+x,origin.y+y)
        yield from rig.click('Right',goal)
        if index==0:
            rig.assert_cursor_goal(goal)
        yield .42
        if index in (0,2):
            yield from close_capture(rig,HERO+'-sharp-turn-'+str(index))
    rig.controller.stop_movement()
    rig.movement.stop_movement_immediately()
    yield 1.6
    yield from close_capture(rig,HERO+'-movement-recovery')
    capture_samples(rig)

def primary(rig):
    target=rig.dummy(0,450 if HERO=='sparrow' else 140)
    rig.aim_target(target)
    yield from rig.click('Left',target.get_actor_location())
    yield .05
    yield from close_capture(rig,HERO+'-primary-sharp-turn')
    yield rig.idle()
    yield 1.0
    yield from close_capture(rig,HERO+'-primary-recovery')
    capture_samples(rig)

def skill(key):
 def run(rig):
    unreal.SystemLibrary.execute_console_command(rig.world,('Sparrow' if HERO=='sparrow' else 'Countess')+'.Skills.IgnoreCooldowns 1')
    ranges={'Q':400,'W':140,'E':200,'R':-180} if HERO=='countess' else {'Q':600,'W':600,'E':600,'R':600}
    target=rig.dummy(0,ranges[key])
    rig.aim_target(target)
    initial_health=rig.health(target)
    rapid=HERO=='countess' and key=='R'
    if rapid:
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Close')
        yield 3./fps
    started=rig.now
    yield from rig.skill_key(key,target.get_actor_location())
    total=profile['presentation_contract']['quality_gate']['minimum_seconds']['skill_'+key]+.2
    definition=rig.component.get_editor_property('skills')[('Q','W','E','R').index(key)]
    action=float(definition.get_editor_property('action_time'))
    recovery=float(definition.get_editor_property('recovery_time'))
    if HERO=='countess':
        play_rate=float(rig.component.get_skill_play_rate(getattr(unreal.CountessSkill,('SHADOW_SLIP','BLADE_SIPHON','DARK_TIDE','FEAST')[('Q','W','E','R').index(key)])))
        start_time=float(rig.component.get_skill_start_time(getattr(unreal.CountessSkill,('SHADOW_SLIP','BLADE_SIPHON','DARK_TIDE','FEAST')[('Q','W','E','R').index(key)])))
        action,recovery=(action-start_time)/play_rate,(recovery-start_time)/play_rate
    phases=(('anticipation',max(1./fps,min(.1,action*.35))),('action',action+.12),
            ('recovery',max(action+.45,recovery+.08)),('residual',total))
    if rapid:
        phases=(('anticipation',1./fps),('preparation',.13),('approach',.3),('arrival',.44),('action',.56),('recovery',.9),('residual',total))
    rig.data['captured_phases']=[]
    for phase,seconds in phases:
        yield max(0.,seconds-(rig.now-started))
        if phase=='residual':
            # Include the real timer-driven expiry, including late impact and clone-burst particles.
            while True:
                sample=rig.snapshot()
                pending=sample['casting'] or any(effect['active'] and effect['particles']>0 for effect in sample['effects'])
                if not pending:
                    break
                rig.check(rig.now-started < 12.,'skill and all residual particles expire within 12 seconds')
                yield 1./fps
        # R is a buff for the archer: include a real empowered shot within the timeline.
        if HERO=='sparrow' and key=='R' and phase=='recovery':
            rig.aim_target(target)
            yield from rig.click('Left',target.get_actor_location())
            yield .12
        if rapid:
            yield rig.capture(HERO+'-'+key+'-'+phase)
        else:
            yield from close_capture(rig,HERO+'-'+key+'-'+phase)
        if phase in ('anticipation','action','recovery','residual'):
            rig.data['captured_phases'].append(phase)
    if rapid:
        unreal.SystemLibrary.execute_console_command(rig.world,'CharacterVisualQA.Camera Restore')
    rig.data['target_health_before_after']=[initial_health,rig.health(target)]
    capture_samples(rig)
 return run

class QualityRunner(SwitchRunner):
 def __init__(self):
    Runner.__init__(self,'character_visual_quality',[('selection',select),('locomotion',locomotion),('primary',primary)]+[('skill_'+key,skill(key)) for key in ('Q','W','E','R')])
    sources=list((root/'Source/LearnTopDown').rglob('*.cpp'))+list((root/'Source/LearnTopDown').rglob('*.h'))+list((root/'Source/LearnTopDown').glob('*.cs'))
    self.report.update(character_id=HERO,map=ORIGINAL_MAP,profile_sha256=sha256(Path(job['profile'])),
        execution_fingerprints={p.relative_to(root).as_posix():sha256(p) for p in sources})
 def case_generator(self,factory):
    self.rig.origin=self.rig.pawn.get_actor_location()
    self.rig.ground_cache={}
    yield from super().case_generator(factory)
    self.rig.check(field_meshes(self.rig.world)==self.original_field,'temporal quality preserves original field meshes')
 def write(self):
    if self.report.get('passed') and self.report.get('protected_files_match'):
        try:
            self.report['temporal_quality']=check_quality(profile,self.report)
        except (ValueError,KeyError) as error:
            self.report.update(passed=False,error=str(error))
    super().write()

if __name__=='__main__':
 runtime=QualityRunner()
 runtime.start()
