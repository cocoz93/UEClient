"""F 녹스 번개 2차 재질(10-19, 녹화 대조 뒤). 녹스 번개 = 가는 흰 심 + 가장자리가 부드럽게 번지는 파란 빛무리 + 둘레에 흩어진 불티
(사용자 녹화 녹스푸른번개.mp4 b_009). 원통·한 색 띠는 가장자리가 딱 끊겨 「그림을 떼다 붙인」 느낌이 났다.
/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip: 띠(판)의 가로 방향(V) 가운데가 밝고 가장자리로 부드럽게 꺼지는 가산 재질.
  발광 = CoreColor × f^CoreSharpness × CoreIntensity + GlowColor × f^GlowSoftness × GlowIntensity, f = 1 − |V×2−1|.
/Game/TopDown/Characters/Gideon/FX/M_NoxSpark: 판 한가운데서 둥글게 꺼지는 불티 재질. 발광 = Color × Intensity × (1 − 거리)^Softness.
둘 다 빛만(그늘 없음)·양면·인스턴스 메시용."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
DEST = '/Game/TopDown/Characters/Gideon/FX/'
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {}


def new_material(name):
    path = DEST + name
    if assets.does_asset_exist(path):
        assets.delete_asset(path)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST.rstrip('/'), unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('used_with_instanced_static_meshes', True)
    return material, path


def node(material, cls, x, y, **props):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        expression.set_editor_property(key, value)
    return expression


def link(a, b, to_input, from_output=''):
    assert lib.connect_material_expressions(a, from_output, b, to_input), (a.get_name(), to_input)


def scalar(material, name, value, x, y):
    return node(material, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def vector(material, name, value, x, y):
    return node(material, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=value)


def centered(material, x, y, use_distance):
    """f = 1 − |V×2−1| (띠) 또는 1 − 거리(UV×2−1, 0) (불티), 0~1로 자른 것."""
    tc = node(material, unreal.MaterialExpressionTextureCoordinate, x, y)
    two = node(material, unreal.MaterialExpressionConstant, x, y + 100, r=2.0)
    one = node(material, unreal.MaterialExpressionConstant, x, y + 160, r=1.0)
    mul = node(material, unreal.MaterialExpressionMultiply, x + 150, y)
    link(tc, mul, 'A')
    link(two, mul, 'B')
    sub = node(material, unreal.MaterialExpressionSubtract, x + 300, y)
    link(mul, sub, 'A')
    link(one, sub, 'B')
    if use_distance:
        zero = node(material, unreal.MaterialExpressionConstant2Vector, x + 300, y + 120, r=0.0, g=0.0)
        magnitude = node(material, unreal.MaterialExpressionDistance, x + 450, y)
        link(sub, magnitude, 'A')
        link(zero, magnitude, 'B')
    else:
        mask = node(material, unreal.MaterialExpressionComponentMask, x + 450, y - 120, r=False, g=True, b=False, a=False)
        link(sub, mask, '')
        magnitude = node(material, unreal.MaterialExpressionAbs, x + 600, y - 120)
        link(mask, magnitude, '')
    inverted = node(material, unreal.MaterialExpressionOneMinus, x + 750, y)
    link(magnitude, inverted, '')
    clamped = node(material, unreal.MaterialExpressionSaturate, x + 900, y)
    link(inverted, clamped, '')
    return clamped


def term(material, f, color, intensity, exponent, x, y):
    powered = node(material, unreal.MaterialExpressionPower, x, y)
    link(f, powered, 'Base')
    link(exponent, powered, 'Exp')
    tinted = node(material, unreal.MaterialExpressionMultiply, x + 150, y)
    link(color, tinted, 'A')
    link(powered, tinted, 'B')
    scaled = node(material, unreal.MaterialExpressionMultiply, x + 300, y)
    link(tinted, scaled, 'A')
    link(intensity, scaled, 'B')
    return scaled


try:
    strip, strip_path = new_material('M_NoxGlowStrip')
    f = centered(strip, -1600, 0, use_distance=False)
    core = term(strip, f, vector(strip, 'CoreColor', unreal.LinearColor(1, 1, 1, 1), -600, -300),
                scalar(strip, 'CoreIntensity', 4.0, -600, -200), scalar(strip, 'CoreSharpness', 24.0, -600, -100), -400, -250)
    glow = term(strip, f, vector(strip, 'GlowColor', unreal.LinearColor(0.45, 0.45, 1.0, 1), -600, 200),
                scalar(strip, 'GlowIntensity', 0.6, -600, 300), scalar(strip, 'GlowSoftness', 2.0, -600, 400), -400, 250)
    total = node(strip, unreal.MaterialExpressionAdd, -50, 0)
    link(core, total, 'A')
    link(glow, total, 'B')
    assert lib.connect_material_property(total, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(strip)
    report['strip'] = {'path': strip_path, 'saved': assets.save_asset(strip_path, only_if_is_dirty=False),
                       'scalars': [str(n) for n in lib.get_scalar_parameter_names(strip)]}

    spark, spark_path = new_material('M_NoxSpark')
    f2 = centered(spark, -1600, 0, use_distance=True)
    only = term(spark, f2, vector(spark, 'Color', unreal.LinearColor(0.6, 0.6, 1.0, 1), -600, -200),
                scalar(spark, 'Intensity', 2.0, -600, -100), scalar(spark, 'Softness', 2.5, -600, 0), -400, 0)
    assert lib.connect_material_property(only, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(spark)
    report['spark'] = {'path': spark_path, 'saved': assets.save_asset(spark_path, only_if_is_dirty=False),
                       'scalars': [str(n) for n in lib.get_scalar_parameter_names(spark)]}
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'noxglow-material.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
