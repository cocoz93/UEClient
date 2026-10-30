"""Verify archer stop completion yields to new navigation, combat and hero selection."""
from pathlib import Path
import json, math, sys
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
sys.path[:0]=[str(ROOT/'Tools/CharacterPipeline'),str(ROOT/'Tools/CharacterPipeline/Suites')]
from context import fps, qa
from training_room_verify import TrainingRunner, room, switch, primary, skill, select, HERO_PROFILES
from character_switch import angle_error


def setup(rig):
    yield from room(rig)
    for name in ('Countess','Sparrow'):
        unreal.SystemLibrary.execute_console_command(rig.world,name+'.Skills.IgnoreCooldowns 1')


def stop_window(rig):
    yield from select(rig,'sparrow')
    yield from rig.click('Right',rig.ground(0,500))
    yield rig.until(lambda:rig.latest['speed']>100,2,'archer genuinely enters approach movement')
    yield rig.until(lambda:rig.latest['speed']<1,3,'approach naturally stops')
    yield .25
    p=rig.pawn.get_actor_location()
    yield from rig.click('Right',rig.ground_absolute(p.x,p.y-110))
    yield rig.until(lambda:rig.latest['path_status']=='Idle' and rig.latest['speed']>1,
                    3,'reverse path finishes while its last physical movement frame remains')
    rig.data['interruption_window']={'time':rig.now,'speed':rig.latest['speed'],
                                    'yaw':rig.pawn.get_actor_rotation().yaw,'path_status':rig.latest['path_status']}
    unreal.SystemLibrary.execute_console_command(rig.world,'SparrowStopQA.State sparrow-stop-state')
    state=json.loads((qa/'sparrow-stop-state.json').read_text(encoding='utf-8'))
    rig.check(state['anim_class']==HERO_PROFILES['sparrow']['expected'].get('runtime_anim_class', HERO_PROFILES['sparrow']['expected']['anim_class']),
              'the possessed archer actually uses the declared runtime copy preserving smooth-stop')
    rig.check(state['pending'] and state['deadline']>state['time'],
              'arrival finishing is actually pending before the interruption')
    rig.data['interruption_window']['reservation']=state


def observe_aim(rig,target):
    rows=[]
    initial_yaw=rig.pawn.get_actor_rotation().yaw
    rig.data['combat_aim_frames']=rows
    p=rig.pawn.get_actor_location();t=target.get_actor_location()
    distance=math.hypot(t.x-p.x,t.y-p.y)
    radius=target.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_radius()
    # Real mouse traces aim at the hit capsule surface, rather than its actor origin.
    center_bound=math.degrees(math.asin(min(1,radius/distance)))+1
    rig.data['combat_aim_surface_bound_degrees']=center_bound
    for _ in range(math.ceil(.25*fps)):
        p=rig.pawn.get_actor_location();t=target.get_actor_location()
        expected=math.degrees(math.atan2(t.y-p.y,t.x-p.x))
        error=angle_error(expected,rig.pawn.get_actor_rotation().yaw)
        drift=angle_error(initial_yaw,rig.pawn.get_actor_rotation().yaw)
        rows.append({'time':rig.now,'yaw':rig.pawn.get_actor_rotation().yaw,
                     'aim_error_degrees':error,'heading_drift_degrees':drift})
        rig.check(error<center_bound,'the actual attack or skill aims at the clicked target surface')
        rig.check(drift<.1,'arrival finishing preserves the actual combat heading on every observed frame')
        yield 1/fps
    rig.data['combat_aim_error_degrees']=max(row['aim_error_degrees'] for row in rows)
    rig.data['combat_heading_drift_degrees']=max(row['heading_drift_degrees'] for row in rows)


def aimed_interruption(key):
    def run(rig):
        yield from stop_window(rig)
        p=rig.pawn.get_actor_location()
        target=rig.dummy_at_ground(p.x+450,p.y+120)
        rig.aim_target(target)
        if key=='Attack':
            yield from rig.click('Left',target.get_actor_location())
            rig.check(rig.pawn.is_attacking(),'actual primary attack interrupts arrival finishing')
        else:
            yield from rig.skill_key(key,target.get_actor_location())
            rig.check(rig.component.is_casting(),'actual '+key+' interrupts arrival finishing')
        yield from observe_aim(rig,target)
        yield rig.capture('stop-interrupted-by-'+key)
        yield rig.until(lambda:rig.health(target)<100,5,'interruption produces real target damage')
        yield rig.idle(6)
        yield rig.until(lambda:not any(e['active'] and e['particles']>0 for e in rig.latest['effects']),
                        12,'interruption particles expire normally')
        rig.assert_recovered()
    return run


def new_move(rig):
    yield from stop_window(rig)
    p=rig.pawn.get_actor_location()
    goal=rig.ground_absolute(p.x+450,p.y)
    yield from rig.click('Right',goal)
    selected=rig.assert_cursor_goal(goal)
    rows=[]
    previous_error=None
    for _ in range(math.ceil(.25*fps)):
        current=rig.pawn.get_actor_location()
        desired=math.degrees(math.atan2(selected.y-current.y,selected.x-current.x))
        error=angle_error(rig.pawn.get_actor_rotation().yaw,desired)
        rows.append({'time':rig.now,'yaw':rig.pawn.get_actor_rotation().yaw,'goal_error_degrees':error})
        if previous_error is not None:
            rig.check(error<=previous_error+1,'new navigation continues turning toward its own goal each frame')
        previous_error=error
        yield 1/fps
    rig.data['new_navigation_heading_frames']=rows
    yield .15
    yaw=math.degrees(math.atan2(selected.y-p.y,selected.x-p.x))
    rig.check(rig.latest['speed']>400 and angle_error(rig.pawn.get_actor_rotation().yaw,yaw)<2,
              'new navigation turns toward its own direction without the previous stop reservation')
    yield rig.capture('new-navigation-overrides-stop')
    yield rig.until(lambda:rig.latest['speed']<1,3,'new navigation naturally stops')
    yield .3
    rig.assert_recovered()


def change_owner(rig):
    yield from stop_window(rig)
    yield from rig.switch('countess',moving=True)
    yield .25
    rig.hero('countess')
    yield rig.capture('owner-switch-clears-arrival')


class RegressionRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases=[('room_and_materials',setup),('numeric_selection_camera',switch),
                    ('archer_primary',primary('sparrow'))]
        self.cases += [('archer_'+key,skill('sparrow',key)) for key in ('Q','W','E','R')]
        self.cases += [('stop_attack_interruption',aimed_interruption('Attack')),
                       ('stop_new_navigation',new_move),('stop_Q_interruption',aimed_interruption('Q')),
                       ('stop_owner_selection',change_owner)]
        self.report_name=f'dual-character-regression-{fps}.json'
        self.report.update(character_code_modified=True,scope='archer combat/selection after stop completion changes')


if __name__=='__main__':
    runtime=RegressionRunner()
    runtime.start()
