"""Read Sparrow source assets without saving or modifying their packages."""
import json
import os
from pathlib import Path
import sys
import traceback

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / 'Tools/CharacterPipeline'))
if os.environ.get('CHARACTER_PIPELINE_JOB'):
    from context import qa
else:
    qa = Path(os.environ.get('SPARROW_QA_OUTPUT', str(root / 'Saved/QA/SparrowInventory'))).resolve()
    if not qa.is_relative_to(root / 'Saved/QA'):
        raise ValueError('Sparrow inventory output must be inside this project Saved/QA')
    qa.mkdir(parents=True, exist_ok=True)
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')

HERO = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
ANIM = HERO + '/Animations'
FX = '/Game/ParagonSparrow/FX/Particles/Sparrow'
PRIMARY_NAMES = ('Primary_Fire_Med', 'Q_Ability', 'RMB_Drawback', 'RMB_Loop',
                 'RMB_Fire', 'R_Ability_Med_Fire', 'idle', 'Jog_Fwd')


def object_path(value):
    return value.get_path_name() if value else None


def editor_properties(obj, names):
    values = {}
    unavailable = {}
    for name in names:
        try:
            value = obj.get_editor_property(name)
            if hasattr(value, 'get_path_name'):
                value = object_path(value)
            elif not isinstance(value, (str, int, float, bool, type(None))):
                value = str(value)
            values[name] = value
        except Exception as error:
            unavailable[name] = str(error)
    return {'values': values, 'unavailable': unavailable}


def summary(path):
    asset = unreal.load_asset(path)
    if not asset:
        return {'path': path, 'present': False}
    result = {'path': object_path(asset), 'present': True, 'class': object_path(asset.get_class())}
    if isinstance(asset, unreal.AnimSequenceBase):
        result['length'] = asset.get_play_length()
        result['animation_properties'] = editor_properties(asset, (
            'skeleton', 'rate_scale', 'enable_root_motion', 'root_motion_root_lock',
            'force_root_lock', 'use_normalized_root_motion_scale', 'notifies'))
        result['notifies'] = []
        for event in unreal.AnimationLibrary.get_animation_notify_events(asset):
            notify = event.get_editor_property('notify')
            state = event.get_editor_property('notify_state_class')
            result['notifies'].append({
                'name': str(event.get_editor_property('notify_name')),
                'trigger_time': unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event),
                'duration': unreal.AnimationLibrary.get_anim_notify_event_duration(event),
                'notify_path': object_path(notify),
                'notify_class': object_path(notify.get_class()) if notify else None,
                'notify_state_path': object_path(state),
                'notify_state_class': object_path(state.get_class()) if state else None,
                'notify_properties': editor_properties(notify, (
                    'template', 'socket_name', 'location_offset', 'rotation_offset', 'attached',
                    'sound', 'volume_multiplier', 'pitch_multiplier')) if notify else None})
        if isinstance(asset, unreal.AnimMontage):
            result['montage_properties'] = editor_properties(asset, ('slot_anim_tracks', 'composite_sections', 'blend_in', 'blend_out'))
    if isinstance(asset, unreal.Blueprint):
        result['blueprint_properties'] = editor_properties(asset, ('parent_class',))
        generated = asset.generated_class()
        result['generated_class'] = object_path(generated)
        if generated:
            cdo = unreal.get_default_object(generated)
            result['cdo'] = {'path': object_path(cdo), 'class': object_path(cdo.get_class())}
            if isinstance(cdo, unreal.Character):
                mesh = cdo.get_editor_property('mesh')
                result['cdo']['mesh'] = editor_properties(mesh, ('skeletal_mesh_asset', 'anim_class', 'relative_location', 'relative_rotation'))
                movement = cdo.get_editor_property('character_movement')
                result['cdo']['movement'] = editor_properties(movement, ('max_walk_speed', 'max_acceleration', 'braking_deceleration_walking', 'rotation_rate'))
            if isinstance(cdo, unreal.AnimInstance):
                result['cdo']['known_variables'] = editor_properties(cdo, (
                    'speed', 'direction', 'is_in_air', 'yaw_delta', 'pitch',
                    'is_moving', 'is_targeting', 'is_in_travel_mode', 'root_motion_mode'))
    if isinstance(asset, unreal.SkeletalMesh):
        result['mesh_properties'] = editor_properties(asset, ('skeleton', 'physics_asset', 'materials', 'sockets'))
    return result


try:
    all_assets = unreal.EditorAssetLibrary.list_assets('/Game/ParagonSparrow', recursive=True, include_folder=False)
    all_assets = sorted(set(all_assets))
    core_paths = [HERO + '/SparrowPlayerCharacter', HERO + '/Sparrow_AnimBlueprint',
                  HERO + '/Skins/Rogue/Meshes/Sparrow_Rogue']
    core_paths += [ANIM + '/' + name for name in PRIMARY_NAMES]
    selected = list(core_paths)
    selected += [path for path in all_assets if path.startswith(ANIM + '/') and
                 ('Montage' in path or '/Blendspaces/' in path)]
    selected += [path for path in all_assets if path.startswith(FX + '/Skins/Rogue/') or
                 path.startswith(FX + '/Abilities/RainOfArrows/')]
    selected = list(dict.fromkeys(selected))
    report = {'passed': False, 'read_only': True, 'source_root': '/Game/ParagonSparrow',
              'asset_count': len(all_assets), 'selected_assets': [summary(path) for path in selected]}
    native_path = qa / 'sparrow-native-inventory.json'
    if native_path.exists():
        native_path.unlink()
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + path + '"' for path in selected))
    report['read_only_asset_presence_passed'] = all(asset['present'] for asset in report['selected_assets'])
    report['passed'] = report['read_only_asset_presence_passed']
    if native_path.exists():
        native = json.loads(native_path.read_text(encoding='utf-8-sig'))
        report['native_report'] = str(native_path)
        report['native_asset_count'] = len(native['assets'])
        report['native_dump_available'] = True
        report['native_pending'] = False
        report['passed'] &= bool(native.get('passed'))
    else:
        report['native_dump_available'] = False
        report['native_pending'] = True
        report['native_report'] = None
        report['passed'] = False
        report['native_dump_note'] = 'Build the editor module for CDO variables, graph connections, bones and particle module details'
    (qa / 'sparrow-inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('SPARROW_INVENTORY ' + json.dumps({'passed': report['passed'], 'path': str(qa / 'sparrow-inventory.json')}))
except Exception as error:
    (qa / 'sparrow-inventory.json').write_text(json.dumps({'passed': False, 'read_only': True,
        'error': str(error), 'traceback': traceback.format_exc()}, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log_error(traceback.format_exc())
finally:
    if os.environ.get('SPARROW_INVENTORY_KEEP_EDITOR') != '1':
        unreal.SystemLibrary.quit_editor()
