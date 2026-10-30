"""Install environment-only resource copies on the existing final room."""
import json
import os
from pathlib import Path
import sys
import traceback
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / 'Tools/CharacterPipeline'))
from training_room_resources import budget_material, changes
from training_room_build import floor_material

out = Path(os.environ['SPARROW_QA_OUTPUT'])
report = {'passed': False, 'environment_only': True, 'texture_limit': 2048}
try:
    path = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
    world = unreal.EditorLoadingAndSavingUtils.load_map(path)
    if not world:
        raise RuntimeError('Room failed to load for texture-budget installation')
    floor_material()
    count = 0
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(component.get_num_materials()):
                source = component.get_material(slot)
                # Resolve our earlier instances back to their original parent for idempotent updates.
                if isinstance(source, unreal.MaterialInstanceConstant) and source.get_path_name().startswith('/Game/TopDown/TrainingRoom/Materials/MI_Room_'):
                    source = source.get_editor_property('parent')
                material = budget_material(source)
                if material != component.get_material(slot):
                    # SetMaterial is a runtime setter: explicitly dirty the external actor package.
                    actor.modify()
                    component.modify()
                    component.set_material(slot, material)
                    count += 1
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, path):
        raise RuntimeError('Room budget changes could not be saved')
    report.update(passed=True, material_slots_updated=count, textures=changes,
                  external_actor_packages_explicitly_dirtied=True)
except Exception as error:
    report.update(error=str(error), traceback=traceback.format_exc())
    unreal.log_error(traceback.format_exc())
finally:
    (out / 'budget.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
