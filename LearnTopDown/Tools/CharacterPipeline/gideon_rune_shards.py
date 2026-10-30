"""Gideon W border: the inner rune ring mesh carries small triangle shards outside its drawn circle.
SHARD_MODE=dump  -> write the vertex radius histogram (plane = the mesh's two wide axes).
SHARD_MODE=build -> duplicate the mesh to DEST and delete every polygon with a vertex beyond SHARD_RADIUS, then save."""
import json
import math
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
SOURCE = '/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Rune_Ring_Inner'
DEST = '/Game/TopDown/Characters/Gideon/FX/SM_Rune_Ring_Inner_NoShards'
MODE = os.environ.get('SHARD_MODE', 'dump')
LIMIT = float(os.environ.get('SHARD_RADIUS', '0'))
report = {'mode': MODE}


def element_id(cls, value):
    # IDValue는 블루프린트 읽기 전용이라 생성자 인자로 넣는다.
    return cls(value)


def radius(position):
    # 고리는 YZ 면(두께 축 X)이다.
    return math.hypot(position.y, position.z)


try:
    mesh = unreal.load_asset(SOURCE)
    if MODE == 'build':
        if unreal.EditorAssetLibrary.does_asset_exist(DEST):
            unreal.EditorAssetLibrary.delete_asset(DEST)
        mesh = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
    description = mesh.get_static_mesh_description(0)
    count = description.get_vertex_count()
    radii = []
    for index in range(count):
        vertex = element_id(unreal.VertexID, index)
        radii.append((index, radius(description.get_vertex_position(vertex))))
    report['vertices'] = count
    report['polygons_before'] = description.get_polygon_count()
    histogram = {}
    for _, value in radii:
        key = int(value // 2) * 2
        histogram[key] = histogram.get(key, 0) + 1
    report['radius_histogram_2cm'] = dict(sorted(histogram.items()))
    if MODE == 'build':
        if LIMIT <= 0:
            raise ValueError('SHARD_RADIUS required')
        doomed = set()
        for index, value in radii:
            if value > LIMIT:
                for polygon in description.get_vertex_connected_polygons(element_id(unreal.VertexID, index)):
                    doomed.add(polygon.get_editor_property('id_value'))
        for polygon in sorted(doomed):
            description.delete_polygon(element_id(unreal.PolygonID, polygon))
        report['polygons_deleted'] = len(doomed)
        report['polygons_after'] = description.get_polygon_count()
        mesh.build_from_static_mesh_descriptions([description])
        report['bounds_after'] = str(mesh.get_bounds().box_extent)
        report['saved'] = unreal.EditorAssetLibrary.save_asset(DEST, only_if_is_dirty=False)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(qa / 'rune-shards.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
