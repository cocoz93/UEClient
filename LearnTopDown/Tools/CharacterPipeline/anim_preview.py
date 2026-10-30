"""Play several animations side by side on bare skeletal mesh actors in the training room and capture them at the game
camera angle over time. PREVIEW_MESH = skeletal mesh path, PREVIEW_ANIMS = comma list of anim paths,
PREVIEW_MOMENTS = comma list of seconds. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
MESH = os.environ.get('PREVIEW_MESH', '/Game/ParagonGideon/Characters/Heroes/Gideon/Meshes/Gideon')
ANIMS = os.environ['PREVIEW_ANIMS'].split(',')
MOMENTS = [float(m) for m in os.environ.get('PREVIEW_MOMENTS', '0.1,0.3,0.5,0.7,0.9,1.1').split(',')]
SPACING = 260.0
state = {'phase': 'load', 'wall': time.monotonic(), 'moment': 0}
report = {'anims': ANIMS, 'captures': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'anim-preview.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def stage(editor_world):
    # 파이썬은 PIE 세계에 액터를 못 띄우므로 PIE 전에 에디터 세계에 놓는다. 화면 오른쪽(yaw 135)으로 나란히, 모두 화면 위쪽을 본다.
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + unreal.Vector(0, 0, -96)
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    mesh = unreal.load_asset(MESH)
    for index, path in enumerate(ANIMS):
        offset = (index - (len(ANIMS) - 1) / 2.0) * SPACING
        # 메시 정면이 +Y라 액터 yaw는 바라볼 방향 - 90. 카메라 깊이 방향(yaw 45)을 보게 한다.
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, center + right * offset,
            unreal.Rotator(roll=0, pitch=0, yaw=45 - 90))
        actor.set_editor_property('tags', [unreal.Name(path)])
        component = actor.get_editor_property('skeletal_mesh_component')
        component.set_skeletal_mesh_asset(mesh)
        component.set_editor_property('visibility_based_anim_tick_option',
            unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    width = SPACING * len(ANIMS)
    # 화각 40도라 넷 이상이면 양 끝이 잘린다. PREVIEW_DISTANCE로 물러난다(넷이면 1450).
    distance = float(os.environ.get('PREVIEW_DISTANCE', max(700.0, width * 0.95)))
    unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
        center + unreal.Vector(0, 0, 100) - rotation.get_forward_vector() * distance, rotation)


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 300:
            raise TimeoutError('anim preview timed out')
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
            capture = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)[0].get_editor_property('capture_component2d')
            capture.set_editor_property('capture_every_frame', False)
            capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            capture.set_editor_property('fov_angle', 40)
            settings = capture.get_editor_property('post_process_settings')
            settings.set_editor_property('override_auto_exposure_bias', True)
            settings.set_editor_property('auto_exposure_bias', float(os.environ.get('PREVIEW_EXPOSURE', '5.0')))
            capture.set_editor_property('post_process_settings', settings)
            capture.set_editor_property('texture_target',
                unreal.RenderingLibrary.create_render_target2d(world, 960, 540, unreal.TextureRenderTargetFormat.RTF_RGBA8))
            state['capture'] = capture
            # 모두 같은 순간에 처음부터 다시 재생한다.
            # 에디터 세계에서 건 단일 애니 설정은 PIE 사본에 안 넘어오므로 태그로 찾아 여기서 건다.
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if not tags or tags[0] not in ANIMS:
                    continue
                component = actor.get_editor_property('skeletal_mesh_component')
                component.play_animation(unreal.load_asset(tags[0]), True)
            state.update(phase='capture', started=now)
            return
        if state['phase'] == 'capture' and now >= state['started'] + MOMENTS[state['moment']]:
            capture = state['capture']
            capture.capture_scene()
            file = f"{state['moment']:02d}_{int(MOMENTS[state['moment']] * 100):03d}.png"
            unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
            report['captures'].append({'seconds': MOMENTS[state['moment']], 'file': file})
            state['moment'] += 1
            if state['moment'] == len(MOMENTS):
                finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
