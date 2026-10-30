"""Install the final dominant-light priority on the room without touching other assets."""
import json
import os
from pathlib import Path
import traceback
import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
report = {'passed': False, 'changes': []}
try:
    path = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
    world = unreal.EditorLoadingAndSavingUtils.load_map(path)
    if not world:
        raise RuntimeError('Training room failed to reload')
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.DirectionalLight):
        comp = actor.get_component_by_class(unreal.DirectionalLightComponent)
        priority = 1 if actor.get_actor_label() == 'TrainingRoom_CoolKey' else 0
        comp.set_editor_property('forward_shading_priority', priority)
        report['changes'].append({'actor': actor.get_actor_label(), 'forward_shading_priority': priority})
    if len(report['changes']) != 2:
        raise RuntimeError('Expected exactly one key and one camera-side fill light')
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, path):
        raise RuntimeError('Failed to save the room light priorities')
    report['passed'] = True
except Exception as error:
    report.update(error=str(error), traceback=traceback.format_exc())
    unreal.log_error(traceback.format_exc())
finally:
    (out / 'finalize.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
