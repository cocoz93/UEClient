"""PIE in the dark training room: spawn each particle system alone on a stage and capture it at several moments.
FX_FOLDER (content path) picks the folder; default = Aurora non-ability FX.
FX_COMBOS (json file) instead stages named combinations: {name: [{path, right, ahead, up, yaw, pitch, roll, scale, delay, beam}, ...]}
where beam = [right, ahead, up] of a user-set beam end point,
move = [right, ahead, up] it flies to in travel seconds (falling projectiles),
life = seconds after which it is destroyed (redrawn bolts, one at a time).
An item with mesh (static mesh path) instead of path places that model from [right, ahead, up] to span = [right, ahead, up]:
its X extent is stretched to the span, thick scales Y/Z, material (optional) overrides every slot, spin = random roll and mirror.
Or with rot = [pitch, yaw, roll] (world) and scale3 the model sits at [right, ahead, up] unstretched.
vectors / scalars = {parameter: value} set on a dynamic copy of the slot material (recolouring pack materials).
Mesh items need FX_MESH_POOL = how many hidden model actors to lay down before PIE (at most that many visible at once).
where right/ahead are cm along the game camera's screen right / depth. Saves no assets."""
import json
import os
from pathlib import Path
import random
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
FOLDER = os.environ.get('FX_FOLDER', '/Game/ParagonAurora/FX/Particles/Aurora')
MOMENTS = tuple(float(m) for m in os.environ.get('FX_MOMENTS', '0.2,0.6,1.2,2.2').split(','))
state = {'phase': 'load', 'wall': time.monotonic(), 'index': 0, 'moment': 0, 'until': 0.0, 'live': None}
report = {'folder': FOLDER, 'captures': [], 'effects': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report['passed'] = error is None
    report['error'] = error
    (qa / 'fx-gallery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def place_camera(editor_world):
    # 파이썬은 PIE 세계에 액터를 띄우지 못하므로 PIE 전에 에디터 세계에 촬영 카메라를 놓는다. 게임과 같은 각도(-50°/45°).
    start = unreal.GameplayStatics.get_all_actors_of_class(editor_world, unreal.PlayerStart)[0]
    center = start.get_actor_location() + start.get_actor_forward_vector() * 500 + unreal.Vector(0, 0, -96)
    # FX_PITCH = 모양 확인용 다른 내려다보는 각(예: -5 = 옆에서). 기본은 게임 각.
    rotation = unreal.Rotator(roll=0, pitch=float(os.environ.get('FX_PITCH', '-50')), yaw=45)
    # FX_DISTANCE = 카메라 거리. 게임 화면과 같은 굵기로 보려면 2000(카메라 붐 길이)·FX_FOV 55·FX_RES 1520x864.
    distance = float(os.environ.get('FX_DISTANCE', '1100'))
    unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, center - rotation.get_forward_vector() * distance, rotation)
    # 모형 부품(mesh 항목)용 액터 묶음도 PIE 전에 숨겨 깔아 두고 PIE에서 옮겨 쓴다(add_component_by_class도 파이썬에 없음).
    for _ in range(int(os.environ.get('FX_MESH_POOL', '0'))):
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, center - unreal.Vector(0, 0, 5000), unreal.Rotator())
        actor.set_editor_property('tags', ['fx_mesh_pool'])
        component = actor.get_editor_property('static_mesh_component')
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_cast_shadow(False)
        actor.set_actor_hidden_in_game(True)
    return center


def ready_camera(world):
    capture = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SceneCapture2D)[0].get_editor_property('capture_component2d')
    capture.set_editor_property('capture_every_frame', False)
    capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    capture.set_editor_property('fov_angle', float(os.environ.get('FX_FOV', '28')))
    # 어두운 수련장에서 빛을 받는 얼음 재질이 검게 묻히지 않도록 노출만 올린다(이펙트 자체는 그대로).
    settings = capture.get_editor_property('post_process_settings')
    settings.set_editor_property('override_auto_exposure_bias', True)
    settings.set_editor_property('auto_exposure_bias', float(os.environ.get('FX_EXPOSURE', '3.0')))
    capture.set_editor_property('post_process_settings', settings)
    capture.set_editor_property('post_process_blend_weight', 1.0)
    capture.set_editor_property('texture_target',
        unreal.RenderingLibrary.create_render_target2d(world, *(int(v) for v in os.environ.get('FX_RES', '640x480').split('x')),
                                                       unreal.TextureRenderTargetFormat.RTF_RGBA8))
    return capture


def release(thing):
    """다 쓴 것 치우기: 입자 효과는 지우고, 모형 묶음의 액터는 숨겨 묶음에 돌려준다."""
    if not thing:
        return
    if isinstance(thing, unreal.Actor):
        thing.set_actor_hidden_in_game(True)
        state['pool'].append(thing)
        return
    thing.deactivate()
    thing.destroy_component(thing)


def spawn_mesh(world, item, place):
    if 'pool' not in state:
        state['pool'] = list(unreal.GameplayStatics.get_all_actors_with_tag(world, 'fx_mesh_pool'))
    mesh = unreal.load_asset(item['mesh'])
    if not mesh:
        report.setdefault('missing', []).append(item['mesh'])
        return None
    if not state['pool']:
        report.setdefault('pool_empty', 0)
        report['pool_empty'] += 1
        return None
    actor = state['pool'].pop(0)
    component = actor.get_editor_property('static_mesh_component')
    component.set_static_mesh(mesh)
    material = unreal.load_asset(item['material']) if item.get('material') else None
    for slot in range(component.get_num_materials()):
        component.set_material(slot, material or mesh.get_material(slot))
        # vectors / scalars (optional) = 그 재질 사본(MID)의 값을 바꿔 띄운다(팩 재질 색 바꾸기 시험)
        if item.get('vectors') or item.get('scalars'):
            dynamic = component.create_dynamic_material_instance(slot, material or mesh.get_material(slot))
            for name, rgba in item.get('vectors', {}).items():
                dynamic.set_vector_parameter_value(name, unreal.LinearColor(*rgba))
            for name, number in item.get('scalars', {}).items():
                dynamic.set_scalar_parameter_value(name, number)
    start = place(item.get('right', 0.0), item.get('ahead', 0.0), item.get('up', 0.0))
    if 'rot' in item:
        # rot = [pitch, yaw, roll] 월드 방향 그대로 · scale3 = 축마다 배율(모형을 늘이지 않고 원래 꼴로 놓는다)
        actor.set_actor_rotation(unreal.Rotator(roll=item['rot'][2], pitch=item['rot'][0], yaw=item['rot'][1]), False)
        actor.set_actor_scale3d(unreal.Vector(*item.get('scale3', [1.0, 1.0, 1.0])))
        actor.set_actor_location(start, False, False)
        actor.set_actor_hidden_in_game(False)
        return actor
    end = place(*item['span'])
    bounds = mesh.get_bounds()
    low, length = bounds.origin.x - bounds.box_extent.x, 2.0 * bounds.box_extent.x
    rotation = (end - start).rotator()
    roll = random.uniform(0.0, 360.0) if item.get('spin') else item.get('roll', 0.0)
    rotation = unreal.Rotator(roll=roll, pitch=rotation.pitch, yaw=rotation.yaw)
    stretch = (end - start).length() / length
    thick = item.get('thick', 1.0) * (random.choice((-1.0, 1.0)) if item.get('spin') else 1.0)
    actor.set_actor_rotation(rotation, False)
    actor.set_actor_scale3d(unreal.Vector(stretch, thick, abs(thick)))
    # 모형의 X 시작점(low)이 시작 위치에 오게 민다.
    actor.set_actor_location(start - rotation.get_forward_vector() * (low * stretch), False, False)
    actor.set_actor_hidden_in_game(False)
    return actor


def spawn_item(world, item):
    if 'mesh' in item:
        right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
        ahead = unreal.Rotator(roll=0, pitch=0, yaw=45).get_forward_vector()
        actor = spawn_mesh(world, item, lambda r, a, u: state['center'] + right * r + ahead * a + unreal.Vector(0, 0, u))
        if actor and 'life' in item:
            state.setdefault('kills', []).append((actor, state['now'] + item['life']))
        if actor:
            state['live'].append(actor)
        return
    template = unreal.load_asset(item['path'])
    if not template:
        report.setdefault('missing', []).append(item['path'])
        return
    # 화면 오른쪽 = 게임 카메라 yaw 45°의 오른쪽(yaw 135), 깊이 = 카메라가 보는 쪽(yaw 45)
    right = unreal.Rotator(roll=0, pitch=0, yaw=135).get_forward_vector()
    ahead = unreal.Rotator(roll=0, pitch=0, yaw=45).get_forward_vector()
    def place(r, a, u):
        return state['center'] + right * r + ahead * a + unreal.Vector(0, 0, u)
    location = place(item.get('right', 0.0), item.get('ahead', 0.0), item.get('up', 0.0))
    scale = item.get('scale', 1.0)
    # scale3 = [x, y, z] 축마다 다른 배율(눕힌 번개를 길이 축만 늘이기).
    scale3 = unreal.Vector(*item['scale3']) if 'scale3' in item else unreal.Vector(scale, scale, scale)
    component = unreal.GameplayStatics.spawn_emitter_at_location(world, template, location,
        unreal.Rotator(roll=item.get('roll', 0.0), pitch=item.get('pitch', 0.0), yaw=item.get('yaw', 0.0)),
        scale3, False)
    if component and 'move' in item:
        rotation = (place(*item['move']) - location).rotator()
        component.set_world_rotation(rotation, False, False)
        state.setdefault('movers', []).append((component, location, place(*item['move']), state['now'], item.get('travel', 0.5)))
    if component and 'beam' in item:
        for emitter in range(4):
            component.set_beam_source_point(emitter, location, 0)
            component.set_beam_target_point(emitter, place(*item['beam']), 0)
    if component and 'life' in item:
        # life = 이 초가 지나면 지운다(다시 긋는 번개를 한 번에 하나만 보이게).
        state.setdefault('kills', []).append((component, state['now'] + item['life']))
    state['live'].append(component)


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 600:
            raise TimeoutError('FX gallery timed out')
        if state['phase'] == 'load':
            if os.environ.get('FX_COMBOS'):
                combos = json.loads(Path(os.environ['FX_COMBOS']).read_text(encoding='utf-8'))
                state['paths'] = list(combos)
                state['combos'] = combos
            else:
                registry = unreal.AssetRegistryHelpers.get_asset_registry()
                assets = registry.get_assets_by_path(FOLDER, recursive=True)
                state['paths'] = sorted(str(a.package_name) for a in assets if str(a.asset_class_path.asset_name) == 'ParticleSystem')
            report['effects'] = state['paths']
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
        state['now'] = now
        for component, start, end, t0, travel in state.get('movers', []):
            if component:
                alpha = min(max((now - t0) / travel, 0.0), 1.0)
                component.set_world_location(start + (end - start) * alpha, False, False)
        for component, until in [k for k in state.get('kills', []) if now >= k[1]]:
            state['kills'].remove((component, until))
            if component in state['live']:
                state['live'].remove(component)
                release(component)
        if state['phase'] == 'wait':
            if now < 3:
                return
            pawn.set_actor_hidden_in_game(True)
            state['camera'] = ready_camera(world)
            state['phase'] = 'spawn'
            return
        if state['phase'] == 'capture' and state.get('pending'):
            # 조합의 늦게 나오는 조각을 제 시각에 띄운다.
            for item in [i for i in state['pending'] if now >= state['started'] + i.get('delay', 0.0)]:
                state['pending'].remove(item)
                spawn_item(world, item)
        if now < state['until']:
            return
        if state['phase'] == 'spawn':
            if state['index'] == len(state['paths']):
                finish()
                return
            state['live'] = []
            if 'combos' in state:
                items = state['combos'][state['paths'][state['index']]]
                state['pending'] = [i for i in items if i.get('delay', 0.0) > 0.0]
                for item in items:
                    if item.get('delay', 0.0) <= 0.0:
                        spawn_item(world, item)
            else:
                spawn_item(world, {'path': state['paths'][state['index']]})
            state.update(phase='capture', moment=0, started=now, until=now + MOMENTS[0])
            return
        if state['phase'] == 'capture':
            name = state['paths'][state['index']].rsplit('/', 1)[-1]
            capture = state['camera']
            capture.capture_scene()
            file = f"{state['index']:02d}_{name}_{state['moment']}.png"
            unreal.RenderingLibrary.export_render_target(world, capture.get_editor_property('texture_target'), str(qa), file)
            report['captures'].append({'effect': name, 'seconds': MOMENTS[state['moment']], 'file': file})
            state['moment'] += 1
            if state['moment'] < len(MOMENTS):
                state['until'] = state['started'] + MOMENTS[state['moment']]
                return
            for component in state['live']:
                release(component)
            state['live'] = []
            state['pending'] = []
            state['movers'] = []
            state['kills'] = []
            state['index'] += 1
            state.update(phase='spawn', until=now + 0.6)
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
