"""Shield look candidates for Aurora's Ice Armor: an Aurora mesh in each slot wrapped by a sphere mesh with a candidate
material, one scene capture per slot at the game camera pitch. Row 0 = material as is, row 1 = a dynamic instance with every
vector parameter whose name looks like a colour set to SHIELD_GREY. Writes material parameter names to shield-preview.json.
SHIELD_MATERIALS = comma list of material paths, SHIELD_MESH = sphere mesh path. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
MESH = '/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora'
IDLE = '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/Idle.Idle'
SPHERE = os.environ.get('SHIELD_MESH', '/Game/ParagonMinions/FX/Meshes/Shapes/SM_Sphere_Scale_Unit_100')
MATERIALS = os.environ['SHIELD_MATERIALS'].split(',')
GREY = [float(v) for v in os.environ.get('SHIELD_GREY', '0.55,0.58,0.62').split(',')]
# 몸을 감싸는 타원체 크기(cm): 가로 지름, 높이
SIZE = tuple(float(v) for v in os.environ.get('SHIELD_SIZE', '150,230').split(','))
SPACING = 450.0
MOMENTS = (2.0, 2.6)
state = {'phase': 'load', 'wall': time.monotonic(), 'moment': 0}
report = {'materials': MATERIALS, 'mesh': SPHERE, 'parameters': {}, 'captures': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'shield-preview.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def slot_tag(row, index):
    return f'shield_{row}_{index}'


def stage(editor_world):
    # 파이썬은 PIE 세계에 액터를 띄우지 못하므로 PIE 전에 에디터 세계에 놓는다. 칸마다 촬영 카메라 하나.
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + unreal.Vector(0, 0, -96)
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    ahead = unreal.Rotator(roll=0, pitch=0, yaw=45).get_forward_vector()
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    mesh = unreal.load_asset(MESH)
    sphere = unreal.load_asset(SPHERE)
    extent = sphere.get_bounds().box_extent
    scale = unreal.Vector(SIZE[0] / (2 * extent.x), SIZE[0] / (2 * extent.y), SIZE[1] / (2 * extent.z))
    report['sphere_extent'] = [extent.x, extent.y, extent.z]
    for row in range(2):
        for index, path in enumerate(MATERIALS):
            spot = center + right * ((index - (len(MATERIALS) - 1) / 2.0) * SPACING) + ahead * (row * SPACING)
            tag = unreal.Name(slot_tag(row, index))
            body = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, spot,
                unreal.Rotator(roll=0, pitch=0, yaw=-135 - 90))
            body.set_editor_property('tags', [tag])
            component = body.get_editor_property('skeletal_mesh_component')
            component.set_skeletal_mesh_asset(mesh)
            component.set_editor_property('visibility_based_anim_tick_option',
                unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            shell = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, spot + unreal.Vector(0, 0, SIZE[1] / 2 - 5))
            shell.set_editor_property('tags', [tag])
            shell_component = shell.get_editor_property('static_mesh_component')
            shell_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            shell_component.set_static_mesh(sphere)
            shell_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            shell_component.set_cast_shadow(False)
            shell.set_actor_scale3d(scale)
            material = unreal.load_asset(path)
            if material:
                shell_component.set_material(0, material)
            else:
                report.setdefault('missing', []).append(path)
            camera = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D,
                spot + unreal.Vector(0, 0, 100) - rotation.get_forward_vector() * 520, rotation)
            camera.set_editor_property('tags', [tag])


def tint(world):
    # 둘째 줄은 색 이름 벡터 값을 모두 회색으로 바꾼 동적 인스턴스를 입힌다. 값 이름은 재질마다 다르므로 같이 적어 둔다.
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        tags = [str(t) for t in actor.get_editor_property('tags')]
        if not tags or not tags[0].startswith('shield_'):
            continue
        _, row, index = tags[0].split('_')
        path = MATERIALS[int(index)]
        material = unreal.load_asset(path)
        if not material:
            continue
        base = material.get_base_material() if hasattr(material, 'get_base_material') else material
        vectors = [str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(base)]
        scalars = [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(base)]
        report['parameters'][path] = {'vectors': vectors, 'scalars': scalars}
        if row != '1':
            continue
        component = actor.get_editor_property('static_mesh_component')
        instance = component.create_dynamic_material_instance(0, material)
        changed = []
        for name in vectors:
            if any(key in name.lower() for key in ('color', 'colour', 'tint', 'emissive')):
                instance.set_vector_parameter_value(name, unreal.LinearColor(GREY[0], GREY[1], GREY[2], 1.0))
                changed.append(name)
        report['parameters'][path]['tinted'] = changed


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 420:
            raise TimeoutError('shield preview timed out')
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
            if now < 1.0:
                return
            pawn.set_actor_hidden_in_game(True)
            idle = unreal.load_asset(IDLE)
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if tags and tags[0].startswith('shield_') and idle:
                    actor.get_editor_property('skeletal_mesh_component').play_animation(idle, True)
            tint(world)
            state['captures'] = {}
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D):
                tags = [str(t) for t in actor.get_editor_property('tags')]
                if not tags or not tags[0].startswith('shield_'):
                    continue
                capture = actor.get_editor_property('capture_component2d')
                capture.set_editor_property('capture_every_frame', False)
                capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
                capture.set_editor_property('fov_angle', 40)
                settings = capture.get_editor_property('post_process_settings')
                settings.set_editor_property('override_auto_exposure_bias', True)
                settings.set_editor_property('auto_exposure_bias', float(os.environ.get('SHIELD_EXPOSURE', '4.0')))
                capture.set_editor_property('post_process_settings', settings)
                capture.set_editor_property('texture_target',
                    unreal.RenderingLibrary.create_render_target2d(world, 360, 360, unreal.TextureRenderTargetFormat.RTF_RGBA8))
                state['captures'][tags[0]] = capture
            state['phase'] = 'capture'
            return
        if state['phase'] == 'capture':
            if now < MOMENTS[state['moment']]:
                return
            for tag, capture in sorted(state['captures'].items()):
                capture.capture_scene()
                file = f"{tag}_{state['moment']}.png"
                unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
                report['captures'].append({'slot': tag, 'seconds': MOMENTS[state['moment']], 'file': file})
            state['moment'] += 1
            if state['moment'] == len(MOMENTS):
                finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
