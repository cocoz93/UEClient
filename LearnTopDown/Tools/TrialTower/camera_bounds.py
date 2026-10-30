"""Author the Trial Tower's map-local SpringArm camera clamp.

The native character switch copies SpringArm.TargetOffset and camera-lag state.
This actor updates only the current pawn's world-space XY offset, leaving the
active view target, arm length, rotation, FOV and camera lag under their existing
owners. Its tick precedes the SpringArm through an explicit prerequisite.

Run build() in the owning editor while the Trial Tower map is open. No C++,
shared controller, training map or character asset is modified.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal

from ui_build import require, node_call, pin, wire, value, execute, compile_bp, event_graph


MAP = "/Game/TopDown/TrialTower/Maps/Lvl_TrialTower"
BLUEPRINT = "/Game/TopDown/TrialTower/Environment/BP_TowerCameraBounds"
LABEL = "TrialTower_CameraBounds"
ARM_CLASS = "/Script/Engine.SpringArmComponent"
B = unreal.BlueprintEditorLibrary


def _current_world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    require(world and str(unreal.GameplayStatics.get_current_level_name(world, True)) == "Lvl_TrialTower",
            "Open only Lvl_TrialTower before installing camera bounds")
    return world


def _bounds(min_x, max_x, min_y, max_y):
    require(min_x < max_x and min_y < max_y, "Camera bounds must have positive area")
    return {"CameraMinX": float(min_x), "CameraMaxX": float(max_x),
            "CameraMinY": float(min_y), "CameraMaxY": float(max_y)}


def _make_graph(bp):
    editor = event_graph(bp)
    editor.remove_nodes(editor.list_all_nodes())
    compile_bp(bp)
    editor = event_graph(bp)
    tick = require(B.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 0)), "Tick event missing")

    # Resolve each frame so native character switching requires no new hook.
    pawn = node_call(editor, "/Script/Engine.GameplayStatics.GetPlayerPawn")
    value(pawn, "PlayerIndex", 0)
    valid_pawn = node_call(editor, "/Script/Engine.KismetSystemLibrary.IsValid")
    wire(pawn.find_result_pin(), pin(valid_pawn, "Object"))
    pawn_branch = editor.add_branch_node()
    wire(valid_pawn.find_result_pin(), pin(pawn_branch, "Condition"))
    execute(tick, pawn_branch)

    arm = node_call(editor, "/Script/Engine.Actor.GetComponentByClass")
    wire(pawn.find_result_pin(), arm.find_self_pin())
    value(arm, "ComponentClass", ARM_CLASS)
    valid_arm = node_call(editor, "/Script/Engine.KismetSystemLibrary.IsValid")
    wire(arm.find_result_pin(), pin(valid_arm, "Object"))
    arm_branch = editor.add_branch_node()
    wire(valid_arm.find_result_pin(), pin(arm_branch, "Condition"))
    if arm.find_execute_pin().is_valid():
        wire(pawn_branch.find_then_pin(), arm.find_execute_pin())
        execute(arm, arm_branch)
    else:
        wire(pawn_branch.find_then_pin(), arm_branch.find_execute_pin())

    self_node = None
    self_class = unreal.load_class(None, "/Script/BlueprintGraph.K2Node_Self")
    # This authoring API compares localized menu titles, not reflected names.
    # Restrict the declaring class as well so an unrelated action cannot match.
    for action_name in ("Variables|Getareferencetoself", "Variables|셀프레퍼런스가져오기"):
        self_node = editor.create_node_from_name(action_name, unreal.Vector2D(0, 220), [], self_class)
        if self_node:
            break
    require(self_node, "Self-reference node unavailable for the current editor language")
    prerequisite = node_call(editor, "/Script/Engine.ActorComponent.AddTickPrerequisiteActor")
    wire(arm.find_result_pin(), prerequisite.find_self_pin())
    wire(pin(self_node, "self", True), pin(prerequisite, "PrerequisiteActor"))
    wire(arm_branch.find_then_pin(), prerequisite.find_execute_pin())

    origin = node_call(editor, "/Script/Engine.SceneComponent.K2_GetComponentLocation")
    wire(arm.find_result_pin(), origin.find_self_pin())
    xyz = node_call(editor, "/Script/Engine.KismetMathLibrary.BreakVector")
    wire(origin.find_result_pin(), pin(xyz, "InVec"))
    previous_offset = require(editor.add_get_member_variable_node("TargetOffset", ARM_CLASS), "TargetOffset getter missing")
    wire(arm.find_result_pin(), previous_offset.find_self_pin())
    previous_xyz = node_call(editor, "/Script/Engine.KismetMathLibrary.BreakVector")
    wire(previous_offset.find_result_pin(), pin(previous_xyz, "InVec"))
    offset = node_call(editor, "/Script/Engine.KismetMathLibrary.MakeVector")

    # Clamp the uncorrected arm origin rather than the already corrected target;
    # otherwise the correction would alternate between zero and the edge offset.
    for axis in ("X", "Y"):
        clamp = node_call(editor, "/Script/Engine.KismetMathLibrary.FClamp")
        wire(pin(xyz, axis, True), pin(clamp, "Value"))
        for endpoint, prefix in (("Min", "CameraMin"), ("Max", "CameraMax")):
            member = require(editor.add_get_member_variable_node(prefix + axis), "Camera bound getter missing")
            wire(member.find_result_pin(), pin(clamp, endpoint))
        subtract = node_call(editor, "/Script/Engine.KismetMathLibrary.Subtract_DoubleDouble")
        wire(clamp.find_result_pin(), pin(subtract, "A"))
        wire(pin(xyz, axis, True), pin(subtract, "B"))
        wire(subtract.find_result_pin(), pin(offset, axis))
    wire(pin(previous_xyz, "Z", True), pin(offset, "Z"))

    setter = require(editor.add_set_member_variable_node("TargetOffset", ARM_CLASS), "TargetOffset setter missing")
    wire(arm.find_result_pin(), setter.find_self_pin())
    wire(offset.find_result_pin(), pin(setter, "TargetOffset"))
    execute(prerequisite, setter)

    for index, node in enumerate(editor.list_all_nodes()):
        node.set_node_pos(unreal.IntPoint((index % 6) * 300, (index // 6) * 200))
    editor.add_comment_to_nodes(
        "Tower only: clamp the current SpringArm world XY pivot before its own tick. "
        "Native camera settings, lag and character switching remain unchanged.",
        editor.list_all_nodes(), 35)
    compile_bp(bp)


def build(output=None, min_x=-1800, max_x=2100, min_y=-1800, max_y=2100):
    """Create/update one BP and its single map instance; bounds are instance-editable."""
    world = _current_world()
    bounds = _bounds(min_x, max_x, min_y, max_y)
    bp = (unreal.load_asset(BLUEPRINT)
          if unreal.EditorAssetLibrary.does_asset_exist(BLUEPRINT) else None)
    if not bp:
        # Loading a missing asset may leave an empty UPackage. AssetTools can
        # populate that package; CreateBlueprintAssetWithParent rejects it.
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.load_class(None, "/Script/Engine.Actor"))
        package, name = BLUEPRINT.rsplit("/", 1)
        bp = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, package, unreal.Blueprint, factory), "Camera BP creation failed")
    editor = event_graph(bp)
    names = set(str(name) for name in B.list_member_variable_names(bp))
    for name, number in bounds.items():
        if name not in names:
            require(editor.add_member_variable(name, B.get_basic_type_by_name("real"), str(number)),
                    "Could not add camera bound " + name)
        B.set_blueprint_variable_instance_editable(bp, name, True)
        B.set_blueprint_variable_category(bp, name, "Tower Camera Bounds")
    compile_bp(bp)
    _make_graph(bp)

    cdo = unreal.get_default_object(bp.generated_class())
    tick = cdo.get_editor_property("primary_actor_tick")
    # ReceiveTick compilation enables bCanEverTick. It is not exposed as an
    # editable Python struct property, unlike the following tick defaults.
    tick.set_editor_property("start_with_tick_enabled", True)
    tick.set_editor_property("tick_group", unreal.TickingGroup.TG_POST_PHYSICS)
    cdo.set_editor_property("primary_actor_tick", tick)
    for name, number in bounds.items():
        cdo.set_editor_property(name, number)
    require(unreal.EditorAssetLibrary.save_loaded_asset(bp, False), "Camera BP save failed")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [actor for actor in actors.get_all_level_actors() if actor.get_class() == bp.generated_class()]
    require(len(matches) <= 1, "Multiple Tower camera bounds actors found")
    actor = matches[0] if matches else require(actors.spawn_actor_from_class(bp.generated_class(), unreal.Vector()),
                                              "Camera bounds placement failed")
    actor.modify()
    actor.set_actor_label(LABEL)
    actor.set_folder_path("TrialTower/Camera")
    actor.tags = ["TrialTowerCameraBounds"]
    # PrimaryActorTick is EditDefaultsOnly; use its public runtime setters on
    # the placed instance while retaining the compiled CDO's start-enabled flag.
    actor.set_tick_group(unreal.TickingGroup.TG_POST_PHYSICS)
    actor.set_actor_tick_enabled(True)
    for name, number in bounds.items():
        actor.set_editor_property(name, number)
    require(unreal.EditorLoadingAndSavingUtils.save_map(world, MAP), "Tower camera map save failed")

    result = {"blueprint": BLUEPRINT, "map": MAP, "actor": actor.get_path_name(), "bounds_cm": bounds,
              "tick_group": "PostPhysics", "spring_arm_tick_prerequisite": LABEL,
              "view_target_replaced": False, "cpp_changed": False, "training_map_changed": False}
    if output:
        destination = Path(output)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "camera-bounds-build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def set_limits(min_x, max_x, min_y, max_y, save=True):
    """Tune the placed Tower actor after game-camera corner projection checks."""
    world = _current_world()
    bp_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    actors = [actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
              if actor.get_class() == bp_class]
    require(len(actors) == 1, "Expected one Tower camera bounds actor")
    bounds = _bounds(min_x, max_x, min_y, max_y)
    actors[0].modify()
    for name, number in bounds.items():
        actors[0].set_editor_property(name, number)
    if save:
        require(unreal.EditorLoadingAndSavingUtils.save_map(world, MAP), "Tower camera limits save failed")
    return bounds


def sample_runtime():
    """Read-only QA snapshot for native camera settings and the effective target pivot."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    require(world, "PIE is not running")
    pawn = require(unreal.GameplayStatics.get_player_pawn(world, 0), "Player pawn is missing")
    arm = require(pawn.get_component_by_class(unreal.SpringArmComponent), "Player SpringArm is missing")
    camera = require(pawn.get_component_by_class(unreal.CameraComponent), "Player camera is missing")
    location = arm.get_world_location()
    offset = arm.get_editor_property("target_offset")
    actual_camera = camera.get_world_location()
    rotation = arm.get_world_rotation()
    return {"map": str(unreal.GameplayStatics.get_current_level_name(world, True)),
            "pawn": pawn.get_class().get_name(),
            "pawn_position": [pawn.get_actor_location().x, pawn.get_actor_location().y, pawn.get_actor_location().z],
            "arm_position": [location.x, location.y, location.z], "target_offset": [offset.x, offset.y, offset.z],
            "effective_pivot": [location.x + offset.x, location.y + offset.y, location.z + offset.z],
            "camera_position": [actual_camera.x, actual_camera.y, actual_camera.z],
            "arm_length": arm.get_editor_property("target_arm_length"),
            "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
            "fov": camera.get_editor_property("field_of_view"),
            "lag": arm.get_editor_property("enable_camera_lag")}

