"""Draw pattern drafts for Aurora's A shell in place of the honeycomb (2026-10-21 「A 육각형 대신에 어떤 무늬 그리면 좋을까? 아님 그냥
아무것도 그리지 말까? 이것도 시안 여러 개」). Same sphere UV and channels as aurora_honeycomb_texture.py (engine sphere: v = polar angle /
pi from the top pole, u = 1 - (atan2(y, x) + 90 deg) / 360; R = faint fill, G = lines, B = a fainter line), so the same shell material
(build_honey) shows them:
- Crack: jagged branching frost cracks.
- Fern: feathery hoarfrost fronds (window frost) - curving stems with barbs on both sides.
- Flake: a dozen thin snowflakes of mixed sizes.
- Shard: tall thin ice shards rising from below the middle towards the top, all round (outline + centre line, faint fill).
Features sit mostly on the side the game camera sees (pitch -50, yaw 45 - the shell does not turn) and stay out of the middle of the
picture where the body stands (like the honeycomb's --clear-centre 0.45); a few go round the back (the shell is two-sided).
Usage: python aurora_shell_patterns.py [crack fern flake shard] [--preview DIR]. Writes SourceArt/Aurora/T_Aurora_Shell_<Name>.png (2048 x 1024)."""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

WIDTH, HEIGHT = 2048, 1024
FOLDER = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora'
# 선 반폭(라디안) — 보호막 반지름 105cm에서 약 0.85cm(육각 테두리는 경계 양쪽 0.011씩)
LINE = 0.008
TEXEL = math.pi / HEIGHT


def camera_axes():
    # aurora_honeycomb_texture.py와 같다: 보는 방향, 화면 오른쪽, 화면 위쪽
    pitch, yaw = math.radians(50.0), math.radians(45.0)
    view = np.array([math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch)])
    right = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
    up = np.cross(right, view)
    up /= np.linalg.norm(up)
    return view, right, up if up[2] > 0 else -up


VIEW, RIGHT, UP = camera_axes()


def seen_at(sx, sy, back=False):
    # 화면 (sx, sy)(구 반지름 단위)에 보이는 앞면(back이면 뒷면) 구 위 점
    depth = math.sqrt(max(1.0 - sx * sx - sy * sy, 0.0)) * (1.0 if back else -1.0)
    p = sx * RIGHT + sy * UP + depth * VIEW
    return p / np.linalg.norm(p)


def seeds(rng, front, back, inner=0.5, outer=0.93):
    # 화면 가운데(몸)를 비우고 둘레 띠에 고르게(각을 나눠 흔들어) 앞면 front개 + 뒷면 back개
    points = []
    for count, is_back in ((front, False), (back, True)):
        start = rng.uniform(0, 2 * math.pi)
        for i in range(count):
            a = start + 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / max(count, 1)
            r = rng.uniform(inner, outer)
            points.append(seen_at(r * math.cos(a), r * math.sin(a), is_back))
    return points


def tangent_towards(p, direction):
    t = direction - p * (p @ direction)
    return t / np.linalg.norm(t)


def step(p, t, angle):
    # 대원을 따라 angle만큼 가고 방향도 같이 옮긴다
    q = p * math.cos(angle) + t * math.sin(angle)
    u = -p * math.sin(angle) + t * math.cos(angle)
    return q / np.linalg.norm(q), u / np.linalg.norm(u)


def turn(p, t, angle):
    return t * math.cos(angle) + np.cross(p, t) * math.sin(angle)


class Sheet:
    def __init__(self):
        self.lines = []  # (a, b, half width, channel)
        self.fill = Image.new('L', (WIDTH, HEIGHT), 0)

    def add(self, a, b, half=LINE, channel=1):
        self.lines.append((np.asarray(a, float), np.asarray(b, float), half, channel))

    def polyline(self, points, half=LINE, channel=1):
        for a, b in zip(points, points[1:]):
            self.add(a, b, half, channel)

    def render(self):
        v = (np.arange(HEIGHT) + 0.5) / HEIGHT
        u = (np.arange(WIDTH) + 0.5) / WIDTH
        theta = v * math.pi
        phi = np.radians(-90.0 + (1.0 - u) * 360.0)
        out = np.zeros((HEIGHT, WIDTH, 3), np.float32)
        out[..., 0] = np.asarray(self.fill, np.float32) / 255.0
        for a, b, half, channel in self.lines:
            mid = (a + b) / 2
            reach = np.linalg.norm(b - a) / 2 + half + 3 * TEXEL
            centre = math.acos(np.clip(mid[2] / np.linalg.norm(mid), -1, 1))
            top, bottom = max(0, int((centre - reach) / math.pi * HEIGHT) - 1), min(HEIGHT, int((centre + reach) / math.pi * HEIGHT) + 2)
            if top >= bottom:
                continue
            t = theta[top:bottom][:, None]
            d = np.stack([np.sin(t) * np.cos(phi)[None, :], np.sin(t) * np.sin(phi)[None, :],
                          np.broadcast_to(np.cos(t), (bottom - top, WIDTH))], axis=-1)
            ab = b - a
            k = np.clip(((d - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
            gap = np.linalg.norm(d - (a + k[..., None] * ab), axis=-1)
            value = np.clip((half - gap) / TEXEL + 0.5, 0, 1)
            out[top:bottom, :, channel] = np.maximum(out[top:bottom, :, channel], value)
        return out


def crack(sheet, rng):
    # 들쭉날쭉 갈라지는 균열: 씨앗마다 두세 줄, 걸음마다 ±20도 꺾이고 가끔 갈래가 난다(두 단계까지)
    def walk(p, t, steps, depth):
        points = [p]
        for _ in range(steps):
            t = turn(p, t, rng.uniform(-0.35, 0.35))
            p, t = step(p, t, rng.uniform(0.035, 0.06))
            points.append(p)
            if depth < 2 and rng.random() < 0.22:
                walk(p, turn(p, t, rng.choice([-1, 1]) * rng.uniform(0.5, 1.0)), max(3, steps // 2), depth + 1)
        sheet.polyline(points, LINE * (1.0 - 0.25 * depth))

    for seed in seeds(rng, 7, 3):
        for _ in range(rng.integers(2, 4)):
            t = turn(seed, tangent_towards(seed, rng.normal(size=3)), 0.0)
            walk(seed, t, int(rng.integers(8, 14)), 0)


def fern(sheet, rng):
    # 성에(창에 낀 서리) 잎: 한쪽으로 휘는 줄기 + 양옆으로 비스듬한 잔가지(끝으로 갈수록 짧게), 가끔 곁줄기
    def frond(p, t, steps, bend, size, depth):
        stem = [p]
        for i in range(steps):
            t = turn(p, t, bend + rng.uniform(-0.05, 0.05))
            p, t = step(p, t, 0.05 * size)
            stem.append(p)
            barb = 0.11 * size * (1.0 - i / steps) + 0.02
            for side in (-1, 1):
                q, _ = step(p, turn(p, t, side * math.radians(48)), barb)
                sheet.add(p, q, LINE * 0.7)
            if depth == 0 and i == steps // 3:
                frond(p, turn(p, t, rng.choice([-1, 1]) * 0.9), steps // 2, -bend, size * 0.7, 1)
        sheet.polyline(stem, LINE)

    for seed in seeds(rng, 7, 3):
        t = tangent_towards(seed, rng.normal(size=3))
        frond(seed, t, int(rng.integers(11, 16)), rng.choice([-1, 1]) * 0.06, rng.uniform(0.9, 1.2), 0)


def flake(sheet, rng):
    # 가는 눈꽃: 팔 여섯 + 팔마다 곁가지 두 쌍 + 가운데 육각 고리
    for index, centre in enumerate(seeds(rng, 9, 3, inner=0.5, outer=0.9)):
        radius = rng.uniform(0.11, 0.2)
        start = tangent_towards(centre, rng.normal(size=3))
        for arm in range(6):
            t = turn(centre, start, math.radians(60 * arm))
            tip, _ = step(centre, t, radius)
            sheet.add(centre, tip)
            for at, length in ((0.45, 0.32), (0.7, 0.2)):
                p, along = step(centre, t, radius * at)
                for side in (-1, 1):
                    q, _ = step(p, turn(p, along, side * math.radians(55)), radius * length)
                    sheet.add(p, q, LINE * 0.8)
        ring = []
        for k in range(7):
            p, _ = step(centre, turn(centre, start, math.radians(60 * k + 30)), radius * 0.22)
            ring.append(p)
        sheet.polyline(ring, LINE * 0.8)


def shard(sheet, rng):
    # 아래(적도 밑)에서 위로 솟은 가는 얼음 결: 둘레 22개, 높이·폭 제각각. 테두리 + 가운데 선, 안은 옅게 채움(R)
    draw = ImageDraw.Draw(sheet.fill)
    count = 22
    for i in range(count):
        azimuth = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / count
        base = math.pi * rng.uniform(0.6, 0.68)
        top = math.pi * rng.uniform(0.2, 0.4)
        half = rng.uniform(0.05, 0.09)

        def at(theta, phi):
            return np.array([math.sin(theta) * math.cos(phi), math.sin(theta) * math.sin(phi), math.cos(theta)])

        left, tip, right = at(base, azimuth - half), at(top, azimuth + rng.uniform(-0.03, 0.03)), at(base, azimuth + half)
        steps = [k / 6 for k in range(7)]
        edge_l = [left * (1 - s) + tip * s for s in steps]
        edge_r = [right * (1 - s) + tip * s for s in steps]
        sheet.polyline([p / np.linalg.norm(p) for p in edge_l])
        sheet.polyline([p / np.linalg.norm(p) for p in edge_r])
        mid = (left + right) / 2
        sheet.polyline([p / np.linalg.norm(p) for p in [mid * (1 - s) + tip * s for s in steps]], LINE * 0.6)

        def uv(p):
            p = p / np.linalg.norm(p)
            theta = math.acos(np.clip(p[2], -1, 1))
            phi = math.degrees(math.atan2(p[1], p[0]))
            u = 1.0 - ((phi + 90.0) % 360.0) / 360.0
            return u * WIDTH, theta / math.pi * HEIGHT

        outline = [uv(p) for p in edge_l] + [uv(p) for p in reversed(edge_r)]
        us = [x for x, _ in outline]
        if max(us) - min(us) > WIDTH / 2:  # u 이음매를 넘는 결은 양쪽에 한 번씩
            draw.polygon([(x + WIDTH if x < WIDTH / 2 else x, y) for x, y in outline], fill=140)
            draw.polygon([(x - WIDTH if x > WIDTH / 2 else x, y) for x, y in outline], fill=140)
        else:
            draw.polygon(outline, fill=140)


def preview(sheet_rgb, path):
    # 게임 카메라에서 본 보호막(정사영): 앞면 + 뒷면(0.75) — 재질처럼 G 선을 밝게, R 채움을 옅게
    size = 420
    image = np.full((size, size, 3), 0.1, np.float32)
    ys, xs = np.mgrid[0:size, 0:size]
    sx = (xs + 0.5) / size * 2 - 1
    sy = 1 - (ys + 0.5) / size * 2
    inside = sx * sx + sy * sy < 1
    for depth_sign, weight in ((1.0, 0.75), (-1.0, 1.0)):
        depth = np.sqrt(np.clip(1 - sx * sx - sy * sy, 0, 1)) * depth_sign
        p = sx[..., None] * RIGHT + sy[..., None] * UP + depth[..., None] * VIEW
        theta = np.arccos(np.clip(p[..., 2], -1, 1))
        phi = np.degrees(np.arctan2(p[..., 1], p[..., 0]))
        u = 1.0 - ((phi + 90.0) % 360.0) / 360.0
        col = np.clip((u * WIDTH).astype(int), 0, WIDTH - 1)
        row = np.clip((theta / math.pi * HEIGHT).astype(int), 0, HEIGHT - 1)
        texel = sheet_rgb[row, col]
        glow = np.clip(texel[..., 1] * 0.9 + texel[..., 0] * 0.25, 0, 1) * weight
        image += (glow * inside)[..., None] * np.array([0.5, 0.8, 1.0])
    Image.fromarray((np.clip(image, 0, 1) * 255).astype(np.uint8)).save(path)


PATTERNS = {'crack': crack, 'fern': fern, 'flake': flake, 'shard': shard}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('names', nargs='*', default=list(PATTERNS))
    parser.add_argument('--preview')
    args = parser.parse_args()
    FOLDER.mkdir(parents=True, exist_ok=True)
    for name in args.names:
        sheet = Sheet()
        PATTERNS[name](sheet, np.random.default_rng(21))
        rgb = sheet.render()
        out = FOLDER / f'T_Aurora_Shell_{name.capitalize()}.png'
        Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(out)
        print(out, 'lines', len(sheet.lines))
        if args.preview:
            Path(args.preview).mkdir(parents=True, exist_ok=True)
            preview(rgb, Path(args.preview) / f'shell_{name}.png')


if __name__ == '__main__':
    main()
