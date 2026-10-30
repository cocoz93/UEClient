"""Draw honeycomb ice plate masks for Aurora's A shell (2026-10-19 「육각형이 붙어 있는 벌집 느낌, 빽빽하지 않게 1/3쯤 뒤덮인」).
The engine sphere (/Engine/BasicShapes/Sphere) uses a plain latitude-longitude UV layout (mesh_uv_dump.py: v = polar angle / pi
from the top pole, u = 1 - (atan2(y, x) + 90 deg) / 360), so each texel is turned back into a direction on the sphere. Cells are
the spherical Voronoi regions of evenly spread (Fibonacci) points, which come out almost all hexagons with the same size and no
pole squeeze. A smooth noise picks neighbouring cells together so the covered third grows in attached honeycomb patches.
Cell centres = the vertices of an icosahedron subdivided <frequency> times (10 f^2 + 2 cells: hexagons plus 12 pentagons,
turned so no pentagon sits on the top pole the game camera looks at). Fibonacci points were tried first: their cells came out
as diamonds, not hexagons.
Channels: R = covered plate fill (brighter towards its rim, a little different per cell), G = border of covered cells,
B = a faint border on every cell. Usage: python aurora_honeycomb_texture.py <name> <frequency> [coverage] [upper bias]
[--clear-centre D] [--grow=SX,SY,SIDE,N ...] [--extend=SX,SY,N ...]
Upper bias leans the picked cells towards the top half (the game camera looks down at about 50 degrees): with a fifth covered
and no bias the kept patches happened to sit near the rim, foreshortened and small, leaving the visible front empty.
The last two edit the picked cells as the game camera sees the shell (screen x right, y up, both in shell radii from its
centre): --clear-centre uncovers cells seen closer than D to the centre, --grow covers the N free cells nearest the point
seen at (SX, SY) on the near (front) or far (back) side, --extend grows the front patch seen nearest (SX, SY) by N attached
cells, each time the one furthest from the camera (so it wraps round onto the back). Give them with '=' so a negative SX is not
read as a flag.
Writes SourceArt/Aurora/T_Aurora_Honey_<name>.png (2048 x 1024)."""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image

WIDTH, HEIGHT = 2048, 1024


def geodesic_points(frequency):
    # 정이십면체의 면마다 무게중심 격자(i + j + k = frequency)를 깔고 구로 밀어낸 뒤 겹친 점을 지운다.
    g = (1.0 + 5.0 ** 0.5) / 2.0
    corners = np.array([[-1, g, 0], [1, g, 0], [-1, -g, 0], [1, -g, 0], [0, -1, g], [0, 1, g], [0, -1, -g], [0, 1, -g],
                        [g, 0, -1], [g, 0, 1], [-g, 0, -1], [-g, 0, 1]], float)
    corners /= np.linalg.norm(corners, axis=1, keepdims=True)
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    found = []
    for a, b, c in faces:
        for i in range(frequency + 1):
            for j in range(frequency + 1 - i):
                p = corners[a] * (frequency - i - j) + corners[b] * i + corners[c] * j
                found.append(p / np.linalg.norm(p))
    return np.unique(np.round(np.array(found), 6), axis=0)


def camera_axes():
    # 게임 카메라(pitch -50 · yaw 45, 보호막은 돌지 않음): 보는 방향, 화면 오른쪽, 화면 위쪽(구 좌표 = 세계 축)
    pitch, yaw = math.radians(50.0), math.radians(45.0)
    view = np.array([math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), -math.sin(pitch)])
    right = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
    up = np.cross(right, view)
    up /= np.linalg.norm(up)
    return view, right, up if up[2] > 0 else -up


def extend_cluster(points, covered, screen, view, spacing, extends):
    # --extend=SX,SY,N(10-19 밤 「옆쪽 육각형이 뒤쪽으로 이어져 있으면」): 화면 (SX, SY)에 가장 가깝게 보이는 앞면 덮인 칸의 덩어리
    # (맞닿은 덮인 칸끼리)에서, 덩어리에 맞닿은 빈 칸 중 카메라에서 가장 먼 쪽(구 뒤쪽)을 하나씩 N번 덮는다 — 구 표면을 따라 붙어서
    # 뒷면으로 감겨 넘어간다. 화면 자리로 뒷면 칸을 고르면(--grow back) 앞 덩어리와 떨어진 칸이 골라졌다.
    neighbour = (points @ points.T) > math.cos(1.3 * spacing)
    np.fill_diagonal(neighbour, False)
    for extend in extends:
        sx, sy, n = extend.split(',')
        front = covered & (points @ view < 0)
        seed = int(np.argmin(np.where(front, np.linalg.norm(screen - np.array([float(sx), float(sy)]), axis=1), np.inf)))
        cluster = np.zeros(len(points), bool)
        cluster[seed] = True
        while True:
            grown = cluster | (neighbour[cluster].any(axis=0) & covered)
            if grown.sum() == cluster.sum():
                break
            cluster = grown
        added = 0
        for _ in range(int(n)):
            free = neighbour[cluster].any(axis=0) & ~covered
            if not free.any():
                break
            pick = int(np.argmax(np.where(free, points @ view, -np.inf)))
            covered[pick] = True
            cluster[pick] = True
            added += 1
        print('extended', (sx, sy), 'cluster', int(cluster.sum()) - added, 'added', added)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('frequency', type=int)
    parser.add_argument('coverage', type=float, nargs='?', default=1.0 / 3.0)
    parser.add_argument('upper_bias', type=float, nargs='?', default=0.0)
    parser.add_argument('--clear-centre', type=float, default=0.0)
    parser.add_argument('--grow', action='append', default=[])
    parser.add_argument('--extend', action='append', default=[])
    args = parser.parse_args()
    name, frequency, coverage, upper_bias = args.name, args.frequency, args.coverage, args.upper_bias
    out = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora' / f'T_Aurora_Honey_{name}.png'
    rng = np.random.default_rng(11)
    points = geodesic_points(frequency)
    # 오각형 칸(원래 꼭짓점 12개)이 위 극에 오지 않게 아무 방향으로나 돌린다
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    points = points @ q.T
    count = len(points)
    spacing = math.sqrt(4.0 * math.pi / count)  # 칸 사이 각도(라디안) 대략
    # 덮인 칸 고르기: 칸 중심에서 잰 부드러운 잡음(평면파 여덟 개 합)이 큰 칸부터 coverage만큼 → 이웃끼리 붙은 덩어리
    waves = rng.normal(size=(8, 3))
    waves /= np.linalg.norm(waves, axis=1, keepdims=True)
    phases = rng.uniform(0, 2 * math.pi, 8)
    frequency = 2.0 * math.pi / (7.0 * spacing)  # 덩어리 한 개가 칸 서너 개 폭
    noise = np.sin(points @ waves.T * frequency + phases).sum(axis=1) + rng.normal(scale=0.6, size=count)
    noise = noise + upper_bias * noise.std() * points[:, 2]  # 위쪽(+Z, UV v = 0 쪽)으로 기울이기
    covered = noise >= np.quantile(noise, 1.0 - coverage)
    print('upper half share', round(float((points[covered, 2] > 0).mean()), 2))
    view, right, up = camera_axes()
    screen = np.stack([points @ right, points @ up], axis=1)
    if args.clear_centre > 0:
        # 화면에서 구 가운데(캐릭터 몸이 서는 자리)에 보이는 칸을 비운다(10-19 「정중앙에 있는 것들은 좀 지워 줘」)
        centre = covered & (np.linalg.norm(screen, axis=1) < args.clear_centre)
        covered &= ~centre
        print('cleared centre', int(centre.sum()))
    for grow in args.grow:
        # 화면 (SX, SY)에 보이는 앞면(front)·뒷면(back) 자리에서 가장 가까운 빈 칸 N개를 덮는다(10-19 「3·4쪽에 좀 더 추가」)
        sx, sy, side, n = grow.split(',')
        sx, sy = float(sx), float(sy)
        depth = math.sqrt(max(1.0 - sx * sx - sy * sy, 0.0)) * (1.0 if side == 'back' else -1.0)
        target = sx * right + sy * up + depth * view
        order = np.argsort(-(points @ target))
        picked = [i for i in order if not covered[i]][:int(n)]
        covered[picked] = True
        print('grew', side, (sx, sy), len(picked))
    extend_cluster(points, covered, screen, view, spacing, args.extend)
    # 게임 카메라에서 앞면으로 보이는 칸과 구 뒤쪽 면(양면 재질일 때만 보임) 칸 수
    facing = points[covered] @ view
    print('camera front', int((facing < 0).sum()), 'back', int((facing > 0).sum()))
    shade = rng.uniform(0.7, 1.0, count)

    v = (np.arange(HEIGHT) + 0.5) / HEIGHT
    u = (np.arange(WIDTH) + 0.5) / WIDTH
    theta = v * math.pi
    phi = np.radians(-90.0 + (1.0 - u) * 360.0)
    aa = (2.0 * math.pi / WIDTH) / spacing  # 텍셀 하나를 칸 크기 단위로
    fill = np.zeros((HEIGHT, WIDTH), np.float32)
    border = np.zeros_like(fill)
    ghost = np.zeros_like(fill)
    for row in range(0, HEIGHT, 16):
        rows = slice(row, row + 16)
        t = theta[rows][:, None]
        d = np.stack([np.sin(t) * np.cos(phi)[None, :], np.sin(t) * np.sin(phi)[None, :], np.broadcast_to(np.cos(t), (t.shape[0], WIDTH))],
                     axis=-1).reshape(-1, 3)
        dots = d @ points.T
        order = np.argpartition(-dots, 1, axis=1)[:, :2]
        first = np.take_along_axis(dots, order, axis=1)
        swap = first[:, 1] > first[:, 0]
        nearest = np.where(swap, order[:, 1], order[:, 0])
        second = np.where(swap, order[:, 0], order[:, 1])
        a1 = np.arccos(np.clip(dots[np.arange(len(d)), nearest], -1, 1))
        a2 = np.arccos(np.clip(dots[np.arange(len(d)), second], -1, 1))
        edge = (a2 - a1) * 0.5 / spacing  # 칸 경계까지 거리(칸 크기 단위)
        mine = covered[nearest]
        # 덮인 칸끼리 맞닿은 경계도, 덮인 칸의 바깥 경계도 테두리로 그린다(덮인 쪽 칸에서만)
        line = np.clip((0.05 - edge) / aa + 0.5, 0, 1)
        plate = np.where(mine, shade[nearest] * (0.55 + 0.45 * np.clip(1.0 - edge / 0.3, 0, 1)), 0.0)
        shape = (t.shape[0], WIDTH)
        fill[rows] = (plate * (1.0 - line)).reshape(shape)
        border[rows] = np.where(mine, line, 0.0).reshape(shape)
        ghost[rows] = np.clip((0.02 - edge) / aa + 0.5, 0, 1).reshape(shape)
    packed = np.stack([fill, border, ghost], axis=-1)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((packed * 255 + 0.5).astype(np.uint8), 'RGB').save(out)
    print(out, 'covered', int(covered.sum()), 'of', count)


if __name__ == '__main__':
    main()
