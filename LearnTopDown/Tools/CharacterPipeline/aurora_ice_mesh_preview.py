"""Stage candidate ice meshes and frozen-target effects around a bare Aurora stand-in in the dark training room and
capture each spot at the game camera pitch. ICE_ITEMS = json file: [{name, mesh | effect, height | radius, up, yaw,
material, stretch [x, y, z], roll, body (stand-in inside, default true), back (cm the effect is pushed toward the camera to undo a built-in offset)}].
Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
BODY = '/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora'
IDLE = '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Idle.Idle'
ITEMS = json.loads(Path(os.environ['ICE_ITEMS']).read_text(encoding='utf-8'))
# PREVIEW_MOMENTS = 찍을 때(초, 쉼표). 검기류는 0.1초 안에 정점이라 앞당겨 쓴다(10-20 Q 대체 후보).
MOMENTS = tuple(float(m) for m in os.environ.get('PREVIEW_MOMENTS', '0.3,0.8,1.6').split(','))
SPACING = 700.0
state = {'phase': 'load', 'wall': time.monotonic(), 'moment': 0}
report = {'items': [i['name'] for i in ITEMS], 'captures': [], 'meshes': {}}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'ice-mesh-preview.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def spot_of(center, index):
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    return center + right * ((index - (len(ITEMS) - 1) / 2.0) * SPACING)


def stage(editor_world):
    # 파이썬은 PIE 세계에 액터를 못 띄우므로 메시·몸·카메라는 PIE 전에 에디터 세계에 놓는다. 입자 효과만 PIE에서 띄운다.
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + unreal.Vector(0, 0, -96)
    state['center'] = center
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    body_mesh = unreal.load_asset(BODY)
    for index, item in enumerate(ITEMS):
        spot = spot_of(center, index)
        if item.get('body', True):
            body = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, spot, unreal.Rotator(roll=0, pitch=0, yaw=135 - 90))
            body.set_editor_property('tags', ['ice_body'])
            component = body.get_editor_property('skeletal_mesh_component')
            component.set_skeletal_mesh_asset(body_mesh)
        if 'mesh' in item:
            mesh = unreal.load_asset(item['mesh'])
            bounds = mesh.get_bounds()
            extent = bounds.box_extent
            report['meshes'][item['name']] = {'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                                              'extent': [extent.x, extent.y, extent.z]}
            if 'radius' in item:
                scale = item['radius'] / max(extent.x, extent.y, 1.0)
            else:
                scale = item.get('height', 200.0) / max(2.0 * extent.z, 1.0)
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, spot,
                unreal.Rotator(roll=item.get('roll', 0.0), pitch=0, yaw=item.get('yaw', 0.0)))
            component = actor.get_editor_property('static_mesh_component')
            component.set_mobility(unreal.ComponentMobility.MOVABLE)
            component.set_static_mesh(mesh)
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            # material = 칸 0에 입힐 재질 · stretch = 축마다 배율(가늘고 긴 창처럼 게임에서 따로 늘이는 메시) · roll = X축으로 기울임(도)
            if 'material' in item:
                component.set_material(0, unreal.load_asset(item['material']))
            stretch = item.get('stretch', [1.0, 1.0, 1.0])
            actor.set_actor_scale3d(unreal.Vector(scale * stretch[0], scale * stretch[1], scale * stretch[2]))
            # 메시 바닥(또는 가운데)이 바닥 + up 에 오게 민다.
            low = (bounds.origin.z - extent.z) * scale if 'radius' not in item else bounds.origin.z * scale
            actor.set_actor_location(spot + unreal.Vector(0, 0, item.get('up', 0.0) - low), False, False)
            report['meshes'][item['name']]['scale'] = scale
        camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
            spot + unreal.Vector(0, 0, 100) - rotation.get_forward_vector() * 560, rotation)
        camera.set_editor_property('tags', [item['name']])


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 400:
            raise TimeoutError('ice mesh preview timed out')
        if state['phase'] == 'load':
            stage(unreal.EditorLoadingAndSavingUtils.load_map(MAP))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'wait'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'wait':
            if now < 2:
                return
            pawn.set_actor_hidden_in_game(True)
            idle = unreal.load_asset(IDLE)
            for actor in unreal.GameplayStatics.get_all_actors_with_tag(world, 'ice_body'):
                if idle:
                    actor.get_editor_property('skeletal_mesh_component').play_animation(idle, True)
            state['captures'] = {}
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if not tags:
                    continue
                capture = actor.get_editor_property('capture_component2d')
                capture.set_editor_property('capture_every_frame', False)
                capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
                capture.set_editor_property('fov_angle', 40)
                settings = capture.get_editor_property('post_process_settings')
                settings.set_editor_property('override_auto_exposure_bias', True)
                settings.set_editor_property('auto_exposure_bias', float(os.environ.get('PREVIEW_EXPOSURE', '6.0')))
                capture.set_editor_property('post_process_settings', settings)
                capture.set_editor_property('texture_target',
                    unreal.RenderingLibrary.create_render_target2d(world, 400, 400, unreal.TextureRenderTargetFormat.RTF_RGBA8))
                state['captures'][tags[0]] = capture
            toward_camera = unreal.Rotator(roll=0, pitch=0, yaw=225).get_forward_vector()
            for index, item in enumerate(ITEMS):
                if 'effect' not in item:
                    continue
                template = unreal.load_asset(item['effect'])
                if not template:
                    report.setdefault('missing', []).append(item['effect'])
                    continue
                spot = spot_of(state['center'], index) + toward_camera * item.get('back', 0.0) + unreal.Vector(0, 0, item.get('up', 0.0))
                scale = item.get('scale', 1.0)
                unreal.GameplayStatics.spawn_emitter_at_location(world, template, spot,
                    unreal.Rotator(roll=0, pitch=0, yaw=item.get('yaw', 0.0)), unreal.Vector(scale, scale, scale), False)
            state.update(phase='capture', started=now)
            return
        if state['phase'] == 'capture':
            if now < state['started'] + MOMENTS[state['moment']]:
                return
            for index, item in enumerate(ITEMS):
                capture = state['captures'].get(item['name'])
                if not capture:
                    continue
                capture.capture_scene()
                file = f"{index:02d}_{item['name']}_{state['moment']}.png"
                unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
                report['captures'].append(file)
            state['moment'] += 1
            if state['moment'] == len(MOMENTS):
                finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
