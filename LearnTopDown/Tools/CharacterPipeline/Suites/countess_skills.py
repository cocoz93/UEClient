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
enum = unreal.CountessSkill
skills = [enum.SHADOW_SLIP, enum.BLADE_SIPHON, enum.DARK_TIDE, enum.FEAST]
keys = ['Q', 'W', 'E', 'R']
cases = [
    ('q_controller_and_return', 0, 'normal'), ('w_controller_aoe', 1, 'normal'),
    ('e_controller_three_stabs', 2, 'normal'), ('r_controller_stun', 3, 'normal'),
    ('q_no_target', 0, 'no_target'), ('r_no_target', 3, 'no_target'),
    ('q_range', 0, 'range'), ('r_range', 3, 'range'),
    ('q_wall', 0, 'wall'), ('r_wall', 3, 'wall'),
    ('w_wall_and_far', 1, 'wall'), ('e_static_wall', 2, 'wall'),
    ('e_dynamic_wall', 2, 'dynamic_wall'), ('q_return_expiration', 0, 'expire'),
    ('q_return_blocked', 0, 'return_blocked'), ('q_target_destroyed', 0, 'target_destroyed'),
    ('r_target_destroyed', 3, 'target_destroyed'),
    ('w_interrupt_before_hit', 1, 'interrupt_before'), ('w_interrupt_after_hit', 1, 'interrupt_after'),
    ('r_interrupt_during_stun', 3, 'stun_interrupt'), ('q_character_slow_restore', 0, 'slow'),
    ('r_character_stun_restore', 3, 'stun'),
    ('w_cancels_basic_hit_timer', 1, 'cancel_basic'),
    ('w_cancel_for_animation_replacement', 1, 'anim_replace'),
    ('q_owner_destroyed', 0, 'owner_destroyed'), ('e_owner_destroyed', 2, 'owner_destroyed'),
    ('w_rejects_falling_input', 1, 'falling'),
    ('q_controller_character', 0, 'controller_character'),
    ('r_controller_character', 3, 'controller_character'),
    ('r_close_timing', 3, 'close'), ('r_max_range_timing', 3, 'max_range'),
    ('r_moving_target_timing', 3, 'moving'),
    ('r_target_destroyed_after_arrival', 3, 'target_destroyed_after_arrival'),
]
state = {'phase': 'start', 'wall': time.monotonic(), 'index': globals().get('start_index', 0), 'spawn_id': 0,
         'report': {'passed': False, 'fixed_simulation_fps': fps, 'audio_engine_enabled': True, 'checks': [], 'cases': [],
                    'physical_input_tested': False, 'input': 'actual_controller_bindings_and_public_skill_api',
                    'scene_changes_saved': False}}
if state['index']:
    previous = json.loads((qa / f'runtime-skills-{fps}.json').read_text(encoding='utf-8'))
    state['report']['cases'] = previous['cases'][:state['index']]
    state['report']['checks'] = previous['checks']
    assert len(state['report']['cases']) == state['index'] and all(c['passed'] for c in state['report']['cases'])


def check(condition, label):
    if not condition:
        raise RuntimeError(label)
    state['report']['checks'].append(label)


def spawn(world, actor_class, position):
    state['spawn_id'] += 1
    name = 'SkillQA_' + str(state['spawn_id'])
    actor_class = actor_class if isinstance(actor_class, unreal.Class) else actor_class.static_class()
    unreal.SystemLibrary.execute_console_command(world,
        f'CountessComboQA.Spawn {name} {actor_class.get_path_name()} {position.x} {position.y} {position.z}')
    return next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, actor_class) if a.get_name() == name)


def mouse(world, action, button, point):
    unreal.SystemLibrary.execute_console_command(world,
        f'CountessComboQA.Mouse {action} {button} {point.x} {point.y} {point.z}')


def key(world, action, name):
    unreal.SystemLibrary.execute_console_command(world, f'CountessSkillsQA.Key {action} {name}')


def snapshot(world):
    unreal.SystemLibrary.execute_console_command(world, 'CountessSkillsQA.State skill-sample')
    sample = json.loads((qa / 'skill-sample.json').read_text(encoding='utf-8'))
    unreal.SystemLibrary.execute_console_command(world, 'CountessFXQA.State audio-sample')
    fx = json.loads((qa / 'audio-sample.json').read_text(encoding='utf-8'))
    assert fx['skill_audio_enabled'] is False and fx['skill_voice_enabled'] is False
    assert not fx['audio'], 'A muted skill spawned an audio component'
    state['report']['audio_samples_checked'] = state['report'].get('audio_samples_checked', 0) + 1
    return sample


def make_wall(world, position, dynamic=False):
    wall = spawn(world, unreal.StaticMeshActor, position)
    component = wall.get_component_by_class(unreal.StaticMeshComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    component.set_collision_profile_name('BlockAllDynamic' if dynamic else 'BlockAll')
    wall.set_actor_scale3d(unreal.Vector(x=0.8, y=5.0, z=3.5))
    state['fixtures'].append(wall)
    return wall


def prepare(world, now):
    for name in keys:
        key(world, 'Release', name)
    mouse(world, 'Release', 'Right', state['origin'])
    state['controller'].stop_movement()
    for actor in state.get('fixtures', []):
        if unreal.SystemLibrary.is_valid(actor):
            actor.destroy_actor()
    previous = state.get('pawn')
    pawn = spawn(world, state['character_class'], state['origin'])
    state['controller'].possess(pawn)
    if previous and unreal.SystemLibrary.is_valid(previous):
        previous.destroy_actor()
    state.update(pawn=pawn, component=pawn.get_countess_skills(), anim=pawn.get_editor_property('mesh').get_anim_instance(),
                 movement=pawn.get_editor_property('character_movement'), fixtures=[], samples=[], events=[],
                 phase='settle', settle=now, interrupted=False, acted=False, returned=False,
                 action_peak_effects=0, after_origin=None, last_sample=-1, previous_healths=None)
    name, index, kind = cases[state['index']]
    state.update(name=name, skill_index=index, kind=kind)
    positions = [unreal.Vector(x=300, y=0, z=-7)]
    if index == 1:
        positions = [unreal.Vector(x=160, y=0, z=-7), unreal.Vector(x=-160, y=0, z=-7),
                     unreal.Vector(x=0, y=180, z=-7), unreal.Vector(x=360, y=0, z=-7)]
    elif index == 2:
        positions = [unreal.Vector(x=200, y=0, z=-7), unreal.Vector(x=260, y=0, z=-7),
                     unreal.Vector(x=500, y=250, z=-7)]
    if kind in ('close','max_range'):
        positions=[unreal.Vector(x=120 if kind=='close' else 480,y=0,z=-7)]
    if kind == 'range':
        positions = [unreal.Vector(x=1000 if index == 0 else 650, y=0, z=-7)]
    if kind in ('slow', 'stun', 'stun_interrupt', 'controller_character', 'moving'):
        victim = spawn(world, unreal.load_asset('/Game/TopDown/Blueprints/BP_KwangCharacter').generated_class(),
                       state['origin'] + unreal.Vector(x=positions[0].x, y=positions[0].y, z=0))
        victim.spawn_default_controller()
        state['fixtures'].append(victim)
        state['victim'] = victim
        state['victim_movement'] = victim.get_editor_property('character_movement')
        state['victim_movement'].set_movement_mode(unreal.MovementMode.MOVE_WALKING)
        state['victim_speed'] = state['victim_movement'].get_editor_property('max_walk_speed')
        if kind=='moving':
            state['victim_movement'].set_editor_property('max_walk_speed',150.0)
            state['victim_start']=victim.get_actor_location()
            victim.get_controller().move_to_location(state['victim_start']+unreal.Vector(x=0,y=300,z=0), acceptance_radius=5.0, stop_on_overlap=False)
        targets = [victim]
    else:
        targets = [spawn(world, unreal.KwangTrainingDummy, state['origin'] + p) for p in positions]
        state['fixtures'] += targets
    state['targets'] = targets
    if kind in ('wall', 'dynamic_wall'):
        distance = 100 if index == 1 else 150
        make_wall(world, state['origin'] + unreal.Vector(x=distance, y=0, z=0), kind == 'dynamic_wall')


def start_case(world, now):
    pawn, component = state['pawn'], state['component']
    check(component.is_enabled(), state['name'] + ': Countess skill component enabled')
    definitions = component.get_editor_property('skills')
    check([d.get_editor_property('animation').get_name() for d in definitions] ==
          ['Ability_Q', 'Ability_RMB', 'Ability_Ultimate', 'Ability_Ultimate'], 'Configured skill animation sources loaded')
    target = state['targets'][0]
    aim = target.get_actor_location()
    state.update(start=now, aim=aim, root_mode=state['anim'].get_editor_property('root_motion_mode'),
                 saved_orient=state['movement'].get_editor_property('orient_rotation_to_movement'))
    kind = state['kind']
    index = state['skill_index']
    if kind == 'falling':
        state['movement'].set_movement_mode(unreal.MovementMode.MOVE_FALLING)
        check(not component.try_use_skill(skills[index], aim, target), 'Falling input is rejected')
        check(component.get_cooldown_remaining(skills[index]) == 0, 'Falling rejection does not consume cooldown')
        state['movement'].set_movement_mode(unreal.MovementMode.MOVE_WALKING)
        complete_case(now)
        return
    if kind == 'no_target':
        target = None
    if kind == 'cancel_basic':
        check(pawn.try_basic_attack(aim), 'Basic attack starts before skill cancel')
        check(pawn.try_basic_attack(aim), 'Basic combo input was queued')
    if kind == 'moving':
        victim=state['victim']
        check(victim.get_velocity().length()>10,'R target is already moving at input')
    if kind in ('normal', 'controller_character', 'close', 'max_range', 'moving'):
        mouse(world, 'Move', 'Left', aim)
        key(world, 'Press', keys[index])
        state['key_release_pending'] = True
        state['phase'] = 'await_controller'
        return
    else:
        accepted = component.try_use_skill(skills[index], aim, target)
        expected = not (kind in ('no_target', 'range') or (kind == 'wall' and index in (0, 3)))
        check(accepted == expected, state['name'] + ': activation result matches target validation')
        if not expected:
            check(component.get_cooldown_remaining(skills[index]) == 0, 'Rejected input keeps cooldown at zero')
            check(not pawn.is_combat_busy(), 'Rejected input leaves movement unlocked')
            complete_case(now)
            return
    check(component.is_casting(), state['name'] + ': cast starts')
    check(not pawn.is_attacking(), 'Skill owns combat lock without a stale basic attack')
    check(not pawn.try_basic_attack(aim), 'Basic attack cannot overlap active skill')
    check(not component.try_use_skill(skills[(index + 1) % 4], aim, target), 'Skills cannot overlap')
    state.update(phase='case', key_release_pending=state.get('key_release_pending', False))


def healths():
    return [actor.get_editor_property('health') if isinstance(actor, unreal.KwangTrainingDummy) else None
            for actor in state['targets'] if unreal.SystemLibrary.is_valid(actor)]


def complete_case(now):
    state['report']['cases'].append({'name': state['name'], 'skill': keys[state['skill_index']],
        'kind': state['kind'], 'passed': True, 'healths': healths(), 'events': state['events'],
        'peak_active_effects': state['action_peak_effects'], 'samples': state['samples']})
    (qa / f'runtime-skills-{fps}.json').write_text(json.dumps(state['report'], indent=2), encoding='utf-8')
    state['index'] += 1
    state.update(phase='between', between=now)


def finish(error=None):
    if error:
        state['report']['error'] = str(error)
        state['report']['traceback'] = traceback.format_exc()
        state['report']['failed_case'] = cases[state['index']] if state['index'] < len(cases) else None
        state['report']['failed_samples'] = state.get('samples')
        unreal.log_error(state['report']['traceback'])
    state['report']['protected_files_match'] = all(hashlib.sha256((root / p).read_bytes()).hexdigest() == h for p, h in protected.items())
    state['report']['passed'] = error is None and state['report']['protected_files_match']
    (qa / f'runtime-skills-{fps}.json').write_text(json.dumps(state['report'], indent=2), encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(state['handle'])
    for name in list(state):
        if isinstance(state[name], unreal.Object) or name in ('fixtures', 'targets'):
            state.pop(name)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    state['exit_time'] = time.monotonic()
    state['exit_handle'] = unreal.register_slate_post_tick_callback(exit_tick)


def exit_tick(delta):
    if time.monotonic() - state['exit_time'] > 2:
        unreal.unregister_slate_post_tick_callback(state['exit_handle'])
        unreal.log('COUNTESS_SKILLS_RUNTIME_COMPLETE ' + str(fps))
        unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300:
            raise RuntimeError('Skills QA timed out at ' + state['phase'])
        if state['phase'] == 'start':
            if time.monotonic() - state['wall'] > 3 and editor_navigation_ready():
                state['report']['editor_navigation_ready_before_pie'] = True
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                state['phase'] = 'world'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if world is None:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if now == state.get('last_time'):
            return
        state['last_time'] = now
        if state['phase'] == 'world':
            pawn = unreal.GameplayStatics.get_player_character(world, 0)
            if not pawn or pawn.get_editor_property('character_movement').is_falling():
                return
            unreal.SystemLibrary.execute_console_command(world, 'CountessInputQA.State skills-ready')
            ready = json.loads((qa / 'skills-ready.json').read_text(encoding='utf-8'))
            if not ready['navigation_ready']:
                return
            state.update(pawn=pawn, controller=unreal.GameplayStatics.get_player_controller(world, 0),
                         character_class=pawn.get_class(), origin=pawn.get_actor_location(), fixtures=[])
            check(isinstance(state['controller'].get_hud(), unreal.CharacterSkillHUD), 'Common skill cooldown HUD is active')
            for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
                dummy.destroy_actor()
            state.update(phase='between', between=now)
            return
        if state['phase'] == 'between':
            if now - state['between'] > 0.4:
                if state['index'] == len(cases):
                    state.update(phase='fx_cleanup', cleanup_start=now)
                else:
                    prepare(world, now)
            return
        if state['phase'] == 'fx_cleanup':
            if now - state['cleanup_start'] > 4.0:
                unreal.SystemLibrary.execute_console_command(world, 'CountessFXQA.State cleanup')
                fx = json.loads((qa / 'cleanup.json').read_text(encoding='utf-8'))
                check(not fx['effects'], 'Temporary skill effects expire')
                check(not fx['clones'], 'No shadow clone remains')
                check(fx['proxy_count'] == 0, 'No skeletal effect proxy remains')
                check(not fx['audio'], 'No muted skill audio remains')
                state['report']['final_fx_cleanup'] = fx
                finish()
            return
        if state['phase'] == 'settle':
            if now - state['settle'] > 0.6 and not state['movement'].is_falling():
                start_case(world, now)
            return
        if state['phase'] == 'await_controller':
            if now - state['start'] < 0.08:
                return
            check(state['component'].is_casting(), state['name'] + ': real controller binding starts cast')
            state['phase'] = 'case'
            return
        if state['phase'] != 'case':
            return
        pawn, component, anim = state['pawn'], state['component'], state['anim']
        elapsed = now - state['start']
        index, kind = state['skill_index'], state['kind']
        if state['key_release_pending']:
            key(world, 'Release', keys[index])
            state['key_release_pending'] = False
        if elapsed - state['last_sample'] >= 0.04:
            sample = snapshot(world)
            location = pawn.get_actor_location() if unreal.SystemLibrary.is_valid(pawn) else state['origin']
            sample.update(elapsed=elapsed, position=[location.x, location.y, location.z], healths=healths())
            if index==3 and unreal.SystemLibrary.is_valid(state['targets'][0]):
                target_pos=state['targets'][0].get_actor_location()
                sample['target_position']=[target_pos.x,target_pos.y,target_pos.z]
            if kind in ('slow', 'stun', 'stun_interrupt', 'controller_character', 'moving'):
                sample['victim_movement_mode'] = str(state['victim_movement'].get_editor_property('movement_mode'))
            state['samples'].append(sample)
            state['action_peak_effects'] = max(state['action_peak_effects'], sample['active_effects'])
            state['last_sample'] = elapsed
        current = healths()
        if current != state['previous_healths']:
            state['events'].append({'elapsed': elapsed, 'healths': current})
            state['previous_healths'] = current
        if component.is_casting() and elapsed > 0.1:
            sample = state['samples'][-1]
            check(sample['montage_slots'] == 'CountessFullBody', 'Skill uses full-body slot') if not state['acted'] else None
            state['acted'] = True
        if kind in ('target_destroyed', 'target_destroyed_after_arrival', 'owner_destroyed') and not state['interrupted']:
            threshold = 1.5 if kind=='target_destroyed_after_arrival' else (.02 if index==3 else (0.1 if index==0 else 0.4))
            if elapsed > threshold:
                if kind in ('target_destroyed','target_destroyed_after_arrival'):
                    state['targets'][0].destroy_actor()
                else:
                    pawn.destroy_actor()
                    # 컨트롤러가 사라진 캐릭터를 참조하지 않도록 같은 위치에 새 캐릭터를 소유한다.
                    replacement = spawn(world, state['character_class'], state['origin'])
                    state['controller'].possess(replacement)
                    state['pawn'] = replacement
                state['interrupted'] = True
        if kind in ('interrupt_before', 'interrupt_after', 'stun_interrupt', 'anim_replace') and not state['interrupted']:
            threshold = 0.2 if kind in ('interrupt_before', 'anim_replace') else (0.25 if kind == 'stun_interrupt' else 0.65)
            if elapsed > threshold:
                if kind == 'anim_replace':
                    pawn.get_editor_property('mesh').set_anim_instance_class(
                        unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Countess_AnimBlueprint').generated_class())
                else:
                    anim.montage_stop(0.02)
                state['interrupted'] = True
        if kind == 'normal' and index == 0 and not state['returned'] and elapsed > 0.85:
            check(healths() == [65.0], 'Q applies exactly one hit')
            check((pawn.get_actor_location() - state['origin']).length() > 100, 'Q blinks toward target')
            check(component.get_return_remaining() > 2.0, 'Q opens return window')
            old_cd = component.get_cooldown_remaining(skills[0])
            mouse(world, 'Move', 'Left', state['origin'])
            key(world, 'Press', 'Q')
            key(world, 'Release', 'Q')
            check(component.get_cooldown_remaining(skills[0]) <= old_cd + 0.01, 'Return does not restart cooldown')
            state['returned'] = True
        if kind == 'return_blocked' and not state['returned'] and elapsed > 0.8:
            make_wall(world, state['origin'])
            check(not component.try_use_skill(skills[0], state['origin'], None), 'Blocked return is rejected')
            check(component.get_return_remaining() > 0, 'Blocked return keeps remaining opportunity')
            state['returned'] = True
        if kind == 'slow' and 0.4 < elapsed < 0.8:
            check(abs(state['victim_movement'].get_editor_property('max_walk_speed') - state['victim_speed'] * 0.58) < 0.1,
                  'Q applies original slow to moving character')
        if kind in ('stun', 'stun_interrupt') and 0.02 < elapsed < 0.045:
            check(not state['victim_movement'].is_moving_on_ground(), 'R disables victim movement during stun')
        duration = 4.0 if kind in ('expire', 'return_blocked') else (3.1 if index == 3 else 2.2)
        if elapsed > duration:
            if kind == 'owner_destroyed':
                if index == 2:
                    check(not unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CountessDarkTide), 'Owner destruction removes active wave')
                complete_case(now)
                return
            check(not component.is_casting() and not pawn.is_combat_busy(), state['name'] + ': cast lock recovered')
            check(state['movement'].get_editor_property('orient_rotation_to_movement') == state['saved_orient'], 'Movement orientation restored')
            if kind != 'anim_replace':
                check(anim.get_editor_property('root_motion_mode') == state['root_mode'], 'Root motion mode restored')
            if kind in ('target_destroyed', 'target_destroyed_after_arrival', 'interrupt_before', 'anim_replace', 'stun_interrupt'):
                if current and index in (1,3) and kind!='target_destroyed' and all(value is not None for value in current):
                    check(current == [100.0] * (4 if index==1 else 1), 'Interrupted cast never delivers stale damage')
            elif index == 0:
                if kind == 'normal':
                    check((pawn.get_actor_location() - state['origin']).length() < 12, 'Q returns to original location')
                    check(current == [65.0], 'Return deals no second hit')
                if kind == 'expire':
                    check(component.get_return_remaining() == 0, 'Q return window expires')
                    check(not component.try_use_skill(skills[0], state['origin'], None), 'Expired return cannot bypass cooldown')
                if kind == 'slow':
                    check(abs(state['victim_movement'].get_editor_property('max_walk_speed') - state['victim_speed']) < 0.1, 'Q slow restores original speed')
            elif index == 1:
                expected = [100.0, 60.0, 60.0, 100.0] if kind == 'wall' else [60.0, 60.0, 60.0, 100.0]
                check(current == expected, 'W damages each in-range visible target once')
            elif index == 2:
                expected = [100.0, 100.0, 100.0] if kind in ('wall', 'dynamic_wall') else [55.0, 55.0, 100.0]
                check(current == expected, 'E stabs visible nearby targets three times and respects walls and lateral range')
                check(not unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CountessDarkTide), 'E wave expires')
            elif index == 3:
                if kind in ('normal','close','max_range'):
                    check(current == [20.0], 'R deals one heavy hit')
                    check((pawn.get_actor_location() - state['origin']).length() > (5 if kind=='close' else 100), 'R moves toward victim')
                if kind in ('normal','close','max_range','moving'):
                    trace=state['samples']
                    played=[s for s in trace if s['montage_slots']=='CountessFullBody' and s['casting']]
                    check(played and all(abs(s['montage_play_rate']-1.0)<0.001 for s in played), 'R original jump montage uses its restored 1x rate')
                    origin=[state['origin'].x,state['origin'].y,state['origin'].z]
                    preparation=[s for s in trace if s['elapsed']<.9]
                    check(preparation and all(sum((s['position'][i]-origin[i])**2 for i in (0,1))<9 for s in preparation),'R shows preparation before moving')
                    arrival=[s for s in trace if 1.5<s['elapsed']<1.7]
                    check(arrival and all(sum((s['position'][i]-s['target_position'][i])**2 for i in (0,1))<180**2 for s in arrival),'R finishes the swept approach near the target')
                    check(played[0]['montage_position']<.15,'R begins at the original animation start')
                    windup=[s for s in trace if .15<s['elapsed']<1.75]
                    if kind!='moving':
                        check(windup and all(s['healths']==[100.0] for s in windup),'R preparation and approach do not prematurely deal damage')
                    recovered=[s for s in trace if not s['casting'] and s['elapsed']>.2]
                    expected_recovery=min(2.25,played[0]['montage_length'])
                    check(recovered and expected_recovery-.08<=recovered[0]['elapsed']<=expected_recovery+.15,'R combat lock follows the readable jump recovery')
                    if kind!='moving':
                        hit=next(e['elapsed'] for e in state['events'] if e['healths']==[20.0])
                        check(1.78<=hit<=1.94,'R impact follows the visible attack around 1.8 seconds')
                    else:
                        start=state['victim_start']
                        check(any(sum((s['target_position'][i]-[start.x,start.y,start.z][i])**2 for i in (0,1))>100 for s in trace),'R target really moves before binding')
                        check((pawn.get_actor_location()-state['victim'].get_actor_location()).length()<180,'R lands next to moving target')
                if kind in ('stun', 'stun_interrupt'):
                    check(state['victim_movement'].is_moving_on_ground(), 'R restores victim movement')
            if kind not in ('target_destroyed', 'target_destroyed_after_arrival', 'wall', 'dynamic_wall'):
                check(state['action_peak_effects'] > 0, 'Original skill particles activated')
            if kind not in ('target_destroyed', 'target_destroyed_after_arrival',):
                if index == 0 and component.get_return_remaining() > 0:
                    check(component.get_cooldown_remaining(skills[index]) > 0, 'Q return opportunity coexists with original cooldown')
                else:
                    check(not component.try_use_skill(skills[index], state['aim'], state['targets'][0]), 'Repeated input cannot bypass skill cooldown')
            goal = pawn.get_actor_location() + unreal.Vector(x=0, y=250, z=-96)
            mouse(world, 'Press', 'Right', goal)
            mouse(world, 'Release', 'Right', goal)
            state.update(phase='move_after', move_start=now, move_origin=pawn.get_actor_location())
            return
        return
    except Exception as error:
        finish(error)


base_tick = tick


def tick_with_movement(delta):
    if state['phase'] == 'move_after':
        try:
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if world:
                now = unreal.GameplayStatics.get_time_seconds(world)
                if now - state['move_start'] > 0.5:
                    check((state['pawn'].get_actor_location() - state['move_origin']).length() > 70, 'Right-click movement resumes after skill')
                    complete_case(now)
        except Exception as error:
            finish(error)
    else:
        base_tick(delta)


unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
state['handle'] = unreal.register_slate_post_tick_callback(tick_with_movement)
