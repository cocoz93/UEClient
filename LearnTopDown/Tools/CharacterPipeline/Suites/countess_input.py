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
intro_cases = ['Right', 'Left', 'E', 'SpaceBar', 'Gamepad_FaceButton_Bottom']
move_cases = [('short', 120), ('long', 650), ('repeat_short', 160)]
state = {'phase': 'start', 'wall_start': time.monotonic(), 'intro_index': 0, 'move_index': 0,
         'report': {'passed': False, 'mode': 'actual_editor_Play_In_Editor', 'checks': [],
                    'intro_cases': [], 'movement_cases': [], 'physical_input_tested': False}}

def check(condition, label):
    if not condition:
        raise RuntimeError(label)
    state['report']['checks'].append(label)

def write_report():
    (qa / 'input-regression.json').write_text(json.dumps(state['report'], indent=2), encoding='utf-8')

def sample(world):
    unreal.SystemLibrary.execute_console_command(world, 'CountessInputQA.State current-sample')
    result = json.loads((qa / 'current-sample.json').read_text(encoding='utf-8'))
    location = state['pawn'].get_actor_location()
    result['position'] = [location.x, location.y, location.z]
    return result

def movement_metrics(samples):
    return {'peak_speed': max(s['speed'] for s in samples),
            'peak_run_weight': max(s.get('run_weight', 0) for s in samples),
            'travel_cm': sum(math.dist(a['position'][:2], b['position'][:2])
                             for a, b in zip(samples, samples[1:]))}

def check_remote_movement(name, measured):
    check(measured['peak_speed'] > 100, name + ': actual peak speed exceeds 100 cm/s')
    check(measured['travel_cm'] > 100, name + ': actual movement exceeds 100 cm')
    check(measured['peak_run_weight'] > 0.5, name + ': actual running pose has majority weight')

def mouse(world, action, button, point):
    unreal.SystemLibrary.execute_console_command(world, 'CountessComboQA.Mouse ' + action + ' ' + button +
        ' ' + str(point.x) + ' ' + str(point.y) + ' ' + str(point.z))

def key(world, name, action):
    unreal.SystemLibrary.execute_console_command(world, 'CountessInputQA.Key ' + name + ' ' + action)

def finish(error=None):
    if error:
        state['report']['error'] = str(error)
        state['report']['traceback'] = traceback.format_exc()
        state['report']['failed_phase'] = state['phase']
        state['report']['last_sample'] = state.get('last_sample')
        unreal.log_error(state['report']['traceback'])
    else:
        state['report']['passed'] = True
    unreal.unregister_slate_post_tick_callback(state['handle'])
    for object_key in list(state):
        if isinstance(state[object_key], unreal.Object):
            state.pop(object_key)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    write_report()
    state['finish_wall'] = time.monotonic()
    state['finish_handle'] = unreal.register_slate_post_tick_callback(exit_editor)

def exit_editor(delta):
    if time.monotonic() - state['finish_wall'] < 2:
        return
    unreal.unregister_slate_post_tick_callback(state['finish_handle'])
    state['report']['scene_changes_saved'] = False
    state['report']['preserved_assets_match'] = all(hashlib.sha256((root / p).read_bytes()).hexdigest() == h
                                                   for p, h in expected_hashes.items())
    if not state['report']['preserved_assets_match']:
        state['report']['passed'] = False
        state['report']['error'] = 'Protected asset changed during runtime QA'
    write_report()
    unreal.log('COUNTESS_INPUT_STOP_RUNTIME_RESULT ' + json.dumps(state['report']))
    next_script = globals().get('next_qa_script')
    if state['report']['passed'] and next_script:
        script = Path(next_script)
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'),
             {'__file__': str(script), 'next_qa_script': globals().get('final_qa_script')})
        return
    unreal.SystemLibrary.quit_editor()

def reset_pawn():
    state['controller'].stop_movement()
    state['anim'].montage_stop(0.0)
    state['pawn'].set_actor_location(state['origin'], False, True)
    state['movement'].stop_movement_immediately()

def begin_intro_case(world, game_time):
    reset_pawn()
    check(state['anim'].montage_play(state['intro'], 1.0) > 0, 'Original intro montage can still play')
    state.update(phase='intro_prepare', case_name=intro_cases[state['intro_index']], case_start=game_time)

def advance_intro(world, game_time):
    state['intro_index'] += 1
    if state['intro_index'] < len(intro_cases):
        begin_intro_case(world, game_time)
    else:
        state.update(phase='move_prepare', prepare_time=game_time)
        reset_pawn()

def begin_move(world, game_time):
    reset_pawn()
    name, distance = move_cases[state['move_index']]
    goal = state['origin'] + unreal.Vector(x=0, y=distance, z=-96)
    mouse(world, 'Press', 'Right', goal)
    state.update(phase='move', case_name=name, case_start=game_time, goal=goal, samples=[],
                 first_moving=None, first_stopped=None, first_idle=None, foot_samples=[], released=False)

def tick(delta):
    try:
        wall = time.monotonic()
        if wall - state['wall_start'] > 150:
            raise RuntimeError('Runtime QA timeout at ' + state['phase'])
        if state['phase'] == 'start':
            if wall - state['wall_start'] < 3:
                return
            if not editor_navigation_ready():
                return
            state['report']['editor_navigation_ready'] = True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'world'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if world is None:
            return
        game_time = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'world':
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            if pawn is None or pawn.get_editor_property('mesh').get_anim_instance() is None:
                return
            mesh = pawn.get_editor_property('mesh')
            state.update(pawn=pawn, mesh=mesh, anim=mesh.get_anim_instance(),
                         controller=unreal.GameplayStatics.get_player_controller(world, 0),
                         movement=pawn.get_editor_property('character_movement'), origin=pawn.get_actor_location(),
                         intro=unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Animations/LevelStart_Montage'))
            check(pawn.get_class().get_name() == 'BP_CountessCharacter_C', 'Saved Countess character is active')
            check([s.get_editor_property('play_rate') for s in pawn.get_editor_property('combo_attacks')] == [1.25, 1.25, 1.0],
                  'Attack rates remain 1.25 / 1.25 / 1.0')
            state.update(phase='initial_intro', initial_start=game_time)
            return
        current = sample(world)
        state['last_sample'] = current
        pawn, anim = state['pawn'], state['anim']
        if state['phase'] == 'initial_intro':
            if game_time - state['initial_start'] < 0.12:
                return
            check(current['intro_playing'], 'BeginPlay still starts the original appearance montage without input')
            check(current['intro_weight'] > 0.1, 'Original appearance montage contributes to the actual pose')
            state['report']['initial_intro_sample'] = current
            state.update(phase='ready')
            return
        if state['phase'] == 'ready':
            if state['movement'].is_falling() or not current['navigation_ready']:
                return
            state['origin'] = pawn.get_actor_location()
            check(pawn.get_components_by_class(unreal.SpringArmComponent)[0].get_editor_property('target_arm_length') == 2000,
                  'Camera remains 2000')
            name = 'InputStopTarget'
            target = state['origin'] + unreal.Vector(x=160, y=0, z=-7)
            unreal.SystemLibrary.execute_console_command(world, 'CountessComboQA.Spawn ' + name +
                ' /Script/LearnTopDown.KwangTrainingDummy ' + str(target.x) + ' ' + str(target.y) + ' ' + str(target.z))
            state['dummy'] = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
                                  if a.get_name() == name)
            begin_intro_case(world, game_time)
            return
        if state['phase'] == 'intro_prepare':
            if game_time - state['case_start'] < 0.25:
                return
            name = state['case_name']
            check(current['intro_playing'] and current['intro_weight'] > 0.1, name + ': appearance is playing before input')
            state['before_input'] = current
            if name == 'Right':
                state['input_point'] = state['origin'] + unreal.Vector(x=0, y=650, z=-96)
                state['intro_movement_samples'] = [dict(current)]
                mouse(world, 'Press', name, state['input_point'])
            elif name == 'Left':
                state['input_point'] = state['dummy'].get_actor_location()
                state['before_health'] = state['dummy'].get_editor_property('health')
                mouse(world, 'Press', name, state['input_point'])
            else:
                key(world, name, 'Press')
            state.update(phase='intro_input', input_time=game_time)
            return
        if state['phase'] == 'intro_input':
            name = state['case_name']
            check(not current['intro_playing'] and current['intro_weight'] == 0, name + ': next input frame removes intro pose completely')
            if name in ['Right', 'Left']:
                mouse(world, 'Release', name, state['input_point'])
            else:
                key(world, name, 'Release')
            state['report']['intro_cases'].append({'input': name, 'before': state['before_input'], 'after': current, 'passed': True})
            if name == 'Left':
                check(pawn.get_combo_attack_number() == 1, 'Left: the same click immediately starts attack 1')
                key(world, 'SpaceBar', 'Press')
                state.update(phase='attack_input', attack_time=game_time)
            elif name == 'Right':
                if current['time'] > state['intro_movement_samples'][-1]['time'] + 0.000001:
                    state['intro_movement_samples'].append(dict(current))
                state.update(phase='intro_movement', movement_seen=False)
            else:
                check(not pawn.is_attacking() and current['speed'] < 1, name + ': intro cancellation leaves basic attack and movement idle')
                advance_intro(world, game_time)
            return
        if state['phase'] == 'attack_input':
            check(pawn.is_attacking(), 'AnyKey input during an attack does not interrupt the attack montage')
            key(world, 'SpaceBar', 'Release')
            state['phase'] = 'attack_finish'
            return
        if state['phase'] == 'attack_finish':
            if pawn.is_attacking():
                return
            check(state['dummy'].get_editor_property('health') == state['before_health'] - 20,
                  'Attack after cancelling intro causes exactly one hit')
            advance_intro(world, game_time)
            return
        if state['phase'] == 'intro_movement':
            if current['time'] > state['intro_movement_samples'][-1]['time'] + 0.000001:
                state['intro_movement_samples'].append(dict(current))
            if current['speed'] > 590:
                state['movement_seen'] = True
            if state['movement_seen'] and current['speed'] < 1 and current['ground_state'] == 'Idle':
                measured = movement_metrics(state['intro_movement_samples'])
                state['report']['intro_right_movement'] = {'goal_distance': 650, 'metrics': measured,
                    'samples': state['intro_movement_samples']}
                check_remote_movement('Right after intro cancellation', measured)
                check(True, 'Right: navigation and Idle return work immediately after intro cancellation')
                advance_intro(world, game_time)
            return
        if state['phase'] == 'move_prepare':
            if game_time - state['prepare_time'] > 0.2:
                begin_move(world, game_time)
            return
        if state['phase'] == 'move':
            if not state['released']:
                mouse(world, 'Release', 'Right', state['goal'])
                state['released'] = True
            current['elapsed'] = game_time - state['case_start']
            state['samples'].append(current)
            if current['speed'] > 590:
                if state['first_moving'] is None:
                    state['first_moving'] = current
                foot = state['mesh'].get_socket_transform('foot_l', unreal.RelativeTransformSpace.RTS_COMPONENT).translation
                state['foot_samples'].append([foot.x, foot.y, foot.z])
            elif state['first_moving'] is not None and current['speed'] < 1:
                if state['first_stopped'] is None:
                    state['first_stopped'] = current
                if current['ground_state'] == 'Idle' and state['first_idle'] is None:
                    state['first_idle'] = current
            if state['first_stopped'] and game_time - state['first_stopped']['time'] > 0.28:
                name = state['case_name']
                check(state['first_idle'] is not None, name + ': stopping switches to Idle')
                delay = state['first_idle']['time'] - state['first_stopped']['time']
                check(delay <= animation_stop_grace + 0.035, name + ': physical stop immediately starts the Idle transition')
                check(current.get('run_weight', 0) < 0.001, name + ': stop blending settles completely')
                check(all(s['ground_state'] not in ['JogStart', 'JogStop'] for s in state['samples']),
                      name + ': no lingering start or stop animation')
                check(any(s['ground_state'] == 'Run' and s['speed'] > 590 for s in state['samples']),
                      name + ': actual Run state is active while moving')
                check(0 < state['first_moving']['speed'] <= 600.01, name + ': movement begins within the configured speed limit')
                span = max(max(p[i] for p in state['foot_samples']) - min(p[i] for p in state['foot_samples']) for i in range(3))
                check(span > 5, name + ': walking pose actually advances')
                measured = movement_metrics(state['samples'])
                if name == 'long':
                    state['report']['long_movement_metrics'] = measured
                    check_remote_movement(name, measured)
                state['report']['movement_cases'].append({'name': name, 'idle_delay_seconds': delay,
                    'foot_component_span_cm': span, 'metrics': measured, 'samples': state['samples'], 'passed': True})
                write_report()
                state['move_index'] += 1
                if state['move_index'] < len(move_cases):
                    state.update(phase='move_prepare', prepare_time=game_time)
                    reset_pawn()
                else:
                    finish()
            elif game_time - state['case_start'] > 5:
                raise RuntimeError('Movement did not finish: ' + state['case_name'])
            return
    except Exception as error:
        finish(error)

unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
state['handle'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('COUNTESS_INPUT_STOP_RUNTIME_STARTED')

unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS ' + str(fps))
