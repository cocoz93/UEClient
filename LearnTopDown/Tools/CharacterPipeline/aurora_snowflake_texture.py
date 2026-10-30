"""Draw the snowflake mask for Aurora's S frost floor (white flake on black, soft edges) with the bundled Python + Pillow.
Writes SourceArt/Aurora/T_Aurora_Snowflake.png and T_Aurora_Glints.png (slowly twinkling stars over the circle);
aurora_frost_materials_build.py imports them as textures.
R = the lines, G = a wide soft glow around the lines, B = the disc inside the inner ring (faint white fill).
6 main arms with three pairs of side branches and a forked tip, short arms between, a hexagon outline in the middle,
a thin outer ring with a fainter inner ring and small dots between them (2026-10-18 「원보다는 눈 모양」, then
「선을 더 얇게 · 원형 테두리도 얇게 · 디테일 좀 더」).
A procedural flake in the material graph only showed its centre disc, so the shape is drawn here instead.
T_Aurora_SnowCircle.png (2026-10-20 「지금 재질은 유지하면서 마법진 형태로, 약간 거친 재질로」) packs the snow magic circle the
same way: double outer ring with snow crystals and ice diamonds between, a hexagon whose corners touch the inner ring with a
circle inside it, a snow crystal outside each hexagon side, and the old flake enlarged in the middle - then the lines are
shaken, their edges frayed and a few short gaps cut. The first version (hexagram + runes + ringed glyphs) was rejected as
「너무 악마 문양 같아」."""
import math
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 1024
OUT = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora' / 'T_Aurora_Snowflake.png'


class Pen:
    """두 배 크기 그림에 선·고리·점을 긋는다(끝을 둥글게)."""

    def __init__(self, draw, centre):
        self.draw = draw
        self.centre = centre

    def point(self, r, angle, at=None):
        x, y = (self.centre, self.centre) if at is None else at
        return (x + r * math.cos(angle), y + r * math.sin(angle))

    def line(self, a, b, width):
        self.draw.line([a, b], fill=255, width=max(int(width), 1))
        for end in (a, b):
            self.draw.ellipse([end[0] - width / 2, end[1] - width / 2, end[0] + width / 2, end[1] + width / 2], fill=255)

    def ring(self, r, width, at=None):
        x, y = (self.centre, self.centre) if at is None else at
        self.draw.ellipse([x - r, y - r, x + r, y + r], outline=255, width=max(int(width), 1))

    def dot(self, at, r):
        self.draw.ellipse([at[0] - r, at[1] - r, at[0] + r, at[1] + r], fill=255)


def crystal(pen, at, reach, width):
    """작은 눈 결정 문양: 여섯 살 + 살 가운데 작은 가지 한 쌍."""
    for spoke in range(6):
        a = math.pi / 3 * spoke
        pen.line(at, (at[0] + reach * math.cos(a), at[1] + reach * math.sin(a)), width)
        mid = (at[0] + reach * 0.58 * math.cos(a), at[1] + reach * 0.58 * math.sin(a))
        for side in (-1, 1):
            pen.line(mid, (mid[0] + reach * 0.3 * math.cos(a + side * 0.9), mid[1] + reach * 0.3 * math.sin(a + side * 0.9)), width * 0.7)


def flake_arm(pen, radius, angle, arm_width):
    """눈꽃 팔 하나(가운데 = pen.centre, angle 쪽): 곁가지 세 쌍 + 갈래진 끝·마름모. flake와 R 얼음 난무 팔 그림이 같이 쓴다."""
    draw, point, line = pen.draw, pen.point, pen.line
    line(point(radius * 0.1, angle), point(radius, angle), arm_width)
    # 곁가지 세 쌍: 팔을 따라 바깥으로 갈수록 짧고, 가운데 쌍은 끝에서 한 번 더 갈라진다
    for along, length, fork in ((0.34, 0.26, False), (0.56, 0.22, True), (0.76, 0.14, False)):
        base = point(radius * along, angle)
        for side in (-1, 1):
            tip_angle = angle + side * math.pi / 3
            tip = (base[0] + radius * length * math.cos(tip_angle), base[1] + radius * length * math.sin(tip_angle))
            line(base, tip, arm_width * 0.7)
            if fork:
                mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
                twig = (mid[0] + radius * 0.07 * math.cos(angle), mid[1] + radius * 0.07 * math.sin(angle))
                line(mid, twig, arm_width * 0.5)
    # 팔 끝: 작은 갈래 한 쌍 + 마름모
    tip = point(radius, angle)
    for side in (-1, 1):
        fork_angle = angle + side * math.pi / 5
        line(point(radius * 0.9, angle), (point(radius * 0.9, angle)[0] + radius * 0.08 * math.cos(fork_angle),
             point(radius * 0.9, angle)[1] + radius * 0.08 * math.sin(fork_angle)), arm_width * 0.5)
    normal = angle + math.pi / 2
    diamond = [point(radius * 1.03, angle), (tip[0] + radius * 0.025 * math.cos(normal), tip[1] + radius * 0.025 * math.sin(normal)),
               point(radius * 0.97, angle), (tip[0] - radius * 0.025 * math.cos(normal), tip[1] - radius * 0.025 * math.sin(normal))]
    draw.polygon(diamond, fill=255)


def flake(pen, radius, arm_width, glyphs=True):
    """눈꽃(가운데 = pen.centre): 팔 여섯 + 곁가지 세 쌍 + 갈래진 끝·마름모, 사이 짧은 팔, 가운데 육각형·점·점선 고리,
    glyphs면 팔 사이 바깥쪽에 작은 눈 결정 문양 여섯."""
    draw, centre, point, line = pen.draw, pen.centre, pen.point, pen.line
    for arm in range(6):
        angle = math.pi / 3 * arm - math.pi / 2
        flake_arm(pen, radius, angle, arm_width)
        # 사이 짧은 팔: 끝에 작은 곁가지 한 쌍
        between = angle + math.pi / 6
        line(point(radius * 0.14, between), point(radius * 0.4, between), arm_width * 0.6)
        base = point(radius * 0.32, between)
        for side in (-1, 1):
            tip_angle = between + side * math.pi / 3
            line(base, (base[0] + radius * 0.07 * math.cos(tip_angle), base[1] + radius * 0.07 * math.sin(tip_angle)), arm_width * 0.45)
    # 가운데: 육각형 테두리 + 작은 점
    hexagon = [point(radius * 0.13, math.pi / 3 * k - math.pi / 2) for k in range(6)]
    draw.line(hexagon + [hexagon[0]], fill=255, width=int(arm_width * 0.8), joint='curve')
    pen.dot((centre, centre), radius * 0.035)
    # 10-19 「마법진 디테일 약간만 더」: 가운데를 두르는 점선 고리 + 팔 사이 바깥쪽에 작은 눈 결정 문양 여섯
    for k in range(36):
        if k % 2 == 0:
            start = math.pi * 2 * k / 36 - math.pi / 2
            draw.arc([centre - radius * 0.24, centre - radius * 0.24, centre + radius * 0.24, centre + radius * 0.24],
                     math.degrees(start), math.degrees(start + math.pi * 2 / 36), fill=255, width=max(int(arm_width * 0.4), 1))
    if glyphs:
        for arm in range(6):
            glyph = point(radius * 0.8, math.pi / 3 * arm - math.pi / 2 + math.pi / 6)
            for spoke in range(6):
                a = math.pi / 3 * spoke
                end = (glyph[0] + radius * 0.06 * math.cos(a), glyph[1] + radius * 0.06 * math.sin(a))
                line(glyph, end, arm_width * 0.35)
                mid = (glyph[0] + radius * 0.035 * math.cos(a), glyph[1] + radius * 0.035 * math.sin(a))
                for side in (-1, 1):
                    line(mid, (mid[0] + radius * 0.018 * math.cos(a + side * 0.9), mid[1] + radius * 0.018 * math.sin(a + side * 0.9)),
                         arm_width * 0.25)


def pack(image, size, fill_radius):
    """R = 선, G = 선 둘레 퍼진 빛, B = fill_radius 안 원판 — 1024로 줄여 RGB 한 장에 담는다."""
    centre = size / 2
    lines = image.filter(ImageFilter.GaussianBlur(radius=size * 0.0018))
    glow = image.filter(ImageFilter.GaussianBlur(radius=size * 0.012))
    # 퍼진 빛은 얇은 선 주변이라 값이 낮게 나온다 → 최댓값을 1로 늘린다
    peak = max(glow.getextrema()[1], 1)
    glow = glow.point(lambda v: min(255, v * 255 // peak))
    # B = 안쪽 고리 안을 채우는 원판(10-19 「마법진 내부를 약간 흰색 톤으로」) — 재질이 FillOpacity만큼 흰빛으로 깐다
    disc = Image.new('L', (size, size), 0)
    ImageDraw.Draw(disc).ellipse([centre - fill_radius, centre - fill_radius, centre + fill_radius, centre + fill_radius], fill=255)
    disc = disc.filter(ImageFilter.GaussianBlur(radius=size * 0.004))
    return Image.merge('RGB', (lines, glow, disc)).resize((SIZE, SIZE), Image.LANCZOS)


def main():
    scale = 2  # 두 배로 그려 줄여 가장자리를 매끈하게
    size = SIZE * scale
    centre = size / 2
    radius = size * 0.43  # 팔 길이. 바깥 고리(0.49)와 안쪽 고리(0.455) 사이에 점을 둔다
    image = Image.new('L', (size, size), 0)
    pen = Pen(ImageDraw.Draw(image), centre)
    flake(pen, radius, size * 0.012)
    # 바깥 얇은 고리, 그 안쪽 더 가는 고리, 두 고리 사이 작은 점 24개(팔 방향은 큰 점)
    pen.ring(size * 0.49, size * 0.0045)
    pen.ring(size * 0.455, size * 0.0025)
    for k in range(24):
        pen.dot(pen.point(size * 0.4725, math.pi / 12 * k - math.pi / 2), size * (0.005 if k % 4 == 0 else 0.0028))
    packed = pack(image, size, size * 0.455)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    packed.save(OUT)
    print(OUT)


def noise_field(size, cells, seed, octaves=3):
    """0~1 잡음: 거친 격자를 키워 겹친다(옥타브마다 칸 두 배·세기 절반)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for octave in range(octaves):
        cells_now = int(cells * 2 ** octave)
        grid = Image.fromarray((rng.random((cells_now + 1, cells_now + 1)) * 255).astype(np.uint8))
        out += amp * np.asarray(grid.resize((size, size), Image.BICUBIC), dtype=float) / 255.0
        total += amp
        amp *= 0.5
    return out / total


def roughen(image, seed, shake=1.0, fray=0.35, grain_cells=140, gap=0.03, blotch=0.0):
    """깔끔하게 그린 선을 약간 거칠게: 좌표를 흔들고(굵은 굽이 + 잘게 깨짐, shake배), 가장자리를 잡음 문턱으로 갉고(fray, 잡음 칸
    grain_cells), 짧게 군데군데 끊는다(잡음 아래 gap). blotch > 0 = 선 밝기를 굵은 잡음으로 고르지 않게(1 - blotch ~ 1).
    기본값 = 10-20 눈 마법진(T_Aurora_SnowCircle) 그대로."""
    size = image.size[0]
    unit = size / SIZE  # 1024 그림 기준 1px
    a = np.asarray(image, dtype=float) / 255.0
    ys, xs = np.mgrid[0:size, 0:size]
    dx = (noise_field(size, 8, seed) - 0.5) * 2 * 2.5 * shake * unit + (noise_field(size, 90, seed + 1, 2) - 0.5) * 2 * 1.2 * shake * unit
    dy = (noise_field(size, 8, seed + 2) - 0.5) * 2 * 2.5 * shake * unit + (noise_field(size, 90, seed + 3, 2) - 0.5) * 2 * 1.2 * shake * unit
    shaken = a[np.clip(ys + dy, 0, size - 1).astype(int), np.clip(xs + dx, 0, size - 1).astype(int)]
    soft = np.asarray(Image.fromarray((shaken * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9 * unit)), dtype=float) / 255.0
    grain = noise_field(size, grain_cells, seed + 4, 2)
    frayed = np.clip((soft - 0.5 + (grain - 0.5) * fray) / 0.25 + 0.5, 0, 1)
    # 끊김: 잡음의 아래 3% 자리(5%·굵은 잡음은 바깥 고리가 길게 끊기고 룬이 통째로 지워졌다)
    gaps = noise_field(size, 36, seed + 5, 2)
    cut = np.quantile(gaps, gap)
    frayed *= np.clip((gaps - cut) / 0.02, 0, 1)
    if blotch > 0.0:
        frayed *= 1.0 - blotch * noise_field(size, 14, seed + 6, 2)
    return Image.fromarray((frayed * 255).astype(np.uint8))


def diamond(pen, r, angle, length, width):
    """바깥을 향해 길쭉한 얼음 마름모(고리 띠 장식)."""
    o = (math.cos(angle), math.sin(angle))
    s = (-o[1], o[0])
    mid = pen.point(r, angle)
    pen.draw.polygon([(mid[0] + o[0] * length / 2, mid[1] + o[1] * length / 2), (mid[0] + s[0] * width / 2, mid[1] + s[1] * width / 2),
                      (mid[0] - o[0] * length / 2, mid[1] - o[1] * length / 2), (mid[0] - s[0] * width / 2, mid[1] - s[1] * width / 2)], fill=255)


def circle(name='T_Aurora_SnowCircle', inner=True, **rough):
    # inner = 가운데 큰 눈꽃을 그림(10-25 「내부 큰 눈 문양을 없애는 방식은 어때」 → T_Aurora_SnowCircleRing은 False).
    # rough = roughen에 넘길 거칠기(없으면 게임에 쓰는 그 값). 10-20 밤 「S 괜찮긴 한데 거친 느낌이 없어 — 너무 정갈하고 이쁨」:
    # 기본 흔들림 2.5·1.2칸은 장판 900cm에 1024칸이라 화면에서 1~1.5화소(계산)라 안 보였다 → T_Aurora_SnowCircleRough(아래 __main__).
    # 눈 마법진(10-20). 반지름은 그림 반폭(half) 배수. 첫 판(육각별 + 룬 글자 + 고리 두른 문양)은 「너무 악마 문양 같아」로
    # 별·글자·작은 고리를 빼고 눈 결정만으로 꾸민다: 육각형(눈 결정의 꼴) + 그 안 원 + 눈꽃 + 작은 결정·얼음 마름모.
    scale = 2
    size = SIZE * scale
    centre = size / 2
    half = size / 2
    unit = scale  # 1024 그림 기준 1px
    up = -math.pi / 2
    image = Image.new('L', (size, size), 0)
    pen = Pen(ImageDraw.Draw(image), centre)
    outer, band, corner = half * 0.98, half * 0.90, half * 0.86
    inside = corner * math.cos(math.pi / 6)  # 육각형 안에 닿는 원
    # 바깥 겹고리(지금 바깥 고리 자리) + 사이 띠: 팔 방향마다 작은 눈 결정, 그 사이 10도마다 얼음 마름모(가운데가 크다)
    # 선 굵기: 10-20 「왜 이렇게 아쉽지」 분석(선이 가늘어 바닥 타일 줄눈과 세기가 비슷) → 약 1.6배
    pen.ring(outer, 8 * unit)
    pen.ring(band, 5 * unit)
    middle = (outer + band) / 2
    for k in range(6):
        arm = up + math.pi / 3 * k
        crystal(pen, pen.point(middle, arm), half * 0.03, 3.8 * unit)
        for step, big in ((1, False), (2, False), (3, True), (4, False), (5, False)):
            a = arm + math.radians(10 * step)
            if step in (1, 5):
                pen.dot(pen.point(middle, a), 4 * unit)
            else:
                diamond(pen, middle, a, half * (0.055 if big else 0.04), half * (0.026 if big else 0.02))
    # 육각형: 꼭짓점이 팔 방향, 안쪽 고리 바로 안 · 그 안에 닿는 원 · 원에서 꼭짓점까지 짧은 살
    corners = [pen.point(corner, up + math.pi / 3 * j) for j in range(6)]
    for j in range(6):
        pen.line(corners[j], corners[(j + 1) % 6], 6.5 * unit)
        pen.line(pen.point(inside, up + math.pi / 3 * j), corners[j], 5 * unit)
    pen.ring(inside, 5 * unit)
    # 육각형 변 바깥(변과 안쪽 고리 사이)마다 작은 눈 결정
    for j in range(6):
        crystal(pen, pen.point(half * 0.83, up + math.pi / 6 + math.pi / 3 * j), half * 0.045, 4 * unit)
    # 가운데: 지금 눈꽃을 원 안에 크게(바깥 결정 문양은 위의 작은 결정으로 옮겼다)
    if inner:
        flake(pen, half * 0.62, size * 0.012 * 1.0, glyphs=False)
    packed = pack(roughen(image, 45, **rough), size, band)
    out = OUT.parent / f'{name}.png'
    packed.save(out)
    print(out)


def glints():
    # S 별빛(10-19 「구원의 세레나데처럼 반짝거리는 느낌, 아주 느리게」): 마법진 안에 흩어진 작은 네 갈래 별빛 70개.
    # R = 별 모양(긴 가는 빛살 + 둥근 빛), G = 별마다 다른 박자(0~1, 별 둘레 원 안은 같은 값) — 재질이 G만큼 늦춰 천천히 켜고 끈다.
    rng = random.Random(21)
    size = SIZE
    centre = size / 2
    shape = Image.new('L', (size, size), 0)
    phase = Image.new('L', (size, size), 0)
    sd = ImageDraw.Draw(shape)
    pd = ImageDraw.Draw(phase)
    placed = []
    # 10-19 한때 35개로 줄였으나 화면의 자잘한 점 중 별빛 몫은 약 8%라 차이가 없었다(바쁨의 원인은 서리 결정 무늬) → 70개로 되돌림
    while len(placed) < 70:
        r = size * 0.44 * math.sqrt(rng.random())
        a = rng.uniform(0, 2 * math.pi)
        x, y = centre + r * math.cos(a), centre + r * math.sin(a)
        reach = rng.uniform(10, 26)
        if any(math.hypot(x - px, y - py) < reach + pr + 6 for px, py, pr in placed):
            continue
        placed.append((x, y, reach))
        pd.ellipse([x - reach - 3, y - reach - 3, x + reach + 3, y + reach + 3], fill=rng.randint(1, 255))
        tilt = rng.uniform(0, math.pi / 2)
        for k in range(4):
            ang = tilt + math.pi / 2 * k
            length = reach * (1.0 if k % 2 == 0 else 0.7)
            sd.line([(x, y), (x + length * math.cos(ang), y + length * math.sin(ang))], fill=255, width=2)
        sd.ellipse([x - reach * 0.18, y - reach * 0.18, x + reach * 0.18, y + reach * 0.18], fill=255)
    lines = shape.filter(ImageFilter.GaussianBlur(radius=0.8))
    glow = shape.filter(ImageFilter.GaussianBlur(radius=5))
    peak = max(glow.getextrema()[1], 1)
    glow = glow.point(lambda v: min(255, v * 255 // peak))
    # 또렷한 빛살 위에 둥근 빛을 반쯤 섞는다
    combined = ImageChops.lighter(lines, glow.point(lambda v: v // 2))
    packed = Image.merge('RGB', (combined, phase, Image.new('L', (size, size), 0)))
    out = OUT.parent / 'T_Aurora_Glints.png'
    packed.save(out)
    print(out)


def flake_arm_pair():
    # R 얼음 난무(10-21 「눈 모양 너무 퀄리티 낮아 보인다 — 이펙트 좀 더 신경 써 줄 수 있나」): 칼선 한 번에 바닥에 남는 눈꽃 지름 하나 —
    # 위·아래 두 팔(flake와 같은 곁가지·갈래·마름모) + 가운데 육각형. 세 번 60도씩 돌려 깔면 눈꽃 하나가 된다. 전엔 같은 굵기 막대
    # 15개(지름 3 + 곁가지 12)를 판으로 띄웠다. 얼음을 깎은 듯 조금 흔들고 갉고 밝기를 고르지 않게.
    # R = 선, G = 퍼진 빛, B = 아래 0 → 위 1(데칼이 베며 지나가는 쪽으로 드러남 — 그림 위쪽 = 나간 쪽)
    scale = 2
    size = SIZE * scale
    centre = size / 2
    radius = size * 0.46
    image = Image.new('L', (size, size), 0)
    pen = Pen(ImageDraw.Draw(image), centre)
    for angle in (-math.pi / 2, math.pi / 2):
        flake_arm(pen, radius, angle, size * 0.016)
    hexagon = [pen.point(radius * 0.13, math.pi / 3 * k - math.pi / 2) for k in range(6)]
    pen.draw.line(hexagon + [hexagon[0]], fill=255, width=int(size * 0.016 * 0.8), joint='curve')
    rough = roughen(image, 41, shake=1.6, fray=0.45, gap=0.0, blotch=0.35)
    lines = rough.filter(ImageFilter.GaussianBlur(radius=size * 0.0018))
    glow = rough.filter(ImageFilter.GaussianBlur(radius=size * 0.014))
    peak = max(glow.getextrema()[1], 1)
    glow = glow.point(lambda v: min(255, v * 255 // peak))
    along = Image.linear_gradient('L').rotate(180).resize((size, size))
    out = OUT.parent / 'T_Aurora_FlakeArm.png'
    Image.merge('RGB', (lines, glow, along)).resize((SIZE, SIZE), Image.LANCZOS).save(out)
    print(out)


if __name__ == '__main__':
    main()
    circle()
    # S 거친 시안: 흔들림 4배(화면 약 6·3화소) · 갉음 0.35 → 0.9(잡음 칸 140 → 70, 굵게 갉힘) · 끊김 3 → 12% · 선 밝기 0.5~1로 고르지 않게
    circle('T_Aurora_SnowCircleRough', shake=4.0, fray=0.9, grain_cells=70, gap=0.12, blotch=0.5)
    # S 가운데 눈꽃 없음(10-25, C++ Aurora.FX.SInner 0): 고리·띠·육각형은 게임 그림과 같은 거칠기
    circle('T_Aurora_SnowCircleRing', inner=False)
    glints()
    flake_arm_pair()
