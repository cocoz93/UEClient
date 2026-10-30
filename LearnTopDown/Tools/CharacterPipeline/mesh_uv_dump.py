"""Dump a static mesh's LOD0 section 0 vertices with their UVs (read-only), so a texture can be drawn in that UV layout.
UV_DUMP_MESH = mesh object path. Writes mesh-uv.json: [[x, y, z, u, v], ...] plus the vertex and triangle counts."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
report = {'passed': False}
try:
    mesh = unreal.load_asset(os.environ['UV_DUMP_MESH'])
    if mesh is None:
        raise RuntimeError('Mesh missing: ' + os.environ['UV_DUMP_MESH'])
    vertices, triangles, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
    report['vertices'] = len(vertices)
    report['triangles'] = len(triangles) // 3
    report['indices'] = list(triangles)
    report['points'] = [[v.x, v.y, v.z, uv.x, uv.y] for v, uv in zip(vertices, uvs)]
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'mesh-uv.json').write_text(json.dumps(report), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
