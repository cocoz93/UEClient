"""S-only lit demon silhouette and a short, split entry shell.

The accepted source body graph is duplicated so its solid-body mask, clothing
usage and mantle-only displacement survive. Only the two owned packages below
are saved; no shared Countess material, particle or mesh is edited.
"""
import hashlib
import json
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Countess/DemonSilhouette20261024'
BODY_SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessDemonForm'
BODY = ROOT + '/M_CountessDemonSilhouette'
SHELL = ROOT + '/M_CountessDemonEntryShell'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
READ_ONLY = (BODY_SOURCE, NOISE, INK,
    '/Game/TopDown/Characters/Countess/Reference20261024/M_CountessReferenceVeil',
    '/Game/TopDown/Characters/Countess/Reference20261024/SM_CountessDemonShroud',
    '/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_WingMesh')
TAG = 'CountessDemonSilhouetteVersion'
VERSION = '1'


def _hash_sources():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    return {asset: hashlib.sha256((content / (asset.removeprefix('/Game/') + '.uasset')).read_bytes()).hexdigest()
            for asset in READ_ONLY}


def _save(material):
    errors = [str(e) for e in (unreal.MaterialEditingLibrary.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('S silhouette shader failed: ' + repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, TAG, VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save S-owned material ' + unreal.SystemLibrary.get_path_name(material))


def _body():
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(BODY)
    if material is None:
        material = unreal.EditorAssetLibrary.duplicate_asset(BODY_SOURCE, BODY)
    if not isinstance(material, unreal.Material):
        raise RuntimeError('Cannot duplicate the accepted S body material')
    if unreal.EditorAssetLibrary.get_metadata_tag(material, TAG) == VERSION:
        return material
    # Query the actual output nodes. ObjectIterator can include disconnected
    # historical expressions, so counting those would accept the wrong shader.
    base = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    emission = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mask = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY_MASK)
    motion = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    for expression in (base, emission, mask, motion):
        if not isinstance(expression, unreal.MaterialExpressionCustom) or expression.get_outer() != material:
            raise RuntimeError('Unexpected S body graph; keep the source untouched')
    if ('return lerp(1., coverage' not in mask.get_editor_property('code') or
            'saturate(Mantle)' not in motion.get_editor_property('code')):
        raise RuntimeError('The source no longer has the solid-body / mantle-only contract')
    names = {str(pin.get_editor_property('input_name')) for pin in emission.get_editor_property('inputs')}
    if names != {'Noise', 'Ink', 'Mantle', 'MaskNoise', 'Facing', 'Strength', 'Pulse'}:
        raise RuntimeError('Unexpected connected S emission inputs: ' + repr(names))
    base.set_editor_property('code', '''
float n=pow(saturate((Noise-.0075)/.5766),.55);
float ink=pow(saturate((Ink-.0009)/.3131),.30);
float grain=saturate(n*.55+ink*.45);
float3 body=float3(.042,.029,.036)+float3(.050,.018,.024)*grain*grain;
float3 mantle=float3(.018,.009,.014)+float3(.035,.006,.009)*grain;
return lerp(body,mantle,saturate(Mantle));
''')
    emission.set_editor_property('code', '''
float n=pow(saturate((Noise-.0075)/.5766),.55);
float ink=pow(saturate((Ink-.0009)/.3131),.30);
float grain=saturate(n*.55+ink*.45);
float veins=1-smoothstep(.004,.030,abs(n-ink*.67-.17));
veins*=smoothstep(.35,.75,grain);
// Facing already contains the accepted Fresnel exponent. Its square root
// widens the anatomical ridges without filling the front-facing dark planes.
float edge=pow(saturate(Facing),.52)*(.65+.35*grain);
float strength=.18+.82*saturate(Strength);
float3 color=float3(1.80,.008,.032)*(edge*.76+veins*.20)*strength;
color+=float3(2.20,.025,.035)*saturate(Pulse)*(edge*.65+veins*.22);
float uvInk=pow(saturate((MaskNoise-.0009)/.3131),.30);
float field=uvInk*.72+grain*.28;
float tornEdge=1-smoothstep(.018,.055,abs(field-.34));
float irregularRim=edge*smoothstep(.32,.72,grain)*(.55+.45*uvInk);
// The two mantles frame the brighter head, shoulders and arms. Their broad
// faces stay charcoal; neither a flat red panel nor a second bright body.
float3 cloak=float3(.92,.003,.018)*(irregularRim*.60+tornEdge*.055+veins*.020);
cloak+=float3(.009,.0002,.001)*ink*ink;
cloak+=float3(1.10,.009,.024)*saturate(Pulse)*irregularRim*.38;
return lerp(color,cloak,saturate(Mantle));
''')
    material.set_editor_property('used_with_skeletal_mesh', True)
    material.set_editor_property('used_with_clothing', True)
    _save(material)
    return material


def _shell():
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(SHELL)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            SHELL.rsplit('/', 1)[1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(material, unreal.Material):
        raise RuntimeError('Cannot create the S-owned entry shell')
    if unreal.EditorAssetLibrary.get_metadata_tag(material, TAG) == VERSION:
        return material
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)

    def node(kind, **props):
        expression = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        if expression is None:
            raise RuntimeError('Cannot create S shell expression ' + kind)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        return expression

    def wire(source, channel, target, pin):
        if not lib.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError('Cannot connect S shell input ' + pin)

    uv = node('TextureCoordinate')
    values = [(uv, '', 'UV'),
              (node('Fresnel', exponent=1., base_reflect_fraction=0.), '', 'Facing')]
    for index, asset in enumerate((NOISE, INK)):
        texture = unreal.load_asset(asset)
        if texture is None:
            raise RuntimeError('Missing read-only S texture ' + asset)
        pan = node('Panner', speed_x=.045 if index == 0 else -.025,
                   speed_y=-.30 if index == 0 else -.12)
        wire(uv, '', pan, 'Coordinate')
        sample = node('TextureSample', texture=texture)
        wire(pan, '', sample, 'UVs')
        values.append((sample, 'R', 'Noise' if index == 0 else 'Ink'))
    for name, value in (('RuinErode', 0.), ('RuinPulse', 0.), ('RuinEnergy', 1.),
                        ('CloneOpacity', 1.), ('ReferenceAge', 0.)):
        values.append((node('ScalarParameter', parameter_name=name, default_value=value), '', name))
    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float n=pow(saturate((Noise-.0075)/.5766),.62);
float ink=pow(saturate((Ink-.0009)/.3131),.38);
float grain=saturate(n*.58+ink*.42);
float release=saturate(RuinErode);
float opening=smoothstep(.12,.62,release);
float ridge=pow(saturate(Facing),.72);
float fissure=pow(saturate(1-abs(n-ink*.72-.11)*22),2.3)*smoothstep(.28,.64,grain);
float boundary=smoothstep(0,.14,UV.y)*smoothstep(0,.12,1-UV.y);
float ends=smoothstep(0,.035,UV.x)*smoothstep(0,.035,1-UV.x);
// Unequal vertical fissures open the broad front faces first. Only a torn
// outer contour survives briefly, making the lit demon readable inside.
float split=.5+.5*sin(UV.x*31.4159+ink*3.3+UV.y*1.8);
float tongues=smoothstep(.24+opening*.36,.68+opening*.23,split);
float bodyWindow=lerp(1.,.10+.90*ridge,opening);
float life=1-smoothstep(.30+grain*.24,.62+grain*.26,release);
float density=smoothstep(.18+.23*release,.59+.17*release,grain);
float alpha=CloneOpacity*boundary*ends*density*life*bodyWindow*lerp(1.,tongues,opening);
float3 color=float3(.004,.0002,.0007)+float3(.014,.0005,.0015)*grain*grain;
color+=float3(1.30,.012,.027)*(fissure*.34+ridge*.075)*RuinEnergy;
color+=float3(2.0,.022,.035)*saturate(RuinPulse)*(fissure*.40+ridge*.10)*RuinEnergy;
return float4(color,saturate(alpha));
''')
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
    for expression in (rgb, alpha):
        wire(shader, '', expression, lib.get_material_expression_input_names(expression)[0])
    for expression, prop in ((rgb, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                             (alpha, unreal.MaterialProperty.MP_OPACITY)):
        if not lib.connect_material_property(expression, '', prop):
            raise RuntimeError('Cannot connect S shell output ' + str(prop))
    _save(material)
    return material


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    before = _hash_sources()
    materials = [_body(), _shell()]
    after = _hash_sources()
    if before != after:
        raise RuntimeError('An S read-only source package changed')
    result = {'passed': True, 'version': VERSION,
        'materials': [unreal.SystemLibrary.get_path_name(m) for m in materials],
        'source_hashes': after, 'source_hashes_unchanged': True,
        'scope': 'S-only body and entry shell; source graph mask/WPO, meshes, particles and other skills preserved',
        'timing': 'native .5s entry/24s form preserved; front shell tears before the body ridge pulse',
        'visual_acceptance': 'pending actual countess-quality-gate-20261024 S capture'}
    (output / 'countess-demon-silhouette-surface.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
