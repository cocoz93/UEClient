"""Rejected D core experiment. Installed D uses the authored ink vortex, not this material.

The recorded visual-05/06 captures used earlier revisions. Revision 3 is an
unreviewed lighting experiment, with no runtime references; do not install it by default.
"""
import json
import os
from pathlib import Path
import traceback

import unreal


TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideCore'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
VERSION = '3'


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'target': TARGET, 'version': VERSION,
              'source_textures': [NOISE, INK], 'pack_assets_saved': False,
              'controls': {'TideErode': 0., 'TideOpacity': 1., 'TideTint': [1., 1., 1., 1.]},
              'source_normalization': {'noise': [.0075, .5841, .55], 'ink': [.0009, .3140, .30]},
              'wpo': 'VertexNormalWS * (normalized source noise - .5) * 8 cm; explicit mip 0'}
    try:
        lib = unreal.MaterialEditingLibrary
        material = unreal.load_asset(TARGET)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                TARGET.rsplit('/', 1)[1], TARGET.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
        if material is None:
            raise RuntimeError('Could not create ' + TARGET)
        if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessNightTideCoreVersion') != VERSION:
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
            material.set_editor_property('two_sided', False)

            def node(kind, **props):
                item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
                if item is None:
                    raise RuntimeError('Cannot create ' + kind)
                for key, value in props.items():
                    item.set_editor_property(key, value)
                return item

            def connect(source, channel, consumer, pin):
                if not lib.connect_material_expressions(source, channel, consumer, pin):
                    raise RuntimeError('Cannot connect ' + consumer.get_name() + ':' + pin)

            def custom_input(name):
                item = unreal.CustomInput()
                item.set_editor_property('input_name', name)
                return item

            noise_texture = unreal.load_asset(NOISE)
            ink_texture = unreal.load_asset(INK)
            if noise_texture is None or ink_texture is None:
                raise RuntimeError('Source ink texture missing')
            noise_uv = node('TextureCoordinate', u_tiling=1.7, v_tiling=.9)
            ink_uv = node('TextureCoordinate', u_tiling=1.3, v_tiling=1.6)
            noise_pan = node('Panner', speed_x=.11, speed_y=-.045)
            ink_pan = node('Panner', speed_x=-.05, speed_y=.075)
            connect(noise_uv, '', noise_pan, 'Coordinate')
            connect(ink_uv, '', ink_pan, 'Coordinate')
            noise = node('TextureSample', texture=noise_texture)
            ink = node('TextureSample', texture=ink_texture)
            connect(noise_pan, '', noise, 'UVs')
            connect(ink_pan, '', ink, 'UVs')
            rim = node('Fresnel', exponent=2.4, base_reflect_fraction=.0)
            erode = node('ScalarParameter', parameter_name='TideErode', default_value=0.)
            opacity = node('ScalarParameter', parameter_name='TideOpacity', default_value=1.)
            tint = node('VectorParameter', parameter_name='TideTint', default_value=unreal.LinearColor(1., 1., 1., 1.))
            shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
// Both source textures are sRGB; samples reaching this code are linear R.
float n = pow(saturate((Noise - .0075) / (.5841 - .0075)), .55);
float ink = pow(saturate((Ink - .0009) / (.3140 - .0009)), .30);
float marble = saturate(n * .48 + ink * .52);
float fissure = 1 - smoothstep(.004, .023, abs(n - ink * .63 - .15));
fissure *= smoothstep(.18, .52, marble);
float field = saturate(n * .65 + ink * .35);
float e = saturate(Erode);
float threshold = e * 1.16 - .08;
float survive = smoothstep(threshold, threshold + .10, field);
float holes = smoothstep(.16, .31, field);
float erosionEdge = (1 - smoothstep(.025, .10, abs(field - threshold - .035)))
                    * step(.015, e) * survive;
float3 charcoal = float3(.006, .0013, .0028);
float3 deepRed = float3(.16, .004, .012) * pow(ink, 1.2) * (.4 + .6 * n);
float3 cracks = float3(.55, .007, .018) * fissure;
float3 rimRed = float3(.7, .004, .014) * saturate(Rim) * pow(saturate(n * 1.3 - .12), 2) * (.3 + .7 * ink);
float3 erodingRed = float3(1.1, .018, .045) * erosionEdge;
float3 color = (charcoal + deepRed + cracks + rimRed + erodingRed) * Tint.rgb;
float alpha = (.91 + .07 * ink) * holes * survive * saturate(Opacity);
return float4(color, alpha);
''')
            shader.set_editor_property('inputs', [custom_input(name) for name in ('Noise', 'Ink', 'Rim', 'Erode', 'Opacity', 'Tint')])
            for source, channel, name in ((noise, 'R', 'Noise'), (ink, 'R', 'Ink'),
                                          (rim, '', 'Rim'), (erode, '', 'Erode'),
                                          (opacity, '', 'Opacity'), (tint, 'RGB', 'Tint')):
                connect(source, channel, shader, name)
            color = node('ComponentMask', r=True, g=True, b=True, a=False)
            alpha = node('ComponentMask', r=False, g=False, b=False, a=True)
            connect(shader, '', color, '')
            connect(shader, '', alpha, '')
            if not lib.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
                raise RuntimeError('Cannot connect emissive')
            if not lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY_MASK):
                raise RuntimeError('Cannot connect opacity')
            body = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                        code='float ink=pow(saturate((Ink-.0009)/(.314-.0009)),.30); return float3(.018,.001,.003)+float3(.12,.004,.009)*ink;')
            body.set_editor_property('inputs', [custom_input('Ink')])
            connect(ink, 'R', body, 'Ink')
            if not lib.connect_material_property(body, '', unreal.MaterialProperty.MP_BASE_COLOR):
                raise RuntimeError('Cannot connect body color')
            for value, prop in ((.36, unreal.MaterialProperty.MP_ROUGHNESS), (.45, unreal.MaterialProperty.MP_SPECULAR)):
                if not lib.connect_material_property(node('Constant', r=value), '', prop):
                    raise RuntimeError('Cannot connect surface property')

            # Vertex texture fetch needs explicit mip; keep normal pixel samples
            # on their default mip path so their moving cracks remain filtered.
            vertex_noise = node('TextureSample', texture=noise_texture,
                                mip_value_mode=unreal.TextureMipValueMode.TMVM_MIP_LEVEL, const_mip_value=0)
            connect(noise_pan, '', vertex_noise, 'UVs')
            displacement = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                                code='return (pow(saturate((Noise-.0075)/(.5841-.0075)),.55)-.5)*8;')
            displacement.set_editor_property('inputs', [custom_input('Noise')])
            connect(vertex_noise, 'R', displacement, 'Noise')
            normal = node('VertexNormalWS')
            wpo = node('Multiply')
            connect(normal, '', wpo, 'A')
            connect(displacement, '', wpo, 'B')
            if not lib.connect_material_property(wpo, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
                raise RuntimeError('Cannot connect WPO')
            errors = [str(e) for e in (lib.recompile_material(material) or [])]
            report['compile_errors'] = errors
            if errors:
                raise RuntimeError('Core material compile failed: ' + repr(errors))
            unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessNightTideCoreVersion', VERSION)
            unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessNightTideCoreSources', json.dumps([NOISE, INK]))
        else:
            report['reused'] = True
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save ' + TARGET)
        report['saved_assets'] = [TARGET]
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'countess-tide-core-material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('COUNTESS_TIDE_CORE_MATERIAL passed=' + str(report['passed']) + ' output=' + str(output))
    return report


if __name__ == '__main__':
    destination = os.environ.get('SPARROW_QA_OUTPUT') or str(Path(unreal.Paths.project_saved_dir()) / 'QA/CharacterPipeline/countess-D-rebuild-20261021/tide-core-material')
    author(destination)
    unreal.SystemLibrary.quit_editor()
