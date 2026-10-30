"""Inspect real Countess/Sparrow PIE cameras without modifying maps or assets."""
import json
import os
from pathlib import Path
import time
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT'])
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
maps = [('countess', '/Game/TopDown/Lvl_TopDown'), ('sparrow', '/Game/TopDown/Maps/Lvl_Sparrow')]
state = {'index': 0, 'phase': 'load', 'wall': time.monotonic(), 'rows': []}


def value(item):
    if isinstance(item, unreal.Vector):
        return [item.x, item.y, item.z]
    if isinstance(item, unreal.Rotator):
        return [item.pitch, item.yaw, item.roll]
    if isinstance(item, (str, bool, int, float)) or item is None:
        return item
    return str(item)


def properties(component, names):
    result = {'name': component.get_name(), 'class': component.get_class().get_path_name(),
              'world_location': value(component.get_world_location()),
              'world_rotation': value(component.get_world_rotation())}
    for name in names:
        try:
            result[name] = value(component.get_editor_property(name))
        except Exception as error:
            result[name] = {'unavailable': str(error)}
    return result


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    (qa / 'camera-compare.json').write_text(json.dumps({'passed': error is None, 'rows': state['rows'],
        'error': str(error) if error else None}, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if time.monotonic() - state['wall'] > 150:
            raise TimeoutError('PIE camera comparison timed out')
        editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if state['phase'] == 'load':
            if state['index'] == len(maps):
                finish()
                return
            unreal.EditorLoadingAndSavingUtils.load_map(maps[state['index']][1])
            editor.editor_request_begin_play()
            state['phase'] = 'world'
            return
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if state['phase'] == 'between':
            if world is None:
                state['phase'] = 'load'
            return
        pawn = unreal.GameplayStatics.get_player_character(world, 0) if world else None
        controller = unreal.GameplayStatics.get_player_controller(world, 0) if world else None
        if not pawn or not controller or unreal.GameplayStatics.get_time_seconds(world) < 0.35:
            return
        camera = controller.player_camera_manager
        row = {'character': maps[state['index']][0], 'map': maps[state['index']][1],
            'pawn_class': pawn.get_class().get_path_name(), 'pawn_location': value(pawn.get_actor_location()),
            'pawn_rotation': value(pawn.get_actor_rotation()),
            'view_location': value(camera.get_camera_location()), 'view_rotation': value(camera.get_camera_rotation()),
            'view_fov': camera.get_fov_angle(),
            'arms': [properties(c, ('target_arm_length', 'relative_location', 'relative_rotation', 'socket_offset',
                'target_offset', 'absolute_rotation', 'use_pawn_control_rotation', 'do_collision_test',
                'inherit_pitch', 'inherit_yaw', 'inherit_roll', 'enable_camera_lag', 'enable_camera_rotation_lag',
                'camera_lag_speed', 'camera_rotation_lag_speed', 'camera_lag_max_distance',
                'use_camera_lag_substepping', 'camera_lag_max_time_step'))
                for c in pawn.get_components_by_class(unreal.SpringArmComponent)],
            'cameras': [properties(c, ('relative_location', 'relative_rotation', 'projection_mode', 'field_of_view',
                'ortho_width', 'ortho_near_clip_plane', 'ortho_far_clip_plane', 'aspect_ratio',
                'constrain_aspect_ratio', 'use_pawn_control_rotation', 'auto_calculate_ortho_planes'))
                for c in pawn.get_components_by_class(unreal.CameraComponent)]}
        state['rows'].append(row)
        state['index'] += 1
        editor.editor_request_end_play()
        state['phase'] = 'between'
    except Exception as error:
        unreal.log_error(traceback.format_exc())
        finish(error)


handle = unreal.register_slate_post_tick_callback(tick)
