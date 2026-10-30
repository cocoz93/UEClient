"""Dump bounds (extent, origin) and material slots of every static mesh under MESH_FOLDER (default Aurora FX meshes). Saves no assets."""
import json
import os
from pathlib import Path

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
folder = os.environ.get('MESH_FOLDER', '/Game/ParagonAurora/FX/Meshes')
rows = []
registry = unreal.AssetRegistryHelpers.get_asset_registry()
for data in registry.get_assets_by_path(folder, recursive=True):
    if str(data.asset_class_path.asset_name) != 'StaticMesh':
        continue
    mesh = unreal.load_asset(str(data.package_name))
    bounds = mesh.get_bounds()
    e, o = bounds.box_extent, bounds.origin
    rows.append({'mesh': str(data.package_name), 'extent': [round(e.x, 1), round(e.y, 1), round(e.z, 1)],
                 'origin': [round(o.x, 1), round(o.y, 1), round(o.z, 1)],
                 'materials': [m.material_interface.get_path_name() if m.material_interface else None
                               for m in mesh.get_editor_property('static_materials')]})
(qa / 'mesh-bounds.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
