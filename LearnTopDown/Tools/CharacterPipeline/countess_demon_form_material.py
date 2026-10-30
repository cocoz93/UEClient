"""Inspect existing DemonForm assets; optionally author its private surface.

Default author() only reads existing assets. After inspecting the native form
with its E-shadow fallback, set COUNTESS_DEMON_AUTHOR_MATERIAL=1 for the private
textured material. This module never launches the editor or saves source packs.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal


SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessSkillShadowCloneDetailed'
TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessDemonForm'
WING = '/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_WingMesh'
MANTLE = '/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideWing'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'
VERSION = '5'
EFFECTS = (
    '/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGather',
    '/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealBurst',
    '/Game/TopDown/Characters/Countess/FX/P_CountessBloodSealGround',
    '/Game/ParagonCountess/FX/Particles/Abilities/BlinkStrike/FX/p_Countess_ShadowCloneBurst',
    '/Game/ParagonCountess/FX/Particles/Abilities/Ultimate/FX/p_CountessUlt_EyeFX_Looping',
    '/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail',
)


def _write(output, name, value):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _hash_sources():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    rows = {}
    for asset in (SOURCE, WING, MANTLE, NOISE, INK, *EFFECTS):
        path = content/(asset.removeprefix('/Game/')+'.uasset')
        if not path.is_file():
            raise RuntimeError('Missing source package '+str(path))
        rows[asset] = hashlib.sha256(path.read_bytes()).hexdigest()
    return rows


def inspect(output):
    lib = unreal.MaterialEditingLibrary
    rows = {'assets_saved': False, 'materials': [], 'effects': []}
    for asset in (SOURCE, MANTLE):
        material = unreal.load_asset(asset)
        if material is None:
            raise RuntimeError('Missing form material '+asset)
        rows['materials'].append({'path': asset, 'class': material.get_class().get_name(),
            'scalars': [str(x) for x in lib.get_scalar_parameter_names(material)],
            'vectors': [str(x) for x in lib.get_vector_parameter_names(material)]})
    mesh = unreal.load_asset(WING)
    if mesh is None:
        raise RuntimeError('Missing Countess mantle mesh')
    box = mesh.get_bounding_box()
    size = box.max-box.min
    center = (box.max+box.min)*.5
    rows['wing'] = {'path': WING, 'bounds_size': [size.x, size.y, size.z],
                    'bounds_center': [center.x, center.y, center.z],
                    'shape_note': '원본 곡면에 소유 재질의 침식 마스크를 적용한 두 혈색 망토; 여섯 방향 진입 조각 없음'}
    for asset in EFFECTS:
        effect = unreal.load_asset(asset)
        if effect is None:
            raise RuntimeError('Missing form particle '+asset)
        rows['effects'].append({'path': asset, 'loaded': True,
            'emitter_audit': 'skipped_optional_protected_property'})
    rows['source_hashes'] = _hash_sources()
    _write(output, 'countess-demon-form-assets.json', rows)
    return rows


def build_material(output):
    """Lit charcoal body plus masked, torn mantle mode in the same owned package."""
    before = _hash_sources()
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(TARGET)
    old_version = unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessDemonFormVersion') if material else None
    if old_version == VERSION:
        if before != _hash_sources():
            raise RuntimeError('An original source package changed')
        result = {'asset': TARGET, 'version': VERSION, 'reused': True,
                  'shading': 'DefaultLit charcoal body / masked torn blood mantle', 'passed': True,
                  'source_hashes_unchanged': True, 'pack_assets_saved': False}
        _write(output, 'countess-demon-form-material.json', result)
        return result
    if material is not None and old_version not in ('1', '2', '3', '4'):
        raise RuntimeError('Existing owned form material has an unreviewed version')
    if material is None:
        material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if material is None:
        raise RuntimeError('Could not duplicate the accepted clone surface')
    # Only this private form package changes. A lit solid body intentionally
    # replaces the clone's translucent emissive/opacity/WPO presentation.
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property('opacity_mask_clip_value', .25)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('used_with_skeletal_mesh', True)
    material.set_editor_property('used_with_clothing', True)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
        if item is None:
            raise RuntimeError('Cannot create '+kind)
        for key, value in props.items():
            item.set_editor_property(key, value)
        return item

    def wire(source, output_name, target, pin):
        if not lib.connect_material_expressions(source, output_name, target, pin):
            raise RuntimeError('Cannot connect '+target.get_name()+':'+pin)

    def custom(code, inputs, output_type):
        shader = node('Custom', output_type=output_type, code=code)
        pins = []
        for source, output_name, name in inputs:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        shader.set_editor_property('inputs', pins)
        for source, output_name, name in inputs:
            wire(source, output_name, shader, name)
        return shader

    # Actor-relative coordinates keep the same field across the source body slots
    # without dragging a world-fixed pattern through the character's movement.
    position = node('Subtract')
    wire(node('WorldPosition'), '', position, 'A')
    wire(node('ActorPositionWS'), '', position, 'B')
    scale = node('Multiply', const_b=.023)
    wire(position, '', scale, 'A')
    uv_xz = node('ComponentMask', r=True, g=False, b=True, a=False)
    uv_yz = node('ComponentMask', r=False, g=True, b=True, a=False)
    wire(scale, '', uv_xz, '')
    wire(scale, '', uv_yz, '')
    noise_pan = node('Panner', speed_x=.028, speed_y=-.07)
    ink_pan = node('Panner', speed_x=-.015, speed_y=.045)
    wire(uv_xz, '', noise_pan, 'Coordinate')
    wire(uv_yz, '', ink_pan, 'Coordinate')
    noise = node('TextureSample', texture=unreal.load_asset(NOISE))
    ink = node('TextureSample', texture=unreal.load_asset(INK))
    wire(noise_pan, '', noise, 'UVs')
    wire(ink_pan, '', ink, 'UVs')
    # Only mantle MIDs enable this path. Body mask is identically one, retaining
    # the lit v3 body coverage while the two curved mantle meshes have torn holes.
    mantle = node('ScalarParameter', parameter_name='FormMantle', default_value=0.)
    opacity = node('ScalarParameter', parameter_name='FormOpacity', default_value=1.)
    mantle_uv = node('TextureCoordinate')
    mantle_pan = node('Panner', speed_x=.025, speed_y=-.055)
    wire(mantle_uv, '', mantle_pan, 'Coordinate')
    mantle_ink = node('TextureSample', texture=unreal.load_asset(INK))
    wire(mantle_pan, '', mantle_ink, 'UVs')
    grain_inputs = ((noise, 'R', 'Noise'), (ink, 'R', 'Ink'))
    body = custom('''
float n = pow(saturate((Noise - .0075) / (.5841 - .0075)), .55);
float ink = pow(saturate((Ink - .0009) / (.3140 - .0009)), .30);
float grain = saturate(n * .55 + ink * .45);
float3 body = float3(.025, .024, .029) + float3(.042, .019, .027) * grain * grain;
float3 mantle = float3(.022, .012, .017) + float3(.055, .007, .012) * grain;
return lerp(body, mantle, saturate(Mantle));
''', grain_inputs + ((mantle, '', 'Mantle'),), unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    emission = custom('''
float n = pow(saturate((Noise - .0075) / (.5841 - .0075)), .55);
float ink = pow(saturate((Ink - .0009) / (.3140 - .0009)), .30);
float grain = saturate(n * .55 + ink * .45);
float veins = 1 - smoothstep(.003, .024, abs(n - ink * .67 - .17));
veins *= smoothstep(.35, .75, grain);
float edge = pow(saturate(Facing), 1.15) * (.45 + .55 * grain);
float energy = (edge * .55 + veins * .16) * (.58 + .42 * saturate(Strength));
float3 color = float3(.75, .002, .013) * energy;
color += float3(.9, .005, .020) * saturate(Pulse) * (edge * .5 + veins * .25);
float uvInk = pow(saturate((MaskNoise - .0009) / (.3140 - .0009)), .30);
float field = uvInk * .72 + grain * .28;
float tornEdge = 1 - smoothstep(.018, .055, abs(field - .34));
float irregularRim = edge * smoothstep(.32, .72, grain) * (.55 + .45 * uvInk);
float3 cloak = float3(1.0, .003, .018) * (irregularRim * .48 + tornEdge * .045 + veins * .018);
cloak += float3(.012, .0003, .001) * ink * ink;
cloak += float3(.8, .004, .017) * saturate(Pulse) * (.06 + irregularRim * .30);
color = lerp(color, cloak, saturate(Mantle));
return color;
''', grain_inputs + (
        (mantle, '', 'Mantle'), (mantle_ink, 'R', 'MaskNoise'),
        (node('Fresnel', exponent=5.5, base_reflect_fraction=0.), '', 'Facing'),
        (node('ScalarParameter', parameter_name='FormStrength', default_value=1.), '', 'Strength'),
        (node('ScalarParameter', parameter_name='FormPulse', default_value=0.), '', 'Pulse')),
        unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    mask = custom('''
float n = pow(saturate((Noise - .0075) / (.5841 - .0075)), .55);
float ink = pow(saturate((Ink - .0009) / (.3140 - .0009)), .30);
float grain = saturate(n * .55 + ink * .45);
float uvInk = pow(saturate((MaskNoise - .0009) / (.3140 - .0009)), .30);
float coverage = smoothstep(.18, .34, uvInk * .72 + grain * .28);
return lerp(1., coverage * saturate(Opacity), saturate(Mantle));
''', grain_inputs + ((mantle, '', 'Mantle'), (mantle_ink, 'R', 'MaskNoise'), (opacity, '', 'Opacity')),
        unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    mantle_motion = custom('''
float loose = saturate(UV.y * .8 + .2);
float wave = sin(UV.x * 12 + UV.y * 8 + Clock * 2.6) * .65;
wave += sin(UV.y * 19 - UV.x * 5 - Clock * 3.1) * .35;
return Normal * (wave * 3.4 * loose * saturate(Mantle));
''', ((mantle_uv, '', 'UV'), (node('Time'), '', 'Clock'), (node('VertexNormalWS'), '', 'Normal'),
      (mantle, '', 'Mantle')), unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    roughness = custom('return .52 + .14 * saturate(Noise);', ((noise, 'R', 'Noise'),), unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    for source, prop in ((body, unreal.MaterialProperty.MP_BASE_COLOR),
                         (emission, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                         (mask, unreal.MaterialProperty.MP_OPACITY_MASK),
                         (mantle_motion, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET),
                         (roughness, unreal.MaterialProperty.MP_ROUGHNESS),
                         (node('Constant', r=.24), unreal.MaterialProperty.MP_METALLIC),
                         (node('Constant', r=.42), unreal.MaterialProperty.MP_SPECULAR)):
        if not lib.connect_material_property(source, '', prop):
            raise RuntimeError('Cannot connect form property '+str(prop))
    # UE5.8 MaterialEditingLibrary.h:267 returns TArray<FString>, empty on success.
    errors = lib.recompile_material(material)
    if errors:
        raise RuntimeError('Form material compiler errors '+repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessDemonFormVersion', VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save the owned form material')
    after = _hash_sources()
    if before != after:
        raise RuntimeError('An original source package changed')
    result = {'asset': TARGET, 'source': SOURCE, 'version': VERSION, 'reused': False,
        'migrated_from': old_version, 'passed': True, 'source_hashes_unchanged': True,
        'shading': 'DefaultLit charcoal body / masked torn blood mantle',
        'private_clone_alpha_and_WPO_replaced': True,
        'pack_assets_saved': False, 'source_hashes': after,
        'controls': {'FormStrength': '0→1 over native .5s entry', 'FormPulse': 'short native .16s crimson rupture',
                     'FormMantle': '0 body mask=1 and WPO=0 / 1 two torn curved blood mantles, 3.4cm maximum normal ripple',
                     'FormOpacity': 'mantle-only reveal and release'},
        'visual_acceptance': '실제 게임 본체/입장/이동 중 화면 확인 대기'}
    _write(output, 'countess-demon-form-material.json', result)
    return result


def author(output):
    result = {'inspection': inspect(output), 'material_authored': False}
    if os.environ.get('COUNTESS_DEMON_AUTHOR_MATERIAL') == '1':
        result['material'] = build_material(output)
        result['material_authored'] = True
    result['passed'] = True
    return result
