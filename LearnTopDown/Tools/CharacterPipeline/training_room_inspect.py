"""Read-only UE 5.8 inventory of the downloaded dungeon and preserved hero field."""
import json
import os
from pathlib import Path
import sys
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
OUT = Path(os.environ['SPARROW_QA_OUTPUT'])


def vec(v):
    return [v.x, v.y, v.z]


def main():
    report = {'passed': False, 'engine': unreal.SystemLibrary.get_engine_version(),
              'assets': [], 'meshes': [], 'failures': []}
    try:
        paths = unreal.EditorAssetLibrary.list_assets('/Game/MedievalDungeon', recursive=True, include_folder=False)
        for path in paths:
            asset = unreal.load_asset(path)
            if not asset:
                report['failures'].append(path)
                continue
            report['assets'].append({'path': path, 'class': asset.get_class().get_name()})
            if isinstance(asset, unreal.StaticMesh):
                box = asset.get_bounding_box()
                component = unreal.StaticMeshComponent()
                component.set_static_mesh(asset)
                materials = [component.get_material(i).get_path_name() if component.get_material(i) else None
                             for i in range(component.get_num_materials())]
                report['meshes'].append({'path': path, 'min': vec(box.min), 'max': vec(box.max),
                                        'materials': materials, 'lods': asset.get_num_lods()})
        demo = unreal.EditorLoadingAndSavingUtils.load_map('/Game/MedievalDungeon/Maps/Demonstration')
        if not demo:
            raise RuntimeError('Downloaded demonstration map failed to load')
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        report['demo_actor_count'] = len(actors)
        report['demo_actor_classes'] = sorted(set(a.get_class().get_name() for a in actors))
        world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/TopDown/Lvl_TopDown')
        if not world:
            raise RuntimeError('Preserved Countess field failed to load')
        mode = world.get_world_settings().get_editor_property('default_game_mode')
        report['original_game_mode'] = mode.get_path_name() if mode else None
        report['starts'] = [{'location': vec(a.get_actor_location()), 'rotation': str(a.get_actor_rotation())}
                            for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)]
        report['passed'] = len(report['assets']) >= 409 and not report['failures'] and bool(mode)
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
        unreal.log_error(traceback.format_exc())
    finally:
        (OUT / 'inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        unreal.SystemLibrary.quit_editor()


main()
