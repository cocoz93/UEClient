"""Measured relaxed/combat posture transitions in the original Countess field."""
from pathlib import Path
import math
import sys
import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from context import fps
from sparrow_runtime import Runner, valid
from character_switch import SwitchRunner, ORIGINAL_MAP, field_meshes
from sparrow_field_presentation import select_sparrow


def lowered(rig, label):
    sample = rig.snapshot()
    rig.check(not sample['combat_locomotion'], label + ' selects relaxed locomotion')
    rig.check(sample['head_minus_draw_hand_z'] >= 30.0, label + ' keeps the draw hand at least 30 cm below the head')


def close_capture(rig, name):
    # SCS 재생성을 일으키는 에디터 속성 편집 대신 PIE 런타임 API로 잠시 확대한다.
    arm = rig.pawn.get_components_by_class(unreal.SpringArmComponent)[0]
    camera = rig.pawn.get_components_by_class(unreal.CameraComponent)[0]
    before = (arm.get_editor_property('target_arm_length'), camera.get_editor_property('field_of_view'))
    mesh = rig.mesh
    unreal.SystemLibrary.execute_console_command(rig.world, 'CharacterVisualQA.Camera Close')
    rig.runner.report['transient_evidence_camera'] = {'distance': 600, 'pitch': -15, 'yaw': 35, 'fov': 45, 'saved': False}
    yield 3.0 / fps
    yield rig.capture(name)
    unreal.SystemLibrary.execute_console_command(rig.world, 'CharacterVisualQA.Camera Restore')
    yield 2.0 / fps
    rig.check(rig.pawn.get_editor_property('mesh') == mesh, 'evidence camera retains the original live mesh and cloth simulation')
    rig.check(abs(arm.get_editor_property('target_arm_length') - before[0]) < .001 and
              abs(camera.get_editor_property('field_of_view') - before[1]) < .001,
              'evidence camera restores the actual original-field distance and FOV')


def neutral_loop(rig):
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', rig.mesh.get_editor_property('skeletal_mesh_asset'))
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    original = unreal.load_asset('/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/idle_relaxed')
    copy = unreal.load_asset('/Game/TopDown/Characters/Sparrow/Animations/A_Sparrow_RelaxedIdle')
    source_start = unreal.AnimationLibrary.get_time_at_frame(original, 183)
    errors = []
    for step in range(11):
        seconds = min(copy.get_play_length() - 0.00001, step * copy.get_play_length() / 10)
        before = unreal.AnimPoseExtensions.get_anim_pose_at_time(original, source_start + seconds, options)
        after = unreal.AnimPoseExtensions.get_anim_pose_at_time(copy, seconds, options)
        for bone in ('pelvis', 'head', 'hand_l', 'hand_r', 'bow_base', 'foot_l', 'foot_r'):
            left = unreal.AnimPoseExtensions.get_bone_pose(before, bone, unreal.AnimPoseSpaces.WORLD).translation
            right = unreal.AnimPoseExtensions.get_bone_pose(after, bone, unreal.AnimPoseSpaces.WORLD).translation
            errors.append(math.dist([left.x, left.y, left.z], [right.x, right.y, right.z]))
    rig.check(max(errors) < 0.01, 'owned idle bone keys reproduce the selected source segment within 0.01 cm')
    rig.data['maximum_owned_source_pose_error_cm'] = max(errors)
    yield 0.4
    lowered(rig, 'ordinary idle')
    yield from close_capture(rig, 'relaxed-idle')
    start = rig.now
    gaps = []
    while rig.now - start < 10.4:
        lowered(rig, 'relaxed idle across two complete loops')
        gaps.append(rig.latest['head_minus_draw_hand_z'])
        yield 0.15
    rig.data['minimum_idle_head_hand_gap_cm'] = min(gaps)
    yield from close_capture(rig, 'relaxed-idle-loop-boundary')


def neutral_move(rig):
    goal = rig.ground(0, 800)
    yield from rig.click('Right', goal)
    rig.assert_cursor_goal(goal)
    yield 0.5
    moving = rig.snapshot()
    rig.check(moving['speed'] > 450.0, 'actual right-click moves the selected pawn')
    lowered(rig, 'ordinary moving pose')
    yield from close_capture(rig, 'relaxed-movement')
    yield 0.35
    rig.check(rig.snapshot()['speed'] > 450.0, 'ordinary movement continues after its initial turn')
    lowered(rig, 'steady moving pose')
    yield from close_capture(rig, 'relaxed-movement-settled')
    yield 1.5
    lowered(rig, 'movement arrival')
    rig.check(rig.latest['speed'] < 1.0, 'movement stops at the field destination')
    yield from close_capture(rig, 'relaxed-after-movement')


def primary_recovery(rig):
    target = rig.dummy(0, 450)
    rig.aim_target(target)
    yield from rig.click('Left', target.get_actor_location())
    yield 0.05
    rig.snapshot()
    rig.check(rig.pawn.is_attacking() and not rig.latest['combat_locomotion'],
              'actual regular attack preserves the relaxed underlying lower body')
    rig.check(rig.latest['montage'] == 'AM_Sparrow_PrimaryNatural',
              'actual regular attack plays its declared upper-body draw/release montage')
    yield from close_capture(rig, 'primary-combat-pose')
    yield rig.idle()
    yield 0.4
    lowered(rig, 'basic attack recovery')
    yield from close_capture(rig, 'relaxed-after-primary')


def skills_recovery(rig):
    target = rig.dummy(0, 450)
    for key in ('Q', 'W'):
        rig.aim_target(target)
        yield from rig.skill_key(key, target.get_actor_location())
        yield 0.25
        rig.snapshot()
        rig.check(rig.component.is_casting() and rig.latest['combat_locomotion'], key + ' cast uses the combat pose')
        yield from close_capture(rig, key.lower() + '-combat-pose')
        yield rig.idle(4.0)
        yield 0.4
        lowered(rig, key + ' recovery')
        yield from close_capture(rig, 'relaxed-after-' + key.lower())
    yield from rig.skill_key('E', target.get_actor_location())
    yield 0.3
    lowered(rig, 'passive E input')
    rig.check(rig.latest['slots'][2]['passive'], 'E retains its passive definition')


def ultimate_recovery(rig):
    yield from rig.skill_key('R', rig.ground(0, 700))
    yield rig.idle()
    yield 0.3
    rig.snapshot()
    rig.check(rig.component.is_inner_fire_active() and rig.latest['combat_locomotion'], 'active R buff retains armed idle')
    rig.check(rig.latest['head_minus_draw_hand_z'] < 20.0, 'R buff uses the measured authored armed pose')
    yield from close_capture(rig, 'r-buff-armed-idle')
    goal = rig.ground(0, 450)
    yield from rig.click('Right', goal)
    rig.assert_cursor_goal(goal)
    yield 0.45
    rig.snapshot()
    rig.check(rig.latest['speed'] > 450.0 and rig.latest['combat_locomotion'], 'R movement uses armed locomotion')
    rig.check(rig.latest['head_minus_draw_hand_z'] < 20.0, 'R movement keeps the authored armed hand position')
    yield from close_capture(rig, 'r-buff-armed-movement')
    yield rig.until(lambda: not rig.component.is_inner_fire_active(), 5.0, 'R buff expires through its real timer')
    yield 0.5
    lowered(rig, 'R buff expiry')
    yield from close_capture(rig, 'relaxed-after-r')


class PoseRunner(SwitchRunner):
    def __init__(self):
        Runner.__init__(self, 'sparrow_pose', [
            ('original_field_selection', select_sparrow), ('neutral_idle_loop', neutral_loop),
            ('neutral_movement', neutral_move), ('primary_recovery', primary_recovery),
            ('skills_recovery', skills_recovery), ('ultimate_recovery', ultimate_recovery)])
        self.selected_pawn = None
        self.report.update(map=ORIGINAL_MAP, presentation_mode='user_requested_variant',
                           original_game_behavior='unverified', pawn_respawn_between_cases=False)

    def case_generator(self, factory):
        yield from super().case_generator(factory)
        self.rig.check(self.rig.pawn == self.selected_pawn and valid(self.selected_pawn), 'posture cases retain the selected original-field pawn')
        self.rig.check(field_meshes(self.rig.world) == self.original_field, 'posture cases preserve the original field')


if __name__ == '__main__':
    runtime = PoseRunner()
    runtime.start()
