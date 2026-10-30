"""93rd Aurora round: read-only facts about candidate pack meshes for the Q sword wave (swipe meshes) and F icicles
(spike meshes) - bounds, UV0 range from an OBJ export, material slots and every material parameter with its value.
Writes aurora-q93-inspect.json. Saves no assets."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
lib = unreal.MaterialEditingLibrary
MESHES = (
    '/Game/ParagonKwang/FX/Meshes/Shapes/SM_Kwang_Ultimate_Swipe',
    '/Game/ParagonRampage/FX/Meshes/Shapes/SM_Rampage_Leap_Swipe',
    '/Game/ParagonSerath/FX/Meshes/Hero_Specific/SM_Serath_QSlash',
    '/Game/ParagonSerath/FX/Meshes/Hero_Specific/Sm_Serath_WingflapSwipe',
    '/Game/ParagonCountess/FX/Meshes/Shapes/SM_Countess_UltSwingMesh',
    '/Game/ParagonCountess/FX/Meshes/Shapes/SM_Blink_XSlashMesh',
    '/Game/ParagonMinions/FX/Meshes/Shapes/SM_Vamp_UltSwingMesh',
    '/Game/ParagonAurora/FX/Meshes/Aurora/SM_Aurora_Spike_Single',
    '/Game/ParagonAurora/FX/Meshes/Aurora/SM_Aurora_Spike_Single2',
    '/Game/ParagonAurora/FX/Meshes/Ice/SM_Ice_Spikes',
)
MATERIALS = (
    '/Game/ParagonKwang/FX/Materials/Shockwave/M_Kwang_Sword_Swipe_Inst',
    '/Game/ParagonKwang/FX/Materials/Trails/M_Sword_ClearAPath_Swipe',
    '/Game/ParagonRampage/FX/Materials/Trails/M_Rampage_Leap_Swipe',
    '/Game/ParagonSerath/FX/Materials/Trails/M_WingSwipeHoly',
    '/Game/ParagonCountess/FX/Materials/Trails/m_CountessUltSwing',
    '/Game/ParagonCountess/FX/Materials/Trails/M_MeshSwipe',
)


def value(v):
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    if isinstance(v, unreal.LinearColor):
        return [round(v.r, 3), round(v.g, 3), round(v.b, 3), round(v.a, 3)]
    return str(v)


def xyz(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


result = {'meshes': [], 'materials': []}
try:
    names = set(MATERIALS)
    for path in MESHES:
        row = {'path': path}
        result['meshes'].append(row)
        mesh = unreal.load_asset(path)
        if not isinstance(mesh, unreal.StaticMesh):
            row['error'] = 'not loaded'
            continue
        box = mesh.get_bounding_box()
        row['min'], row['max'] = xyz(box.min), xyz(box.max)
        row['slots'] = []
        for slot in mesh.get_editor_property('static_materials'):
            material = slot.get_editor_property('material_interface')
            row['slots'].append(value(material))
            if material:
                names.add(material.get_path_name().split('.')[0])
        obj = qa / (mesh.get_name() + '.obj')
        task = unreal.AssetExportTask()
        task.object = mesh
        task.exporter = unreal.StaticMeshExporterOBJ()
        task.filename = str(obj)
        task.selected = False
        task.replace_identical = True
        task.prompt = False
        task.automated = True
        try:
            if unreal.Exporter.run_asset_export_task(task) and obj.is_file():
                us, vs, count = [], [], 0
                for line in obj.read_text(encoding='utf-8-sig', errors='replace').splitlines():
                    terms = line.split()
                    if terms and terms[0] == 'vt':
                        us.append(float(terms[1]))
                        vs.append(float(terms[2]))
                    elif terms and terms[0] == 'v':
                        count += 1
                row['vertices'] = count
                if us:
                    row['uv'] = [round(min(us), 3), round(max(us), 3), round(min(vs), 3), round(max(vs), 3)]
        except Exception as error:
            row['export_error'] = str(error)
    for path in sorted(names):
        row = {'path': path}
        result['materials'].append(row)
        material = unreal.load_asset(path)
        if material is None:
            row['error'] = 'not loaded'
            continue
        base = material.get_base_material()
        row['class'] = material.get_class().get_name()
        row['base'] = value(base)
        try:
            row['blend'] = value(base.get_editor_property('blend_mode'))
        except Exception as error:
            row['blend'] = str(error)
        for kind in ('scalar', 'vector', 'texture'):
            values = {}
            try:
                for name in getattr(lib, 'get_' + kind + '_parameter_names')(material):
                    try:
                        if isinstance(material, unreal.MaterialInstanceConstant):
                            got = getattr(lib, 'get_material_instance_' + kind + '_parameter_value')(material, name)
                        else:
                            got = getattr(lib, 'get_material_default_' + kind + '_parameter_value')(base, name)
                        values[str(name)] = value(got)
                    except Exception as error:
                        values[str(name)] = 'error ' + str(error)
            except Exception as error:
                values = 'error ' + str(error)
            row[kind] = values
    result['passed'] = all('error' not in row for row in result['meshes'])
except Exception:
    result['passed'] = False
    result['error'] = traceback.format_exc()
(qa / 'aurora-q93-inspect.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
