"""PIE in the dark training room: right-click very short moves (SHORT_DISTANCES cm, default 60,120,200) with characters
1 (Countess), 2 (Sparrow) and 4 (Aurora), capturing the game view every 0.1 s and logging speed, pelvis height and the
anim class each frame. Answers 'why does a tiny move look wrong on 4 but not on 1/2'. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
DISTANCES = [float(d) for d in os.environ.get('SHORT_DISTANCES', '60,120,200').split(',')]
CHARACTERS = [c for c in os.environ.get('SHORT_CHARACTERS', 'One,Two,Four').split(',')]
# SHORT_SKILLS = 이동 전에 차례로 쓸 스킬 키(쉼표, 예: Q,E,R — 10-19 밤 「Aurora 이동이 이상해졌다」: 스킬이 이동 상태를 남기는지)
SKILLS = [k for k in os.environ.get('SHORT_SKILLS', '').split(',') if k]
FRAMES = 14
state = {'phase': 'load', 'wall': time.monotonic(), 'queue': [], 'until': 0.0, 'log': []}


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def command(world, text):
    unreal.SystemLibrary.execute_console_command(world, text)


def pelvis_height(pawn):
    mesh = pawn.get_editor_property('mesh')
    return round(mesh.get_socket_location('pelvis').z - (pawn.get_actor_location().z - 96), 1)


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'short-move.json').write_text(json.dumps({'passed': error is None, 'error': str(error) if error else None,
        'log': state['log']}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def build_queue():
    queue = []
    for character in CHARACTERS:
        queue.append((0.0, ('key', character)))
        queue.append((1.5, ('settle', None)))
        for skill in SKILLS:
            queue.append((0.5, ('key', skill)))
            # 시전 0.35초 뒤 캐릭터가 띄운 메시 부품의 충돌·내비 설정을 적는다(10-20 Q 검기 판이 내비를 깎는지)
            queue.append((0.35, ('parts', skill)))
            # SHORT_NAV_SHOTS=1: 시전 뒤 시각별로 화면을 찍는다(show Navigation과 같이 쓰면 내비 구멍이 생기는 때·모양)
            if os.environ.get('SHORT_NAV_SHOTS') == '1':
                previous = 0.35
                for moment in (0.5, 0.7, 0.9, 1.2, 1.6, 2.5, 4.0):
                    queue.append((moment - previous, ('navshot', f'{skill}_{int(moment * 100):03d}')))
                    previous = moment
            queue.append((5.0, ('settle', None)))
        for index, distance in enumerate(DISTANCES):
            # 방향을 번갈아(화면 오른쪽 / 왼쪽) 제자리 근처에 머문다.
            sign = 1 if index % 2 == 0 else -1
            queue.append((1.2, ('move', (character, distance, sign))))
            for frame in range(FRAMES):
                queue.append((0.0 if frame == 0 else 0.1, ('shot', (character, distance, frame))))
    return queue


def run_action(world, pawn, action):
    kind, payload = action
    if kind == 'key':
        command(world, f'CountessInputQA.Key {payload} Press')
        command(world, f'CountessInputQA.Key {payload} Release')
    elif kind == 'move':
        character, distance, sign = payload
        right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
        here = pawn.get_actor_location()
        goal = here + right * (distance * sign) - unreal.Vector(0, 0, 96)
        state['start'] = here
        command(world, f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        command(world, f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        # 주변 600cm 안에서 충돌이 켜진 부품(스킬이 남긴 보이지 않는 장애물 찾기, 10-20)
        types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
                 unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY3, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY4]
        found = unreal.SystemLibrary.sphere_overlap_components(world, here, 600.0, types, None, [pawn]) or []
        near = sorted({f'{c.get_owner().get_name() if c.get_owner() else "?"}.{c.get_name()}:{c.get_class().get_name()}' for c in found})
        # 같은 출발점·목표의 길찾기 경로 꼭짓점(경로가 꺾이면 내비에 구멍이 생긴 것)
        path = unreal.NavigationSystemV1.find_path_to_location_synchronously(world, here - unreal.Vector(0, 0, 96), goal)
        points = [vec(p) for p in path.get_editor_property('path_points')] if path else []
        dummies = [vec(d.get_actor_location()) for d in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.KwangTrainingDummy)]
        state['log'].append({'event': 'move', 'character': character, 'distance': distance, 'from': vec(here), 'goal': vec(goal),
                             'near': near, 'path': points, 'partial': bool(path and path.is_partial()) if path else None,
                             'dummies': dummies})
    elif kind == 'parts':
        # 캐릭터 둘레 1000cm 안 모든 액터의 부품 중 내비에 들어갈 수 있는 것(충돌 켜짐 + can_ever_affect_navigation)
        parts = {}
        here = pawn.get_actor_location()
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
            if (actor.get_actor_location() - here).length() > 1000 and actor != pawn:
                continue
            for component in actor.get_components_by_class(unreal.PrimitiveComponent):
                if not component.get_editor_property('can_ever_affect_navigation'):
                    continue
                key = '%s.%s:%s col=%s' % (actor.get_class().get_name(), component.get_name(), component.get_class().get_name(),
                                          component.get_collision_enabled())
                parts[key] = parts.get(key, 0) + 1
        state['log'].append({'event': 'parts', 'skill': payload, 'parts': parts})
    elif kind == 'navshot':
        command(world, f'CharacterVisualQA.Capture nav_{payload}')
    elif kind == 'shot':
        character, distance, frame = payload
        name = f'{character}_{int(distance):03d}_{frame:02d}'
        command(world, f'CharacterVisualQA.Capture {name}')
        mesh = pawn.get_editor_property('mesh')
        anim = mesh.get_anim_instance()
        movement = pawn.get_editor_property('character_movement')
        velocity = pawn.get_velocity()
        state['log'].append({'event': 'frame', 'name': name, 'time': round(unreal.GameplayStatics.get_time_seconds(world), 3),
            'speed': round(velocity.length(), 1), 'pelvis': pelvis_height(pawn),
            'travel': round((pawn.get_actor_location() - state['start']).length(), 1),
            'yaw': round(pawn.get_actor_rotation().yaw, 1), 'velocity_yaw': round(velocity.rotator().yaw, 1) if velocity.length() > 1 else None,
            'orient': movement.get_editor_property('orient_rotation_to_movement'),
            'max_speed': round(movement.get_editor_property('max_walk_speed'), 1),
            'montage': bool(anim and anim.is_any_montage_playing()), 'pawn': pawn.get_class().get_name(),
            'anim': anim.get_class().get_name() if anim else None})


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 400:
            raise TimeoutError('short move probe timed out')
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
            state['queue'] = build_queue()
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn or unreal.NavigationSystemV1.is_navigation_being_built(world):
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if 'configured' not in state:
            if now < 4:
                return
            command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
            # SHORT_CVARS = 시작 때 넣을 콘솔 값(세미콜론, 예: Aurora.FX.QStyle 1)
            for text in [c for c in os.environ.get('SHORT_CVARS', '').split(';') if c]:
                command(world, text)
            state['configured'] = True
        if now < state['until']:
            return
        if not state['queue']:
            finish()
            return
        delay, action = state['queue'][0]
        if 'armed' not in state:
            state['armed'] = True
            state['until'] = now + delay
            return
        del state['armed']
        state['queue'].pop(0)
        run_action(world, pawn, action)
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
