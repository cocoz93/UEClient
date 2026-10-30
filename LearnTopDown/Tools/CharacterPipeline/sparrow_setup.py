"""Install only project-owned Sparrow assets and a field cloned from the Countess scene."""
import json
import os
from pathlib import Path
import sys
import traceback

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / "Tools/CharacterPipeline"))
from baseline import verify

qa = Path(os.environ["SPARROW_QA_OUTPUT"]).resolve()
if not qa.is_relative_to(root / "Saved/QA"):
    raise ValueError("Setup output must stay in this project Saved/QA")
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
profile_path = root / "Tools/CharacterPipeline/Profiles/sparrow.json"
profile = json.loads(profile_path.read_text(encoding="utf-8"))
baselines = [path for path in (root / "Saved/QA/CharacterPipeline").glob("baseline-*/baseline.json")
             if "Content/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue.uasset"
             in json.loads(path.read_text(encoding="utf-8"))["protected_hashes"]]
if not baselines:
    raise RuntimeError("Capture the original Sparrow source baseline before setup")
baseline = max(baselines, key=lambda path: path.stat().st_mtime_ns)

HERO = "/Game/ParagonSparrow/Characters/Heroes/Sparrow"
DEST = "/Game/TopDown/Characters/Sparrow/Animations"


def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError("Missing required asset: " + path)
    return asset


def duplicate(source, destination):
    asset = unreal.load_asset(destination)
    if asset is None:
        asset = unreal.EditorAssetLibrary.duplicate_asset(source, destination)
    if asset is None:
        raise RuntimeError("Could not create project-owned asset: " + destination)
    return asset


def blueprint(destination, parent_path):
    asset = unreal.load_asset(destination)
    if asset is None:
        parent = unreal.load_class(None, parent_path)
        if parent is None:
            raise RuntimeError("Native parent is not compiled: " + parent_path)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        folder, name = destination.rsplit("/", 1)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, factory)
    if asset is None:
        raise RuntimeError("Could not create Blueprint: " + destination)
    return asset


try:
    check_before = verify(baseline)
    if not check_before["passed"]:
        raise RuntimeError("Original assets changed before installation: " + str(check_before["mismatches"]))
    animation = duplicate(HERO + "/Sparrow_AnimBlueprint", DEST + "/ABP_Sparrow_TopDown")
    primary = duplicate(HERO + "/Animations/Primary_Fire_Med_Montage", DEST + "/AM_Sparrow_Primary")
    unreal.SystemLibrary.execute_console_command(None, "SparrowAssetQA.Configure")
    config_path = qa / "sparrow-configuration.json"
    if not config_path.exists():
        raise RuntimeError("SparrowAssetQA.Configure did not write its report")
    configuration = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if not configuration.get("passed"):
        raise RuntimeError("Animation configuration failed: " + str(configuration))
    unreal.BlueprintEditorLibrary.compile_blueprint(animation)
    for asset in (animation, primary):
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError("Could not save project-owned animation: " + asset.get_path_name())
    character = blueprint(profile["character_blueprint"], profile["parent_class"])
    cdo = unreal.get_default_object(character.generated_class())
    component = cdo.get_skills()
    if component.get_class().get_path_name() != profile["behavior_class"]:
        raise RuntimeError("Sparrow Blueprint has the wrong native skill component")
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("skeletal_mesh_asset", load(profile["expected"]["mesh"]))
    mesh.set_editor_property("anim_class", animation.generated_class())
    mesh.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mesh.set_editor_property("relative_location", unreal.Vector(0, 0, -97))
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0, yaw=-90, roll=0))
    mesh.set_editor_property("override_materials", [])
    movement = cdo.get_editor_property("character_movement")
    for name, value in profile["expected"]["movement"].items():
        movement.set_editor_property(name, value)
    rotation = movement.get_editor_property("rotation_rate")
    rotation.yaw = profile["expected"]["rotation_rate"]
    movement.set_editor_property("rotation_rate", rotation)
    movement.set_editor_property("requested_move_use_acceleration", True)
    nav = movement.get_editor_property("nav_movement_properties")
    nav.set_editor_property("use_acceleration_for_paths", True)
    movement.set_editor_property("nav_movement_properties", nav)
    for component_class, key in ((unreal.SpringArmComponent, "spring_arm"),
                                 (unreal.CameraComponent, "camera_component")):
        camera_component = cdo.get_components_by_class(component_class)[0]
        for name, value in profile["expected"]["camera"][key].items():
            if name == "relative_rotation":
                value = unreal.Rotator(pitch=value[0], yaw=value[1], roll=value[2])
            camera_component.set_editor_property(name, value)
    cdo.set_editor_property("combo_restart_cooldown", profile["expected"]["combo_restart_cooldown"])
    steps = []
    for desired in profile["basic_attack"]:
        step = unreal.BasicAttackComboStep()
        step.set_editor_property("montage", load(desired["montage"]))
        step.set_editor_property("play_rate", desired["play_rate"])
        step.set_editor_property("hit_time_fraction", desired["hit_fraction"])
        steps.append(step)
    cdo.set_editor_property("combo_attacks", steps)
    definitions = component.get_editor_property("skills")
    if len(definitions) != len(profile["skill_defaults"]):
        raise RuntimeError("Sparrow profile and native skill count disagree")
    for definition, desired in zip(definitions, profile["skill_defaults"]):
        for name, value in desired.items():
            if name in ("animation", "cast_effect", "impact_effect", "cast_sound"):
                value = load(value) if value else None
            elif name == "name":
                value = unreal.Name(value)
            current = definition.get_editor_property(name)
            same = (abs(float(current) - float(value)) < 0.00001
                    if isinstance(current, (float, int)) and isinstance(value, (float, int)) else current == value)
            if not same:
                definition.set_editor_property(name, value)
    component.set_editor_property("skills", definitions)
    unreal.BlueprintEditorLibrary.compile_blueprint(character)
    if not unreal.EditorAssetLibrary.save_loaded_asset(character, False):
        raise RuntimeError("Could not save Sparrow character")
    mode = blueprint("/Game/TopDown/Characters/Sparrow/BP_SparrowGameMode", "/Script/Engine.GameModeBase")
    mode_cdo = unreal.get_default_object(mode.generated_class())
    mode_cdo.set_editor_property("default_pawn_class", character.generated_class())
    mode_cdo.set_editor_property("player_controller_class", unreal.load_class(None, "/Script/LearnTopDown.KwangPlayerController"))
    mode_cdo.set_editor_property("hud_class", unreal.load_class(None, "/Script/LearnTopDown.CharacterSkillHUD"))
    unreal.BlueprintEditorLibrary.compile_blueprint(mode)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mode, False):
        raise RuntimeError("Could not save Sparrow GameMode")
    # Load-as-template creates an untitled package and cannot overwrite the source field.
    map_path = profile["map"]
    if unreal.EditorAssetLibrary.does_asset_exist(map_path):
        world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
    else:
        world = unreal.EditorLoadingAndSavingUtils.new_map_from_template("/Game/TopDown/Lvl_TopDown", False)
    if world is None:
        raise RuntimeError("Could not create Sparrow field from the existing template")
    world.get_world_settings().set_editor_property("default_game_mode", mode.generated_class())
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, map_path):
        raise RuntimeError("Could not save the new Sparrow field")
    check_after = verify(baseline)
    report = {"passed": check_after["passed"], "baseline": str(baseline), "before": check_before,
              "after": check_after, "character": profile["character_blueprint"], "map": map_path,
              "configuration": configuration, "sound_enabled": False, "source_packages_saved": False}
    (qa / "sparrow-setup.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("An original package changed: " + str(check_after["mismatches"]))
except Exception as error:
    (qa / "sparrow-setup.json").write_text(json.dumps({"passed": False, "error": str(error),
        "traceback": traceback.format_exc()}, indent=2), encoding="utf-8")
    unreal.log_error(traceback.format_exc())
finally:
    unreal.SystemLibrary.quit_editor()
