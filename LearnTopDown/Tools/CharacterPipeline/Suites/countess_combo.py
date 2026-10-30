import hashlib
import json
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
expected_rates = [step['play_rate'] for step in installation['metadata']]
cases = [
    {'name': 'single_click', 'hits': 1, 'attacks': 1},
    {'name': 'two_clicks', 'hits': 2, 'attacks': 2},
    {'name': 'three_clicks', 'hits': 3, 'attacks': 3},
    {'name': 'repeat_cycle', 'hits': 4, 'attacks': 4},
    {'name': 'late_input_resets', 'hits': 1, 'attacks': 2, 'queue_at': 0.74},
    {'name': 'interrupt_before_hit', 'hits': 0, 'attacks': 2, 'interrupt_at': 0.12},
    {'name': 'interrupt_after_hit', 'hits': 1, 'attacks': 2, 'interrupt_at': 0.42},
    {'name': 'restart_after_interruption', 'hits': 3, 'attacks': 3},
    {'name': 'facing_away', 'hits': 0, 'attacks': 3, 'away': True},
    {'name': 'out_of_range', 'hits': 0, 'attacks': 3, 'far': True},
]
state = {'phase': 'start', 'wall_start': time.monotonic(), 'case_index': 0,
         'report': {'passed': False, 'checks': [], 'cases': [],
                    'mode': 'actual_editor_Play_In_Editor', 'physical_mouse_tested': False}}

def check(condition, label):
    if not condition:
        raise RuntimeError(label)
    state['report']['checks'].append(label)

def write_report():
    (qa / 'combo-regression.json').write_text(json.dumps(state['report'], indent=2), encoding='utf-8')

def finish(error=None):
    if error:
        state['report']['error'] = str(error)
        state['report']['traceback'] = traceback.format_exc()
        state['report']['failed_case_state'] = {k: state.get(k) for k in ['observed', 'input_count', 'damage_changes', 'previous_step']}
        unreal.log_error(state['report']['traceback'])
    else:
        state['report']['passed'] = True
    unreal.unregister_slate_post_tick_callback(state['handle'])
    for object_key in list(state):
        if isinstance(state[object_key], unreal.Object):
            state.pop(object_key)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    write_report()
    unreal.log('COUNTESS_COMBO_RUNTIME_RESULT ' + json.dumps(state['report']))
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
        state['report']['error'] = 'A protected asset changed during runtime QA'
    write_report()
    next_script = globals().get('next_qa_script')
    if state['report']['passed'] and next_script:
        script = Path(next_script)
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), {'__file__': str(script)})
        return
    unreal.SystemLibrary.quit_editor()

def begin_case(world):
    case = cases[state['case_index']]
    pawn, dummy = state['pawn'], state['dummy']
    state['controller'].stop_movement()
    state['anim'].montage_stop(0.0)
    origin = state['origin']
    pawn.set_actor_location(origin, False, True)
    pawn.get_editor_property('character_movement').stop_movement_immediately()
    target = origin + unreal.Vector(x=400 if case.get('far') else 160, y=0,
                     z=-pawn.get_editor_property('capsule_component').get_editor_property('capsule_half_height') + 90)
    # 체력은 읽기 전용이다. 각 케이스마다 게임 월드에 새 표적을 생성한다.
    dummy.destroy_actor()
    dummy = spawn_actor(world, unreal.KwangTrainingDummy, target)
    state['dummy'] = dummy
    aim = origin - (target - origin) if case.get('away') else target
    check(pawn.try_basic_attack(aim), case['name'] + ': first attack starts')
    check(abs(pawn.get_editor_property('combo_restart_cooldown') - 0.3) < 1e-6, 'Saved Countess loads native cooldown default')
    check(pawn.get_combo_attack_number() == 1, case['name'] + ': starts at Normal')
    check(pawn.get_velocity().length() < 1, case['name'] + ': navigation stops')
    game_time = unreal.GameplayStatics.get_time_seconds(world)
    state.update(phase='case', case=case, aim=aim, case_start=game_time, step_start=game_time,
                 observed=[1], step_times=[0.0], positions=[], queued_steps=set(), previous_step=1, input_count=1,
                 damage_changes=[], previous_health=100.0, interrupted=False)
    unreal.log('COUNTESS_COMBO_CASE_STARTED ' + case['name'])

def spawn_actor(world, actor_class, location):
    state['spawn_counter'] = state.get('spawn_counter', 0) + 1
    name = 'ComboTestActor_' + str(state['spawn_counter'])
    actor_class = actor_class if isinstance(actor_class, unreal.Class) else actor_class.static_class()
    unreal.SystemLibrary.execute_console_command(world, 'CountessComboQA.Spawn ' + name + ' ' +
        actor_class.get_path_name() + ' ' + str(location.x) + ' ' + str(location.y) + ' ' + str(location.z))
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, actor_class)
    return next(a for a in actors if a.get_name() == name)

def mouse_input(world, action, button, point):
    unreal.SystemLibrary.execute_console_command(world, 'CountessComboQA.Mouse ' + action + ' ' + button +
        ' ' + str(point.x) + ' ' + str(point.y) + ' ' + str(point.z))

def tick(delta):
    try:
        wall = time.monotonic()
        if wall - state['wall_start'] > 180:
            raise RuntimeError('Runtime QA timed out at ' + state['phase'])
        if state['phase'] == 'start':
            if wall - state['wall_start'] < 3 or not editor_navigation_ready():
                return
            state['report']['editor_navigation_ready_before_pie'] = True
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'world'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if world is None:
            return
        if state['phase'] == 'world':
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            if pawn is None or pawn.get_editor_property('mesh').get_anim_instance() is None:
                return
            unreal.SystemLibrary.execute_console_command(world, 'CountessInputQA.State combo-navigation')
            navigation_sample = json.loads((qa / 'combo-navigation.json').read_text(encoding='utf-8'))
            if pawn.get_editor_property('character_movement').is_falling() or not navigation_sample['navigation_ready']:
                return
            check(pawn.get_class().get_name() == 'BP_CountessCharacter_C', 'Saved Countess character is used in PIE')
            check(pawn.get_components_by_class(unreal.SpringArmComponent)[0].get_editor_property('target_arm_length') == 2000,
                  'Saved game camera remains 2000')
            mesh = pawn.get_editor_property('mesh')
            check(mesh.get_editor_property('anim_class').get_name() == 'ABP_Countess_TopDown_C', 'Existing locomotion Blueprint preserved')
            check([s.get_editor_property('montage').get_name() for s in pawn.get_editor_property('combo_attacks')] ==
                  [step['montage'].rsplit('.', 1)[-1] for step in profile['basic_attack']], 'Saved Normal / A / B configuration loaded in PIE')
            check([s.get_editor_property('play_rate') for s in pawn.get_editor_property('combo_attacks')] == expected_rates,
                  'Saved attack speeds match ' + str(expected_rates))
            movement = pawn.get_editor_property('character_movement')
            state['report']['movement_settings'] = {name: movement.get_editor_property(name) for name in
                ['max_walk_speed', 'max_acceleration', 'requested_move_use_acceleration', 'ground_friction',
                 'braking_friction', 'braking_friction_factor', 'braking_deceleration_walking', 'use_separate_braking_friction']}
            state['report']['movement_settings']['use_acceleration_for_paths'] = movement.get_editor_property('nav_movement_properties').get_editor_property('use_acceleration_for_paths')
            check(state['report']['movement_settings']['use_acceleration_for_paths'] and
                  state['report']['movement_settings']['requested_move_use_acceleration'],
                  'Saved Countess enables short path acceleration in actual PIE')
            check(state['report']['movement_settings']['max_walk_speed'] ==
                  profile['expected']['movement']['max_walk_speed'],
                  'Saved maximum movement speed is preserved')
            dummy = unreal.GameplayStatics.get_actor_of_class(world, unreal.KwangTrainingDummy)
            check(dummy is not None, 'Existing training dummy spawned')
            anim = mesh.get_anim_instance()
            state.update(pawn=pawn, dummy=dummy, anim=anim,
                         controller=unreal.GameplayStatics.get_player_controller(world, 0),
                         origin=pawn.get_actor_location(), root_mode=anim.get_editor_property('root_motion_mode'),
                         orient=pawn.get_editor_property('character_movement').get_editor_property('orient_rotation_to_movement'),
                         phase='settle', settle_time=wall)
            return
        if state['phase'] == 'settle':
            if wall - state['settle_time'] >= 2:
                begin_case(world)
            return
        pawn, dummy, anim = state['pawn'], state['dummy'], state['anim']
        game_time = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'case':
            case = state['case']
            stage = pawn.get_combo_attack_number()
            if stage and stage != state['previous_step']:
                state['observed'].append(stage)
                state['step_times'].append(game_time - state['case_start'])
                state['step_start'] = game_time
                state['previous_step'] = stage
            health = dummy.get_editor_property('health')
            if health != state['previous_health']:
                check(abs(state['previous_health'] - health - 20.0) < 0.01, case['name'] + ': damage event is exactly 20')
                state['damage_changes'].append({'time': game_time - state['case_start'], 'stage': stage, 'health': health})
                state['previous_health'] = health
            if stage:
                elapsed = game_time - state['step_start']
                check((pawn.get_actor_location() - state['origin']).length() < 2, case['name'] + ': attack stays in place') if len(state['positions']) == 0 else None
                state['positions'].append((pawn.get_actor_location() - state['origin']).length())
                montage = pawn.get_editor_property('combo_attacks')[stage - 1].get_editor_property('montage')
                rate = pawn.get_editor_property('combo_attacks')[stage - 1].get_editor_property('play_rate')
                check(abs(anim.montage_get_play_rate(montage) - rate) < 0.001,
                      case['name'] + ': actual montage speed matches the configured stage') if stage not in state.get('validated_stages', set()) else None
                check(anim.montage_is_playing(montage), case['name'] + ': current stage montage is playing') if stage not in state.get('validated_stages', set()) else None
                state.setdefault('validated_stages', set()).add(stage)
                step_number = len(state['observed'])
                if case['name'] == 'repeat_cycle' and stage == 3:
                    check(not pawn.try_basic_attack(state['aim']), 'Final attack refuses immediate wrap-around')
                if not (case['name'] == 'repeat_cycle' and stage == 3) and state['input_count'] < case['attacks'] and step_number not in state['queued_steps'] and elapsed >= case.get('queue_at', 0.10) / rate:
                    check(pawn.try_basic_attack(state['aim']), case['name'] + ': extra input is queued')
                    check(not any(pawn.try_basic_attack(state['aim']) for _ in range(6)), case['name'] + ': rapid repeats cannot accumulate more inputs')
                    check(pawn.get_combo_attack_number() == stage, case['name'] + ': input does not cut the current attack immediately')
                    state['input_count'] += 1
                    state['queued_steps'].add(step_number)
                if case.get('interrupt_at') and elapsed >= case['interrupt_at'] / rate and not state['interrupted']:
                    anim.montage_stop(0.08)
                    state['interrupted'] = True
                    check(not pawn.is_attacking(), case['name'] + ': interruption immediately clears the attack lock')
            if game_time - state['case_start'] > 5:
                raise RuntimeError('Attack did not recover: ' + case['name'])
            if stage == 0 and case['name'] == 'repeat_cycle' and len(state['observed']) == 3:
                if 'cooldown_start' not in state:
                    state['cooldown_start'] = game_time
                    state['cooldown_attempts'] = 0
                elapsed_cooldown = game_time - state['cooldown_start']
                if elapsed_cooldown < 0.28:
                    check(not pawn.try_basic_attack(state['aim']), 'Cooldown rejects repeated inputs')
                    state['cooldown_attempts'] += 1
                elif elapsed_cooldown > 0.32:
                    check(state['cooldown_attempts'] >= 5, 'Cooldown was sampled across multiple frames')
                    check(pawn.try_basic_attack(state['aim']), 'New first attack starts after cooldown')
                    state['input_count'] += 1
                return
            if stage == 0 and game_time - state['case_start'] > 1.15:
                expected_order = [1] if case.get('interrupt_at') or case.get('queue_at') else [i % 3 + 1 for i in range(case['attacks'])]
                check(state['observed'] == expected_order, case['name'] + ': observed order is ' + str(expected_order))
                for step_index in range(1, len(state['step_times'])):
                    previous_stage = state['observed'][step_index - 1]
                    expected_advance = installation['metadata'][previous_stage - 1]['advance_time']
                    if case['name'] == 'repeat_cycle' and previous_stage == 3:
                        expected_advance = installation['metadata'][2]['reset_time'] + 0.3 + 0.04
                    actual_advance = state['step_times'][step_index] - state['step_times'][step_index - 1]
                    check(abs(actual_advance - expected_advance) < 0.06,
                          case['name'] + ': combo transition follows the speed-adjusted notify time')
                for hit_index, damage in enumerate(state['damage_changes']):
                    expected_hit = installation['metadata'][damage['stage'] - 1]['hit_time']
                    actual_hit = damage['time'] - state['step_times'][hit_index]
                    check(abs(actual_hit - expected_hit) < 0.06,
                          case['name'] + ': damage follows the speed-adjusted hit time')
                check(abs(health - (100 - 20 * case['hits'])) < 0.01, case['name'] + ': expected total damage')
                check(len(state['damage_changes']) == case['hits'], case['name'] + ': no duplicate or stale hits')
                check(max(state['positions'], default=0) < 2, case['name'] + ': root motion did not displace the character')
                check(anim.get_editor_property('root_motion_mode') == state['root_mode'], case['name'] + ': root motion mode restored')
                check(pawn.get_editor_property('character_movement').get_editor_property('orient_rotation_to_movement') == state['orient'],
                      case['name'] + ': movement orientation restored')
                state['report']['cases'].append({'name': case['name'], 'observed_order': state['observed'],
                    'step_start_times': state['step_times'], 'damage_events': state['damage_changes'], 'health': health, 'passed': True})
                state['case_index'] += 1
                state['validated_stages'] = set()
                write_report()
                if state['case_index'] < len(cases):
                    state.update(phase='between_cases', between_time=game_time)
                else:
                    dummy.destroy_actor()
                    state['dummy'] = spawn_actor(world, unreal.KwangTrainingDummy, state['origin'] + unreal.Vector(x=160, y=0, z=-7))
                    state.update(phase='mouse_cooldown_wait', mouse_ready_time=game_time)
            return
        if state['phase'] == 'between_cases':
            if game_time - state['between_time'] > 0.35:
                begin_case(world)
            return
        if state['phase'] == 'mouse_cooldown_wait':
            if game_time - state['mouse_ready_time'] > 0.35:
                mouse_input(world, 'Press', 'Left', dummy.get_actor_location())
                state.update(phase='mouse_case', mouse_start=game_time, mouse_stages=[], mouse_inputs=1,
                             mouse_release_pending=True, mouse_step_time=game_time, mouse_last_stage=0)
            return
        if state['phase'] == 'mouse_case':
            if state['mouse_release_pending']:
                mouse_input(world, 'Release', 'Left', dummy.get_actor_location())
                state['mouse_release_pending'] = False
            stage = pawn.get_combo_attack_number()
            if stage and stage != state['mouse_last_stage']:
                state['mouse_stages'].append(stage)
                state['mouse_last_stage'] = stage
                state['mouse_step_time'] = game_time
            if stage and state['mouse_inputs'] < len(state['mouse_stages']) + 1 and state['mouse_inputs'] < 3 and game_time - state['mouse_step_time'] > 0.15:
                mouse_input(world, 'Press', 'Left', dummy.get_actor_location())
                state['mouse_inputs'] += 1
                state['mouse_release_pending'] = True
            if stage == 0 and len(state['mouse_stages']) == 3 and game_time - state['mouse_start'] > 2.4:
                check(state['mouse_stages'] == [1, 2, 3], 'Virtual left mouse input traverses the real controller bindings for all three attacks')
                check(dummy.get_editor_property('health') == 40, 'Mouse-driven combo delivers exactly three hits')
                state['report']['synthetic_mouse_tested'] = True
                kwang_class = unreal.load_asset('/Game/TopDown/Blueprints/BP_KwangCharacter').generated_class()
                kwang = spawn_actor(world, kwang_class, state['origin'] + unreal.Vector(x=0, y=500, z=0))
                state['controller'].possess(kwang)
                state.update(phase='legacy_settle', kwang=kwang, legacy_start=game_time, legacy_health=dummy.get_editor_property('health'))
            elif game_time - state['mouse_start'] > 6:
                raise RuntimeError('Mouse input did not complete the combo: ' + str(state['mouse_stages']))
            return
        if state['phase'] == 'legacy_settle':
            kwang = state['kwang']
            if game_time - state['legacy_start'] < 2 or kwang.get_editor_property('character_movement').is_falling():
                return
            check(not kwang.get_editor_property('combo_attacks'), 'Kwang retains the single-attack configuration')
            dummy.set_actor_location(kwang.get_actor_location() + unreal.Vector(x=160, y=0, z=-7), False, True)
            state['report']['legacy_preconditions'] = {
                'movement_mode': str(kwang.get_editor_property('character_movement').get_editor_property('movement_mode')),
                'anim_instance': str(kwang.get_editor_property('mesh').get_anim_instance()),
                'montage': str(kwang.get_editor_property('basic_attack_montage'))}
            check(kwang.try_basic_attack(dummy.get_actor_location()), 'Legacy single attack starts in actual PIE')
            check(not kwang.try_basic_attack(dummy.get_actor_location()), 'Legacy single attack still rejects queued input')
            state.update(phase='legacy_attack', legacy_attack_start=game_time)
            return
        if state['phase'] == 'legacy_attack':
            if game_time - state['legacy_attack_start'] < 2.0:
                return
            check(not state['kwang'].is_attacking(), 'Legacy single attack recovers')
            check(dummy.get_editor_property('health') == state['legacy_health'] - 20, 'Legacy single attack still causes exactly one 20-damage hit')
            state['controller'].possess(pawn)
            state['kwang'].destroy_actor()
            goal = pawn.get_actor_location() + unreal.Vector(x=0, y=250, z=-96)
            mouse_input(world, 'Press', 'Right', goal)
            state.update(phase='movement', move_start=game_time, move_origin=pawn.get_actor_location(), peak_speed=0,
                         movement_goal=goal, movement_release=False, movement_samples=[], last_movement_sample=-1,
                         first_moving_sample=None)
            return
        if state['phase'] == 'movement':
            if not state['movement_release'] and game_time - state['move_start'] > 0.15:
                mouse_input(world, 'Release', 'Right', state['movement_goal'])
                state['movement_release'] = True
            state['peak_speed'] = max(state['peak_speed'], pawn.get_velocity().length())
            elapsed = game_time - state['move_start']
            if state['first_moving_sample'] is None and pawn.get_velocity().length() > 1:
                state['first_moving_sample'] = {'time': elapsed, 'speed': pawn.get_velocity().length()}
            if elapsed - state['last_movement_sample'] >= 0.05 and elapsed <= 1.0:
                state['movement_samples'].append({'time': elapsed, 'speed': pawn.get_velocity().length(),
                    'distance': (pawn.get_actor_location() - state['move_origin']).length(),
                    'anim_moving_gate': bool(state['anim'].get_editor_property('IsAccelerating'))})
                state['last_movement_sample'] = elapsed
            if game_time - state['move_start'] < 2.5:
                return
            check(state['peak_speed'] > 100 and (pawn.get_actor_location() - state['move_origin']).length() > 100,
                  'Virtual right mouse input resumes navigation movement after all combo cases')
            check(state['first_moving_sample'] is not None and
                  0 < state['first_moving_sample']['speed'] <= state['report']['movement_settings']['max_walk_speed'] + 0.01,
                  'Movement resumes within the configured speed limit after the attacks')
            check(pawn.get_velocity().length() < 1, 'Countess stops after arriving at the right-click destination')
            walking_samples = [sample for sample in state['movement_samples'] if sample['speed'] > 590 and sample['time'] > 0.05]
            check(len(walking_samples) >= 2 and all(sample['anim_moving_gate'] for sample in walking_samples),
                  'Walking animation remains enabled during right-click movement after the attacks')
            check(not state['anim'].get_editor_property('IsAccelerating'),
                  'Walking animation gate clears after arriving at the destination')
            check(pawn.get_components_by_class(unreal.SpringArmComponent)[0].get_editor_property('target_arm_length') == 2000,
                  'Camera still remains 2000 after gameplay')
            state['report']['movement_peak_speed'] = state['peak_speed']
            state['report']['movement_speed_samples'] = state['movement_samples']
            state['report']['first_moving_sample'] = state['first_moving_sample']
            finish()
    except Exception as error:
        finish(error)

unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
state['handle'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('COUNTESS_COMBO_RUNTIME_STARTED')

unreal.SystemLibrary.execute_console_command(None, 't.MaxFPS ' + str(fps))
