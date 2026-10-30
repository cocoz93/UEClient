import json
from pathlib import Path
import sys
import traceback

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from context import profile, qa, configure_practice, write_json

try:
    configure_practice(True)
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipelineQA.Contract')
    contract = json.loads((qa / 'contract.json').read_text(encoding='utf-8'))
    assert contract['passed'], contract
    blueprint_class = unreal.EditorAssetLibrary.load_blueprint_class(profile['character_blueprint'])
    character = unreal.get_default_object(blueprint_class)
    movement = character.get_editor_property('character_movement')
    mesh = character.get_editor_property('mesh')
    skills = character.get_skills()
    combo = character.get_editor_property('combo_attacks')
    metadata = []
    for step in combo:
        montage = step.get_editor_property('montage')
        rate = step.get_editor_property('play_rate')
        hit_fraction = step.get_editor_property('hit_time_fraction')
        duration = montage.get_play_length() / (rate * montage.get_editor_property('rate_scale'))
        metadata.append({'montage': montage.get_path_name(), 'play_rate': rate,
                         'duration': duration, 'hit_fraction': hit_fraction,
                         'hit_time': duration * hit_fraction})
    definitions = []
    for index, definition in enumerate(skills.get_editor_property('skills') if profile['skills'] else []):
        definitions.append({name: definition.get_editor_property(name) for name in
                            ('damage', 'cooldown', 'range', 'action_time', 'recovery_time')})
        definitions[-1].update({'slot': index, 'name': str(definition.get_editor_property('name')), 'display_name': str(skills.get_skill_display_name(index))
                               if hasattr(skills, 'get_skill_display_name') else profile['skills'][index]['display_name'],
                               'animation': definition.get_editor_property('animation').get_path_name()
                                  if definition.get_editor_property('animation') else None,
                               **{name: definition.get_editor_property(name).get_path_name()
                                  if definition.get_editor_property(name) else None
                                  for name in ('cast_effect', 'impact_effect', 'cast_sound')}})
    result = {'passed': True, 'contract': contract, 'character_class': character.get_class().get_path_name(),
              'skill_component_class': skills.get_class().get_path_name(), 'skill_component_name': skills.get_name(),
              'mesh': mesh.get_editor_property('skeletal_mesh_asset').get_path_name(),
              'anim_class': mesh.get_editor_property('anim_class').get_path_name(),
              'movement': {name: movement.get_editor_property(name) for name in
                           ('max_walk_speed', 'max_acceleration', 'braking_deceleration_walking')},
              'rotation_rate': movement.get_editor_property('rotation_rate').yaw,
              'combo_restart_cooldown': character.get_editor_property('combo_restart_cooldown'),
              'basic_attack': metadata, 'skills': definitions}
    expected = profile['expected']
    assert result['movement'] == expected['movement'], result['movement']
    assert result['rotation_rate'] == expected['rotation_rate']
    assert abs(result['combo_restart_cooldown'] - expected['combo_restart_cooldown']) < 0.00001
    assert [step['play_rate'] for step in metadata] == expected['attack_rates']
    assert result['mesh'] == expected['mesh']
    assert result['anim_class'] == expected['anim_class']
    if expected.get('camera'):
        result['camera'] = {}
        for component_class, key in ((unreal.SpringArmComponent, 'spring_arm'),
                                     (unreal.CameraComponent, 'camera_component')):
            component = character.get_components_by_class(component_class)[0]
            result['camera'][key] = {}
            for name, desired in expected['camera'][key].items():
                actual = component.get_editor_property(name)
                if name == 'relative_rotation':
                    actual = [actual.pitch, actual.yaw, actual.roll]
                    assert all(abs(a - b) < 0.001 for a, b in zip(actual, desired))
                elif isinstance(desired, bool):
                    assert actual == desired
                else:
                    assert abs(float(actual) - desired) < 0.001
                result['camera'][key][name] = actual
    write_json('inspection.json', result)
except Exception as error:
    write_json('inspection.json', {'passed': False, 'error': str(error), 'traceback': traceback.format_exc()})
    unreal.log_error(traceback.format_exc())
finally:
    unreal.SystemLibrary.quit_editor()
