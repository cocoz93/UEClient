"""Draw the snow cover mask for Aurora's Q trail marks (option 3, 2026-10-19 「거미줄 같다 → 새하얀 눈이 덮인 느낌」).
Writes SourceArt/Aurora/T_Aurora_SnowCover.png; aurora_frost_materials_build.py imports it as a texture.
R = where snow lies (a lumpy patch made of overlapping soft blobs with a fluffy, noise-eaten edge and slight lumps inside),
G = loose snow dust around it (fine flecks thinning out with distance plus a soft fringe). B unused.
Several marks overlap along the slash arc, each turned at random, so the patch is deliberately irregular, not round."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

SIZE = 1024
OUT = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora' / 'T_Aurora_SnowCover.png'


def value_noise(rng, cells):
    # 거친 무작위 격자를 부드럽게 키운 잡음(0~1)
    grid = Image.fromarray((rng.random((cells, cells)) * 255).astype(np.uint8))
    return np.asarray(grid.resize((SIZE, SIZE), Image.BICUBIC), np.float32) / 255.0


def main():
    rng = np.random.default_rng(5)
    y, x = (np.mgrid[0:SIZE, 0:SIZE] + 0.5) / SIZE - 0.5
    field = np.zeros((SIZE, SIZE), np.float32)
    # 가운데에 몰린 부드러운 덩어리 여럿을 겹친다(가운데일수록 크다)
    for _ in range(36):
        cx, cy = rng.normal(scale=0.12, size=2)
        r = 0.05 + 0.09 * np.exp(-(cx * cx + cy * cy) / 0.02) + rng.uniform(0, 0.03)
        field += np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (r * r))
    fluff = 0.55 * value_noise(rng, 24) + 0.3 * value_noise(rng, 64) + 0.15 * value_noise(rng, 160)
    edge = field + (fluff - 0.5) * 0.9
    snow = np.clip((edge - 0.55) / 0.35, 0, 1)
    snow = snow * snow * (3 - 2 * snow)  # 부드러운 계단
    # 안쪽 울퉁불퉁함(격자 잡음은 네모가 비쳐 한 번 흐린다)
    bumps = Image.fromarray((value_noise(rng, 40) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SIZE * 0.008))
    lumps = 0.84 + 0.16 * np.asarray(bumps, np.float32) / 255.0
    lines = snow * lumps
    # 눈가루: 덩어리 둘레로 갈수록 드물어지는 작은 점 + 덩어리를 넓게 번진 띠
    dust = np.zeros_like(field)
    reach = np.clip(field * 1.6, 0, 1)
    count = 2600
    px = rng.integers(0, SIZE, count)
    py = rng.integers(0, SIZE, count)
    keep = rng.random(count) < reach[py, px] * 0.9
    for cx, cy in zip(px[keep], py[keep]):
        radius = rng.uniform(1.0, 3.2)
        x0, x1 = max(int(cx - 4), 0), min(int(cx + 5), SIZE)
        y0, y1 = max(int(cy - 4), 0), min(int(cy + 5), SIZE)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dot = np.clip(radius - np.hypot(xx - cx, yy - cy), 0, 1)
        dust[y0:y1, x0:x1] = np.maximum(dust[y0:y1, x0:x1], dot * rng.uniform(0.5, 1.0))
    fringe = np.asarray(Image.fromarray((snow * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(SIZE * 0.03)), np.float32) / 255.0
    glow = np.clip(np.maximum(dust, fringe * 0.7), 0, 1)
    # 사각 데칼 가장자리에 닿지 않게 바깥은 0으로 모은다
    vignette = np.clip((0.5 - np.hypot(x, y)) / 0.08, 0, 1)
    packed = np.stack([lines * vignette, glow * vignette, np.zeros_like(field)], axis=-1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((packed * 255 + 0.5).astype(np.uint8), 'RGB').save(OUT)
    print(OUT)


if __name__ == '__main__':
    main()
