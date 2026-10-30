"""Actual room old/new regular bow cycle, leg stability and skill regression."""
import hashlib
import json
import math
from pathlib import Path
import sys
import types
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path[:0] = [str(ROOT/'Tools/CharacterPipeline'), str(ROOT/'Tools/CharacterPipeline/Suites')]
from context import fps, qa
from character_switch import FieldRig
from training_room_verify import TrainingRunner, room, select, skill, navigation
from sparrow_runtime import xyz, valid
from countess_w_speed_compare import settle_switch

TIMES = (.0333, .10, .20, .2833, .40, .65, .95, 1.15, 1.40)

def record(rig):
    previous = len(rig.trace)
    FieldRig.record(rig)
    if len(rig.trace) == previous:
        return
    rig.latest['animation_class'] = rig.mesh.get_anim_instance().get_class().get_path_name()
    rig.latest['bones_component_space'] = {
        bone: xyz(rig.mesh.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT).translation)
        for bone in ('pelvis', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r')}

def setup(rig, mode=1):
    if isinstance(rig.pawn, unreal.SparrowCharacter):
        yield from select(rig, 'countess')
    unreal.SystemLibrary.execute_console_command(rig.world, 'Sparrow.Attack.Natural '+str(mode))
    yield from select(rig, 'sparrow')
    expected = 'ABP_Sparrow_BasicNatural_C' if mode else 'ABP_Sparrow_SmoothStop_C'
    rig.check(rig.mesh.get_anim_instance().get_class().get_name() == expected,
              'actual pawn selects requested isolated basic-attack AnimBP')
    rig.data['presentation_mode'] = mode
    yield .4

def spans(rows):
    return {bone: {axis: max(r['bones_component_space'][bone][i] for r in rows)-
                             min(r['bones_component_space'][bone][i] for r in rows)
                         for i, axis in enumerate(('x','y','z'))}
            for bone in ('pelvis','head','hand_r','foot_l','foot_r')}

def cycle(mode, close=False):
    def run(rig):
        yield from setup(rig, mode)
        target = rig.dummy(0, 550)
        rig.aim_target(target)
        if close:
            unreal.SystemLibrary.execute_console_command(rig.world, 'CharacterVisualQA.Camera Close')
            yield 1.5
        rig.snapshot()
        yield rig.capture(('new' if mode else 'old')+'-'+('close' if close else 'field')+'-before')
        first = len(rig.trace)
        start = rig.now
        yield from rig.click('Left', target.get_actor_location())
        rig.check(rig.pawn.is_attacking(), 'actual left controller click starts the bow montage')
        rig.data['started'] = start
        for index, at in enumerate(TIMES):
            yield max(1/fps, at-(rig.now-start))
            rig.snapshot()
            rig.data.setdefault('capture_times',[]).append(rig.now-start)
            yield rig.capture(('new' if mode else 'old')+'-'+('close' if close else 'field')+f'-{index:02d}')
        rows = [r for r in rig.trace[first:] if r['pawn']==rig.pawn.get_path_name()]
        shots = [r for r in rows if r['projectiles']]
        rig.check(bool(shots), 'the attack has a real released flying projectile')
        observed = shots[0]['time']-start
        expected = (.25 if mode else .05) / rig.pawn.get_editor_property('combo_attacks')[0].get_editor_property('play_rate')
        rig.check(expected-.0001 <= observed <= expected+3/fps+.0001,
                  'projectile release follows the selected draw/release timing')
        rig.check(abs(rig.health(target)-80)<.01, 'one basic arrow deals exactly 20 collision damage')
        rig.assert_recovered()
        armed = [r for r in rows if r['attacking']]
        rig.check(bool(armed), 'attack phase exists in the native trace')
        rig.check(all(r['combat_locomotion'] == (not bool(mode)) for r in armed),
                  'only the new basic attack preserves the relaxed underlying lower body')
        rig.check(max(math.dist(r['position'],rows[0]['position']) for r in rows)<.1,
                  'normal shot remains in place in the world')
        measurements = spans(rows)
        if mode:
            rig.check(max(measurements[bone][axis] for bone in ('pelvis','foot_l','foot_r')
                          for axis in ('x','y','z')) < 5,
                      'new regular bow cycle no longer repositions the pelvis or feet by large amounts')
        rig.data.update(first_projectile_seconds=observed, bone_axis_spans_cm=measurements,
                        damage=100-rig.health(target), capture_camera='close diagnostic' if close else 'approved gameplay quarter-view')
        if close:
            unreal.SystemLibrary.execute_console_command(rig.world, 'CharacterVisualQA.Camera Restore')
            yield 1.5
    return run

def repeated(rig):
    yield from setup(rig)
    target = rig.dummy(0,650)
    releases=[]
    for _ in range(3):
        start=rig.now
        yield from rig.click('Left',target.get_actor_location())
        rig.check(rig.pawn.is_attacking(),'each accepted repeated click starts one draw cycle')
        yield rig.until(lambda: bool(rig.arrows()),.6,'each new draw releases a real projectile')
        releases.append(rig.now-start)
        yield rig.idle()
        yield .4
    # Existing E applies 1.75% per previous stack: 20 + 20.35 + 20.70.
    rig.check(abs(rig.health(target)-38.95)<.01 and rig.component.get_relentless_stacks(target)==3,
              'three deliberate shots preserve existing Relentless scaling and record exactly three hits')
    rig.data['release_delays']=releases
    rig.assert_recovered()

def interrupted(rig):
    yield from setup(rig)
    target=rig.dummy(0,650)
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()),'bow draw starts before cancel')
    yield .12
    rig.interrupt()
    yield 1.1
    rig.check(rig.health(target)==100 and not rig.arrows(),'canceling during the new draw cancels the pending shot')
    rig.assert_recovered()

def ultimate_release(rig):
    yield from setup(rig)
    target=rig.dummy(0,700)
    yield from rig.skill_key('R',target.get_actor_location())
    yield rig.idle()
    rig.check(rig.component.is_inner_fire_active(),'R buff is active before enhanced attack')
    start=rig.now
    yield from rig.click('Left',target.get_actor_location())
    yield rig.until(lambda: len(rig.arrows())==3,.3,'R still releases its original three-arrow fan')
    delay=rig.now-start
    expected=.05/rig.pawn.get_editor_property('combo_attacks')[0].get_editor_property('play_rate')
    rig.check(expected-.0001<=delay<=expected+3/fps+.0001,'R retains its original early release phase at the configured attack speed')
    rig.check(rig.snapshot()['combat_locomotion'],'R retains its existing armed whole-body pose')
    rig.data['R_release_delay']=delay
    yield 4.5
    rig.assert_recovered()

class BasicRunner(TrainingRunner):
    def __init__(self):
        super().__init__()
        self.cases=[('room',room),('old_field',cycle(0)),('new_field',cycle(1)),
                    ('old_close',cycle(0,True)),('new_close',cycle(1,True)),
                    ('new_repeated',repeated),('new_cancel_during_draw',interrupted),
                    ('R_release_unchanged',ultimate_release)]
        self.cases += [('archer_'+key,skill('sparrow',key)) for key in ('Q','W','E','R')]
        self.cases += [('archer_movement',navigation('sparrow')),('assassin_W',skill('countess','W'))]
        self.report_name=f'sparrow-basic-natural-{fps}.json'
        self.report.update(suite='sparrow_basic_draw_and_upper_body',physical_input_tested=False,
                           capture_kind='actual-time native PIE frames, not continuous video',
                           fixed_viewport=[700,330], modified_skills=False)

    def case_generator(self,factory):
        self.rig.record=types.MethodType(record,self.rig)
        self.rig.switch=types.MethodType(settle_switch,self.rig)
        if not getattr(self,'viewport_ready',False):
            unreal.SystemLibrary.execute_console_command(self.rig.world,'CharacterVisualQA.ViewportSize 700 330')
            yield 2/fps
            self.viewport_ready=True
        yield from TrainingRunner.case_generator(self,factory)
        path=qa/(self.case_name+'-full-trace.json')
        path.write_text(json.dumps({'case':self.case_name,'fps':fps,'samples':self.rig.trace},indent=2),encoding='utf-8')
        self.rig.data['full_simulation_trace']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                                'samples':len(self.rig.trace)}

if __name__=='__main__':
    runtime=BasicRunner()
    runtime.start()
