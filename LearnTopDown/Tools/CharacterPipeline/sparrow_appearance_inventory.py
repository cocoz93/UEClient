"""Read Sparrow material assignments and export original textures for inspection."""
import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
if not qa.is_relative_to(root / 'Saved/QA'):
    raise ValueError('Appearance inspection output must remain inside Saved/QA')


def path(value):
    return value.get_path_name() if value else None


def hashes():
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / 'Content/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue').rglob('*.uasset')}


report = {'read_only': True, 'passed': False}
before = hashes()
try:
    bp = unreal.load_asset('/Game/TopDown/Characters/Sparrow/BP_SparrowCharacter')
    cdo = unreal.get_default_object(bp.generated_class())
    component = cdo.get_editor_property('mesh')
    mesh = component.get_editor_property('skeletal_mesh_asset')
    report['mesh'] = path(mesh)
    report['override_materials'] = [path(m) for m in component.get_editor_property('override_materials')]
    report['materials'] = []
    library = unreal.MaterialEditingLibrary
    for index, slot in enumerate(mesh.get_editor_property('materials')):
        original = slot.get_editor_property('material_interface')
        actual = component.get_material(index)
        item = {'slot': str(slot.get_editor_property('material_slot_name')),
                'source': path(original), 'actual': path(actual), 'matches': actual == original}
        if isinstance(actual, unreal.Material):
            item['textures'] = [path(t) for t in library.get_used_textures(actual)]
            item['vector_parameters'] = {}
            for name in library.get_vector_parameter_names(actual):
                color = library.get_material_default_vector_parameter_value(actual, name)
                item['vector_parameters'][str(name)] = [color.r, color.g, color.b, color.a]
        report['materials'].append(item)
    report['exports'] = []
    for name in ['T_Sparrow_Rogue_CloakHat_RGB', 'T_Sparrow_Rogue_ChestandBag_RGB',
                 'T_Sparrow_Rogue_Torso_Arms_RGB', 'T_Sparrow_Legs_Rogue_Hands_RGB']:
        texture = unreal.load_asset('/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Textures/' + name)
        task = unreal.AssetExportTask()
        task.object = texture
        task.exporter = unreal.TextureExporterPNG()
        task.filename = str(qa / (name + '.png'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        report['exports'].append({'texture': path(texture), 'file': task.filename,
                                  'passed': unreal.Exporter.run_asset_export_task(task)})
    report['source_unchanged'] = before == hashes()
    report['passed'] = report['source_unchanged'] and all(m['matches'] and m['actual'] for m in report['materials'])
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'appearance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('SPARROW_APPEARANCE_INSPECTION ' + json.dumps({'passed': report['passed'], 'output': str(qa)}))
    unreal.SystemLibrary.quit_editor()
