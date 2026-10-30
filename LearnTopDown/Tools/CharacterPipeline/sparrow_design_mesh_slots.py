"""Validate the material sections of this review's generated, single-material meshes."""
import json
from pathlib import Path

import unreal


FOLDERS = (
    '/Game/TopDown/Characters/Sparrow/FX/FDesign20261027',
    '/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027',
    '/Game/TopDown/Characters/Sparrow/FX/EDesign20261027',
    '/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027',
)


def author(output):
    """Bind sections to slot zero only on owned meshes with exactly one material."""
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    report = {'passed': False, 'meshes': [], 'changed': []}
    for folder in FOLDERS:
        for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=True, include_folder=False):
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                continue
            slots = mesh.get_editor_property('static_materials')
            if len(slots) != 1 or not slots[0].get_editor_property('material_interface'):
                raise RuntimeError('Expected one populated material on generated mesh: ' + path)
            row = {'path': path, 'sections': []}
            changed = False
            for lod in range(subsystem.get_lod_count(mesh)):
                for section in range(mesh.get_num_sections(lod)):
                    before = subsystem.get_lod_material_slot(mesh, lod, section)
                    if before != 0:
                        subsystem.set_lod_material_slot(mesh, 0, lod, section)
                        changed = True
                    after = subsystem.get_lod_material_slot(mesh, lod, section)
                    row['sections'].append({'lod': lod, 'section': section, 'before': before, 'after': after})
                    if after != 0:
                        raise RuntimeError('Generated material section remains invalid: ' + path)
            if changed:
                if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
                    raise RuntimeError('Cannot save corrected material sections: ' + path)
                report['changed'].append(path)
            report['meshes'].append(row)
    report['passed'] = bool(report['meshes'])
    (Path(output)/'design-mesh-material-slots.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
