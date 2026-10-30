"""PIE in the dark training room: base vs Undertow Gideon skill FX side by side at three moments. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
FX = '/Game/ParagonGideon/FX/Particles/Gideon'
PAIRS = [
    ('rmb_projectile', FX + '/Abilities/ProjectileMeteor/FX/P_Gideon_RMB_Proj'),
    ('rmb_hit', FX + '/Abilities/ProjectileMeteor/FX/P_Gideon_RMB_HitWorld'),
    ('meteor_portal', FX + '/Abilities/Meteor/FX/P_Gideon_Meteor_Portal'),
    ('meteor_impact', FX + '/Abilities/Meteor/FX/P_Gideon_MeteorBigImpact'),
    ('portal_entrance', FX + '/Abilities/Portal/FX/P_Portal_Entrance'),
    ('ultimate', FX + '/Abilities/Ultimate/FX/P_Gideon_Ultimate'),
]
MOMENTS = (0.25, 0.7, 1.5)
GAP = 260.0  # 기본(왼쪽)과 Undertow(오른쪽) 사이 반 간격
state = {'phase': 'load', 'wall': time.monotonic(), 'index': 0, 'moment': 0, 'until': 0.0, 'live': []}
report = {'captures': [], 'missing': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None and not report['missing']
    report['error'] = error
    (qa / 'gideon-fx.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def place_camera(editor_world):
    # 파이썬은 PIE 세계에 액터를 띄우지 못하므로, PIE 시작 전에 에디터 세계에 촬영 카메라를 놓아 복사되게 한다.
    # 무대 = 시작 지점 앞 500, 게임과 같은 각도(-50°/45°)로 두 이펙트가 함께 들어오게 가까이 둔다.
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + start.get_actor_forward_vector() * 500 + unreal.Vector(0, 0, -96)
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
        center - rotation.get_forward_vector() * 1300, rotation)
    return center


def ready_camera(world):
    capture = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)[0].get_editor_property('capture_component2d')
    capture.set_editor_property('capture_every_frame', False)
    capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property('fov_angle', 50)
    capture.set_editor_property('texture_target',
        unreal.RenderingLibrary.create_render_target2d(world, 960, 640, unreal.TextureRenderTargetFormat.RTF_RGBA8))
    return capture


def clear_live():
    for component in state['live']:
        if component:
            component.deactivate()
            component.destroy_component(component)
    state['live'] = []


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300:
            raise TimeoutError('Gideon FX compare timed out')
        if state['phase'] == 'load':
            editor_world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            state['center'] = place_camera(editor_world)
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'wait'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'wait':
            if now < 3:
                return
            # 캐릭터가 무대를 가리지 않게 숨긴다.
            pawn.set_actor_hidden_in_game(True)
            state['camera'] = ready_camera(world)
            state['phase'] = 'spawn'
            return
        if now < state['until']:
            return
        if state['phase'] == 'spawn':
            if state['index'] == len(PAIRS):
                finish()
                return
            name, base = PAIRS[state['index']]
            # 카메라 기준 좌우: 게임 카메라 yaw 45°의 오른쪽 방향
            right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
            for side, path in ((-1, base), (1, FX + '/Skins/Undertow/' + base.rsplit('/', 1)[1] + '_Undertow')):
                template = unreal.load_asset(path)
                if not template:
                    report['missing'].append(path)
                    continue
                component = unreal.GameplayStatics.spawn_emitter_at_location(world, template,
                    state['center'] + right * (GAP * side), unreal.Rotator(0, 0, 0), unreal.Vector(1, 1, 1), False)
                state['live'].append(component)
            state.update(phase='capture', moment=0, started=now, until=now + MOMENTS[0])
            return
        if state['phase'] == 'capture':
            name = PAIRS[state['index']][0]
            capture = state['camera']
            capture.capture_scene()
            file = f"{name}_{state['moment']}.png"
            unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
            report['captures'].append({'skill': name, 'seconds': MOMENTS[state['moment']], 'file': file,
                                       'exists': (qa / file).is_file()})
            state['moment'] += 1
            if state['moment'] < len(MOMENTS):
                state['until'] = state['started'] + MOMENTS[state['moment']]
                return
            clear_live()
            state['index'] += 1
            state.update(phase='spawn', until=now + 0.5)
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
