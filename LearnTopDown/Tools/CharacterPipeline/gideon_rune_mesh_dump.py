"""Dump the Gideon rune ring meshes: sections, materials and their parameter names (to hide pieces or fade them out).
Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = '/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/'
MESHES = os.environ.get('RUNE_MESHES', 'SM_Rune_Ring_Inner,SM_Rune_Ring_Outer,SM_Burden_Spline').split(',')


def material_info(material):
    if material is None:
        return None
    lib = unreal.MaterialEditingLibrary
    base = material.get_base_material() if hasattr(material, 'get_base_material') else material
    info = {'name': material.get_path_name(), 'base': base.get_path_name() if base else None}
    for kind, getter in (('scalar', lib.get_scalar_parameter_names), ('vector', lib.get_vector_parameter_names),
                         ('texture', lib.get_texture_parameter_names)):
        try:
            info[kind] = [str(n) for n in getter(material)]
        except Exception as error:
            info[kind] = str(error)
    try:
        info['blend'] = str(base.get_editor_property('blend_mode'))
        info['two_sided'] = base.get_editor_property('two_sided')
    except Exception as error:
        info['blend'] = str(error)
    return info


result = {}
try:
    for name in MESHES:
        mesh = unreal.load_asset(ROOT + name)
        entry = {'bounds': str(mesh.get_bounds().box_extent)}
        entry['lod0_sections'] = mesh.get_num_sections(0)
        entry['materials'] = []
        for index, slot in enumerate(mesh.get_editor_property('static_materials')):
            entry['materials'].append({'slot': index, 'slot_name': str(slot.get_editor_property('material_slot_name')),
                                       'material': material_info(slot.get_editor_property('material_interface'))})
        result[name] = entry
except Exception:
    result['error'] = traceback.format_exc()
(qa / 'rune-mesh.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
