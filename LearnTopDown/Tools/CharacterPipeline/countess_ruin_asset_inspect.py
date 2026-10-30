"""Read-only Ruin mesh/material audit. OBJ export reuses the local proven exporter.

author(output) never changes or saves assets and never starts/stops an editor.
Optional reflection/export failures are recorded; the mandatory live meshes must load.
"""
import json
from pathlib import Path

import unreal


MESHES = (
    '/Game/ParagonAurora/FX/Meshes/Aurora/SM_Aurora_Spike_Single',
    '/Game/ParagonAurora/FX/Meshes/Aurora/SM_Aurora_Spike_Single2',
    '/Game/ParagonAurora/FX/Meshes/Debris/SM_Aurora_Fragment',
    '/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_RollingDark_SwordMesh',
    '/Game/ParagonCountess/FX/Meshes/Shapes/SM_BowlWave',
    '/Game/ParagonProps/Monolith/Dusk/Meshes/Grim_Barbican_Spike_A',
    '/Game/ParagonProps/Monolith/Dusk/Meshes/Grim_Barbican_Spike_B',
    '/Game/ParagonRampage/FX/Meshes/Debris/SM_Rock_Shard',
    '/Game/ParagonRampage/FX/Meshes/Debris/SM_Rampage_Rock_Rip_Crater',
    '/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Spline_Claw',
    '/Game/ParagonAurora/FX/Meshes/Ice/SM_Ice_Spikes',
)
MATERIALS = (
    '/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideCore',
    '/Game/TopDown/Characters/Countess/Materials/M_CountessNightTideBlade',
    '/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve',
    '/Game/TopDown/Characters/Countess/Materials/M_CountessSkillShadowCloneDetailed',
)


def _value(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    if isinstance(value, unreal.LinearColor):
        return [value.r, value.g, value.b, value.a]
    return str(value)


def _xyz(v):
    return [v.x, v.y, v.z]


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'assets_saved': False, 'meshes': [], 'materials': [], 'errors': []}
    material_paths = set(MATERIALS)
    lib = unreal.MaterialEditingLibrary

    def attempt(row, name, fn):
        try:
            row[name] = fn()
        except Exception as error:
            row.setdefault('optional_api_errors', {})[name] = str(error)

    for path in MESHES:
        row = {'path': path, 'loaded': False}
        report['meshes'].append(row)
        try:
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                row['error'] = 'Not a loaded StaticMesh'
                continue
            row['loaded'] = True
            box = mesh.get_bounding_box()
            row['bounds'] = {'min': _xyz(box.min), 'max': _xyz(box.max), 'size': _xyz(box.max - box.min)}
            attempt(row, 'vertices_lod0', lambda: mesh.get_num_vertices(0))
            attempt(row, 'triangles_lod0', lambda: mesh.get_num_triangles(0))
            slots = []
            for slot in mesh.get_editor_property('static_materials'):
                material = slot.get_editor_property('material_interface')
                slots.append({'slot': str(slot.get_editor_property('material_slot_name')), 'material': _value(material)})
                if material:
                    material_paths.add(material.get_path_name())
            row['slots'] = slots
            obj_path = output / (mesh.get_name() + '.obj')
            task = unreal.AssetExportTask()
            task.object = mesh
            task.exporter = unreal.StaticMeshExporterOBJ()
            task.filename = str(obj_path)
            task.selected = False
            task.replace_identical = True
            task.prompt = False
            task.automated = True
            task.write_empty_files = False
            try:
                success = unreal.Exporter.run_asset_export_task(task)
                row['export'] = {'passed': bool(success), 'path': str(obj_path), 'axes': 'OBJ=[UE.X,UE.Z,UE.Y]',
                                 'errors': [str(e) for e in task.errors]}
                if success and obj_path.is_file():
                    vertices, faces = [], []
                    for line in obj_path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
                        terms = line.split()
                        if terms and terms[0] == 'v':
                            vertices.append([float(terms[1]), float(terms[3]), float(terms[2])])
                        elif terms and terms[0] == 'f':
                            faces.append([int(t.split('/')[0]) - 1 for t in terms[1:]])
                    geometry_path = output / (mesh.get_name() + '-geometry.json')
                    geometry_path.write_text(json.dumps({'vertices_ue': vertices, 'faces': faces}), encoding='utf-8')
                    row['export'].update(geometry_json=str(geometry_path), vertices=len(vertices), faces=len(faces))
            except Exception as error:
                row['export'] = {'passed': False, 'error': str(error)}
        except Exception as error:
            row['error'] = str(error)

    for path in sorted(material_paths):
        row = {'path': path}
        report['materials'].append(row)
        try:
            material = unreal.load_asset(path)
            if material is None:
                row['error'] = 'Material not found'
                continue
            base = material.get_base_material()
            row.update(class_name=material.get_class().get_name(), base=_value(base))
            for prop in ('blend_mode', 'two_sided', 'shading_model', 'opacity_mask_clip_value'):
                attempt(row, prop, lambda p=prop: _value(base.get_editor_property(p)))
            row['parameters'] = {}
            for kind in ('scalar', 'vector', 'texture'):
                try:
                    values = {}
                    for name in getattr(lib, 'get_' + kind + '_parameter_names')(material):
                        try:
                            if isinstance(material, unreal.MaterialInstanceConstant):
                                value = getattr(lib, 'get_material_instance_' + kind + '_parameter_value')(material, name)
                            else:
                                value = getattr(lib, 'get_material_default_' + kind + '_parameter_value')(base, name)
                            values[str(name)] = _value(value)
                        except Exception as error:
                            values[str(name)] = {'error': str(error)}
                    row['parameters'][kind] = values
                except Exception as error:
                    row['parameters'][kind] = {'error': str(error)}
            properties = {}
            for name in ('MP_OPACITY', 'MP_OPACITY_MASK', 'MP_EMISSIVE_COLOR', 'MP_BASE_COLOR', 'MP_WORLD_POSITION_OFFSET'):
                try:
                    expression = lib.get_material_property_input_node(base, getattr(unreal.MaterialProperty, name))
                    properties[name] = expression.get_name() if expression else None
                except Exception as error:
                    properties[name] = {'error': str(error)}
            row['properties'] = properties
            nodes = []
            row['nodes'] = nodes
            for node in lib.get_material_expressions(base):
                item = {'name': node.get_name(), 'class': node.get_class().get_name()}
                for prop in ('parameter_name', 'default_value', 'param_names', 'texture', 'code',
                             'r', 'g', 'b', 'a', 'const_a', 'const_b', 'exponent', 'coordinate_index',
                             'u_tiling', 'v_tiling', 'speed_x', 'speed_y'):
                    try:
                        item[prop] = _value(node.get_editor_property(prop))
                    except Exception:
                        pass
                attempt(item, 'inputs', lambda n=node: [_value(x) for x in lib.get_inputs_for_material_expression(base, n)])
                nodes.append(item)
        except Exception as error:
            row['error'] = str(error)
    report['passed'] = all(row['loaded'] for row in report['meshes'][:5])
    (output / 'countess-ruin-asset-inspect.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('COUNTESS_RUIN_AUDIT passed=' + str(report['passed']))
    return report
