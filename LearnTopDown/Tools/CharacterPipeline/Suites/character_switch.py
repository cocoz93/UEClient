"""Number-key selection in the original Countess field; no map or asset saves."""
from __future__ import annotations

import math
from pathlib import Path
import sys
import time

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from context import qa, fps, profile, configure_practice
from navigation_ready import editor_navigation_ready
from sparrow_runtime import Rig, Runner, valid, xyz

ORIGINAL_MAP = '/Game/TopDown/Lvl_TopDown'
HERO_NAMES = {
    'countess': ['Shadow Slip', 'Blade Siphon', 'Dark Tide', 'Feast'],
    'sparrow': ['Hail of Arrows', 'Piercing Shot', 'Rapid Shot', 'Inner Fire'],
}
HERO_CLASSES = {'countess': 'BP_CountessCharacter_C', 'sparrow': 'BP_SparrowCharacter_C'}
ARM_FIELDS = ('target_arm_length', 'relative_rotation', 'socket_offset', 'target_offset',
    'absolute_location', 'absolute_rotation', 'absolute_scale', 'use_pawn_control_rotation',
    'do_collision_test', 'probe_size', 'inherit_pitch', 'inherit_yaw', 'inherit_roll',
    'enable_camera_lag', 'enable_camera_rotation_lag', 'camera_lag_speed',
    'camera_rotation_lag_speed', 'camera_lag_max_distance', 'use_camera_lag_substepping',
    'camera_lag_max_time_step')
CAMERA_FIELDS = ('relative_location', 'relative_rotation', 'absolute_location',
    'absolute_rotation', 'absolute_scale', 'projection_mode', 'field_of_view', 'ortho_width',
    'ortho_near_clip_plane', 'ortho_far_clip_plane', 'aspect_ratio', 'constrain_aspect_ratio',
    'use_pawn_control_rotation', 'auto_calculate_ortho_planes')


def value(item):
    if isinstance(item, unreal.Vector):
        return xyz(item)
    if isinstance(item, unreal.Rotator):
        return [item.pitch, item.yaw, item.roll]
    if isinstance(item, (str, bool, int, float)) or item is None:
        return item
    return str(item)


def angle_error(left, right):
    return abs((left - right + 180.0) % 360.0 - 180.0)


def settings_equal(left, right):
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(settings_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(settings_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(left - right) <= 0.001
    return left == right


def settings(component, names):
    return {name: value(component.get_editor_property(name)) for name in names}


def field_meshes(world):
    """Snapshot original field actors, including their actual mesh and transforms."""
    rows = {}
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = component.get_editor_property('static_mesh')
        rows[actor.get_name()] = {'class': actor.get_class().get_path_name(),
            'mesh': mesh.get_path_name() if mesh else None, 'location': xyz(actor.get_actor_location()),
            'rotation': value(actor.get_actor_rotation()), 'scale': xyz(actor.get_actor_scale3d()),
            'mobility': str(component.get_editor_property('mobility')),
            'collision': str(component.get_collision_enabled())}
    return rows


class FieldRig(Rig):
    # Override the Sparrow-only access before Rig.__init__ invokes update_player.
    def update_player(self):
        self.mesh = self.pawn.get_editor_property('mesh')
        self.anim = self.mesh.get_anim_instance()
        self.movement = self.pawn.get_editor_property('character_movement')
        self.component = self.pawn.get_skills()
        self.saved_root_mode = self.anim.get_editor_property('root_motion_mode') if self.anim else None
        self.saved_orient = self.movement.get_editor_property('orient_rotation_to_movement')

    def native(self, command, token):
        import json
        path = qa / (token + '.json')
        if path.exists():
            path.unlink()
        unreal.SystemLibrary.execute_console_command(self.world, command + ' ' + token)
        self.check(path.exists(), 'current PIE native snapshot is produced: ' + command)
        return json.loads(path.read_text(encoding='utf-8'))

    def feet(self):
        half_height = self.pawn.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
        location = self.pawn.get_actor_location()
        return [location.x, location.y, location.z - half_height]

    def snapshot(self):
        self.pawn = unreal.GameplayStatics.get_player_character(self.world, 0)
        self.update_player()
        sample = self.native('SparrowQA.State', 'character-switch-state')
        nav = self.native('CountessInputQA.State', 'character-switch-input')
        camera = self.controller.player_camera_manager
        sample.update(pawn=self.pawn.get_path_name(), pawn_class=self.pawn.get_class().get_name(),
            controller=self.controller.get_path_name(), position=xyz(self.pawn.get_actor_location()),
            feet=self.feet(), view_location=xyz(camera.get_camera_location()),
            view_rotation=value(camera.get_camera_rotation()), view_fov=camera.get_fov_angle(),
            arm=settings(self.pawn.get_components_by_class(unreal.SpringArmComponent)[0], ARM_FIELDS),
            camera=settings(self.pawn.get_components_by_class(unreal.CameraComponent)[0], CAMERA_FIELDS),
            movement_mode=value(self.movement.get_editor_property('movement_mode')),
            velocity_z=self.pawn.get_velocity().z,
            floor_walkable=self.movement.get_editor_property('current_floor').get_editor_property('walkable_floor'),
            path_status=nav.get('path_status'), right_mouse_held=nav['right_mouse_held'],
            healths=[self.health(actor) for actor in self.targets])
        self.check(sample['audio_components'] == 0, 'no audio components are spawned during switching')
        for arrow in sample['projectiles']:
            self.check(arrow.get('mesh_forward_dot_flight', 0.0) >= 0.999,
                       'original-field arrowheads align with their actual flight trajectories')
        self.latest = sample
        return sample

    def record(self):
        now = self.now
        if self.trace and abs(now - self.trace[-1]['time']) < 0.000001:
            return
        sample = self.snapshot()
        sample['elapsed'] = now - self.runner.case_started
        if self.trace and sample['healths'] != self.trace[-1]['healths']:
            self.events.append({'time': sample['elapsed'], 'before': self.trace[-1]['healths'],
                                'after': sample['healths']})
        self.trace.append(sample)
        self.runner.report['audio_samples_checked'] += 1

    def hero(self, name):
        sample = self.snapshot()
        self.check(sample['pawn_class'] == HERO_CLASSES[name], 'actual controlled pawn is ' + name)
        self.check(sample['viewport_lighting'] and not sample['viewport_wireframe'],
                   'number-key selection retains the original lit viewport without debug view-mode changes')
        self.check(self.component.is_enabled() and self.component.get_skill_count() == 4,
                   name + ' implements the active four-slot skill contract')
        expected_names=HERO_NAMES[name][:]
        if name=='countess' and hasattr(self.component,'is_flurry_prototype_enabled') and self.component.is_flurry_prototype_enabled():
            expected_names[2]='Rending Flurry'
        self.check([slot['name'] for slot in sample['slots']] == expected_names,
                   'HUD resolves current ' + name + ' skill names from the possessed pawn')
        self.check([slot['passive'] for slot in sample['slots']] == [False] * 4,
                   'HUD passivity follows the currently selected hero')
        self.check(isinstance(self.controller.get_hud(), unreal.CharacterSkillHUD),
                   'the same controller retains its common skill HUD')
        self.check(unreal.GameplayStatics.get_player_controller(self.world, 0) == self.controller,
                   'character selection retains the original player controller')
        self.check(field_meshes(self.world) == self.runner.original_field,
                   'original field StaticMeshActors and their transforms remain unchanged')
        return sample

    def switch(self, name, moving=False, camera_settled=True):
        before = self.snapshot()
        previous = self.pawn
        key = 'Two' if name == 'sparrow' else 'One'
        self.key('Press', key)
        # InputKey queues an edge; the next PlayerInput frame invokes the real binding.
        yield 1.0 / fps
        immediate = self.hero(name)
        self.key('Release', key)
        self.check(self.pawn != previous and not valid(previous), 'successful selection destroys only the prior pawn')
        if before['movement_mode'] == str(unreal.MovementMode.MOVE_WALKING):
            self.check(immediate['movement_mode'] == before['movement_mode'] and immediate['floor_walkable']
                       and abs(immediate['velocity_z']) <= 0.001,
                       'grounded selection immediately retains Walking, a valid floor and zero vertical speed')
        feet_error = math.dist(before['feet'], immediate['feet'])
        bound = max(1.0, before['speed'] / fps + 1.0) if moving else 1.0
        self.check(feet_error <= bound, 'selection preserves capsule feet within 1 cm or one moving input-frame step')
        self.check(settings_equal(before['arm'], immediate['arm']) and settings_equal(before['camera'], immediate['camera']),
                   'selection preserves camera projection, rotation and lag settings within 0.001 numeric tolerance')
        row = {'from': before, 'immediate': immediate, 'feet_error_cm': feet_error,
               'moving': moving, 'camera_settled_before_input': camera_settled, 'input_processing_frames': 1,
               'one_simulation_step_bound_cm': bound, 'camera_cache_preservation_required': not moving}
        self.data.setdefault('switches', []).append(row)
        self.origin = self.pawn.get_actor_location()
        self.ground_cache = {}
        yield 1.0 / fps
        next_frame = self.snapshot()
        if before['movement_mode'] == str(unreal.MovementMode.MOVE_WALKING):
            self.check(next_frame['movement_mode'] == before['movement_mode'] and next_frame['floor_walkable']
                       and abs(next_frame['velocity_z']) <= 0.001,
                       'grounded selection keeps its valid floor without a falling frame')
        row.update(next_frame=next_frame, next_frame_feet_error_cm=math.dist(before['feet'], next_frame['feet']),
                   one_simulation_step_bound_cm=bound)
        self.check(row['next_frame_feet_error_cm'] <= bound,
                   'next-frame foot movement stays within the measured simulation-step bound')
        if not moving:
            row['next_frame_view_location_error_cm'] = math.dist(before['view_location'], next_frame['view_location'])
            row['next_frame_view_angle_error_degrees'] = [angle_error(a, b) for a, b in
                zip(before['view_rotation'], next_frame['view_rotation'])]
            self.check(row['next_frame_view_location_error_cm'] <= 1.0,
                       'next-frame stopped actual camera location is preserved within 1 cm')
            self.check(max(row['next_frame_view_angle_error_degrees']) <= 0.001,
                       'next-frame stopped actual camera angles are preserved within 0.001 degrees')
            # 시작 직후의 기존 카메라는 이미 보간 중이다. 두 프레임의 연속성은 위에서 검사하고,
            # 정착된 시점에만 0.4초 뒤에도 최초 위치가 같아야 한다는 조건을 적용한다.
            if not camera_settled:
                return
            yield 0.4
            settled = self.snapshot()
            row['settled'] = settled
            row['view_location_error_cm'] = math.dist(before['view_location'], settled['view_location'])
            row['view_angle_error_degrees'] = [angle_error(a, b) for a, b in
                zip(before['view_rotation'], settled['view_rotation'])]
            self.check(row['view_location_error_cm'] <= 1.0,
                       'stopped actual CameraManager view location is preserved within 1 cm')
            self.check(max(row['view_angle_error_degrees']) <= 0.001,
                       'stopped actual CameraManager view angles are preserved within 0.001 degrees')
            self.check(abs(before['view_fov'] - settled['view_fov']) <= 0.001,
                       'actual CameraManager field of view is preserved')

    def noop(self, name):
        before = self.hero(name)
        previous = self.pawn
        self.key('Press', 'Two' if name == 'sparrow' else 'One')
        self.key('Release', 'Two' if name == 'sparrow' else 'One')
        yield 0.15
        after = self.hero(name)
        self.check(self.pawn == previous and valid(previous), 'selecting current ' + name + ' is a pawn no-op')
        self.check(math.dist(before['feet'], after['feet']) <= 1.0,
                   'no-op selection preserves feet')
        self.data.setdefault('noops', []).append({'hero': name, 'before': before, 'after': after})

    def cleanup(self):
        sample = self.snapshot()
        # 공통 측정기는 암살자의 정상 잔여 효과도 기록하므로 제거된 궁수 소유 효과만 검사한다.
        sparrow_effects = [effect for effect in sample['effects'] if
            '/ParagonSparrow/' in effect['template'] or 'P_RainofArrows_SparrowRuntime' in effect['template']]
        self.check(not sample['projectiles'] and not sparrow_effects,
                   'previous Sparrow leaves no registered owned FX or projectile')
        self.check(not unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.SparrowCharacter),
                   'previous Sparrow pawn, skill zones and buff owner have been destroyed')
        return sample

    def aim_target(self, target):
        self.mouse('Move', 'Left', target.get_actor_location())
        cursor = self.native('CountessInputQA.State', 'character-switch-aim')
        probe = self.ground_probe(target.get_actor_location().x, target.get_actor_location().y, record=False)
        screen, viewport = probe['cursor_screen'], probe['viewport']
        self.data.setdefault('cursor_targets', []).append({'target': target.get_name(),
            'position': xyz(target.get_actor_location()), 'cursor': cursor,
            'screen': screen, 'viewport': viewport})
        self.check(screen['valid'] and 1.0 <= screen['x'] < viewport['x'] - 1.0 and
                   1.0 <= screen['y'] < viewport['y'] - 1.0,
                   'actual target projection lies inside the current PIE viewport')
        self.check(cursor['cursor_has_hit'] and cursor['cursor_raw_hit_actor'] == target.get_name(),
                   'actual viewport cursor ray selects the intended target instead of field geometry')


def idle_camera_and_field(rig):
    rig.hero('countess')
    rig.check(rig.pawn == rig.runner.first_pawn, 'original field starts its actual existing Countess pawn')
    yield 5.0  # Let the original level-start animation finish without replacing the pawn.
    rig.controller.stop_movement()
    rig.movement.stop_movement_immediately()
    yield 0.8
    sample = rig.snapshot()
    rig.check(sample['speed'] < 1.0 and not sample['combat_busy'], 'initial Countess is stopped before camera comparison')
    expected = profile['expected']['camera']
    for section, target in (('arm', expected['spring_arm']), ('camera', expected['camera_component'])):
        for key, desired in target.items():
            actual = sample[section][key]
            matches = all(abs(a - b) <= 0.001 for a, b in zip(actual, desired)) if isinstance(desired, list) else \
                (actual == desired if isinstance(desired, bool) else abs(float(actual) - desired) <= 0.001)
            rig.check(matches, 'original-field camera agrees with verified profile: ' + key)
    yield rig.capture('original-field-countess')
    yield from rig.switch('sparrow')
    rig.check(rig.latest['speed'] < 1.0, 'new Sparrow remains stopped for the paired capture')
    yield rig.capture('original-field-sparrow')


def noops_and_hud(rig):
    yield from rig.noop('sparrow')
    yield from rig.switch('countess')
    yield from rig.noop('countess')


def held_movement_and_pending_combo(rig):
    yield from rig.switch('sparrow')
    goal = rig.ground(0, 650)
    rig.mouse('Move', 'Right', goal)
    rig.assert_cursor_goal(goal)
    rig.mouse('Press', 'Right', goal)
    yield rig.until(lambda: math.hypot(rig.pawn.get_velocity().x, rig.pawn.get_velocity().y) > 100.0, 3.0,
                    'Sparrow actually moves under held right-mouse input')
    yield from rig.switch('countess', moving=True)
    stopped = rig.feet()
    yield 0.7  # Intentionally retain the physical key-down state until after this assertion.
    sample = rig.snapshot()
    rig.check(sample['right_mouse_held'], 'right key remains down while internal held-move reset is tested')
    rig.check(sample['speed'] < 1.0 and sample['path_status'] == 'Idle',
               'new Countess stops instead of inheriting the prior held movement request')
    rig.check(math.dist(stopped, sample['feet']) <= 1.0,
               'new Countess stays stopped while the previous mouse button remains held')
    rig.mouse('Release', 'Right', goal)
    yield 1.0 / fps
    # Queue a real Countess combo, then switch before any old hit timer can execute.
    target = rig.dummy(160)
    rig.aim_target(target)
    before = rig.health(target)
    step = rig.pawn.get_editor_property('combo_attacks')[0]
    montage = step.get_editor_property('montage')
    hit_delay = montage.get_play_length() / (step.get_editor_property('play_rate') *
        montage.get_editor_property('rate_scale')) * step.get_editor_property('hit_time_fraction')
    first_press = rig.now
    inputs = []
    for _ in range(2):
        yield from rig.click('Left', target.get_actor_location())
        rig.check(rig.pawn.is_attacking() and rig.pawn.get_combo_attack_number() == 1,
                   'processed Countess combo click retains its first active attack before the hit timer')
        inputs.append({'processed_at': rig.now, 'combo_step': rig.pawn.get_combo_attack_number(),
                       'sample': rig.snapshot()})
        yield 1.0 / fps  # Process this release before issuing the next distinct press.
    rig.check(rig.health(target) == before, 'both processed combo inputs occur before the first actual hit')
    rig.check(rig.now - first_press + 1.0 / fps < hit_delay,
               'the pending selection processing frame precedes the installed first-hit timer')
    rig.data['pending_combo_inputs'] = {'processed_clicks': inputs, 'first_press': first_press,
        'selection_queued_at': rig.now, 'installed_hit_delay': hit_delay,
        'queue_observed': 'two real press/release frames while the first combo step remains active'}
    yield from rig.switch('sparrow')
    yield 3.0
    rig.check(rig.health(target) == before,
               'destroyed Countess combo timers apply no delayed damage after selection')
    rig.data['pending_combo_health'] = {'before': before, 'after': rig.health(target)}


def skill_owner_cleanup_and_countess_reuse(rig):
    # Both pending and released Q/R are tested on the same original field and controller.
    for key, active in (('Q', False), ('Q', True), ('R', False), ('R', True)):
        if rig.pawn.get_class().get_name() != HERO_CLASSES['sparrow']:
            yield from rig.switch('sparrow')
        yield 0.2
        target = rig.dummy(550 if key == 'Q' else 1200)
        rig.aim_target(target)
        yield from rig.skill_key(key, target.get_actor_location())
        old_component = rig.component
        rig.check(old_component.is_casting(), key + ' real binding starts before owner selection')
        if active and key == 'Q':
            yield rig.until(lambda: old_component.get_active_hail_count() > 0, 1.0,
                            'released Q has an actual active damage zone before selection')
            yield rig.until(lambda: rig.health(target) < 100.0, 1.0,
                            'released Q has dealt actual damage before owner removal')
            yield rig.until(lambda: not rig.pawn.is_combat_busy(), 2.5, 'Q cast recovers while its zone remains active')
            rig.check(old_component.get_active_hail_count() > 0, 'Q independent zone still exists at selection')
        elif active and key == 'R':
            yield rig.until(old_component.is_inner_fire_active, 0.7,
                            'R actual buff is active before selection')
            yield rig.idle()
            yield from rig.click('Left', target.get_actor_location())
            rig.check(rig.pawn.is_attacking(), 'processed R-buffed basic input starts its actual attack')
            yield rig.until(lambda: len(rig.arrows()) == 3, 0.7,
                            'R has three actually released owner projectiles before selection')
        elif key == 'Q':
            rig.check(old_component.get_active_hail_count() == 0, 'pending Q has not emitted a zone')
        else:
            rig.check(not old_component.is_inner_fire_active(), 'pending R has not emitted its buff')
        health_before = rig.health(target)
        before = rig.snapshot()
        yield from rig.switch('countess')
        rig.cleanup()
        yield 1.1
        after = rig.cleanup()
        rig.check(rig.health(target) == health_before,
                   key + (' active' if active else ' pending') + ' causes no damage after owner selection')
        rig.data.setdefault('owner_cleanup', []).append({'skill': key, 'released': active,
            'before': before, 'after': after, 'health_before': health_before, 'health_after': rig.health(target)})
        target.destroy_actor()
        rig.targets.remove(target)
        rig.fixtures.remove(target)
    target = rig.dummy(160)
    rig.aim_target(target)
    before_basic = rig.health(target)
    yield from rig.click('Left', target.get_actor_location())
    rig.check(rig.pawn.is_attacking(), 'returned Countess basic attack starts through the same controller')
    yield rig.until(lambda: rig.health(target) < before_basic, 2.0,
                    'returned Countess basic attack deals actual target damage')
    yield rig.idle()
    before_skill = rig.health(target)
    yield from rig.skill_key('W', target.get_actor_location())
    rig.check(rig.component.is_casting(), 'returned Countess W starts through the same controller')
    yield rig.until(lambda: rig.health(target) < before_skill, 2.5,
                    'returned Countess Blade Siphon deals actual target damage')
    yield rig.idle()
    rig.hero('countess')
    rig.cleanup()
    rig.data['countess_reuse_health'] = {'before_basic': before_basic, 'after_basic': before_skill,
                                       'after_skill': rig.health(target)}


class SwitchRunner(Runner):
    def __init__(self):
        super().__init__('character_switch', [
            ('idle_camera_and_original_field', idle_camera_and_field),
            ('same_selection_and_hud', noops_and_hud),
            ('moving_and_pending_combo', held_movement_and_pending_combo),
            ('pending_active_skill_owner_cleanup_and_countess_reuse', skill_owner_cleanup_and_countess_reuse)])
        self.report.update(map=ORIGINAL_MAP, profile_map_ignored=profile['map'],
            pawn_respawn_between_cases=False, input='actual_controller_One_Two_and_gameplay_bindings',
            physical_input_tested=False, world_settings_saved=False)

    def start(self):
        try:
            configure_practice(False)
            if not unreal.EditorLoadingAndSavingUtils.load_map(ORIGINAL_MAP):
                raise RuntimeError('Original Countess field could not be loaded')
            self.handle = unreal.register_slate_post_tick_callback(self.tick)
        except Exception as error:
            self.finish(error)

    def case_generator(self, factory):
        # Remove only this suite's temporary targets; never replace its possessed pawn or field actors.
        for actor in self.rig.fixtures:
            if valid(actor):
                actor.destroy_actor()
        self.rig.fixtures, self.rig.targets = [], []
        self.rig.trace, self.rig.events, self.rig.data = [], [], {}
        self.case_started = self.rig.now
        yield from factory(self.rig)

    def tick(self, delta):
        if self.phase == 'start':
            try:
                if time.monotonic() - self.wall_started > 120.0:
                    raise TimeoutError('EditorWorld navigation did not become usable before PIE copying')
                if not editor_navigation_ready():
                    return
                self.report['editor_navigation_ready_before_pie'] = True
                self.report['editor_navigation_wait_seconds'] = time.monotonic() - self.wall_started
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                self.phase = 'world'
                self.pie_requested_wall = time.monotonic()
            except Exception as error:
                self.finish(error)
            return
        if self.phase != 'world':
            super().tick(delta)
            return
        try:
            if time.monotonic() - self.pie_requested_wall > 70.0:
                raise TimeoutError('Original Countess field PIE did not become ready')
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if world is None:
                return
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            if not pawn or not controller or not pawn.get_editor_property('mesh').get_anim_instance() or \
                    pawn.get_editor_property('character_movement').is_falling() or \
                    unreal.NavigationSystemV1.is_navigation_being_built(world):
                return
            self.first_pawn = pawn
            self.original_field = field_meshes(world)
            self.rig = FieldRig(self, world, controller, pawn)
            self.rig.check(bool(self.original_field), 'original field contains actual StaticMeshActors')
            first = self.rig.hero('countess')
            self.report.update(initial_pawn=first, original_field_static_mesh_actors=self.original_field,
                               original_field_static_mesh_actor_count=len(self.original_field))
            self.phase = 'between'
        except Exception as error:
            self.finish(error)


if __name__ == '__main__':
    runtime = SwitchRunner()
    runtime.start()
