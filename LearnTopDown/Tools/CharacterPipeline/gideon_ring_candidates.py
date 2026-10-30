"""Lay candidate Gideon ring meshes flat on the training room floor (2 rows x 4) and capture them from the game camera,
to pick a clean circle for the W border. RING_MESHES = comma list of content paths. Saves no assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
ROOT = '/Game/ParagonGideon/FX/Meshes/'
MESHES = os.environ.get('RING_MESHES', ','.join([
    'Heroes/Gideon/SM_Rune_Ring_Inner', 'Heroes/Gideon/SM_Gideon_Ring_Inner', 'Heroes/Gideon/SM_Gideon_Ring_Outer',
    'Heroes/Gideon/SM_Gideon_Ring_Portal', 'Heroes/Gideon/SM_Circle_Curved_Edge', 'Heroes/Gideon/SM_Ult_Runes_Inner',
    'Heroes/Gideon/SM_Ult_Runes_Outer', 'Shapes/SM_ShockRing'])).split(',')
RADIUS = 130.0
state = {'phase': 'load', 'wall': time.monotonic(), 'log': []}


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'ring-candidates.json').write_text(json.dumps({'passed': error is None, 'error': error, 'log': state['log']},
        indent=1), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def stage(world):
    # 파이썬은 PIE 세계에 액터를 못 띄우므로 에디터 세계에 놓아 복사되게 한다. 시작점 앞쪽(화면 위)에 2줄 x 4칸.
    start = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)[0].get_actor_location()
    floor = start - unreal.Vector(0, 0, 95)
    for index, name in enumerate(MESHES):
        mesh = unreal.load_asset(ROOT + name)
        if mesh is None:
            state['log'].append({'mesh': name, 'missing': True})
            continue
        extent = mesh.get_bounds().box_extent
        axes = [extent.x, extent.y, extent.z]
        thin = axes.index(min(axes))
        # 가장 얇은 축이 위를 보게 눕힌다(X 얇음 = YZ 면 → pitch 90, Y 얇음 → roll 90, Z 얇음 → 그대로).
        rotation = [unreal.Rotator(roll=0, pitch=90, yaw=0), unreal.Rotator(roll=90, pitch=0, yaw=0),
                    unreal.Rotator(roll=0, pitch=0, yaw=0)][thin]
        scale = RADIUS / max(max(axes), 1.0)
        row, column = divmod(index, 4)
        location = floor + unreal.Vector(-150 + row * 330, -480 + column * 320, 3)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        component = actor.get_editor_property('static_mesh_component')
        component.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
        component.set_static_mesh(mesh)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        state['log'].append({'index': index, 'mesh': name, 'extent': [round(a, 1) for a in axes], 'thin_axis': 'XYZ'[thin],
                             'scale': round(scale, 2), 'row': row, 'column': column})


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 240:
            raise TimeoutError('ring candidates timed out')
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
            unreal.SystemLibrary.execute_console_command(world, 'CharacterVisualQA.Capture rings')
            state['phase'] = 'done'
            state['done_at'] = now
            return
        if state['phase'] == 'done' and now > state['done_at'] + 1.0:
            finish()
    except Exception:
        unreal.log_error(traceback.format_exc())
        finish(traceback.format_exc())


handle = unreal.register_slate_post_tick_callback(tick)
