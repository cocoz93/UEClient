"""Apply declared defaults to a character Blueprint; unchanged assets are never saved."""
import json
from pathlib import Path
import sys
import traceback

import unreal

sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'))
from context import profile, write_json

try:
    destination = profile['character_blueprint']
    if not destination.startswith('/Game/TopDown/'):
        raise ValueError('Only project-owned /Game/TopDown assets may be installed')
    asset = unreal.load_asset(destination)
    created = asset is None
    if created:
        parent = unreal.load_class(None, profile['parent_class'])
        if parent is None:
            raise ValueError('Native parent class is not compiled: ' + profile['parent_class'])
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', parent)
        folder, name = destination.rsplit('/', 1)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, factory)
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(destination)
    character = unreal.get_default_object(character_class)
    if character.get_skills().get_class().get_path_name() != profile['behavior_class']:
        raise ValueError('Native parent has the wrong skill component; choose the correct parent_class')
    changes = []

    def equal(current, desired):
        if isinstance(current, (float, int)) and isinstance(desired, (float, int)):
            return abs(float(current) - float(desired)) < 0.00001
        if isinstance(current, unreal.Object):
            return isinstance(desired, unreal.Object) and current.get_path_name() == desired.get_path_name()
        return current == desired

    def set_default(target, name, desired):
        if not equal(target.get_editor_property(name), desired):
            target.set_editor_property(name, desired)
            changes.append(target.get_name() + '.' + name)

    expected = profile['expected']
    mesh = character.get_editor_property('mesh')
    skeletal_mesh = unreal.load_asset(expected['mesh'])
    animation_class = unreal.load_class(None, expected['anim_class'])
    if skeletal_mesh is None or animation_class is None:
        raise ValueError('Required skeletal mesh or animation Blueprint is not installed')
    set_default(mesh, 'skeletal_mesh_asset', skeletal_mesh)
    set_default(mesh, 'anim_class', animation_class)
    movement = character.get_editor_property('character_movement')
    for name, value in expected['movement'].items():
        set_default(movement, name, value)
    rotation = movement.get_editor_property('rotation_rate')
    if abs(rotation.yaw - expected['rotation_rate']) > 0.00001:
        rotation.yaw = expected['rotation_rate']
        set_default(movement, 'rotation_rate', rotation)
    set_default(character, 'combo_restart_cooldown', expected['combo_restart_cooldown'])
    camera_defaults = expected.get('camera')
    if camera_defaults:
        for component_class, key in ((unreal.SpringArmComponent, 'spring_arm'),
                                     (unreal.CameraComponent, 'camera_component')):
            components = character.get_components_by_class(component_class)
            if len(components) != 1:
                raise ValueError('Expected exactly one native camera component: ' + key)
            for name, value in camera_defaults[key].items():
                if name == 'relative_rotation':
                    value = unreal.Rotator(pitch=value[0], yaw=value[1], roll=value[2])
                set_default(components[0], name, value)
    current_steps = character.get_editor_property('combo_attacks')
    desired_steps = profile.get('basic_attack', [])
    same_combo = len(current_steps) == len(desired_steps)
    if same_combo:
        for current, desired in zip(current_steps, desired_steps):
            same_combo &= (current.get_editor_property('montage').get_path_name() == desired['montage'] and
                           equal(current.get_editor_property('play_rate'), desired['play_rate']) and
                           equal(current.get_editor_property('hit_time_fraction'), desired['hit_fraction']))
    if not same_combo:
        steps = []
        for desired in desired_steps:
            montage = unreal.load_asset(desired['montage'])
            if montage is None:
                raise ValueError('Required attack montage is not installed: ' + desired['montage'])
            step = unreal.BasicAttackComboStep()
            step.set_editor_property('montage', montage)
            step.set_editor_property('play_rate', desired['play_rate'])
            step.set_editor_property('hit_time_fraction', desired['hit_fraction'])
            steps.append(step)
        character.set_editor_property('combo_attacks', steps)
        changes.append('combo_attacks')
    skill_defaults = profile.get('skill_defaults')
    if skill_defaults is not None:
        component = character.get_skills()
        definitions = component.get_editor_property('skills')
        if len(definitions) != len(skill_defaults):
            raise ValueError('Skill definition count differs from the native behavior contract')
        skills_changed = False
        for index, (definition, desired) in enumerate(zip(definitions, skill_defaults)):
            for name, value in desired.items():
                if name in ('animation', 'cast_effect', 'impact_effect', 'cast_sound'):
                    value = unreal.load_asset(value) if value else None
                    if value is None and desired[name]:
                        raise ValueError('Required skill asset is not installed: ' + desired[name])
                if name == 'name':
                    value = unreal.Name(value)
                if not equal(definition.get_editor_property(name), value):
                    definition.set_editor_property(name, value)
                    changes.append(f'skills[{index}].{name}')
                    skills_changed = True
        if skills_changed:
            component.set_editor_property('skills', definitions)
    if created or changes:
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('Failed to save character Blueprint')
    write_json('installation.json', {'passed': True, 'created': created, 'changed_defaults': changes,
                                      'saved': bool(created or changes), 'asset': destination})
except Exception as error:
    write_json('installation.json', {'passed': False, 'error': str(error), 'traceback': traceback.format_exc()})
    unreal.log_error(traceback.format_exc())
finally:
    unreal.SystemLibrary.quit_editor()
