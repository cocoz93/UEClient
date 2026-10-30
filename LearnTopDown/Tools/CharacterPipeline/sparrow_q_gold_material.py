"""Preserve original rain-arrow geometry/opacity while removing hue at its final material outputs."""
import hashlib
import json
from pathlib import Path
import unreal


SOURCE = '/Game/ParagonSparrow/FX/Materials/Heroes/Sparrow/Abilities/M_ArrowRain'
TARGET = '/Game/TopDown/Characters/Sparrow/Materials/Salvo20261026/M_QArrowRainGold'
VERSION = 'rain-final-luminance-gold-v1'


def author(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    source = unreal.load_asset(SOURCE)
    assert isinstance(source, unreal.Material), SOURCE
    source_file = Path(unreal.Paths.project_content_dir()) / (SOURCE.removeprefix('/Game/') + '.uasset')
    original_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
    material = unreal.load_asset(TARGET)
    if material is None:
        material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    assert isinstance(material, unreal.Material), TARGET
    reused = unreal.EditorAssetLibrary.get_metadata_tag(material, 'QGoldVersion') == VERSION
    outputs = []
    if not reused:
        for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_BASE_COLOR):
            previous = lib.get_material_property_input_node(material, prop)
            if not previous:
                continue
            previous_output = lib.get_material_property_input_node_output_name(material, prop)
            dot = lib.create_material_expression(material, unreal.MaterialExpressionDotProduct)
            luminance = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
            luminance.set_editor_property('constant', unreal.LinearColor(.2126, .7152, .0722, 1.))
            tint = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
            tint.set_editor_property('constant', unreal.LinearColor(1., .72, .16, 1.))
            multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
            assert lib.connect_material_expressions(previous, previous_output, dot, 'A')
            assert lib.connect_material_expressions(luminance, '', dot, 'B')
            assert lib.connect_material_expressions(dot, '', multiply, 'A')
            assert lib.connect_material_expressions(tint, '', multiply, 'B')
            assert lib.connect_material_property(multiply, '', prop)
            outputs.append({'property': str(prop), 'previous_node': previous.get_class().get_name(),
                            'previous_output': previous_output})
        assert outputs, 'Original rain arrow has no connected color output'
    errors = [str(error) for error in (lib.recompile_material(material) or [])]
    report = {'passed': not errors, 'source': SOURCE, 'target': TARGET, 'reused': reused,
              'changed_outputs': outputs, 'compile_errors': errors,
              'opacity_and_mesh_unchanged': True,
              'source_file_unchanged': original_hash == hashlib.sha256(source_file.read_bytes()).hexdigest()}
    (out / 'q-gold-material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    assert not errors, '\n'.join(errors)
    assert report['source_file_unchanged'], 'The original M_ArrowRain must remain untouched'
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'QGoldVersion', VERSION)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return report
