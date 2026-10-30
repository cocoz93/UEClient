"""PIE in the dark training room: key 4 -> Aurora, the dash pushing a dummy back along its path and the Hoarfrost crystal wall.
Notes pawn and dummy spots every few frames around the dash; results come from the editor log (AURORA_* lines). No screenshots."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
# 돌진 키(10-21 W ↔ Space 맞바꿈 뒤 Space) · 도약 키(대상 지정)
DASH_KEY = os.environ.get('AURORA_PROBE_DASH_KEY', 'SpaceBar')
LEAP_KEY = os.environ.get('AURORA_PROBE_LEAP_KEY', 'W')
state = {'phase': 'load', 'wall': time.monotonic(), 'step': 0, 'until': 0.0, 'log': []}


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def key(world, name):
    command(world, f'CountessInputQA.Key {name} Press')
    command(world, f'CountessInputQA.Key {name} Release')


def aim(world, point):
    command(world, f'CountessComboQA.Mouse Move Left {point.x} {point.y} {point.z}')


def nearest_dummy(world, pawn):
    dummies = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)
    here = pawn.get_actor_location()
    return min(dummies, key=lambda d: (d.get_actor_location() - here).length())


def note(label):
    def run(world, pawn):
        target = state.get('target')
        entry = {'label': label, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
                 'pawn': vec(pawn.get_actor_location())}
        if target:
            entry['dummy'] = vec(target.get_actor_location())
            entry['gap'] = round((target.get_actor_location() - pawn.get_actor_location()).length(), 1)
        state['log'].append(entry)
    return run


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'aurora-move.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def build_steps():
    def switch(world, pawn):
        key(world, 'Four')

    def walk_near(distance):
        def run(world, pawn):
            target = nearest_dummy(world, pawn)
            state['target'] = target
            point = target.get_actor_location() - unreal.Vector(0, 0, 90)
            here = pawn.get_actor_location()
            back = unreal.Vector(here.x - point.x, here.y - point.y, 0)
            back = back * (1.0 / max(back.length(), 1.0))
            goal = point + back * distance
            state['log'].append({'label': 'walk', 'target': target.get_name(), 'goal': vec(goal)})
            command(world, f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            command(world, f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        return run

    def reset(world, pawn):
        for dummy in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy):
            dummy.reset_dummy()

    def dash_through(world, pawn):
        # 허수아비 너머 400을 겨눈다(허수아비가 돌진 길 한가운데)
        target = state['target']
        point = target.get_actor_location() - unreal.Vector(0, 0, 90)
        here = pawn.get_actor_location()
        forward = unreal.Vector(point.x - here.x, point.y - here.y, 0)
        forward = forward * (1.0 / max(forward.length(), 1.0))
        chosen = point + forward * 400
        state['log'].append({'label': 'aim dash', 'point': vec(chosen)})
        aim(world, chosen)
        key(world, DASH_KEY)
        state['trace_until'] = unreal.GameplayStatics.get_time_seconds(world) + 1.2

    def at_dummy(key_name):
        def run(world, pawn):
            point = state['target'].get_actor_location() - unreal.Vector(0, 0, 90)
            aim(world, point)
            key(world, key_name)
        return run

    steps = [
        (0.0, 'switch', switch),
        (0.8, 'walk', walk_near(170)), (3.5, 'arrived', note('arrived')),
        (0.5, 'reset_w', reset), (0.0, 'before_w', note('before_w')), (0.0, 'W', dash_through),
    ]
    # 돌진 동안(0.4초 준비 + 약 0.15초 이동)은 tick이 장면마다 적는다(trace)
    steps += [
        (1.6, 'after_w', note('after_w')),
        (2.0, 'restored', note('restored')),
        (0.2, 'walk_e', walk_near(170)), (3.0, 'reset_e', reset), (0.0, 'E', at_dummy('E')),
        (2.0, 'after_e', note('after_e')),
        # 도약: 허수아비에서 450 물러나 허수아비를 고른다 → 머리 위에 나타났다 바로 앞(떠난 쪽)에 내려선다
        (0.2, 'walk_leap', walk_near(450)), (3.5, 'before_leap', note('before_leap')),
        (0.0, 'leap', lambda world, pawn: (at_dummy(LEAP_KEY)(world, pawn),
                                          state.__setitem__('trace_until', unreal.GameplayStatics.get_time_seconds(world) + 1.0))),
        (1.2, 'after_leap', note('after_leap')),
        # 대상 없이 누르면 거절(No target)
        (0.3, 'leap_empty', lambda world, pawn: (aim(world, pawn.get_actor_location() + unreal.Vector(-300, 0, -90)), key(world, LEAP_KEY))),
        (0.5, 'end', note('end')),
    ]
    return steps


STEPS = build_steps()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 240:
            raise TimeoutError('Aurora move probe timed out')
        if state['phase'] == 'load':
            unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            state['phase'] = 'navwait'
            return
        if state['phase'] == 'navwait':
            # 불러온 직후 내비메시를 만드는 중이면 PIE 사본에 내비가 없다. 시작점이 내비에 투영될 때까지 기다린다.
            editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0].get_actor_location()
            if time.monotonic() - state['wall'] < 2 or unreal.NavigationSystemV1.is_navigation_being_built(editor_world):
                return
            projected = unreal.NavigationSystemV1.project_point_to_navigation(editor_world, start - unreal.Vector(0, 0, 90),
                None, None, unreal.Vector(100, 100, 250))
            if projected is None and time.monotonic() - state['wall'] < 90:
                return
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'run'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        # 돌진 동안은 장면마다 적는다 — 밀린 허수아비 때문에 내비를 다시 만드는 동안에도(아래 대기와 상관없이)
        if pawn and state.get('trace_until', 0.0) > unreal.GameplayStatics.get_time_seconds(world):
            note('trace')(world, pawn)
        if not pawn or unreal.NavigationSystemV1.is_navigation_being_built(world):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['step'] == 0 and now < 4:
            return
        if state['step'] == 0 and 'configured' not in state:
            command(world, 'Aurora.Skills.IgnoreCooldowns 1')
            state['configured'] = True
        if now < state['until']:
            return
        if state['step'] >= len(STEPS):
            finish()
            return
        delay, name, action = STEPS[state['step']]
        if 'armed' not in state:
            state['armed'] = True
            state['until'] = now + delay
            return
        del state['armed']
        unreal.log(f'AURORA_PROBE step={name}')
        action(world, pawn)
        state['step'] += 1
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
