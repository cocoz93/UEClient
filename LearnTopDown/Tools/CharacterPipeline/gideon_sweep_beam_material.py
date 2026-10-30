"""A 시안 7 빛줄기 재질(10-20 「A7 느낌 괜찮은데 광선 느낌으로 — 디테일·이펙트 신경」). 빛 점 줄은 구슬 꿴 줄로 보여 판(띠)에 그린다.
/Game/TopDown/Characters/Gideon/FX/M_Gideon_SweepBeam: 띠(판)에 쓰는 가산·빛만·양면·인스턴스 메시용 재질.
  a = 길이 방향 0(뿌리)~1(끝)(FlipU = 1이면 U를 뒤집음), V = 굵기 방향.
  일렁임: Gideon 팩 T_Turbulence_Seamless를 길이 방향으로 흘려 V를 Wobble만큼 비튼다(가장자리가 꿈틀).
  발광 = (흰 심 f^CoreSharpness×CoreIntensity + 보라 빛무리 f^GlowSoftness×GlowIntensity×일렁임
         + 흐르는 에너지 가닥(T_EnergyPlasma_Tile_H_01 G, 길이 방향으로 FlowSpeed만큼 흐름)×StrandIntensity
         + 가는 흰 실(같은 무늬 R, 뒤집어 다른 빠르기))
       × 끝 쪽 TipFade 구간에서 0으로 × 뿌리 RootFade 구간에서 0으로 × Fade, f = 1 − |V'×2−1|.
이미 있으면 건드리지 않는다(생성자가 붙잡고 있는 재질은 지우면 에디터가 죽음 — gideon_scorch_material.py와 같은 까닭)."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
DEST = '/Game/TopDown/Characters/Gideon/FX/'
NAME = os.environ.get('SWEEP_BEAM_NAME', 'M_Gideon_SweepBeam')
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {}


def node(material, cls, x, y, **props):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        expression.set_editor_property(key, value)
    return expression


def link(a, b, to_input, from_output=''):
    assert lib.connect_material_expressions(a, from_output, b, to_input), (a.get_name(), from_output, b.get_name(), to_input)


def scalar(material, name, value, x, y):
    return node(material, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def vector(material, name, value, x, y):
    return node(material, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=value)


def const(material, value, x, y):
    return node(material, unreal.MaterialExpressionConstant, x, y, r=value)


def binary(material, cls, a, b, x, y, a_out='', b_out=''):
    expression = node(material, cls, x, y)
    link(a, expression, 'A', a_out)
    link(b, expression, 'B', b_out)
    return expression


def unary(material, cls, a, x, y, a_out=''):
    expression = node(material, cls, x, y)
    link(a, expression, '', a_out)
    return expression


def _mask(material, source, flags, x, y):
    expression = node(material, unreal.MaterialExpressionComponentMask, x, y, **flags)
    link(source, expression, '')
    return expression


def flowing_uv(material, a, v, tiling, speed, time, x, y):
    """(a × tiling − time × speed, v)"""
    scaled = binary(material, unreal.MaterialExpressionMultiply, a, tiling, x, y)
    moved = binary(material, unreal.MaterialExpressionMultiply, time, speed, x, y + 80)
    along = binary(material, unreal.MaterialExpressionSubtract, scaled, moved, x + 150, y)
    return binary(material, unreal.MaterialExpressionAppendVector, along, v, x + 300, y)


def sample(material, texture, uv, x, y):
    expression = node(material, unreal.MaterialExpressionTextureSample, x, y, texture=texture)
    link(uv, expression, 'UVs')
    return expression


def powered(material, base, exponent, x, y):
    expression = node(material, unreal.MaterialExpressionPower, x, y)
    link(base, expression, 'Base')
    link(exponent, expression, 'Exp')
    return expression


try:
    path = DEST + NAME
    if assets.does_asset_exist(path):
        report['skipped'] = 'exists'
    else:
        plasma_tex = unreal.load_asset('/Game/ParagonGideon/FX/Textures/Energy/Plasma/T_EnergyPlasma_Tile_H_01.T_EnergyPlasma_Tile_H_01')
        turb_tex = unreal.load_asset('/Game/ParagonGideon/FX/Textures/Energy/Plasma/T_Turbulence_Seamless.T_Turbulence_Seamless')
        assert plasma_tex and turb_tex
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DEST.rstrip('/'), unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
        m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        m.set_editor_property('two_sided', True)
        m.set_editor_property('used_with_instanced_static_meshes', True)

        tc = node(m, unreal.MaterialExpressionTextureCoordinate, -3000, 0)
        u = _mask(m, tc, {'r': True, 'g': False, 'b': False, 'a': False}, -2850, -100)
        v = _mask(m, tc, {'r': False, 'g': True, 'b': False, 'a': False}, -2850, 100)
        flip = scalar(m, 'FlipU', 0.0, -2850, -250)
        a = node(m, unreal.MaterialExpressionLinearInterpolate, -2650, -150)
        link(u, a, 'A')
        link(unary(m, unreal.MaterialExpressionOneMinus, u, -2750, -50), a, 'B')
        link(flip, a, 'Alpha')
        time = node(m, unreal.MaterialExpressionTime, -2850, 300)

        # 일렁임: 길이 방향으로 흐르는 난류 무늬(0.25~0.65)로 V를 비튼다.
        turb_uv = flowing_uv(m, a, v, scalar(m, 'TurbTiling', 2.0, -2650, 400), scalar(m, 'TurbSpeed', 0.6, -2650, 480), time, -2450, 400)
        turb = sample(m, turb_tex, turb_uv, -2050, 400)
        centered = binary(m, unreal.MaterialExpressionSubtract, turb, const(m, 0.45, -1900, 520), -1850, 400, a_out='R')
        wobble = binary(m, unreal.MaterialExpressionMultiply, centered, scalar(m, 'Wobble', 0.25, -1850, 560), -1700, 400)
        v2 = binary(m, unreal.MaterialExpressionAdd, v, wobble, -1550, 200)
        twice = binary(m, unreal.MaterialExpressionMultiply, v2, const(m, 2.0, -1450, 300), -1400, 200)
        offset = binary(m, unreal.MaterialExpressionSubtract, twice, const(m, 1.0, -1300, 300), -1250, 200)
        f = unary(m, unreal.MaterialExpressionSaturate, unary(m, unreal.MaterialExpressionOneMinus,
                  unary(m, unreal.MaterialExpressionAbs, offset, -1100, 200), -950, 200), -800, 200)

        core = binary(m, unreal.MaterialExpressionMultiply,
                      binary(m, unreal.MaterialExpressionMultiply, vector(m, 'CoreColor', unreal.LinearColor(1, 0.95, 1, 1), -700, -400),
                             powered(m, f, scalar(m, 'CoreSharpness', 10.0, -800, -300), -650, -300), -500, -400),
                      scalar(m, 'CoreIntensity', 6.0, -500, -250), -350, -400)
        turb_gain = binary(m, unreal.MaterialExpressionMultiply, turb, const(m, 2.0, -1900, 640), -1700, 600, a_out='R')
        glow = binary(m, unreal.MaterialExpressionMultiply,
                      binary(m, unreal.MaterialExpressionMultiply, vector(m, 'GlowColor', unreal.LinearColor(0.55, 0.25, 1.0, 1), -700, -100),
                             powered(m, f, scalar(m, 'GlowSoftness', 1.5, -800, 0), -650, 0), -500, -100),
                      binary(m, unreal.MaterialExpressionMultiply, scalar(m, 'GlowIntensity', 2.0, -650, 80), turb_gain, -500, 80), -350, -100)

        plasma_uv = flowing_uv(m, a, v, scalar(m, 'FlowTiling', 4.0, -2650, 800), scalar(m, 'FlowSpeed', 2.5, -2650, 880), time, -2450, 800)
        plasma = sample(m, plasma_tex, plasma_uv, -2050, 800)
        strand_mask = binary(m, unreal.MaterialExpressionMultiply, plasma, powered(m, f, scalar(m, 'StrandSoftness', 1.0, -1900, 950), -1750, 950),
                             -1550, 800, a_out='G')
        strands = binary(m, unreal.MaterialExpressionMultiply,
                         binary(m, unreal.MaterialExpressionMultiply, vector(m, 'StrandColor', unreal.LinearColor(0.75, 0.45, 1.0, 1), -700, 300),
                                strand_mask, -500, 300),
                         scalar(m, 'StrandIntensity', 3.0, -500, 420), -350, 300)
        # 가는 흰 실: 같은 무늬의 R을 V를 뒤집어 다른 빠르기로.
        v_flip = unary(m, unreal.MaterialExpressionOneMinus, v, -2650, 1150)
        plasma2 = sample(m, plasma_tex, flowing_uv(m, a, v_flip, scalar(m, 'FlowTiling2', 2.8, -2650, 1200),
                                                   scalar(m, 'FlowSpeed2', 4.0, -2650, 1280), time, -2450, 1200), -2050, 1200)
        filament_mask = binary(m, unreal.MaterialExpressionMultiply, plasma2, powered(m, f, const(m, 3.0, -1900, 1350), -1750, 1350),
                               -1550, 1200, a_out='R')
        filaments = binary(m, unreal.MaterialExpressionMultiply, filament_mask, scalar(m, 'FilamentIntensity', 2.0, -1550, 1350), -1400, 1200)
        filaments_rgb = binary(m, unreal.MaterialExpressionMultiply, vector(m, 'FilamentColor', unreal.LinearColor(1, 0.85, 1, 1), -1400, 1050),
                               filaments, -1250, 1100)

        total = binary(m, unreal.MaterialExpressionAdd,
                       binary(m, unreal.MaterialExpressionAdd, core, glow, -200, -250),
                       binary(m, unreal.MaterialExpressionAdd, strands, filaments_rgb, -200, 350), -50, 0)
        tip = unary(m, unreal.MaterialExpressionSaturate,
                    binary(m, unreal.MaterialExpressionDivide, unary(m, unreal.MaterialExpressionOneMinus, a, -500, 600),
                           scalar(m, 'TipFade', 0.15, -500, 700), -350, 600), -200, 600)
        root = unary(m, unreal.MaterialExpressionSaturate,
                     binary(m, unreal.MaterialExpressionDivide, a, scalar(m, 'RootFade', 0.03, -500, 850), -350, 800), -200, 800)
        ends = binary(m, unreal.MaterialExpressionMultiply, tip, root, -50, 700)
        faded = binary(m, unreal.MaterialExpressionMultiply, ends, scalar(m, 'Fade', 1.0, -50, 850), 100, 700)
        emissive = binary(m, unreal.MaterialExpressionMultiply, total, faded, 250, 0)
        assert lib.connect_material_property(emissive, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.recompile_material(m)
        report['saved'] = assets.save_asset(path, only_if_is_dirty=False)
        report['scalars'] = [str(n) for n in lib.get_scalar_parameter_names(m)]
        report['vectors'] = [str(n) for n in lib.get_vector_parameter_names(m)]
        stats = lib.get_statistics(m)
        report['stats'] = {'pixel': stats.num_pixel_shader_instructions, 'vertex': stats.num_vertex_shader_instructions,
                           'samplers': stats.num_samplers}
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'sweep-beam-material.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
