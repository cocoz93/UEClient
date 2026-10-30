"""Read Sparrow arrow geometry and export LOD 0 to Saved/QA without saving assets."""
import hashlib
import json
import math
import os
from pathlib import Path
import traceback

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
qa = Path(os.environ.get('SPARROW_QA_OUTPUT', str(root / 'Saved/QA/Sparrow/ArrowGeometry'))).resolve()
if not qa.is_relative_to(root / 'Saved/QA'):
    raise ValueError('Arrow geometry output must be inside this project Saved/QA')
qa.mkdir(parents=True, exist_ok=True)

ASSET = '/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow'
package = root / 'Content/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow'
report_path = qa / 'arrow-geometry-inventory.json'
report = {'passed': False, 'read_only': True, 'asset': ASSET, 'asset_save_requested': False}


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def hash_packages():
    return {str(package.with_suffix(suffix)): hashlib.sha256(package.with_suffix(suffix).read_bytes()).hexdigest()
            for suffix in ('.uasset', '.uexp', '.ubulk') if package.with_suffix(suffix).is_file()}


def ranges(points):
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    size = [maximum[axis] - minimum[axis] for axis in range(3)]
    order = sorted(range(3), key=lambda axis: size[axis], reverse=True)
    return {'minimum': minimum, 'maximum': maximum, 'size': size,
            'long_axis': 'XYZ'[order[0]],
            'long_axis_dominance': size[order[0]] / max(size[order[1]], 0.000001)}


def geometry_profile(points):
    bounds = ranges(points)
    axis = 'XYZ'.index(bounds['long_axis'])
    transverse = [index for index in range(3) if index != axis]
    minimum, maximum = bounds['minimum'][axis], bounds['maximum'][axis]
    length = maximum - minimum
    center = [(bounds['minimum'][index] + bounds['maximum'][index]) * 0.5 for index in range(3)]
    sections = []
    for index in range(16):
        low = minimum + length * index / 16.0
        high = minimum + length * (index + 1) / 16.0
        section = [point for point in points if low <= point[axis] and
                   (point[axis] < high or (index == 15 and point[axis] <= high))]
        radii = [math.sqrt(sum((point[t] - center[t]) ** 2 for t in transverse)) for point in section]
        sections.append({'axial_minimum': low, 'axial_maximum': high, 'vertices': len(section),
                         'maximum_transverse_radius': max(radii) if radii else None,
                         'mean_transverse_radius': sum(radii) / len(radii) if radii else None})
    bounds['axial_sections'] = sections
    bounds['end_regions'] = {}
    for name, region in (
            ('minimum_end', [point for point in points if point[axis] <= minimum + length * 0.1]),
            ('maximum_end', [point for point in points if point[axis] >= maximum - length * 0.1])):
        bounds['end_regions'][name] = {'vertices': len(region),
            'transverse_size': [max(point[t] for point in region) - min(point[t] for point in region)
                                for t in transverse] if region else [], 'coordinates': region}
    bounds['tip_and_fletching_classified'] = False
    bounds['tip_and_fletching_note'] = 'Inspect the OBJ and axial sections before assigning a forward sign'
    return bounds


try:
    report['source_hashes_before'] = hash_packages()
    mesh = unreal.load_asset(ASSET)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError('Sparrow arrow static mesh is unavailable')
    box = mesh.get_bounding_box()
    bounds = mesh.get_bounds()
    report['unreal_local_bounding_box'] = ranges([xyz(box.min), xyz(box.max)])
    report['unreal_local_bounds'] = {'origin': xyz(bounds.origin), 'extent': xyz(bounds.box_extent),
                                    'sphere_radius': float(bounds.sphere_radius)}
    obj_path = qa / 'SM_Sparrow_Arrow.obj'
    task = unreal.AssetExportTask()
    task.object = mesh
    task.exporter = unreal.StaticMeshExporterOBJ()
    task.filename = str(obj_path)
    task.selected = False
    task.replace_identical = True
    task.prompt = False
    task.automated = True
    task.write_empty_files = False
    report['export'] = {'requested_path': str(obj_path), 'automated': True, 'prompt': False,
                        'lod': 0, 'unreal_to_obj_axes': '[X,Z,Y]', 'vertex_available': False}
    try:
        exported = unreal.Exporter.run_asset_export_task(task)
        report['export'].update(returned_success=bool(exported), errors=[str(value) for value in task.errors])
        if exported and obj_path.is_file() and obj_path.stat().st_size > 0:
            obj_vertices = []
            for line in obj_path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[0] == 'v':
                    obj_vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            # UE 5.8 EditorExporters.cpp writes OBJ vertices as Unreal X,Z,Y.
            vertices = sorted(set((point[0], point[2], point[1]) for point in obj_vertices))
            if vertices:
                vertices = [list(point) for point in vertices]
                report['export'].update(vertex_available=True, obj_vertex_count=len(obj_vertices),
                    unique_vertex_count=len(vertices), obj_bytes=obj_path.stat().st_size,
                    obj_sha256=hashlib.sha256(obj_path.read_bytes()).hexdigest())
                report['exported_geometry_unreal_axes'] = geometry_profile(vertices)
                report['vertices_unreal_axes'] = vertices
                source_size = report['unreal_local_bounding_box']['size']
                exported_size = report['exported_geometry_unreal_axes']['size']
                report['export']['bounding_box_size_delta'] = [exported_size[i] - source_size[i] for i in range(3)]
    except Exception as error:
        report['export']['error'] = str(error)
        report['export']['traceback'] = traceback.format_exc()

    native_path = Path(os.environ.get('SPARROW_NATIVE_INVENTORY', str(
        root / 'Saved/QA/Sparrow/inventory-native/sparrow-native-inventory.json')))
    report['original_fx_inventory'] = {'available': native_path.is_file(), 'source': str(native_path)}
    if native_path.is_file():
        native = json.loads(native_path.read_text(encoding='utf-8-sig'))
        facts = []
        for asset in native['assets']:
            if '/Skins/Rogue/' not in asset.get('path', '') or not any(
                    asset['path'].endswith('/' + name + '.' + name)
                    for name in ('P_Sparrow_PrimaryRogue', 'P_Sparrow_UltArrow')):
                continue
            meshes = []
            for emitter in asset.get('emitters', []):
                for index, lod in enumerate(emitter.get('lods', [])):
                    type_data = lod.get('type_data', {})
                    mesh_path = type_data.get('properties', {}).get('Mesh')
                    if not mesh_path:
                        continue
                    rotations = [{'module': module['class'], 'properties': module['properties'],
                                  'distributions': module.get('inner_objects', [])}
                                 for module in lod.get('modules', []) if 'MeshRotation' in module['class']]
                    meshes.append({'emitter': emitter.get('properties', {}).get('EmitterName'),
                                   'lod': index, 'enabled': lod.get('enabled'), 'mesh': mesh_path,
                                   'mesh_rotations': rotations})
            facts.append({'system': asset['path'], 'mesh_emitters': meshes,
                          'contains_sparrow_arrow_mesh': any('SM_Sparrow_Arrow' in item['mesh'] for item in meshes)})
        report['original_fx_inventory']['systems'] = facts
    report['source_hashes_after'] = hash_packages()
    report['source_packages_unchanged'] = report['source_hashes_before'] == report['source_hashes_after']
    report['passed'] = report['source_packages_unchanged'] and bool(report['source_hashes_before'])
except Exception as error:
    report['error'] = str(error)
    report['traceback'] = traceback.format_exc()
    unreal.log_error(traceback.format_exc())
finally:
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('SPARROW_ARROW_GEOMETRY ' + json.dumps({'passed': report['passed'], 'report': str(report_path),
               'vertex_available': report.get('export', {}).get('vertex_available', False)}))
    unreal.SystemLibrary.quit_editor()
