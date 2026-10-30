"""Author only the AS-owned tapered gust material; leave Sparrow source materials unchanged."""
import json
import os
from pathlib import Path
import traceback

import unreal

DEST = '/Game/TopDown/Characters/Sparrow/Materials'
NAME = 'M_SparrowExtraGust'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'
qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
qa.mkdir(parents=True, exist_ok=True)
lib = unreal.MaterialEditingLibrary
report = {'passed': False, 'asset': DEST + '/' + NAME, 'source_texture': NOISE,
          'source_channel': 'R', 'source_assets_saved': False}


def node(material, kind, **properties):
    item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
    for key, value in properties.items():
        item.set_editor_property(key, value)
    return item


def connect(source, target, target_input, output=''):
    assert lib.connect_material_expressions(source, output, target, target_input)


try:
    texture = unreal.load_asset(NOISE)
    assert texture is not None, NOISE
    material = unreal.load_asset(DEST + '/' + NAME)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            NAME, DEST, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)

    shader = '''
float u = saturate(UV.x);
float arch = sin(u * 3.14159265);
float center = 0.5 + Bend * arch + (Noise - 0.5) * 0.028 * arch;
float halfWidth = max(0.003, Thickness * (0.22 + 0.78 * pow(max(arch, 0.0), 0.6)));
float distanceFromCenter = abs(UV.y - center);
float core = 1.0 - smoothstep(halfWidth * 0.18, halfWidth, distanceFromCenter);
float halo = exp2(-3.0 * pow(distanceFromCenter / max(halfWidth * 2.4, 0.006), 2.0));
float ends = smoothstep(0.0, 0.13, u) * (1.0 - smoothstep(0.80, 1.0, u));
// Noise supplies low-frequency grain inside one curved band, never a pack of parallel bands.
float grain = 0.72 + 0.28 * saturate(Noise);
float opacity = saturate(Envelope) * ends * grain * saturate(core * 0.72 + halo * 0.25);
float3 color = CoreTint * core + HaloTint * halo * 0.45;
return float4(color, opacity);
'''
    custom = node(material, 'Custom', code=shader,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    inputs = []
    for name in ('UV', 'Noise', 'Envelope', 'Bend', 'Thickness', 'CoreTint', 'HaloTint'):
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        inputs.append(pin)
    custom.set_editor_property('inputs', inputs)
    uv = node(material, 'TextureCoordinate')
    connect(uv, custom, 'UV')
    tiled = node(material, 'Multiply')
    connect(uv, tiled, 'A')
    connect(node(material, 'Constant2Vector', r=0.75, g=0.5), tiled, 'B')
    panner = node(material, 'Panner', speed_x=-0.45, speed_y=0.08)
    connect(tiled, panner, 'Coordinate')
    sample = node(material, 'TextureSample', texture=texture)
    connect(panner, sample, 'UVs')
    connect(sample, custom, 'Noise', 'R')
    for name, value in (('Envelope', 0.0), ('Bend', 0.16), ('Thickness', 0.09)):
        connect(node(material, 'ScalarParameter', parameter_name=name, default_value=value), custom, name)
    for name, value in (
            ('CoreTint', unreal.LinearColor(8.0, 4.8, 1.6, 1)),
            ('HaloTint', unreal.LinearColor(1.6, 0.65, 0.2, 1))):
        connect(node(material, 'VectorParameter', parameter_name=name, default_value=value), custom, name)
    for prop, channels in (
            (unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
            (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node(material, 'ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        connect(custom, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    report['saved'] = bool(unreal.EditorAssetLibrary.save_loaded_asset(material, False))
    report['scalar_parameters'] = [str(value) for value in lib.get_scalar_parameter_names(material)]
    report['vector_parameters'] = [str(value) for value in lib.get_vector_parameter_names(material)]
    report['ordinary_static_mesh_only'] = True
    report['passed'] = report['saved'] and {'Envelope', 'Bend', 'Thickness'}.issubset(report['scalar_parameters'])
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'sparrow-extra-gust-material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('SPARROW_EXTRA_GUST ' + json.dumps({'passed': report['passed'], 'asset': report['asset']}))
    unreal.SystemLibrary.quit_editor()
