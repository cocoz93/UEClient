"""Local third-pass surfaces for E/R cups and A/V cuts; D/S assets stay untouched."""
import hashlib
import json
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Countess/Reference20261024'
TEXTURES = ('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile',
            '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M')
VERSION = '1'


def _make(name, cup):
    path = ROOT + '/' + name
    material = unreal.load_asset(path)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessRuptureFinishVersion') == VERSION:
        return material
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items():
            item.set_editor_property(key, value)
        return item

    def wire(source, channel, target, pin):
        if not lib.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError('Countess finish connection failed: ' + pin)

    uv = node('TextureCoordinate')
    values = [(uv, '', 'UV')]
    for index, tex_path in enumerate(TEXTURES):
        sample = node('TextureSample', texture=unreal.load_asset(tex_path))
        pan = node('Panner', speed_x=.15 if index == 0 else -.08,
                   speed_y=-.19 if index == 0 else .13)
        wire(uv, '', pan, 'Coordinate')
        wire(pan, '', sample, 'UVs')
        values.append((sample, 'R', 'Noise' if index == 0 else 'Ink'))
    for name, value in (('RuinErode', 0.), ('RuinPulse', 0.), ('RuinEnergy', 1.), ('CloneOpacity', 1.)):
        values.append((node('ScalarParameter', parameter_name=name, default_value=value), '', name))
    common = '''
float n=pow(saturate((Noise-.0075)/.5766),.62);
float ink=pow(saturate((Ink-.0009)/.3131),.38);
float grain=saturate(n*.58+ink*.42);
float vein=pow(saturate(1-abs(n-ink*.67-.12)*19),2.4)*smoothstep(.24,.60,grain);
float life=1-smoothstep(grain*.50+.12,grain*.50+.52,saturate(RuinErode));
'''
    code = common + ('''
float outer=smoothstep(.48,.87,UV.y);
float broken=smoothstep(.24+outer*.22,.61+outer*.16,grain);
float edgeFade=1-smoothstep(.81,1.0,UV.y+(grain-.5)*.17);
float density=lerp(.75+.20*grain,broken,outer);
float alpha=CloneOpacity*life*density*edgeFade*lerp(.87,.57,outer);
float3 color=float3(.005,.00025,.0008)+float3(.050,.0008,.004)*grain*grain;
color+=float3(.67,.006,.019)*(vein*.23+outer*broken*.08)*RuinEnergy;
return float4(color,alpha);
''' if cup else '''
float ends=smoothstep(0,.065,UV.x)*smoothstep(0,.095,1-UV.x);
float boundary=min(UV.y,1-UV.y);
float edge=1-smoothstep(.012,.075,boundary);
float flow=smoothstep(.25,.62,grain);
float torn=smoothstep(.20,.53,grain-edge*.07);
float alpha=CloneOpacity*life*ends*torn*(.34+.40*flow);
float3 color=float3(.008,.0003,.0010)+float3(.031,.0007,.003)*grain*grain;
color+=float3(1.15,.008,.029)*(edge*.72*flow+vein*.19)*RuinEnergy;
color+=float3(.65,.014,.010)*saturate(RuinPulse)*edge*flow*.16;
return float4(color,alpha);
''')
    shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for source, channel, name in values:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shader.set_editor_property('inputs', pins)
    for source, channel, name in values:
        wire(source, channel, shader, name)
    rgb = node('ComponentMask', r=True, g=True, b=True, a=False)
    alpha = node('ComponentMask', r=False, g=False, b=False, a=True)
    for mask in (rgb, alpha):
        wire(shader, '', mask, lib.get_material_expression_input_names(mask)[0])
    lib.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    errors = [str(e) for e in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('Countess finish shader failed: ' + repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessRuptureFinishVersion', VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save Countess finish material ' + path)
    return material


def author(output):
    files = [Path(unreal.Paths.project_content_dir()) / (path.removeprefix('/Game/') + '.uasset') for path in TEXTURES]
    before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    materials = [_make('M_CountessRuptureEdge', True), _make('M_CountessVortexFlow', False)]
    unchanged = all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == value for path, value in before.items())
    if not unchanged:
        raise RuntimeError('Source texture package changed')
    result = {'passed': True, 'version': VERSION, 'materials': [m.get_path_name() for m in materials],
              'source_hash_unchanged': unchanged,
              'scope': 'only E/R low rupture cup and A/V flowing blade surfaces; no D/S/Space asset save'}
    (Path(output) / 'countess-rupture-finish.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
