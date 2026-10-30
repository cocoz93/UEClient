"""Private flowing motion echoes for F and Space; no source-pack edits."""
import hashlib
import json
from pathlib import Path

import unreal

TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessQualityMotionEcho'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
VERSION = '2'


def author(output):
    lib = unreal.MaterialEditingLibrary
    source_file = Path(unreal.Paths.project_content_dir()) / (NOISE.removeprefix('/Game/') + '.uasset')
    before = hashlib.sha256(source_file.read_bytes()).hexdigest()
    material = unreal.load_asset(TARGET)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            TARGET.rsplit('/', 1)[1], TARGET.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessMotionSurfaceVersion') != VERSION:
        lib.delete_all_material_expressions(material)
        for name, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                            'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                            'two_sided': True, 'used_with_skeletal_mesh': True,
                            'used_with_clothing': True}.items():
            material.set_editor_property(name, value)

        def node(kind, **props):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for name, value in props.items():
                item.set_editor_property(name, value)
            return item

        def wire(a, channel, b, pin):
            assert lib.connect_material_expressions(a, channel, b, pin), pin

        def pins(names):
            result = []
            for name in names:
                item = unreal.CustomInput()
                item.set_editor_property('input_name', name)
                result.append(item)
            return result

        local = node('Subtract')
        wire(node('WorldPosition'), '', local, 'A')
        wire(node('ObjectPositionWS'), '', local, 'B')
        uv = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                  code='return float2((P.x+P.y)*.008,P.z*.006);')
        uv.set_editor_property('inputs', pins(('P',)))
        wire(local, '', uv, 'P')
        pan = node('Panner', speed_x=.12, speed_y=-.28)
        wire(uv, '', pan, 'Coordinate')
        sample = node('TextureSample', texture=unreal.load_asset(NOISE))
        wire(pan, '', sample, 'UVs')
        clock = node('Time')
        start = node('ScalarParameter', parameter_name='DissolveStart', default_value=1000000.)
        span = node('ScalarParameter', parameter_name='DissolveDuration', default_value=.22)
        shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float t=saturate((Clock-Start)/max(Span,.01));
float n=pow(saturate((Noise-.0075)/.5766),.55);
float vein=pow(saturate(1-abs(n-.42)*18),3);
float rim=pow(saturate(Facing),4.0);
float flow=smoothstep(.10,.38,n)*(.38+.62*smoothstep(.0,.55,n));
float erode=1-smoothstep(n*.55+.08,n*.55+.42,t);
float a=saturate(Opacity)*flow*erode*pow(1-t,.8);
float3 c=float3(.012,.0003,.0011)+float3(.19,.0014,.008)*n*n;
c+=float3(.68,.003,.021)*(vein*.75+rim*.52)*(.35+.65*flow);
return float4(c*pow(1-t,.5),a);
''')
        shader.set_editor_property('inputs', pins(('Noise', 'Facing', 'Clock', 'Start', 'Span', 'Opacity')))
        for source, channel, pin in ((sample, 'R', 'Noise'),
                                     (node('Fresnel', exponent=1., base_reflect_fraction=.0), '', 'Facing'),
                                     (clock, '', 'Clock'), (start, '', 'Start'), (span, '', 'Span'),
                                     (node('ScalarParameter', parameter_name='CloneOpacity', default_value=.7), '', 'Opacity')):
            wire(source, channel, shader, pin)
        color = node('ComponentMask', r=True, g=True, b=True, a=False)
        alpha = node('ComponentMask', r=False, g=False, b=False, a=True)
        wire(shader, '', color, lib.get_material_expression_input_names(color)[0])
        wire(shader, '', alpha, lib.get_material_expression_input_names(alpha)[0])
        assert lib.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        assert lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
        drift = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,
                     code='float t=saturate((Clock-Start)/max(Span,.01)); return Direction*pow(t,1.4)*(8+Noise*22);')
        drift.set_editor_property('inputs', pins(('Noise', 'Clock', 'Start', 'Span', 'Direction')))
        direction = node('VectorParameter', parameter_name='EchoDirection', default_value=unreal.LinearColor(1, 0, .35, 0))
        for source, channel, pin in ((sample, 'R', 'Noise'), (clock, '', 'Clock'), (start, '', 'Start'),
                                     (span, '', 'Span'), (direction, 'RGB', 'Direction')):
            wire(source, channel, drift, pin)
        assert lib.connect_material_property(drift, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessMotionSurfaceVersion', VERSION)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'passed': True, 'asset': TARGET, 'version': VERSION,
              'source_unchanged': before == hashlib.sha256(source_file.read_bytes()).hexdigest(),
              'scope': 'F motion residues and Space departure/motion echoes only',
              'surface': 'continuous ink flow, thin crimson fractures, directional erosion; no per-pixel dither'}
    assert result['source_unchanged']
    (Path(output) / 'countess-motion-surface.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
