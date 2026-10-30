"""Gideon W magic circle: lay the current layer set and denser variants side by side on the training room floor
and capture them from the game camera, to choose a richer circle. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
GIDEON = '/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/'
BORDER = '/Game/TopDown/Characters/Gideon/FX/SM_Rune_Ring_Inner_NoShards'
RADIUS = 190.0
# (모형, 반경 대비 크기) — 현재 W와 같은 비율(테두리 1.0, 룬 글자·안쪽 겹원 0.8)에서 시작해 층을 더한다.
CURRENT = [(BORDER, 1.0), (GIDEON + 'SM_Rune_Ring_Outer', 0.8), (GIDEON + 'SM_Rune_Ring_Inner', 0.8)]
VARIANTS = {
    'A_current': CURRENT,
    'B_plus_triangle': CURRENT + [(GIDEON + 'SM_Ult_Runes_Inner', 0.5)],
    'C_plus_triangle_band': CURRENT + [(GIDEON + 'SM_Ult_Runes_Inner', 0.5), (GIDEON + 'SM_Ult_Runes_Outer', 1.18)],
}
# RIFT_VARIANTS = json 파일 {이름: [[모형 경로, 반경 대비 크기], ...]} 로 위 시안을 바꾼다(10-18 후보 모형 훑기).
if os.environ.get('RIFT_VARIANTS'):
    VARIANTS = json.loads(Path(os.environ['RIFT_VARIANTS']).read_text(encoding='utf-8'))
state = {'phase': 'load', 'wall': time.monotonic(), 'log': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'rift-circle-preview.json').write_text(json.dumps({'passed': error is None, 'error': error, 'log': state['log']},
        indent=1), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def lay(center, path, fraction):
    mesh = unreal.load_asset(path)
    if mesh is None:
        state['log'].append({'mesh': path, 'missing': True})
        return
    extent = mesh.get_bounds().box_extent
    axes = [extent.x, extent.y, extent.z]
    thin = axes.index(min(axes))
    # 가장 얇은 축이 위를 보게 눕힌다(X 얇음 = YZ 면 → pitch 90, Y 얇음 → roll 90, Z 얇음 → 그대로).
    rotation = [unreal.Rotator(roll=0, pitch=90, yaw=0), unreal.Rotator(roll=90, pitch=0, yaw=0),
                unreal.Rotator(roll=0, pitch=0, yaw=0)][thin]
    scale = RADIUS * fraction / max(max(axes), 1.0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, center, rotation)
    component = actor.get_editor_property('static_mesh_component')
    component.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(mesh)
    actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    state['log'].append({'mesh': path.split('/')[-1], 'fraction': fraction, 'thin_axis': 'XYZ'[thin], 'scale': round(scale, 2)})


def stage(world):
    # 파이썬은 PIE 세계에 액터를 못 띄우므로 에디터 세계에 놓아 복사되게 한다. 시작점 앞쪽에 가로로 셋.
    start = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)[0].get_actor_location()
    floor = start - unreal.Vector(0, 0, 95)
    for index, (name, layers) in enumerate(VARIANTS.items()):
        center = floor + unreal.Vector(150 + (index // 3) * 440, -440 + (index % 3) * 440, 3)
        state['log'].append({'variant': name, 'index': index})
        for path, fraction in layers:
            lay(center, path, fraction)


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 240:
            raise TimeoutError('rift circle preview timed out')
        if state['phase'] == 'load':
            stage(unreal.EditorLoadingAndSavingUtils.load_map(MAP))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            state['phase'] = 'run'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        if not pawn:
            return
        now = unreal.GameplayStatics.get_time_seconds(world)
        if state['phase'] == 'run' and now > 4:
            unreal.SystemLibrary.execute_console_command(world, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
            unreal.SystemLibrary.execute_console_command(world, 'CharacterVisualQA.Capture circles')
            state['phase'] = 'done'
            state['done_at'] = now
            return
        if state['phase'] == 'done' and now > state['done_at'] + 1.0:
            finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
