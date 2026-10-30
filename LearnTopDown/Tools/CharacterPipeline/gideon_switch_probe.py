"""PIE probe in the original field: SWITCH_KEY (default Three = Gideon, Four = Aurora) switches, right-click moves,
then 1/2/3/4 still switch."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

import sys
sys.path.insert(0, str(Path(unreal.Paths.project_dir()).resolve() / 'Tools/CharacterPipeline'))
from navigation_ready import editor_navigation_ready

# 기존 필드의 원통 위 시작점과 북쪽 경사로 아래 지점(navigation_ready.py와 같은 경로)
TOP = (0, 0, 212)
RAMP = (0, 650, 125)

qa = Path(os.environ['SPARROW_QA_OUTPUT'])
KEY = os.environ.get('SWITCH_KEY', 'Three')
SHOT = {'Three': 'gideon', 'Four': 'aurora'}[KEY]
ROUND = ['One', 'Two', 'Three', 'Four']
state = {'phase': 'load', 'wall': time.monotonic(), 'step': 0, 'until': 0.0, 'rows': [], 'switches': []}


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def describe(world, pawn):
    mesh = pawn.get_editor_property('mesh')
    anim = mesh.get_anim_instance()
    return {'time': round(unreal.GameplayStatics.get_time_seconds(world), 3), 'pawn': pawn.get_class().get_path_name(),
            'location': vec(pawn.get_actor_location()), 'speed': round(pawn.get_velocity().length(), 1),
            'anim': anim.get_class().get_path_name() if anim else None}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'gideon-switch.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'switches': state['switches'], 'rows': state['rows'], 'target': state.get('target'),
        'control_after_click': state.get('control_done')}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def press(world, key):
    command(world, f'CountessInputQA.Key {key} Press')
    command(world, f'CountessInputQA.Key {key} Release')


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 240:
            raise TimeoutError('Gideon switch probe timed out')
        if state['phase'] == 'load':
            unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
            state['phase'] = 'navwait'
            return
        if state['phase'] == 'navwait':
            # 불러온 직후 내비메시를 다시 만들므로 경로가 실제로 나올 때까지 PIE를 미룬다.
            if time.monotonic() - state['wall'] > 2 and editor_navigation_ready():
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                state['phase'] = 'run'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn or unreal.NavigationSystemV1.is_navigation_being_built(world):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['step'] >= 2 and state['step'] <= 4:
            state['rows'].append(describe(world, pawn))
        if now < state['until']:
            return
        step = state['step']
        if state.get('control') is None:
            # 대조군: 같은 우클릭 주입으로 기존 카운테스가 움직이는지 먼저 본다.
            if now < 6:
                return
            target = unreal.Vector(*RAMP)
            command(world, f'CountessComboQA.Mouse Press Right {target.x} {target.y} {target.z}')
            command(world, f'CountessComboQA.Mouse Release Right {target.x} {target.y} {target.z}')
            state['control'] = []
            state['until'] = now + 2.5
            return
        if 'control_done' not in state:
            state['control_done'] = describe(world, pawn)
        if step == 0:
            command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
            state['switches'].append({'key': None, **describe(world, pawn)})
            press(world, KEY)
            state['until'] = now + 0.6
        elif step == 1:
            state['switches'].append({'key': KEY, **describe(world, pawn)})
            command(world, f'CharacterVisualQA.Capture {SHOT}_idle')
            target = unreal.Vector(*TOP)
            state['target'] = vec(target)
            command(world, f'CountessComboQA.Mouse Press Right {target.x} {target.y} {target.z}')
            command(world, f'CountessComboQA.Mouse Release Right {target.x} {target.y} {target.z}')
            state['until'] = now + 0.35
        elif step == 2:
            command(world, f'CharacterVisualQA.Capture {SHOT}_run')
            state['until'] = now + 2.5
        elif step == 3:
            command(world, f'CharacterVisualQA.Capture {SHOT}_stopped')
            state['until'] = now + 0.1
        elif step == 4:
            press(world, 'One')
            state['until'] = now + 0.6
        elif step in (5, 6, 7, 8):
            # 1 → 2 → 3 → 4 순서로 한 바퀴 돈다.
            state['switches'].append({'key': ROUND[step - 5], **describe(world, pawn)})
            if step == 8:
                finish()
                return
            press(world, ROUND[step - 4])
            state['until'] = now + 0.6
        state['step'] += 1
    except Exception as error:
        unreal.log_error(traceback.format_exc())
        finish(error)


handle = unreal.register_slate_post_tick_callback(tick)
