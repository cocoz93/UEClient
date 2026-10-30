"""Attach the isolated three-floor encounter to the authored Trial Tower map."""
import json
from pathlib import Path
import unreal
import environment as hall
import combat_animation_build

DEST = '/Game/TopDown/TrialTower/Combat'
MONSTER = DEST + '/BP_TrialTowerMinion'
PACK = '/Game/ParagonMinions/Characters/Minions/Down_Minions/'


def build(output=None):
    animation_report = combat_animation_build.build(output)
    world = unreal.EditorLoadingAndSavingUtils.load_map(hall.MAP)
    if not world:
        raise RuntimeError('Could not load Trial Tower')
    assets = unreal.EditorAssetLibrary
    assets.make_directory(DEST)
    if assets.does_asset_exist(MONSTER):
        bp = unreal.load_asset(MONSTER)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', unreal.TrialTowerMonster)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'BP_TrialTowerMinion', DEST, unreal.Blueprint, factory)
    if not bp:
        raise RuntimeError('Could not create tower-owned minion Blueprint')
    cls = assets.load_blueprint_class(MONSTER)
    cdo = unreal.get_default_object(cls)
    cdo.modify()
    mesh = hall.load(PACK + 'Meshes/Minion_Lane_Melee_Dawn')
    component = cdo.get_editor_property('mesh')
    component.modify()
    component.set_skeletal_mesh_asset(mesh)
    component.set_anim_instance_class(assets.load_blueprint_class(combat_animation_build.ASSET))
    animations = {'idle_animation': 'NonCombat_Idle', 'run_animation': 'Combat_JogFwd',
                  'death_animation': 'Death_A', 'attack_animation': 'Attack_A'}
    skeleton = mesh.get_editor_property('skeleton')
    for prop, name in animations.items():
        animation = hall.load(PACK + 'Animations/Melee/' + name)
        if animation.get_editor_property('skeleton') != skeleton:
            raise RuntimeError('Incompatible minion animation: ' + name)
        cdo.set_editor_property(prop, animation)
    if not unreal.BlueprintEditorLibrary.compile_blueprint(bp):
        raise RuntimeError('Tower minion Blueprint did not compile')
    if not assets.save_loaded_asset(bp, False):
        raise RuntimeError('Could not save tower minion Blueprint')
    instances = [a for a in hall.ACTORS.get_all_level_actors() if isinstance(a, unreal.TrialTowerEncounter)]
    if len(instances) > 1:
        raise RuntimeError('Duplicate Trial Tower encounter actors')
    actor = instances[0] if instances else hall.ACTORS.spawn_actor_from_class(unreal.TrialTowerEncounter, unreal.Vector())
    actor.modify()
    actor.set_actor_label('TrialTower_Encounter')
    actor.set_folder_path('TrialTower/Combat')
    actor.tags = ['TrialTowerEncounter']
    actor.set_editor_property('monster_class', assets.load_blueprint_class(MONSTER))
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, hall.MAP):
        raise RuntimeError('Could not save Tower encounter placement')
    report = {'map': hall.MAP, 'monster': MONSTER, 'mesh': mesh.get_path_name(),
              'animations': animations, 'animation_blueprint': animation_report['asset'],
              'floors': [8, 12, 16], 'existing_game_mode_modified': False}
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
        (Path(output)/'combat-build.json').write_text(json.dumps(report, indent=2),encoding='utf-8')
    return report
