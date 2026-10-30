"""Per material section (polygon group) vertex height range and radius range of a static mesh, plus a height histogram.
SECTION_MESH = content path. Saves no assets."""
import json
import math
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
MESH = os.environ['SECTION_MESH']
report = {'mesh': MESH}
try:
    mesh = unreal.load_asset(MESH)
    report['bounds'] = str(mesh.get_bounds())
    report['materials'] = [str(s.get_editor_property('material_slot_name')) for s in mesh.get_editor_property('static_materials')]
    description = mesh.get_static_mesh_description(0)
    report['groups'] = []
    for group in range(description.get_polygon_group_count()):
        polygons = description.get_polygon_group_polygons(unreal.PolygonGroupID(group))
        vertices = set()
        for polygon in polygons:
            for vertex in description.get_polygon_vertices(polygon):
                vertices.add(vertex.get_editor_property('id_value'))
        positions = [description.get_vertex_position(unreal.VertexID(v)) for v in vertices]
        heights = sorted(p.z for p in positions)
        radii = [math.hypot(p.x, p.y) for p in positions]
        histogram = {}
        for z in heights:
            key = int(z // 20) * 20
            histogram[key] = histogram.get(key, 0) + 1
        report['groups'].append({'group': group, 'polygons': len(polygons), 'vertices': len(vertices),
                                 'z_min': round(heights[0], 1) if heights else None, 'z_max': round(heights[-1], 1) if heights else None,
                                 'r_min': round(min(radii), 1) if radii else None, 'r_max': round(max(radii), 1) if radii else None,
                                 'z_hist_20cm': dict(sorted(histogram.items()))})
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'mesh-sections.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
