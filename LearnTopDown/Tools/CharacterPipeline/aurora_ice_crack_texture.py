"""Draw the ice crack mask for Aurora's Q trail marks (option 2) with Pillow, like aurora_snowflake_texture.py.
Writes SourceArt/Aurora/T_Aurora_IceCrack.png; aurora_frost_materials_build.py imports it as a texture.
R = the crack lines, G = a wide soft glow around them (B unused).
Six jagged main cracks from a small broken centre, side branches, and short web links between neighbouring cracks.
The pack's T_IceVeins has hairline veins (1-3 texels of 2048) that turn into grey fog on a 150cm mark at the game camera
(2026-10-18 night), so the lines here are bold enough to stay readable at roughly 110 screen pixels per mark."""
import math
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
OUT = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora' / 'T_Aurora_IceCrack.png'


def main():
    scale = 2  # 두 배로 그려 줄여 가장자리를 매끈하게
    size = SIZE * scale
    centre = size / 2
    rng = random.Random(7)  # 매번 같은 그림
    image = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(image)

    def crack(start, angle, length, width, end_width, wobble=0.35, step=0.035):
        # 짧은 마디를 이어 붙이며 마디마다 각도를 제 방향 둘레로 흔든다(흔들림을 쌓으면 금이 휘어 되돌아온다).
        # 굵기는 끝으로 갈수록 가늘어진다.
        points = [start]
        travelled = 0.0
        while travelled < length:
            heading = angle + rng.uniform(-wobble, wobble)
            piece = size * step * rng.uniform(0.7, 1.3)
            last = points[-1]
            points.append((last[0] + piece * math.cos(heading), last[1] + piece * math.sin(heading)))
            travelled += piece
        for index in range(len(points) - 1):
            t = index / max(len(points) - 2, 1)
            w = width + (end_width - width) * t
            draw.line([points[index], points[index + 1]], fill=255, width=max(int(w), 1))
            draw.ellipse([points[index + 1][0] - w / 2, points[index + 1][1] - w / 2,
                          points[index + 1][0] + w / 2, points[index + 1][1] + w / 2], fill=255)
        return points

    mains = []
    base = rng.uniform(0, math.pi * 2)
    for k in range(6):
        angle = base + math.pi / 3 * k + rng.uniform(-0.25, 0.25)
        points = crack((centre, centre), angle, size * rng.uniform(0.36, 0.46), size * 0.014, size * 0.004)
        mains.append(points)
        # 곁가지 한두 개
        for _ in range(rng.choice((1, 2))):
            at = points[rng.randint(len(points) // 3, max(len(points) * 2 // 3, len(points) // 3 + 1))]
            side = rng.choice((-1, 1))
            crack(at, angle + side * rng.uniform(0.45, 0.8), size * rng.uniform(0.1, 0.18), size * 0.007, size * 0.003)
    # 이웃한 금 사이를 잇는 짧은 거미줄 금(안쪽·바깥쪽 두 겹, 일부만)
    for ring in (0.32, 0.62):
        for k in range(6):
            if rng.random() > 0.65:
                continue
            a, b = mains[k], mains[(k + 1) % 6]
            pa = a[min(int(len(a) * ring), len(a) - 1)]
            pb = b[min(int(len(b) * ring), len(b) - 1)]
            mid = ((pa[0] + pb[0]) / 2 + rng.uniform(-1, 1) * size * 0.02, (pa[1] + pb[1]) / 2 + rng.uniform(-1, 1) * size * 0.02)
            draw.line([pa, mid, pb], fill=255, width=int(size * 0.005), joint='curve')
    # 가운데: 깨진 자리(불규칙한 작은 다각형)
    shard = [(centre + size * rng.uniform(0.018, 0.034) * math.cos(math.pi / 4 * k),
              centre + size * rng.uniform(0.018, 0.034) * math.sin(math.pi / 4 * k)) for k in range(8)]
    draw.polygon(shard, fill=255)
    lines = image.filter(ImageFilter.GaussianBlur(radius=size * 0.0018))
    glow = image.filter(ImageFilter.GaussianBlur(radius=size * 0.014))
    peak = max(glow.getextrema()[1], 1)
    glow = glow.point(lambda v: min(255, v * 255 // peak))
    blank = Image.new('L', (size, size), 0)
    packed = Image.merge('RGB', (lines, glow, blank)).resize((SIZE, SIZE), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    packed.save(OUT)
    print(OUT)


if __name__ == '__main__':
    main()
