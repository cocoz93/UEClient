"""Write Aurora's D icicle-rain spear meshes (2026-10-25 「D는 저 꽂히는 얼음 오브젝트가 너무 별로인 것 같은데 다른 거 없어?」 - the
engine cone read as a plain white stick) as OBJ files in centimetres, long axis +Z with the tip at +Z, centred on the origin like the
engine cone so the game places them the same way. Written as x, -y, z for the engine's OBJ importer (it flips handedness, see
aurora_bird_art.py). Every triangle has its own corners so the imported normals stay flat - each facet catches light on its own.
UV: u runs once round the spear, v from the back end (0) to the tip (1) - the layout spline spike materials expect.
- SM_Aurora_IceSpear: one faceted ice crystal 100 long, 10 across at its widest - six uneven sides with ridges, widest a little behind
  the back end and tapering to a needle tip, a broken flat back end.
- SM_Aurora_IceSpearCluster: the same crystal with two short crystals growing off its back third at a slant (same size box for the
  main crystal so the game's width and length stay the same).
Writes into SourceArt/Aurora/Meshes. Usage: python aurora_spear_art.py"""
import math
import random
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora' / 'Meshes'
LENGTH = 100.0
RADIUS = 5.0
SIDES = 6
# 옆모습(뒤 끝 → 끝): (z, 반경 배율) — 뒤 끝은 부러진 듯 평평, 뒤 1/5쯤이 가장 굵고 끝은 바늘
PROFILE = [(-50.0, 0.72), (-41.0, 1.0), (-18.0, 0.86), (12.0, 0.5), (50.0, 0.0)]


def crystal(length, radius, seed, twist=0.35):
    """Triangles + UVs of one faceted crystal along +Z, centred on the origin."""
    rng = random.Random(seed)
    # 면마다 굵기를 조금씩 달리하고(울퉁불퉁한 결정), 꼭짓점은 하나 걸러 바깥으로 — 모서리가 선다
    jitter = [rng.uniform(0.85, 1.12) for _ in range(SIDES)]
    rings = []
    for ring, (z, scale) in enumerate(PROFILE):
        points = []
        for side in range(SIDES + 1):
            k = side % SIDES
            angle = 2.0 * math.pi * side / SIDES + twist * ring
            r = radius * scale * jitter[k] * (1.08 if k % 2 == 0 else 0.94)
            points.append((r * math.cos(angle), r * math.sin(angle), z * length / LENGTH))
        rings.append(points)
    triangles = []
    for ring in range(len(rings) - 1):
        v0 = (PROFILE[ring][0] + 50.0) / 100.0
        v1 = (PROFILE[ring + 1][0] + 50.0) / 100.0
        for side in range(SIDES):
            u0, u1 = side / SIDES, (side + 1) / SIDES
            a, b = rings[ring][side], rings[ring][side + 1]
            c, d = rings[ring + 1][side + 1], rings[ring + 1][side]
            triangles.append(((a, (u0, v0)), (b, (u1, v0)), (c, (u1, v1))))
            if ring + 1 < len(rings) - 1:
                triangles.append(((a, (u0, v0)), (c, (u1, v1)), (d, (u0, v1))))
    # 뒤 끝 평평한 뚜껑
    back = rings[0]
    middle = (0.0, 0.0, PROFILE[0][0] * length / LENGTH)
    for side in range(SIDES):
        triangles.append(((middle, (0.5, 0.0)), (back[side + 1], (0.0, 0.0)), (back[side], (1.0, 0.0))))
    return triangles


def place(triangles, tilt_degrees, yaw_degrees, offset):
    """Rotate a crystal about X by tilt, then about Z by yaw, then move it."""
    tilt, yaw = math.radians(tilt_degrees), math.radians(yaw_degrees)
    moved = []
    for corners in triangles:
        out = []
        for (x, y, z), uv in corners:
            y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
            x, y = x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw)
            out.append(((x + offset[0], y + offset[1], z + offset[2]), uv))
        moved.append(tuple(out))
    return moved


def write_obj(name, triangles):
    FOLDER.mkdir(parents=True, exist_ok=True)
    lines = [f'o {name}']
    for corners in triangles:
        for (x, y, z), _ in corners:
            lines.append(f'v {x:.3f} {-y:.3f} {z:.3f}')
    for corners in triangles:
        for _, (u, v) in corners:
            lines.append(f'vt {u:.4f} {v:.4f}')
    for i in range(len(triangles)):
        lines.append(f'f {3 * i + 1}/{3 * i + 1} {3 * i + 2}/{3 * i + 2} {3 * i + 3}/{3 * i + 3}')
    (FOLDER / f'{name}.obj').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(FOLDER / f'{name}.obj', len(triangles))


def main():
    spear = crystal(LENGTH, RADIUS, seed=7)
    write_obj('SM_Aurora_IceSpear', spear)
    # 곁가지 둘: 본 결정의 뒤 1/3에서 바깥으로 비스듬히(길이 0.42·0.32배) — 박힌 뒤 위로 삐죽 나온 얼음 다발처럼
    side_a = place(crystal(LENGTH * 0.42, RADIUS * 0.75, seed=11), 24.0, 30.0, (0.0, 0.0, -22.0))
    side_b = place(crystal(LENGTH * 0.32, RADIUS * 0.65, seed=13), -20.0, -40.0, (0.0, 0.0, -30.0))
    write_obj('SM_Aurora_IceSpearCluster', spear + side_a + side_b)


if __name__ == '__main__':
    main()
