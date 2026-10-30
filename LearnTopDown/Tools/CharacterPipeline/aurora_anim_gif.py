"""Play each animation on its own bare Aurora mesh in the training room, one scene capture per mesh at the game camera
pitch, and save every 2nd frame (30 per second at -FPS=60) so the frames can be turned into a GIF per animation.
PREVIEW_ANIMS = comma list of anim paths, PREVIEW_SECONDS = max seconds per anim (default 2.6),
PREVIEW_BONES = optional comma list of bones whose component-space location is written per frame. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
MESH = '/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora'
ANIMS = os.environ['PREVIEW_ANIMS'].split(',')
MAX_SECONDS = float(os.environ.get('PREVIEW_SECONDS', '2.6'))
BONES = [b for b in os.environ.get('PREVIEW_BONES', '').split(',') if b]
SPACING = 700.0
state = {'phase': 'load', 'wall': time.monotonic(), 'frame': 0}
report = {'anims': ANIMS, 'frames': {}}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'anim-gif.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def stage(editor_world):
    # 파이썬은 PIE 세계에 액터를 못 띄우므로 PIE 전에 에디터 세계에 놓는다. 메시 하나마다 촬영 카메라 하나.
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + unreal.Vector(0, 0, -96)
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    mesh = unreal.load_asset(MESH)
    for index, path in enumerate(ANIMS):
        spot = center + right * ((index - (len(ANIMS) - 1) / 2.0) * SPACING)
        # 메시 정면이 +Y라 액터 yaw = 바라볼 방향 - 90. 화면 오른쪽(yaw 135)을 보게 해 옆모습으로 찍는다.
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, spot,
            unreal.Rotator(roll=0, pitch=0, yaw=135 - 90))
        actor.set_editor_property('tags', [unreal.Name(path)])
        component = actor.get_editor_property('skeletal_mesh_component')
        component.set_skeletal_mesh_asset(mesh)
        component.set_editor_property('visibility_based_anim_tick_option',
            unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
            spot + unreal.Vector(0, 0, 100) - rotation.get_forward_vector() * 520, rotation)
        camera.set_editor_property('tags', [unreal.Name(path)])


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 420:
            raise TimeoutError('anim gif timed out')
        if state['phase'] == 'load':
            stage(unreal.EditorLoadingAndSavingUtils.load_map(MAP))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'wait'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            return
        if state['phase'] == 'wait':
            if unreal.GameplayStatics.get_time_seconds(world) < 2:
                return
            pawn.set_actor_hidden_in_game(True)
            state['captures'] = {}
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if not tags or tags[0] not in ANIMS:
                    continue
                capture = actor.get_editor_property('capture_component2d')
                capture.set_editor_property('capture_every_frame', False)
                capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
                capture.set_editor_property('fov_angle', 40)
                settings = capture.get_editor_property('post_process_settings')
                settings.set_editor_property('override_auto_exposure_bias', True)
                settings.set_editor_property('auto_exposure_bias', float(os.environ.get('PREVIEW_EXPOSURE', '7.0')))
                capture.set_editor_property('post_process_settings', settings)
                capture.set_editor_property('texture_target',
                    unreal.RenderingLibrary.create_render_target2d(world, 400, 400, unreal.TextureRenderTargetFormat.RTF_RGBA8))
                state['captures'][tags[0]] = capture
            state['lengths'] = {}
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if not tags or tags[0] not in ANIMS:
                    continue
                animation = unreal.load_asset(tags[0])
                state['lengths'][tags[0]] = min(animation.get_play_length(), MAX_SECONDS)
                actor.get_editor_property('skeletal_mesh_component').play_animation(animation, True)
                state.setdefault('meshes', {})[tags[0]] = actor.get_editor_property('skeletal_mesh_component')
            report['lengths'] = state['lengths']
            state['phase'] = 'capture'
            return
        if state['phase'] == 'capture':
            frame = state['frame']
            state['frame'] += 1
            if frame % 2:
                return
            seconds = frame / 60.0
            alive = False
            for index, path in enumerate(ANIMS):
                if seconds > state['lengths'].get(path, 0.0):
                    continue
                alive = True
                capture = state['captures'][path]
                capture.capture_scene()
                file = f"{index:02d}_{frame // 2:03d}.png"
                unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
                report['frames'].setdefault(path, []).append(file)
                if BONES:
                    mesh = state['meshes'][path]
                    spots = {b: mesh.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT).translation for b in BONES}
                    report.setdefault('bones', {}).setdefault(path, []).append(
                        {'t': round(seconds, 3), **{b: [round(l.x, 1), round(l.y, 1), round(l.z, 1)] for b, l in spots.items()}})
            if not alive:
                finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
