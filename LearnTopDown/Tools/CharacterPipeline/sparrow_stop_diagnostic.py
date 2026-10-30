"""Read-only Sparrow stop/heading/cloth observation in the actual training-room PIE."""
import hashlib
import json
import math
from pathlib import Path
import sys
import types

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path[:0] = [str(ROOT / 'Tools/CharacterPipeline'), str(ROOT / 'Tools/CharacterPipeline/Suites')]
from context import fps, qa
from sparrow_runtime import Runner, valid, xyz
from character_switch import FieldRig, angle_error, field_meshes
from training_room_verify import TrainingRunner, ROOM, room, select


def heading(vector):
    return math.degrees(math.atan2(vector.y, vector.x)) if math.hypot(vector.x, vector.y) > .001 else None


def transform_row(transform):
    q = transform.rotation
    return {'translation': xyz(transform.translation), 'rotation_quaternion': [q.x, q.y, q.z, q.w],
            'scale': xyz(transform.scale3d)}


def record_motion(rig):
    if rig.trace and abs(rig.now - rig.trace[-1]['time']) < .000001:
        return
    FieldRig.record(rig)
    sample = rig.latest
    velocity = rig.pawn.get_velocity()
    acceleration = rig.movement.get_current_acceleration()
    requested = rig.movement.get_last_update_requested_velocity()
    actor_yaw = rig.pawn.get_actor_rotation().yaw
    bones = {bone: transform_row(rig.mesh.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT))
             for bone in ('root', 'pelvis', 'spine_03', 'head', 'foot_l', 'foot_r')}
    sample['motion'] = {'actor_yaw': actor_yaw, 'velocity': xyz(velocity), 'velocity_yaw': heading(velocity),
        'acceleration': xyz(acceleration), 'acceleration_yaw': heading(acceleration),
        'last_update_requested_velocity': xyz(requested), 'requested_velocity_yaw': heading(requested),
        'bones_component_space': bones, 'mesh_world_transform': transform_row(rig.mesh.get_world_transform()),
        'orient_to_movement': rig.movement.get_editor_property('orient_rotation_to_movement')}
    sample['motion']['actor_velocity_error_degrees'] = (angle_error(actor_yaw, heading(velocity))
        if heading(velocity) is not None else None)
    # Native command returns deterministic, evenly sampled simulation vertices in component space.
    sample['cloth_points_component_space'] = (rig.native('SparrowMotionQA.Cloth', 'sparrow-motion-cloth')
        if isinstance(rig.pawn, unreal.SparrowCharacter) else None)


def camera_check(rig):
    arm = rig.pawn.get_components_by_class(unreal.SpringArmComponent)[0]
    camera = rig.pawn.get_components_by_class(unreal.CameraComponent)[0]
    rotation = arm.get_editor_property('relative_rotation')
    rig.check(abs(arm.get_editor_property('target_arm_length') - 2000) < .001 and
              abs(rotation.pitch + 50) < .001 and abs(rotation.yaw - 45) < .001 and
              abs(camera.get_editor_property('field_of_view') - 55) < .001,
              'diagnostic retains approved quarter-view camera')


def motion_measurement(rig, label, goal, captures=True):
    start = rig.now
    initial = xyz(rig.pawn.get_actor_location())
    yield from rig.click('Right', goal)
    selected = rig.assert_cursor_goal(goal)
    observation = {'label': label, 'started': start, 'start_position': initial,
        'requested_goal': xyz(goal), 'selected_navigation_goal': xyz(selected), 'captures': [],
        'pre_stop_capture_method': 'remaining XY distance / current speed <= .15 seconds; measured offset recorded afterward'}
    rig.data.setdefault('legs', []).append(observation)
    moving_seen = rig.latest['speed'] > 1
    pre_captured = False
    maximum_speed = 0.0
    while rig.now - start < 6:
        sample = rig.latest
        speed = sample['speed']
        maximum_speed = max(maximum_speed, speed)
        moving_seen |= speed > 1
        remaining = math.dist(xyz(rig.pawn.get_actor_location())[:2], xyz(selected)[:2])
        if captures and not pre_captured and speed > 1 and remaining / speed <= .15 + 1 / fps:
            pre_captured = True
            observation['captures'].append({'phase': 'estimated-pre-stop', 'time': rig.now})
            yield rig.capture(label + '-pre-stop')
        if moving_seen and speed < 1:
            break
        yield 1 / fps
    rig.check(moving_seen, label + ' actually moves after its controller click')
    rig.check(rig.latest['speed'] < 1, label + ' reaches natural physical rest without forced stop')
    stopped = rig.now
    observation.update(stopped=stopped, duration=stopped - start, maximum_speed=maximum_speed,
        actual_stop_actor_yaw=rig.pawn.get_actor_rotation().yaw,
        final_goal_distance_cm=math.dist(xyz(rig.pawn.get_actor_location())[:2], xyz(selected)[:2]))
    rig.check(observation['final_goal_distance_cm'] < 60, label + ' arrives near its actual navigation target')
    if captures:
        # A very short path can stop before the predictive threshold is sampled. Record this honestly.
        observation['predictive_capture_observed'] = pre_captured
        for suffix, after in (('stop', 0), ('after-010', .1), ('after-030', .3), ('after-070', .7)):
            if after:
                yield max(1 / fps, after - (rig.now - stopped))
            observation['captures'].append({'phase': suffix, 'time': rig.now})
            yield rig.capture(label + '-' + suffix)
        yield max(1 / fps, 1.5 - (rig.now - stopped))
    else:
        yield .15
    for capture in observation['captures']:
        capture['seconds_relative_to_actual_stop'] = capture['time'] - stopped
    rows = [row for row in rig.trace if start <= row['time'] <= stopped + 1.51]
    moving_rows = [row for row in rows if row['speed'] > 20]
    observation['last_moving_actor_yaw'] = moving_rows[-1]['motion']['actor_yaw'] if moving_rows else None
    observation['last_moving_velocity_yaw'] = moving_rows[-1]['motion']['velocity_yaw'] if moving_rows else None
    observation['stopped_actor_yaw'] = observation['actual_stop_actor_yaw']
    observation['post_settling_actor_yaw'] = rig.pawn.get_actor_rotation().yaw
    observation['final_actor_vs_last_velocity_error_degrees'] = (angle_error(
        observation['stopped_actor_yaw'], observation['last_moving_velocity_yaw']) if moving_rows else None)
    observation['maximum_moving_actor_velocity_error_degrees'] = max(
        (row['motion']['actor_velocity_error_degrees'] for row in moving_rows), default=None)
    observation['stopped_pose_steps_cm'] = {}
    for bone in ('foot_l', 'foot_r', 'pelvis', 'head'):
        edges = [(a, b) for a, b in zip(rows, rows[1:]) if stopped - .2 <= b['time'] <= stopped + .3]
        observation['stopped_pose_steps_cm'][bone] = max((math.dist(
            a['motion']['bones_component_space'][bone]['translation'],
            b['motion']['bones_component_space'][bone]['translation']) for a, b in edges), default=0)


def direction_case(index):
    def run(rig):
        yield from select(rig, 'sparrow')
        camera_check(rig)
        theta = math.radians(index * 45)
        goal = rig.ground(650 * math.cos(theta), 650 * math.sin(theta))
        yield from motion_measurement(rig, 'direction-' + str(index * 45), goal)
    return run


def short_turn(label, dx, dy):
    def run(rig):
        yield from select(rig, 'sparrow')
        camera_check(rig)
        yield from motion_measurement(rig, label + '-approach', rig.ground(0, 500), False)
        position = rig.pawn.get_actor_location()
        yield from motion_measurement(rig, label, rig.ground_absolute(position.x + dx, position.y + dy))
    return run


def held_near(rig):
    yield from select(rig, 'sparrow')
    camera_check(rig)
    start = rig.now
    origin = xyz(rig.pawn.get_actor_location())
    rig.mouse('Press', 'Right', rig.ground(0, 90))
    for _ in range(fps):
        position = rig.pawn.get_actor_location()
        rig.mouse('Move', 'Right', rig.ground_absolute(position.x, position.y + 90))
        yield 1 / fps
    position = rig.pawn.get_actor_location()
    goal = rig.ground_absolute(position.x, position.y + 90)
    rig.mouse('Release', 'Right', goal)
    released = rig.now
    yield rig.capture('held-near-release')
    yield rig.until(lambda: rig.latest['speed'] < 1, 3, 'released held input naturally reaches rest')
    stopped = rig.now
    actual_stop_actor_yaw = rig.pawn.get_actor_rotation().yaw
    rows = [{'phase': 'release', 'time': released}]
    for label, after in (('stop', 0), ('after-010', .1), ('after-030', .3), ('after-070', .7)):
        if after:
            yield max(1 / fps, after - (rig.now - stopped))
        rows.append({'phase': label, 'time': rig.now, 'seconds_relative_to_actual_stop': rig.now - stopped})
        yield rig.capture('held-near-' + label)
    yield max(1 / fps, 1.5 - (rig.now - stopped))
    rows[0]['seconds_relative_to_actual_stop'] = released - stopped
    rig.check(math.dist(origin[:2], xyz(rig.pawn.get_actor_location())[:2]) > 100,
              'held nearby cursor actually moves the archer through the room')
    rig.data['held_input'] = {'started': start, 'released': released, 'stopped': stopped, 'captures': rows,
        'actual_stop_actor_yaw': actual_stop_actor_yaw, 'post_settling_actor_yaw': rig.pawn.get_actor_rotation().yaw}


def overview(rig):
    yield from room(rig)
    yield from select(rig, 'sparrow')
    camera_check(rig)
    yield rig.capture('diagnostic-sparrow-overview')


class StopDiagnosticRunner(TrainingRunner):
    def __init__(self):
        cases = [('room_and_archer_selection', overview)]
        cases += [('direction_' + str(index * 45), direction_case(index)) for index in range(8)]
        cases += [('short_reverse_110', short_turn('short-reverse-110', 0, -110)),
                  ('short_reverse_160', short_turn('short-reverse-160', 0, -160)),
                  ('short_cross_110', short_turn('short-cross-110', 110, 0)),
                  ('held_near_release', held_near)]
        Runner.__init__(self, 'sparrow_stop_diagnostic', cases)
        self.report.update(map=ROOM, character_code_modified=False, scene_changes_saved=False,
            diagnostic_only=True, direction_error_is_measurement_not_failure=True,
            cloth_limits_are_measurements_not_acceptance=True,
            camera='approved gameplay quarter-view; no close-camera replacements',
            offscreen_texture_pool_mb=512, offscreen_virtual_shadow_cache_pages=1024,
            trace_sampling='every unique simulation frame; separate full trace files, report samples remain 10 Hz')

    def case_generator(self, factory):
        rig = self.rig
        rig.record = types.MethodType(record_motion, rig)
        yield from TrainingRunner.case_generator(self, factory)
        rig.check(field_meshes(rig.world) == self.original_field, 'diagnostic preserves all original room mesh actors')
        directory = qa / 'traces'
        directory.mkdir(exist_ok=True)
        path = directory / (self.case_name + '-' + str(fps) + '.json')
        path.write_text(json.dumps({'case': self.case_name, 'fps': fps, 'samples': rig.trace}, indent=2), encoding='utf-8')
        rig.data['full_simulation_trace'] = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'samples': len(rig.trace), 'minimum_time_step': min((b['time'] - a['time'] for a, b in zip(rig.trace, rig.trace[1:])), default=None),
            'maximum_time_step': max((b['time'] - a['time'] for a, b in zip(rig.trace, rig.trace[1:])), default=None)}

    def advance(self):
        # This observation run must retain raw cloth excursions rather than abort at the older style gate.
        Runner.advance(self)


if __name__ == '__main__':
    runtime = StopDiagnosticRunner()
    runtime.start()
