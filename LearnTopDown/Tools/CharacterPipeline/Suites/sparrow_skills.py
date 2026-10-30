"""Sparrow Q/W/E/R behavior, retained passive damage and independent lifetimes."""
import math
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from sparrow_runtime import run, distance2d, valid, xyz, assert_bow_effect_attachment

Q = unreal.SparrowSkill.HAIL_OF_ARROWS
W = unreal.SparrowSkill.PIERCING_SHOT
E = unreal.SparrowSkill.RELENTLESS
R = unreal.SparrowSkill.INNER_FIRE


def damage(rig, slot):
    return rig.component.get_editor_property('skills')[slot].get_editor_property('damage')


def assert_open_hail_path(rig, source, target):
    ignored = list(unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.Pawn))
    ignored.extend(unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.KwangTrainingDummy))
    result = unreal.SystemLibrary.line_trace_single(rig.world, source, target.get_actor_location(),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored, unreal.DrawDebugTrace.NONE, True)
    values = result if isinstance(result, tuple) else (result,)
    flags = [value for value in values if isinstance(value, bool)]
    hits = [value for value in values if isinstance(value, unreal.HitResult)]
    if flags:
        blocked = flags[0]
    elif hits:
        blocked = bool(hits[0].get_editor_property('blocking_hit'))
    elif result is None:
        blocked = False
    else:
        raise RuntimeError('Unrecognized native visibility-trace return contract')
    rig.check(not blocked, 'Q radius fixture has an actual unobstructed ground-to-target visibility path')
    rig.data.setdefault('q_radius_visibility', []).append({'from': xyz(source),
        'to': xyz(target.get_actor_location()), 'blocked': blocked,
        'trace_complex': False, 'ignored': 'all Pawn and KwangTrainingDummy'})


def arrow_capsule_geometry(arrow, center, radius, half_height):
    origin = arrow.get_actor_location()
    direction = arrow.get_flight_direction()
    remaining = arrow.get_remaining_range()
    axis_half = half_height - radius
    xy_squared = direction.x * direction.x + direction.y * direction.y
    candidates = [0.0, remaining]
    if xy_squared > 0.000001:
        candidates.append(((center.x - origin.x) * direction.x +
                           (center.y - origin.y) * direction.y) / xy_squared)
    for endpoint_z in (center.z - axis_half, center.z + axis_half):
        candidates.append((center.x - origin.x) * direction.x + (center.y - origin.y) * direction.y +
                          (endpoint_z - origin.z) * direction.z)
    closest = float('inf')
    nearest_point = None
    for distance in candidates:
        distance = max(0.0, min(remaining, distance))
        point = origin + direction * distance
        axis_z = max(center.z - axis_half, min(center.z + axis_half, point.z))
        separation = math.dist(xyz(point), [center.x, center.y, axis_z])
        if separation < closest:
            closest, nearest_point = separation, point
    return {'target_center': xyz(center), 'capsule_radius': radius,
            'capsule_axis_half_height': axis_half, 'ray_capsule_axis_distance': closest,
            'closest_ray_point': xyz(nearest_point)}


def assert_arrow_crosses_capsules(rig, arrow, targets, data_key='charged_arrow_capsule_geometry'):
    rows = []
    for target in targets:
        capsule = target.get_component_by_class(unreal.CapsuleComponent)
        row = arrow_capsule_geometry(arrow, target.get_actor_location(), capsule.get_scaled_capsule_radius(),
                                     capsule.get_scaled_capsule_half_height())
        rows.append(row)
        rig.data[data_key] = {'ray_origin': xyz(arrow.get_actor_location()),
            'ray_direction': xyz(arrow.get_flight_direction()), 'remaining_range': arrow.get_remaining_range(),
            'targets': rows}
        rig.check(row['ray_capsule_axis_distance'] <= row['capsule_radius'] + 0.001,
                  'actual charged-arrow center trajectory intersects the intended target capsule')


def q_area_ticks(rig):
    center = rig.dummy(600)
    # 경사면 옆의 낮은 바닥은 지형에 가려진다. 반경 검사는 경사면의 진행 방향에서 분리한다.
    inside = rig.dummy(820)
    outside = rig.dummy(980)
    center_ground = rig.ground(600)
    rig.check(distance2d(center_ground, inside.get_actor_location()) < 300.0,
              'uncovered positive fixture lies inside the 300 cm Q radius')
    rig.check(distance2d(center_ground, outside.get_actor_location()) > 300.0,
              'uncovered negative fixture lies outside the 300 cm Q radius')
    for target in (inside, outside):
        assert_open_hail_path(rig, center_ground + unreal.Vector(x=0, y=0, z=70), target)
    yield from rig.skill_key('Q', center.get_actor_location())
    rig.check(rig.component.is_casting(), 'Q controller binding starts its cast')
    rig.check(not rig.pawn.try_basic_attack(center.get_actor_location()), 'active Q cast excludes a concurrent bow attack')
    yield 4.75
    total = damage(rig, 0)
    rig.check(abs(rig.health(center) - (100.0 - total)) < 0.01 and
              abs(rig.health(inside) - (100.0 - total)) < 0.01, 'eight Q pulses apply the configured damage inside the area')
    rig.check(rig.health(outside) == 100.0, 'Q does not damage a target outside its 300 cm radius')
    changes = [event for event in rig.events if event['before'] and event['after'] and
               event['before'][0] is not None and event['after'][0] is not None and
               event['after'][0] < event['before'][0]]
    rig.check(len(changes) == 8, 'PIE health samples observe exactly eight separate Q pulses')
    intervals = [right['time'] - left['time'] for left, right in zip(changes, changes[1:])]
    rig.check(all(abs(interval - 0.5) <= 0.08 for interval in intervals), 'Q pulse intervals are 0.5 seconds at this frame rate')
    rig.check(rig.component.get_active_hail_count() == 0, 'the four-second arrow rain removes its zone')
    rig.check(rig.component.get_relentless_stacks(center) == 8, 'Q damage records passive stacks without applying basic-attack bonus')
    rig.check(rig.component.get_cooldown_remaining(Q) > 0 and
              not rig.component.try_use_skill(Q, center.get_actor_location(), center), 'Q cannot bypass its configured cooldown')
    rig.assert_recovered()
    rig.data.update(pulse_times=[event['time'] for event in changes], pulse_intervals=intervals, total_damage=total)


def q_invalid(kind):
    def case(rig):
        target = rig.dummy(650 if kind == 'wall' else 1700)
        if kind == 'wall':
            rig.wall(250)
        accepted = rig.component.try_use_skill(Q, target.get_actor_location(), target)
        rig.check(not accepted, 'Q rejects ' + kind + ' placement')
        yield 0.6
        rig.check(rig.health(target) == 100.0 and rig.component.get_active_hail_count() == 0,
                  'rejected Q creates no damaging area')
        rig.check(rig.component.get_cooldown_remaining(Q) == 0.0, 'rejected Q does not consume cooldown')
        rig.assert_recovered()
    return case


def q_cover(rig):
    front = rig.dummy(550)
    covered = rig.dummy(800)
    rig.wall(700)
    rig.check(rig.component.try_use_skill(Q, rig.ground(550), front), 'Q can be placed before an obstacle')
    yield 4.7
    rig.check(abs(rig.health(front) - (100.0 - damage(rig, 0))) < 0.01, 'Q damages the uncovered target')
    rig.check(rig.health(covered) == 100.0, 'Q area pulses respect cover inside the radius')


def q_interrupt(after):
    def case(rig):
        target = rig.dummy(550)
        rig.check(rig.component.try_use_skill(Q, rig.ground(550), target), 'Q starts before interruption')
        if after:
            yield rig.until(lambda: rig.component.get_active_hail_count() > 0, 1.0, 'Q area exists before interruption')
        else:
            yield 0.12
        rig.interrupt()
        yield 4.55 if after else 0.8
        expected = 100.0 - damage(rig, 0) if after else 100.0
        rig.check(abs(rig.health(target) - expected) < 0.01,
                  'released Q persists after cast cancellation' if after else 'Q cancellation before release causes zero damage')
        rig.check(rig.component.get_active_hail_count() == 0, 'interrupted Q leaves no expired zone')
        rig.assert_recovered()
    return case


def q_target_destroyed(rig):
    target = rig.dummy(550)
    survivor = rig.dummy(550, 150)
    rig.check(rig.component.try_use_skill(Q, rig.ground(550), target), 'ground-area Q starts with a target fixture')
    yield rig.until(lambda: rig.component.get_active_hail_count() > 0, 1.0, 'arrow rain exists before its initial target disappears')
    target.destroy_actor()
    yield 4.4
    rig.check(abs(rig.health(survivor) - (100.0 - damage(rig, 0))) < 0.01,
              'ground-area Q keeps damaging surviving actors after its initial target is destroyed')
    rig.check(rig.component.get_active_hail_count() == 0, 'Q expires after target destruction')


def q_owner_cleanup(rig):
    target = rig.dummy(550)
    rig.check(rig.component.try_use_skill(Q, rig.ground(550), target), 'Q starts before shooter destruction')
    yield rig.until(lambda: rig.component.get_active_hail_count() > 0, 1.0, 'Q area is active before its owner is destroyed')
    before = rig.health(target)
    rig.pawn.destroy_actor()
    rig.replace_destroyed_player()
    yield 1.15
    rig.check(rig.health(target) == before, 'owner destruction clears future arrow-rain damage timers')
    rig.check(not rig.arrows(), 'owner destruction leaves no active projectiles')
    rig.check(not any(effect['active'] or effect['particles'] > 0 for effect in rig.latest['effects']),
              'destroyed Q owner leaves no active owned particles')
    rig.check(rig.component.get_active_hail_count() == 0, 'replacement pawn has no inherited arrow-rain state')


def w_charge_and_pierce(rig):
    first = rig.dummy(550)
    second = rig.dummy(950)
    yield from rig.skill_key('W', second.get_actor_location())
    rig.check(rig.component.is_casting(), 'W controller binding starts charging')
    for wait in (0.1, 0.15, 0.15):
        yield wait
        assert_bow_effect_attachment(rig, 'P_Sparrow_RMB')
    rig.check(rig.health(first) == rig.health(second) == 100.0 and not rig.arrows(),
              'W does not fire or apply damage before its half-second charge completes')
    yield rig.until(lambda: bool(rig.arrows()), 0.6, 'W charge releases a projectile')
    arrow = rig.arrows()[0]
    assert_arrow_crosses_capsules(rig, arrow, (first, second))
    rig.check(arrow.is_piercing() and arrow.passes_world(), 'W arrow explicitly pierces targets and world obstacles')
    rig.check(abs(arrow.get_flight_speed() - 4000.0) < 0.01, 'charged W arrow flies at its configured speed')
    release = rig.now
    yield 0.8
    expected = 100.0 - damage(rig, 1)
    rig.check(abs(rig.health(first) - expected) < 0.01 and abs(rig.health(second) - expected) < 0.01,
              'one W arrow damages both aligned targets once')
    rig.check(rig.component.get_relentless_stacks(first) == 1 and rig.component.get_relentless_stacks(second) == 1,
              'W records passive stacks for each pierced target')
    yield rig.idle()
    rig.check(rig.component.get_cooldown_remaining(W) > 0 and
              not rig.component.try_use_skill(W, first.get_actor_location(), first), 'W repeat input cannot bypass cooldown after recovery')
    rig.assert_recovered()
    rig.data['observed_release_time'] = release


def w_world_and_direction(rig):
    first = rig.dummy(0, 700)
    second = rig.dummy(0, 1100)
    rig.wall(0, 350, dynamic=True)
    rig.check(rig.component.try_use_skill(W, second.get_actor_location(), second), 'W starts toward a non-default world direction')
    yield rig.until(lambda: bool(rig.arrows()), 1.5, 'charged arrow exists behind the world-passing test')
    arrow = rig.arrows()[0]
    direction = arrow.get_flight_direction()
    xy_length = math.hypot(direction.x, direction.y)
    rig.check(xy_length > 0 and direction.y / xy_length > 0.99,
              'W projectile horizontal heading follows +Y while preserving its vertical aim')
    assert_arrow_crosses_capsules(rig, arrow, (first, second))
    yield 1.0
    expected = 100.0 - damage(rig, 1)
    rig.check(abs(rig.health(first) - expected) < 0.01 and abs(rig.health(second) - expected) < 0.01,
              'W crosses a dynamic world wall and damages both targets beyond it')


def w_interrupt(after):
    def case(rig):
        target = rig.dummy(950)
        rig.check(rig.component.try_use_skill(W, target.get_actor_location(), target), 'W starts before cast interruption')
        if after:
            yield rig.until(lambda: bool(rig.arrows()), 1.5, 'W arrow is released before its animation is interrupted')
        else:
            yield 0.35
        rig.interrupt()
        yield 1.0
        expected = 100.0 - damage(rig, 1) if after else 100.0
        rig.check(abs(rig.health(target) - expected) < 0.01,
                  'released W arrow continues after cancellation' if after else 'interrupted W charge causes zero damage')
        rig.assert_recovered()
    return case


def e_passive_stacks_and_expiry(rig):
    target = rig.dummy(550)
    rig.check(not rig.latest['slots'][2]['passive'], 'E is active while Relentless remains an independent passive')
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'first basic attack starts passive integration test')
    yield rig.until(lambda: rig.health(target) < 100.0, 1.2, 'first basic attack collides with its target')
    rig.check(rig.component.get_relentless_stacks(target) == 1, 'first collision creates one passive stack')
    yield rig.idle()
    yield 0.35
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'second attack starts after recovery and restart cooldown')
    yield rig.until(lambda: rig.component.get_relentless_stacks(target) == 2, 1.2, 'second collision increases the same-target stack')
    rig.check(abs(rig.health(target) - 59.65) < 0.01, 'existing stack increases the second 20-damage attack by 1.75 percent')
    other = rig.dummy(850, 250)
    rig.check(rig.component.get_relentless_stacks(other) == 0, 'passive stacks belong to the individual target')
    yield 5.2
    rig.check(rig.component.get_relentless_stacks(target) == 0, 'passive stacks expire five seconds after the last hit')
    rig.assert_recovered()


def r_five_lanes_and_expiry(rig):
    yield from rig.skill_key('R', rig.point(700))
    yield rig.until(rig.component.is_inner_fire_active, 0.5, 'R controller input activates Inner Fire')
    rig.check(rig.component.get_buff_remaining() > 9.7, 'Inner Fire starts with a ten-second duration')
    yield rig.idle()
    rig.assert_recovered()
    start = rig.pawn.get_actor_location()
    yield from rig.click('Right', rig.ground(0, 250))
    yield 0.6
    rig.check(distance2d(start, rig.pawn.get_actor_location()) > 100.0 and rig.component.is_inner_fire_active(),
              'Sparrow moves while the independent Inner Fire buff remains active')
    buff_effects = [effect for effect in rig.latest['effects'] if 'P_SparrowBuff' in effect['template'] and effect['active']]
    bow_follow = assert_bow_effect_attachment(rig, 'P_SparrowBuff')
    rig.data['inner_fire_movement_follow'] = {'pawn_position': xyz(rig.pawn.get_actor_location()),
        'bow_position': bow_follow['bow_position'],
        'buff_positions': [effect['position'] for effect in buff_effects],
        'travel_cm': distance2d(start, rig.pawn.get_actor_location())}
    rig.controller.stop_movement()
    rig.movement.stop_movement_immediately()
    rig.check(rig.component.fire_basic_attack(unreal.Vector(x=1, y=0, z=0)), 'buffed bow emits its projectiles')
    arrows = rig.arrows()
    rig.check(len(arrows) == 5, 'Inner Fire emits one central and four side arrows')
    headings = sorted(math.degrees(math.atan2(a.get_flight_direction().y, a.get_flight_direction().x)) for a in arrows)
    rig.check(all(abs(a - b) < 0.01 for a, b in zip(headings, [-24.0, -12.0, 0.0, 12.0, 24.0])), 'Inner Fire side arrows spread by twelve degrees')
    ray_targets = []
    lane_targets = []
    for lane, arrow in enumerate(arrows):
        direction = arrow.get_flight_direction()
        rig.check(arrow.is_piercing() and not arrow.passes_world(), 'Inner Fire arrows pierce targets and remain blocked by terrain')
        expected_damage = 20.0 if abs(direction.y) < 0.01 else 5.0
        near_destination = arrow.get_actor_location() + direction * 300.0
        near = rig.dummy_at_ground(near_destination.x, near_destination.y)
        capsule = near.get_component_by_class(unreal.CapsuleComponent)
        radius, half_height = capsule.get_scaled_capsule_radius(), capsule.get_scaled_capsule_half_height()
        candidates = []
        selected = None
        for distance in (420.0, 410.0, 400.0, 390.0, 380.0, 375.0, 372.0):
            destination = arrow.get_actor_location() + direction * distance
            probe = rig.ground_probe(destination.x, destination.y)
            entry = {'distance': distance, 'ground_hit': probe['ground_hit']}
            candidates.append(entry)
            if not probe['ground_hit'] or probe['normal_z'] < 0.55:
                continue
            ground = probe['ground']
            center = unreal.Vector(x=ground['x'], y=ground['y'], z=ground['z'] + half_height)
            own = arrow_capsule_geometry(arrow, center, radius, half_height)
            other_paths = []
            for other in arrows:
                if other == arrow:
                    continue
                other_geometry = arrow_capsule_geometry(other, center, radius, half_height)
                other_paths.append({'axis_distance': other_geometry['ray_capsule_axis_distance'],
                                    'expanded_radius': radius + other.get_editor_property('collision_radius')})
            distinct = distance2d(center, near.get_actor_location()) > radius * 2.0 + 0.001
            own_intersects = own['ray_capsule_axis_distance'] <= radius + 0.001
            neighbors_clear = all(path['axis_distance'] > path['expanded_radius'] + 0.001 for path in other_paths)
            entry.update(ground=ground, center=xyz(center), geometry=own, other_paths=other_paths,
                         distinct_capsules=distinct, own_intersects=own_intersects, neighbors_clear=neighbors_clear)
            if distinct and own_intersects and neighbors_clear:
                selected = center
                break
        rig.data.setdefault('r_grounded_far_candidates', []).append({'lane': lane, 'candidates': candidates})
        rig.check(selected is not None, 'R piercing fixture has a second distinct grounded capsule on its actual ray')
        far = rig.dummy_at_ground(selected.x, selected.y)
        assert_arrow_crosses_capsules(rig, arrow, (near, far), data_key=f'r_lane_{lane}_capsule_geometry')
        lane_targets.append((arrow, (near, far)))
        ray_targets.extend([(near, expected_damage), (far, expected_damage)])
    neighboring_paths = []
    for own_arrow, targets in lane_targets:
        for target in targets:
            capsule = target.get_component_by_class(unreal.CapsuleComponent)
            for other in arrows:
                if other == own_arrow:
                    continue
                geometry = arrow_capsule_geometry(other, target.get_actor_location(),
                    capsule.get_scaled_capsule_radius(), capsule.get_scaled_capsule_half_height())
                limit = capsule.get_scaled_capsule_radius() + other.get_editor_property('collision_radius')
                neighboring_paths.append({'target': xyz(target.get_actor_location()),
                    'other_heading': xyz(other.get_flight_direction()),
                    'axis_distance': geometry['ray_capsule_axis_distance'], 'combined_collision_radius': limit})
                rig.data['r_neighboring_ray_clearances'] = neighboring_paths
                rig.check(geometry['ray_capsule_axis_distance'] > limit + 0.001,
                          'neighboring R projectiles cannot collide with another lane target capsule')
    rig.data['arrow_headings_degrees'] = headings
    rig.data['ray_target_positions'] = [xyz(actor.get_actor_location()) for actor, _ in ray_targets]
    yield 0.6
    rig.check(all(abs(rig.health(actor) - (100.0 - expected)) < 0.01 for actor, expected in ray_targets),
              'all five R lanes damage two aligned targets each, with quarter damage on side arrows')
    yield rig.component.get_buff_remaining() + 0.25
    rig.check(not rig.component.is_inner_fire_active(), 'Inner Fire expires without keeping the movement lock')
    rig.check(rig.component.fire_basic_attack(unreal.Vector(x=0, y=-1, z=0)), 'normal attack is available after the buff expires')
    rig.check(len(rig.arrows()) == 1 and not rig.arrows()[0].is_piercing(), 'expired Inner Fire restores the single normal arrow')


def r_interrupt(after):
    def case(rig):
        rig.check(rig.component.try_use_skill(R, rig.point(700), None), 'R starts before interruption')
        if after:
            yield rig.until(rig.component.is_inner_fire_active, 0.5, 'Inner Fire is active before cast interruption')
        else:
            yield 0.035
        rig.interrupt()
        yield 0.4
        rig.check(rig.component.is_inner_fire_active() == after,
                  'activated R buff survives cancellation' if after else 'pre-action R cancellation does not activate a buff')
        rig.assert_recovered()
        if after:
            yield rig.component.get_buff_remaining() + 0.2
            rig.check(not rig.component.is_inner_fire_active(), 'cancelled R cast leaves no permanent buff')
    return case


runtime = run('sparrow_skills', [
    ('q_controller_area_eight_pulses', q_area_ticks), ('q_out_of_range', q_invalid('range')),
    ('q_cast_blocked_by_wall', q_invalid('wall')), ('q_pulses_respect_cover', q_cover),
    ('q_interrupt_before_release', q_interrupt(False)), ('q_interrupt_after_release', q_interrupt(True)),
    ('q_target_destroyed', q_target_destroyed), ('q_owner_destroyed', q_owner_cleanup),
    ('w_controller_charge_and_pierce', w_charge_and_pierce), ('w_world_pass_and_direction', w_world_and_direction),
    ('w_interrupt_before_release', w_interrupt(False)), ('w_interrupt_after_release', w_interrupt(True)),
    ('e_passive_stacks_and_expiry', e_passive_stacks_and_expiry),
    ('r_controller_five_lanes_move_and_expiry', r_five_lanes_and_expiry),
    ('r_interrupt_before_activation', r_interrupt(False)), ('r_interrupt_after_activation', r_interrupt(True))])
