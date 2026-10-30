"""Author a hood-only ivory MI; never save the imported material, mesh or BP."""
import hashlib
import json
from pathlib import Path

import unreal

SOURCE = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Materials/M_Sparrow_Rogue_Cloak'
MESH = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue'
DESTINATION = '/Game/TopDown/Characters/Sparrow/Materials/MI_Sparrow_IvoryHood'
HOOD_SLOT = 'M14_CloakHood'

# Linear cloth tints only. Existing mask textures, micro normals, roughness,
# leather and metallic trim parameters remain inherited from the source.
CLOTH_COLORS = {
    'Cloak_whool_intA': (0.88, 0.83, 0.72, 1.0),
    'Cloak_whool_intB': (0.79, 0.79, 0.75, 1.0),
    'Cloak_whool_intC': (0.72, 0.68, 0.58, 1.0),
    'Cloak_Scatter_Silk_Color_Base': (0.88, 0.83, 0.72, 1.0),
    'Cloak_Scatter_Silk_Color_intA': (0.78, 0.74, 0.65, 1.0),
    'Cloak_Scatter_Silk_Color_intB': (0.84, 0.80, 0.70, 1.0),
    'Cloak_Scatter_Silk_Color_intC': (0.67, 0.63, 0.54, 1.0),
}


def author(output=None):
    root = Path(unreal.Paths.project_dir()).resolve()
    source_file = root / ('Content/' + SOURCE.removeprefix('/Game/') + '.uasset')
    before = hashlib.sha256(source_file.read_bytes()).hexdigest()
    source = unreal.load_asset(SOURCE)
    mesh = unreal.load_asset(MESH)
    if not isinstance(source, unreal.Material) or not mesh:
        raise RuntimeError('Expected the imported Rogue material and mesh')
    slots = list(mesh.get_editor_property('materials'))
    matches = [slot for slot in slots if str(slot.get_editor_property('material_slot_name')) == HOOD_SLOT]
    if len(matches) != 1 or matches[0].get_editor_property('material_interface') != source:
        raise RuntimeError('Original hood slot no longer matches the inspected Rogue source')

    library = unreal.MaterialEditingLibrary
    available = {str(name) for name in library.get_vector_parameter_names(source)}
    if not set(CLOTH_COLORS).issubset(available):
        raise RuntimeError('Required cloth tint parameters are missing')
    asset = unreal.load_asset(DESTINATION)
    if not asset:
        folder, name = DESTINATION.rsplit('/', 1)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if not isinstance(asset, unreal.MaterialInstanceConstant):
        raise RuntimeError('Owned ivory hood destination has an unexpected type')
    library.set_material_instance_parent(asset, source)
    for name, values in CLOTH_COLORS.items():
        # UE 5.8 returns false even after setting this parameter; verify the read-back below.
        library.set_material_instance_vector_parameter_value(asset, name, unreal.LinearColor(*values))
    library.update_material_instance(asset)
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Cannot save owned ivory hood material')

    applied = {}
    for name in CLOTH_COLORS:
        value = library.get_material_instance_vector_parameter_value(asset, name)
        applied[name] = [value.r, value.g, value.b, value.a]
    unchanged = before == hashlib.sha256(source_file.read_bytes()).hexdigest()
    report = {
        'passed': unchanged and all(all(abs(a - b) < 1e-5 for a, b in zip(applied[name], values))
                                  for name, values in CLOTH_COLORS.items()),
        'material': asset.get_path_name(), 'parent': source.get_path_name(),
        'runtime_slot': HOOD_SLOT, 'cloth_tints': applied,
        'source_unchanged': unchanged,
        'scope': 'Hood slot only. No mesh, BP, original material, textures or cloth settings saved.',
    }
    if output:
        destination = Path(output).resolve()
        if not destination.is_relative_to(root / 'Saved/QA'):
            raise ValueError('Report must remain inside project Saved/QA')
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'ivory-hood-assets.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
