"""Make Aurora's Ice Armor shell material /Game/TopDown/Characters/Aurora/FX/M_Aurora_ArmorShell: unlit translucent,
a soft grey glow at the rim (fresnel) and a faint fill inside, so the body stays visible through it. Paragon shield
materials were either black inside or invisible on the dark floor (aurora-9th-shield-mat runs). Rebuilds the graph if the
asset already exists. Parameters: Colour_A (rim/fill colour), Brightness, RimPower, RimOpacity, FillOpacity, and the frost
pattern FrostTexture / FrostTiling / FrostOpacity / FrostGlow."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
FOLDER = '/Game/TopDown/Characters/Aurora/FX'
NAME = 'M_Aurora_ArmorShell'
# 2차(2026-10-18 사용자 「얼음 보호막 같은 느낌」): 표면에 Aurora 서리 무늬(T_Aurora_Hoarfrost_2_M)를 깔고 색을 얼음빛 회색으로.
FROST = '/Game/ParagonAurora/FX/Textures/Aurora/T_Aurora_Hoarfrost_2_M.T_Aurora_Hoarfrost_2_M'
DEFAULTS = {'Brightness': 1.2, 'RimPower': 2.5, 'RimOpacity': 0.55, 'FillOpacity': 0.05,
            'FrostTiling': 2.0, 'FrostOpacity': 0.28, 'FrostGlow': 0.9}
COLOR = (0.60, 0.67, 0.74)
report = {'passed': False, 'asset': f'{FOLDER}/{NAME}', 'defaults': DEFAULTS, 'colour': COLOR}
lib = unreal.MaterialEditingLibrary


def scalar(material, name, x, y):
    node = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', DEFAULTS[name])
    return node


def binary(material, kind, a, b, x, y):
    node = lib.create_material_expression(material, kind, x, y)
    lib.connect_material_expressions(a, '', node, 'A')
    lib.connect_material_expressions(b, '', node, 'B')
    return node


try:
    path = f'{FOLDER}/{NAME}'
    material = unreal.load_asset(path)
    report['created'] = material is None
    if material is None:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset(NAME, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError('Could not create the shell material')
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', False)

    # 가장자리일수록 1에 가까운 값(fresnel^RimPower). 색 = Colour_A × Brightness × 가장자리, 불투명 = 안쪽 FillOpacity ~ 가장자리 RimOpacity.
    fresnel = lib.create_material_expression(material, unreal.MaterialExpressionFresnel, -900, 0)
    rim_power = scalar(material, 'RimPower', -1100, 60)
    lib.connect_material_expressions(rim_power, '', fresnel, 'ExponentIn')
    colour = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -900, -260)
    colour.set_editor_property('parameter_name', 'Colour_A')
    colour.set_editor_property('default_value', unreal.LinearColor(COLOR[0], COLOR[1], COLOR[2], 1.0))
    brightness = scalar(material, 'Brightness', -900, -120)
    lit = binary(material, unreal.MaterialExpressionMultiply, colour, brightness, -650, -200)
    fill = scalar(material, 'FillOpacity', -900, 200)
    rim = scalar(material, 'RimOpacity', -900, 320)
    blend = lib.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate, -450, 200)
    lib.connect_material_expressions(fill, '', blend, 'A')
    lib.connect_material_expressions(rim, '', blend, 'B')
    lib.connect_material_expressions(fresnel, '', blend, 'Alpha')
    glow = lib.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate, -450, -200)
    lib.connect_material_expressions(fill, '', glow, 'A')
    constant_one = lib.create_material_expression(material, unreal.MaterialExpressionConstant, -650, -60)
    constant_one.set_editor_property('r', 1.0)
    lib.connect_material_expressions(constant_one, '', glow, 'B')
    lib.connect_material_expressions(fresnel, '', glow, 'Alpha')

    # 서리 무늬: 구 UV를 FrostTiling배로 깔아 R 값만큼 불투명·빛을 더한다(가장자리 빛과 별개로 표면 전체에 성에가 낀 듯).
    texture = unreal.load_asset(FROST)
    if texture is None:
        raise RuntimeError('Frost texture missing: ' + FROST)
    coords = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1500, 520)
    tiling = scalar(material, 'FrostTiling', -1500, 640)
    tiled = binary(material, unreal.MaterialExpressionMultiply, coords, tiling, -1300, 560)
    frost = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 520)
    frost.set_editor_property('parameter_name', 'FrostTexture')
    frost.set_editor_property('texture', texture)
    compression = texture.get_editor_property('compression_settings')
    if compression == unreal.TextureCompressionSettings.TC_MASKS:
        frost.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    elif compression in (unreal.TextureCompressionSettings.TC_GRAYSCALE, unreal.TextureCompressionSettings.TC_ALPHA):
        frost.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE)
    elif not texture.get_editor_property('srgb'):
        frost.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    report['frost_compression'] = str(compression)
    lib.connect_material_expressions(tiled, '', frost, 'UVs')
    frost_opacity = binary(material, unreal.MaterialExpressionMultiply, frost, scalar(material, 'FrostOpacity', -900, 640),
        -650, 560)
    lib.connect_material_expressions(frost, 'R', frost_opacity, 'A')
    frost_glow = binary(material, unreal.MaterialExpressionMultiply, frost, scalar(material, 'FrostGlow', -900, 760), -650, 700)
    lib.connect_material_expressions(frost, 'R', frost_glow, 'A')
    opacity = binary(material, unreal.MaterialExpressionAdd, blend, frost_opacity, -250, 260)
    clamped = lib.create_material_expression(material, unreal.MaterialExpressionSaturate, -100, 260)
    lib.connect_material_expressions(opacity, '', clamped, '')
    shine = binary(material, unreal.MaterialExpressionAdd, glow, frost_glow, -300, -100)
    emissive = binary(material, unreal.MaterialExpressionMultiply, lit, shine, -150, -200)
    lib.connect_material_property(emissive, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(clamped, '', unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save the shell material')
    report['expressions'] = lib.get_num_material_expressions(material)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'aurora-shell-material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
