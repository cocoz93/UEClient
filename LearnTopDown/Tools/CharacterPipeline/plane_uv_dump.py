"""엔진 기본 판(/Engine/BasicShapes/Plane)의 꼭짓점 위치와 UV를 적는다(읽기만). 판에 띠를 그릴 때 U가 X의 어느 쪽에서 0인지 보려는 것(10-20 A 시안 7 빛줄기).
산출: plane-uv.json (꼭짓점마다 [x, y, z, u, v])."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
report = {'passed': False}
try:
    mesh = unreal.load_asset('/Engine/BasicShapes/Plane.Plane')
    vertices, triangles, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
    report['vertices'] = [[v.x, v.y, v.z, uv.x, uv.y] for v, uv in zip(vertices, uvs)]
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'plane-uv.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
