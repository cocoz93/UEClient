"""Draw the light pictures for Aurora's fresh D drafts (2026-10-26 「내가 준 레퍼런스 참고하지 말고 니가 자유롭게 시안 여러 개 —
근본적인 이펙트 퀄리티나 디자인이 마음에 안 든다」, C++ Aurora.FX.DFresh) with numpy + Pillow. The drafts are built from these
glowing pictures on the engine plane (additive M_Aurora_FxAdd: R = soft glow tinted ice blue, G = bright white core) instead of pack
crystals, so every part shares one clean palette.
- T_Aurora_FxStreak: a falling light streak - bright head at the top (v = 0), a thin core and wider glow tapering to the tail.
- T_Aurora_FxStar: a sharp four-point star with four short diagonal rays and a soft halo (impact flash, glint).
- T_Aurora_FxRing: a ground ripple - a thin ring (core at 0.82 of the half size) whose brightness wavers round it, with a glow
  dragged inwards and a faint wash inside.
- T_Aurora_FxShard: an ice shard made of light - a long diamond, point at the top, bright edges and facet lines, one side lit.
- T_Aurora_DWard: the ward circle decal for draft 3 - two thin rings, twelve ice diamonds between them and six small inward triangles;
  B = angle clockwise from the top so C++ draws it round (same convention as the S rim cracks).
- T_Aurora_BlizzardSeal: the V blizzard's floor seal (10-26 「누가 봐도 궁극기로 보이게 화려하게」) - a double outer ring, a band of
  36 small glyphs, a hexagram, an inner ring and a six-armed snow crystal with twigs, on a faint wash (same R glow / G core packing).
- T_Aurora_FxSnow: a tiling field of falling snow (same day 「맵 전체에 눈보라가 쏟아지는 느낌」) - many small flakes, some bigger and
  a few large soft ones, each smeared a little along the fall (down and slightly left on the picture) for M_Aurora_FxSnow to scroll.
- T_Aurora_FxSpike: the V blizzard's ice spike (same day 「얼음송곳 좀 더 날카롭게, 이펙트 좀 다듬어」) - slimmer than FxShard with a long
  needle point (the width grows as a power of the distance from the tip), crisp edges, a ridge and two facet lines, a bright tip and
  only a tight glow.
- T_Aurora_FxSplash: the flat burst where a spike strikes - a dozen thin, sharp, uneven ice rays round a small bright centre and no
  wash inside (the ground ripple ring's wash read as bubbles under the blizzard).
Writes those PNGs into SourceArt/Aurora."""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

FOLDER = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora'


def blur(channel, pixels):
    image = Image.fromarray((np.clip(channel, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(pixels))
    return np.asarray(image, np.float32) / 255.0


def save(name, red, green, blue=None):
    if blue is None:
        blue = np.zeros_like(red)
    packed = np.stack([np.clip(red, 0, 1), np.clip(green, 0, 1), np.clip(blue, 0, 1)], axis=-1)
    FOLDER.mkdir(parents=True, exist_ok=True)
    Image.fromarray((packed * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / f'{name}.png')
    print(FOLDER / f'{name}.png')


def square(size):
    # 가운데 0, 가장자리 ±0.5
    y, x = (np.mgrid[0:size, 0:size] + 0.5) / size - 0.5
    return x, y


def streak():
    # 판 위 비율(굵기 16 : 길이 380 ≈ 1 : 24)로 늘어나 보이므로 머리는 세로로 아주 짧게 그린다
    height, width = 1024, 128
    v = (np.arange(height) + 0.5) / height
    u = (np.arange(width) + 0.5) / width - 0.5
    v, u = np.meshgrid(v, u, indexing='ij')
    head = 0.04
    t = np.clip((v - head) / (1.0 - head), 0.0, 1.0)  # 0 = 머리, 1 = 꼬리 끝
    behind = (v >= head).astype(np.float32)
    core = np.exp(-(u / (0.05 * (1.0 - 0.75 * t))) ** 2) * (1.0 - t) ** 1.4 * behind
    glow = np.exp(-(u / (0.17 * (1.0 - 0.55 * t))) ** 2) * (1.0 - t) ** 2.6 * behind
    # 머리: 앞쪽은 아주 짧게 사라지고 뒤로 조금 번지는 둥근 빛
    ahead = np.exp(-((v - head) / 0.012) ** 2)
    knob = np.exp(-(u / 0.22) ** 2) * np.where(v < head, ahead, np.exp(-((v - head) / 0.05) ** 2))
    save('T_Aurora_FxStreak', np.maximum(glow * 0.85, knob * 0.9), np.maximum(core, knob * np.exp(-(u / 0.1) ** 2)))


def star():
    size = 512
    x, y = square(size)
    x, y = x * 2.0, y * 2.0  # 가장자리 = ±1
    r = np.hypot(x, y)

    def ray(angle, length, width):
        along = np.abs(x * math.cos(angle) + y * math.sin(angle))
        across = np.abs(-x * math.sin(angle) + y * math.cos(angle))
        left = np.clip(1.0 - along / length, 0.0, 1.0)
        return np.exp(-(across / (width * left + 0.004)) ** 2) * left ** 2.2

    main = np.maximum(ray(0.0, 0.95, 0.045), ray(math.pi / 2, 0.95, 0.045))
    side = np.maximum(ray(math.pi / 4, 0.45, 0.035), ray(3 * math.pi / 4, 0.45, 0.035)) * 0.55
    spikes = np.maximum(main, side)
    centre = np.exp(-(r / 0.09) ** 2)
    halo = np.exp(-(r / 0.42) ** 2) * 0.45 * np.clip(1.0 - r, 0.0, 1.0)
    save('T_Aurora_FxStar', np.maximum(halo, blur(spikes, 6) * 0.9), np.maximum(spikes, centre))


def ring():
    size = 1024
    x, y = square(size)
    r = np.hypot(x, y) * 2.0
    angle = np.arctan2(x, -y)
    at = 0.82
    # 첫 판(고른 흰 선 + 좁은 빛)은 바닥에 그린 표시 원처럼 딱딱했다 → 심은 둘레를 따라 밝기가 출렁이고, 빛은 안쪽으로 넓게 끌린다
    rng = np.random.default_rng(11)
    wobble = sum(np.cos(k * angle + rng.uniform(0, 2 * math.pi)) / k for k in range(2, 8))
    wobble = (wobble - wobble.min()) / (wobble.max() - wobble.min())
    core = np.exp(-((r - at) / 0.006) ** 2) * (0.35 + 0.65 * wobble)
    glow = np.where(r < at, np.exp(-((r - at) / 0.09) ** 2), np.exp(-((r - at) / 0.025) ** 2)) * (0.6 + 0.4 * wobble)
    wash = np.where(r < at, np.clip((r - 0.3) / (at - 0.3), 0.0, 1.0) ** 2.0 * 0.22, 0.0)
    save('T_Aurora_FxRing', np.maximum(glow * 0.75, wash), core)


def shard():
    # 판 위 비율(굵기 34 : 길이 160 ≈ 1 : 4.7)에 맞춰 1 : 4로 그린다. 끝 = 위(v = 0.02), 가장 넓은 곳 v = 0.66, 뒤 끝은 좁게 잘림.
    height, width = 1024, 256
    samples = 3  # 테두리 계단을 줄이려고 3배로 그려 줄인다
    v = (np.arange(height * samples) + 0.5) / (height * samples)
    u = (np.arange(width * samples) + 0.5) / (width * samples) - 0.5
    v, u = np.meshgrid(v, u, indexing='ij')
    tip, wide, back = 0.02, 0.66, 0.97
    half = np.where(v < wide, 0.42 * np.clip((v - tip) / (wide - tip), 0.0, 1.0) ** 0.85,
                    0.42 - (0.42 - 0.16) * np.clip((v - wide) / (back - wide), 0.0, 1.0))
    half = np.where((v < tip) | (v > back), 0.0, half)
    inside = (np.abs(u) < half).astype(np.float32)
    edge_gap = half - np.abs(u)  # 가로 1 = 판 굵기(34cm)
    rim = np.exp(-(np.clip(edge_gap, 0, None) / 0.03) ** 2) * inside
    # 뒤 끝 잘린 면
    cut = np.exp(-((back - v) / 0.006) ** 2) * (np.abs(u) < half + 0.01)
    # 면 선: 가운데 등줄기 + 가장 넓은 모서리에서 뒤 가운데(v = 0.86)로 모이는 두 줄
    ridge = np.exp(-(u / 0.018) ** 2) * inside * np.clip((v - tip) / 0.1, 0.0, 1.0)
    facets = np.zeros_like(u)
    for side in (-1.0, 1.0):
        x0, y0, x1, y1 = side * 0.42, wide, 0.0, 0.86
        dx, dy = x1 - x0, (y1 - y0) / 4.0
        t = np.clip(((u - x0) * dx + (v - y0) / 4.0 * dy) / (dx * dx + dy * dy), 0.0, 1.0)
        distance = np.hypot(u - (x0 + t * dx), (v - y0) / 4.0 - t * dy)
        facets = np.maximum(facets, np.exp(-(distance / 0.015) ** 2) * inside)
    lines = np.maximum.reduce([rim, cut, ridge * 0.8, facets * 0.6])
    # 몸: 왼쪽 면이 빛을 받아 밝고, 끝으로 갈수록 밝아진다
    lit = np.where(u < 0, 1.0, 0.55)
    body = inside * lit * (0.3 + 0.25 * (1.0 - np.clip((v - tip) / (back - tip), 0.0, 1.0)))

    def shrink(channel):
        image = Image.fromarray((np.clip(channel, 0, 1) * 255).astype(np.uint8)).resize((width, height), Image.LANCZOS)
        return np.asarray(image, np.float32) / 255.0

    lines, body = shrink(lines), shrink(body)
    save('T_Aurora_FxShard', np.maximum(body, blur(lines, 5) * 0.8), lines)


def ward():
    size = 1024
    x, y = square(size)
    r = np.hypot(x, y) * 2.0
    angle = np.arctan2(x, -y)  # 위쪽 = 0, 시계 방향 +
    order = np.mod(angle, 2.0 * math.pi) / (2.0 * math.pi)
    px = 2.0 / size  # 반지름 단위 한 픽셀

    def band(at, width):
        return np.clip(1.0 - np.abs(r - at) / width, 0.0, 1.0)

    lines = np.maximum(band(0.93, 2.2 * px), band(0.86, 1.6 * px) * 0.8)
    # 두 고리 사이 얼음 마름모 12개(번갈아 크고 작게) — 눈금(첫 판)은 시계 판처럼 보였다
    for k in range(12):
        a = 2.0 * math.pi * k / 12
        along = x * 2.0 * math.sin(a) - y * 2.0 * math.cos(a)
        across = np.abs(x * 2.0 * math.cos(a) + y * 2.0 * math.sin(a))
        reach, width = (0.05, 0.022) if k % 2 == 0 else (0.03, 0.014)
        diamond = np.abs(along - 0.895) / reach + across / width
        lines = np.maximum(lines, np.clip((1.0 - diamond) * 6.0, 0.0, 1.0) * (1.0 if k % 2 == 0 else 0.75))
    # 안쪽을 가리키는 작은 세모 여섯
    for k in range(6):
        a = 2.0 * math.pi * (k + 0.5) / 6
        along = x * 2.0 * math.sin(a) - y * 2.0 * math.cos(a)
        across = np.abs(x * 2.0 * math.cos(a) + y * 2.0 * math.sin(a))
        depth = np.clip((0.845 - along) / 0.06, 0.0, 1.0)  # 0 = 밑변(고리 쪽), 1 = 꼭짓점(안쪽)
        inside = (along < 0.845) & (along > 0.785) & (across < 0.03 * (1.0 - depth))
        lines = np.maximum(lines, inside.astype(np.float32) * 0.9)
    save('T_Aurora_DWard', lines, blur(lines, 5) * 1.6, order)


def segment(x, y, x0, y0, x1, y1):
    # 점(x, y)에서 선분까지 거리(가장자리 = ±1 좌표)
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(x - (x0 + t * dx), y - (y0 + t * dy))


def seal():
    # 반경 800 바닥에 깔려 화면을 거의 다 덮으므로 2048로 그린다(한 픽셀 ≈ 0.8cm)
    size = 2048
    x, y = square(size)
    x, y = x * 2.0, y * 2.0  # 가장자리 = ±1, 위 = -y
    r = np.hypot(x, y)
    px = 2.0 / size

    def band(at, width):
        return np.clip(1.0 - np.abs(r - at) / width, 0.0, 1.0)

    def line(x0, y0, x1, y1, width):
        return np.clip(1.0 - segment(x, y, x0, y0, x1, y1) / width, 0.0, 1.0)

    def polar(radius, angle):
        # 위쪽 = 0, 시계 방향 +
        return radius * math.sin(angle), -radius * math.cos(angle)

    lines = np.maximum.reduce([band(0.96, 3.2 * px), band(0.935, 1.8 * px), band(0.85, 2.4 * px), band(0.43, 2.0 * px),
                               band(0.09, 1.8 * px)])
    # 바깥 띠의 글자 36개: 마름모 · 짧은 금 둘 · 작은 고리를 번갈아
    for k in range(36):
        a = 2.0 * math.pi * k / 36
        along = x * math.sin(a) - y * math.cos(a)
        across = x * math.cos(a) + y * math.sin(a)
        kind = k % 3
        if kind == 0:
            mark = np.clip((1.0 - (np.abs(along - 0.893) / 0.022 + np.abs(across) / 0.011)) * 5.0, 0.0, 1.0)
        elif kind == 1:
            mark = np.zeros_like(r)
            for side in (-0.007, 0.007):
                near = (np.abs(along - 0.893) < 0.017) & (np.abs(across - side) < 1.6 * px)
                mark = np.maximum(mark, near.astype(np.float32))
        else:
            mark = np.clip(1.0 - np.abs(np.hypot(along - 0.893, across) - 0.008) / (1.4 * px), 0.0, 1.0)
        lines = np.maximum(lines, mark * 0.9)
    # 30° 엇갈린 육각형 둘(꼭짓점이 0.85 고리에 닿아 열두 꼭짓점 눈 결정처럼) — 삼각형 둘을 겹친 첫 판은 종교 상징(육각별)으로 읽혔다
    for start in (0.0, math.pi / 6):
        corners = [polar(0.85, start + math.pi / 3 * k) for k in range(6)]
        for k in range(6):
            (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 6]
            lines = np.maximum(lines, line(x0, y0, x1, y1, 2.2 * px))
    # 가운데 눈 결정: 육각별 꼭짓점 사이를 가리키는 여섯 팔 + 곁가지 둘씩
    for k in range(6):
        a = math.pi / 6 + math.pi / 3 * k
        x0, y0 = polar(0.11, a)
        x1, y1 = polar(0.41, a)
        lines = np.maximum(lines, line(x0, y0, x1, y1, 2.4 * px))
        for at, reach in ((0.22, 0.07), (0.32, 0.05)):
            bx, by = polar(at, a)
            for turn in (-math.pi / 4, math.pi / 4):
                tx, ty = bx + reach * math.sin(a + turn), by - reach * math.cos(a + turn)
                lines = np.maximum(lines, line(bx, by, tx, ty, 1.8 * px))
    wash = np.where(r < 0.96, 0.05 + 0.05 * np.clip((r - 0.4) / 0.56, 0.0, 1.0), 0.0)
    save('T_Aurora_BlizzardSeal', np.maximum(blur(lines, 7) * 0.95, wash), lines)


def snow():
    # 이어 붙여도 이음매가 없게(가장자리를 넘는 눈송이는 반대쪽으로 감아 그린다). 눈송이는 흐르는 쪽(그림 아래 · 조금 왼쪽)으로 번져 있다.
    size = 1024
    rng = np.random.default_rng(26)
    glow = np.zeros((size, size), np.float32)
    core = np.zeros((size, size), np.float32)
    fall = (-math.sin(math.radians(15)), math.cos(math.radians(15)))  # (가로, 세로) 그림 아래 = +세로

    def flake(cx, cy, radius, smear, strength, soft):
        reach = int(math.ceil(radius * (smear + 2.5)))
        oy, ox = np.mgrid[-reach:reach + 1, -reach:reach + 1].astype(np.float32)
        ox, oy = ox - (cx % 1.0), oy - (cy % 1.0)
        along = ox * fall[0] + oy * fall[1]
        across = -ox * fall[1] + oy * fall[0]
        shape = np.exp(-(along / (radius * smear)) ** 2 - (across / radius) ** 2)
        rows = (np.arange(-reach, reach + 1) + int(cy)) % size
        cols = (np.arange(-reach, reach + 1) + int(cx)) % size
        block = np.ix_(rows, cols)
        glow[block] = np.maximum(glow[block], shape * strength * (1.0 if soft else 0.7))
        if not soft:
            core[block] = np.maximum(core[block], np.exp(-(along / (radius * smear * 0.6)) ** 2 - (across / (radius * 0.6)) ** 2) * strength)

    # 10-26 「눈이 너무 밀도가 높다」 — 900 · 110 · 14 → 400 · 50 · 6
    for _ in range(400):
        flake(rng.uniform(0, size), rng.uniform(0, size), rng.uniform(1.0, 2.2), rng.uniform(1.6, 2.6), rng.uniform(0.5, 1.0), False)
    for _ in range(50):
        flake(rng.uniform(0, size), rng.uniform(0, size), rng.uniform(2.8, 4.5), rng.uniform(1.3, 2.0), rng.uniform(0.6, 1.0), False)
    for _ in range(6):
        flake(rng.uniform(0, size), rng.uniform(0, size), rng.uniform(9.0, 15.0), 1.2, rng.uniform(0.25, 0.45), True)
    save('T_Aurora_FxSnow', glow, core)


def spike():
    # 판 비율(굵기 24~34 : 길이 190~280 ≈ 1 : 8)에 맞춰 1 : 4 그림을 세로로 두 배 늘려 쓴다. 끝 = 위(v = 0.01), 가장 넓은 곳 v = 0.8.
    # 굵기가 끝에서부터 거듭제곱(1.7)으로 늘어 끝이 바늘처럼 길게 빠진다(FxShard는 0.85제곱이라 끝이 뭉툭한 마름모였다).
    height, width = 1024, 256
    samples = 3
    v = (np.arange(height * samples) + 0.5) / (height * samples)
    u = (np.arange(width * samples) + 0.5) / (width * samples) - 0.5
    v, u = np.meshgrid(v, u, indexing='ij')
    tip, wide, back = 0.01, 0.8, 0.975
    most = 0.34
    half = np.where(v < wide, most * np.clip((v - tip) / (wide - tip), 0.0, 1.0) ** 1.7,
                    most - (most - 0.12) * np.clip((v - wide) / (back - wide), 0.0, 1.0) ** 0.8)
    half = np.where((v < tip) | (v > back), 0.0, half)
    inside = (np.abs(u) < half).astype(np.float32)
    gap = np.clip(half - np.abs(u), 0, None)
    rim = np.exp(-(gap / 0.016) ** 2) * inside
    cut = np.exp(-((back - v) / 0.004) ** 2) * (np.abs(u) < half + 0.008)
    ridge = np.exp(-(u / 0.012) ** 2) * inside
    # 끝에서 가장 넓은 모서리 안쪽으로 가는 면 선 둘
    facets = np.zeros_like(u)
    for side in (-1.0, 1.0):
        along = np.clip((v - tip) / (wide - tip), 0.0, 1.0)
        line = side * most * 0.55 * along ** 1.7
        facets = np.maximum(facets, np.exp(-((u - line) / 0.01) ** 2) * inside * (v < wide))
    lines = np.maximum.reduce([rim, cut, ridge * 0.9, facets * 0.55])
    # 몸: 끝으로 갈수록 희고 밝게, 왼쪽 면이 빛을 받음
    toward_tip = 1.0 - np.clip((v - tip) / (back - tip), 0.0, 1.0)
    body = inside * np.where(u < 0, 1.0, 0.5) * (0.18 + 0.4 * toward_tip ** 2)
    # 끝 하이라이트는 몸 안에만(밖으로 나가면 끝 위에 빛 구슬이 떠 보였다)
    point = np.exp(-((v - tip - 0.07) / 0.05) ** 2) * (np.abs(u) < half + 0.004) * inside

    def shrink(channel):
        image = Image.fromarray((np.clip(channel, 0, 1) * 255).astype(np.uint8)).resize((width, height), Image.LANCZOS)
        return np.asarray(image, np.float32) / 255.0

    lines, body, point = shrink(lines), shrink(body), shrink(point)
    save('T_Aurora_FxSpike', np.maximum(body, blur(lines, 2) * 0.75), np.maximum(lines, point))


def splash():
    size = 512
    x, y = square(size)
    x, y = x * 2.0, y * 2.0
    r = np.hypot(x, y)
    rng = np.random.default_rng(79)
    rays = np.zeros_like(r)
    for k in range(13):
        a = 2.0 * math.pi * (k + rng.uniform(-0.3, 0.3)) / 13
        length = rng.uniform(0.45, 1.0)
        width = rng.uniform(0.018, 0.032)
        along = x * math.cos(a) + y * math.sin(a)
        across = np.abs(-x * math.sin(a) + y * math.cos(a))
        left = np.clip(1.0 - along / length, 0.0, 1.0) * (along > 0.02)
        rays = np.maximum(rays, np.clip(1.0 - across / (width * left + 1e-4), 0.0, 1.0) * left ** 0.7)
    centre = np.exp(-(r / 0.08) ** 2)
    save('T_Aurora_FxSplash', np.maximum(blur(rays, 3) * 0.8, centre * 0.6), np.maximum(rays, centre))


def gem():
    # F 얼음 결정 사격(10-26 「전혀 2번 캐릭터의 F 스킬 느낌이 아닌데」 — Sparrow F는 크고 각진 보석 판이 꽃잎처럼 모인다): 연 모양 판(위 끝이
    # 길고 아래가 짧음), 가장 넓은 가로선과 세로 등줄기로 나뉜 면 넷의 밝기를 달리해(왼위 밝게 · 오른위 중간 · 왼아래 중간 · 오른아래 어둡게)
    # 각진 결정으로 읽히게, 테두리·면 경계는 흰 심. 1 : 2.
    height, width = 512, 256
    samples = 3
    v = (np.arange(height * samples) + 0.5) / (height * samples)
    u = (np.arange(width * samples) + 0.5) / (width * samples) - 0.5
    v, u = np.meshgrid(v, u, indexing='ij')
    tip, wide, bottom, most = 0.02, 0.62, 0.98, 0.46
    half = np.where(v < wide, most * np.clip((v - tip) / (wide - tip), 0.0, 1.0),
                    most * np.clip(1.0 - (v - wide) / (bottom - wide), 0.0, 1.0))
    half = np.where((v < tip) | (v > bottom), 0.0, half)
    inside = (np.abs(u) < half).astype(np.float32)
    gap = np.clip(half - np.abs(u), 0, None)
    rim = np.exp(-(gap / 0.022) ** 2) * inside
    ridge = np.exp(-(u / 0.012) ** 2) * inside
    cross = np.exp(-((v - wide) / 0.006) ** 2) * inside
    upper, left = v < wide, u < 0
    facets = np.select([upper & left, upper & ~left, ~upper & left], [0.75, 0.45, 0.35], 0.2) * inside
    # 왼위 면 안쪽에 비스듬한 반사 한 줄
    glint = np.exp(-((u + 0.16 + (v - 0.35) * 0.35) / 0.018) ** 2) * inside * upper * left * (v > 0.18)
    lines = np.maximum.reduce([rim, ridge * 0.8, cross * 0.7, glint * 0.6])

    def shrink(channel):
        image = Image.fromarray((np.clip(channel, 0, 1) * 255).astype(np.uint8)).resize((width, height), Image.LANCZOS)
        return np.asarray(image, np.float32) / 255.0

    lines, facets = shrink(lines), shrink(facets)
    save('T_Aurora_FxGem', np.maximum(facets, blur(lines, 3) * 0.7), lines)


def main():
    streak()
    star()
    ring()
    shard()
    ward()
    seal()
    snow()
    spike()
    splash()
    gem()


if __name__ == '__main__':
    main()
