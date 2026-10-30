"""Ranged basic attacks tested by flight, collision, health and interruption."""
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from sparrow_runtime import run, valid
from context import profile


def single_flight(rig):
    target = rig.dummy(800)
    yield from rig.click('Left', target.get_actor_location())
    rig.check(rig.health(target) == 100.0, 'controller attack does not apply instant ranged damage')
    yield rig.until(lambda: bool(rig.arrows()), 1.0, 'bow release creates a flying arrow')
    rig.check(rig.health(target) == 100.0, 'released arrow has not damaged a distant target before arrival')
    arrow = rig.arrows()[0]
    origin = arrow.get_actor_location()
    rig.check(not arrow.is_piercing() and not arrow.passes_world(), 'normal arrows stop on targets and walls')
    yield 0.06
    rig.check(not valid(arrow) or arrow.get_actor_location().x > origin.x,
              'the actual projectile advances toward the cursor direction')
    yield 0.7
    rig.check(abs(rig.health(target) - 80.0) < 0.01, 'first arrow collision applies exactly the configured 20 damage')
    rig.check(not rig.arrows(), 'normal arrow is removed after its first collision')
    yield 0.45
    rig.check(abs(rig.health(target) - 80.0) < 0.01, 'one arrow never applies duplicate damage')
    rig.assert_recovered()
    rig.check(any(sample['projectiles'] for sample in rig.trace), 'PIE state recorded the projectile before impact')
    rig.data['damage_events'] = rig.events


def first_target(rig):
    first = rig.dummy(450)
    behind = rig.dummy(800)
    rig.check(rig.pawn.try_basic_attack(first.get_actor_location()), 'basic attack starts toward aligned targets')
    yield 1.15
    rig.check(abs(rig.health(first) - 80.0) < 0.01, 'the nearest target receives the arrow')
    rig.check(rig.health(behind) == 100.0, 'a normal arrow does not pass its first target')
    rig.check(not rig.arrows(), 'first-target collision cleans the projectile')


def blocked(dynamic):
    def case(rig):
        target = rig.dummy(650)
        rig.wall(260, dynamic=dynamic)
        rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'attack toward an occluded target starts its animation')
        yield 1.1
        rig.check(rig.health(target) == 100.0, 'the obstacle prevents damage behind it')
        rig.check(not rig.arrows(), 'the arrow stops at the obstacle')
        observed = [arrow['position'][0] for sample in rig.trace for arrow in sample['arrow_state']]
        rig.check(observed and max(observed) < rig.origin.x + 280.0,
                  'projectile samples remain in front of the obstacle')
        rig.assert_recovered()
    return case


def small_target(rig):
    target = rig.dummy(650, small=True)
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'attack starts toward a narrow target')
    yield 1.0
    rig.check(abs(rig.health(target) - 80.0) < 0.01,
              'segment sweep catches a target with an 8.75 cm capsule radius at this frame rate')


def range_limit(rig):
    # 실제 지면이 없는 바깥 좌표에서는 지상 적을 만들지 않고 고공 궤적으로 사거리만 분리한다.
    target = rig.spawn(unreal.KwangTrainingDummy, rig.point(2100, 0, 1000))
    rig.targets.append(target)
    rig.data['fixture_scope'] = 'airborne range isolation; target is outside the ground field and above terrain'
    rig.data['target_position'] = [target.get_actor_location().x, target.get_actor_location().y, target.get_actor_location().z]
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'attack toward an out-of-range point can fire')
    yield rig.until(lambda: bool(rig.arrows()), 0.5, 'high flight path emits a range-test projectile')
    speed = rig.arrows()[0].get_flight_speed()
    yield 1.4
    rig.check(rig.health(target) == 100.0, 'arrows do not damage targets beyond their 1800 cm flight range')
    rig.check(not rig.arrows(), 'range exhaustion removes the projectile')
    distances = [arrow['distance'] for sample in rig.trace for arrow in sample['arrow_state']]
    rig.check(distances and max(distances) <= 1800.01, 'recorded flight never exceeds its configured range')
    near_limit = 1800.0 - speed / rig.runner.report['fixed_simulation_fps'] - 0.01
    rig.check(max(distances) >= near_limit,
              'projectile reaches within one simulation step of its flight limit before range expiry')
    rig.data.update(max_observed_flight_cm=max(distances), last_frame_range_lower_bound_cm=near_limit,
                    flight_speed_cm_per_second=speed)


def interrupt_before(rig):
    target = rig.dummy(600)
    yield from rig.click('Left', target.get_actor_location())
    rig.check(rig.pawn.is_attacking(), 'left controller input enters the bow attack before its timer fires')
    # 입력을 처리한 같은 프레임에서 중단한다. 30 FPS에서도 추가 프레임을 기다리지 않는다.
    rig.interrupt()
    yield 0.85
    rig.check(rig.health(target) == 100.0, 'interrupting the windup cancels its pending damage')
    rig.check(not any(sample['projectiles'] for sample in rig.trace), 'interrupting before release spawns no arrow')
    rig.assert_recovered()


def interrupt_after(rig):
    target = rig.dummy(950)
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'attack begins before release interruption')
    yield rig.until(lambda: bool(rig.arrows()), 1.0, 'arrow exists before the attack is interrupted')
    rig.interrupt()
    yield 0.8
    rig.check(abs(rig.health(target) - 80.0) < 0.01, 'a released arrow survives interruption of its bow animation')
    rig.assert_recovered()


def animation_replacement(rig):
    target = rig.dummy(700)
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'attack starts before animation replacement')
    yield min(0.04, rig.attack_metadata()['hit_delay'] * 0.2)
    rig.mesh.set_anim_instance_class(unreal.AnimInstance.static_class())
    yield rig.attack_metadata()['duration'] + 0.25
    rig.check(not rig.pawn.is_combat_busy(), 'recovery timer releases input when the old AnimInstance disappears')
    rig.check(rig.health(target) == 100.0 and not rig.arrows(), 'replacement cancels the old instance hit reservation')
    rig.mesh.set_anim_instance_class(unreal.load_class(None, profile['expected'].get('runtime_anim_class', profile['expected']['anim_class'])))
    yield 0.35
    rig.anim = rig.mesh.get_anim_instance()
    rig.anim.montage_stop(0.0)
    rig.assert_recovered()
    rig.check(rig.pawn.try_basic_attack(target.get_actor_location()), 'restored Sparrow AnimBP accepts a new attack')
    yield 1.0
    rig.check(rig.health(target) < 100.0, 'new AnimInstance attack produces real collision damage')


def owner_destroyed(rig):
    target = rig.dummy(900)
    rig.check(rig.component.fire_basic_attack(unreal.Vector(x=1, y=0, z=0)), 'arrow is emitted before owner destruction')
    arrows = list(rig.arrows())
    rig.check(len(arrows) == 1, 'the owner has one emitted projectile')
    rig.pawn.destroy_actor()
    yield 0.45
    rig.check(not any(valid(arrow) for arrow in arrows), 'destroying the shooter cleans its owned projectiles')
    rig.check(rig.health(target) == 100.0, 'an ownerless arrow does not damage the target')


def target_destroyed(rig):
    target = rig.dummy(900)
    rig.check(rig.component.fire_basic_attack(unreal.Vector(x=1, y=0, z=0)), 'arrow starts before target destruction')
    target.destroy_actor()
    yield 0.9
    rig.check(not rig.arrows(), 'a removed target leaves the arrow to expire by range')
    rig.assert_recovered()


def piercing_dedup(rig):
    target = rig.dummy(180)
    arrow = rig.spawn(unreal.SparrowArrow, rig.ground(50) + unreal.Vector(x=0, y=0, z=90))
    arrow.set_owner(rig.pawn)
    arrow.set_editor_property('instigator', rig.pawn)
    arrow.init_arrow(unreal.Vector(x=1, y=0, z=0), 20.0, 800.0, 200.0,
                     True, False, None, None, None)
    yield 1.4
    rig.check(abs(rig.health(target) - 80.0) < 0.01,
              'a slow piercing arrow damages an overlapping target once across multiple frames')
    rig.check(valid(arrow) and arrow.get_hit_count() == 1, 'one target is recorded once in projectile hit state')
    rig.check(rig.component.get_relentless_stacks(target) == 1, 'duplicate overlaps do not create passive stacks')


def rapid_clicks(rig):
    target = rig.dummy(800)
    for _ in range(4):
        yield from rig.click('Left', target.get_actor_location())
    yield 1.0
    rig.check(abs(rig.health(target) - 80.0) < 0.01, 'clicks during one bow attack do not queue duplicate arrows')
    rig.assert_recovered()


def falling_input(rig):
    target = rig.dummy(550)
    rig.movement.set_movement_mode(unreal.MovementMode.MOVE_FALLING)
    rig.check(not rig.pawn.try_basic_attack(target.get_actor_location()), 'falling state rejects a basic attack')
    rig.check(not rig.component.try_use_skill_slot(1, target.get_actor_location(), target), 'falling state rejects a charged skill')
    rig.check(rig.component.get_cooldown_remaining(unreal.SparrowSkill.PIERCING_SHOT) == 0.0,
              'falling skill rejection does not consume cooldown')
    rig.movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
    yield 0.2
    rig.check(rig.health(target) == 100.0 and not rig.arrows(), 'rejected falling input creates no collision damage')
    rig.assert_recovered()


runtime = run('sparrow_combat', [
    ('controller_flight_then_collision', single_flight), ('first_target_stops_arrow', first_target),
    ('static_wall', blocked(False)), ('dynamic_wall', blocked(True)), ('narrow_target', small_target),
    ('flight_range_limit', range_limit), ('interrupt_before_release', interrupt_before),
    ('interrupt_after_release', interrupt_after), ('animation_instance_replacement', animation_replacement),
    ('owner_destroyed', owner_destroyed), ('target_destroyed', target_destroyed),
    ('piercing_duplicate_overlap', piercing_dedup), ('rapid_controller_clicks', rapid_clicks),
    ('falling_input_rejected', falling_input)])
