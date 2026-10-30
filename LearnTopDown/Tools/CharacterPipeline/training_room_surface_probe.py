"""Inspect original floor normals, materials and authored demo transforms without saving."""
import json
import os
from pathlib import Path
import traceback
import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
report = {}
try:
    mesh = unreal.load_asset('/Game/MedievalDungeon/Meshes/Architecture/Dungeon/SM_Floor')
    task = unreal.AssetExportTask()
    task.object = mesh
    task.filename = str(out / 'floor.obj')
    task.automated = True
    task.prompt = False
    task.exporter = unreal.StaticMeshExporterOBJ()
    report['exported'] = unreal.Exporter.run_asset_export_task(task)
    mat = unreal.load_asset('/Game/MedievalDungeon/Materials/M_BrickFloor_Clean_Inst')
    lib = unreal.MaterialEditingLibrary
    report['parameters'] = {}
    for kind in ('scalar', 'vector', 'texture'):
        names = getattr(lib, 'get_' + kind + '_parameter_names')(mat)
        values = {}
        for name in names:
            value = getattr(lib, 'get_material_instance_' + kind + '_parameter_value')(mat, name)
            values[str(name)] = str(value)
        report['parameters'][kind] = values
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/MedievalDungeon/Maps/Demonstration')
    report['demo_floors'] = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp and comp.get_editor_property('static_mesh') == mesh:
            report['demo_floors'].append({'transform': str(actor.get_actor_transform()),
                'materials': [str(comp.get_material(i)) for i in range(comp.get_num_materials())]})
            if len(report['demo_floors']) >= 3:
                break
except Exception as error:
    report.update(error=str(error), traceback=traceback.format_exc())
finally:
    (out / 'surface.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
