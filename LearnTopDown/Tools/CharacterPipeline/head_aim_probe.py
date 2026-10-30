"""PIE in the dark training room: for keys 1/3/4, walk in four directions and read the anim BP aim variables (Pitch/Yaw)
and the head bone yaw relative to the body at each stop. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
KEYS = ['One', 'Three', 'Four']
# 시작점(0,-400) 둘레를 네 방향으로 걷는다.
POINTS = [(300, -400), (300, -100), (-300, -100), (-300, -400)]
if os.environ.get('HEAD_SAME'):
    # 대조: 한 자리·한 방향에 서서 시간만 흘려 대기 동작 자체의 고개 흔들림을 잰다.
    KEYS = os.environ['HEAD_SAME'].split(',')
    POINTS = [(300, -400)] * 6
state = {'phase': 'load', 'wall': time.monotonic(), 'step': 0, 'until': 0.0, 'rows': []}


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def read(anim, name):
    try:
        return round(float(anim.get_editor_property(name)), 1)
    except Exception:
        return None


def measure(world, pawn, key, point):
    mesh = pawn.get_editor_property('mesh')
    anim = mesh.get_anim_instance()
    body = pawn.get_actor_rotation().yaw
    head = mesh.get_socket_rotation('head').yaw
    neck = mesh.get_socket_rotation('neck_01').yaw
    pelvis = mesh.get_socket_rotation('pelvis').yaw
    wrap = lambda v: round((v + 180) % 360 - 180, 1)
    # 몸 기준(컴포넌트 공간) 머리 회전. 축이 거의 수직인 뼈는 세계 Yaw만 떼면 값이 튀므로 회전 전체를 남긴다.
    local = mesh.get_socket_transform('head', unreal.RelativeTransformSpace.RTS_COMPONENT).rotation.rotator()
    head_local = [round(local.roll, 1), round(local.pitch, 1), round(local.yaw, 1)]
    state['rows'].append({'key': key, 'point': point, 'pawn': pawn.get_class().get_name(), 'body_yaw': round(body, 1),
                          'head_local': head_local, 'head_minus_pelvis': wrap(head - pelvis), 'neck_minus_pelvis': wrap(neck - pelvis),
                          'anim_pitch': read(anim, 'Pitch'), 'anim_yaw': read(anim, 'Yaw'),
                          'aim': str(pawn.get_base_aim_rotation()) if hasattr(pawn, 'get_base_aim_rotation') else None})
    command(world, f'CharacterVisualQA.Capture head_{key}_{len(state["rows"])}')


def build_steps():
    steps = []
    for key in KEYS:
        steps.append((0.3, f'switch {key}', lambda w, p, k=key: (command(w, f'CountessInputQA.Key {k} Press'),
                                                                 command(w, f'CountessInputQA.Key {k} Release'))))
        for point in POINTS:
            def walk(w, p, pt=point):
                command(w, f'CountessComboQA.Mouse Press Right {pt[0]} {pt[1]} 0')
                command(w, f'CountessComboQA.Mouse Release Right {pt[0]} {pt[1]} 0')
            steps.append((0.8, f'walk {key} {point}', walk))
            steps.append((1.6, f'measure {key} {point}', lambda w, p, k=key, pt=point: measure(w, p, k, pt)))
    return steps


STEPS = build_steps()


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'head-aim.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
                                                  'rows': state['rows']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 240:
            raise TimeoutError('head aim probe timed out')
        if state['phase'] == 'load':
            unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            state['phase'] = 'navwait'
            return
        if state['phase'] == 'navwait':
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
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['step'] == 0 and now < 4:
            return
        if state['step'] == 0 and 'configured' not in state:
            command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
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
        unreal.log(f'HEAD_PROBE step={name}')
        action(world, pawn)
        state['step'] += 1
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
