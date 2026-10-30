"""Actual Q/W/E/R viewport evidence after number-key selection in the original field."""
from __future__ import annotations

import math
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from context import fps, profile
from sparrow_runtime import Runner, valid, xyz
from character_switch import FieldRig, SwitchRunner, ORIGINAL_MAP, field_meshes


def effects(rig, fragment):
    return [effect for effect in rig.latest.get('effects', [])
            if fragment in effect['template'] and effect['active'] and effect['particles'] > 0]


def damage(rig, slot):
    return rig.component.get_editor_property('skills')[slot].get_editor_property('damage')


def check_bow_attachment(rig, fragment, label):
    rows = effects(rig, fragment)
    rig.check(bool(rows), label + ' has active original particles')
    socket = rig.mesh.get_socket_location('BowEmitterSocket')
    measured = []
    for effect in rows:
        distance = math.dist(effect['position'], xyz(socket))
        attached_socket = effect.get('attach_socket', effect.get('socket', ''))
        row = {'template': effect['template'], 'socket': attached_socket,
               'effect_position': effect['position'], 'bow_socket_position': xyz(socket),
               'distance_cm': distance, 'particles': effect['particles'],
               'bone_source_valid': effect['bone_source_valid']}
        measured.append(row)
        rig.check(attached_socket == 'BowEmitterSocket' and distance <= 1.0,
                  label + ' is attached at the actual bow emitter socket within 1 cm')
        rig.check(effect['bone_source_valid'], label + ' resolves the current Sparrow skeletal source')
    rig.data.setdefault('bow_attachments', []).extend(measured)


def select_sparrow(rig):
    rig.hero('countess')
    rig.check(rig.pawn == rig.runner.first_pawn,
              'original field retains its actual initial Countess before the number-key input')
    yield 0.2
    yield from rig.switch('sparrow', camera_settled=False)
    rig.runner.selected_pawn = rig.pawn
    rig.runner.report['selected_pawn'] = rig.pawn.get_path_name()
    rig.check(not rig.pawn.is_combat_busy() and not rig.latest['montage'],
              'actual Two selection leaves Sparrow immediately ready for field inputs')
    yield rig.capture('original-field-sparrow-idle')


def q_arrow_rain(rig):
    target = rig.dummy(600)
    rig.aim_target(target)
    # 방향 스킬은 화면에 보이는 캡슐 표면의 커서 HitPoint를 사용한다. 표적 중심으로 강제 스냅하지 않는다.
    aim_probe = rig.ground_probe(target.get_actor_location().x, target.get_actor_location().y)
    cursor = aim_probe['cursor_visibility_hit']
    rig.check(cursor['hit'] and cursor['actor'] == target.get_name(),
              'Q expected ground is derived from the actual visible cursor hit on the target')
    ground = rig.ground_absolute(cursor['x'], cursor['y'])
    started = rig.now
    yield from rig.skill_key('Q', target.get_actor_location())
    rig.check(rig.component.is_casting() and rig.latest['active_skill'] == 1,
              'actual Q controller key starts the field cast')
    yield rig.capture('field-q-cast')
    yield rig.until(lambda: rig.component.get_active_hail_count() == 1, 0.8,
                    'actual Q releases one persistent arrow-rain zone')
    yield max(0.0, 1.3 - (rig.now - started))
    rig.snapshot()
    rain = [row for row in effects(rig, 'RainofArrows') if 'Proj' not in row['template']]
    rig.check(bool(rain), 'Q rain at 1.3 seconds contains live falling-arrow particles')
    impacts = [emitter for row in rain for emitter in row.get('emitters', [])
               if emitter['name'].startswith('Impact') and emitter['particles'] > 0]
    rig.check(bool(impacts), 'Q rain produces actual ground collision-event impact particles')
    rig.check(all(math.dist(row['position'], xyz(ground)) <= 1.0 for row in rain),
              'Q rain emitter is anchored to the measured original-field ground within 1 cm')
    rig.check(rig.health(target) < 100.0, 'visible Q rain has already applied actual target damage')
    rig.data.update(q_input_time=started, q_rain_capture_elapsed=rig.now - started,
                    q_ground=xyz(ground), q_rain_effects=rain, q_impact_emitters=impacts)
    yield rig.capture('field-q-arrow-rain-1p3s')
    yield rig.until(lambda: rig.component.get_active_hail_count() == 0, 4.5,
                    'Q field zone expires through its real gameplay timer')
    rig.check(abs(rig.health(target) - (100.0 - damage(rig, 0))) < 0.01,
              'the complete Q field rain applies its configured total damage')
    rig.check(rig.component.get_relentless_stacks(target) == 8,
              'Q field rain records all eight actual damage pulses')
    yield rig.idle()
    yield 0.3


def w_charge_and_release(rig):
    target = rig.dummy(1000)
    rig.aim_target(target)
    started = rig.now
    yield from rig.skill_key('W', target.get_actor_location())
    yield max(0.0, 0.4 - (rig.now - started))
    rig.snapshot()
    rig.check(rig.component.is_casting() and rig.latest['active_skill'] == 2 and not rig.arrows(),
              'actual W at 0.4 seconds is charging without an early projectile')
    rig.check(rig.health(target) == 100.0, 'W charge applies no pre-release damage')
    check_bow_attachment(rig, 'Sparrow_RMB', 'W charge')
    rig.data.update(w_input_time=started, w_charge_capture_elapsed=rig.now - started)
    yield rig.capture('field-w-charge-0p4s')
    yield rig.until(lambda: len(rig.arrows()) == 1, 1.5,
                    'actual W key releases one charged projectile after the charge')
    arrow = rig.arrows()[0]
    rig.check(arrow.is_piercing() and arrow.passes_world(),
              'the field W release retains target piercing and world passage')
    rig.data['w_release'] = {'elapsed': rig.now - started, 'origin': xyz(arrow.get_actor_location()),
                             'direction': xyz(arrow.get_flight_direction()),
                             'speed': arrow.get_flight_speed()}
    yield 1.0 / fps
    rig.snapshot()
    rig.check(valid(arrow) and len(rig.latest['projectiles']) == 1,
              'W release capture contains the actual flying arrow')
    rig.check(bool(effects(rig, 'Sparrow_RMB')), 'W release contains live charged-arrow trail particles')
    yield rig.capture('field-w-release')
    yield rig.until(lambda: rig.health(target) < 100.0, 1.2,
                    'the field W projectile collides with the aimed target')
    rig.check(abs(rig.health(target) - (100.0 - damage(rig, 1))) < 0.01,
              'actual W collision applies its configured damage exactly once')
    yield rig.idle()
    yield 0.4
    rig.check(abs(rig.health(target) - (100.0 - damage(rig, 1))) < 0.01,
              'W presentation leaves no repeated collision damage')


def e_passive_feedback_and_stacks(rig):
    # +X에는 원본 허수아비가 서 있다. 이를 보존하고 단일 적중/패시브 검사는 +Y에서 수행한다.
    target = rig.dummy(0, 800)
    rig.aim_target(target)
    yield from rig.skill_key('E', target.get_actor_location())
    rig.snapshot()
    rig.check(rig.latest['slots'][2]['passive'] and not rig.component.is_casting()
              and not rig.pawn.is_combat_busy(), 'actual E retains the selected passive behavior')
    rig.check('passive' in rig.latest['feedback'].lower(),
              'actual E key produces visible explanatory HUD feedback')
    rig.check(rig.latest['slots'][2]['cooldown'] == 0.0,
              'passive E key does not consume an active cooldown')
    rig.data['e_feedback'] = rig.latest['feedback']
    yield rig.capture('field-e-passive-feedback')
    healths = [rig.health(target)]
    for expected_stacks in (1, 2):
        yield from rig.click('Left', target.get_actor_location())
        rig.check(rig.pawn.is_attacking(), 'actual left-click starts the E integration bow attack')
        yield rig.until(lambda: rig.component.get_relentless_stacks(target) == expected_stacks, 1.2,
                        'actual bow collision creates passive stack ' + str(expected_stacks))
        healths.append(rig.health(target))
        yield rig.idle()
        if expected_stacks == 1:
            yield 0.35
    rig.snapshot()
    base_damage = rig.component.get_editor_property('basic_attack_damage')
    rig.check(abs(healths[1] - (100.0 - base_damage)) < 0.01,
              'first E integration hit applies the configured basic damage')
    rig.check(abs(healths[2] - (healths[1] - base_damage * 1.0175)) < 0.01,
              'the second E integration hit applies the prior-stack 1.75 percent bonus')
    rig.check('2 / 10' in rig.latest['slots'][2]['status'],
              'the field HUD displays the two measured Relentless stacks')
    rig.data.update(e_healths=healths, e_actual_stacks=rig.component.get_relentless_stacks(target),
                    e_hud_status=rig.latest['slots'][2]['status'])
    yield rig.capture('field-e-two-hit-stacks')
    yield 0.4


def r_cast_buff_and_three_arrows(rig):
    target = rig.dummy(0, 1100)
    rig.aim_target(target)
    pressed = rig.now
    yield from rig.skill_key('R', target.get_actor_location())
    rig.check(rig.component.is_casting() and rig.latest['active_skill'] == 4,
              'actual R controller key starts its initial field montage')
    yield rig.capture('field-r-cast-initial')
    yield rig.until(rig.component.is_inner_fire_active, 0.5,
                    'actual R action activates the four-second Inner Fire buff')
    activated = rig.now
    rig.check(rig.component.get_buff_remaining() > 3.7,
              'R field buff starts with its full configured duration')
    yield rig.idle()
    rig.snapshot()
    check_bow_attachment(rig, 'SparrowBuff', 'R persistent buff')
    rig.check('3-shot' in rig.latest['slots'][3]['status'],
              'field HUD reports the active R buff and its remaining duration')
    rig.data.update(r_key_time=pressed, r_observed_activation_time=activated,
                    r_buff_before_attack=rig.component.get_buff_remaining())
    yield rig.capture('field-r-buff')
    yield from rig.click('Left', target.get_actor_location())
    rig.check(rig.pawn.is_attacking(), 'actual left-click starts the buffed field bow attack')
    yield rig.until(lambda: len(rig.arrows()) == 3, 0.5,
                    'the actual R-buffed release produces three distinct arrows')
    release = rig.now
    arrows = list(rig.arrows())
    rig.check(release - activated < 4.0 and rig.component.is_inner_fire_active(),
              'the three-arrow release occurs inside the actual four-second buff window')
    rig.check(all(arrow.is_piercing() and not arrow.passes_world() for arrow in arrows),
              'all R lanes pierce targets while retaining world collision')
    rig.data['r_arrow_release'] = {'elapsed_from_activation': release - activated,
        'arrows': [{'name': arrow.get_name(), 'direction': xyz(arrow.get_flight_direction()),
                    'position': xyz(arrow.get_actor_location())} for arrow in arrows]}
    yield 1.0 / fps
    rig.snapshot()
    rig.check(len(rig.latest['projectiles']) == 3,
              'the field release screenshot contains all three live R projectiles')
    rig.check(rig.latest.get('montage_sequence') == 'R_Ability_Med_Fire',
              'the actual buffed field attack uses the dedicated R firing sequence')
    rig.check(bool(effects(rig, 'Sparrow_UltArrow')),
              'the field R lanes have active original ultimate-arrow trail particles')
    yield rig.capture('field-r-three-arrows')
    yield rig.until(lambda: rig.health(target) < 100.0, 1.2,
                    'the aimed R lane applies actual collision damage on the original field')
    basic_damage = rig.component.get_editor_property('basic_attack_damage')
    rig.check(abs(rig.health(target) - (100.0 - basic_damage)) < 0.01,
              'the central R lane applies one configured basic hit to its fresh target')
    yield rig.until(lambda: not rig.component.is_inner_fire_active(), 4.5,
                    'the field R buff expires through its real four-second timer')
    yield rig.idle()
    yield 0.8
    rig.snapshot()
    rig.check(not rig.arrows() and not any(row['active'] or row['particles'] > 0
                                        for row in rig.latest['effects']),
              'expired field R leaves no owned live projectile or persistent FX')


def rogue_source_appearance(rig):
    yield rig.idle()
    yield 0.3
    source = unreal.load_asset(profile['expected']['mesh'])
    rig.check(rig.mesh.get_editor_property('skeletal_mesh_asset') == source,
              'actual field appearance uses the untouched original Rogue mesh')
    slots = source.get_editor_property('materials')
    assignments = []
    for index, slot in enumerate(slots):
        original = slot.get_editor_property('material_interface')
        actual = rig.mesh.get_material(index)
        parent = actual.get_editor_property('parent') if isinstance(actual, unreal.MaterialInstance) else None
        item = {'slot': str(slot.get_editor_property('material_slot_name')),
                'source': original.get_path_name() if original else None,
                'actual': actual.get_path_name() if actual else None,
                'runtime_parent': parent.get_path_name() if parent else None,
                'vector_changes': {}, 'scalar_changes': {}}
        if isinstance(actual, unreal.MaterialInstanceDynamic) and isinstance(original, unreal.Material):
            library = unreal.MaterialEditingLibrary
            for name in library.get_vector_parameter_names(original):
                expected = library.get_material_default_vector_parameter_value(original, name)
                value = actual.get_vector_parameter_value(name)
                expected = [expected.r, expected.g, expected.b, expected.a]
                value = [value.r, value.g, value.b, value.a]
                if any(abs(a - b) > 0.00001 for a, b in zip(expected, value)):
                    item['vector_changes'][str(name)] = {'source': expected, 'actual': value}
            for name in library.get_scalar_parameter_names(original):
                expected = library.get_material_default_scalar_parameter_value(original, name)
                value = actual.get_scalar_parameter_value(name)
                if abs(expected - value) > 0.00001:
                    item['scalar_changes'][str(name)] = {'source': expected, 'actual': value}
        assignments.append(item)
    rig.data['appearance_material_assignments'] = assignments
    for index, item in enumerate(assignments):
        rig.check(item['source'] is not None and item['source'] in (item['actual'], item['runtime_parent']),
                  'field material or its runtime instance inherits source Rogue material: ' + str(index))
        rig.check(not item['vector_changes'], 'field material preserves authored color parameters: ' + str(index))
    arm = rig.pawn.get_component_by_class(unreal.SpringArmComponent)
    camera = rig.pawn.get_component_by_class(unreal.CameraComponent)
    names = ('target_arm_length', 'relative_rotation', 'target_offset',
             'enable_camera_lag', 'enable_camera_rotation_lag', 'do_collision_test')
    saved = {name: arm.get_editor_property(name) for name in names}
    rotation = saved['relative_rotation']
    saved['relative_rotation'] = unreal.Rotator(pitch=rotation.pitch, yaw=rotation.yaw, roll=rotation.roll)
    offset = saved['target_offset']
    saved['target_offset'] = unreal.Vector(x=offset.x, y=offset.y, z=offset.z)
    saved_fov = camera.get_editor_property('field_of_view')
    rear_yaw = rig.pawn.get_actor_rotation().yaw + 20.0
    front_yaw = rear_yaw + 180.0
    raw = None
    try:
        arm.set_editor_property('target_arm_length', 450.0)
        arm.set_editor_property('relative_rotation', unreal.Rotator(pitch=-10, yaw=rear_yaw, roll=0))
        arm.set_editor_property('target_offset', unreal.Vector(x=0, y=0, z=10))
        arm.set_editor_property('enable_camera_lag', False)
        arm.set_editor_property('enable_camera_rotation_lag', False)
        arm.set_editor_property('do_collision_test', False)
        camera.set_editor_property('field_of_view', 40.0)
        yield 0.2
        yield rig.capture('field-rogue-back-closeup')
        raw = rig.spawn(unreal.SkeletalMeshActor, rig.mesh.get_world_location())
        raw.set_actor_rotation(rig.mesh.get_world_rotation(), True)
        raw.set_actor_scale3d(rig.mesh.get_world_scale())
        raw_mesh = raw.get_component_by_class(unreal.SkeletalMeshComponent)
        raw_mesh.set_skeletal_mesh_asset(source)
        raw_mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        raw_mesh.set_leader_pose_component(rig.mesh, True, False)
        raw_mesh.bind_cloth_to_leader_pose_component()
        rig.mesh.set_visibility(False, True)
        yield 0.2
        yield rig.capture('field-original-rogue-back-same-lighting')
        raw.destroy_actor()
        rig.fixtures.remove(raw)
        raw = None
        rig.mesh.set_visibility(True, True)
        arm.set_editor_property('relative_rotation', unreal.Rotator(pitch=-10, yaw=front_yaw, roll=0))
        yield 0.2
        yield rig.capture('field-rogue-front-closeup')
        rig.data['appearance'] = {'source_mesh': source.get_path_name(), 'materials': assignments,
            'comparison': 'Original Rogue asset and configured pawn, same field, lighting and current pose',
            'closeup_camera_yaw': {'rear': rear_yaw, 'front': front_yaw},
            'source_game_lighting_fidelity_claimed': False,
            'closeup_camera_changes_are_pie_only': True}
    finally:
        rig.mesh.set_visibility(True, True)
        if raw is not None and valid(raw):
            raw.destroy_actor()
        for name, value in saved.items():
            arm.set_editor_property(name, value)
        camera.set_editor_property('field_of_view', saved_fov)


class FieldPresentationRunner(SwitchRunner):
    def __init__(self):
        Runner.__init__(self, 'sparrow_field_presentation', [
            ('original_field_two_selection', select_sparrow),
            ('q_arrow_rain', q_arrow_rain), ('w_charge_and_release', w_charge_and_release),
            ('e_passive_feedback_and_stacks', e_passive_feedback_and_stacks),
            ('r_cast_buff_and_three_arrows', r_cast_buff_and_three_arrows),
            ('rogue_source_material_and_visual_comparison', rogue_source_appearance)])
        self.selected_pawn = None
        self.report.update(map=ORIGINAL_MAP, profile_map_ignored=profile['map'],
            pawn_respawn_between_cases=False, input='actual_controller_Two_Q_W_E_R_and_left_click',
            physical_input_tested=False, world_settings_saved=False,
            visual_acceptance='actual saved viewport images require separate visual review')

    def case_generator(self, factory):
        yield from super().case_generator(factory)
        rig = self.rig
        rig.check(rig.pawn == self.selected_pawn and valid(self.selected_pawn),
                  'all field presentation cases retain the actual selected Sparrow pawn')
        rig.check(field_meshes(rig.world) == self.original_field,
                  'field presentation preserves original field actors and their transforms')
        rig.check(rig.snapshot()['audio_components'] == 0,
                  'field presentation keeps the audio engine free of spawned audio components')


if __name__ == '__main__':
    runtime = FieldPresentationRunner()
    runtime.start()
