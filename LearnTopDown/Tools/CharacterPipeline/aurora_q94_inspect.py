"""94th Aurora round: read-only dump of the pack's own sword-trail materials (and a few smoke/trail textures) so the Q sword wave
can be rebuilt from the same look - blend mode, every parameter with its value, and every expression node with its texture.
Writes aurora-q94-inspect.json. Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
lib = unreal.MaterialEditingLibrary
MATERIALS = (
    '/Game/ParagonAurora/FX/Materials/Aurora/FX/M_Aurora_Primary_AnimTrail',
    '/Game/ParagonAurora/FX/Materials/Aurora/FX/M_Aurora_Trail_Mesh',
    '/Game/ParagonAurora/FX/Materials/Smoke/WispySmokeSoft/M_WispySmokeSoft',
)
TEXTURES = (
    '/Game/ParagonAurora/FX/Textures/trails/T_Streak_Soft_Trail_03',
    '/Game/ParagonAurora/FX/Textures/trails/T_Trail_Mask',
    '/Game/ParagonAurora/FX/Textures/Smoke/T_WispySmoke_V2_OCC+Alpha',
    '/Game/ParagonAurora/FX/Textures/energy/T_Swirly_Noise',
    '/Game/ParagonAurora/FX/Textures/Smoke/T_tiling_smoke_01',
)


def value(v):
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    if isinstance(v, unreal.LinearColor):
        return [round(v.r, 3), round(v.g, 3), round(v.b, 3), round(v.a, 3)]
    return str(v)


result = {'materials': [], 'textures': []}
try:
    for path in MATERIALS:
        row = {'path': path}
        result['materials'].append(row)
        material = unreal.load_asset(path)
        if material is None:
            row['error'] = 'not loaded'
            continue
        base = material.get_base_material()
        row['class'] = material.get_class().get_name()
        for prop in ('blend_mode', 'shading_model', 'two_sided'):
            try:
                row[prop] = value(base.get_editor_property(prop))
            except Exception as error:
                row[prop] = str(error)
        for kind in ('scalar', 'vector', 'texture'):
            values = {}
            for name in getattr(lib, 'get_' + kind + '_parameter_names')(material):
                try:
                    if isinstance(material, unreal.MaterialInstanceConstant):
                        got = getattr(lib, 'get_material_instance_' + kind + '_parameter_value')(material, name)
                    else:
                        got = getattr(lib, 'get_material_default_' + kind + '_parameter_value')(base, name)
                    values[str(name)] = value(got)
                except Exception as error:
                    values[str(name)] = 'error ' + str(error)
            row[kind] = values
        nodes = []
        for node in lib.get_material_expressions(base):
            item = {'class': node.get_class().get_name()}
            for prop in ('parameter_name', 'texture', 'default_value', 'speed_x', 'speed_y', 'coordinate_index', 'u_tiling', 'v_tiling'):
                try:
                    item[prop] = value(node.get_editor_property(prop))
                except Exception:
                    pass
            nodes.append(item)
        row['nodes'] = nodes
        for prop in ('MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_BASE_COLOR'):
            try:
                expression = lib.get_material_property_input_node(base, getattr(unreal.MaterialProperty, prop))
                row.setdefault('inputs', {})[prop] = expression.get_class().get_name() if expression else None
            except Exception as error:
                row.setdefault('inputs', {})[prop] = str(error)
    for path in TEXTURES:
        texture = unreal.load_asset(path)
        if texture is None:
            result['textures'].append({'path': path, 'error': 'not loaded'})
            continue
        result['textures'].append({'path': path, 'size': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()],
                                   'srgb': texture.get_editor_property('srgb'),
                                   'compression': value(texture.get_editor_property('compression_settings'))})
    result['passed'] = all('error' not in row for row in result['materials'])
except Exception:
    result['passed'] = False
    result['error'] = traceback.format_exc()
(qa / 'aurora-q94-inspect.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
