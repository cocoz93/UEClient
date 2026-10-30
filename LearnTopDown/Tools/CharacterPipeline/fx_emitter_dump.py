"""Dump particle systems' emitters (name, material, mesh, modules with key distributions) and static meshes' materials.
FX_DUMP = particle paths, MESH_DUMP = mesh paths, MATERIAL_DUMP = material paths. Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SYSTEMS = [p for p in os.environ.get('FX_DUMP', '').split(',') if p]
MESHES = [p for p in os.environ.get('MESH_DUMP', '').split(',') if p]
MATERIALS = [p for p in os.environ.get('MATERIAL_DUMP', '').split(',') if p]
report = {'passed': False, 'read_only': True, 'systems': [], 'meshes': [], 'materials': []}


def describe(value):
    item = {'value': str(value)[:300]}
    try:
        dist = value.get_editor_property('distribution')
    except Exception:
        return item
    if dist:
        item['class'] = dist.get_class().get_name()
        for field in ('constant', 'min', 'max', 'constant_curve', 'parameter_name', 'min_input', 'max_input', 'min_output', 'max_output', 'param_mode'):
            try:
                item[field] = str(dist.get_editor_property(field))[:600]
            except Exception:
                pass
    return item


try:
    for path in SYSTEMS:
        system = unreal.load_asset(path)
        prefix = system.get_path_name() + ':'
        row = {'system': path, 'emitters': []}
        # Cascade 이미터 속성은 파이썬에 안 열려 있다. 시스템에 딸린 객체를 경로·클래스와 함께 모두 적는다(경로에 이미터·LOD 순서가 드러난다).
        objects = [o for o in unreal.ObjectIterator(unreal.Object) if unreal.SystemLibrary.get_path_name(o).startswith(prefix)]
        for obj in objects:
            entry = {'class': obj.get_class().get_name(), 'path': unreal.SystemLibrary.get_path_name(obj)[len(prefix):]}
            for prop in ('material', 'mesh', 'start_size', 'start_location', 'start_velocity', 'start_lifetime', 'size_scale',
                         'lifetime', 'spawn_rate', 'rate', 'emitter_duration', 'emitter_origin', 'emitter_rotation',
                         'mesh_materials', 'dynamic_params', 'start_color', 'start_alpha', 'color_scale_over_life', 'alpha_scale_over_life'):
                try:
                    entry[prop] = describe(obj.get_editor_property(prop))
                except Exception:
                    pass
            row['emitters'].append(entry)
        report['systems'].append(row)
    for path in MESHES:
        mesh = unreal.load_asset(path)
        entry = {'mesh': path, 'bounds': str(mesh.get_bounds().box_extent), 'materials': []}
        for slot in mesh.get_editor_property('static_materials'):
            material = slot.get_editor_property('material_interface')
            base = material.get_base_material() if material else None
            info = {'material': material.get_path_name() if material else None, 'base': base.get_path_name() if base else None}
            if base:
                lib = unreal.MaterialEditingLibrary
                info['scalars'] = [str(n) for n in lib.get_scalar_parameter_names(material)]
                info['blend'] = str(base.get_editor_property('blend_mode'))
                opacity = lib.get_material_property_input_node(base, unreal.MaterialProperty.MP_OPACITY)
                emissive = lib.get_material_property_input_node(base, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                info['opacity_input'] = opacity.get_class().get_name() if opacity else None
                info['emissive_input'] = emissive.get_class().get_name() if emissive else None
            entry['materials'].append(info)
        report['meshes'].append(entry)
    lib = unreal.MaterialEditingLibrary
    for path in MATERIALS:
        material = unreal.load_asset(path)
        if material is None:
            report['materials'].append({'path': path, 'error': 'missing'})
            continue
        base = material.get_base_material() if hasattr(material, 'get_base_material') else material
        info = {'path': path, 'base': base.get_path_name(), 'scalars': {}, 'vectors': {}, 'graph_controls': []}
        is_instance = isinstance(material, unreal.MaterialInstanceConstant)
        for name in lib.get_scalar_parameter_names(material):
            try:
                value = lib.get_material_instance_scalar_parameter_value(material, name) if is_instance else lib.get_material_default_scalar_parameter_value(base, name)
                info['scalars'][str(name)] = value
            except Exception as error:
                info['scalars'][str(name)] = {'error': str(error)}
        for name in lib.get_vector_parameter_names(material):
            try:
                value = lib.get_material_instance_vector_parameter_value(material, name) if is_instance else lib.get_material_default_vector_parameter_value(base, name)
                info['vectors'][str(name)] = [value.r, value.g, value.b, value.a]
            except Exception as error:
                info['vectors'][str(name)] = {'error': str(error)}
        info['blend_mode'] = str(base.get_editor_property('blend_mode'))
        info['two_sided'] = base.get_editor_property('two_sided')
        for node in lib.get_material_expressions(base):
            kind = node.get_class().get_name()
            if kind not in ('MaterialExpressionDynamicParameter', 'MaterialExpressionParticleColor',
                            'MaterialExpressionVertexColor', 'MaterialExpressionTextureCoordinate'):
                continue
            control = {'class': kind}
            for prop in ('param_names', 'default_value', 'coordinate_index', 'u_tiling', 'v_tiling'):
                try:
                    control[prop] = str(node.get_editor_property(prop))
                except Exception:
                    pass
            info['graph_controls'].append(control)
        report['materials'].append(info)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'fx-dump.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
if os.environ.get('FX_DUMP_KEEP_EDITOR') != '1':
    unreal.SystemLibrary.quit_editor()
