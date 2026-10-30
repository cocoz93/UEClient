"""D 유성이 바닥에 남기는 그을음 자국(10-20 「바닥에 부딪혔을 때 흔적 같은 게 남고, 스킬 다 끝나면 자연스럽게 사라지게」).
/Game/TopDown/Characters/Gideon/FX/M_Gideon_StarScorch: 바닥에 투사하는 반투명 데칼 재질.
  모양 = 가운데가 진하고 가장자리로 흐려지는 원(1 − 거리)^Spread × 얼룩 무늬(T_DecalMask_Noise06)로 테두리를 들쭉날쭉하게.
  색 = 거의 검은 보라(그을음) + 가운데만 옅은 보라 빛(Glow). 투명도와 빛 모두 DecalLifetimeOpacity를 곱해 SetFadeOut으로 서서히 사라진다.
같은 짜임으로 무늬만 바꾼 M_Gideon_StarRune(룬 무늬)·M_Gideon_StarAstro(별 무늬)도 만든다(D 바닥 자국 시안). 게임 코드에서 SpawnDecalAtLocation으로 띄운다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
DEST = '/Game/TopDown/Characters/Gideon/FX/'
NOISE = '/Game/ParagonProps/FX/Textures/Masks/T_DecalMask_Noise06'
RUNE = '/Game/ParagonMinions/FX/Textures/Runes/T_Decal_RuneSheet3c'
ASTRO = '/Game/ParagonKwang/FX/Textures/Debris/T_Decal_Astro'
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {}


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


def multiply(material, a, b, x, y):
    result = node(material, unreal.MaterialExpressionMultiply, x, y)
    link(a, result, 'A')
    link(b, result, 'B')
    return result


def power(material, base, exponent, x, y):
    result = node(material, unreal.MaterialExpressionPower, x, y)
    link(base, result, 'Base')
    link(exponent, result, 'Exp')
    return result


def sampler_for(texture):
    # 압축 설정에 맞는 표본 방식이어야 재질이 컴파일된다.
    compression = texture.get_editor_property('compression_settings')
    srgb = texture.get_editor_property('srgb')
    if compression == unreal.TextureCompressionSettings.TC_MASKS:
        return unreal.MaterialSamplerType.SAMPLERTYPE_MASKS
    if compression in (unreal.TextureCompressionSettings.TC_GRAYSCALE, unreal.TextureCompressionSettings.TC_ALPHA):
        return unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
    if compression == unreal.TextureCompressionSettings.TC_NORMALMAP:
        return unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
    return unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR


def make(name, pattern, noise_strength, spread, glow_sharpness, glow_intensity):
    path = DEST + name
    # 게임 코드가 시작할 때 이 재질을 붙잡고 있어 지우기도(실패), 노드 비우기도(DeleteAllMaterialExpressions — !IsRooted() 단언으로
    # 에디터가 죽음, gideon-36th-marks-20261020-121942) 안 된다 → 이미 있으면 건드리지 않는다. 고치려면 새 이름으로 만들 것.
    if assets.does_asset_exist(path):
        report[name] = {'path': path, 'kept': True}
        return
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST.rstrip('/'), unreal.Material, unreal.MaterialFactoryNew())
    # 혼합 방식을 먼저 바꿔야 한다 — 데칼 영역을 먼저 정하면 불투명 상태로 한 번 컴파일되며 실패한다(첫 실행 로그).
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)

    # 원: f = saturate(1 − |UV×2−1|)
    tc = node(material, unreal.MaterialExpressionTextureCoordinate, -2200, 0)
    two = node(material, unreal.MaterialExpressionConstant, -2200, 120, r=2.0)
    one = node(material, unreal.MaterialExpressionConstant, -2200, 200, r=1.0)
    centered = node(material, unreal.MaterialExpressionSubtract, -1900, 0)
    link(multiply(material, tc, two, -2050, 0), centered, 'A')
    link(one, centered, 'B')
    zero = node(material, unreal.MaterialExpressionConstant2Vector, -1900, 150, r=0.0, g=0.0)
    distance = node(material, unreal.MaterialExpressionDistance, -1750, 0)
    link(centered, distance, 'A')
    link(zero, distance, 'B')
    inverted = node(material, unreal.MaterialExpressionOneMinus, -1600, 0)
    link(distance, inverted, '')
    f = node(material, unreal.MaterialExpressionSaturate, -1450, 0)
    link(inverted, f, '')

    # 얼룩: 무늬 R × NoiseStrength + (1 − NoiseStrength)
    texture = unreal.load_asset(pattern)
    noise = node(material, unreal.MaterialExpressionTextureSample, -1600, 350, texture=texture, sampler_type=sampler_for(texture))
    strength = scalar(material, 'NoiseStrength', noise_strength, -1400, 500)
    lerp = node(material, unreal.MaterialExpressionLinearInterpolate, -1200, 350)
    link(one, lerp, 'A')
    link(noise, lerp, 'B', 'R')
    link(strength, lerp, 'Alpha')

    lifetime = node(material, unreal.MaterialExpressionDecalLifetimeOpacity, -900, 600)

    # 투명도 = saturate(f^Spread × 얼룩 × Hardness) × Opacity × 수명 투명도
    shape = power(material, f, scalar(material, 'Spread', spread, -1300, 150), -1200, 0)
    blotch = multiply(material, shape, lerp, -1000, 100)
    hardened = multiply(material, blotch, scalar(material, 'Hardness', 2.2, -1000, 250), -850, 100)
    clamped = node(material, unreal.MaterialExpressionSaturate, -700, 100)
    link(hardened, clamped, '')
    opacity = multiply(material, multiply(material, clamped, scalar(material, 'Opacity', 0.85, -700, 250), -550, 100), lifetime, -400, 150)
    assert lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)

    color = vector(material, 'ScorchColor', unreal.LinearColor(0.012, 0.006, 0.025, 1), -400, -150)
    assert lib.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)

    # 가운데 빛 = GlowColor × GlowIntensity × f^GlowSharpness × 얼룩 × 수명 투명도
    core = power(material, f, scalar(material, 'GlowSharpness', glow_sharpness, -1300, -300), -1200, -300)
    glow = multiply(material, multiply(material, core, lerp, -1000, -300),
                    vector(material, 'GlowColor', unreal.LinearColor(0.6, 0.25, 1.0, 1), -1000, -450), -850, -300)
    glow = multiply(material, glow, scalar(material, 'GlowIntensity', glow_intensity, -850, -150), -700, -300)
    glow = multiply(material, glow, lifetime, -550, -300)
    assert lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    lib.recompile_material(material)
    report[name] = {'path': path, 'saved': assets.save_asset(path, only_if_is_dirty=False),
                          'pattern': pattern, 'sampler': str(sampler_for(texture)),
                          'scalars': [str(n) for n in lib.get_scalar_parameter_names(material)]}

try:
    # D 바닥 자국 시안(10-20 「바닥 이펙트가 좀 아쉬운데 시안 좀」): 그을음(얼룩 무늬) · 룬 무늬 · 별 무늬.
    # 무늬 둘은 무늬가 그대로 보이게 얼룩 세기 1·원 퍼짐 0.3, 빛을 가운데만이 아니라 무늬 전체에(0.6).
    make('M_Gideon_StarScorch', NOISE, 0.8, 0.7, 4.0, 2.0)
    make('M_Gideon_StarRune', RUNE, 1.0, 0.3, 0.6, 4.0)
    make('M_Gideon_StarAstro', ASTRO, 1.0, 0.3, 0.6, 4.0)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'scorch-material.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
