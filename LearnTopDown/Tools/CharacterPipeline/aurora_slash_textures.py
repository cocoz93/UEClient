"""Draw the two sweeping floor masks for Aurora's Q drafts (2026-10-19 「Q 이펙트를 어쩌면 좋을까, 시안 여러 개」) with numpy + Pillow.
Both face up in the picture (towards v = 0) around the decal centre (= the caster's feet) and span the slash fan (+-62 deg).
B = where along the fan a pixel sits (0 at the left end, 1 at the right end) so the material can sweep them in (Reveal).
- T_Aurora_SlashArc: a crescent sword wave - a sharp bright outer edge (R), a body that fades inwards and a soft glow (G),
  thickest in the middle and tapering to points at both ends, with a few frost sparkles along it.
- T_Aurora_FrostSweep: a fan of frost wind - radial white streaks of different lengths (R) over a soft mist (G).
- T_Aurora_SpinRing / T_Aurora_SpinFrost (E drafts): a full-circle sword wave and six spiral frost streaks; their B runs once
  round clockwise from the top instead of across the fan.
- T_Aurora_SlashScar (Q warrior draft): a gouge cut into the floor just inside the blade edge (G = trench to darken, R = broken
  frost lips and flung chips), B across the fan like the crescent.
- T_Aurora_HasteCrack (S warrior draft): seven thick ice cracks splitting out from the centre with short branches and a broken
  ice rim (R = crack cores, G = trench around them); B = distance from the centre so it splits outwards.
- T_Aurora_RimCrack / T_Aurora_RimShatter (S drafts 6·7, 2026-10-19 night): the two rings of the snowflake floor cracked - thin
  glowing cracks / thick ones with a dark trench and chips; B = angle from the front so it cracks round both sides.
- T_Aurora_RuptureCrack (D drafts): a jagged crack running up the middle of a square (bottom = caster, top = end of the line).
- T_Aurora_ImpactCrack (F drafts): a star of cracks round a dented centre where a blade struck.
- T_Aurora_SlashWave (Q flying wave draft, 2026-10-20 night): the SlashArc crescent with a thicker body that stays bright
  all the way in (R) and a wider glow (G), no sparkles; same placement on the plane as SlashArc.
- T_Aurora_SlashRough / T_Aurora_NovaRing (Q big wave / V shockwave drafts, same night): a thicker crescent and a full ring torn
  like a brush stroke - a jagged bright edge, strands of different lengths running in from it, chips flung off past them.
- T_Aurora_SlashRougher / T_Aurora_NovaRingRough (next drafts): the same torn band roughed up harder - a deeper jagged edge,
  strands of very different lengths and gaps torn out of the edge.
Writes those PNGs (plus the W streak and the flake sprite) into SourceArt/Aurora."""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
HALF_ANGLE = math.radians(62.0)
FOLDER = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora'


def polar():
    y, x = (np.mgrid[0:SIZE, 0:SIZE] + 0.5) / SIZE - 0.5
    radius = np.hypot(x, y) * 2.0  # 가장자리 = 1
    angle = np.arctan2(x, -y)  # 위쪽(v = 0) = 0, 오른쪽 = +
    return radius, angle


def blur(channel, amount):
    image = Image.fromarray((np.clip(channel, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SIZE * amount))
    return np.asarray(image, np.float32) / 255.0


def save(name, red, green, blue):
    packed = np.stack([np.clip(red, 0, 1), np.clip(green, 0, 1), np.clip(blue, 0, 1)], axis=-1)
    FOLDER.mkdir(parents=True, exist_ok=True)
    Image.fromarray((packed * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / f'{name}.png')
    print(FOLDER / f'{name}.png')


def slash_arc(radius, angle, along, inside):
    rng = np.random.default_rng(3)
    # 가운데가 가장 두껍고 양끝이 뾰족해지는 두께(sin 꼴), 바깥 날은 반경 0.78 근처.
    # 10-19 오후 「이상하다, 테두리 더 얇게」: 몸통 두께 0.2 → 0.1, 날 0.006 → 0.0045, 퍼진 빛 0.02 → 0.012(바닥에 굵은 흰 띠를 칠한 듯 보였다)
    taper = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.8
    edge = 0.78 + 0.03 * np.cos(angle * 3.0)
    thickness = 0.1 * taper
    depth = (edge - radius) / np.maximum(thickness, 1e-4)  # 0 = 바깥 날, 1 = 안쪽 끝
    body = np.where((depth >= 0) & (depth <= 1) & inside, np.clip(1.0 - depth, 0, 1) ** 1.6, 0.0)
    blade = np.clip(1.0 - np.abs(radius - edge) / 0.0045, 0, 1) * (taper > 0.05) * inside
    red = np.maximum(blade, body * 0.75)
    glow = blur(np.maximum(blade, body), 0.012) * 1.3
    # 서리 반짝임: 날 언저리에 작은 점(몸통이 얇아진 만큼 날 가까이)
    sparkle = np.zeros_like(radius)
    for _ in range(140):
        t = rng.uniform(-1, 1) * HALF_ANGLE * 0.95
        r = 0.78 + 0.03 * math.cos(t * 3.0) + rng.normal(scale=0.02) - 0.03 * rng.random()
        cx = 0.5 + r * 0.5 * math.sin(t)
        cy = 0.5 - r * 0.5 * math.cos(t)
        px, py = int(cx * SIZE), int(cy * SIZE)
        size = rng.uniform(1.2, 3.5)
        x0, x1, y0, y1 = max(px - 5, 0), min(px + 6, SIZE), max(py - 5, 0), min(py + 6, SIZE)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        sparkle[y0:y1, x0:x1] = np.maximum(sparkle[y0:y1, x0:x1], np.clip(size - np.hypot(xx - px, yy - py), 0, 1))
    save('T_Aurora_SlashArc', np.maximum(red, sparkle), glow, along)


def slash_wave(radius, angle, along, inside):
    # Q 날아가는 얼음 검기 시안(10-20 밤 「Q 다 아쉽다」): 게임 화면에선 SlashArc의 날 선(두께 0.0045 — 300cm 검기에서 약 1cm)만
    # 보이고 몸통은 안쪽으로 빨리 옅어져(세제곱 꼴 × 0.75) 짙은 파랑으로 묻혔다. 같은 자리(바깥 날 반경 0.78 근처)에 몸통 0.16
    # (SlashArc 0.1의 1.6배)을 날에서 안쪽 끝까지 R 1 → 0.45로 곧게 옅어지게 채우고, 안쪽 끝 25%만 부드럽게 끊는다. 퍼진 빛은 넓게.
    taper = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.7
    edge = 0.78 + 0.03 * np.cos(angle * 3.0)
    thickness = 0.16 * taper
    depth = (edge - radius) / np.maximum(thickness, 1e-4)  # 0 = 바깥 날, 1 = 안쪽 끝
    body = np.where((depth >= 0) & (depth <= 1) & inside, (1.0 - 0.55 * depth) * np.clip((1.0 - depth) / 0.25, 0, 1), 0.0)
    blade = np.clip(1.0 - np.abs(radius - edge) / 0.008, 0, 1) * (taper > 0.05) * inside
    shape = np.maximum(blade, body)
    save('T_Aurora_SlashWave', blur(shape, 0.002), blur(shape, 0.02) * 1.2, along)


def line_noise(rng, count, t, loop=False):
    # 0~1 사이 매끄러운 1차원 잡음: 무작위 점 count개를 t(0~1)에 맞춰 잇는다. loop = 한 바퀴(끝 점 = 첫 점, 이음매 없음)
    points = rng.random(count + 1)
    if loop:
        points[-1] = points[0]
    return np.interp(t * count, np.arange(count + 1), points)


def torn_band(rng, radius, t, edge_at, thickness, fine, coarse, loop, jag=(0.006, 0.003), reach_floor=0.35, gaps=0.0):
    # 붓으로 그은 듯 뜯긴 띠: 바깥 날(edge_at 근처, 굵게·잘게 jag만큼 울퉁불퉁)에서 안쪽으로 각도마다 길이가 다른 가는 결이 뻗고(잔 결
    # fine개 + 굵은 결 coarse개, 가장 짧은 결 = 몸통의 reach_floor), 결마다 밝기가 달라 안쪽 끝이 들쭉날쭉하다.
    # gaps > 0 = 날째 군데군데 뜯겨 나간 틈(각도의 그만큼). 돌려주는 것 = (모양, 바깥 날, 깊이)
    edge = edge_at + jag[0] * (line_noise(rng, coarse // 2, t, loop) - 0.5) + jag[1] * (line_noise(rng, fine, t, loop) - 0.5)
    depth = (edge - radius) / np.maximum(thickness, 1e-4)  # 0 = 바깥 날, 1 = 몸통 끝
    reach = reach_floor + (1.0 - reach_floor) * (0.6 * line_noise(rng, fine, t, loop) + 0.4 * line_noise(rng, coarse, t, loop))
    streak = 0.65 + 0.35 * line_noise(rng, int(fine * 1.4), t, loop)
    inner = np.clip((reach - depth) / 0.12, 0, 1)
    body = np.where(depth >= 0, (1.0 - 0.6 * np.clip(depth, 0, 1)) * streak * inner, 0.0)
    blade = np.clip(1.0 - np.abs(radius - edge) / 0.009, 0, 1)
    shape = np.maximum(blade, body)
    if gaps > 0.0:
        hole = line_noise(rng, coarse, t, loop)
        shape = shape * np.clip((hole - np.quantile(hole, gaps)) / 0.04, 0, 1)
    return shape, edge, depth


def scatter_chips(rng, mask_fn, count):
    # 작은 얼음 조각 count개(지름 1.5~4칸, 밝기 0.5~1). mask_fn(rng) = 조각 하나의 (x, y) 화소 자리
    chips = np.zeros((SIZE, SIZE), np.float32)
    for _ in range(count):
        px, py = mask_fn(rng)
        size = rng.uniform(1.5, 4.0)
        bright = rng.uniform(0.5, 1.0)
        x0, x1, y0, y1 = max(px - 5, 0), min(px + 6, SIZE), max(py - 5, 0), min(py + 6, SIZE)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        chips[y0:y1, x0:x1] = np.maximum(chips[y0:y1, x0:x1], np.clip(size - np.hypot(xx - px, yy - py), 0, 1) * bright)
    return chips


def slash_rough(radius, angle, along, inside):
    # Q 큰 검기 시안(10-20 밤 「7번이 그나마 낫다 — 더 크게, 굵게, 빠르게, 더 멀리, 더 거친 느낌, 퀄리티도 더 좋게」): SlashWave(몸통 0.16)보다
    # 굵은 0.24 몸통을 붓질처럼 뜯긴 결로(torn_band), 결 너머로 뜯겨 날리는 조각. 자리(바깥 날 반경 0.8 근처)는 SlashArc와 같다.
    rng = np.random.default_rng(11)
    t = (angle / HALF_ANGLE + 1.0) / 2.0
    taper = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.6
    shape, edge, depth = torn_band(rng, radius, t, 0.8 + 0.025 * np.cos(angle * 3.0), 0.24 * taper, 220, 45, False)
    shape = shape * inside * (taper > 0.03)

    def chip(rng):
        a = rng.uniform(-0.92, 0.92) * HALF_ANGLE
        r = 0.8 + 0.025 * math.cos(a * 3.0) - 0.24 * math.cos(a / HALF_ANGLE * math.pi / 2) ** 0.6 * rng.uniform(0.6, 1.25)
        return int((0.5 + r * 0.5 * math.sin(a)) * SIZE), int((0.5 - r * 0.5 * math.cos(a)) * SIZE)

    # 첫 판 260개는 결 너머에 흩뿌린 반짝이 가루처럼 보였다(10-19 「공주 같다」로 뺀 느낌) → 90개를 띠 가까이에만
    chips = scatter_chips(rng, chip, 90)
    save('T_Aurora_SlashRough', np.maximum(blur(shape, 0.0015), chips), blur(shape, 0.025) * 1.25, along)


def slash_flip(radius, angle, along, inside):
    # Q 시안 QFeel 4(10-21 「시안 중에선 지금 Q가 제일 낫다 — 다른 시안, 한계인가」): 지금 큰 검기(SlashRough)와 같은 뜯긴 결을 여덟 장으로
    # 그려 4×2 한 장에 담는다(장마다 1024, 왼쪽 위부터 가로로). 0·1 = 생겨남(몸통이 얇고 결이 짧다 → 반쯤), 2~4 = 다 자란 모습(결 자리를
    # 조금씩 밀어 일렁임 — 2의 결은 SlashRough와 같고 조각만 따로 뿌림), 5~7 = 찢겨 흩어짐(날째 뜯긴 틈 15 → 35 → 60%, 결 너머로 조각이 점점 멀리·많이).
    # 장마다 (몸통 굵기 배율, 가장 짧은 결, 뜯긴 틈, 조각 수, 조각이 몸통 깊이의 몇 배까지, 결 자리 밀기)
    frames = [(0.35, 0.7, 0.0, 15, 1.0, 0.0), (0.7, 0.5, 0.0, 40, 1.2, 0.0), (1.0, 0.35, 0.0, 90, 1.25, 0.0),
              (1.0, 0.35, 0.0, 90, 1.25, 0.004), (1.0, 0.35, 0.0, 90, 1.25, -0.004),
              (1.0, 0.3, 0.15, 130, 1.5, 0.0), (0.95, 0.25, 0.35, 170, 1.8, 0.0), (0.9, 0.2, 0.6, 200, 2.2, 0.0)]
    taper = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.6
    atlas = np.zeros((SIZE * 2, SIZE * 4, 3), np.float32)
    for index, (thick, reach_floor, gaps, chip_count, chip_reach, slide) in enumerate(frames):
        rng = np.random.default_rng(11)
        t = (angle / HALF_ANGLE + 1.0) / 2.0 + slide
        shape, edge, depth = torn_band(rng, radius, t, 0.8 + 0.025 * np.cos(angle * 3.0), 0.24 * thick * taper, 220, 45, False,
                                       reach_floor=reach_floor, gaps=gaps)
        shape = shape * inside * (taper > 0.03)

        def chip(rng, thick=thick, chip_reach=chip_reach):
            a = rng.uniform(-0.92, 0.92) * HALF_ANGLE
            r = 0.8 + 0.025 * math.cos(a * 3.0) - 0.24 * thick * math.cos(a / HALF_ANGLE * math.pi / 2) ** 0.6 * rng.uniform(-0.1, chip_reach)
            return int((0.5 + r * 0.5 * math.sin(a)) * SIZE), int((0.5 - r * 0.5 * math.cos(a)) * SIZE)

        chips = scatter_chips(np.random.default_rng(100 + index), chip, chip_count)
        row, col = divmod(index, 4)
        tile = np.stack([np.maximum(blur(shape, 0.0015), chips), np.clip(blur(shape, 0.025) * 1.25, 0, 1), along], axis=-1)
        atlas[row * SIZE:(row + 1) * SIZE, col * SIZE:(col + 1) * SIZE] = tile
    FOLDER.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / 'T_Aurora_SlashFlip.png')
    print(FOLDER / 'T_Aurora_SlashFlip.png')


def nova_ring(radius, angle):
    # V 서리 충격파 시안(10-20 밤 「저 얼음 오브젝트가 별로 — 지우고 다른 이펙트」): Q 큰 검기와 같은 뜯긴 결을 한 바퀴 — 바깥 날 반경 0.9,
    # 결은 가운데 쪽으로 0.16. 잡음은 한 바퀴로 이어 붙여 이음매가 없다. B = 0(드러남 없이 처음부터 다).
    rng = np.random.default_rng(17)
    t = (angle + math.pi) / (2.0 * math.pi)
    shape, edge, depth = torn_band(rng, radius, t, 0.9, 0.16, 260, 50, True)

    def chip(rng):
        a = rng.uniform(-math.pi, math.pi)
        r = 0.9 - 0.16 * rng.uniform(0.6, 1.25)
        return int((0.5 + r * 0.5 * math.sin(a)) * SIZE), int((0.5 - r * 0.5 * math.cos(a)) * SIZE)

    chips = scatter_chips(rng, chip, 150)
    save('T_Aurora_NovaRing', np.maximum(blur(shape, 0.0015), chips), blur(shape, 0.025) * 1.25, np.zeros_like(radius))


def rougher(radius, angle, along, inside):
    # 더 거친 판(10-20 밤 「23이 괜찮은데 이걸 기반으로 여러 시안」 · 「V는 8을 기반으로」): 같은 뜯긴 결을 더 세게 — 바깥 날 울퉁불퉁 약 3배
    # (0.006·0.003 → 0.018·0.008), 가장 짧은 결 0.35 → 0.12(결 길이 차이가 커짐), 잔 결 더 촘촘히, 날째 뜯겨 나간 틈 8%.
    rng = np.random.default_rng(23)
    t = (angle / HALF_ANGLE + 1.0) / 2.0
    taper = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.6
    shape, edge, depth = torn_band(rng, radius, t, 0.8 + 0.025 * np.cos(angle * 3.0), 0.26 * taper, 340, 60, False,
                                   jag=(0.018, 0.008), reach_floor=0.12, gaps=0.08)
    shape = shape * inside * (taper > 0.03)

    def chip(rng):
        a = rng.uniform(-0.92, 0.92) * HALF_ANGLE
        r = 0.8 + 0.025 * math.cos(a * 3.0) - 0.26 * math.cos(a / HALF_ANGLE * math.pi / 2) ** 0.6 * rng.uniform(0.3, 1.3)
        return int((0.5 + r * 0.5 * math.sin(a)) * SIZE), int((0.5 - r * 0.5 * math.cos(a)) * SIZE)

    chips = scatter_chips(rng, chip, 130)
    save('T_Aurora_SlashRougher', np.maximum(blur(shape, 0.0015), chips), blur(shape, 0.025) * 1.25, along)
    rng = np.random.default_rng(29)
    t = (angle + math.pi) / (2.0 * math.pi)
    shape, edge, depth = torn_band(rng, radius, t, 0.9, 0.17, 380, 64, True, jag=(0.018, 0.008), reach_floor=0.12, gaps=0.08)

    def ring_chip(rng):
        a = rng.uniform(-math.pi, math.pi)
        r = 0.9 - 0.17 * rng.uniform(0.3, 1.3)
        return int((0.5 + r * 0.5 * math.sin(a)) * SIZE), int((0.5 - r * 0.5 * math.cos(a)) * SIZE)

    chips = scatter_chips(rng, ring_chip, 200)
    save('T_Aurora_NovaRingRough', np.maximum(blur(shape, 0.0015), chips), blur(shape, 0.025) * 1.25, np.zeros_like(radius))


def frost_sweep(radius, angle, along, inside):
    rng = np.random.default_rng(9)
    streaks = np.zeros_like(radius)
    # 부채꼴 안에 바깥으로 뻗는 흰 줄 여럿(길이·굵기·밝기가 제각각)
    for _ in range(46):
        t = rng.uniform(-1, 1) * HALF_ANGLE * 0.92
        start = rng.uniform(0.18, 0.45)
        end = min(start + rng.uniform(0.25, 0.55), 0.96)
        width = rng.uniform(0.004, 0.011)
        strength = rng.uniform(0.5, 1.0)
        across = np.abs(np.sin(angle - t)) * radius
        span = (radius - start) / max(end - start, 1e-3)
        line = np.clip(1.0 - across / width, 0, 1) * np.clip(np.sin(np.clip(span, 0, 1) * math.pi), 0, 1)
        streaks = np.maximum(streaks, line * strength * (np.cos(angle - t) > 0))
    streaks = blur(streaks, 0.0015) * inside
    reach = np.clip((radius - 0.12) / 0.1, 0, 1) * np.clip((0.97 - radius) / 0.12, 0, 1)
    fade = np.clip(np.cos(angle / HALF_ANGLE * math.pi / 2), 0, 1) ** 0.5
    mist = blur(streaks, 0.02) * 1.6 + 0.35 * reach * fade * inside
    save('T_Aurora_FrostSweep', streaks, mist, along)


def spin_ring(radius, angle):
    # E 시안 1(10-19 「휘두르는 이펙트 자체가 아쉽다」): 몸을 한 바퀴 도는 원형 검기. 바깥 날(R)과 안쪽으로 옅어지는 몸통, 퍼진 빛(G).
    # B = 위쪽(앞)부터 시계 방향으로 한 바퀴 0 → 1. 시작·끝 이음매는 날을 가늘게 해 티 나지 않게.
    rng = np.random.default_rng(4)
    around = (angle % (2 * math.pi)) / (2 * math.pi)
    taper = np.clip(np.minimum(around, 1.0 - around) / 0.08, 0, 1) ** 0.7
    edge = 0.8
    thickness = 0.16 * taper * (0.7 + 0.3 * around)
    depth = (edge - radius) / np.maximum(thickness, 1e-4)
    body = np.where((depth >= 0) & (depth <= 1), np.clip(1.0 - depth, 0, 1) ** 1.6, 0.0)
    blade = np.clip(1.0 - np.abs(radius - edge) / 0.006, 0, 1) * (taper > 0.05)
    red = np.maximum(blade, body * 0.75)
    glow = blur(np.maximum(blade, body), 0.02) * 1.4
    sparkle = np.zeros_like(radius)
    for _ in range(220):
        t = rng.uniform(0, 2 * math.pi)
        r = 0.8 + rng.normal(scale=0.03) - 0.05 * rng.random()
        px, py = int((0.5 + r * 0.5 * math.sin(t)) * SIZE), int((0.5 - r * 0.5 * math.cos(t)) * SIZE)
        size = rng.uniform(1.2, 3.5)
        x0, x1, y0, y1 = max(px - 5, 0), min(px + 6, SIZE), max(py - 5, 0), min(py + 6, SIZE)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        sparkle[y0:y1, x0:x1] = np.maximum(sparkle[y0:y1, x0:x1], np.clip(size - np.hypot(xx - px, yy - py), 0, 1))
    save('T_Aurora_SpinRing', np.maximum(red, sparkle), glow, around)


def spin_frost(radius, angle):
    # E 시안 2: 가운데서 바깥으로 감겨 나가는 서리 줄기(로그 나선 여섯 갈래, R)와 옅은 서리 안개(G). B = 시계 방향 한 바퀴.
    rng = np.random.default_rng(12)
    around = (angle % (2 * math.pi)) / (2 * math.pi)
    streaks = np.zeros_like(radius)
    for arm in range(6):
        start = 2 * math.pi * arm / 6 + rng.uniform(-0.2, 0.2)
        for strand in range(3):
            twist = 2.2 + 0.35 * strand
            width = rng.uniform(0.006, 0.012)
            # 나선: 반경 r에서 각도 = start + twist·ln(r/0.15). 픽셀 각도와의 차이를 둘레 거리로 재어 선을 긋는다.
            target = start + twist * np.log(np.maximum(radius, 1e-3) / 0.15) + 0.12 * strand
            difference = np.angle(np.exp(1j * (angle - target)))
            line = np.clip(1.0 - np.abs(difference) * radius / width, 0, 1)
            span = np.clip((radius - 0.15) / 0.1, 0, 1) * np.clip((0.95 - radius) / 0.15, 0, 1)
            streaks = np.maximum(streaks, line * span * rng.uniform(0.6, 1.0))
    streaks = blur(streaks, 0.0015)
    mist = blur(streaks, 0.025) * 1.5 + 0.18 * np.clip((radius - 0.12) / 0.1, 0, 1) * np.clip((0.95 - radius) / 0.2, 0, 1)
    save('T_Aurora_SpinFrost', streaks, mist, around)


def dash_streak():
    # W(10-19 「이펙트에 맞춰 땅에 흰색 이펙트」): 돌진 길을 따라 남는 흰 검기 자국. 그림 아래 = 출발, 위 = 도착(B = 0 → 1).
    # 데칼이 길이·폭을 따로 늘리므로 그림은 가운데 세로 띠로 그린다. 출발 쪽은 가늘고 도착 쪽으로 굵어지다 끝이 둥글게 닫힌다.
    rng = np.random.default_rng(8)
    y, x = (np.mgrid[0:SIZE, 0:SIZE] + 0.5) / SIZE
    along = 1.0 - y  # 아래 0 → 위 1
    across = np.abs(x - 0.5) * 2.0  # 가운데 0 → 가장자리 1
    half = 0.08 + 0.3 * np.clip(along / 0.85, 0, 1) ** 0.8
    head = np.clip((0.97 - along) / 0.06, 0, 1) ** 0.5
    tail = np.clip(along / 0.04, 0, 1)
    half = half * head * tail
    body = np.clip(1.0 - across / np.maximum(half, 1e-4), 0, 1) ** 1.4
    core = np.clip(1.0 - across / np.maximum(half * 0.18, 1e-4), 0, 1) * (half > 0.02)
    # 옆으로 긁힌 서리 줄 몇 개(띠 안쪽, 길이·위치 제각각)
    scratches = np.zeros_like(x)
    for _ in range(9):
        offset = rng.uniform(-0.75, 0.75)
        start, end = sorted(rng.uniform(0.1, 0.95, 2))
        line = np.clip(1.0 - np.abs(across * np.sign(x - 0.5) - offset * np.clip(along / 0.85, 0.2, 1)) / 0.015, 0, 1)
        scratches = np.maximum(scratches, line * ((along > start) & (along < end)) * (body > 0.05) * rng.uniform(0.4, 0.8))
    sparkle = np.zeros_like(x)
    for _ in range(160):
        t = rng.uniform(0.05, 0.95)
        side = rng.normal(scale=0.35) * (0.08 + 0.3 * min(t / 0.85, 1.0))
        px, py = int((0.5 + side / 2) * SIZE), int((1.0 - t) * SIZE)
        size = rng.uniform(1.2, 3.2)
        x0, x1, y0, y1 = max(px - 5, 0), min(px + 6, SIZE), max(py - 5, 0), min(py + 6, SIZE)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        sparkle[y0:y1, x0:x1] = np.maximum(sparkle[y0:y1, x0:x1], np.clip(size - np.hypot(xx - px, yy - py), 0, 1))
    red = np.maximum.reduce([core, body * 0.7, scratches, sparkle])
    glow = blur(np.maximum(core, body), 0.025) * 1.3
    save('T_Aurora_DashStreak', red, glow, along)


def jagged_lines(paths, glow_blur):
    # 꺾인 선 여럿(paths = [(점들 [(x, y) 0~1], 굵기들, 밝기)])을 두 배 크기로 그려 줄인다(가장자리 계단 방지).
    # 돌려주는 것: 선(R) · 선 둘레에 넓게 깔리는 파인 자리(G용)
    big = SIZE * 2
    core = Image.new('L', (big, big), 0)
    trench = Image.new('L', (big, big), 0)
    draw_core = ImageDraw.Draw(core)
    draw_trench = ImageDraw.Draw(trench)
    for points, widths, strength in paths:
        for (x0, y0), (x1, y1), w0, w1 in zip(points, points[1:], widths, widths[1:]):
            width = 0.5 * (w0 + w1)
            for draw, scale, value in ((draw_trench, 2.6, 255), (draw_core, 1.0, int(255 * strength))):
                pixels = max(int(width * scale * big), 1)
                draw.line([(x0 * big, y0 * big), (x1 * big, y1 * big)], fill=value, width=pixels)
                radius = pixels / 2
                draw.ellipse([x1 * big - radius, y1 * big - radius, x1 * big + radius, y1 * big + radius], fill=value)
    core = np.asarray(core.resize((SIZE, SIZE), Image.LANCZOS), np.float32) / 255.0
    trench = np.asarray(trench.resize((SIZE, SIZE), Image.LANCZOS), np.float32) / 255.0
    return core, blur(trench, glow_blur)


def walk(rng, start, heading, step, steps, wiggle):
    # 각도를 조금씩 꺾으며 나아가는 금 하나(그림 좌표 0~1, heading = 라디안)
    points = [start]
    x, y = start
    for _ in range(steps):
        heading += rng.normal(scale=wiggle)
        x, y = x + step * math.cos(heading), y + step * math.sin(heading)
        points.append((x, y))
    return points, heading


def slash_scar(radius, angle, along, inside):
    # Q 여전사풍 시안 3(10-19 저녁 「너무 공주 같다, 여전사 같은 느낌」): 칼이 바닥을 베고 지나간 자국. 검기 날 조금 안쪽(반경 0.72)을
    # 따라 파인 홈(G = 어둡게 깔리는 파인 자리)과 그 양쪽에 하얗게 부서진 서리 가장자리·튄 조각(R). 양끝은 가늘게 사라진다.
    rng = np.random.default_rng(21)
    paths = []
    count = 90
    for lane, (offset, strength, base) in enumerate(((0.0, 1.0, 0.012), (0.022, 0.55, 0.004), (-0.02, 0.45, 0.0035))):
        points, widths = [], []
        bend = 0.0
        for index in range(count + 1):
            t = -HALF_ANGLE * 0.96 + 2 * HALF_ANGLE * 0.96 * index / count
            bend = 0.7 * bend + rng.normal(scale=0.004)
            r = 0.72 + offset + bend
            points.append((0.5 + r * 0.5 * math.sin(t), 0.5 - r * 0.5 * math.cos(t)))
            taper = max(math.cos(t / HALF_ANGLE * math.pi / 2), 0.0) ** 0.8
            widths.append(base * taper * rng.uniform(0.6, 1.3))
        if lane == 0:
            paths.append((points, widths, strength))
        else:
            # 곁 긁힘은 군데군데 끊긴다
            start = 0
            while start < count:
                length = int(rng.integers(6, 18))
                if rng.random() < 0.6:
                    paths.append((points[start:start + length], widths[start:start + length], strength))
                start += length + int(rng.integers(3, 10))
    core, trench = jagged_lines(paths, 0.004)
    # 홈 바깥으로 튄 작은 얼음 조각(삼각형 조각)
    chips = Image.new('L', (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(chips)
    for _ in range(120):
        t = rng.uniform(-1, 1) * HALF_ANGLE * 0.9
        r = 0.72 + rng.uniform(0.015, 0.09) * (1 if rng.random() < 0.75 else -0.6)
        cx, cy = (0.5 + r * 0.5 * math.sin(t)) * SIZE, (0.5 - r * 0.5 * math.cos(t)) * SIZE
        size = rng.uniform(1.5, 5.0) * max(math.cos(t / HALF_ANGLE * math.pi / 2), 0.2)
        turn = rng.uniform(0, 2 * math.pi)
        corners = [(cx + size * math.cos(turn + k * 2.2 + rng.normal(scale=0.3)), cy + size * math.sin(turn + k * 2.2)) for k in range(3)]
        draw.polygon(corners, fill=int(255 * rng.uniform(0.5, 1.0)))
    chips = np.asarray(chips, np.float32) / 255.0
    red = np.maximum(core, chips) * inside
    green = np.clip(trench * 1.2, 0, 1) * inside
    save('T_Aurora_SlashScar', red, green, along)


def haste_crack(radius):
    # S 여전사풍 시안 4(10-19 저녁 「Q랑 마찬가지로 여전사 같은 장판기」): 발밑에서 바깥으로 갈라져 나가는 굵은 얼음 균열 일곱 줄기
    # (곁가지는 짧게 둘씩 — 둥글게 도는 금이 없어야 거미줄로 안 보인다, 10-18 Q 균열 「거미줄 같다」), 가운데 짧게 터진 금,
    # 둘레는 군데군데 깨진 굵은 얼음 테두리. R = 금 속(밝게), G = 금 둘레 파인 자리, B = 가운데에서 잰 거리(가운데부터 갈라져 나감).
    rng = np.random.default_rng(31)
    paths = []
    mains = 7
    for index in range(mains):
        heading = 2 * math.pi * index / mains + rng.uniform(-0.25, 0.25)
        start = (0.5 + 0.03 * math.cos(heading), 0.5 + 0.03 * math.sin(heading))
        reach = rng.uniform(0.39, 0.45)
        steps = int(reach / 0.012)
        points, _ = walk(rng, start, heading, 0.012, steps, 0.13)
        widths = [0.012 * (1.0 - 0.75 * k / steps) * rng.uniform(0.7, 1.3) for k in range(steps + 1)]
        paths.append((points, widths, 1.0))
        for _ in range(2):
            at = int(rng.integers(steps // 4, steps * 3 // 4))
            side = rng.choice((-1, 1)) * rng.uniform(0.45, 0.8)
            length = int(rng.integers(5, 11))
            branch, _ = walk(rng, points[at], heading + side, 0.012, length, 0.15)
            branch_widths = [widths[at] * 0.6 * (1.0 - 0.8 * k / length) for k in range(length + 1)]
            paths.append((branch, branch_widths, 0.8))
    # 가운데: 짧게 터진 금
    for index in range(12):
        heading = 2 * math.pi * index / 12 + rng.uniform(-0.2, 0.2)
        length = int(rng.integers(3, 7))
        points, _ = walk(rng, (0.5, 0.5), heading, 0.01, length, 0.2)
        paths.append((points, [0.007 * (1.0 - 0.8 * k / length) for k in range(length + 1)], 0.9))
    paths += broken_rim(rng)
    core, trench = jagged_lines(paths, 0.006)
    red = core
    green = np.clip(trench * 1.2, 0, 1)
    save('T_Aurora_HasteCrack', red, green, np.clip(radius, 0, 1))


def broken_rim(rng):
    # 둘레: 반경 0.93 둘레를 짧게 끊어 가며 도는 깨진 얼음 테두리(조각마다 길이·굵기·밝기가 다르고 반경이 들쭉날쭉) +
    # 테두리에서 안쪽으로 짧게 갈라진 금. 매끈한 원 띠는 마법진처럼 보였다(첫 그림).
    paths = []
    first = rng.uniform(0, 2 * math.pi)
    turn = first
    while turn < first + 2 * math.pi - 0.1:
        length = int(rng.integers(6, 22))
        arc, widths = [], []
        bend = rng.normal(scale=0.006)
        for _ in range(length + 1):
            bend = 0.85 * bend + rng.normal(scale=0.0025)
            r = 0.465 + bend
            arc.append((0.5 + r * math.sin(turn), 0.5 - r * math.cos(turn)))
            widths.append(rng.uniform(0.004, 0.011))
            turn += 0.012 / 0.465
        paths.append((arc, widths, rng.uniform(0.6, 0.95)))
        turn += rng.uniform(0.04, 0.16)
    for _ in range(14):
        at = rng.uniform(0, 2 * math.pi)
        start = (0.5 + 0.462 * math.sin(at), 0.5 - 0.462 * math.cos(at))
        inward = math.atan2(-(start[1] - 0.5), -(start[0] - 0.5))
        length = int(rng.integers(2, 6))
        points, _ = walk(rng, start, inward + rng.uniform(-0.4, 0.4), 0.011, length, 0.25)
        paths.append((points, [0.006 * (1.0 - 0.8 * k / length) for k in range(length + 1)], 0.75))
    return paths


def straight_crack(rng, start, heading, step, steps, wiggle, pull=0.6):
    # 정해진 방향(heading)을 크게 벗어나지 않고 들쭉날쭉 나아가는 금(눈송이 팔·가지용)
    points = [start]
    x, y = start
    drift = 0.0
    for _ in range(steps):
        drift = pull * drift + rng.normal(scale=wiggle)
        x, y = x + step * math.cos(heading + drift), y + step * math.sin(heading + drift)
        points.append((x, y))
    return points


def haste_flake_crack(radius):
    # S 시안 5(10-19 저녁 「그래도 눈 모양 유지하면서 거친 느낌 살릴 수 없을까」): 지금 눈송이 장판의 짜임(여섯 팔 + 팔마다 양쪽으로
    # 비스듬한 가지 셋 + 끝 갈래)을 시안 4의 얼음 균열 선(들쭉날쭉·끝으로 가늘어짐·파인 자리)으로 그리고, 둘레는 시안 4의 깨진 테두리.
    # R = 금 속, G = 금 둘레 파인 자리, B = 가운데에서 잰 거리(가운데부터 갈라져 나감).
    rng = np.random.default_rng(41)
    paths = []
    step = 0.01
    for arm in range(6):
        heading = math.radians(-90 + 60 * arm) + rng.uniform(-0.05, 0.05)
        start = (0.5 + 0.02 * math.cos(heading), 0.5 + 0.02 * math.sin(heading))
        steps = int(rng.uniform(0.41, 0.44) / step)
        points = straight_crack(rng, start, heading, step, steps, 0.09)
        widths = [0.012 * (1.0 - 0.7 * k / steps) * rng.uniform(0.75, 1.25) for k in range(steps + 1)]
        paths.append((points, widths, 1.0))
        # 팔 가운데쯤부터 양쪽으로 비스듬한 가지 셋(바깥으로 갈수록 짧게)
        for at, length in ((0.32, 0.12), (0.52, 0.1), (0.7, 0.07)):
            index = int(at * steps)
            for side in (-1, 1):
                reach = length * rng.uniform(0.8, 1.15)
                count = max(int(reach / step), 2)
                twig = straight_crack(rng, points[index], heading + side * math.radians(rng.uniform(52, 62)), step, count, 0.12)
                paths.append((twig, [widths[index] * 0.65 * (1.0 - 0.8 * k / count) for k in range(count + 1)], 0.85))
        # 팔 끝 갈래
        for side in (-1, 1):
            twig = straight_crack(rng, points[-3], heading + side * math.radians(35), step, 4, 0.15)
            paths.append((twig, [0.004 * (1.0 - 0.7 * k / 4) for k in range(5)], 0.8))
    # 가운데: 짧게 터진 금
    for index in range(8):
        heading = 2 * math.pi * index / 8 + rng.uniform(-0.2, 0.2)
        length = int(rng.integers(3, 6))
        points, _ = walk(rng, (0.5, 0.5), heading, 0.01, length, 0.2)
        paths.append((points, [0.007 * (1.0 - 0.8 * k / length) for k in range(length + 1)], 0.9))
    paths += broken_rim(rng)
    core, trench = jagged_lines(paths, 0.006)
    save('T_Aurora_HasteFlakeCrack', core, np.clip(trench * 1.2, 0, 1), np.clip(radius, 0, 1))


def rim_cracks_between_rings(rng, lane_width, cross_count, cross_width, inward_count, inward_steps, inward_width):
    # 눈송이 장판(T_Aurora_Snowflake)의 두 고리(그림 반경 0.49 · 0.455) 자리가 깨진 금: 두 고리 사이를 따라 도는 금(군데군데 끊김) +
    # 두 고리를 비스듬히 가로지르는 짧은 금(고리가 조각조각 갈라진 것처럼) + 안쪽 고리에서 안으로 갈라진 금
    paths = []
    first = rng.uniform(0, 2 * math.pi)
    turn = first
    while turn < first + 2 * math.pi - 0.05:
        length = int(rng.integers(10, 30))
        arc, widths = [], []
        bend = rng.normal(scale=0.004)
        for _ in range(length + 1):
            bend = 0.8 * bend + rng.normal(scale=0.0022)
            r = 0.4725 + bend
            arc.append((0.5 + r * math.sin(turn), 0.5 - r * math.cos(turn)))
            widths.append(rng.uniform(*lane_width))
            turn += 0.01 / 0.4725
        if rng.random() < 0.85:
            paths.append((arc, widths, rng.uniform(0.7, 1.0)))
        turn += rng.uniform(0.02, 0.08)
    for index in range(cross_count):
        at = 2 * math.pi * index / cross_count + rng.uniform(-0.06, 0.06)
        start_r = rng.uniform(0.435, 0.445)
        start = (0.5 + start_r * math.sin(at), 0.5 - start_r * math.cos(at))
        outward = math.atan2(start[1] - 0.5, start[0] - 0.5)
        steps = int(rng.integers(4, 6))
        points = straight_crack(rng, start, outward + rng.uniform(-0.5, 0.5), 0.01, steps, 0.2)
        paths.append((points, [cross_width * (1.0 - 0.6 * k / steps) for k in range(steps + 1)], 0.85))
    for _ in range(inward_count):
        at = rng.uniform(0, 2 * math.pi)
        start = (0.5 + 0.452 * math.sin(at), 0.5 - 0.452 * math.cos(at))
        inward = math.atan2(-(start[1] - 0.5), -(start[0] - 0.5))
        steps = int(rng.integers(*inward_steps))
        points, _ = walk(rng, start, inward + rng.uniform(-0.5, 0.5), 0.011, steps, 0.3)
        paths.append((points, [inward_width * (1.0 - 0.7 * k / steps) for k in range(steps + 1)], 0.75))
    return paths


def rim_crack(angle):
    # S 시안 6(10-19 밤 「S는 롤백하고, 기존 원에 깨진 듯한 이펙트 추가」): 시안 3 눈송이 장판의 고리 자리가 가늘게 깨진 금.
    # 장판과 같은 밝은 얼음빛으로 은은하게 빛난다. R = 금, G = 금 둘레 옅은 빛, B = 앞에서 잰 각도(앞부터 양옆으로 번져 뒤에서 만남).
    rng = np.random.default_rng(51)
    paths = rim_cracks_between_rings(rng, (0.0022, 0.0045), 30, 0.0035, 16, (3, 8), 0.003)
    core, trench = jagged_lines(paths, 0.005)
    save('T_Aurora_RimCrack', core, np.clip(trench * 1.2, 0, 1), np.abs(angle) / math.pi)


def rim_shatter(angle):
    # S 시안 7: 6보다 굵게 깨진 테두리 — 금이 굵고 둘레가 파인 자리로 어둡게 깔리며(Q 벤 자국·시안 4와 같은 여전사풍), 안쪽으로 길게
    # 갈라진 금과 고리 둘레로 튄 얼음 조각이 더 있다. B = 앞에서 잰 각도.
    rng = np.random.default_rng(61)
    paths = rim_cracks_between_rings(rng, (0.005, 0.011), 22, 0.007, 14, (8, 16), 0.008)
    core, trench = jagged_lines(paths, 0.006)
    chips = Image.new('L', (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(chips)
    for _ in range(160):
        t = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.43, 0.497)
        cx, cy = (0.5 + r * math.sin(t)) * SIZE, (0.5 - r * math.cos(t)) * SIZE
        size = rng.uniform(1.5, 5.0)
        turn = rng.uniform(0, 2 * math.pi)
        corners = [(cx + size * math.cos(turn + k * 2.2 + rng.normal(scale=0.3)), cy + size * math.sin(turn + k * 2.2)) for k in range(3)]
        draw.polygon(corners, fill=int(255 * rng.uniform(0.5, 1.0)))
    chips = np.asarray(chips, np.float32) / 255.0
    save('T_Aurora_RimShatter', np.maximum(core, chips), np.clip(trench * 1.2, 0, 1), np.abs(angle) / math.pi)


def rupture_crack():
    # D 시안 2·3(10-19 밤 「D 방향은 괜찮은데 이펙트가 아쉽다」): 얼음 바위가 차례로 터지는 줄을 따라 바닥이 갈라진 자국.
    # 데칼은 줄 길이만 한 정사각형 — 그림 아래 = 시전자 발밑, 위 = 줄 끝(B = 0 → 1). 가운데를 세로로 들쭉날쭉 오르는 굵은 금(발밑은 가늘고
    # 가운데가 굵고 끝으로 가늘어짐) + 양옆으로 짧게 갈라진 금 + 곁에 끊겨 달리는 가는 금 + 튄 조각. G = 파인 자리(Q 벤 자국처럼 어둡게).
    rng = np.random.default_rng(71)
    paths = []
    points, widths = [], []
    x, y, drift = 0.5, 0.93, 0.0
    while y > 0.04:
        t = (0.93 - y) / 0.89
        points.append((x, y))
        widths.append((0.004 + 0.009 * min(t / 0.15, 1.0) * (1.0 - 0.65 * t)) * rng.uniform(0.75, 1.25))
        drift = 0.75 * drift + rng.normal(scale=0.004)
        x = 0.5 + float(np.clip(x - 0.5 + drift, -0.022, 0.022))
        y -= 0.008
    paths.append((points, widths, 1.0))
    # 양옆으로 갈라진 금(위쪽 = 앞으로 비스듬히)
    for index in range(4, len(points) - 4, 5):
        if rng.random() < 0.3:
            continue
        side = rng.choice((-1, 1))
        heading = -math.pi / 2 + side * math.radians(rng.uniform(50, 80))
        steps = int(rng.integers(3, 8))
        twig = straight_crack(rng, points[index], heading, 0.008, steps, 0.2)
        paths.append((twig, [widths[index] * 0.6 * (1.0 - 0.8 * k / steps) for k in range(steps + 1)], 0.85))
    # 곁에 끊겨 달리는 가는 금
    for offset in (-0.03, 0.03):
        start = int(rng.integers(3, 12))
        while start < len(points) - 4:
            length = int(rng.integers(5, 14))
            if rng.random() < 0.55:
                lane = [(px + offset + rng.normal(scale=0.003), py) for px, py in points[start:start + length]]
                paths.append((lane, [w * 0.35 for w in widths[start:start + length]], 0.6))
            start += length + int(rng.integers(4, 12))
    core, trench = jagged_lines(paths, 0.004)
    chips = Image.new('L', (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(chips)
    for _ in range(140):
        px, py = points[int(rng.integers(0, len(points)))]
        cx, cy = (px + rng.normal(scale=0.03)) * SIZE, (py + rng.normal(scale=0.01)) * SIZE
        size = rng.uniform(1.5, 4.5)
        turn = rng.uniform(0, 2 * math.pi)
        corners = [(cx + size * math.cos(turn + k * 2.2 + rng.normal(scale=0.3)), cy + size * math.sin(turn + k * 2.2)) for k in range(3)]
        draw.polygon(corners, fill=int(255 * rng.uniform(0.5, 1.0)))
    chips = np.asarray(chips, np.float32) / 255.0
    along = np.clip(1.0 - (np.mgrid[0:SIZE, 0:SIZE][0] + 0.5) / SIZE, 0, 1)
    save('T_Aurora_RuptureCrack', np.maximum(core, chips), np.clip(trench * 1.2, 0, 1), along)


def impact_crack(radius):
    # F 시안 2·3(10-19 밤 「F 방향은 괜찮은데 이펙트가 아쉽다」): 얼음 칼날이 꽂힌 자리 바닥이 별 모양으로 갈라진 자국 — 가운데 움푹
    # 파인 자리 + 아홉 갈래 굵은 금(곁가지 하나씩). 둘레 테두리는 없다. R = 금, G = 파인 자리, B = 가운데에서 잰 거리.
    rng = np.random.default_rng(81)
    paths = []
    for index in range(9):
        heading = 2 * math.pi * index / 9 + rng.uniform(-0.2, 0.2)
        start = (0.5 + 0.04 * math.cos(heading), 0.5 + 0.04 * math.sin(heading))
        steps = int(rng.uniform(0.3, 0.45) / 0.014)
        # 방향을 크게 벗어나지 않게(walk로 그었더니 꺾임이 쌓여 금들이 세 갈래로 몰렸다)
        points = straight_crack(rng, start, heading, 0.014, steps, 0.12)
        widths = [0.02 * (1.0 - 0.8 * k / steps) * rng.uniform(0.7, 1.3) for k in range(steps + 1)]
        paths.append((points, widths, 1.0))
        at = int(rng.integers(steps // 3, steps * 2 // 3 + 1))
        length = int(rng.integers(3, 7))
        branch, _ = walk(rng, points[at], heading + rng.choice((-1, 1)) * rng.uniform(0.5, 0.9), 0.014, length, 0.2)
        paths.append((branch, [widths[at] * 0.6 * (1.0 - 0.8 * k / length) for k in range(length + 1)], 0.85))
    core, trench = jagged_lines(paths, 0.008)
    crater = np.clip(1.0 - radius / 0.22, 0, 1) ** 1.5
    save('T_Aurora_ImpactCrack', core, np.clip(np.maximum(trench * 1.2, crater), 0, 1), np.clip(radius, 0, 1))


def flake_sprite():
    # Q 흩날리는 눈송이(10-19 「뭔가 흩날리는 이펙트」)에 붙이는 작은 그림: 가는 여섯 갈래 눈송이 + 둥근 빛(R만 쓴다).
    size = 256
    y, x = (np.mgrid[0:size, 0:size] + 0.5) / size - 0.5
    radius = np.hypot(x, y) * 2.0
    angle = np.arctan2(x, -y)
    arms = np.abs(np.angle(np.exp(1j * angle * 6.0))) / 6.0  # 가장 가까운 팔까지 각도
    arm = np.clip(1.0 - arms * radius / 0.035, 0, 1) * np.clip((0.9 - radius) / 0.1, 0, 1)
    # 팔 가운데쯤 작은 곁가지
    twig_angle = np.abs(np.angle(np.exp(1j * (angle * 6.0 + np.pi / 2)))) / 6.0
    twig = np.clip(1.0 - twig_angle * radius / 0.02, 0, 1) * np.exp(-((radius - 0.5) / 0.08) ** 2)
    glow = np.exp(-(radius / 0.35) ** 2)
    red = np.clip(np.maximum.reduce([arm, twig * 0.8, glow * 0.6]), 0, 1)
    FOLDER.mkdir(parents=True, exist_ok=True)
    packed = np.stack([red, red, red], axis=-1)
    Image.fromarray((packed * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / 'T_Aurora_FlakeSprite.png')
    print(FOLDER / 'T_Aurora_FlakeSprite.png')


def main():
    flake_sprite()
    dash_streak()
    radius, angle = polar()
    inside = np.abs(angle) <= HALF_ANGLE
    along = np.clip((angle + HALF_ANGLE) / (2 * HALF_ANGLE), 0, 1)
    slash_arc(radius, angle, along, inside)
    slash_wave(radius, angle, along, inside)
    slash_rough(radius, angle, along, inside)
    slash_flip(radius, angle, along, inside)
    nova_ring(radius, angle)
    rougher(radius, angle, along, inside)
    frost_sweep(radius, angle, along, inside)
    spin_ring(radius, angle)
    spin_frost(radius, angle)
    slash_scar(radius, angle, along, inside)
    haste_crack(radius)
    haste_flake_crack(radius)
    rim_crack(angle)
    rim_shatter(angle)
    rupture_crack()
    impact_crack(radius)


if __name__ == '__main__':
    main()
