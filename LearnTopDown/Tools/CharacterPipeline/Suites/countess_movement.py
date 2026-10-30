import hashlib
import json
import math
import time
import traceback
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
import sys
sys.path.insert(0, str(root / 'Tools/CharacterPipeline'))
from context import qa, fps, profile, protected, configure_practice
from navigation_ready import editor_navigation_ready
configure_practice(False)
expected_hashes = dict(protected)
animation_stop_grace = 0.0
installation = {'metadata': profile['basic_attack']}

mode = 'after'
assert mode in ('before', 'after')
cases = ([{'name': f'repeat_{d}', 'kind': 'repeat', 'distance': d} for d in (20, 30, 35, 40, 45, 50, 55, 60, 70, 80)] +
         [{'name': f'held_follow_{d}', 'kind': 'held_follow', 'distance': d} for d in (35, 40, 45, 50, 55, 60, 80)] +
         [{'name': f'held_fixed_{d}', 'kind': 'held_fixed', 'distance': d} for d in (45, 60, 80, 650)] +
         [{'name': 'same_goal_650', 'kind': 'same', 'distance': 650},
          {'name': 'goal_noise', 'kind': 'noise', 'distance': 100},
          {'name': 'cancel_near', 'kind': 'cancel', 'distance': 650},
          {'name': 'far_retarget', 'kind': 'retarget', 'distance': 650}])
if mode == 'after':
    cases += [{'name': f'{kind}_{d}', 'kind': kind, 'distance': d}
              for kind in ('repeat', 'held_follow') for d in (62, 65, 68, 71, 73, 74, 75, 76, 77, 90)]
if globals().get('trace_profile'):
    cases = [c for c in cases if c['name'] in ('repeat_20', 'repeat_45', 'repeat_73', 'repeat_74', 'held_follow_74', 'repeat_80')]
if True:
    cases = [c for c in cases if c['name'] in ('repeat_20', 'repeat_50', 'repeat_55', 'repeat_60',
        'repeat_73', 'repeat_74', 'repeat_75', 'repeat_80', 'held_follow_55', 'held_follow_74', 'held_follow_80',
        'held_fixed_80', 'held_fixed_650', 'cancel_near', 'far_retarget')]
state = {'phase': 'start', 'wall_start': time.monotonic(), 'index': 0, 'cases': [], 'release': False}

def mouse(world, action, point):
    unreal.SystemLibrary.execute_console_command(world, 'CountessComboQA.Mouse ' + action + ' Right ' +
        str(point.x) + ' ' + str(point.y) + ' ' + str(point.z))

def sample(world, elapsed):
    unreal.SystemLibrary.execute_console_command(world, 'CountessInputQA.State boundary-sample')
    result = json.loads((qa / 'boundary-sample.json').read_text(encoding='utf-8'))
    pawn, mesh = state['pawn'], state['mesh']
    p = pawn.get_actor_location()
    result.update(elapsed=elapsed, position=[p.x, p.y, p.z], yaw=pawn.get_actor_rotation().yaw,
                  moving_gate=bool(state['anim'].get_editor_property('IsAccelerating')))
    result['feet'] = {}
    for bone in ('foot_l', 'foot_r'):
        p = mesh.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        result['feet'][bone] = [p.x, p.y, p.z]
    return result

def metrics(seq):
    active = [s for s in seq if 0.12 <= s['elapsed'] < 1.18]
    edges = list(zip(active, active[1:]))
    return {'peak_speed': max(s['speed'] for s in seq),
            'peak_run_weight': max(s.get('run_weight', 0) for s in seq),
            'speed_start_count': sum(a['speed'] <= 1 < b['speed'] for a, b in edges),
            'speed_stop_count': sum(a['speed'] > 1 >= b['speed'] for a, b in edges),
            'gait_state_changes': sum(a['ground_state'] != b['ground_state'] for a, b in edges),
            'request_changes': sum(a.get('move_request_id') != b.get('move_request_id') for a, b in edges),
            'travel_cm': sum(math.dist(a['position'][:2], b['position'][:2]) for a, b in zip(seq, seq[1:])),
            'max_yaw_step': max((abs((b['yaw'] - a['yaw'] + 180) % 360 - 180) for a, b in edges), default=0),
            'max_foot_pose_step': max((max(math.dist(a['feet'][f], b['feet'][f]) for f in a['feet']) for a, b in edges), default=0),
            'held_frames': sum(s['right_mouse_held'] for s in active),
            'final_speed': seq[-1]['speed'], 'final_run_weight': seq[-1].get('run_weight', 1),
            'actual_goal_distance_min': min((s['cursor_goal_distance'] for s in active if 'cursor_goal_distance' in s), default=None),
            'actual_goal_distance_max': max((s['cursor_goal_distance'] for s in active if 'cursor_goal_distance' in s), default=None)}

def prepare(world, now):
    mouse(world, 'Release', state['origin'])
    state['controller'].stop_movement()
    state['movement'].stop_movement_immediately()
    state['anim'].montage_stop(0.0)
    state['pawn'].set_actor_location(state['origin'], False, True)
    state['pawn'].set_actor_rotation(unreal.Rotator(yaw=90), True)
    state.update(phase='settle', settle=now, samples=[], events=[], release=False, clicks=0, last_issue=-1)

def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['handle'])
    report = {'passed': error is None, 'mode': mode, 'cases': state['cases'],
              'error': str(error) if error else None, 'traceback': traceback.format_exc() if error else None,
              'input': 'actual_controller_bindings', 'physical_input_tested': False,
              'fixed_simulation_fps': fps, 'scene_changes_saved': False,
              'editor_navigation_ready': state.get('editor_navigation_ready', False),
              'protected_files_match': all(hashlib.sha256((root / p).read_bytes()).hexdigest() == h for p, h in protected.items())}
    report['passed'] = report['passed'] and report['protected_files_match']
    if state.get('samples') and error:
        report['failed_case'] = cases[state['index']]
        report['failed_samples'] = state['samples']
        report['failed_metrics'] = metrics(state['samples'])
    report_name = 'trace-cursor.json' if globals().get('trace_profile') else mode + '-boundary.json'
    if True:
        report_name = 'movement-' + str(fps) + '.json'
    (qa / report_name).write_text(json.dumps(report, indent=2), encoding='utf-8')
    for key in list(state):
        if isinstance(state[key], unreal.Object):
            state.pop(key)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    state['exit_wall'] = time.monotonic()
    state['exit_handle'] = unreal.register_slate_post_tick_callback(exit_tick)

def exit_tick(delta):
    if time.monotonic() - state['exit_wall'] > 2:
        unreal.unregister_slate_post_tick_callback(state['exit_handle'])
        unreal.log('COUNTESS_BOUNDARY_QA_COMPLETE ' + mode)
        unreal.SystemLibrary.quit_editor()

def tick(delta):
    try:
        wall = time.monotonic()
        if wall - state['wall_start'] > 600:
            raise RuntimeError('Boundary QA timeout at ' + state['phase'])
        if state['phase'] == 'start':
            if wall - state['wall_start'] < 3:
                return
            if not editor_navigation_ready():
                return
            state['editor_navigation_ready'] = True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'world'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if not world:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'world':
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            if not pawn or not pawn.get_editor_property('mesh').get_anim_instance():
                return
            state.update(pawn=pawn, mesh=pawn.get_editor_property('mesh'),
                         movement=pawn.get_editor_property('character_movement'),
                         controller=unreal.GameplayStatics.get_player_controller(world, 0),
                         anim=pawn.get_editor_property('mesh').get_anim_instance())
            ready = sample(world, 0)
            if state['movement'].is_falling() or not ready['navigation_ready']:
                return
            assert pawn.get_class().get_name() == 'BP_CountessCharacter_C'
            state['origin'] = pawn.get_actor_location()
            prepare(world, now)
            return
        if state['phase'] == 'settle':
            if now - state['settle'] < 0.4:
                return
            state.update(phase='run', start=now)
            case = cases[state['index']]
            state['fixed_goal'] = state['origin'] + unreal.Vector(x=0, y=case['distance'], z=-96)
            return
        elapsed = now - state['start']
        case = cases[state['index']]
        current = sample(world, elapsed)
        if not state['samples'] or current['time'] > state['samples'][-1]['time'] + 0.000001:
            state['samples'].append(current)
        if state['release']:
            mouse(world, 'Release', state['last_goal'])
            state['release'] = False
        elif 0.05 <= elapsed < 1.2 and elapsed - state['last_issue'] >= 0.1 - 0.00001:
            kind = case['kind']
            point = state['fixed_goal']
            action = 'Press'
            if kind in ('repeat', 'held_follow'):
                angle = math.pi / 2 + (1 if state['clicks'] % 2 else -1) * math.pi / 12
                point = state['pawn'].get_actor_location() + unreal.Vector(
                    x=case['distance'] * math.cos(angle), y=case['distance'] * math.sin(angle), z=-96)
            if kind.startswith('held'):
                action = 'Press' if state['clicks'] == 0 else 'Move'
            elif kind == 'noise':
                point = state['fixed_goal'] + unreal.Vector(x=2 if state['clicks'] % 2 else -2)
            elif kind == 'cancel':
                if state['clicks'] > 0 and elapsed < 0.4:
                    point = None
                elif elapsed >= 0.4:
                    point = state['pawn'].get_actor_location() + unreal.Vector(x=0, y=20, z=-96)
            elif kind == 'retarget':
                if state['clicks'] > 0 and elapsed < 0.4:
                    point = None
                elif elapsed >= 0.4:
                    point = state['origin'] + unreal.Vector(x=-350, y=350, z=-96)
            if point is not None:
                mouse(world, action, point)
                state['last_goal'] = point
                state['clicks'] += 1
                if not kind.startswith('held'):
                    state['release'] = True
            state['last_issue'] = elapsed
        if elapsed >= 1.2 and not state.get('held_released', False):
            mouse(world, 'Release', state['last_goal'])
            state['held_released'] = True
        if elapsed >= 2.2:
            assert current['speed'] < 1, case['name'] + ': movement did not settle'
            assert current.get('run_weight', 1) < 0.001, case['name'] + ': animation did not settle'
            measured = metrics(state['samples'])
            if case['name'] in ('held_fixed_650', 'cancel_near', 'far_retarget'):
                assert measured['peak_speed'] > 100, case['name'] + ': no actual remote-goal movement occurred'
                assert measured['travel_cm'] > 100, case['name'] + ': actual travel did not exceed 100 cm'
                assert measured['peak_run_weight'] > 0.5, case['name'] + ': actual running pose was not observed'
            result = dict(case, metrics=measured, samples=state['samples'])
            state['cases'].append(result)
            unreal.log('COUNTESS_BOUNDARY_CASE ' + case['name'] + ' ' + json.dumps(result['metrics']))
            state['index'] += 1
            if state['index'] == len(cases):
                finish()
            else:
                state['held_released'] = False
                prepare(world, now)
    except Exception as error:
        unreal.log_error(traceback.format_exc())
        finish(error)

unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS ' + str(fps))
state['handle'] = unreal.register_slate_post_tick_callback(tick)
