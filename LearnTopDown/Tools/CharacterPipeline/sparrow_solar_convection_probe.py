"""Read the exact solar core material graph; no asset saves or PIE mutation."""
import json
from pathlib import Path

import unreal


def author(output):
    output = Path(output)
    lib = unreal.MaterialEditingLibrary
    rows = []
    for path in (
        '/Game/ParagonSparrow/FX/Materials/Heroes/Sparrow/Abilities/M_Plasma_Sparrow',
        '/Game/ParagonSparrow/FX/Materials/Heroes/Sparrow/Abilities/M_ShockwaveFlameSparrow',
    ):
        material = unreal.load_asset(path)
        assert isinstance(material, unreal.Material), path
        row = {'material': path, 'properties': {}, 'nodes': []}
        for name, prop in (('opacity', unreal.MaterialProperty.MP_OPACITY),
                           ('emissive', unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
            source = lib.get_material_property_input_node(material, prop)
            row['properties'][name] = {
                'node': source.get_name() if source else None,
                'output': str(lib.get_material_property_input_node_output_name(material, prop)),
            }
        for node in lib.get_material_expressions(material):
            item = {'name': node.get_name(), 'class': node.get_class().get_name(), 'inputs': []}
            for source in lib.get_inputs_for_material_expression(material, node):
                if source:
                    item['inputs'].append({
                        'source': source.get_name(),
                        'output': str(lib.get_input_node_output_name_for_material_expression(node, source)),
                    })
            for field in ('parameter_name', 'default_value', 'texture', 'const_a',
                          'const_b', 'const_exponent', 'const_base', 'fade_distance_default'):
                try:
                    value = node.get_editor_property(field)
                    item[field] = value.get_path_name() if isinstance(value, unreal.Object) else str(value)
                except Exception:
                    pass
            row['nodes'].append(item)
        rows.append(row)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'solar-convection-material-audit.json'
    path.write_text(json.dumps({'passed': True, 'read_only': True, 'assets_saved': False,
                                'graphs': rows}, indent=2), encoding='utf-8')
    return {'passed': True, 'read_only': True, 'assets_saved': False, 'report': str(path)}
