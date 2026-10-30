"""Draw Aurora's F ice-hawk drafts (2026-10-21 「얼음 모양 매나 새 같은 게 날아가는 거 어때? F는」) with numpy + Pillow.
- T_Aurora_IceHawk: a glowing ice hawk seen from above, eight wingbeat pictures in a 4 x 2 sheet (left to right, top row first).
  Head up (towards v = 0 of each cell) - the side that flies forward on the engine plane. R = bright lines (outline, feather
  splits, crystal facets), G = glowing body + soft halo, B = 0 (always shown by the wave material's Reveal).
- SM_Aurora_CrystalHawk_Body / _WingL / _WingR / _Tail (.obj): a faceted ice-crystal hawk in centimetres, X forward, Y right,
  Z up (written as x, -y, z for the engine's OBJ importer, which flips handedness). Every triangle has its own corners so the
  imported normals stay flat - each facet catches the fresnel glow on its own. Wings have their pivot at the shoulder (origin)
  so the game can flap them by rolling round X.
- 10-21 「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안」 (thin glowing line drawings, the inside nearly see-through):
  T_Aurora_IceHawkThin (slim-winged hawk, 4 x 2 wingbeats) · T_Aurora_IcePhoenix (512 x 1024 cells, 4 x 2: wingbeats + three long
  tail streamers rippling) · T_Aurora_IceDragon (2 x 2: head, body link, body link with legs, tail end - the game chains the links
  into a snaking serpent) · T_Aurora_FrostStar (one spinning snowflake blade).
Writes into SourceArt/Aurora (meshes into SourceArt/Aurora/Meshes). Usage: python aurora_bird_art.py [hawk crystal thin phoenix dragon star]."""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

FOLDER = Path(__file__).resolve().parents[2] / 'SourceArt' / 'Aurora'
CELL = 512
SCALE = 4  # 4배로 그려 줄인다(계단 없이)
BIG = CELL * SCALE
# 날갯짓 여덟 장 — 날개를 든 각(도, 위로 +). 아래로 내리칠 때는 날개 끝이 조금 앞으로, 들 때는 첫째 깃이 뒤로 접힌다.
BEATS = [0.0, -22.0, -38.0, -22.0, 12.0, 38.0, 58.0, 32.0]


# ---------- 위에서 본 매(펼친 모양, 오른쪽 날개만 — 왼쪽은 거울) ----------
# 좌표: x = 옆(날개 끝 1), y = 앞뒤(머리 -, 꼬리 +). 칸 안에서 x·y 모두 -1 ~ 1.
SHOULDER = 0.11
LEADING = [(0.11, -0.30), (0.30, -0.37), (0.55, -0.35), (0.76, -0.27)]
WRIST = (0.60, -0.33)
# 첫째 깃 다섯(바깥부터): 끝 자리 · 밑동 자리 · 밑동 반폭
PRIMARIES = [((0.99, -0.15), (0.70, -0.25), 0.050), ((0.97, -0.03), (0.66, -0.17), 0.050), ((0.91, 0.07), (0.63, -0.09), 0.048),
             ((0.82, 0.14), (0.60, -0.02), 0.046), ((0.72, 0.18), (0.56, 0.04), 0.044)]
# 둘째 깃 뒷전(몸 쪽으로)
SECONDARY = [(0.62, 0.15), (0.52, 0.17), (0.42, 0.18), (0.32, 0.17), (0.22, 0.14), (0.11, 0.08)]


HAWK_WING = {'shoulder': SHOULDER, 'leading': LEADING, 'wrist': WRIST, 'primaries': PRIMARIES, 'secondary': SECONDARY, 'hand_from': 0.6}


def beat_wing(beat, wing=None):
    """날개를 든 각에 따라 위에서 본 오른쪽 날개 점들을 옮긴다: 어깨 밖은 cos(각)만큼 짧아지고, 들 때 첫째 깃이 손목을 축으로 뒤로
    접히고, 내리칠 때 조금 앞으로 모인다. wing = 날개 모양(기본은 매, 얇은 매·봉황은 제 모양) — 앞전 마지막 점과 hand_from보다
    바깥 둘째 깃은 손목을 따라 접힌다."""
    wing = wing or HAWK_WING
    shoulder, wrist = wing['shoulder'], wing['wrist']
    span = math.cos(math.radians(beat))
    fold = math.radians(28.0) * max(0.0, math.sin(math.radians(beat))) - math.radians(10.0) * max(0.0, -math.sin(math.radians(beat)))

    def squash(p):
        return (shoulder + (p[0] - shoulder) * span, p[1])

    def hand(p):
        # 손목 둘레로 fold만큼(시계 방향 = 뒤로) 돌린 뒤 짧게
        dx, dy = p[0] - wrist[0], p[1] - wrist[1]
        c, s = math.cos(fold), math.sin(fold)
        return squash((wrist[0] + dx * c - dy * s, wrist[1] + dx * s + dy * c))

    # hand_edge = 앞전 끝에서 뒷전까지 손 판 둘레(깃 밑동을 덮어 깃이 날개에서 떨어져 보이지 않게, 손목을 따라 접힘 — 꽉 찬 매만)
    leading = [squash(p) for p in wing['leading'][:-1]] + [hand(wing['leading'][-1])] + [hand(p) for p in wing.get('hand_edge', [])]
    primaries = [(hand(tip), hand(base), width) for tip, base, width in wing['primaries']]
    secondary = [squash(p) if p[0] < wing['hand_from'] else hand(p) for p in wing['secondary']]
    return leading, primaries, secondary


def to_px(p, mirror=False):
    x = -p[0] if mirror else p[0]
    return ((x * 0.47 + 0.5) * BIG, (p[1] * 0.47 + 0.5) * BIG)


def finger(tip, base, width):
    # 밑동은 넓고 끝으로 갈수록 좁아지다 둥글게 끝나는 깃 하나
    dx, dy = tip[0] - base[0], tip[1] - base[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    points = []
    for t, w in [(0.0, 1.0), (0.55, 0.85), (0.85, 0.6), (0.97, 0.3)]:
        points.append((base[0] + dx * t + nx * width * w, base[1] + dy * t + ny * width * w))
    points.append(tip)
    for t, w in [(0.97, 0.3), (0.85, 0.6), (0.55, 0.85), (0.0, 1.0)]:
        points.append((base[0] + dx * t - nx * width * w, base[1] + dy * t - ny * width * w))
    return points


def scallop(points, depth=0.018, bumps=2):
    # 둘째 깃 뒷전: 점 사이를 깃 끝처럼 둥글게 볼록
    out = []
    for a, b in zip(points, points[1:]):
        for i in range(bumps * 6):
            t = i / (bumps * 6)
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            out.append((x, y + depth * abs(math.sin(t * math.pi * bumps))))
    out.append(points[-1])
    return out


# 머리는 둥글고 부리는 짧게 굽은 끝(첫 판은 뾰족한 가시 같았다), 가슴이 가장 넓다
BODY = [(0.0, -0.71), (0.022, -0.685), (0.05, -0.66), (0.08, -0.62), (0.095, -0.56), (0.09, -0.50), (0.08, -0.46), (0.12, -0.39),
        (0.15, -0.24), (0.145, -0.05), (0.11, 0.09), (0.08, 0.16)]
# 꼬리는 끝이 둥근 부채(첫 판은 곧은 세모)
TAIL = [(0.08, 0.12), (0.12, 0.30), (0.17, 0.48), (0.17, 0.55), (0.13, 0.60), (0.07, 0.625), (0.0, 0.635)]


def mirror_outline(half):
    # 오른쪽 반쪽 점들(가운데 x = 0에서 시작·끝) → 둘레 전체
    return [(x, y) for x, y in half] + [(-x, y) for x, y in reversed(half) if x != 0.0]


def draw_hawk(beat, rng):
    silhouette = Image.new('L', (BIG, BIG), 0)
    lines = Image.new('L', (BIG, BIG), 0)
    sil = ImageDraw.Draw(silhouette)
    ink = ImageDraw.Draw(lines)
    leading, primaries, secondary = beat_wing(beat)
    wide = int(SCALE * 2.6)
    thin = int(SCALE * 1.4)
    faint = max(int(SCALE * 0.9), 1)
    for mirror in (False, True):
        arm = leading + list(reversed(scallop(list(reversed(secondary)))))
        sil.polygon([to_px(p, mirror) for p in arm], fill=255)
        for tip, base, width in primaries:
            sil.polygon([to_px(p, mirror) for p in finger(tip, base, width)], fill=255)
            # 깃대(깃 가운데 선)
            ink.line([to_px(base, mirror), to_px((base[0] + (tip[0] - base[0]) * 0.9, base[1] + (tip[1] - base[1]) * 0.9), mirror)],
                     fill=150, width=thin)
        # 덮깃 줄(날개 앞쪽 1/3 쯤 가로지르는 선)과 둘째 깃 갈래
        covert = [(p[0], p[1] + 0.13 + 0.02 * math.sin(i)) for i, p in enumerate(leading[:3])]
        ink.line([to_px(p, mirror) for p in covert], fill=170, width=thin)
        for p in secondary[:-1]:
            ink.line([to_px((p[0], p[1] - 0.02), mirror), to_px((p[0] + 0.01, p[1] - 0.15), mirror)], fill=120, width=faint)
        # 얼음 결정 면: 앞전과 덮깃 줄 사이를 지그재그로 이은 삼각 면(옅게)
        edge = leading[:3]
        for i in range(len(edge) - 1):
            for t in (0.25, 0.5, 0.75):
                top = (edge[i][0] + (edge[i + 1][0] - edge[i][0]) * t, edge[i][1] + (edge[i + 1][1] - edge[i][1]) * t)
                low = (covert[i][0] + (covert[i + 1][0] - covert[i][0]) * (t + 0.12), covert[i][1] + (covert[i + 1][1] - covert[i][1]) * (t + 0.12))
                ink.line([to_px(top, mirror), to_px(low, mirror)], fill=110, width=faint)
        # 둘째 깃 칸 안 결정 금(짧고 아무렇게)
        for p in secondary[1:-1]:
            a = (p[0] + rng.uniform(-0.03, 0.03), p[1] - rng.uniform(0.04, 0.09))
            b = (a[0] + rng.uniform(-0.06, 0.06), a[1] - rng.uniform(0.03, 0.07))
            ink.line([to_px(a, mirror), to_px(b, mirror)], fill=95, width=faint)
    sil.polygon([to_px(p) for p in mirror_outline(BODY)], fill=255)
    sil.polygon([to_px(p) for p in mirror_outline(TAIL)], fill=255)
    # 꼬리 깃 갈래 · 등줄기 · 머리 결정 면 · 눈
    for x in (-0.12, -0.06, 0.0, 0.06, 0.12):
        ink.line([to_px((x * 0.5, 0.18)), to_px((x, 0.58))], fill=140, width=thin)
    ink.line([to_px((0.0, -0.60)), to_px((0.0, 0.10))], fill=170, width=thin)
    for y in (-0.36, -0.22, -0.08):
        ink.line([to_px((0.0, y)), to_px((0.11, y + 0.07))], fill=100, width=faint)
        ink.line([to_px((0.0, y)), to_px((-0.11, y + 0.07))], fill=100, width=faint)
    for side in (-1, 1):
        cx, cy = to_px((0.05 * side, -0.59))
        r = SCALE * 3.2
        ink.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    small = lambda image: np.asarray(image.resize((CELL, CELL), Image.LANCZOS), np.float32) / 255.0
    mask = small(silhouette)
    inner = small(lines) * mask
    # 둘레 선: 실루엣에서 조금 깎은 것을 뺀 띠
    shrunk = np.asarray(silhouette.filter(ImageFilter.MinFilter(int(SCALE * 3) * 2 + 1)).resize((CELL, CELL), Image.LANCZOS),
                        np.float32) / 255.0
    outline = np.clip(mask - shrunk, 0, 1)
    red = np.clip(np.maximum(outline * 1.0, inner), 0, 1)
    # 몸통 빛: 가장자리 가까울수록 밝게(깎은 실루엣을 흐려 안쪽 깊이로) + 바깥으로 번지는 빛
    depth = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(CELL * 0.02)), np.float32) / 255.0
    body = mask * (0.55 + 0.45 * np.clip(1.0 - depth, 0, 1) * 2.0)
    halo = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(CELL * 0.025)), np.float32) / 255.0
    green = np.clip(np.maximum(body, halo * 0.75), 0, 1)
    return red, green


def ice_hawk_sheet():
    rng = np.random.default_rng(21)
    sheet = np.zeros((CELL * 2, CELL * 4, 3), np.float32)
    for index, beat in enumerate(BEATS):
        red, green = draw_hawk(beat, rng)
        row, col = divmod(index, 4)
        sheet[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL, 0] = red
        sheet[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL, 1] = green
    FOLDER.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(sheet, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / 'T_Aurora_IceHawk.png')
    print(FOLDER / 'T_Aurora_IceHawk.png')


# ---------- 얼음 결정 매(입체, cm) ----------
def write_obj(name, triangles):
    folder = FOLDER / 'Meshes'
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f'o {name}']
    for a, b, c in triangles:
        for x, y, z in (a, b, c):
            lines.append(f'v {x:.3f} {-y:.3f} {z:.3f}')
    for i in range(len(triangles)):
        lines.append(f'f {3 * i + 1} {3 * i + 2} {3 * i + 3}')
    (folder / f'{name}.obj').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(folder / f'{name}.obj', len(triangles))


def ring_loft(rings):
    # 앞뒤로 늘어선 단면 고리(점 수 같음)를 이어 삼각형으로. 처음·끝 고리는 한 점으로 모아 뾰족하게.
    triangles = []
    for front, back in zip(rings, rings[1:]):
        n = len(front)
        for i in range(n):
            j = (i + 1) % n
            triangles.append((front[i], back[i], back[j]))
            triangles.append((front[i], back[j], front[j]))
    return triangles


def section(x, half_width, half_height, lift=0.0, sides=6, twist=0.0):
    # 앞뒤 x 자리의 단면(마름모꼴 육각): 위·아래 능선이 각진다
    points = []
    for i in range(sides):
        a = 2 * math.pi * i / sides + twist
        points.append((x, half_width * math.sin(a), lift + half_height * math.cos(a)))
    return points


def crystal_body():
    # 부리(앞 +X)부터 꼬리 밑동까지 각진 방추. 머리에서 한 번 굵어졌다 목에서 잘록, 가슴에서 가장 굵다.
    stations = [(54, 0.5, 0.5, 1), (48, 4, 3, 2), (42, 9, 8, 4), (35, 11, 10, 5), (28, 9, 8, 4), (18, 15, 12, 2), (4, 16, 12, 1),
                (-12, 13, 10, 0), (-24, 9, 7, 0), (-32, 5, 3.5, 0)]
    rings = [section(x, w, h, lift) for x, w, h, lift in stations]
    triangles = ring_loft(rings)
    # 꼬리 쪽 막기
    tail_tip = (-33, 0.0, 0.0)
    last = rings[-1]
    for i in range(len(last)):
        triangles.append((last[i], tail_tip, last[(i + 1) % len(last)]))
    write_obj('SM_Aurora_CrystalHawk_Body', triangles)


def slab(outline, ridge, top_lift, bottom_drop):
    """평면 모양(outline, 시계 반대 방향, z = 0)을 능선 쪽으로 솟은 각진 판으로: 윗면은 둘레 점과 능선 점을 이은 삼각 면(능선은
    top_lift만큼 높다), 아랫면은 둘레를 bottom_drop만큼 내린 평평한 면."""
    triangles = []
    centre = (sum(p[0] for p in ridge) / len(ridge), sum(p[1] for p in ridge) / len(ridge), -bottom_drop)
    for i in range(len(outline)):
        a, b = outline[i], outline[(i + 1) % len(outline)]
        # 둘레 두 점에 가장 가까운 능선 점
        r = min(ridge, key=lambda q: (q[0] - (a[0] + b[0]) / 2) ** 2 + (q[1] - (a[1] + b[1]) / 2) ** 2)
        top = (r[0], r[1], top_lift)
        triangles.append(((a[0], a[1], 0.0), (b[0], b[1], 0.0), top))
        triangles.append(((b[0], b[1], 0.0), (a[0], a[1], 0.0), centre))
    # 능선 점끼리도 이어 윗면에 틈이 없게
    for i in range(len(ridge) - 1):
        p, q = ridge[i], ridge[i + 1]
        mid = min(outline, key=lambda o: (o[0] - (p[0] + q[0]) / 2) ** 2 + (o[1] - (p[1] + q[1]) / 2) ** 2)
        triangles.append(((p[0], p[1], top_lift), (mid[0], mid[1], 0.0), (q[0], q[1], top_lift)))
    return triangles


def crystal_wing(mirror):
    # 위에서 본 매 날개(그림과 같은 모양)를 cm로: 그림 x(옆) 1 = 어깨에서 104cm, y(앞뒤) 1 = 120cm. 어깨(그림 x 0.11)가 원점.
    leading, primaries, secondary = beat_wing(0.0)
    def cm(p):
        return (-(p[1] + 0.06) * 120.0, (p[0] - SHOULDER) * 117.0)
    outline = [cm(p) for p in leading]
    for tip, base, width in primaries:
        outline.append(cm(tip))
        nxt = (base[0] - 0.01, base[1] + width * 1.2)
        outline.append(cm(nxt))
    outline += [cm(p) for p in scallop(list(secondary), depth=0.0, bumps=1)[::3]]
    ridge = [cm((0.14, -0.27)), cm((0.32, -0.32)), cm((0.55, -0.30)), cm((0.74, -0.22)), cm((0.9, -0.12))]
    triangles = slab(outline, ridge, 7.0, 2.5)
    if mirror:
        triangles = [tuple((x, -y, z) for x, y, z in reversed(t)) for t in triangles]
    write_obj('SM_Aurora_CrystalHawk_WingL' if mirror else 'SM_Aurora_CrystalHawk_WingR', triangles)


def crystal_tail():
    # 꼬리 부채: 밑동(원점)에서 뒤로 42cm, 끝 폭 46cm, 가운데 능선
    outline = [(4, -6), (-30, -20), (-42, -23), (-46, -12), (-44, 0), (-46, 12), (-42, 23), (-30, 20), (4, 6)]
    ridge = [(2, 0), (-20, 0), (-40, 0)]
    write_obj('SM_Aurora_CrystalHawk_Tail', slab(outline, ridge, 4.0, 1.5))


# ---------- 10-21 「매는 훨씬 더 얇은 느낌 · 매 아니어도 여러 시안」: 얇은 매 · 봉황 · 얼음 용 · 눈꽃 표창 ----------
# 넷 다 같은 짜임: 가는 둘레 선과 깃·비늘 선(R)이 빛나고, 안은 거의 비친다(G 채움 약 0.2 + 좁은 번짐). 그 전 매(T_Aurora_IceHawk)는
# 몸통이 G 0.55~1로 꽉 차 빛나는 덩어리(흰 비둘기)로 보였다.
class Canvas:
    """그림 칸 하나(SCALE배로 그려 줄인다): 1 = 칸 폭의 0.47배, x = 0이 가운데, y = 0이 칸 높이의 top 자리(머리 쪽이 -y).
    sil = 실루엣(둘레 선이 생긴다) · solid = 둘레 선 없이 채움·번짐만(칸 끝까지 이어지는 목·몸통) · ink = 실루엣 안에서만 보이는 선 ·
    free = 실루엣 밖까지 보이는 선(수염·뿔·꼬리 깃·곁가지). 선 굵기·반지름은 줄인 칸의 픽셀 × pen.
    pen = 게임에서 칸이 덮는 크기가 작을수록 크게 — 선이 세상에서 약 1.3~1.6cm 굵기여야 화면(약 0.6픽셀/cm)에서 보인다. 매 판(240cm,
    0.47cm/픽셀)은 1, 용 머리 판(140cm)은 2.2, 용 마디(폭 약 42cm)는 7."""

    def __init__(self, width, height, top=0.5, pen=1.0):
        self.w, self.h = width, height
        self.big = (width * SCALE, height * SCALE)
        self.unit = 0.47 * width * SCALE
        self.oy = top * height * SCALE
        self.pen = pen
        self.layers = {name: Image.new('L', self.big, 0) for name in ('sil', 'solid', 'ink', 'free')}

    def px(self, p, mirror=False):
        x = -p[0] if mirror else p[0]
        return (self.big[0] / 2 + x * self.unit, self.oy + p[1] * self.unit)

    def poly(self, points, mirror=False, layer='sil', fill=255):
        ImageDraw.Draw(self.layers[layer]).polygon([self.px(p, mirror) for p in points], fill=fill)

    def line(self, points, width, mirror=False, layer='ink', fill=255):
        ImageDraw.Draw(self.layers[layer]).line([self.px(p, mirror) for p in points], fill=fill,
                                                width=max(int(SCALE * width * self.pen), 1), joint='curve')

    def taper(self, points, start, end, mirror=False, layer='free'):
        # 굵기가 start에서 end로 줄어드는 선(마디마다 굵기를 바꿔 긋는다)
        for i in range(len(points) - 1):
            t = i / max(len(points) - 2, 1)
            self.line(points[i:i + 2], start + (end - start) * t, mirror, layer)

    def dot(self, p, radius, mirror=False, layer='free'):
        x, y = self.px(p, mirror)
        r = radius * SCALE * self.pen
        ImageDraw.Draw(self.layers[layer]).ellipse([x - r, y - r, x + r, y + r], fill=255)

    def channels(self, outline=2.6, fill=0.2, halo=0.45, blur=0.012, ramp=None):
        """줄인 칸의 (R, G). ramp = (위, 아래) 칸 끝에서 그 길이(단위)만큼 R·G를 0까지 줄인다 — 이어 붙는 용 몸통 마디가 겹치는 곳이 두 겹으로
        밝아지지 않게(겹친 두 마디가 서로 반대로 줄어 합이 1)."""
        w, h = self.w, self.h

        def small(image):
            return np.asarray(image.resize((w, h), Image.LANCZOS), np.float32) / 255.0

        sil = small(self.layers['sil'])
        # 둘레 선: 실루엣을 두 배 크기에서 깎아(작은 창이라 빠르다) 뺀 띠 — outline 픽셀 굵기
        double = self.layers['sil'].resize((w * 2, h * 2), Image.LANCZOS)
        shrunk = small(double.filter(ImageFilter.MinFilter(int(round(outline * self.pen * 2)) * 2 + 1)))
        mask = np.maximum(sil, small(self.layers['solid']))
        red = np.maximum(np.maximum(np.clip(sil - shrunk, 0, 1), small(self.layers['ink']) * mask), small(self.layers['free']))
        shape = np.maximum(mask, red)
        glow = np.asarray(Image.fromarray((shape * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w * blur)), np.float32) / 255.0
        green = np.clip(np.maximum(mask * fill, glow * halo), 0, 1)
        red = np.clip(red, 0, 1)
        if ramp:
            ys = (np.arange(h, dtype=np.float32) + 0.5) * SCALE
            v = (ys - self.oy) / self.unit
            top, bottom = (v - v[0]) / ramp[0] if ramp[0] else np.ones(h), (v[-1] - v) / ramp[1] if ramp[1] else np.ones(h)
            fade = np.clip(np.minimum(top, bottom), 0, 1)[:, None]
            red, green = red * fade, green * fade
        return red, green


def save_sheet(name, cells, columns):
    # cells = [(R, G), ...] 왼쪽에서 오른쪽, 윗줄부터. B = 0(재질 Reveal로 늘 보임)
    h, w = cells[0][0].shape
    rows = (len(cells) + columns - 1) // columns
    sheet = np.zeros((h * rows, w * columns, 3), np.float32)
    for index, (red, green) in enumerate(cells):
        row, col = divmod(index, columns)
        sheet[row * h:(row + 1) * h, col * w:(col + 1) * w, 0] = red
        sheet[row * h:(row + 1) * h, col * w:(col + 1) * w, 1] = green
    FOLDER.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(sheet, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(FOLDER / f'{name}.png')
    print(FOLDER / f'{name}.png', sheet.shape[1], sheet.shape[0])


def curved_finger(tip, base, width, bend):
    # 밑동 넓고 끝이 가는 깃 하나를 활처럼(bend = 가운데가 옆으로 비킨 거리, + = 깃 방향의 왼쪽 법선 = 오른 날개에선 꼬리 쪽)
    dx, dy = tip[0] - base[0], tip[1] - base[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    centre = []
    for t in (0.0, 0.25, 0.5, 0.75, 0.9, 1.0):
        k = bend * 4.0 * t * (1.0 - t)
        centre.append((base[0] + dx * t + nx * k, base[1] + dy * t + ny * k))
    widths = [1.0, 0.95, 0.8, 0.55, 0.3, 0.0]
    left = [(x + nx * width * f, y + ny * width * f) for (x, y), f in zip(centre, widths)]
    right = [(x - nx * width * f, y - ny * width * f) for (x, y), f in zip(centre, widths)]
    return left + list(reversed(right[:-1])), centre


# 얇은 매: 날개 폭(앞전 ~ 뒷전)을 그 전의 약 1/3, 첫째 깃은 넷으로 가늘고 길게(제비·칼새처럼), 몸통 폭 약 0.4배, 꼬리는 좁은 부채
THIN_WING = {'shoulder': 0.06, 'leading': [(0.06, -0.33), (0.16, -0.375), (0.26, -0.40), (0.37, -0.41), (0.47, -0.40), (0.57, -0.375),
                                            (0.66, -0.33)], 'wrist': (0.52, -0.38),
             'primaries': [((0.99, -0.13), (0.64, -0.31), 0.022), ((0.95, -0.05), (0.61, -0.27), 0.021),
                           ((0.89, 0.01), (0.58, -0.24), 0.020), ((0.81, 0.05), (0.55, -0.21), 0.019)],
             'secondary': [(0.55, -0.20), (0.46, -0.23), (0.36, -0.24), (0.26, -0.24), (0.16, -0.23), (0.06, -0.21)], 'hand_from': 0.5}
THIN_BODY = [(0.0, -0.64), (0.018, -0.625), (0.034, -0.595), (0.043, -0.55), (0.038, -0.50), (0.032, -0.46), (0.05, -0.39),
             (0.058, -0.29), (0.052, -0.14), (0.04, 0.0), (0.03, 0.09)]
THIN_TAIL = [(0.03, 0.07), (0.045, 0.25), (0.07, 0.46), (0.06, 0.50), (0.03, 0.48), (0.0, 0.50)]


def draw_thin_hawk(beat):
    c = Canvas(CELL, CELL)
    leading, primaries, secondary = beat_wing(beat, THIN_WING)
    for mirror in (False, True):
        c.poly(leading + list(reversed(scallop(list(reversed(secondary)), depth=0.008))), mirror)
        for tip, base, width in primaries:
            c.poly(finger(tip, base, width), mirror)
            c.line([base, (base[0] + (tip[0] - base[0]) * 0.85, base[1] + (tip[1] - base[1]) * 0.85)], 1.1, mirror)
        # 앞전 안쪽으로 나란한 결 한 줄
        c.line([(p[0], p[1] + 0.045) for p in leading[1:-1]], 1.0, mirror)
    c.poly(mirror_outline(THIN_BODY))
    c.poly(mirror_outline(THIN_TAIL))
    c.line([(0.0, -0.57), (0.0, 0.06)], 1.1)
    for x in (-0.03, 0.03):
        c.line([(x * 0.5, 0.12), (x, 0.44)], 1.0)
    for side in (False, True):
        c.dot((0.022, -0.585), 1.2, side, 'ink')
    return c.channels(outline=2.6, fill=0.2, halo=0.45)


def thin_hawk_sheet():
    save_sheet('T_Aurora_IceHawkThin', [draw_thin_hawk(beat) for beat in BEATS], 4)


# 꽉 찬 매(10-25 「F도 매 모양 좀...」 — 얇은 매는 몸통이 긴 막대 · 가는 날개 · 날개에서 떨어진 깃이라 곤충처럼 보였다):
# 위에서 본 매 — 넓은 날개(팔 폭 약 0.35) · 손 판에서 부채처럼 벌어지는 첫째 깃 여섯 · 짧고 굵은 몸통 · 둥근 머리와 짧은 부리 · 부채 꼬리.
# 안을 채워(fill 0.5) 판이 비쳐 보이지 않게, 둘레 선은 얇은 매와 같은 굵기.
BOLD_WING = {'shoulder': 0.07, 'leading': [(0.07, -0.20), (0.20, -0.27), (0.34, -0.30), (0.48, -0.30), (0.60, -0.27), (0.70, -0.22)],
             'wrist': (0.62, -0.27),
             'hand_edge': [(0.70, -0.16), (0.68, -0.09), (0.65, -0.03), (0.61, 0.02), (0.57, 0.07)],
             'primaries': [((0.99, -0.12), (0.68, -0.19), 0.034), ((0.97, -0.02), (0.67, -0.13), 0.035),
                           ((0.92, 0.07), (0.65, -0.07), 0.035), ((0.85, 0.14), (0.62, -0.02), 0.034),
                           ((0.77, 0.18), (0.59, 0.02), 0.033), ((0.68, 0.20), (0.56, 0.05), 0.032)],
             'secondary': [(0.56, 0.08), (0.47, 0.11), (0.38, 0.12), (0.29, 0.12), (0.20, 0.11), (0.12, 0.09), (0.07, 0.06)],
             'hand_from': 0.55}
BOLD_BODY = [(0.0, -0.505), (0.014, -0.49), (0.03, -0.475), (0.048, -0.45), (0.057, -0.41), (0.054, -0.37), (0.075, -0.31),
             (0.10, -0.21), (0.106, -0.09), (0.092, 0.05), (0.072, 0.17), (0.05, 0.25)]
BOLD_TAIL = [(0.05, 0.21), (0.08, 0.35), (0.125, 0.49), (0.13, 0.535), (0.10, 0.555), (0.065, 0.55), (0.032, 0.562), (0.0, 0.555)]


def slim(wing, chord=0.6, feather=0.75):
    # 같은 매를 날씬하게(10-21 「훨씬 더 얇은 느낌」도 살린 시안): 앞전은 그대로 두고 뒷전·손 판·깃 밑동을 앞전 쪽으로 chord배 당기고 깃을 feather배 가늘게
    front = -0.27

    def pull(p):
        return (p[0], front + (p[1] - front) * chord)
    return {**wing, 'hand_edge': [pull(p) for p in wing['hand_edge']], 'secondary': [pull(p) for p in wing['secondary']],
            'primaries': [(tip, pull(base), width * feather) for tip, base, width in wing['primaries']]}


SLIM_WING = slim(BOLD_WING)
SLIM_BODY = [(x * 0.72, y) for x, y in BOLD_BODY]
SLIM_TAIL = [(x * 0.8, y) for x, y in BOLD_TAIL]


def draw_bold_hawk(beat, wing=BOLD_WING, body=BOLD_BODY, tail=BOLD_TAIL):
    c = Canvas(CELL, CELL)
    leading, primaries, secondary = beat_wing(beat, wing)
    for mirror in (False, True):
        c.poly(leading + list(reversed(scallop(list(reversed(secondary)), depth=0.014))), mirror)
        for tip, base, width in primaries:
            c.poly(finger(tip, base, width), mirror)
            c.line([base, (base[0] + (tip[0] - base[0]) * 0.88, base[1] + (tip[1] - base[1]) * 0.88)], 1.0, mirror)
        # 덮깃 줄(날개 앞쪽 1/3을 가로지름) · 둘째 깃 갈래
        c.line([(p[0], p[1] + 0.12) for p in leading[1:5]], 1.1, mirror)
        for p in secondary[1:-1]:
            c.line([(p[0], p[1] - 0.015), (p[0] + 0.012, p[1] - 0.12)], 0.8, mirror)
    c.poly(mirror_outline(body))
    c.poly(mirror_outline(tail))
    # 등줄기 · 꼬리 깃 갈래 · 눈
    c.line([(0.0, -0.40), (0.0, 0.18)], 1.0)
    for x in (-0.09, -0.045, 0.0, 0.045, 0.09):
        c.line([(x * 0.45, 0.26), (x, 0.52)], 0.9)
    for side in (False, True):
        c.dot((0.03, -0.44), 1.4, side, 'ink')
    return c.channels(outline=2.6, fill=0.5, halo=0.45)


def bold_hawk_sheet():
    save_sheet('T_Aurora_IceHawkBold', [draw_bold_hawk(beat) for beat in BEATS], 4)
    save_sheet('T_Aurora_IceHawkSlim', [draw_bold_hawk(beat, SLIM_WING, SLIM_BODY, SLIM_TAIL) for beat in BEATS], 4)


# 봉황: 칸 512 × 1024(머리가 위, 어깨가 칸 높이 0.24) — 활처럼 휜 긴 첫째 깃 여섯, 머리 깃, 짧은 꼬리 부채 + 긴 꼬리 깃 셋(끝에 마름모 깃).
# 여덟 장마다 날갯짓(매와 같은 각)과 함께 꼬리 깃이 물결친다(한 바퀴).
PHOENIX_WING = {'shoulder': 0.06, 'leading': [(0.06, -0.30), (0.27, -0.40), (0.48, -0.43), (0.66, -0.38)], 'wrist': (0.52, -0.41),
                'primaries': [((0.99, -0.25), (0.64, -0.36), 0.024), ((0.97, -0.13), (0.61, -0.32), 0.024),
                              ((0.93, -0.02), (0.58, -0.29), 0.023), ((0.87, 0.07), (0.55, -0.26), 0.022),
                              ((0.79, 0.14), (0.52, -0.23), 0.021), ((0.69, 0.18), (0.49, -0.21), 0.020)],
                'secondary': [(0.48, -0.19), (0.39, -0.18), (0.30, -0.17), (0.21, -0.17), (0.12, -0.17), (0.06, -0.18)], 'hand_from': 0.46}
PHOENIX_BODY = [(0.0, -0.66), (0.02, -0.645), (0.036, -0.615), (0.044, -0.57), (0.036, -0.51), (0.03, -0.46), (0.048, -0.38),
                (0.06, -0.27), (0.055, -0.12), (0.042, 0.0), (0.03, 0.1)]


def streamer(x0, y0, y1, drift, phase, amplitude=0.13, waves=1.1, steps=40):
    points = []
    for i in range(steps + 1):
        t = i / steps
        points.append((x0 + drift * t + amplitude * t ** 1.2 * math.sin(2.0 * math.pi * waves * t - phase), y0 + (y1 - y0) * t))
    return points


def draw_phoenix(index):
    c = Canvas(CELL, CELL * 2, top=0.24)
    beat = BEATS[index]
    phase = 2.0 * math.pi * index / len(BEATS)
    leading, primaries, secondary = beat_wing(beat, PHOENIX_WING)
    for mirror in (False, True):
        c.poly(leading + list(reversed(scallop(list(reversed(secondary)), depth=0.008))), mirror)
        for tip, base, width in primaries:
            outline, centre = curved_finger(tip, base, width, -0.035)
            c.poly(outline, mirror)
            c.line(centre[:-1], 1.0, mirror)
        c.line([(p[0], p[1] + 0.05) for p in leading[:3]], 1.0, mirror)
        # 머리 깃 둘(뒤·바깥으로 흐름)
        c.taper([(0.02, -0.60), (0.07, -0.55), (0.12, -0.51), (0.17, -0.49)], 2.6, 1.4, mirror)
        c.taper([(0.02, -0.57), (0.05, -0.50), (0.08, -0.45), (0.10, -0.40)], 2.4, 1.3, mirror)
    c.poly(mirror_outline(PHOENIX_BODY))
    c.line([(0.0, -0.58), (0.0, 0.08)], 1.0)
    for side in (False, True):
        c.dot((0.022, -0.6), 1.2, side, 'ink')
    # 짧은 꼬리 부채 다섯
    for tip in ((0.0, 0.66), (0.08, 0.62), (-0.08, 0.62), (0.15, 0.55), (-0.15, 0.55)):
        c.poly(finger(tip, (tip[0] * 0.2, 0.08), 0.022))
    # 긴 꼬리 깃 셋: 가운데가 가장 길다. 끝에 마름모 깃(실루엣 — 둘레 선이 생긴다)
    for x0, drift, y1, offset in ((0.0, 0.0, 2.7, 0.0), (0.03, 0.26, 2.25, 0.9), (-0.03, -0.26, 2.25, 1.8)):
        line = streamer(x0, 0.3, y1, drift, phase + offset)
        c.taper(line, 3.6, 2.0)
        (ax, ay), (bx, by) = line[-2], line[-1]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        c.poly([(bx - dx * 0.02, by - dy * 0.02), (bx + dx * 0.11 - dy * 0.055, by + dy * 0.11 + dx * 0.055), (bx + dx * 0.25, by + dy * 0.25),
                (bx + dx * 0.11 + dy * 0.055, by + dy * 0.11 - dx * 0.055)])
    return c.channels(outline=2.6, fill=0.2, halo=0.45, blur=0.01)


def phoenix_sheet():
    save_sheet('T_Aurora_IcePhoenix', [draw_phoenix(index) for index in range(len(BEATS))], 4)


# 얼음 용: 2 × 2 칸 — 0 머리(위가 주둥이, 칸 아래 끝까지 목) · 1 몸통 마디 · 2 다리 달린 마디 · 3 꼬리 끝. C++이 머리 뒤로 마디를 사슬처럼
# 이어 나는 길을 따라 구불거리게 놓는다. 마디 칸은 위아래 끝까지 몸통이 이어지고 겹치는 끝(DRAGON_RAMP)은 서로 반대로 옅어진다.
# 몸통 반폭은 마디 칸에서 0.55 — C++ 마디 판 폭이 몸통 폭의 2.128 / 1.1배. 머리 칸의 목 반폭 0.167은 머리 판 140cm에서 첫 마디(몸통 폭 22cm)와 같다.
# 선 굵기(pen): 머리 판 140cm = 0.27cm/픽셀 → 2.2 · 마디 판 폭 약 42cm(0.08cm/픽셀) → 7 — 세상에서 약 1.5cm(꼬리로 갈수록 판이 좁아져 가늘어진다)
DRAGON_TUBE = 0.55
DRAGON_RAMP = 0.193
DRAGON_HEAD = [(0.0, -0.95), (0.05, -0.93), (0.085, -0.87), (0.095, -0.75), (0.10, -0.62), (0.13, -0.55), (0.20, -0.48), (0.24, -0.38),
               (0.25, -0.26), (0.22, -0.14), (0.18, -0.04), (0.17, 0.12), (0.0, 0.16)]
DRAGON_NECK = 0.167
DRAGON_HEAD_PEN = 2.2
DRAGON_LINK_PEN = 7.0


def draw_dragon_head():
    c = Canvas(CELL, CELL, pen=DRAGON_HEAD_PEN)
    c.poly(mirror_outline(DRAGON_HEAD))
    # 목은 둘레 선 없이 채우고 양옆 선만 칸 아래 끝까지(첫 마디로 이어진다)
    c.poly([(-DRAGON_NECK, 0.05), (DRAGON_NECK, 0.05), (DRAGON_NECK, 1.2), (-DRAGON_NECK, 1.2)], layer='solid')
    for mirror in (False, True):
        c.line([(DRAGON_NECK, 0.10), (DRAGON_NECK, 1.2)], 2.6, mirror, 'free')
        # 뿔: 머리 옆 가장자리에서 뒤·바깥으로 휘고 중간에 가지 하나
        c.taper([(0.22, -0.32), (0.27, -0.16), (0.32, 0.02), (0.36, 0.20), (0.37, 0.36)], 2.4, 1.0, mirror)
        c.taper([(0.29, -0.08), (0.37, -0.08), (0.45, -0.02)], 1.8, 0.9, mirror)
        # 수염: 주둥이 옆에서 바깥으로 나가 뒤로 길게 흐른다
        c.taper([(0.09, -0.84), (0.22, -0.87), (0.35, -0.82), (0.45, -0.69), (0.50, -0.52), (0.49, -0.34), (0.53, -0.16), (0.60, -0.02)],
                1.6, 0.8, mirror)
        # 갈기: 뒷머리 가장자리에서 뒤·바깥으로 뻗은 가시 셋
        for a, b in (((0.19, -0.06), (0.30, 0.10)), ((0.175, 0.04), (0.27, 0.26)), ((0.17, 0.12), (0.22, 0.40))):
            c.taper([a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), b], 1.8, 0.8, mirror)
        c.line([(0.06, -0.56), (0.19, -0.47)], 1.1, mirror)
        c.line([(0.12, -0.45), (0.18, -0.41)], 2.2, mirror)
        c.dot((0.04, -0.88), 1.2, mirror, 'ink')
        for y in (0.45, 0.82):
            c.line([(0.16, y + 0.06), (0.0, y - 0.06)], 1.2, mirror)
    c.line([(0.0, -0.80), (0.0, 0.12)], 1.0)
    return c.channels(outline=2.6, fill=0.2, halo=0.45)


def dragon_tube(c, frill=True):
    c.poly([(-DRAGON_TUBE, -1.2), (DRAGON_TUBE, -1.2), (DRAGON_TUBE, 1.2), (-DRAGON_TUBE, 1.2)], layer='solid')
    for mirror in (False, True):
        c.line([(DRAGON_TUBE, -1.2), (DRAGON_TUBE, 1.2)], 2.6, mirror, 'free')
        for y in (-0.45, 0.55):
            c.line([(0.50, y + 0.22), (0.0, y - 0.20)], 1.3, mirror)
        if frill:
            # 옆 가시(뒤로 누운 작은 지느러미)
            c.poly([(DRAGON_TUBE - 0.02, -0.25), (0.88, 0.32), (DRAGON_TUBE - 0.02, 0.12)], mirror)
    # 등 가운데 마름모 비늘
    c.poly([(0.0, -0.28), (0.08, 0.0), (0.0, 0.28), (-0.08, 0.0)])


def draw_dragon_body():
    c = Canvas(CELL, CELL, pen=DRAGON_LINK_PEN)
    dragon_tube(c)
    return c.channels(outline=2.6, fill=0.2, halo=0.45, blur=0.03, ramp=(DRAGON_RAMP, DRAGON_RAMP))


def draw_dragon_legs():
    c = Canvas(CELL, CELL, pen=DRAGON_LINK_PEN)
    dragon_tube(c, frill=False)
    for mirror in (False, True):
        # 어깨 → 팔꿈치 → 발, 발끝에 발톱 셋
        c.poly([(DRAGON_TUBE - 0.03, -0.20), (0.80, -0.04), (0.93, 0.26), (0.86, 0.29), (0.74, 0.06), (DRAGON_TUBE - 0.03, 0.02)], mirror)
        for claw in ((1.00, 0.30), (0.97, 0.40), (0.88, 0.43)):
            c.taper([(0.90, 0.28), claw], 1.4, 0.8, mirror)
    return c.channels(outline=2.6, fill=0.2, halo=0.45, blur=0.03, ramp=(DRAGON_RAMP, DRAGON_RAMP))


def draw_dragon_tail():
    c = Canvas(CELL, CELL, pen=DRAGON_LINK_PEN)
    c.poly([(-DRAGON_TUBE, -1.2), (DRAGON_TUBE, -1.2), (0.30, -0.30), (0.0, 0.25), (-0.30, -0.30)], layer='solid')
    for mirror in (False, True):
        c.line([(DRAGON_TUBE, -1.2), (0.30, -0.30), (0.0, 0.25)], 2.6, mirror, 'free')
        c.line([(0.40, -0.65), (0.0, -0.85)], 1.3, mirror)
        # 꼬리 끝 술: 가는 깃 셋이 부채처럼 뒤로
        for end, mid in (((0.16, 0.95), (0.05, 0.6)), ((0.36, 0.82), (0.16, 0.5)), ((0.52, 0.62), (0.26, 0.36))):
            c.taper([(0.0, 0.15), mid, end], 1.8, 0.8, mirror)
    c.taper([(0.0, 0.15), (0.0, 0.6), (0.0, 1.0)], 1.8, 0.8)
    return c.channels(outline=2.6, fill=0.2, halo=0.45, blur=0.03, ramp=(DRAGON_RAMP, 0.0))


def dragon_sheet():
    save_sheet('T_Aurora_IceDragon', [draw_dragon_head(), draw_dragon_body(), draw_dragon_legs(), draw_dragon_tail()], 2)


# 눈꽃 표창: 휘어진 칼날 팔 여섯(바람개비처럼 — C++이 돌린다) + 팔마다 곁가지 둘, 가운데 육각 고리
def draw_frost_star():
    # 판 130cm(0.25cm/픽셀) — 선이 매 판과 같은 세상 굵기가 되게 pen 1.8
    c = Canvas(CELL, CELL, pen=1.8)
    inner, outer, curve = 0.16, 0.98, 0.55
    for arm in range(6):
        base = math.radians(60.0 * arm)
        centre, left, right = [], [], []
        for i in range(25):
            t = i / 24
            r = inner + (outer - inner) * t
            a = base + curve * (r - inner) ** 2
            centre.append((r * math.sin(a), -r * math.cos(a)))
        for i, (x, y) in enumerate(centre):
            t = i / 24
            nx, ny = (centre[min(i + 1, 24)][0] - centre[max(i - 1, 0)][0]), (centre[min(i + 1, 24)][1] - centre[max(i - 1, 0)][1])
            n = math.hypot(nx, ny)
            nx, ny = -ny / n, nx / n
            half = 0.085 * math.sin(math.pi * min(t * 1.05, 1.0)) ** 0.6 * (1.0 - 0.35 * t) if t > 0 else 0.06
            left.append((x + nx * half, y + ny * half))
            right.append((x - nx * half, y - ny * half))
        c.poly(left + list(reversed(right)))
        c.line(centre[2:-3], 1.1)
        for at, length in ((10, 0.17), (16, 0.12)):
            x, y = centre[at]
            tx, ty = centre[at + 1][0] - centre[at - 1][0], centre[at + 1][1] - centre[at - 1][1]
            n = math.hypot(tx, ty)
            tx, ty = tx / n, ty / n
            for sign in (-1.0, 1.0):
                a = math.radians(55.0) * sign
                ex, ey = tx * math.cos(a) - ty * math.sin(a), tx * math.sin(a) + ty * math.cos(a)
                c.taper([(x, y), (x + ex * length * 0.5, y + ey * length * 0.5), (x + ex * length, y + ey * length)], 1.6, 0.8)
    c.poly([(0.2 * math.sin(math.radians(60 * k + 30)), -0.2 * math.cos(math.radians(60 * k + 30))) for k in range(6)])
    c.line([(0.11 * math.sin(math.radians(60 * k + 30)), -0.11 * math.cos(math.radians(60 * k + 30))) for k in range(7)], 1.4)
    c.dot((0.0, 0.0), 2.0, layer='ink')
    return c.channels(outline=2.6, fill=0.22, halo=0.5)


def frost_star_sheet():
    save_sheet('T_Aurora_FrostStar', [draw_frost_star()], 1)


# ---------- 입체 매(10-26 「3D 매를 니가 만들 수 있겠어? — 디테일은 필요 없고 유저가 매라고 느끼기만 하면 돼」) ----------
# 날씬한 매의 날개(SLIM_WING)와 꽉 찬 매의 몸·꼬리(BOLD_* — 가는 몸은 세우면 막대 같았다)를 위에서 본 모양 그대로 cm로 세운다: 그림 1 = HAWK3D_CM. 메시 X = 앞(그림 -y) · Y = 오른쪽(그림 x) · Z = 위.
# 몸(꼬리 포함) 하나 + 날개 안쪽(어깨 → 손목, 원점 = 어깨) 둘 + 날개 바깥쪽(손 판 + 첫째 깃, 원점 = 손목) 둘 — 게임이 어깨와 손목에서
# 따로 돌려 손목에서 한 번 더 꺾이며 퍼덕인다. 판은 가운데가 솟은 각진 얼음판(위 면은 둘레 → 가운데 점, 아래는 평평).
HAWK3D_CM = 80.0
HAWK3D_SHOULDER = (0.07, -0.13)
HAWK3D_WRIST = (0.60, -0.20)


def hawk3d_cm(p, origin=(0.0, 0.0)):
    return ((-(p[1] - origin[1])) * HAWK3D_CM, (p[0] - origin[0]) * HAWK3D_CM)


def hawk3d_panel(outline, centre, top, edge=0.8, bottom=0.8):
    """둘레(cm, 평면) → 가운데(centre)가 top만큼 솟은 각진 판. 둘레 위 = edge, 아래 = -bottom."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1]))
    if area < 0:
        outline = list(reversed(outline))
    up = (centre[0], centre[1], top)
    down = (centre[0], centre[1], -bottom)
    triangles = []
    for a, b in zip(outline, outline[1:] + outline[:1]):
        at, bt = (a[0], a[1], edge), (b[0], b[1], edge)
        ab, bb = (a[0], a[1], -bottom), (b[0], b[1], -bottom)
        triangles += [(at, bt, up), (bb, ab, down), (at, ab, bb), (at, bb, bt)]
    return triangles


def hawk3d_mirror(triangles):
    return [tuple((x, -y, z) for x, y, z in reversed(t)) for t in triangles]


def hawk3d_body():
    # 몸: 앞뒤로 늘어선 팔각 단면(반폭 = 꽉 찬 매 몸 둘레, 높이 0.8배). 부리 끝은 아래로 굽고, 꼬리 밑동에서 닫는다.
    half = sorted(BOLD_BODY, key=lambda p: p[1])
    rings = []
    for x, y in half[1:]:
        w = x * HAWK3D_CM
        lift = -0.5 * w if y < -0.47 else 0.0
        rings.append([(-y * HAWK3D_CM, w * math.sin(a), lift + 0.8 * w * math.cos(a))
                      for a in (2 * math.pi * i / 8 + math.pi / 8 for i in range(8))])
    beak = (-half[0][1] * HAWK3D_CM, 0.0, -0.4 * half[1][0] * HAWK3D_CM)
    triangles = [(beak, rings[0][(i + 1) % 8], rings[0][i]) for i in range(8)]
    triangles += ring_loft(rings)
    tail_end = (-half[-1][1] * HAWK3D_CM - 2.0, 0.0, 0.0)
    triangles += [(rings[-1][i], rings[-1][(i + 1) % 8], tail_end) for i in range(8)]
    # 꼬리 부채: 몸 끝에 붙은 각진 판
    tail = [hawk3d_cm(p) for p in mirror_outline(BOLD_TAIL)]
    triangles += hawk3d_panel(tail, hawk3d_cm((0.0, 0.40)), 2.5, 0.5, 0.5)
    write_obj('SM_Aurora_Hawk3D_Body', triangles)


def hawk3d_wings():
    leading, primaries, secondary = beat_wing(0.0, SLIM_WING)
    # 안쪽: 어깨 → 손목 앞전, 손목 밑 → 몸 쪽 뒷전(손 판 경계 x 0.58까지)
    inner = [p for p in leading if p[0] <= 0.61] + [(0.58, HAWK3D_WRIST[1] + 0.12)] + [p for p in secondary if p[0] < 0.58]
    inner_tris = hawk3d_panel([hawk3d_cm(p, HAWK3D_SHOULDER) for p in inner], hawk3d_cm((0.30, -0.18), HAWK3D_SHOULDER), 3.0)
    # 바깥쪽: 손 판(손목 앞전 · 손 판 둘레 · 안쪽 경계) + 첫째 깃마다 가는 판
    hand = [(0.57, -0.27)] + [p for p in leading if p[0] > 0.6] + list(SLIM_WING['hand_edge']) + [(0.56, -0.05)]
    outer_tris = hawk3d_panel([hawk3d_cm(p, HAWK3D_WRIST) for p in hand], hawk3d_cm((0.64, -0.16), HAWK3D_WRIST), 3.5)
    for tip, base, width in primaries:
        shape = [hawk3d_cm(p, HAWK3D_WRIST) for p in finger(tip, base, width)]
        mid = hawk3d_cm(((tip[0] + base[0]) / 2, (tip[1] + base[1]) / 2), HAWK3D_WRIST)
        outer_tris += hawk3d_panel(shape, mid, 1.6, 0.4, 0.4)
    write_obj('SM_Aurora_Hawk3D_InnerR', inner_tris)
    write_obj('SM_Aurora_Hawk3D_InnerL', hawk3d_mirror(inner_tris))
    write_obj('SM_Aurora_Hawk3D_OuterR', outer_tris)
    write_obj('SM_Aurora_Hawk3D_OuterL', hawk3d_mirror(outer_tris))
    # 게임 쪽(어깨 · 손목 자리, cm) — AuroraSkillComponentFDrafts.cpp Hawk3D 상수와 맞출 것
    print('shoulder', hawk3d_cm(HAWK3D_SHOULDER), 'wrist from shoulder', hawk3d_cm(HAWK3D_WRIST, HAWK3D_SHOULDER))


# python aurora_bird_art.py [hawk crystal thin phoenix dragon star hawk3d] — 이름을 안 주면 다 그린다
PARTS = {'hawk': lambda: ice_hawk_sheet(), 'crystal': lambda: (crystal_body(), crystal_wing(False), crystal_wing(True), crystal_tail()),
         'thin': thin_hawk_sheet, 'bold': bold_hawk_sheet, 'phoenix': phoenix_sheet, 'dragon': dragon_sheet, 'star': frost_star_sheet,
         'hawk3d': lambda: (hawk3d_body(), hawk3d_wings())}

if __name__ == '__main__':
    import sys
    for part in sys.argv[1:] or list(PARTS):
        PARTS[part]()
