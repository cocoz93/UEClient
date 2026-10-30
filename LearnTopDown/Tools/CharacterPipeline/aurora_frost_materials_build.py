"""Make Aurora's frost materials under /Game/TopDown/Characters/Aurora/FX (2026-10-18 user feedback round 10 onwards):
- M_Aurora_IceArmor: round ice shell for A - attached honeycomb ice plates over about a fifth of the sphere (drawn
  T_Aurora_Honey_Armor in the sphere's UV), empty body, ice blue, rim broken by drifting noise. Unlit translucent.
  M_Aurora_IceHoney_Small/Medium/Large are the 2026-10-19 drafts (cell size choices, a third covered), built only on request.
- M_Aurora_SnowCover: deferred decal, white snow lying along the Q trail (drawn T_Aurora_SnowCover).
- M_Aurora_FrostFloor: deferred decal, white + ice blue frost floor in a circle with a thin bright ring (S field, Q trail).
- M_Aurora_IceCrack: deferred decal, bold radial ice cracks for the Q trail (drawn T_Aurora_IceCrack, same graph as the snow floor).
- M_Aurora_SnowFloor: deferred decal, snowflake-shaped white + ice frost floor for S (drawn T_Aurora_Snowflake: R lines, G glow).
- M_Aurora_SlashScar / M_Aurora_HasteCrack (2026-10-19 evening warrior drafts): sweeping decals that darken a gouge / cracks
  in the floor with bright broken frost (drawn by aurora_slash_textures.py).
- M_Aurora_RimCrack / RimShatter / RuptureCrack / ImpactCrack (2026-10-19 night drafts, builder key 'cracks'): S rings cracked
  (thin glowing / thick dark), D floor split along the line, F star crack where a blade struck.
- M_Aurora_WaveBlade / CutMark (2026-10-19 night, builder key 'blades'): unlit two-sided glowing pictures on the engine plane -
  Q1's flying crescent wave (SlashArc picture) and Q2's X cut marks in the air (DashStreak picture), faded by a Fade parameter.
- M_Aurora_WaveBladeBright / GlowIce (2026-10-20 night Q drafts, builder key 'bladedrafts'): a thick crescent glowing through its
  body (SlashWave picture) and self-lit ice (fresnel white edges) for the cones along the wave.
Both decals multiply by DecalLifetimeOpacity so SetFadeIn/SetFadeOut work. Rebuilds the graph if an asset already exists.
The C++ side loads these lazily (TSoftObjectPtr) so this tool can edit them."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
FOLDER = '/Game/TopDown/Characters/Aurora/FX'
ICE_NOISE = '/Game/ParagonAurora/FX/Materials/MaterialLayers/Special/T_Noise_Ice.T_Noise_Ice'
FROST = '/Game/ParagonAurora/FX/Textures/Aurora/T_Aurora_Hoarfrost_2_M.T_Aurora_Hoarfrost_2_M'
LIGHT_FROST = '/Game/ParagonAurora/FX/Materials/MaterialLayers/Special/T_LightFrost.T_LightFrost'
lib = unreal.MaterialEditingLibrary
report = {'passed': False, 'materials': {}, 'failed_links': []}


def _checked_connect(source, source_out, target, target_in):
    # 핀 이름이 틀리면 엔진은 조용히 False만 돌려주고 노드를 비워 둔다(10-18 밤 눈송이 장판이 안 보였던 원인 후보) → 기록한다.
    ok = lib.connect_material_expressions(source, source_out, target, target_in)
    if not ok:
        report['failed_links'].append(f'{source.get_class().get_name()}.{source_out} -> {target.get_class().get_name()}.{target_in}')
    return ok




class Graph:
    def __init__(self, material, defaults):
        self.m = material
        self.defaults = defaults
        self.y = 0

    def node(self, kind, x=None, y=None):
        self.y += 120
        return lib.create_material_expression(self.m, kind, -1200 if x is None else x, self.y if y is None else y)

    def scalar(self, name):
        n = self.node(unreal.MaterialExpressionScalarParameter, -1600)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', self.defaults[name])
        return n

    def colour(self, name):
        n = self.node(unreal.MaterialExpressionVectorParameter, -1600)
        n.set_editor_property('parameter_name', name)
        r, g, b = self.defaults[name]
        n.set_editor_property('default_value', unreal.LinearColor(r, g, b, 1.0))
        return n

    def constant(self, value):
        n = self.node(unreal.MaterialExpressionConstant, -1600)
        n.set_editor_property('r', value)
        return n

    def op(self, kind, a, b, a_out='', b_out=''):
        n = self.node(kind)
        _checked_connect(a, a_out, n, 'A')
        _checked_connect(b, b_out, n, 'B')
        return n

    def lerp(self, a, b, alpha, alpha_out=''):
        n = self.node(unreal.MaterialExpressionLinearInterpolate)
        _checked_connect(a, '', n, 'A')
        _checked_connect(b, '', n, 'B')
        _checked_connect(alpha, alpha_out, n, 'Alpha')
        return n

    def saturate(self, a):
        n = self.node(unreal.MaterialExpressionSaturate)
        _checked_connect(a, '', n, '')
        return n

    def uv(self, tiling_name, pan=None):
        coords = self.node(unreal.MaterialExpressionTextureCoordinate, -2000)
        tiled = self.op(unreal.MaterialExpressionMultiply, coords, self.scalar(tiling_name))
        if not pan:
            return tiled
        panner = self.node(unreal.MaterialExpressionPanner)
        panner.set_editor_property('speed_x', pan[0])
        panner.set_editor_property('speed_y', pan[1])
        _checked_connect(tiled, '', panner, 'Coordinate')
        return panner

    def texture(self, path, uvs, name):
        asset = unreal.load_asset(path)
        if asset is None:
            raise RuntimeError('Texture missing: ' + path)
        n = self.node(unreal.MaterialExpressionTextureSampleParameter2D, -800)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('texture', asset)
        compression = asset.get_editor_property('compression_settings')
        if compression == unreal.TextureCompressionSettings.TC_MASKS:
            n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        elif compression in (unreal.TextureCompressionSettings.TC_GRAYSCALE, unreal.TextureCompressionSettings.TC_ALPHA):
            n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE)
        elif compression == unreal.TextureCompressionSettings.TC_NORMALMAP:
            n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif not asset.get_editor_property('srgb'):
            n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        _checked_connect(uvs, '', n, 'UVs')
        report.setdefault('textures', {})[path] = str(compression)
        return n


def begin(name, decal):
    path = f'{FOLDER}/{name}'
    # 있던 재질은 지우고 새로 만든다. delete_all_material_expressions가 노드를 다 못 지워 다시 만들 때마다 남은 노드가 쌓였고
    # (10-19 눈송이 장판 92 → 104 → 110 → 113 → 162개, 같은 그래프인데), 남은 노드 탓에 「Missing Saturate input」으로 컴파일이
    # 실패해 기본 재질로 떨어졌다(연결 실패 기록 failed_links에는 안 잡힘).
    created = not unreal.EditorAssetLibrary.does_asset_exist(path)
    if not created and not unreal.EditorAssetLibrary.delete_asset(path):
        raise RuntimeError('Could not delete old ' + path)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError('Could not create ' + path)
    if decal:
        # 이 엔진은 데칼 섞기 방식(decal_blend_mode)을 막아 두고 일반 섞기 방식(반투명)을 데칼에도 쓴다.
        # 반투명을 먼저 정한다 — 새 재질(불투명)에 데칼 영역부터 넣으면 그 순간 다시 컴파일되며 「데칼은 반투명만」 실패가 로그에 찍힌다.
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    else:
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', False)
    return material, created


def finish(material, name, created, defaults):
    lib.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + name)
    # 연결은 다 됐는데 입력이 빈 노드가 있으면 컴파일이 실패한다 → 입력이 하나도 안 꽂힌 계산 노드를 센다(텍스처·상수·좌표·시간 같은
    # 입력 없는 노드는 뺀다).
    sources = ('Constant', 'Parameter', 'TextureCoordinate', 'Time', 'Fresnel', 'DecalLifetimeOpacity', 'TwoSidedSign')
    empty = []
    for expression in lib.get_material_expressions(material):
        kind = expression.get_class().get_name()
        if any(word in kind for word in sources):
            continue
        if not any(lib.get_inputs_for_material_expression(material, expression)):
            empty.append(expression.get_name())
    report['materials'][name] = {'created': created, 'expressions': lib.get_num_material_expressions(material), 'empty_inputs': empty,
                                 'defaults': defaults}
    if empty:
        report['failed_links'].append(f'{name}: no inputs on {", ".join(empty)}')


def broken_rim(g):
    # 구 가장자리 빛(프레넬)을 얼음 잡음으로 군데군데 끊는다(10-18 밤 「원 테두리도 다 보일 필요 없다」). 잡음은 멈춰 둔다
    # (10-19 「너무 일렁이지 않았으면」 — 전엔 천천히 흘러 끊긴 자리가 계속 움직였다).
    fresnel = g.node(unreal.MaterialExpressionFresnel)
    _checked_connect(g.scalar('RimPower'), '', fresnel, 'ExponentIn')
    rim_noise = g.texture(ICE_NOISE, g.uv('RimBreakTiling'), 'RimBreakTexture')
    rim_mask = g.saturate(g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, rim_noise, g.scalar('RimCut'), 'R'), g.scalar('RimSharp')))
    return g.op(unreal.MaterialExpressionMultiply, fresnel, rim_mask)


def build_honey(name, honey_path, two_sided=False, overrides=None):
    # A 시안(10-19 「육각형이 붙어 있는 벌집 느낌, 빽빽하지 않게 1/3쯤 뒤덮인」): aurora_honeycomb_texture.py가 구의 UV(위도·경도)에
    # 맞춰 그린 벌집(R = 덮인 칸 판, G = 덮인 칸 테두리, B = 모든 칸의 옅은 테두리)을 구 UV 그대로 깐다. 몸통은 비우고 가장자리는 끊는다.
    # two_sided(10-19 오후 「오브젝트 뒤쪽으로 저 육각형」): 구의 카메라 반대쪽 면(캐릭터 뒤로 비쳐 보이는 면)의 칸도 그린다. 가장자리
    # 빛은 앞면만(뒷면까지 그리면 테두리가 두 겹으로 밝아진다), 뒷면 칸은 BackFade만큼 옅게 해 앞뒤가 구분되게 한다.
    defaults = {'Colour_A': (0.40, 0.70, 1.0), 'Brightness': 1.1, 'RimPower': 3.5, 'RimOpacity': 0.3,
                'RimBreakTiling': 0.8, 'RimCut': 0.45, 'RimSharp': 4.0,
                'PlateOpacity': 0.3, 'PlateGlow': 0.9, 'BorderOpacity': 0.55, 'BorderGlow': 1.4, 'GhostOpacity': 0.04, 'GhostGlow': 0.3}
    if two_sided:
        defaults['BackFade'] = 0.75
    defaults.update(overrides or {})
    material, created = begin(name, False)
    material.set_editor_property('two_sided', two_sided)
    g = Graph(material, defaults)
    rim = broken_rim(g)
    if two_sided:
        front = g.saturate(g.node(unreal.MaterialExpressionTwoSidedSign, -2000))
        rim = g.op(unreal.MaterialExpressionMultiply, rim, front)
    honey = g.texture(honey_path, g.node(unreal.MaterialExpressionTextureCoordinate, -2000), 'HoneyTexture')
    parts = [('R', 'Plate'), ('G', 'Border'), ('B', 'Ghost')]
    cells = None
    cell_shine = None
    for channel, part in parts:
        part_opacity = g.op(unreal.MaterialExpressionMultiply, honey, g.scalar(part + 'Opacity'), channel)
        part_shine = g.op(unreal.MaterialExpressionMultiply, honey, g.scalar(part + 'Glow'), channel)
        cells = part_opacity if cells is None else g.op(unreal.MaterialExpressionAdd, cells, part_opacity)
        cell_shine = part_shine if cell_shine is None else g.op(unreal.MaterialExpressionAdd, cell_shine, part_shine)
    if two_sided:
        # 앞면 1, 뒷면 BackFade
        fade = g.lerp(g.scalar('BackFade'), g.constant(1.0), front)
        cells = g.op(unreal.MaterialExpressionMultiply, cells, fade)
        cell_shine = g.op(unreal.MaterialExpressionMultiply, cell_shine, fade)
    opacity = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, rim, g.scalar('RimOpacity')), cells)
    shine = g.op(unreal.MaterialExpressionAdd, rim, cell_shine)
    lit = g.op(unreal.MaterialExpressionMultiply, g.colour('Colour_A'), g.scalar('Brightness'))
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, lit, shine), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(g.saturate(opacity), '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)


def build_floor(name, pattern, defaults):
    # 데칼 UV(0~1)의 가운데에서 잰 거리 d(가장자리 = 1). 안쪽은 FillOpacity × 무늬, 가장자리 근처에 얇은 밝은 고리.
    material, created = begin(name, True)
    g = Graph(material, defaults)
    coords = g.node(unreal.MaterialExpressionTextureCoordinate, -2000)
    middle = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
    middle.set_editor_property('r', 0.5)
    middle.set_editor_property('g', 0.5)
    distance = g.op(unreal.MaterialExpressionDistance, coords, middle)
    d = g.op(unreal.MaterialExpressionMultiply, distance, g.constant(2.0))
    inside = g.saturate(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.constant(1.0), d),
        g.scalar('EdgeSharp')))
    near_edge = g.node(unreal.MaterialExpressionAbs)
    _checked_connect(g.op(unreal.MaterialExpressionSubtract, d, g.scalar('RingAt')), '', near_edge, '')
    ring = g.saturate(g.op(unreal.MaterialExpressionSubtract, g.constant(1.0),
        g.op(unreal.MaterialExpressionMultiply, near_edge, g.scalar('RingSharp'))))
    tex = g.texture(pattern, g.uv('PatternTiling'), 'PatternTexture')
    weight = g.lerp(g.scalar('PatternFloor'), g.constant(1.0), tex, 'R')
    fill = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, inside, weight), g.scalar('FillOpacity'))
    rim = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, ring, inside), g.scalar('RingOpacity'))
    life = g.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    opacity = g.op(unreal.MaterialExpressionMultiply, g.saturate(g.op(unreal.MaterialExpressionAdd, fill, rim)), life)
    tint = g.lerp(g.colour('IceColour'), g.colour('WhiteColour'), tex, 'R')
    glow = g.op(unreal.MaterialExpressionMultiply, tint, g.scalar('Brightness'))
    lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)


def import_drawn(name, tool):
    # 눈송이(S)·얼음 균열(Q)은 그림 도구(tool)가 그린 SourceArt 그림을 텍스처로 가져와 쓴다. 재질 그래프로 6갈래 팔을 계산하던
    # 눈송이 첫 판은 데칼에서 가운데 원만 보였다(10-18 밤 데칼 미리보기 aurora-12th-decal).
    source = Path(unreal.Paths.project_dir()).resolve() / 'SourceArt' / 'Aurora' / f'{name}.png'
    if not source.exists():
        raise RuntimeError(f'Run {tool} first: ' + str(source))
    # AURORA_REUSE_TEXTURES=1 = 이미 있는 텍스처는 다시 가져오지 않는다(사용자 에디터가 떠 있을 때 새 재질만 만드는 묶음용)
    if os.environ.get('AURORA_REUSE_TEXTURES') == '1' and unreal.EditorAssetLibrary.does_asset_exist(f'{FOLDER}/{name}'):
        report.setdefault('reused_textures', []).append(name)
        return f'{FOLDER}/{name}.{name}'
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = FOLDER
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = unreal.load_asset(f'{FOLDER}/{name}.{name}')
    if texture is None:
        raise RuntimeError(name + ' import failed')
    # 마스크 압축(sRGB 끔): 회색조(sRGB 끔)로 두면 표본 노드 형식(Grayscale)과 어긋나 컴파일이 실패하고 기본 재질(초록)이 보였다.
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('srgb', False)
    # 시전할 때 처음 불러오는 텍스처라 스트리밍이면 낮은 해상도로 먼저 깔려 가는 선이 뭉개진다(10-18 밤 미리보기) → 통째로 올린다.
    texture.set_editor_property('never_stream', True)
    unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
    return f'{FOLDER}/{name}.{name}'


def build_snow_floor(name, flake_path, pattern, defaults, rough=False):
    # 눈송이 모양 장판(S, 10-18 밤 「원보다는 눈 모양」): 데칼 UV 그대로 눈송이 그림을 깐다. R = 선(또렷하게, 흰빛 쪽),
    # G = 선 둘레에 퍼진 빛(서리 무늬로 흰색↔얼음색이 섞이고 군데군데 옅어진다). 「선을 더 얇게 · 디테일 좀 더」로 2차에 나눴다.
    # Q 얼음 균열 자국도 같은 짜임에 균열 그림만 바꿔 쓴다.
    # B = 안을 옅게 채우는 원판(눈송이만, 10-19 「마법진 내부를 약간 흰색 톤으로」): FillOpacity만큼 깔고 FillWhite만큼 흰빛 쪽으로.
    # S 시안(10-19 「너무 깔끔해 게임풍과 안 어울린다」, C++이 재질 사본 값으로 고른다. 0이면 그 전 그대로):
    # Grit = 선·퍼진 빛을 Aurora 서리 무늬(T_Aurora_Hoarfrost_2_M)로 닳게 · FrostFill = 원판 안에 그 서리 무늬를 깐다
    # Reveal(10-20 S 「바깥 고리부터 그려지듯」): 가운데에서 잰 거리가 먼 곳부터 드러난다 — C++이 0 → 1.1로 올린다.
    # 기본 1.1이면 처음부터 다 보인다(같은 짜임을 쓰는 Q 얼음 균열·눈 덮임은 그대로).
    # 돎·맥동(10-20 S 「다 아쉬운데 뭐가 문제지」 시안 — 깔린 뒤 9초 내내 안 움직임): SpinOuter·SpinInner = 가운데에서 잰 거리
    # SpinSplit(가운데 0 ~ 테두리 1)보다 바깥·안쪽 그림을 도는 빠르기(라디안/초, 부호 = 방향) · PulseStrength = 빛 세기가 PulsePeriod초마다
    # 오르내리는 폭 · GlowBoost = 빛 세기에 더하는 배율(깔리는 순간 번쩍). 기본 0이면 그 전과 같다.
    defaults = {'FillOpacity': 0.0, 'FillWhite': 0.0, 'Grit': 0.0, 'GritTiling': 2.5, 'FrostFill': 0.0, 'FrostTiling': 1.5,
                'GlintStrength': 0.0, 'GlintGlow': 0.0, 'TwinklePeriod': 3.0, 'WaveStrength': 0.0, 'WaveGlow': 0.0, 'WavePeriod': 5.0,
                'WaveWidth': 0.12, 'Reveal': 1.1, 'RevealSharp': 8.0, 'SpinOuter': 0.0, 'SpinInner': 0.0, 'SpinSplit': 0.88,
                'PulseStrength': 0.0, 'PulsePeriod': 2.0, 'GlowBoost': 0.0, 'CircleMask': 0.0, **defaults}
    # rough(10-20 밤 S 「2가 그나마 괜찮긴 한데 시안 더」 — 거친 장판 재질에만): GritCut·GritGain = 갉음 경계(기본 0.15·2.2면 그 전과 같다) ·
    # GritFine·GritFineTiling = 잔 서리 무늬로 한 겹 더 갉음(기본 0이면 없음)
    if rough:
        defaults = {'GritCut': 0.15, 'GritGain': 2.2, 'GritFine': 0.0, 'GritFineTiling': 7.0, **defaults}
    material, created = begin(name, True)
    g = Graph(material, defaults)
    coords = g.node(unreal.MaterialExpressionTextureCoordinate, -2000)
    centre = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
    centre.set_editor_property('r', 0.5)
    centre.set_editor_property('g', 0.5)
    time = g.node(unreal.MaterialExpressionTime)

    def spun(speed_name):
        # 가운데를 축으로 시간 × 빠르기만큼 돌린 UV(Rotator 노드의 각 = Time 입력 × Speed 1, 라디안)
        rotor = g.node(unreal.MaterialExpressionRotator, -2000)
        rotor.set_editor_property('speed', 1.0)
        _checked_connect(coords, '', rotor, 'Coordinate')
        _checked_connect(g.op(unreal.MaterialExpressionMultiply, time, g.scalar(speed_name)), '', rotor, 'Time')
        return rotor

    # 바깥 띠와 안쪽 무늬를 따로 돌린다 — 거리는 돌려도 같으므로 돌리기 전 UV로 나눈다(경계는 그림이 비어 있는 틈에 둔다)
    from_centre = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionDistance, coords, centre), g.constant(2.0))
    outer_band = g.saturate(g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, from_centre, g.scalar('SpinSplit')), g.constant(100.0)))
    flake = g.texture(flake_path, g.lerp(spun('SpinInner'), spun('SpinOuter'), outer_band), 'FlakeTexture')
    tex = g.texture(pattern, g.uv('PatternTiling'), 'PatternTexture')
    weight = g.lerp(g.scalar('PatternFloor'), g.constant(1.0), tex, 'R')
    life = g.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    grit_tex = g.texture(FROST, g.uv('GritTiling'), 'GritTexture')
    if rough:
        worn = g.lerp(g.constant(1.0), g.saturate(g.op(unreal.MaterialExpressionMultiply,
            g.op(unreal.MaterialExpressionSubtract, grit_tex, g.scalar('GritCut'), 'R'), g.scalar('GritGain'))), g.scalar('Grit'))
        fine_tex = g.texture(FROST, g.uv('GritFineTiling'), 'GritFineTexture')
        fine = g.lerp(g.constant(1.0), g.saturate(g.op(unreal.MaterialExpressionMultiply,
            g.op(unreal.MaterialExpressionSubtract, fine_tex, g.constant(0.15), 'R'), g.constant(2.2))), g.scalar('GritFine'))
        worn = g.op(unreal.MaterialExpressionMultiply, worn, fine)
    else:
        worn = g.lerp(g.constant(1.0), g.saturate(g.op(unreal.MaterialExpressionMultiply,
            g.op(unreal.MaterialExpressionSubtract, grit_tex, g.constant(0.15), 'R'), g.constant(2.2))), g.scalar('Grit'))
    lines = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, flake, g.scalar('LineOpacity'), 'R'), worn)
    halo = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionMultiply, flake, weight, 'G'), g.scalar('HaloOpacity')), worn)
    fill = g.op(unreal.MaterialExpressionMultiply, flake, g.scalar('FillOpacity'), 'B')
    frost_tex = g.texture(FROST, g.uv('FrostTiling'), 'FrostTexture')
    frost = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, flake, frost_tex, 'B', 'R'),
        g.scalar('FrostFill'))
    # 별빛·빛 띠(10-19 「구원의 세레나데처럼 반짝거리는 느낌, 아주 느리게」 — 색·톤은 그대로, 흰빛만 더한다):
    # 별빛 = T_Aurora_Glints R(별 모양) × 박자(별마다 G만큼 늦춘 사인을 0~1로 올려 세제곱 → TwinklePeriod초에 한 번 천천히 켜졌다 꺼짐)
    # 빛 띠 = 대각선으로 WavePeriod초에 한 번 원판(B)을 가로지르는 부드러운 띠
    glint_tex = g.texture(import_drawn('T_Aurora_Glints', 'aurora_snowflake_texture.py'), coords, 'GlintTexture')
    beat = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionDivide, time, g.scalar('TwinklePeriod')), glint_tex, '', 'G')
    sine = g.node(unreal.MaterialExpressionSine)
    sine.set_editor_property('period', 1.0)
    _checked_connect(beat, '', sine, '')
    rise = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, sine, g.constant(0.5)), g.constant(0.5))
    pulse = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, rise, rise), rise)
    glint = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, glint_tex, pulse, 'R'), g.scalar('GlintStrength'))
    diagonal = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
    diagonal.set_editor_property('r', 0.7071)
    diagonal.set_editor_property('g', 0.7071)
    across = g.node(unreal.MaterialExpressionDotProduct)
    _checked_connect(g.op(unreal.MaterialExpressionSubtract, coords, centre), '', across, 'A')
    _checked_connect(diagonal, '', across, 'B')
    sweep = g.node(unreal.MaterialExpressionFrac)
    _checked_connect(g.op(unreal.MaterialExpressionDivide, time, g.scalar('WavePeriod')), '', sweep, '')
    front = g.op(unreal.MaterialExpressionSubtract, g.op(unreal.MaterialExpressionMultiply, sweep, g.constant(1.8)), g.constant(0.9))
    gap = g.node(unreal.MaterialExpressionAbs)
    _checked_connect(g.op(unreal.MaterialExpressionSubtract, across, front), '', gap, '')
    band_lin = g.saturate(g.op(unreal.MaterialExpressionSubtract, g.constant(1.0),
        g.op(unreal.MaterialExpressionDivide, gap, g.scalar('WaveWidth'))))
    band = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionMultiply, band_lin, band_lin), flake, '', 'B'), g.scalar('WaveStrength'))
    # 드러남: 차례 = 0.9 × (1 - 가운데에서 잰 거리 × 2), 보임 = saturate((Reveal - 차례) × RevealSharp). 0.9배는 Reveal 1.1에서
    # 가운데까지 다 보이게(1배면 가운데가 (1.1 - 1) × 8 = 0.8로 덜 보인다). 가운데에서 잰 거리(from_centre)는 위 돎과 같이 쓴다.
    order = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.constant(1.0), from_centre), g.constant(0.9))
    shown = g.saturate(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.scalar('Reveal'), order),
        g.scalar('RevealSharp')))
    # 맥동·번쩍(위 설명): 빛 세기 × (1 + GlowBoost + PulseStrength × sin(2π × 시간 / PulsePeriod)), 불투명은 × (1 + GlowBoost/2 + 같은 맥동)
    # — 첫 시안은 빛 세기만 올려 흰 선에서 거의 안 보였다(화면 선 평균 178 → 203). CircleMask 1 = 원 밖을 지운다(돌리면 원 밖 UV가
    # 이웃 칸 그림을 비춰 원 바깥에 호가 생겼다). Q 균열·눈 덮임은 네모 데칼 끝까지 그림이 있어 기본 0.
    beat_wave = g.node(unreal.MaterialExpressionSine)
    beat_wave.set_editor_property('period', 1.0)
    _checked_connect(g.op(unreal.MaterialExpressionDivide, time, g.scalar('PulsePeriod')), '', beat_wave, '')
    beat = g.op(unreal.MaterialExpressionMultiply, beat_wave, g.scalar('PulseStrength'))
    swell = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionAdd, g.constant(1.0), g.scalar('GlowBoost')), beat)
    thicken = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionAdd, g.constant(1.0),
        g.op(unreal.MaterialExpressionMultiply, g.scalar('GlowBoost'), g.constant(0.5))), beat)
    inside = g.lerp(g.constant(1.0), g.saturate(g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, g.constant(1.0), from_centre), g.constant(100.0))), g.scalar('CircleMask'))
    opacity = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply,
        g.saturate(g.op(unreal.MaterialExpressionMultiply, g.saturate(g.op(unreal.MaterialExpressionAdd,
        g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionAdd, lines, halo), g.op(unreal.MaterialExpressionAdd, fill, frost)),
        g.op(unreal.MaterialExpressionAdd, glint, band))), thicken)), life), shown), inside)
    frosty = g.lerp(g.colour('IceColour'), g.colour('WhiteColour'), tex, 'R')
    whiten = g.saturate(g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, flake, g.constant(1.0), 'R'),
        g.op(unreal.MaterialExpressionMultiply, flake, g.scalar('FillWhite'), 'B')))
    tint = g.lerp(frosty, g.colour('WhiteColour'), whiten)
    base_glow = g.op(unreal.MaterialExpressionMultiply, tint,
        g.op(unreal.MaterialExpressionAdd, g.scalar('Brightness'), g.op(unreal.MaterialExpressionMultiply, flake, g.scalar('LineGlow'), 'R')))
    sparkle_glow = g.op(unreal.MaterialExpressionMultiply, g.colour('WhiteColour'), g.op(unreal.MaterialExpressionAdd,
        g.op(unreal.MaterialExpressionMultiply, glint, g.scalar('GlintGlow')), g.op(unreal.MaterialExpressionMultiply, band, g.scalar('WaveGlow'))))
    glow = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionAdd, base_glow, sparkle_glow), swell)
    lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)

# S 눈 마법진 장판 값(M_Aurora_SnowFloor · 거친 시안 M_Aurora_SnowFloorRough가 같이 쓴다, 까닭은 build_frost_floors 설명)
SNOW_FLOOR_DEFAULTS = {
    'IceColour': (0.45, 0.72, 1.0), 'WhiteColour': (0.88, 0.94, 1.0), 'Brightness': 0.7, 'LineOpacity': 0.35,
    'LineGlow': 1.6, 'HaloOpacity': 0.04, 'PatternTiling': 3.0, 'PatternFloor': 0.4, 'FillOpacity': 0.0, 'FillWhite': 0.7,
    # 별빛 3초에 한 번 · 빛 띠 5초에 한 번(10-19 구원의 세레나데 참고, 「아주 느리게」)
    'GlintStrength': 0.25, 'GlintGlow': 3.0, 'TwinklePeriod': 3.0, 'WaveStrength': 0.0, 'WaveGlow': 1.0, 'WavePeriod': 5.0}


def build_frost_floors():
    # S 눈송이 장판: 「너무 진하다」로 원 장판(FillOpacity 0.42)보다 옅게
    # 10-19 「3(닳은 선 + 서리 결정 + 반짝임)에 좀 더 투명하게」: 선·퍼진 빛·안 채움을 약 30% 옅게(0.4·0.16·0.12 → 0.28·0.11·0.08),
    # 이어서 「투명도 더 올려 줘」로 한 번 더 약 30%(→ 0.2·0.08·0.055), 「더 옅게 + 약간 빛나게」로 깔리는 양은 또 약 30%
    # (→ 0.16·0.06·0.035) 줄이고 선의 빛 세기를 올림(밝기 0.4 → 0.7, 선 빛 0.4 → 1.6: 선이 1을 넘겨 은은하게 번진다),
    # 「좀 더 투명하게」로 깔리는 양만 또 약 30%(→ 0.11·0.04·0.025, 빛 세기·별빛·빛 띠는 그대로)
    # 10-20 「지금 재질은 유지하면서 마법진 형태로, 약간 거친 재질로」: 값은 그대로 두고 그림만 눈 마법진(T_Aurora_SnowCircle)으로.
    # 그 전 눈꽃 그림 T_Aurora_Snowflake는 애셋·그림 도구에 남아 있다.
    # 이어서 「왜 이렇게 아쉽지」 분석(aurora-48th-snow: 장판 안 78%가 +20 이상 밝아지는 뿌연 막 위에서 선은 겨우 +50 더 밝음,
    # 눈에 띄는 건 별빛뿐) → 권장대로 막을 걷고 선만 또렷하게: 안 채움 0.025 → 0 · 빛 띠 0.07 → 0 · 별빛 0.7 → 0.25 ·
    # 선 0.11 → 0.35(약 세 배, 그림의 선도 굵힘)
    build_snow_floor('M_Aurora_SnowFloor', import_drawn('T_Aurora_SnowCircle', 'aurora_snowflake_texture.py'), LIGHT_FROST,
                     dict(SNOW_FLOOR_DEFAULTS))
    build_floor('M_Aurora_FrostFloor', LIGHT_FROST, {
        'IceColour': (0.45, 0.72, 1.0), 'WhiteColour': (0.88, 0.94, 1.0), 'Brightness': 0.5, 'EdgeSharp': 14.0,
        'RingAt': 0.94, 'RingSharp': 18.0, 'RingOpacity': 0.6, 'PatternTiling': 3.0, 'PatternFloor': 0.35, 'FillOpacity': 0.42})
    # Q 얼음 균열(시안 2): 팩의 T_IceVeins는 금이 머리카락처럼 가늘어(2048 중 1~3칸) 150cm 자국에선 회색 안개가 됐다
    # (10-18 밤 게임 사진) → 굵은 금을 그린 그림으로 바꿈
    build_snow_floor('M_Aurora_IceCrack', import_drawn('T_Aurora_IceCrack', 'aurora_ice_crack_texture.py'), LIGHT_FROST, {
        'IceColour': (0.45, 0.72, 1.0), 'WhiteColour': (0.9, 0.96, 1.0), 'Brightness': 0.6, 'LineOpacity': 0.65,
        'LineGlow': 0.6, 'HaloOpacity': 0.25, 'PatternTiling': 2.0, 'PatternFloor': 0.5})


def build_snow_cover():
    # Q 눈 덮임(시안 3, 10-19 「거미줄 같다 → 새하얀 눈이 덮인 느낌」): R = 눈 덮인 자리(가운데 거의 불투명), G = 둘레에 흩뿌린 눈가루
    build_snow_floor('M_Aurora_SnowCover', import_drawn('T_Aurora_SnowCover', 'aurora_snow_cover_texture.py'), LIGHT_FROST, {
        'IceColour': (0.62, 0.8, 1.0), 'WhiteColour': (0.96, 0.98, 1.0), 'Brightness': 0.55, 'LineOpacity': 0.85,
        'LineGlow': 0.35, 'HaloOpacity': 0.35, 'PatternTiling': 2.0, 'PatternFloor': 0.6})


def build_sweep(name, texture_path, defaults):
    # Q 시안 1·3(10-19): 부채꼴 바닥 무늬(aurora_slash_textures.py: R = 선, G = 퍼진 빛, B = 부채꼴 왼쪽 0 → 오른쪽 1)를
    # 칼 궤적처럼 한쪽부터 휩쓸어 보이게 한다. C++이 Reveal을 0 → 1.1로 올리고, RevealInvert = 1이면 반대쪽부터.
    defaults = {'Reveal': 1.1, 'RevealInvert': 0.0, 'RevealSharp': 10.0, **defaults}
    material, created = begin(name, True)
    g = Graph(material, defaults)
    tex = g.texture(texture_path, g.node(unreal.MaterialExpressionTextureCoordinate, -2000), 'SweepTexture')
    along = g.op(unreal.MaterialExpressionMultiply, tex, g.constant(1.0), 'B')
    flipped = g.op(unreal.MaterialExpressionSubtract, g.constant(1.0), along)
    order = g.lerp(along, flipped, g.scalar('RevealInvert'))
    shown = g.saturate(g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, g.scalar('Reveal'), order), g.scalar('RevealSharp')))
    lines = g.op(unreal.MaterialExpressionMultiply, tex, g.scalar('LineOpacity'), 'R')
    halo = g.op(unreal.MaterialExpressionMultiply, tex, g.scalar('HaloOpacity'), 'G')
    life = g.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    opacity = g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionMultiply, g.saturate(g.op(unreal.MaterialExpressionAdd, lines, halo)), shown), life)
    tint = g.lerp(g.colour('IceColour'), g.colour('WhiteColour'), tex, 'R')
    glow = g.op(unreal.MaterialExpressionMultiply, tint,
        g.op(unreal.MaterialExpressionAdd, g.scalar('Brightness'), g.op(unreal.MaterialExpressionMultiply, tex, g.scalar('LineGlow'), 'R')))
    lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)


def build_flake_sprite():
    # Q 흩날리는 눈송이(10-19 「뭔가 흩날리는 이펙트」): 엔진 판(Plane)에 붙이는 빛나는 작은 눈송이. 앞뒤 다 보이게, 빛 안 받음.
    defaults = {'Colour_A': (0.85, 0.94, 1.0), 'Brightness': 3.0, 'Opacity': 1.0}
    material, created = begin('M_Aurora_FlakeSprite', False)
    material.set_editor_property('two_sided', True)
    g = Graph(material, defaults)
    sprite = g.texture(import_drawn('T_Aurora_FlakeSprite', 'aurora_slash_textures.py'),
        g.node(unreal.MaterialExpressionTextureCoordinate, -2000), 'SpriteTexture')
    lit = g.op(unreal.MaterialExpressionMultiply, g.colour('Colour_A'), g.scalar('Brightness'))
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, lit, sprite, '', 'R'), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, sprite, g.scalar('Opacity'), 'R'), '',
        unreal.MaterialProperty.MP_OPACITY)
    finish(material, 'M_Aurora_FlakeSprite', created, defaults)


def build_slash_sweeps():
    build_flake_sprite()
    # 10-19 오후 「테두리 더 얇게」: 그림의 몸통·빛을 얇게 하고 퍼진 빛 불투명 0.45 → 0.35
    build_sweep('M_Aurora_SlashArc', import_drawn('T_Aurora_SlashArc', 'aurora_slash_textures.py'), {
        'IceColour': (0.55, 0.8, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 0.8, 'LineOpacity': 0.9, 'LineGlow': 1.2,
        'HaloOpacity': 0.35})
    build_sweep('M_Aurora_FrostSweep', import_drawn('T_Aurora_FrostSweep', 'aurora_slash_textures.py'), {
        'IceColour': (0.6, 0.82, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 0.6, 'LineOpacity': 0.7, 'LineGlow': 0.6,
        'HaloOpacity': 0.3})
    # W(10-19 「이펙트에 맞춰 땅에 흰색 이펙트」): 돌진 길을 따라 출발점부터 드러나는 흰 검기 자국
    build_sweep('M_Aurora_DashStreak', import_drawn('T_Aurora_DashStreak', 'aurora_slash_textures.py'), {
        'IceColour': (0.78, 0.9, 1.0), 'WhiteColour': (0.97, 0.99, 1.0), 'Brightness': 0.8, 'LineOpacity': 0.85, 'LineGlow': 1.0,
        'HaloOpacity': 0.4})
    # E 시안 1·2(10-19 「휘두르는 이펙트 자체가 아쉽다」): 몸을 한 바퀴 도는 원형 검기 · 감겨 나가는 서리 소용돌이
    build_sweep('M_Aurora_SpinRing', import_drawn('T_Aurora_SpinRing', 'aurora_slash_textures.py'), {
        'IceColour': (0.55, 0.8, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 0.8, 'LineOpacity': 0.9, 'LineGlow': 1.2,
        'HaloOpacity': 0.45})
    build_sweep('M_Aurora_SpinFrost', import_drawn('T_Aurora_SpinFrost', 'aurora_slash_textures.py'), {
        'IceColour': (0.6, 0.82, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 0.7, 'LineOpacity': 0.8, 'LineGlow': 0.8,
        'HaloOpacity': 0.35})
    build_warrior_floors()


def build_warrior_floors():
    # 여전사풍 시안(10-19 저녁 「너무 공주 같다」): 빛나는 무늬 대신 바닥이 패인 자국 — 퍼진 자리(G)는 짙은 남색으로 바닥을 어둡게,
    # 금 속·부서진 가장자리(R)만 하얗게 빛난다. Q 칼이 벤 자국 · S 갈라지는 얼음 균열
    build_sweep('M_Aurora_SlashScar', import_drawn('T_Aurora_SlashScar', 'aurora_slash_textures.py'), {
        'IceColour': (0.03, 0.06, 0.12), 'WhiteColour': (0.92, 0.97, 1.0), 'Brightness': 0.15, 'LineOpacity': 0.9, 'LineGlow': 1.4,
        'HaloOpacity': 0.6})
    build_sweep('M_Aurora_HasteCrack', import_drawn('T_Aurora_HasteCrack', 'aurora_slash_textures.py'), {
        'IceColour': (0.05, 0.12, 0.22), 'WhiteColour': (0.78, 0.93, 1.0), 'Brightness': 0.2, 'LineOpacity': 0.85, 'LineGlow': 1.3,
        'HaloOpacity': 0.45})
    # S 시안 5(「눈 모양 유지하면서 거친 느낌」): 눈송이 짜임을 균열 선으로. 값은 균열 장판과 같게.
    build_sweep('M_Aurora_HasteFlakeCrack', import_drawn('T_Aurora_HasteFlakeCrack', 'aurora_slash_textures.py'), {
        'IceColour': (0.05, 0.12, 0.22), 'WhiteColour': (0.78, 0.93, 1.0), 'Brightness': 0.2, 'LineOpacity': 0.85, 'LineGlow': 1.3,
        'HaloOpacity': 0.45})
    build_crack_drafts()


def build_crack_drafts():
    # 10-19 밤 시안(「S는 롤백하고 기존 원에 깨진 듯한 이펙트 · D·F 방향은 괜찮은데 이펙트가 아쉽다」):
    # S 6 = 눈송이 장판(시안 3)과 같은 밝은 얼음빛으로 은은하게 빛나는 금(장판 선 불투명 0.11보다 진하게, 퍼진 빛은 옅게 — 바닥을 어둡게
    # 하지 않는다) · S 7 = 균열 장판(시안 4)처럼 파인 자리가 어두운 굵은 금 · D 갈라진 자국 = Q 벤 자국과 같은 값 · F 꽂힌 자리 = 균열 장판 값
    build_sweep('M_Aurora_RimCrack', import_drawn('T_Aurora_RimCrack', 'aurora_slash_textures.py'), {
        'IceColour': (0.45, 0.72, 1.0), 'WhiteColour': (0.9, 0.96, 1.0), 'Brightness': 0.7, 'LineOpacity': 0.45, 'LineGlow': 1.8,
        'HaloOpacity': 0.08})
    build_sweep('M_Aurora_RimShatter', import_drawn('T_Aurora_RimShatter', 'aurora_slash_textures.py'), {
        'IceColour': (0.05, 0.12, 0.22), 'WhiteColour': (0.78, 0.93, 1.0), 'Brightness': 0.2, 'LineOpacity': 0.85, 'LineGlow': 1.3,
        'HaloOpacity': 0.4})
    build_sweep('M_Aurora_RuptureCrack', import_drawn('T_Aurora_RuptureCrack', 'aurora_slash_textures.py'), {
        'IceColour': (0.03, 0.06, 0.12), 'WhiteColour': (0.92, 0.97, 1.0), 'Brightness': 0.15, 'LineOpacity': 0.9, 'LineGlow': 1.4,
        'HaloOpacity': 0.6})
    build_sweep('M_Aurora_ImpactCrack', import_drawn('T_Aurora_ImpactCrack', 'aurora_slash_textures.py'), {
        'IceColour': (0.05, 0.12, 0.22), 'WhiteColour': (0.78, 0.93, 1.0), 'Brightness': 0.2, 'LineOpacity': 0.85, 'LineGlow': 1.3,
        'HaloOpacity': 0.5})


def component(g, source, channel):
    # 좌표처럼 이름 붙은 출력이 없는 노드에서 한 성분만 뽑는다
    n = g.node(unreal.MaterialExpressionComponentMask)
    for name in ('r', 'g', 'b', 'a'):
        n.set_editor_property(name, name == channel)
    _checked_connect(source, '', n, '')
    return n


def build_blade(name, texture_path, defaults, layered=False, flip=None, skin=False):
    # Q1 날아가는 검기 · Q2 공중 X자 칼자국(10-19 밤 큰 틀 「Q1 Q2 둘 다」): 엔진 판(Plane, u = +X · v = +Y, 그림 위쪽 = 판의 -Y)에
    # 붙이는 빛나는 그림. 바닥 무늬(build_sweep)와 같은 그림(R 선 · G 퍼진 빛 · B 드러나는 차례)을 쓰고, 데칼 수명 대신 C++이
    # Fade(1 → 0)를 내린다. 바닥에 깔리지 않고 공중에 뜨므로 앞뒤 다 보이게, 빛 안 받음.
    # layered(10-21 Q 시안 「퀄리티가 아쉽다 — 뭐가 문제지」 → 시안, C++ Aurora.FX.QLook): WhitePower = 흰빛·빛 세기를 R의 그만큼 거듭제곱으로
    # (1이면 그 전과 같다 — 크면 날만 희고 몸통은 얼음빛) · Erode = 서리 무늬(T_Aurora_Hoarfrost_2_M) 낮은 자리부터 갉혀 사라짐
    # (0이면 그 전과 같다, 1이면 다 갉힘 — 보임 = saturate((무늬 × 0.8 + R × 0.2 − 1.25 × Erode) × ErodeSharp + 1))
    # flip = (가로 장 수, 세로 장 수)(10-21 Q 시안 QFeel 4): 여러 장을 담은 그림에서 C++이 정한 장 자리(FrameU·FrameV, 0~1)의 한 장만 쓴다
    # skin(10-21 「누운 초승달 형태가 좋은데 이펙트 시안을 더」, C++ Aurora.FX.QSkin 2·4 — 둘 다 0이면 그 전과 같다):
    # AuroraMix = 얼음빛 대신 날 끝에서 끝까지(그림 가로 u) 청록 AuroraA → 파랑 AuroraB → 보라 AuroraC로 물든 빛(두 번 섞은 곡선) ·
    # FlowStrength = 몸통 불투명·밝기를 얼음 잡음(T_Noise_Ice, FlowTiling배, 그림 아래쪽 = 나는 반대쪽으로 초당 3칸 흐름)으로 1 ± 그만큼 흔듦
    defaults = {'Reveal': 1.1, 'RevealSharp': 10.0, 'Fade': 1.0, **defaults}
    if layered:
        defaults = {'WhitePower': 1.0, 'Erode': 0.0, 'ErodeTiling': 1.5, 'ErodeSharp': 6.0, **defaults}
    if flip:
        defaults = {'FrameU': 0.0, 'FrameV': 0.0, **defaults}
    if skin:
        defaults = {'AuroraMix': 0.0, 'AuroraA': (0.1, 0.95, 0.75), 'AuroraB': (0.15, 0.5, 1.0), 'AuroraC': (0.7, 0.35, 1.0),
                    'FlowStrength': 0.0, 'FlowTiling': 2.0, **defaults}
    material, created = begin(name, False)
    material.set_editor_property('two_sided', True)
    g = Graph(material, defaults)
    coords = g.node(unreal.MaterialExpressionTextureCoordinate, -2000)
    if flip:
        cell = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
        cell.set_editor_property('r', 1.0 / flip[0])
        cell.set_editor_property('g', 1.0 / flip[1])
        offset = g.node(unreal.MaterialExpressionAppendVector)
        _checked_connect(g.scalar('FrameU'), '', offset, 'A')
        _checked_connect(g.scalar('FrameV'), '', offset, 'B')
        coords = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, coords, cell), offset)
    tex = g.texture(texture_path, coords, 'BladeTexture')
    order = g.op(unreal.MaterialExpressionMultiply, tex, g.constant(1.0), 'B')
    shown = g.saturate(g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, g.scalar('Reveal'), order), g.scalar('RevealSharp')))
    lines = g.op(unreal.MaterialExpressionMultiply, tex, g.scalar('LineOpacity'), 'R')
    halo = g.op(unreal.MaterialExpressionMultiply, tex, g.scalar('HaloOpacity'), 'G')
    if layered:
        frost = g.texture(FROST, g.uv('ErodeTiling'), 'ErodeTexture')
        value = g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, frost, g.constant(0.8), 'R'),
            g.op(unreal.MaterialExpressionMultiply, tex, g.constant(0.2), 'R'))
        kept = g.saturate(g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply,
            g.op(unreal.MaterialExpressionSubtract, value, g.op(unreal.MaterialExpressionMultiply, g.scalar('Erode'), g.constant(1.25))),
            g.scalar('ErodeSharp')), g.constant(1.0)))
        shown = g.op(unreal.MaterialExpressionMultiply, shown, kept)
        power = g.node(unreal.MaterialExpressionPower)
        _checked_connect(g.op(unreal.MaterialExpressionMultiply, tex, g.constant(1.0), 'R'), '', power, 'Base')
        # 지수 핀 이름은 「Exponent」로 안 붙었다(첫 판 failed_links) — 화면에 보이는 이름 「Exp」부터 해 본다
        exponent = g.scalar('WhitePower')
        if not lib.connect_material_expressions(exponent, '', power, 'Exp'):
            _checked_connect(exponent, '', power, 'Exponent')
        white = power
    else:
        white = g.op(unreal.MaterialExpressionMultiply, tex, g.constant(1.0), 'R')
    opacity = g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionMultiply, g.saturate(g.op(unreal.MaterialExpressionAdd, lines, halo)), shown), g.scalar('Fade'))
    ice = g.colour('IceColour')
    whitish = g.colour('WhiteColour')
    flow = None
    if skin:
        u = component(g, coords, 'r')
        gradient = g.lerp(g.lerp(g.colour('AuroraA'), g.colour('AuroraB'), u), g.lerp(g.colour('AuroraB'), g.colour('AuroraC'), u), u)
        ice = g.lerp(ice, gradient, g.scalar('AuroraMix'))
        # 큰 검기는 몸통 대부분이 흰빛 쪽이라 얼음빛만 물들이면 끝만 옅게 물들었다(첫 촬영) — 흰빛도 같은 빛깔로(흰 0.45를 섞어 밝게)
        whitish = g.lerp(whitish, g.lerp(gradient, g.constant(1.0), g.constant(0.45)), g.scalar('AuroraMix'))
        # 패너는 좌표에 시간 × 빠르기를 더한다 — 무늬는 그 반대로 움직이므로 그림 아래쪽(+v)으로 흐르게 음수
        noise = g.texture(ICE_NOISE, g.uv('FlowTiling', pan=(0.0, -3.0)), 'FlowTexture')
        centred = g.op(unreal.MaterialExpressionSubtract, g.op(unreal.MaterialExpressionMultiply, noise, g.constant(2.0), 'R'), g.constant(1.0))
        flow = g.op(unreal.MaterialExpressionAdd, g.constant(1.0), g.op(unreal.MaterialExpressionMultiply, centred, g.scalar('FlowStrength')))
        opacity = g.saturate(g.op(unreal.MaterialExpressionMultiply, opacity, flow))
    tint = g.lerp(ice, whitish, white)
    glow = g.op(unreal.MaterialExpressionMultiply, tint,
        g.op(unreal.MaterialExpressionAdd, g.scalar('Brightness'), g.op(unreal.MaterialExpressionMultiply, white, g.scalar('LineGlow'))))
    if flow:
        glow = g.op(unreal.MaterialExpressionMultiply, glow, flow)
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)


def build_blades():
    # 바닥 초승달(SlashArc)보다 밝게 — 바닥이 아니라 공중에서 어두운 바닥을 배경으로 보인다.
    build_blade('M_Aurora_WaveBlade', import_drawn('T_Aurora_SlashArc', 'aurora_slash_textures.py'), {
        'IceColour': (0.55, 0.8, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 1.2, 'LineOpacity': 1.0, 'LineGlow': 2.2,
        'HaloOpacity': 0.45})
    build_blade('M_Aurora_CutMark', import_drawn('T_Aurora_DashStreak', 'aurora_slash_textures.py'), {
        'IceColour': (0.6, 0.85, 1.0), 'WhiteColour': (0.97, 0.99, 1.0), 'Brightness': 1.2, 'LineOpacity': 1.0, 'LineGlow': 2.4,
        'HaloOpacity': 0.5})


def build_glow_ice(name, defaults, skeletal=False, two_sided=False):
    # 스스로 빛나는 얼음(빛 안 받음): 가장자리(프레넬)일수록 흰빛·불투명, 가운데는 푸르고 비친다.
    # skeletal = 캐릭터 메시(분신)에도 쓴다 — 표시가 없으면 게임에서 기본 재질로 그려진다(10-20 밤 R 러프 시안 4, 석상 재질이 그랬다).
    # Aurora 메시는 천(옷자락) 칸도 있어 천 표시도 같이(첫 판은 「missing usage flag Clothing」)
    # two_sided = 얇은 판(F 결정 매 날개)도 아래위 다 보이게
    material, created = begin(name, False)
    material.set_editor_property('two_sided', two_sided)
    if skeletal:
        material.set_editor_property('used_with_skeletal_mesh', True)
        material.set_editor_property('used_with_clothing', True)
    g = Graph(material, defaults)
    fresnel = g.node(unreal.MaterialExpressionFresnel)
    _checked_connect(g.scalar('RimPower'), '', fresnel, 'ExponentIn')
    tint = g.lerp(g.colour('IceColour'), g.colour('WhiteColour'), fresnel)
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, tint, g.scalar('Brightness')), '',
        unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    opacity = g.op(unreal.MaterialExpressionMultiply, g.lerp(g.scalar('BodyOpacity'), g.constant(1.0), fresnel), g.scalar('Fade'))
    lib.connect_material_property(g.saturate(opacity), '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, name, created, defaults)


def build_blade_drafts():
    # Q 검기 시안(10-20 밤 「Q 다 아쉽다, 시안 가자」, C++ Aurora.FX.QBlade): 새 애셋만 만든다(사용자 에디터가 떠 있어도 열린 애셋을 안 덮음).
    # 1 M_Aurora_WaveBladeBright — 몸통이 두꺼운 초승달 그림(T_Aurora_SlashWave)에 몸통까지 빛나는 얼음빛. 지금 검기는 C++이 몸통을
    #   짙은 파랑(0.04, 0.24, 1 × 0.9)으로 칠해 반투명으로 얹혀 바닥에 묻혔고 날 선만 보였다.
    # 2 M_Aurora_GlowIce — 날 위 얼음 원뿔용. 지금은 얼음 분신 석상 재질(빛을 받음)이라 어두운 방에서 회색 빗살로 보였다.
    build_blade('M_Aurora_WaveBladeBright', import_drawn('T_Aurora_SlashWave', 'aurora_slash_textures.py'), {
        'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
        'HaloOpacity': 0.35})
    build_glow_ice('M_Aurora_GlowIce', {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.75, 0.92, 1.0), 'Brightness': 2.0,
                                        'RimPower': 2.0, 'BodyOpacity': 0.45, 'Fade': 1.0})


def build_rough_drafts():
    # 이어서(10-20 밤 「Q 7번이 그나마 — 더 크게·굵게·빠르게·멀리·거칠게 · V 얼음 오브젝트 지우고 다른 이펙트」): 붓질처럼 뜯긴 결 그림
    # 둘(aurora_slash_textures.py slash_rough·nova_ring)에 WaveBladeBright와 같은 얼음빛. 새 애셋만.
    # M_Aurora_WaveBladeRough = Q 큰 검기(C++ QBlade 16) · M_Aurora_NovaRing = V 서리 충격파 고리(VLand 5·7·8, 바닥에 눕힌 판)
    colours = {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
               'HaloOpacity': 0.35}
    build_blade('M_Aurora_WaveBladeRough', import_drawn('T_Aurora_SlashRough', 'aurora_slash_textures.py'), dict(colours))
    build_blade('M_Aurora_NovaRing', import_drawn('T_Aurora_NovaRing', 'aurora_slash_textures.py'), dict(colours))


def build_rougher_drafts():
    # 이어서(「Q 23 기반으로 여러 시안 · V 8 기반으로 여러 시안 · S 거친 느낌이 없다, 너무 정갈하고 이쁨」): 더 거칠게 뜯긴 그림 둘에 같은
    # 얼음빛(새 재질) + S 거친 마법진 그림은 텍스처만 가져온다(C++ Aurora.FX.SRough가 깔린 장판 재질 사본의 FlakeTexture를 바꿈). 새 애셋만.
    colours = {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
               'HaloOpacity': 0.35}
    build_blade('M_Aurora_WaveBladeRougher', import_drawn('T_Aurora_SlashRougher', 'aurora_slash_textures.py'), dict(colours))
    build_blade('M_Aurora_NovaRingRough', import_drawn('T_Aurora_NovaRingRough', 'aurora_slash_textures.py'), dict(colours))
    path = import_drawn('T_Aurora_SnowCircleRough', 'aurora_snowflake_texture.py')
    report.setdefault('textures', {})[path] = 'imported only'


def build_snow_rough_drafts():
    # 이어서(「S 2가 그나마 괜찮긴 한데 — 한계야? 시안 더」): 갉음 값이 더 있는 거친 장판 재질(C++ Aurora.FX.SRough 4·8). 값·그림은 S 장판과 같다.
    # 새 애셋만 — 그림은 이미 가져온 것을 그대로 쓴다(AURORA_REUSE_TEXTURES, 사용자 에디터가 연 텍스처를 다시 가져와 덮지 않게).
    build_snow_floor('M_Aurora_SnowFloorRough', import_drawn('T_Aurora_SnowCircle', 'aurora_snowflake_texture.py'), LIGHT_FROST,
                     dict(SNOW_FLOOR_DEFAULTS), rough=True)


def build_qlook_drafts():
    # Q 큰 검기 퀄리티 시안(10-21 「Q 시안 만들어 줘」, C++ Aurora.FX.QLook 1·2): 지금 큰 검기(M_Aurora_WaveBladeRough)와 같은 그림·값에
    # 층 나누기(WhitePower)·갉혀 사라짐(Erode)을 더한 재질. 기본값이면 지금 큰 검기와 같다. 새 애셋만.
    build_blade('M_Aurora_WaveBladeLayered', import_drawn('T_Aurora_SlashRough', 'aurora_slash_textures.py'), {
        'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
        'HaloOpacity': 0.35}, layered=True)


def build_flip_drafts():
    # Q 시안 QFeel 4(10-21 「지금 Q가 제일 낫다 — 다른 시안」): 지금 큰 검기(M_Aurora_WaveBladeRough)와 같은 값에 그림만 여덟 장 넘김
    # (T_Aurora_SlashFlip 4×2). 새 애셋만.
    build_blade('M_Aurora_WaveBladeFlip', import_drawn('T_Aurora_SlashFlip', 'aurora_slash_textures.py'), {
        'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
        'HaloOpacity': 0.35}, flip=(4, 2))


def build_skin_drafts():
    # Q 이펙트 시안(10-21 「누운 초승달 형태가 좋은데 이펙트 시안을 더」, C++ Aurora.FX.QSkin 2·4): 지금 큰 검기와 같은 그림·값에 오로라 빛깔·
    # 흐르는 결 값을 더한 재질(둘 다 0이면 지금과 같다). 새 애셋만, 그림은 이미 가져온 것을 그대로.
    # 같이 만들었던 공기 일그러짐 판(M_Aurora_WaveHaze — 굴절 2D 밀기, 빛 안 받음·받음)은 세기 0.03~5 모두 바닥이 그대로여서 지웠다.
    rough = import_drawn('T_Aurora_SlashRough', 'aurora_slash_textures.py')
    build_blade('M_Aurora_WaveBladeSkin', rough, {
        'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.7, 0.9, 1.0), 'Brightness': 1.0, 'LineOpacity': 0.9, 'LineGlow': 2.5,
        'HaloOpacity': 0.35}, skin=True)


def build_flake_arm():
    # R 얼음 난무(10-21 「눈 모양 너무 퀄리티 낮아 보인다」): 칼선마다 바닥에 남는 눈꽃 지름 하나(T_Aurora_FlakeArm — 위·아래 팔 + 곁가지).
    # 베며 지나가는 쪽으로 드러난다(B 아래 → 위, C++ SweepFloorDecal). 다 그어지면 C++이 Brightness·LineGlow를 잠깐 올려 번쩍인다. 새 애셋만.
    build_sweep('M_Aurora_FlakeArm', import_drawn('T_Aurora_FlakeArm', 'aurora_snowflake_texture.py'), {
        'IceColour': (0.3, 0.62, 1.0), 'WhiteColour': (0.9, 0.97, 1.0), 'Brightness': 0.9, 'LineOpacity': 0.95, 'LineGlow': 2.2,
        'HaloOpacity': 0.4})


def build_clone_drafts():
    # R 러프 시안 4(얼음 분신 동행)의 분신 몸: 스스로 빛나는 얼음(M_Aurora_GlowIce와 같은 짜임)을 캐릭터 메시에. 새 애셋만.
    build_glow_ice('M_Aurora_CloneIce', {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.75, 0.92, 1.0), 'Brightness': 1.6,
                                         'RimPower': 2.0, 'BodyOpacity': 0.35, 'Fade': 1.0}, skeletal=True)


def import_obj_mesh(name, material):
    # aurora_bird_art.py가 쓴 OBJ(cm, x·-y·z로 적어 엔진 OBJ 가져오기의 손 방향 뒤집힘을 되돌림)를 정적 메시로 — countess_q_outward_assets.py와
    # 같은 설정(장면 변환·단위 변환·앞 축 바꾸기 끔). 삼각형마다 꼭짓점이 따로라 법선은 면마다 평평하다.
    source = Path(unreal.Paths.project_dir()).resolve() / 'SourceArt' / 'Aurora' / 'Meshes' / f'{name}.obj'
    if not source.exists():
        raise RuntimeError('Run aurora_bird_art.py first: ' + str(source))
    folder = f'{FOLDER}/Meshes'
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(source), destination_path=folder, destination_name=name, automated=True,
                           replace_existing=True, save=False, factory=unreal.FbxFactory()).items():
        task.set_editor_property(key, value)
    settings = unreal.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                           import_mesh=True, import_materials=False, import_textures=False).items():
        settings.set_editor_property(key, value)
    data = settings.get_editor_property('static_mesh_import_data')
    for key, value in dict(combine_meshes=True, auto_generate_collision=False, convert_scene=False, convert_scene_unit=False,
                           force_front_x_axis=False, generate_lightmap_u_vs=False).items():
        data.set_editor_property(key, value)
    task.set_editor_property('options', settings)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(f'{folder}/{name}')
    if mesh is None:
        raise RuntimeError(name + ' import failed')
    mesh.set_editor_property('static_materials', [unreal.StaticMaterial(material_interface=material, material_slot_name='Ice')])
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError(name + ' save failed')
    bounds = mesh.get_bounds()
    report.setdefault('meshes', {})[name] = {'origin': [round(bounds.origin.x, 1), round(bounds.origin.y, 1), round(bounds.origin.z, 1)],
                                             'extent': [round(bounds.box_extent.x, 1), round(bounds.box_extent.y, 1), round(bounds.box_extent.z, 1)]}


def build_bird_drafts():
    # F 시안(10-21 「얼음 모양 매나 새 같은 게 날아가는 거 어때? F는」, C++ Aurora.FX.FBird): 새 애셋만.
    # 1 M_Aurora_IceHawk — 위에서 본 빛나는 얼음 매 그림 여덟 장(T_Aurora_IceHawk 4×2, 날갯짓), 큰 검기와 같은 짜임(build_blade flip)
    # 2 SM_Aurora_CrystalHawk_* — 각진 얼음 결정 매(몸·날개 둘·꼬리, 날개는 어깨가 원점) + 양면 빛나는 얼음 M_Aurora_IceHawkCrystal
    build_blade('M_Aurora_IceHawk', import_drawn('T_Aurora_IceHawk', 'aurora_bird_art.py'), {
        'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.8, 0.94, 1.0), 'Brightness': 1.1, 'LineOpacity': 0.95, 'LineGlow': 2.5,
        'HaloOpacity': 0.6}, flip=(4, 2))
    # 첫 판(밝기 2 · 테 1.6)은 하얗게 날아가 면이 안 보였다(흰 비둘기 실루엣) → 어둡게, 테를 좁게
    build_glow_ice('M_Aurora_IceHawkCrystal', {'IceColour': (0.06, 0.35, 1.0), 'WhiteColour': (0.8, 0.95, 1.0), 'Brightness': 0.9,
                                               'RimPower': 3.0, 'BodyOpacity': 0.55, 'Fade': 1.0}, two_sided=True)
    crystal = unreal.load_asset(f'{FOLDER}/M_Aurora_IceHawkCrystal')
    for part in ('Body', 'WingR', 'WingL', 'Tail'):
        import_obj_mesh(f'SM_Aurora_CrystalHawk_{part}', crystal)


def build_flyer_drafts():
    # F 시안 이어서(10-21 「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안」, C++ Aurora.FX.FBird 3~6): aurora_bird_art.py가 그린 가는 선 그림 넷에
    # 그림 매와 같은 짜임·빛깔(안은 그림의 G가 낮아 거의 비친다). 새 애셋만.
    # 3 M_Aurora_IceHawkThin(4×2 날갯짓) · 6 M_Aurora_IcePhoenix(4×2 날갯짓·꼬리 깃 물결) · 4 M_Aurora_IceDragon(2×2 머리·마디·다리 마디·꼬리) ·
    # 5 M_Aurora_FrostStar(한 장, C++이 돌린다)
    colours = {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.8, 0.94, 1.0), 'Brightness': 1.1, 'LineOpacity': 1.0, 'LineGlow': 2.5,
               'HaloOpacity': 0.5}
    for name, flip in (('IceHawkThin', (4, 2)), ('IcePhoenix', (4, 2)), ('IceDragon', (2, 2)), ('FrostStar', None)):
        build_blade(f'M_Aurora_{name}', import_drawn(f'T_Aurora_{name}', 'aurora_bird_art.py'), dict(colours), flip=flip)


def build_hawk_drafts():
    # F 매 모양 시안(10-25 「F도 매 모양 좀...」, C++ Aurora.FX.FBird 7·8): aurora_bird_art.py bold가 그린 꽉 찬 매 · 날씬한 매(4×2 날갯짓)를
    # 얇은 매와 같은 짜임·빛깔로. 새 애셋만.
    colours = {'IceColour': (0.1, 0.45, 1.0), 'WhiteColour': (0.8, 0.94, 1.0), 'Brightness': 1.1, 'LineOpacity': 1.0, 'LineGlow': 2.5,
               'HaloOpacity': 0.5}
    for name in ('IceHawkBold', 'IceHawkSlim'):
        build_blade(f'M_Aurora_{name}', import_drawn(f'T_Aurora_{name}', 'aurora_bird_art.py'), dict(colours), flip=(4, 2))


def build_shell_drafts():
    # A 보호막 무늬 시안(10-21 「육각형 대신에 어떤 무늬? 아님 아무것도 그리지 말까? 시안 여러 개」, C++ Aurora.FX.APattern 2~5):
    # aurora_shell_patterns.py가 같은 구 UV·같은 채널로 그린 무늬를 게임 보호막(M_Aurora_IceArmor)과 같은 재질·같은 옅기로. 새 애셋만.
    for name in ('Crack', 'Fern', 'Flake', 'Shard'):
        build_honey(f'M_Aurora_IceArmor_{name}', import_drawn(f'T_Aurora_Shell_{name}', 'aurora_shell_patterns.py'), two_sided=True,
                    overrides={'PlateOpacity': 0.025, 'BorderOpacity': 0.045, 'GhostOpacity': 0.003})


def build_snow_ring():
    # S 가운데 눈꽃 없음(10-25 「내부 큰 눈 문양을 없애는 방식은 어때」, C++ Aurora.FX.SInner 0): 그림만 가져온다 — C++이 깔린 장판 재질
    # 사본의 FlakeTexture를 바꾼다(SRough 1과 같은 방식). 새 애셋만.
    path = import_drawn('T_Aurora_SnowCircleRing', 'aurora_snowflake_texture.py')
    report.setdefault('textures', {})[path] = 'imported only'


def build_honey_drafts():
    for size in ('Small', 'Medium', 'Large'):
        build_honey(f'M_Aurora_IceHoney_{size}', import_drawn(f'T_Aurora_Honey_{size}', 'aurora_honeycomb_texture.py'))


def build_armor_honey():
    # 게임의 A 보호막(10-19 시안 3 「큰 칸 느낌, 육각형은 더 적게」 → 다음 판에 「더 적게」): 큰 칸(정이십면체 5분할, 252칸) 벌집에서
    # 덮는 칸 84 → 31 → 18. 그림 = `aurora_honeycomb_texture.py Armor 5 0.07 1.0`(덮인 칸의 89%가 카메라가 내려다보는 윗반구 —
    # 기울이지 않고 1/5로만 줄였을 땐 남은 칸이 가장자리에 몰려 앞이 비었고, 1/5에 기울이면 보이는 수가 시안 3과 같아졌다). 그 전(10-18 밤)엔 팩의 육각 무늬(T_Trap_HexMask_Packed)를 UV로 깔고
    # 잡음으로 칸을 드문드문 골랐는데, 칸이 서로 떨어져 「벌집처럼 붙은」 느낌이 안 났다. 그때 정한 것 중 몸통 비우기(우윳빛 0)·
    # 파란 얼음빛(0.40, 0.70, 1.0)·끊긴 가장자리는 build_honey가 그대로 잇는다.
    # 10-19 오후 「오브젝트 뒤쪽으로 저 육각형 · 약간만 더 드문드문 추가」: 양면으로 그리고 덮는 칸 18 → 23(`Armor 5 0.09 1.0` — 같은 잡음의
    # 문턱만 낮춰 있던 18칸은 그대로 두고 다섯 칸을 더함). 게임 카메라(pitch -50 · yaw 45) 기준 앞면 15 → 17칸, 안 보이던 뒷면 3 → 6칸
    # (그림 도구가 「camera front … back …」으로 찍는다). 번호 그림으로 물어 「3·4쪽에 좀 더 추가, 정중앙은 좀 지워」 → 화면 가운데
    # (반경 0.45 안) 3칸 비움 + 왼쪽 앞면 4칸 + 오른쪽 아래 뒷면 4칸 = 28칸(앞 18 · 뒤 10): `Armor 5 0.09 1.0 --clear-centre 0.45
    # --grow=-0.6,0.15,front,4 --grow=0.55,-0.45,back,4`.
    # 10-19 저녁 「저 육각형의 투명도를 많이 올려 줘」: 칸(판·테두리·옅은 테두리)의 불투명만 약 40%로(0.3·0.55·0.04 → 0.12·0.22·0.016).
    # 가장자리 빛(Rim)은 그대로. 밤 「A는 더 옅게, 더 많이 옅게」: 칸만 그 1/3로(원래의 약 13% → 0.04·0.075·0.005), 가장자리 빛은 그대로.
    # 이어서 「A 더 낮춰 · 옆쪽 육각형이 뒤쪽으로 이어져 있으면(더 추가)」: 칸 불투명 약 60% 더(원래의 약 8% → 0.025·0.045·0.003) +
    # 그림에 `--extend=0.6,0.6,5 --extend=-0.8,0.5,5`(오른쪽 위·왼쪽 위 덩어리에서 구 표면을 따라 뒷면으로 5칸씩, 28 → 38칸).
    # 10-20 「보호막 좋은데, 뒤꿈치부터 엉덩이 쪽에도 육각형」: 화면에서 몸 아래(발 ~ 엉덩이 자리)에 보이는 앞면 8칸을 더함
    # `--grow=0,-0.72,front,8`(extend 앞에 — 기존 38칸·extend 결과 그대로, 더한 칸은 화면 y −0.50 ~ −0.85 · 가운데 비움 0.45 밖) → 46칸(앞 28 · 뒤 18).
    build_honey('M_Aurora_IceArmor', import_drawn('T_Aurora_Honey_Armor', 'aurora_honeycomb_texture.py'), two_sided=True,
                overrides={'PlateOpacity': 0.025, 'BorderOpacity': 0.045, 'GhostOpacity': 0.003})


# AURORA_MATERIALS = 만들 묶음(쉼표). 기본은 게임에 쓰는 것 전부. 시안(honey)은 이름을 줄 때만.
# 사용자 에디터가 떠 있을 때는 이미 열린 애셋을 덮어쓰지 않도록 새 애셋 묶음만 골라 돌린다.
def build_spear_drafts():
    # D 창 시안(10-25 「D는 저 꽂히는 얼음 오브젝트가 너무 별로인 것 같은데 다른 거 없어?」, C++ Aurora.FX.DSpear): aurora_spear_art.py가 쓴
    # 각진 얼음 결정 창 · 곁가지 달린 다발 + 몸까지 푸른 빛나는 얼음 M_Aurora_SpearIce. 지금 창(엔진 원뿔에 M_Aurora_CloneIce)은 너무 가늘어
    # 테두리 흰빛만 남아 하얀 막대로 보였다 → 몸을 더 진하고 덜 비치게, 흰 테를 좁게. 새 애셋만.
    build_glow_ice('M_Aurora_SpearIce', {'IceColour': (0.05, 0.32, 1.0), 'WhiteColour': (0.8, 0.95, 1.0), 'Brightness': 1.0,
                                         'RimPower': 3.5, 'BodyOpacity': 0.7, 'Fade': 1.0})
    ice = unreal.load_asset(f'{FOLDER}/M_Aurora_SpearIce')
    for name in ('SM_Aurora_IceSpear', 'SM_Aurora_IceSpearCluster'):
        import_obj_mesh(name, ice)


def build_hawk3d():
    # F 입체 매(10-26 「3D 매를 니가 만들 수 있겠어? — 디테일은 필요 없고 매라고 느끼기만 하면 돼」, C++ Aurora.FX.FBird 9): aurora_bird_art.py
    # hawk3d가 쓴 몸 + 날개 안쪽·바깥쪽 넷. D 창과 같은 진한 푸른 빛 얼음을 양면으로(얇은 날개가 아래위 다 보이게). 새 애셋만.
    # 첫 판(테 3.5 · 밝기 1)은 위에서 보면 면이 거의 다 카메라를 봐 단색 하늘색 실루엣이었다 → 테를 넓혀 면마다 밝기가 갈리게
    build_glow_ice('M_Aurora_Hawk3DIce', {'IceColour': (0.05, 0.32, 1.0), 'WhiteColour': (0.8, 0.95, 1.0), 'Brightness': 1.2,
                                          'RimPower': 1.5, 'BodyOpacity': 0.6, 'Fade': 1.0}, two_sided=True)
    ice = unreal.load_asset(f'{FOLDER}/M_Aurora_Hawk3DIce')
    for part in ('Body', 'InnerR', 'InnerL', 'OuterR', 'OuterL'):
        import_obj_mesh(f'SM_Aurora_Hawk3D_{part}', ice)


def build_frost_burst():
    # D 꽂힌 자리 서리 자국(10-26 「저 얼음 오브젝트 말고 다르게 표현할 방법은 없나」, C++ Aurora.FX.DMark 1): 솟는 결정(물체) 대신 바닥이
    # 가운데부터 얼어붙어 퍼진다. 서리 무늬(T_Aurora_Hoarfrost_2_M)를 깔고, 가장자리는 얼음 잡음으로 들쭉날쭉, 가운데는 흰빛.
    # C++(SweepFloorDecal)이 Reveal을 0 → 1.1로 올려 가운데에서 바깥으로 번진다. 새 애셋만.
    # 첫 판(채움 0.7 · 무늬 바닥 0.25 · 반경 120)은 하얀 솜뭉치처럼 진하고 이웃 자국과 뭉쳐 한 덩어리가 됐다 → 옅게, 서리 무늬가 드러나게
    defaults = {'IceColour': (0.45, 0.75, 1.0), 'WhiteColour': (0.92, 0.97, 1.0), 'Brightness': 0.8, 'FillOpacity': 0.4,
                'PatternFloor': 0.05, 'FrostTiling': 1.2, 'EdgeTiling': 1.5, 'EdgeJag': 0.35, 'EdgeSharp': 5.0,
                'CoreAt': 0.2, 'CoreSharp': 5.0, 'CoreOpacity': 0.35, 'CoreGlow': 1.5, 'Reveal': 1.1, 'RevealInvert': 0.0, 'RevealSharp': 6.0,
                'PatchTiling': 0.6, 'PatchLow': 0.3, 'PatchHigh': 1.3}
    material, created = begin('M_Aurora_FrostBurst', True)
    g = Graph(material, defaults)
    coords = g.node(unreal.MaterialExpressionTextureCoordinate, -2000)
    middle = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
    middle.set_editor_property('r', 0.5)
    middle.set_editor_property('g', 0.5)
    d = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionDistance, coords, middle), g.constant(2.0))
    jag = g.texture(ICE_NOISE, g.uv('EdgeTiling'), 'EdgeTexture')
    ragged = g.op(unreal.MaterialExpressionAdd, d, g.op(unreal.MaterialExpressionMultiply,
        g.op(unreal.MaterialExpressionSubtract, jag, g.constant(0.5), 'R'), g.scalar('EdgeJag')))
    inside = g.saturate(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.constant(1.0), ragged),
        g.scalar('EdgeSharp')))
    core = g.saturate(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.scalar('CoreAt'), d),
        g.scalar('CoreSharp')))
    shown = g.saturate(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, g.scalar('Reveal'), ragged),
        g.scalar('RevealSharp')))
    # 서리 무늬 한 장을 넓게(원 전체 300) 깔면 별무늬가 바둑판처럼 규칙적으로 되풀이됐다(77차 촬영) → 칸 비율이 어긋난 둘째 장(0.61배 ·
    # 밀림)과 겹쳐 가장 밝은 쪽을 쓰고, 큰 얼음 잡음(PatchTiling)으로 짙은 곳·옅은 곳을 군데군데 만든다
    frost_a = g.texture(FROST, g.uv('FrostTiling'), 'FrostTexture')
    shift = g.node(unreal.MaterialExpressionConstant2Vector, -2000)
    shift.set_editor_property('r', 0.37)
    shift.set_editor_property('g', 0.11)
    frost_b = g.texture(FROST, g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, g.uv('FrostTiling'),
        g.constant(0.61)), shift), 'FrostTextureB')
    patch = g.texture(ICE_NOISE, g.uv('PatchTiling'), 'PatchTexture')
    both = g.op(unreal.MaterialExpressionMax, frost_a, frost_b, 'R', 'R')
    frost = g.saturate(g.op(unreal.MaterialExpressionMultiply, both, g.lerp(g.scalar('PatchLow'), g.scalar('PatchHigh'), patch, 'R')))
    weight = g.lerp(g.scalar('PatternFloor'), g.constant(1.0), frost)
    fill = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, inside, weight), g.scalar('FillOpacity'))
    glare = g.op(unreal.MaterialExpressionMultiply, core, g.scalar('CoreOpacity'))
    life = g.node(unreal.MaterialExpressionDecalLifetimeOpacity)
    opacity = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply,
        g.saturate(g.op(unreal.MaterialExpressionAdd, fill, glare)), shown), life)
    tint = g.lerp(g.colour('IceColour'), g.colour('WhiteColour'), g.saturate(g.op(unreal.MaterialExpressionAdd, frost, core)))
    glow = g.op(unreal.MaterialExpressionMultiply, tint,
        g.op(unreal.MaterialExpressionAdd, g.scalar('Brightness'), g.op(unreal.MaterialExpressionMultiply, core, g.scalar('CoreGlow'))))
    lib.connect_material_property(tint, '', unreal.MaterialProperty.MP_BASE_COLOR)
    lib.connect_material_property(glow, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, '', unreal.MaterialProperty.MP_OPACITY)
    finish(material, 'M_Aurora_FrostBurst', created, defaults)


def build_dfresh():
    # D 새 시안(10-26 「내가 준 레퍼런스 참고하지 말고 니가 자유롭게 시안 여러 개 — 근본적인 이펙트 퀄리티나 디자인이 마음에 안 든다」,
    # C++ Aurora.FX.DFresh 1~3): 팩 결정·연기를 섞지 않고 aurora_dfx_textures.py가 그린 빛 그림만으로 짓는다. 엔진 판에 붙이는 더하기
    # (빛이 쌓이는) 재질 하나 — C++이 사본마다 그림(Shape)을 바꿔 끼운다: R = 얼음 파랑 퍼진 빛 · G = 흰 심. Fade = 진하기.
    # 시안 3의 결계 원은 S 고리 금과 같은 휩쓸어 그리는 데칼(B = 위에서 시계 방향 차례). 새 애셋만.
    shapes = [import_drawn(name, 'aurora_dfx_textures.py') for name in
              ('T_Aurora_FxStar', 'T_Aurora_FxStreak', 'T_Aurora_FxRing', 'T_Aurora_FxShard')]
    defaults = {'Colour': (0.2, 0.55, 1.0), 'CoreColour': (0.8, 0.93, 1.0), 'Brightness': 2.5, 'CoreBrightness': 5.0, 'Fade': 1.0}
    material, created = begin('M_Aurora_FxAdd', False)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('two_sided', True)
    g = Graph(material, defaults)
    shape = g.texture(shapes[0], g.node(unreal.MaterialExpressionTextureCoordinate, -2000), 'Shape')
    glow = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, g.colour('Colour'), g.scalar('Brightness')),
        shape, '', 'R')
    core = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, g.colour('CoreColour'), g.scalar('CoreBrightness')),
        shape, '', 'G')
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionAdd, glow, core), g.scalar('Fade')), '',
        unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    finish(material, 'M_Aurora_FxAdd', created, defaults)
    build_sweep('M_Aurora_DWard', import_drawn('T_Aurora_DWard', 'aurora_dfx_textures.py'), {
        'IceColour': (0.55, 0.8, 1.0), 'WhiteColour': (0.95, 0.98, 1.0), 'Brightness': 0.8, 'LineOpacity': 0.95, 'LineGlow': 2.0,
        'HaloOpacity': 0.35})


def build_blizzard():
    # V 눈보라(10-26 「누가 봐도 궁극기로 보이게 화려하게 · 맵 전체에 눈보라가 쏟아지는 느낌」, C++ ExecuteBlizzard): 바닥 마법진 그림은
    # M_Aurora_FxAdd에 끼워 쓰고(가져오기만), 화면에 붙인 판 둘 — 흐르는 눈(M_Aurora_FxSnow: 더하기, 좌표 = 판 좌표 × Tiling + 시간 ×
    # (SpeedX, SpeedY) — 겹마다 C++이 값을 달리 넣음) · 화면을 어둡게 하는 판(M_Aurora_FxDim: 반투명, Colour를 Opacity × Fade만큼 덮음). 새 애셋만.
    import_drawn('T_Aurora_BlizzardSeal', 'aurora_dfx_textures.py')
    # 이어서 「얼음송곳 좀 더 날카롭게, 이펙트 좀 다듬어」: 바늘 끝 송곳 · 꽂힌 자리 얼음 튐 — 둘 다 M_Aurora_FxAdd에 끼워 쓴다
    import_drawn('T_Aurora_FxSpike', 'aurora_dfx_textures.py')
    import_drawn('T_Aurora_FxSplash', 'aurora_dfx_textures.py')
    # 이어서 F 얼음 결정 사격의 각진 보석(Sparrow F 원본처럼 꽃잎으로 모임)
    import_drawn('T_Aurora_FxGem', 'aurora_dfx_textures.py')
    flakes = import_drawn('T_Aurora_FxSnow', 'aurora_dfx_textures.py')
    defaults = {'Colour': (0.45, 0.7, 1.0), 'CoreColour': (0.9, 0.96, 1.0), 'Brightness': 1.2, 'CoreBrightness': 2.0, 'Fade': 1.0,
                'Tiling': 3.0, 'SpeedX': -0.1, 'SpeedY': 0.5}
    material, created = begin('M_Aurora_FxSnow', False)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('two_sided', True)
    g = Graph(material, defaults)
    moving = g.op(unreal.MaterialExpressionMultiply, g.node(unreal.MaterialExpressionTime, -2000),
                  g.op(unreal.MaterialExpressionAppendVector, g.scalar('SpeedX'), g.scalar('SpeedY')))
    shape = g.texture(flakes, g.op(unreal.MaterialExpressionAdd, g.uv('Tiling'), moving), 'Shape')
    glow = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, g.colour('Colour'), g.scalar('Brightness')),
        shape, '', 'R')
    core = g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionMultiply, g.colour('CoreColour'), g.scalar('CoreBrightness')),
        shape, '', 'G')
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionAdd, glow, core), g.scalar('Fade')), '',
        unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    finish(material, 'M_Aurora_FxSnow', created, defaults)
    dim_defaults = {'Colour': (0.01, 0.03, 0.08), 'Opacity': 0.4, 'Fade': 1.0}
    material, created = begin('M_Aurora_FxDim', False)
    g = Graph(material, dim_defaults)
    lib.connect_material_property(g.colour('Colour'), '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(g.op(unreal.MaterialExpressionMultiply, g.scalar('Opacity'), g.scalar('Fade')), '',
        unreal.MaterialProperty.MP_OPACITY)
    finish(material, 'M_Aurora_FxDim', created, dim_defaults)


# 87차 Q 검기 재작업(10-28 「Q의 진짜 문제는 저 검기 자체 — 퀄리티 이펙트 자체가 너무 낮아 보임」): 그림(텍스처) 대신 셰이더 코드로
# 그리는 검기(1번 Q M_CountessQOutwardCut과 같은 Custom 노드 방식). 판의 좌표는 SlashArc 그림과 같다 — 위쪽(v = 0) = 나는 쪽,
# 부채꼴 ±62도, 바깥 날 반경 0.79 근처(aurora_slash_textures.py polar). BladeTick이 넣는 Reveal(왼쪽부터 펼침) · Fade(사라짐)를 받는다.
# Style 1 날 선 검기 = 아주 밝고 가는 날 선 + 청록 번짐 + 결을 따라 흐르는 속도선 + 몸통 안쪽이 결대로 깎이며 사라짐
# Style 2 결정 검기 = 몸통을 얼음 결정 조각(보로노이 칸)으로 쪼개 면마다 밝기·반짝임이 다르고, 사라질 때 조각마다 따로 꺼짐
# 93차 「검기 스킬을 포기할까 — 정말 최종적으로 검기 스타일 여러 개 시안」: 3 에너지 초승달 = 두꺼운 몸통이 날에서 안쪽(뒤)으로 흐르는 결로
# 흩어지고 반짝이가 섞임 · 4 세 줄기 칼바람 = 반경이 다른 가는 날 셋이 차례로 펼쳐지고 날마다 뒤로 끌린 바람 자국 · 5 서리 폭풍 = 날 선 없이
# 소용돌이치는 서리 안개 초승달 + 눈송이 · 6 얼음 덩어리 초승달의 받침 = 가는 날 선과 번짐만(몸통은 C++이 띄우는 입체 얼음 덩어리).
# QF = 값 잡음(N)·겹 잡음(F) 함수 묶음(Custom 노드 안에서 함수를 쓰는 구조체 방식)
QFORGE_SHADER = r'''
struct QF
{
    float H(float2 q) { return frac(sin(dot(q, float2(127.1, 311.7))) * 43758.5453); }
    float N(float2 q)
    {
        float2 i = floor(q);
        float2 f = frac(q);
        float2 u = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(H(i), H(i + float2(1.0, 0.0)), u.x), lerp(H(i + float2(0.0, 1.0)), H(i + float2(1.0, 1.0)), u.x), u.y);
    }
    float F(float2 q)
    {
        float s = 0.0;
        float w = 0.5;
        for (int k = 0; k < 4; k++)
        {
            s += w * N(q);
            q = q * 2.03 + float2(1.7, 9.2);
            w *= 0.5;
        }
        return s / 0.9375;
    }
};
QF qf;
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
float a = atan2(p.x, -p.y);
float halfFan = 1.0821;
float inFan = 1.0 - smoothstep(halfFan - 0.06, halfFan, abs(a));
float along = saturate(a / (2.0 * halfFan) + 0.5);
float taper = pow(saturate(cos(clamp(a / halfFan, -1.0, 1.0) * 1.5707963)), 0.55);
float edgeR = 0.79 + 0.025 * cos(a * 3.0);
float thick = 0.24 * taper + 0.003;
float depth = (edgeR - r) / thick;
float d = r - edgeR;
float headPos = Reveal * 1.25 - 0.12;
float revealed = 1.0 - smoothstep(headPos - 0.05, headPos + 0.02, along);
float2 nq = float2(along * 34.0, depth * 5.0);
float2 ni = floor(nq);
float2 nf = frac(nq);
float n00 = frac(sin(dot(ni, float2(127.1, 311.7))) * 43758.5453);
float n10 = frac(sin(dot(ni + float2(1.0, 0.0), float2(127.1, 311.7))) * 43758.5453);
float n01 = frac(sin(dot(ni + float2(0.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float n11 = frac(sin(dot(ni + float2(1.0, 1.0), float2(127.1, 311.7))) * 43758.5453);
float2 nu = nf * nf * (3.0 - 2.0 * nf);
float noise = lerp(lerp(n00, n10, nu.x), lerp(n01, n11, nu.x), nu.y);
float core = exp(-abs(d) / 0.0055) * taper;
float halo = exp(-max(d, 0.0) / 0.035) * step(-0.001, d) * taper;
float3 color = 0;
float alpha = 0;
if (Style < 1.5)
{
    float inside = step(0.0, depth);
    float feather = 1.0 - smoothstep(0.55 + 0.35 * noise, 1.05, depth);
    float bodyMix = pow(saturate(1.0 - depth), 2.2);
    float lane = floor(saturate(depth) * 9.0);
    float lh = frac(sin(lane * 91.7 + 3.1) * 43758.5453);
    float dash = frac(along * (1.5 + lh * 2.5) + lh - Clock * 2.2);
    float streak = smoothstep(0.0, 0.06, dash) * (1.0 - smoothstep(0.2 + 0.45 * lh, 0.75, dash));
    float laneEdge = abs(frac(saturate(depth) * 9.0) - 0.5) * 2.0;
    streak *= pow(saturate(1.0 - laneEdge), 2.5) * inside * feather;
    // 89차 촬영(aurora-89th-qslash): 하얗고 가늘다 → 몸통·번짐을 더 푸르고 넓게, 날 선은 하늘색 쪽으로
    float3 deep = float3(0.01, 0.05, 0.32);
    float3 bright = float3(0.22, 0.72, 1.8);
    float wideHalo = exp(-max(d, 0.0) / 0.07) * step(-0.001, d) * taper;
    color = lerp(deep, bright, bodyMix) * (1.5 + 3.2 * streak) * inside * feather
          + float3(1.0, 2.0, 3.2) * 9.0 * core
          + float3(0.12, 0.55, 1.7) * 2.8 * halo
          + float3(0.05, 0.3, 1.2) * 1.4 * wideHalo;
    alpha = inside * feather * (0.3 + 0.65 * bodyMix) * (0.6 + 0.4 * noise) + core * 0.95 + halo * 0.4 + wideHalo * 0.2 + streak * 0.3;
    float wear = noise * 0.55 + saturate(depth) * 0.45;
    alpha *= smoothstep(wear - 0.12, wear + 0.04, Fade * 1.1);
}
else if (Style > 2.5 && Style < 3.5)
{
    // 3 에너지 초승달: dp 0 = 날, 1 = 몸통 안쪽 끝. 결(f2)이 시간에 따라 안쪽(뒤)으로 흘러 몸통 끝이 불꽃처럼 흩어진다
    float th = 0.36 * taper + 0.004;
    float dp = (edgeR - r) / th;
    float2 flow = float2(along * 7.0, dp * 2.2 - Clock * 2.6);
    float f1 = qf.F(flow);
    float f2 = qf.F(flow * 1.9 + float2(5.2, 1.3) + f1);
    float body = step(0.0, dp) * (1.0 - smoothstep(0.25 + 0.75 * f2, 0.6 + 0.9 * f2, dp));
    float heat = pow(saturate(1.0 - dp), 1.6);
    float3 tone = lerp(lerp(float3(0.02, 0.1, 0.55), float3(0.25, 1.05, 2.6), saturate(heat * 1.6)), float3(1.6, 2.6, 3.6),
                       saturate(heat * 2.2 - 1.2));
    float wide = exp(-max(d, 0.0) / 0.09) * step(-0.001, d) * taper;
    float2 sq = floor(float2(along * 60.0, dp * 8.0 - Clock * 4.0));
    float spark = step(0.965, qf.H(sq)) * body * (0.5 + 0.5 * sin(Clock * 30.0 + qf.H(sq + 3.1) * 40.0));
    color = tone * body * (1.2 + 1.6 * f2)
          + float3(1.4, 2.4, 3.6) * 10.0 * core
          + float3(0.15, 0.6, 1.8) * 3.0 * halo
          + float3(0.04, 0.25, 1.1) * 1.6 * wide
          + float3(2.0, 3.0, 4.0) * 2.5 * spark;
    alpha = body * (0.35 + 0.6 * heat) + core * 0.95 + halo * 0.45 + wide * 0.22 + spark * 0.5;
    float melt = f2 * 0.6 + saturate(dp) * 0.4;
    alpha *= smoothstep(melt - 0.1, melt + 0.05, Fade * 1.1);
}
else if (Style > 3.5 && Style < 4.5)
{
    // 4 세 줄기 칼바람: 날 k(0 바깥 ~ 2 안쪽)마다 반경·부채 폭·펼침 늦음이 다르고, 가는 날 선 + 번짐 + 안쪽(뒤)으로 끌린 바람 자국
    float3 acc = 0;
    float acc_a = 0;
    for (int k = 0; k < 3; k++)
    {
        float kr = edgeR - 0.085 * k;
        float ka = a / (halfFan * (1.0 - 0.18 * k));
        float kin = 1.0 - smoothstep(0.92, 1.0, abs(ka));
        float kt = pow(saturate(cos(clamp(ka, -1.0, 1.0) * 1.5707963)), 0.7);
        float kAlong = saturate(ka * 0.5 + 0.5);
        float kHead = Reveal * 1.25 - 0.12 - 0.12 * k;
        float kRev = 1.0 - smoothstep(kHead - 0.05, kHead + 0.02, kAlong);
        float kd = r - kr;
        float edgeLine = exp(-abs(kd) / (0.0045 + 0.002 * k)) * kt;
        float glow = exp(-abs(kd) / 0.028) * kt;
        float drag = exp(-max(-kd, 0.0) / 0.06) * step(kd, 0.0) * kt;
        float streak = qf.N(float2(kAlong * 18.0 - Clock * 3.0, k * 7.0));
        float weight = (1.0 - 0.25 * k) * kin * kRev;
        acc += (float3(1.3, 2.3, 3.4) * 8.0 * edgeLine + float3(0.15, 0.65, 2.0) * 2.0 * glow + float3(0.08, 0.4, 1.4) * 1.2 * drag * streak) * weight;
        acc_a += (edgeLine * 0.95 + glow * 0.35 + drag * streak * 0.3) * weight;
    }
    float mist = qf.F(float2(along * 5.0 - Clock * 1.5, depth * 3.0)) * step(0.0, depth) * (1.0 - smoothstep(0.6, 1.0, depth));
    color = acc + float3(0.1, 0.35, 0.9) * 0.8 * mist;
    alpha = acc_a + mist * 0.12;
    float wear = qf.N(float2(along * 20.0, 3.0)) * 0.6 + 0.2;
    alpha *= smoothstep(wear - 0.15, wear + 0.05, Fade * 1.1);
}
else if (Style > 4.5 && Style < 5.5)
{
    // 5 서리 폭풍: 들쭉날쭉한 가장자리(jag) 안을 소용돌이치는 안개(mist, 결을 비튼 겹 잡음)가 채우고 눈송이(flake)가 흩날린다.
    // 93차 첫 촬영(aurora-93rd-final): 하얀 연기 덩어리로 보였다 → 안개를 푸르게·옅게(밝은 쪽 0.75·1.15·1.6 → 0.3·0.7·1.5, 채움 0.25+0.55 → 0.12+0.4)
    float jag = qf.N(float2(along * 26.0, Clock * 2.0)) * 0.05;
    float er = edgeR + jag - 0.02;
    float th = 0.32 * taper + 0.004;
    float dp = (er - r) / th;
    float2 w0 = float2(along * 5.0 + Clock * 0.7, dp * 1.6 - Clock * 1.4);
    float warp = qf.F(w0);
    float mist = qf.F(w0 * 1.7 + warp * 2.0 + float2(3.3, 7.1));
    float band = step(0.0, dp) * (1.0 - smoothstep(0.45 + 0.5 * mist, 0.95 + 0.4 * mist, dp));
    float rim = exp(-abs(dp) / 0.12) * taper * step(-0.3, dp);
    float2 fq = float2(along * 48.0 + Clock * 3.0, dp * 6.0 - Clock * 5.0);
    float flake = step(0.88, qf.H(floor(fq))) * smoothstep(0.22, 0.0, length(frac(fq) - 0.5)) * band;
    float3 tone = lerp(float3(0.03, 0.12, 0.5), float3(0.3, 0.7, 1.5), saturate(mist * 1.3 - 0.1 + (1.0 - dp) * 0.4));
    color = tone * band * 1.6 + float3(0.4, 1.0, 2.2) * 1.6 * rim + float3(2.4, 2.8, 3.2) * 2.0 * flake
          + float3(0.08, 0.35, 1.1) * 1.0 * halo;
    alpha = band * (0.12 + 0.4 * mist) + rim * 0.3 + flake * 0.8 + halo * 0.2;
    alpha *= smoothstep(mist * 0.9 - 0.1, mist * 0.9 + 0.05, Fade * 1.05);
}
else if (Style > 6.5)
{
    // 95차 7 「검기를 아주 얇게」: 머리카락 굵기 날 선(6의 절반 아래) + 바깥으로 아주 좁은 번짐만 — 몸통 없음
    float hair = exp(-abs(d) / 0.0022) * taper;
    float glow = exp(-max(d, 0.0) / 0.018) * step(-0.001, d) * taper;
    color = float3(1.1, 2.0, 3.0) * 8.0 * hair + float3(0.1, 0.5, 1.6) * 1.6 * glow;
    alpha = (hair * 0.95 + glow * 0.25) * Fade;
}
else if (Style > 5.5)
{
    // 6 얼음 덩어리 초승달의 받침: 가는 날 선 + 바깥 번짐 + 안쪽으로 짧은 푸른 빛만
    float wideHalo = exp(-max(d, 0.0) / 0.06) * step(-0.001, d) * taper;
    float inner = exp(-max(-d, 0.0) / 0.05) * step(d, 0.0) * taper;
    color = float3(1.0, 2.0, 3.2) * 7.0 * core + float3(0.12, 0.55, 1.7) * 2.2 * halo + float3(0.05, 0.3, 1.2) * 1.2 * wideHalo
          + float3(0.05, 0.3, 1.2) * 1.0 * inner;
    alpha = (core * 0.9 + halo * 0.35 + wideHalo * 0.18 + inner * 0.25) * Fade;
}
else
{
    // 89차 촬영: 칸이 고른 타일처럼 보여 깨진 유리 같았다 → 결 방향으로 길쭉한 조각(가로 22 · 세로 2.2)에 면 그림자, 테두리는 가늘게
    float2 cq = float2(along * 22.0, saturate(depth) * 2.2);
    float2 ci = floor(cq);
    float2 cf = frac(cq);
    float best = 8.0;
    float second = 8.0;
    float2 bestId = 0;
    float2 bestV = 0;
    for (int j = -1; j <= 1; j++)
    {
        for (int i = -1; i <= 1; i++)
        {
            float2 g = float2(i, j);
            float2 id = ci + g;
            float2 o = frac(sin(float2(dot(id, float2(127.1, 311.7)), dot(id, float2(269.5, 183.3)))) * 43758.5453);
            float2 v = g + o - cf;
            float dd = dot(v, v);
            if (dd < best)
            {
                second = best;
                best = dd;
                bestId = id;
                bestV = v;
            }
            else if (dd < second)
            {
                second = dd;
            }
        }
    }
    float ch = frac(sin(dot(bestId, float2(12.9898, 78.233))) * 43758.5453);
    float facet = 1.0 - smoothstep(0.0, 0.045, sqrt(second) - sqrt(best));
    float band = step(0.0, depth) * (1.0 - smoothstep(0.85 + 0.35 * (ch - 0.5), 0.95 + 0.35 * (ch - 0.5), depth));
    float shade = 0.15 + 0.85 * ch;
    float plane = saturate(0.5 + 0.9 * dot(normalize(bestV + 0.0001), float2(0.6, 0.8)));
    float glint = pow(saturate(sin(Clock * 7.0 + ch * 40.0)), 14.0);
    float lit = pow(saturate(1.0 - depth), 0.8);
    color = lerp(float3(0.01, 0.05, 0.3), float3(0.35, 0.95, 2.0), shade * lit * (0.45 + 0.55 * plane)) * 2.2 * band
          + float3(0.9, 1.7, 2.8) * 1.4 * facet * band * plane
          + float3(2.2, 3.0, 4.0) * 1.8 * glint * band
          + float3(1.0, 2.0, 3.2) * 6.5 * core
          + float3(0.12, 0.55, 1.6) * 1.8 * halo;
    alpha = band * (0.5 + 0.35 * shade) + facet * band * 0.15 + core * 0.9 + halo * 0.3;
    alpha *= smoothstep(ch * 0.85 + 0.05, ch * 0.85 + 0.12, Fade);
}
alpha = saturate(alpha) * inFan * revealed;
return float4(color * inFan * revealed, alpha);
'''


def build_qforge():
    name = 'M_Aurora_QSlashForge'
    material, created = begin(name, False)
    material.set_editor_property('two_sided', True)
    custom = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
    custom.set_editor_property('code', QFORGE_SHADER)
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    custom.set_editor_property('description', 'Aurora Q sword wave drawn in code (87th): 1 sharp blade, 2 ice crystal blade, '
                           '(93rd) 3 energy crescent, 4 three wind blades, 5 frost storm, 6 thin edge under ice chunks')
    names = ('UV', 'Clock', 'Reveal', 'Fade', 'Style')
    inputs = []
    for each in names:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', each)
        inputs.append(entry)
    custom.set_editor_property('inputs', inputs)
    sources = [lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate),
               lib.create_material_expression(material, unreal.MaterialExpressionTime)]
    defaults = {'Reveal': 1.0, 'Fade': 1.0, 'Style': 1.0}
    for parameter, value in defaults.items():
        node = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
        node.set_editor_property('parameter_name', parameter)
        node.set_editor_property('default_value', value)
        sources.append(node)
    for each, source in zip(names, sources):
        _checked_connect(source, '', custom, each)
    for channels, prop in ((dict(r=True, g=True, b=True, a=False), unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                           (dict(r=False, g=False, b=False, a=True), unreal.MaterialProperty.MP_OPACITY)):
        mask = lib.create_material_expression(material, unreal.MaterialExpressionComponentMask)
        for key, value in channels.items():
            mask.set_editor_property(key, value)
        _checked_connect(custom, '', mask, lib.get_material_expression_input_names(mask)[0])
        if not lib.connect_material_property(mask, '', prop):
            report['failed_links'].append(f'{name}: output {prop}')
    finish(material, name, created, defaults)


# 94차 「Q는 그림 톤·게임 톤과 안 맞고 이펙트 퀄리티도 아쉽다 — 검기를 얇게 해야 할까?」: 수식으로 그린 도형 대신 팩의 오로라 칼 궤적
# 재질(평타 M_Aurora_Primary_AnimTrail · 메시 꼬리 M_Aurora_Trail_Mesh — 흐르는 안개·결 텍스처)을 그대로 쓴다. 팩 재질에는 사라짐 값이
# 없어 사본을 떠 불투명도 끝에 Fade(BladeTick이 넣음)를, 빛에 Brightness를 곱하고 양면으로. 리본 메시(aurora_qribbon_art.py)는 U가 호를
# 따라가 팩 텍스처가 칼 궤적처럼 흐른다. 팩 원본은 건드리지 않는다.
QTRAIL_SOURCES = {
    'M_Aurora_QTrailPrimary': '/Game/ParagonAurora/FX/Materials/Aurora/FX/M_Aurora_Primary_AnimTrail',
    'M_Aurora_QTrailMesh': '/Game/ParagonAurora/FX/Materials/Aurora/FX/M_Aurora_Trail_Mesh',
}


def duplicate_with_fade(name, source):
    path = f'{FOLDER}/{name}'
    created = not unreal.EditorAssetLibrary.does_asset_exist(path)
    if not created and not unreal.EditorAssetLibrary.delete_asset(path):
        raise RuntimeError('Could not delete old ' + path)
    material = unreal.EditorAssetLibrary.duplicate_asset(source, path)
    if material is None:
        raise RuntimeError('Could not duplicate ' + source)
    material.set_editor_property('two_sided', True)
    for prop, parameter in ((unreal.MaterialProperty.MP_OPACITY, 'Fade'), (unreal.MaterialProperty.MP_EMISSIVE_COLOR, 'Brightness')):
        old = lib.get_material_property_input_node(material, prop)
        if old is None:
            report['failed_links'].append(f'{name}: nothing feeds {prop}')
            continue
        try:
            pin = lib.get_material_property_input_node_output_name(material, prop)
        except Exception:
            pin = ''
        knob = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1600, 0)
        knob.set_editor_property('parameter_name', parameter)
        knob.set_editor_property('default_value', 1.0)
        multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -200, 0)
        _checked_connect(old, pin, multiply, 'A')
        _checked_connect(knob, '', multiply, 'B')
        if not lib.connect_material_property(multiply, '', prop):
            report['failed_links'].append(f'{name}: output {prop}')
    lib.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Could not save ' + name)
    report['materials'][name] = {'created': created, 'source': source, 'expressions': lib.get_num_material_expressions(material)}
    return material


def build_qtrail():
    made = {name: duplicate_with_fade(name, source) for name, source in QTRAIL_SOURCES.items()}
    import_obj_mesh('SM_Aurora_QRibbonThin', made['M_Aurora_QTrailPrimary'])
    import_obj_mesh('SM_Aurora_QRibbonWide', made['M_Aurora_QTrailMesh'])


def build_qhair():
    # 95차 「검기를 아주 얇게」(C++ QSlash 10): 아주 가는 리본(aurora_qribbon_art.py SM_Aurora_QRibbonHair)만 가져온다 — 재질은 94차 사본
    import_obj_mesh('SM_Aurora_QRibbonHair', unreal.load_asset(f'{FOLDER}/M_Aurora_QTrailMesh'))


def build_r94():
    # 94차 A 「저 보호막도 시안 여러 개」(C++ Aurora.FX.AShell 2): 몸 위에 겹쳐 그리는 얇은 얼음 막 — 가장자리만 빛나고 몸통은 다 비침
    # (프레넬 얼음 build_glow_ice, 캐릭터 메시용). 새 애셋만.
    build_glow_ice('M_Aurora_ArmorSkin', {'IceColour': (0.15, 0.5, 1.0), 'WhiteColour': (0.85, 0.95, 1.0), 'Brightness': 1.4,
                                          'RimPower': 3.0, 'BodyOpacity': 0.0, 'Fade': 1.0}, skeletal=True)


BUILDERS = {'qhair': build_qhair, 'r94': build_r94, 'qtrail': build_qtrail, 'qforge': build_qforge, 'armor': build_armor_honey, 'floors': build_frost_floors, 'snowcover': build_snow_cover, 'sweeps': build_slash_sweeps,
            'honey': build_honey_drafts, 'warrior': build_warrior_floors, 'cracks': build_crack_drafts, 'blades': build_blades,
            'bladedrafts': build_blade_drafts, 'roughdrafts': build_rough_drafts, 'rougherdrafts': build_rougher_drafts,
            'snowroughdrafts': build_snow_rough_drafts, 'clonedrafts': build_clone_drafts, 'qlookdrafts': build_qlook_drafts,
            'flipdrafts': build_flip_drafts, 'flakearm': build_flake_arm, 'skindrafts': build_skin_drafts,
            'birddrafts': build_bird_drafts, 'flyerdrafts': build_flyer_drafts, 'shelldrafts': build_shell_drafts, 'snowring': build_snow_ring,
            'hawkdrafts': build_hawk_drafts, 'speardrafts': build_spear_drafts, 'hawk3d': build_hawk3d,
            'frostburst': build_frost_burst, 'dfresh': build_dfresh, 'blizzard': build_blizzard}
try:
    for key in os.environ.get('AURORA_MATERIALS', 'armor,floors,snowcover,sweeps').split(','):
        BUILDERS[key.strip()]()
    report['passed'] = not report['failed_links']
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'aurora-frost-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
