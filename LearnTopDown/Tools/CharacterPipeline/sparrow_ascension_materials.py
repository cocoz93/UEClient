"""Author two Sparrow-owned ascension materials; source packs and existing skill materials stay untouched."""
import json
from pathlib import Path

import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur'


def author(output):
    output = Path(output).resolve()
    root = Path(unreal.Paths.project_dir()).resolve()
    assert output.is_relative_to(root / 'Saved/QA')
    output.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(NOISE)
    assert texture is not None
    report = {'passed': False, 'source_assets_saved': False, 'materials': []}

    def node(material, kind, **properties):
        value = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, setting in properties.items():
            value.set_editor_property(key, setting)
        return value

    def wire(source, target, name, output_pin=''):
        assert lib.connect_material_expressions(source, output_pin, target, name)

    for echo in (False, True):
        name = 'M_SparrowAscensionEcho' if echo else 'M_SparrowAscensionGold'
        path = FOLDER + '/' + name
        material = unreal.load_asset(path)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        assert isinstance(material, unreal.Material)
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT if echo else unreal.BlendMode.BLEND_OPAQUE)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT if echo else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        material.set_editor_property('two_sided', True)
        material.set_editor_property('used_with_skeletal_mesh', True)
        material.set_editor_property('used_with_clothing', True)
        material.set_editor_property('used_with_instanced_static_meshes', True)
        uv = node(material, 'TextureCoordinate')
        panner = node(material, 'Panner', speed_x=0.14 if echo else 0.025, speed_y=0.06)
        wire(uv, panner, 'Coordinate')
        sample = node(material, 'TextureSample', texture=texture)
        wire(panner, sample, 'UVs')
        fresnel = node(material, 'Fresnel')
        if echo:
            code = '''
float grain = saturate(Noise);
float visible = saturate(Visibility);
float fragments = smoothstep(1.0-visible-0.12, 1.0-visible+0.08, grain);
float alpha = visible * fragments * (0.28 + 0.40 * Facing) * (0.75 + 0.25 * grain);
float3 color = BodyTint * (0.50 + 0.65 * grain) + float3(1.5,0.88,0.18) * Facing * (0.65 + 0.45 * grain);
return float4(color, saturate(alpha));
'''
            custom = node(material, 'Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            pins = []
            for key in ('Noise', 'Facing', 'Visibility', 'BodyTint'):
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', key)
                pins.append(pin)
            custom.set_editor_property('inputs', pins)
            wire(sample, custom, 'Noise', 'R')
            wire(fresnel, custom, 'Facing')
            wire(node(material, 'ScalarParameter', parameter_name='Visibility', default_value=1.0), custom, 'Visibility')
            wire(node(material, 'VectorParameter', parameter_name='BodyTint', default_value=unreal.LinearColor(.7, .39, .06, 1)), custom, 'BodyTint')
            for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                                   (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
                mask = node(material, 'ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
                wire(custom, mask, lib.get_material_expression_input_names(mask)[0])
                assert lib.connect_material_property(mask, '', prop)
        else:
            tint = node(material, 'Constant3Vector', constant=unreal.LinearColor(.62, .32, .055, 1))
            assert lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
            glow = node(material, 'Multiply')
            wire(tint, glow, 'A')
            wire(sample, glow, 'B', 'R')
            assert lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            assert lib.connect_material_property(node(material, 'Constant', r=.72), '', unreal.MaterialProperty.MP_METALLIC)
            assert lib.connect_material_property(node(material, 'Constant', r=.29), '', unreal.MaterialProperty.MP_ROUGHNESS)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        report['materials'].append({'asset': path, 'skeletal_usage': True, 'clothing_usage': True, 'instanced_static_usage': True,
                                    'source_noise': NOISE, 'refraction': False})
    report['passed'] = len(report['materials']) == 2
    (output / 'sparrow-ascension-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
