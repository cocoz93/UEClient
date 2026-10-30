"""Frame-driven Sparrow PIE fixtures; no operating-system input or asset saves."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
import time
import traceback

import unreal

from baseline import verify
from navigation_ready import editor_navigation_ready
from context import root, job, qa, fps, profile, protected, configure_practice, write_json


def valid(actor):
    return actor is not None and unreal.SystemLibrary.is_valid(actor)


def xyz(vector):
    return [vector.x, vector.y, vector.z]


def distance2d(left, right):
    return math.hypot(left.x - right.x, left.y - right.y)


def assert_bow_effect_attachment(rig, fragment):
    effects = [effect for effect in rig.latest.get('effects', [])
               if fragment in effect['template'] and effect['active']]
    bow = xyz(rig.mesh.get_socket_location('BowEmitterSocket'))
    rig.check(bool(effects), fragment + ' has a live original particle component')
    errors = [math.dist(effect['position'], bow) for effect in effects]
    rig.check(all(effect.get('socket') == 'BowEmitterSocket' for effect in effects),
              fragment + ' follows the authored moving bow socket')
    rig.check(max(errors) <= 1.0, fragment + ' remains within one centimeter of the animated bow socket')
    row = {'time': rig.now, 'template': fragment, 'bow_position': bow,
           'effect_positions': [effect['position'] for effect in effects], 'errors_cm': errors}
    rig.data.setdefault('bow_effect_attachment', []).append(row)
    return row


class Until:
    def __init__(self, condition, timeout, label):
        self.condition = condition
        self.timeout = timeout
        self.label = label


class Capture:
    def __init__(self, name):
        self.name = name


class Rig:
    def __init__(self, runner, world, controller, pawn):
        self.runner = runner
        self.world = world
        self.controller = controller
        self.pawn = pawn
        self.origin = pawn.get_actor_location()
        self.character_class = pawn.get_class()
        self.fixtures = []
        self.targets = []
        self.spawn_id = 0
        self.latest = {}
        self.trace = []
        self.events = []
        self.data = {}
        self.ground_cache = {}
        self.update_player()

    @property
    def now(self):
        return unreal.GameplayStatics.get_time_seconds(self.world)

    def check(self, condition, label):
        if not condition:
            raise AssertionError(label)
        self.runner.report['checks'].append(self.runner.case_name + ': ' + label)

    def update_player(self):
        self.mesh = self.pawn.get_editor_property('mesh')
        self.anim = self.mesh.get_anim_instance()
        self.movement = self.pawn.get_editor_property('character_movement')
        self.component = self.pawn.get_sparrow_skills()
        self.saved_root_mode = self.anim.get_editor_property('root_motion_mode') if self.anim else None
        self.saved_orient = self.movement.get_editor_property('orient_rotation_to_movement')

    def spawn(self, actor_class, position):
        self.spawn_id += 1
        name = 'SparrowPIE_' + str(self.spawn_id)
        actor_class = actor_class if isinstance(actor_class, unreal.Class) else actor_class.static_class()
        unreal.SystemLibrary.execute_console_command(self.world,
            f'CountessComboQA.Spawn {name} {actor_class.get_path_name()} {position.x} {position.y} {position.z}')
        actor = next((actor for actor in unreal.GameplayStatics.get_all_actors_of_class(self.world, actor_class)
                      if actor.get_name() == name), None)
        self.check(valid(actor), 'PIE fixture spawned: ' + name)
        self.fixtures.append(actor)
        return actor

    def point(self, x=0.0, y=0.0, z=0.0):
        return self.origin + unreal.Vector(x=x, y=y, z=z)

    def ground(self, x=0.0, y=0.0):
        return self.ground_absolute(self.origin.x + x, self.origin.y + y)

    def ground_probe(self, x, y, record=True):
        unreal.SystemLibrary.execute_console_command(self.world,
            f'SparrowQA.Ground sparrow-ground {x} {y} {self.origin.z}')
        path = qa / 'sparrow-ground.json'
        self.check(path.exists(), 'native ground probe produced its current PIE report')
        probe = json.loads(path.read_text(encoding='utf-8'))
        if probe['ground_hit']:
            self.check(abs(probe['ground']['x'] - x) < 0.001 and abs(probe['ground']['y'] - y) < 0.001,
                       'native ground probe reports the current requested XY coordinates')
        if record:
            self.data.setdefault('ground_probes', []).append(probe)
        return probe

    def ground_absolute(self, x, y):
        cache_key = (round(float(x), 4), round(float(y), 4))
        if cache_key not in self.ground_cache:
            probe = self.ground_probe(x, y)
            self.check(probe['ground_hit'], 'vertical trace finds an actual field surface')
            self.check(probe['normal_z'] >= 0.55, 'ground fixture uses a walkable field surface')
            self.ground_cache[cache_key] = probe
        point = self.ground_cache[cache_key]['ground']
        return unreal.Vector(x=point['x'], y=point['y'], z=point['z'])

    def assert_cursor_goal(self, goal):
        probe = self.ground_probe(goal.x, goal.y)
        self.check(probe['navigation_projected'], 'actual ground target projects onto the character navigation mesh')
        self.check(probe['cursor_navigation_projected'], 'actual viewport cursor hit projects onto the same navigation mesh')
        requested_screen, cursor_screen = probe['requested_screen'], probe['cursor_screen']
        self.check(requested_screen['valid'] and cursor_screen['valid'],
                   'requested ground and cached cursor have valid viewport coordinates')
        screen_error = {axis: abs(requested_screen[axis] - cursor_screen[axis]) for axis in ('x', 'y')}
        self.check(max(screen_error.values()) <= 1.0 + 0.0001,
                   'cached cursor agrees with the requested screen point within one physical pixel per axis')
        self.check(probe['cursor_visibility_hit']['hit'] and
                   probe['cursor_visibility_hit']['actor'] == probe['ground_actor'],
                   'vertical ground and actual cursor ray select the same field actor')
        requested, selected = probe['nav'], probe['cursor_nav']
        navigation_error = math.dist([requested[axis] for axis in ('x', 'y', 'z')],
                                     [selected[axis] for axis in ('x', 'y', 'z')])
        one_pixel_world_step = float(probe['one_pixel_ground_step_cm'])
        self.check(math.isfinite(one_pixel_world_step) and one_pixel_world_step > 0.0,
                   'native probe measures a finite nonzero world distance for one screen pixel')
        quantization_bound = one_pixel_world_step * math.sqrt(2.0) + 0.001
        self.check(navigation_error <= quantization_bound,
                   'navigation goal difference fits the measured physical-pixel quantization bound')
        self.data['cursor_input_measurement'] = {'requested_screen': requested_screen,
            'cursor_screen': cursor_screen, 'viewport': probe['viewport'], 'screen_error_pixels': screen_error,
            'one_pixel_ground_step_cm': one_pixel_world_step, 'navigation_error_cm': navigation_error,
            'navigation_quantization_bound_cm': quantization_bound, 'ground_actor': probe['ground_actor']}
        self.data['requested_navigation_goal'] = requested
        self.data['selected_navigation_goal'] = selected
        return unreal.Vector(x=selected['x'], y=selected['y'], z=selected['z'])

    def dummy_at_ground(self, x, y, small=False):
        ground = self.ground_absolute(x, y)
        actor = self.spawn(unreal.KwangTrainingDummy, ground + unreal.Vector(x=0, y=0, z=90.0))
        if small:
            actor.set_actor_scale3d(unreal.Vector(x=0.25, y=0.25, z=1.0))
        self.targets.append(actor)
        return actor

    def dummy(self, x=600.0, y=0.0, small=False):
        return self.dummy_at_ground(self.origin.x + x, self.origin.y + y, small)

    def wall(self, x=250.0, y=0.0, dynamic=False):
        probe = self.ground_probe(self.origin.x + x, self.origin.y + y)
        self.check(probe['ground_hit'], 'wall fixture is anchored to an actual solid field surface')
        ground = probe['ground']
        actor = self.spawn(unreal.StaticMeshActor,
            unreal.Vector(x=ground['x'], y=ground['y'], z=ground['z'] + 175.0))
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        component.set_collision_profile_name('BlockAllDynamic' if dynamic else 'BlockAll')
        actor.set_actor_scale3d(unreal.Vector(x=0.4, y=5.0, z=3.5))
        return actor

    def health(self, actor):
        return float(actor.get_editor_property('health')) if valid(actor) else None

    def arrows(self):
        return [actor for actor in unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SparrowArrow)
                if valid(actor)]

    def mouse(self, action, button, point):
        unreal.SystemLibrary.execute_console_command(self.world,
            f'CountessComboQA.Mouse {action} {button} {point.x} {point.y} {point.z}')

    def key(self, action, key):
        unreal.SystemLibrary.execute_console_command(self.world, f'CountessInputQA.Key {key} {action}')

    def click(self, button, point):
        self.mouse('Press', button, point)
        yield 1.0 / fps
        self.mouse('Release', button, point)

    def skill_key(self, key, aim):
        self.mouse('Move', 'Left', aim)
        self.key('Press', key)
        yield 1.0 / fps
        self.key('Release', key)

    def until(self, condition, timeout, label):
        return Until(condition, timeout, label)

    def idle(self, timeout=3.0):
        return self.until(lambda: valid(self.pawn) and not self.pawn.is_combat_busy(), timeout,
                          'combat state returns to idle')

    def capture(self, name):
        return Capture(name)

    def interrupt(self):
        self.anim.montage_stop(0.0)

    def assert_recovered(self):
        self.check(not self.pawn.is_combat_busy(), 'combat lock recovered')
        self.check(self.movement.get_editor_property('orient_rotation_to_movement') == self.saved_orient,
                   'movement-facing flag restored')
        self.check(self.mesh.get_anim_instance().get_editor_property('root_motion_mode') == self.saved_root_mode,
                   'root-motion mode restored')

    def record(self):
        if not valid(self.pawn) or self.mesh.get_anim_instance() is None:
            return
        unreal.SystemLibrary.execute_console_command(self.world, 'SparrowQA.State sparrow-sample')
        path = qa / 'sparrow-sample.json'
        sample = json.loads(path.read_text(encoding='utf-8'))
        if self.trace and abs(sample['time'] - self.trace[-1]['time']) < 0.000001:
            return
        self.latest = sample
        self.check(sample['audio_components'] == 0, 'audio engine has no spawned audio components')
        for effect in sample['effects']:
            template = effect['template']
            if not template:
                self.check(not effect['active'] and effect['particles'] == 0,
                           'an unconfigured particle component remains inactive and emits no particles')
                continue
            self.check('/Skins/Rogue/' not in template,
                       'live Sparrow FX do not use Rogue skin templates')
            self.check('/ParagonSparrow/FX/Particles/Sparrow/Abilities/' in template or
                       'P_RainofArrows_SparrowRuntime' in template,
                       'live Sparrow FX use default source assets or the protected transient rain copy')
        for arrow in sample['projectiles']:
            self.check(arrow.get('mesh_forward_dot_flight', 0.0) >= 0.999,
                       'the actual arrowhead direction aligns with its three-dimensional flight trajectory')
        sample.update(position=xyz(self.pawn.get_actor_location()), yaw=self.pawn.get_actor_rotation().yaw,
                      arrow_origin=xyz(self.component.get_arrow_origin()),
                      elapsed=self.now - self.runner.case_started,
                      healths=[self.health(actor) for actor in self.targets],
                      feet={bone: xyz(self.mesh.get_socket_transform(bone,
                            unreal.RelativeTransformSpace.RTS_COMPONENT).translation)
                            for bone in ('foot_l', 'foot_r')},
                      arrow_state=[{'position': xyz(actor.get_actor_location()),
                                    'distance': actor.get_distance_travelled(),
                                    'remaining': actor.get_remaining_range(),
                                    'hits': actor.get_hit_count(),
                                    'direction': xyz(actor.get_flight_direction()),
                                    'piercing': actor.is_piercing(), 'passes_world': actor.passes_world()}
                                   for actor in self.arrows()])
        if self.trace and sample['healths'] != self.trace[-1]['healths']:
            self.events.append({'time': sample['elapsed'], 'before': self.trace[-1]['healths'],
                                'after': sample['healths']})
        self.latest = sample
        self.trace.append(sample)
        self.runner.report['audio_samples_checked'] += 1

    def fresh(self):
        for key in ('Q', 'W', 'E', 'R', 'SpaceBar'):
            self.key('Release', key)
        for button in ('Left', 'Right'):
            self.mouse('Release', button, self.origin)
        self.controller.stop_movement()
        for actor in self.fixtures + self.arrows():
            if valid(actor):
                actor.destroy_actor()
        self.fixtures = []
        self.targets = []
        previous = self.pawn
        self.pawn = self.spawn(self.character_class, self.origin)
        self.fixtures.remove(self.pawn)
        self.controller.possess(self.pawn)
        if valid(previous):
            previous.destroy_actor()
        self.update_player()
        self.trace = []
        self.events = []
        self.data = {}
        self.latest = {}
        self.ground_cache = {}

    def attack_metadata(self):
        steps = self.pawn.get_editor_property('combo_attacks')
        self.check(len(steps) == 1, 'Sparrow has one ranged basic-attack step')
        step = steps[0]
        montage = step.get_editor_property('montage')
        duration = montage.get_play_length() / (step.get_editor_property('play_rate') *
                                               montage.get_editor_property('rate_scale'))
        fraction = step.get_editor_property('hit_time_fraction')
        variant = profile.get('presentation_contract', {}).get('basic_attack_variant')
        expected_runtime = profile.get('expected', {}).get('runtime_anim_class')
        if variant and self.mesh.get_anim_instance().get_class().get_path_name() == expected_runtime and not self.component.is_inner_fire_active():
            fraction = variant['release_seconds'] / variant['duration']
        return {'duration': duration, 'hit_delay': duration * fraction}

    def replace_destroyed_player(self):
        self.pawn = self.spawn(self.character_class, self.origin)
        self.fixtures.remove(self.pawn)
        self.controller.possess(self.pawn)
        self.update_player()


class Runner:
    def __init__(self, suite, cases):
        self.suite = suite
        self.cases = cases
        self.index = 0
        self.case_name = 'startup'
        self.case_started = 0.0
        self.wall_started = time.monotonic()
        self.phase = 'start'
        self.rig = None
        self.report = {'passed': False, 'suite': suite, 'fixed_simulation_fps': fps,
                       'map': profile['map'], 'mode': 'actual_editor_Play_In_Editor',
                       'physical_input_tested': False, 'input': 'controller_bindings_and_public_gameplay_api',
                       'audio_engine_enabled': True, 'audio_samples_checked': 0,
                       'scene_changes_saved': False, 'cases': [], 'checks': [], 'screenshots': []}
        self.report_name = f'{suite.replace("_", "-")}-{fps}.json'

    def write(self):
        write_json(self.report_name, self.report)

    def start(self):
        try:
            configure_practice(False)
            if not unreal.EditorLoadingAndSavingUtils.load_map(profile['map']):
                raise RuntimeError('Sparrow field could not be loaded')
            self.handle = unreal.register_slate_post_tick_callback(self.tick)
        except Exception as error:
            self.finish(error)

    def validate_player(self):
        rig = self.rig
        rig.check(rig.pawn.get_class().get_name() == 'BP_SparrowCharacter_C', 'Sparrow field starts the configured pawn')
        rig.check(rig.mesh.get_editor_property('skeletal_mesh_asset').get_path_name() == profile['expected']['mesh'],
                  'configured Rogue mesh is active')
        rig.check(rig.mesh.get_editor_property('anim_class').get_path_name() == profile['expected'].get('runtime_anim_class', profile['expected']['anim_class']),
                  'Sparrow locomotion AnimBP is active')
        rig.check(rig.mesh.get_editor_property('anim_class').get_name() == profile['expected'].get('runtime_anim_class', profile['expected']['anim_class']).rsplit('.', 1)[-1],
                  'dedicated Sparrow AnimBP is active')
        rig.check(rig.pawn.get_components_by_class(unreal.SpringArmComponent)[0].get_editor_property('target_arm_length') == 2000,
                  'quarter-view camera distance is 2000')
        for component_class, key in ((unreal.SpringArmComponent, 'spring_arm'),
                                     (unreal.CameraComponent, 'camera_component')):
            camera_component = rig.pawn.get_components_by_class(component_class)[0]
            for name, desired in profile['expected']['camera'][key].items():
                actual = camera_component.get_editor_property(name)
                if name == 'relative_rotation':
                    actual = [actual.pitch, actual.yaw, actual.roll]
                    matches = all(abs(a - b) < 0.001 for a, b in zip(actual, desired))
                elif isinstance(desired, bool):
                    matches = actual == desired
                else:
                    matches = abs(float(actual) - desired) < 0.001
                rig.check(matches, f'{key}.{name} matches the verified Countess camera')
        rig.check(rig.component.is_enabled(), 'Sparrow skills validate their animation skeletons')
        rig.check(isinstance(rig.controller.get_hud(), unreal.CharacterSkillHUD), 'common skill HUD is active')
        actual = rig.component.get_editor_property('skills')
        expected = profile.get('skill_defaults', [])
        rig.check(len(actual) == len(expected) == 4, 'four configured skill slots are installed')
        for index, (definition, declared) in enumerate(zip(actual, expected)):
            for name in ('damage', 'cooldown', 'range', 'action_time', 'recovery_time'):
                rig.check(abs(definition.get_editor_property(name) - declared[name]) < 0.0001,
                          f'slot {index} {name} matches its installed profile')
        self.report['installed_skill_defaults'] = expected
        self.report['installed_basic_attack'] = rig.attack_metadata()

    def case_generator(self, factory):
        rig = self.rig
        rig.fresh()
        yield 0.6
        yield rig.until(lambda: not rig.movement.is_falling() and rig.mesh.get_anim_instance() is not None,
                        10.0, 'fresh Sparrow pawn settles on the field')
        rig.update_player()
        rig.anim.montage_stop(0.0)
        rig.movement.stop_movement_immediately()
        rig.pawn.set_actor_rotation(unreal.Rotator(yaw=0.0), True)
        rig.trace = []
        rig.events = []
        self.case_started = rig.now
        yield from factory(rig)

    def advance(self):
        try:
            waiting = next(self.generator)
        except StopIteration:
            rig = self.rig
            self.report['cases'].append({'name': self.case_name, 'passed': True,
                'duration': rig.now - self.case_started, 'events': rig.events, 'data': rig.data,
                'samples': rig.trace[::max(1, fps // 10)], 'sample_count': len(rig.trace)})
            self.write()
            self.index += 1
            self.phase = 'between'
            return
        self.waiting = waiting
        self.wait_started = self.rig.now
        self.wait_wall = time.monotonic()
        if isinstance(waiting, Capture):
            directory = qa / 'screenshots'
            directory.mkdir(exist_ok=True)
            self.capture_path = directory / f'{self.index:02d}-{waiting.name}-{fps}.png'
            self.capture_state = dict(self.rig.latest)
            self.capture_size = 0
            self.capture_stable_since = time.monotonic()
            self.rig.check(unreal.GameplayStatics.set_game_paused(self.rig.world, True), 'PIE pauses at the capture pose')
            unreal.SystemLibrary.execute_console_command(self.rig.world,
                'CharacterVisualQA.Capture ' + self.capture_path.stem)

    def tick(self, delta):
        try:
            wall = time.monotonic()
            if wall - self.wall_started > 340.0:
                raise TimeoutError('Sparrow suite exceeded 340 seconds at ' + self.case_name)
            if self.phase == 'start':
                if wall - self.wall_started > 120.0:
                    raise TimeoutError('Editor navigation did not become usable before PIE copying')
                if wall - self.wall_started > 1.0 and editor_navigation_ready():
                    self.report['editor_navigation_ready_before_pie'] = True
                    self.report['editor_navigation_wait_seconds'] = wall - self.wall_started
                    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                    self.phase = 'world'
                    self.pie_requested_wall = wall
                return
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if world is None:
                return
            if self.phase == 'world':
                if wall - self.pie_requested_wall > 70.0:
                    raise TimeoutError('Sparrow PIE pawn or navigation did not become ready')
                pawn = unreal.GameplayStatics.get_player_character(world, 0)
                controller = unreal.GameplayStatics.get_player_controller(world, 0)
                if pawn is None or controller is None or pawn.get_editor_property('mesh').get_anim_instance() is None:
                    return
                if unreal.NavigationSystemV1.is_navigation_being_built(world):
                    return
                self.rig = Rig(self, world, controller, pawn)
                self.validate_player()
                for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
                    dummy.destroy_actor()
                self.phase = 'between'
                return
            if self.phase == 'between':
                if self.index == len(self.cases):
                    self.finish()
                    return
                self.case_name, factory = self.cases[self.index]
                self.case_started = self.rig.now
                self.generator = self.case_generator(factory)
                self.phase = 'case'
                self.advance()
                return
            if self.phase != 'case':
                return
            self.rig.record()
            waiting = self.waiting
            elapsed = self.rig.now - self.wait_started
            if isinstance(waiting, Until):
                if waiting.condition():
                    self.rig.check(True, waiting.label)
                    self.advance()
                elif elapsed > waiting.timeout:
                    raise TimeoutError(waiting.label)
            elif isinstance(waiting, Capture):
                if self.capture_path.exists() and self.capture_path.stat().st_size > 24:
                    size = self.capture_path.stat().st_size
                    if size != self.capture_size:
                        self.capture_size = size
                        self.capture_stable_since = wall
                        return
                    if wall - self.capture_stable_since < 0.05:
                        return
                    data = self.capture_path.read_bytes()
                    self.rig.check(data[:8] == b'\x89PNG\r\n\x1a\n', 'native screenshot is a PNG file')
                    self.rig.check(data[-8:-4] == b'IEND', 'native screenshot write includes the complete PNG end chunk')
                    width, height = struct.unpack('>II', data[16:24])
                    self.rig.check([width, height] == self.capture_state['viewport_size'], 'native screenshot matches the actual PIE viewport dimensions')
                    self.report['screenshots'].append({'image': str(self.capture_path),
                        'sha256': hashlib.sha256(data).hexdigest(), 'width': width, 'height': height,
                        'case': self.case_name, 'state': self.capture_state, 'visual_reviewed': False})
                    unreal.GameplayStatics.set_game_paused(world, False)
                    self.advance()
                elif wall - self.wait_wall > 12.0:
                    raise TimeoutError('Native screenshot was not saved: ' + str(self.capture_path))
            elif elapsed + 0.00001 >= float(waiting):
                self.advance()
        except Exception as error:
            self.finish(error)

    def finish(self, error=None):
        if self.phase == 'finished':
            return
        previous_phase = self.phase
        self.phase = 'finished'
        self.report['passed'] = error is None
        if error is not None:
            self.report.update(error=str(error), traceback=traceback.format_exc(), failed_case=self.case_name,
                               failed_phase=previous_phase, failed_samples=self.rig.trace[-120:] if self.rig else [],
                               failed_initial_samples=self.rig.trace[:30] if self.rig else [],
                               failed_fixture_data=self.rig.data if self.rig else {},
                               last_sample=self.rig.latest if self.rig else {})
            unreal.log_error(str(error))
        try:
            if hasattr(self, 'handle'):
                unreal.unregister_slate_post_tick_callback(self.handle)
            if self.rig:
                unreal.GameplayStatics.set_game_paused(self.rig.world, False)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            self.write()
        finally:
            self.finish_wall = time.monotonic()
            self.finish_handle = unreal.register_slate_post_tick_callback(self.exit_editor)

    def exit_editor(self, delta):
        if time.monotonic() - self.finish_wall < 1.5:
            return
        unreal.unregister_slate_post_tick_callback(self.finish_handle)
        try:
            result = verify(Path(job['baseline']))
            captures = self.report.get('screenshots', [])
            changed = [row['image'] for row in captures if not Path(row['image']).is_file() or
                       hashlib.sha256(Path(row['image']).read_bytes()).hexdigest() != row['sha256']]
            self.report['capture_integrity'] = {'passed': not changed, 'checked': len(captures), 'changed': changed}
            if changed:
                self.report.update(passed=False, error='Screenshot changed after capture: ' + str(changed))
            self.report['baseline_after'] = result
            self.report['protected_files_match'] = result['passed']
            self.report['protected_files_checked'] = len(protected)
            if not result['passed']:
                self.report['passed'] = False
                self.report['error'] = 'Protected assets changed during Sparrow PIE verification'
            self.write()
        except Exception as error:
            self.report.update(passed=False, error=str(error), traceback=traceback.format_exc())
            self.write()
        finally:
            unreal.SystemLibrary.quit_editor()


def run(suite, cases):
    runner = Runner(suite, cases)
    runner.start()
    return runner
