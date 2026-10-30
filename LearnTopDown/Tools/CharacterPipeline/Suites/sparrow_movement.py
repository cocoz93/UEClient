"""Sparrow locomotion, actual foot poses and controller movement recovery."""
import math
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from sparrow_runtime import run, distance2d


def foot_motion(samples):
    return max((math.dist(left['feet'][bone], right['feet'][bone])
                for left, right in zip(samples, samples[1:]) for bone in ('foot_l', 'foot_r')), default=0.0)


def move_and_stop(rig):
    goal = rig.ground(0, 650)
    yield from rig.click('Right', goal)
    selected_goal = rig.assert_cursor_goal(goal)
    yield 1.9
    trace = rig.trace
    moving = [sample for sample in trace if sample['speed'] > 50]
    rig.check(moving, 'right-click starts physical character movement')
    peak = max(sample['speed'] for sample in trace)
    rig.check(abs(peak - 600.0) < 12.0, 'walking speed reaches the configured 600 cm/s')
    rig.check(distance2d(rig.pawn.get_actor_location(), selected_goal) < 22.0, 'navigation arrives at the actual selected field point')
    rig.check(abs((rig.pawn.get_actor_rotation().yaw - 90.0 + 180.0) % 360.0 - 180.0) < 10.0,
              'character rotates toward its movement direction')
    rig.check(foot_motion(moving) > 0.5, 'actual foot bone positions animate while running')
    rig.check(max(sample.get('run_weight', 0.0) for sample in moving) > 0.5,
              'Sparrow run state contributes to the moving pose')
    rig.check(rig.latest['speed'] < 1.0 and rig.latest.get('run_weight', 1.0) < 0.05,
              'velocity and run pose return to idle after arrival')
    stopped = [sample for sample in trace if sample['elapsed'] > 1.65]
    rig.check(foot_motion(stopped) < 15.0, 'actual feet do not jump between run and idle after stopping')
    rig.data.update(peak_speed=peak, moving_foot_step_cm=foot_motion(moving),
                    stopped_foot_step_cm=foot_motion(stopped), final_goal_distance=distance2d(rig.pawn.get_actor_location(), selected_goal))


def repeat_near(rig):
    goal = rig.ground(0, 55)
    start = rig.pawn.get_actor_location()
    for _ in range(10):
        yield from rig.click('Right', goal)
        yield 0.08
    yield 0.4
    rig.check(distance2d(start, rig.pawn.get_actor_location()) < 110.0,
              'near repeated clicks do not send Sparrow beyond the nearby goal')
    rig.check(rig.latest['speed'] < 1.0 and rig.latest.get('run_weight', 1.0) < 0.05,
              'repeated near input settles in the actual idle pose')
    edges = list(zip(rig.trace, rig.trace[1:]))
    restarts = sum(a['speed'] <= 1 < b['speed'] for a, b in edges)
    rig.check(restarts <= 2, 'repeated near input does not repeatedly restart locomotion')
    rig.data.update(speed_restarts=restarts, final_speed=rig.latest['speed'], foot_pose_step_cm=foot_motion(rig.trace))


def held_follow(rig):
    start = rig.pawn.get_actor_location()
    rig.mouse('Press', 'Right', rig.ground(0, 74))
    for _ in range(30):
        position = rig.pawn.get_actor_location()
        rig.mouse('Move', 'Right', rig.ground_absolute(position.x, position.y + 74))
        yield 1.0 / 30.0
    position = rig.pawn.get_actor_location()
    rig.mouse('Release', 'Right', rig.ground_absolute(position.x, position.y + 74))
    yield 0.7
    moving = [sample for sample in rig.trace if 0.12 < sample['elapsed'] < 0.9]
    rig.check(distance2d(start, rig.pawn.get_actor_location()) > 120.0,
              'held right input follows a nearby moving cursor goal')
    rig.check(sum(sample['speed'] > 20 for sample in moving) >= len(moving) * 0.8,
              'held near input maintains movement across frame boundaries')
    rig.check(foot_motion(moving) > 0.5, 'held movement advances actual foot poses')
    rig.check(rig.latest['speed'] < 1.0, 'released right input finishes its last navigation request')
    rig.data['travel_cm'] = distance2d(start, rig.pawn.get_actor_location())


def attack_then_move(rig):
    target = rig.dummy(400)
    yield from rig.click('Left', target.get_actor_location())
    rig.check(rig.pawn.is_attacking(), 'left controller input starts the bow attack')
    yield rig.idle()
    rig.assert_recovered()
    start = rig.pawn.get_actor_location()
    yield from rig.click('Right', rig.ground(0, 300))
    yield 0.65
    rig.check(distance2d(start, rig.pawn.get_actor_location()) > 150.0,
              'right controller input moves Sparrow after attack recovery')
    rig.check(foot_motion([sample for sample in rig.trace if sample['speed'] > 20]) > 0.5,
              'locomotion bones animate again after the bow montage')
    rig.check(rig.health(target) < 100.0, 'the recovered attack actually hit its target')


runtime = run('sparrow_movement', [('move_rotate_stop', move_and_stop), ('repeat_near_goal', repeat_near),
                                  ('held_near_follow', held_follow), ('attack_then_move', attack_then_move)])
