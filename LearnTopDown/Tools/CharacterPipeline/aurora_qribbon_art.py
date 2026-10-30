"""94th round (10-28 「Q는 그림 톤·게임 톤과 안 맞고 이펙트 퀄리티도 아쉽다 — 검기를 얇게 해야 할까?」): crescent ribbon meshes for the Q
sword wave so the pack's own sword-trail materials (textures streaming along U) can draw it. Written as OBJ files for
aurora_frost_materials_build.py qtrail (import_obj_mesh).
Laid out in the same frame as the engine plane the wave flies on (BladeTick moves and scales it like that plane): 100 x 100 around the
origin, flight direction = -Y, the crescent's outer edge at radius 0.79 x 50, fan +-62 degrees (aurora_slash_textures.py polar, M_Aurora_QSlashForge).
UV: u runs along the arc from the left tip (0) to the right tip (1), v from the outer edge (0) to the inner edge (1).
- SM_Aurora_QRibbonThin: a thin blade, 0.09 of the plane half deep at the middle, tapering to the tips, the outer edge lifted 6 cm
- SM_Aurora_QRibbonWide: the same arc 0.30 deep (room for a trailing smoky body), the outer edge lifted 10 cm
- SM_Aurora_QRibbonHair: (95th 「검기를 아주 얇게」) the same arc only 0.035 deep, the outer edge lifted 3 cm"""
import math

from aurora_spear_art import write_obj

HALF_FAN = math.radians(62.0)
EDGE = 0.79
SEGMENTS = 64
ROWS = 6


def ribbon(depth, lift):
    """Triangles of one crescent ribbon (plane units: the plane is +-50)."""
    def point(i, j):
        u = i / SEGMENTS
        v = j / ROWS
        a = (u * 2.0 - 1.0) * HALF_FAN
        taper = max(math.cos(a / HALF_FAN * math.pi * 0.5), 0.0) ** 0.55
        r = EDGE + 0.025 * math.cos(a * 3.0) - (depth * taper + 0.004) * v
        x = 50.0 * r * math.sin(a)
        y = -50.0 * r * math.cos(a)
        z = lift * (1.0 - v) ** 2 * taper
        return (x, y, z), (u, v)

    triangles = []
    for i in range(SEGMENTS):
        for j in range(ROWS):
            a, b, c, d = point(i, j), point(i + 1, j), point(i + 1, j + 1), point(i, j + 1)
            triangles.append((a, b, c))
            triangles.append((a, c, d))
    return triangles


def main():
    write_obj('SM_Aurora_QRibbonThin', ribbon(0.09, 6.0))
    write_obj('SM_Aurora_QRibbonWide', ribbon(0.30, 10.0))
    write_obj('SM_Aurora_QRibbonHair', ribbon(0.035, 3.0))


if __name__ == '__main__':
    main()
