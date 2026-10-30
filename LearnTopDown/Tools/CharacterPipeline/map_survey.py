"""Capture candidate maps from above and at the game camera angle (arm 2000, pitch -50, yaw 45, FOV 55).
SURVEY_MAPS = comma list of map paths. A scale mesh is placed at each spot. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAPS = os.environ.get('SURVEY_MAPS', '/Game/SampleMap/ParagonSample,/Game/SampleMap/ParagonSample_Daylight').split(',')
SCALE_MESH = '/Game/ParagonAurora/Characters/Heroes/Aurora/Meshes/Aurora'
WARMUP = float(os.environ.get('SURVEY_WARMUP', '240'))
SETTLE = 6.0
# 실내 맵은 천장이 바닥 탐색과 촬영을 가린다 — 메시 이름에 이 낱말이 든 액터는 숨기고 바닥 탐색에서도 뺀다(쉼표 목록).
HIDE = [t for t in os.environ.get('SURVEY_HIDE', '').split(',') if t]
state = {'map': 0, 'phase': 'load', 'wall': time.monotonic()}
report = {'maps': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    report['passed'] = error is None
    report['error'] = error
    (qa / 'map-survey.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def ground_bounds(world):
    # 바닥 범위는 지형(Landscape)이 있으면 그것, 없으면 하늘 구 같은 거대 물체를 뺀 스태틱 메시들로 잡는다.
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Landscape)
    if not actors:
        actors = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor)
                  if a.get_actor_bounds(False)[1].x < 20000]
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    for actor in actors:
        origin, extent = actor.get_actor_bounds(False)
        for i, (o, e) in enumerate(((origin.x, extent.x), (origin.y, extent.y), (origin.z, extent.z))):
            lo[i] = min(lo[i], o - e)
            hi[i] = max(hi[i], o + e)
    return lo, hi, len(actors)


def trace_down(world, x, y, top, bottom):
    # 나무·풀(폴리지) 윗면에 걸리면 그 아래부터 다시 쏴서 실제 바닥을 찾는다.
    for _ in range(12):
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, top), unreal.Vector(x, y, bottom),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, state.get('hidden', []), unreal.DrawDebugTrace.NONE, True)
        if hit is None or not hit.to_tuple()[0]:
            return None
        point = hit.to_tuple()[4]
        actor = next((v for v in hit.to_tuple() if isinstance(v, unreal.Actor)), None)
        if actor is None or 'Foliage' not in actor.get_class().get_name():
            return point
        top = point.z - 5
    return None


def plan_shots(world):
    lo, hi, count = ground_bounds(world)
    entry = {'map': MAPS[state['map']], 'bounds': [lo, hi], 'ground_actors': count, 'shots': []}
    shots = []
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    size = max(hi[0] - lo[0], hi[1] - lo[1])
    shots.append(('overview', unreal.Vector(cx, cy, hi[2] + size * 0.95), unreal.Rotator(roll=0, pitch=-89.9, yaw=0), None))
    spots = [unreal.Vector(s.get_actor_location().x, s.get_actor_location().y, 0)
             for s in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)][:2]
    for fx, fy in ((0.5, 0.5), (0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7), (0.5, 0.2), (0.5, 0.8)):
        spots.append(unreal.Vector(lo[0] + (hi[0] - lo[0]) * fx, lo[1] + (hi[1] - lo[1]) * fy, 0))
    rotation = unreal.Rotator(roll=0, pitch=-50, yaw=45)
    for index, spot in enumerate(spots):
        point = trace_down(world, spot.x, spot.y, hi[2] + 1000, lo[2] - 1000)
        if point is None:
            entry['shots'].append({'spot': index, 'skipped': 'no ground hit'})
            continue
        target = unreal.Vector(point.x, point.y, point.z + 90)
        shots.append((f'game_{index:02d}', target - rotation.get_forward_vector() * 2000, rotation, point))
    # 화면을 덮는 큰 덩어리가 무엇인지 가리기 위해 가장 큰 스태틱 메시 10개를 남긴다.
    sized = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
        extent = a.get_actor_bounds(False)[1]
        mesh = a.static_mesh_component.static_mesh
        sized.append((extent.x * extent.y, a.get_actor_label(), mesh.get_name() if mesh else None, [round(extent.x), round(extent.y), round(extent.z)]))
    entry['largest'] = [s[1:] for s in sorted(sized, key=lambda s: -s[0])[:10]]
    report['maps'].append(entry)
    return shots


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 3000:
            raise TimeoutError('map survey timed out')
        if state['phase'] == 'load':
            if state['map'] == len(MAPS):
                finish()
                return
            # 맵 로딩 중에도 슬레이트 틱이 돌아 이 콜백이 다시 불린다 — 먼저 단계를 바꿔 중복 로드를 막는다.
            state['phase'] = 'loading'
            map_path, _, extra = MAPS[state['map']].partition('+')
            world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
            if extra:
                # 조명만 담긴 맵을 하위 레벨로 얹는다(저장하지 않음).
                unreal.EditorLevelUtils.add_level_to_world(world, extra, unreal.LevelStreamingAlwaysLoaded)
            report.setdefault('lights', {})[MAPS[state['map']]] = sorted(
                f"{a.get_class().get_name()}:{a.get_actor_label()}" for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
                if any(k in a.get_class().get_name() for k in ('Light', 'Sky', 'Fog', 'PostProcess')))
            capture_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
            capture = capture_actor.get_editor_property('capture_component2d')
            # 한 장만 찍으면 자동 노출이 기본값에 머물러 맵마다 새까맣거나 하얗게 날아간다 — 매 프레임 돌려 노출을 따라오게 한다.
            capture.set_editor_property('capture_every_frame', True)
            capture.set_editor_property('always_persist_rendering_state', True)
            capture.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            capture.set_editor_property('fov_angle', 55)
            capture.set_editor_property('texture_target',
                unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8))
            scale = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, -100000))
            scale.get_editor_property('skeletal_mesh_component').set_skeletal_mesh_asset(unreal.load_asset(SCALE_MESH))
            hidden = []
            for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
                mesh = a.static_mesh_component.static_mesh
                if mesh and any(t.lower() in mesh.get_name().lower() for t in HIDE):
                    hidden.append(a)
            # hidden_actors 는 편집 속성으로 못 바꾼다(템플릿 오류) — 액터별 호출로 숨긴다.
            for a in hidden:
                capture.hide_actor_components(a)
            state['hidden'] = hidden
            if os.environ.get('SURVEY_NOFOG'):
                # 짙은 높이 안개는 2000 거리 카메라에서 바닥 무늬를 단색으로 덮는다 — 비교용으로 끈다(저장 안 함).
                for fog in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ExponentialHeightFog):
                    fog.get_component_by_class(unreal.ExponentialHeightFogComponent).set_visibility(False)
            report.setdefault('hidden', {})[MAPS[state['map']]] = len(hidden)
            state.update(world=world, actor=capture_actor, capture=capture, scale=scale, shots=plan_shots(world),
                         shot=0, phase='warm', since=time.monotonic())
            return
        if state['phase'] == 'warm':
            # 셰이더 컴파일·텍스처 스트리밍이 끝날 시간을 준다(첫 맵만 길게).
            if time.monotonic() - state['since'] < (WARMUP if state['map'] == 0 else 60):
                return
            state['phase'] = 'move'
        if state['phase'] == 'move':
            if state['shot'] == len(state['shots']):
                state.update(map=state['map'] + 1, phase='load')
                return
            name, location, rotation, foot = state['shots'][state['shot']]
            state['actor'].set_actor_location_and_rotation(location, rotation, False, False)
            if foot is not None:
                state['scale'].set_actor_location_and_rotation(foot, unreal.Rotator(roll=0, pitch=0, yaw=-45), False, False)
            else:
                state['scale'].set_actor_location(unreal.Vector(0, 0, -100000), False, False)
            state.update(phase='settle', since=time.monotonic())
            return
        if state['phase'] == 'settle' and time.monotonic() - state['since'] >= SETTLE:
            name = state['shots'][state['shot']][0]
            state['capture'].capture_scene()
            file = f"{Path(MAPS[state['map']]).name}_{name}.png"
            unreal.RenderingLibrary.export_render_target(state['world'], state['capture'].get_editor_property('texture_target'), str(qa), file)
            foot = state['shots'][state['shot']][3]
            report['maps'][-1]['shots'].append({'name': name, 'file': file,
                'foot': [foot.x, foot.y, foot.z] if foot is not None else None})
            state.update(shot=state['shot'] + 1, phase='move')
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
