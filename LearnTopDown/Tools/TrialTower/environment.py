"""Author the isolated Trial Tower hall with existing finished environment assets.

Run build() from the parent editor session, then finalize_navigation() after
asynchronous navigation generation is ready. Only the new map and materials
below are saved; training room, imported packs and character assets stay read-only.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve()
DEST = "/Game/TopDown/TrialTower/Environment"
MAP = "/Game/TopDown/TrialTower/Maps/Lvl_TrialTower"
TEMPLATE = "/Game/TopDown/Lvl_TopDown"
RUINS = "/Game/ParagonProps/Monolith/Ruins/Meshes/"
AGORA = "/Game/ParagonProps/Agora/Props/Meshes/"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ASSETS = unreal.EditorAssetLibrary
MATERIALS = unreal.MaterialEditingLibrary
REPORT = {}
LOADED = {}


def load(path):
    if path not in LOADED:
        LOADED[path] = unreal.load_asset(path)
    if not LOADED[path]:
        raise RuntimeError("Required Trial Tower asset missing: " + path)
    return LOADED[path]


def material(name, color, roughness=.85, metallic=0, texture=None, normal=None, tiling=1):
    """All expressions belong to a new map-owned material, never a pack asset."""
    path = DEST + "/Materials/" + name
    mat = unreal.load_asset(path)
    if mat is None:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, DEST + "/Materials", unreal.Material, unreal.MaterialFactoryNew())
    MATERIALS.delete_all_material_expressions(mat)
    tint = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -250, -150)
    tint.set_editor_property("constant", unreal.LinearColor(*color, 1))
    if texture:
        uv = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -850, 0)
        uv.set_editor_property("u_tiling", float(tiling))
        uv.set_editor_property("v_tiling", float(tiling))
        tex = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, 0)
        tex.set_editor_property("texture", load(texture))
        MATERIALS.connect_material_expressions(uv, "", tex, "UVs")
        multiply = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionMultiply, -100, 0)
        MATERIALS.connect_material_expressions(tex, "RGB", multiply, "A")
        MATERIALS.connect_material_expressions(tint, "", multiply, "B")
        MATERIALS.connect_material_property(multiply, "", unreal.MaterialProperty.MP_BASE_COLOR)
        if normal:
            n = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, 260)
            n.set_editor_property("texture", load(normal))
            n.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            MATERIALS.connect_material_expressions(uv, "", n, "UVs")
            MATERIALS.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
    else:
        MATERIALS.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in ((roughness, unreal.MaterialProperty.MP_ROUGHNESS, 420),
                          (metallic, unreal.MaterialProperty.MP_METALLIC, 520)):
        node = MATERIALS.create_material_expression(mat, unreal.MaterialExpressionConstant, -200, y)
        node.set_editor_property("r", value)
        MATERIALS.connect_material_property(node, "", prop)
    MATERIALS.recompile_material(mat)
    if not ASSETS.save_loaded_asset(mat, False):
        raise RuntimeError("Cannot save Trial Tower material: " + path)
    return mat


def medallion_material():
    """Preserve the pack's color/cracks/detail normals in a private stationary MI."""
    name = "MI_TowerCarvedMedallion"
    path = DEST + "/Materials/" + name
    mat = unreal.load_asset(path)
    if mat is None:
        mat = ASSETS.duplicate_asset(
            "/Game/ParagonProps/Monolith/Ruins/Materials/MI_Ruins_DecoFloor", path)
    if not mat:
        raise RuntimeError("Could not copy the original carved-floor material instance")
    mat.modify()
    for parameter in ("PDO", "ScaleWPO"):
        MATERIALS.set_material_instance_scalar_parameter_value(mat, parameter, 0.0)
        if abs(MATERIALS.get_material_instance_scalar_parameter_value(mat, parameter)) > .0001:
            raise RuntimeError("The private floor parameter did not persist: " + parameter)
    # UE 5.8's setter never changes its false return value; verify the readback.
    MATERIALS.set_material_instance_static_switch_parameter_value(mat, "WPOTrue", False)
    if MATERIALS.get_material_instance_static_switch_parameter_value(mat, "WPOTrue"):
        raise RuntimeError("The private floor WPO switch did not persist")
    overrides = mat.get_editor_property("base_property_overrides")
    overrides.set_editor_property("override_blend_mode", True)
    overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property("base_property_overrides", overrides)
    MATERIALS.update_material_instance(mat)
    if not ASSETS.save_loaded_asset(mat, False):
        raise RuntimeError("Could not save the stationary carved-floor material instance")
    return mat


def mesh(name, path, bottom_center, scale=(1, 1, 1), yaw=0, collision=False,
         override_material=None, folder="Architecture"):
    """Place by rotated bounds center in XY and bounds bottom in Z."""
    source = load(path)
    bounds = source.get_bounding_box()
    local = ((bounds.min.x + bounds.max.x) * .5 * scale[0],
             (bounds.min.y + bounds.max.y) * .5 * scale[1], bounds.min.z * scale[2])
    angle = math.radians(yaw)
    rotated = (local[0] * math.cos(angle) - local[1] * math.sin(angle),
               local[0] * math.sin(angle) + local[1] * math.cos(angle), local[2])
    position = unreal.Vector(*(bottom_center[i] - rotated[i] for i in range(3)))
    actor = ACTORS.spawn_actor_from_class(unreal.StaticMeshActor, position, unreal.Rotator(yaw=yaw))
    actor.set_actor_label("TrialTower_" + name)
    actor.set_folder_path("TrialTower/" + folder)
    actor.tags = ["TrialTowerEnvironment"]
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_static_mesh(source)
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
    if override_material:
        for i in range(component.get_num_materials()):
            component.set_material(i, override_material)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    REPORT["placements"].append({"name": name, "mesh": path, "bottom_center": bottom_center,
                                  "scale": scale, "yaw": yaw, "collision": collision})
    return actor


def fit(name, path, position, size, yaw=0, collision=False, override_material=None, folder="Architecture"):
    b = load(path).get_bounding_box()
    dims = (b.max.x - b.min.x, b.max.y - b.min.y, b.max.z - b.min.z)
    scale = tuple(size[i] / max(dims[i], .01) for i in range(3))
    return mesh(name, path, position, scale, yaw, collision, override_material, folder)


def box(name, position, size, mat, yaw=0, collision=False, folder="Architecture"):
    return fit(name, "/Engine/BasicShapes/Cube", position, size, yaw, collision, mat, folder)


def plane(name, position, size, mat, yaw=0):
    return mesh(name, "/Engine/BasicShapes/Plane", position,
                (size[0] / 100, size[1] / 100, 1), yaw, False, mat, "Floor")


def arched_gate(name, position, width=820, height=650, depth=200, yaw=0):
    # JungleArch_01A is one half: local X is depth and negative Y runs from
    # the outside pier to the apex at Y=0. Pair two halves around that apex.
    angle = math.radians(yaw)
    for side in (-1, 1):
        local_y = side * width / 4
        center = (position[0] - local_y * math.sin(angle),
                  position[1] + local_y * math.cos(angle), position[2])
        fit(f"{name}_{side}", RUINS + "JungleArch_01A", center,
            (depth, width / 2, height), yaw=yaw if side < 0 else yaw + 180)


def point_light(name, position, intensity=600, radius=650, color=(1, .68, .35)):
    light = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*position))
    light.set_actor_label("TrialTower_" + name)
    light.set_folder_path("TrialTower/Lighting")
    light.tags = ["TrialTowerEnvironment"]
    component = light.get_component_by_class(unreal.PointLightComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_light_color(unreal.LinearColor(*color, 1))
    component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    component.set_intensity(intensity)
    component.set_editor_property("attenuation_radius", radius)
    component.set_editor_property("source_radius", 30.0)
    component.set_editor_property("cast_shadows", False)


def lighting():
    for name, rotation, color, intensity, shadows in (
        ("SunThroughOpenRoof", (-58, -30), (1, .88, .71), 3.4, True),
        ("CameraSideFill", (-35, 45), (.78, .84, 1), .65, False)):
        actor = ACTORS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1800),
                                              unreal.Rotator(pitch=rotation[0], yaw=rotation[1]))
        actor.set_actor_label("TrialTower_" + name)
        actor.set_folder_path("TrialTower/Lighting")
        actor.tags = ["TrialTowerEnvironment"]
        component = actor.get_component_by_class(unreal.DirectionalLightComponent)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_light_color(unreal.LinearColor(*color, 1))
        component.set_intensity(intensity)
        component.set_editor_property("cast_shadows", shadows)
        if shadows:
            component.set_editor_property("forward_shading_priority", 1)
    sky = ACTORS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1500))
    sky.set_actor_label("TrialTower_AmbientStoneBounce")
    sky.set_folder_path("TrialTower/Lighting")
    sky.tags = ["TrialTowerEnvironment"]
    comp = sky.get_component_by_class(unreal.SkyLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    comp.set_cubemap(load("/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
    comp.set_intensity(.85)
    comp.set_light_color(unreal.LinearColor(.92, .87, .78, 1))
    pp = ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    pp.set_actor_label("TrialTower_StableExposure")
    pp.set_folder_path("TrialTower/Lighting")
    pp.tags = ["TrialTowerEnvironment"]
    pp.set_editor_property("unbound", True)
    settings = pp.get_editor_property("settings")
    for key, value in {"auto_exposure_min_brightness": 0.0, "auto_exposure_max_brightness": 0.0,
                       "auto_exposure_bias": .0, "bloom_intensity": .18,
                       "vignette_intensity": .17, "motion_blur_amount": 0.0}.items():
        settings.set_editor_property("override_" + key, True)
        settings.set_editor_property(key, value)
    pp.set_editor_property("settings", settings)
    fog = ACTORS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -100))
    fog.set_actor_label("TrialTower_OuterDust")
    fog.set_folder_path("TrialTower/Lighting")
    fog.tags = ["TrialTowerEnvironment"]
    comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    comp.set_editor_property("fog_density", .009)
    comp.set_editor_property("fog_height_falloff", .35)
    comp.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(.075, .057, .035, 1))
    comp.set_editor_property("start_distance", 1700.0)


def prepare_world():
    exists = ASSETS.does_asset_exist(MAP)
    world = (unreal.EditorLoadingAndSavingUtils.load_map(MAP) if exists else
             unreal.EditorLoadingAndSavingUtils.new_map_from_template(TEMPLATE, False))
    if not world:
        raise RuntimeError("Could not create or load the Trial Tower map")
    keep = (unreal.WorldSettings, unreal.PlayerStart, unreal.NavMeshBoundsVolume, unreal.RecastNavMesh)
    for actor in ACTORS.get_all_level_actors():
        if isinstance(actor, keep) or actor.get_class().get_name() in (
                "Brush", "NavigationSystemConfigActor", "WorldDataLayers", "WorldPartitionMiniMap"):
            continue
        if exists and "TrialTowerUI" in [str(tag) for tag in actor.tags]:
            continue
        ACTORS.destroy_actor(actor)
    if not exists:
        world.get_world_settings().modify()
        world.get_world_settings().set_editor_property("default_game_mode", unreal.load_class(
            None, "/Game/TopDown/Blueprints/BP_CountessGameMode.BP_CountessGameMode_C"))
    starts = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)
    if len(starts) != 1:
        raise RuntimeError("Template must have exactly one PlayerStart")
    # Preserved World Partition actors need an explicit dirty mark before
    # runtime-style transform setters, otherwise their external package stays old.
    starts[0].modify()
    starts[0].get_editor_property("root_component").modify()
    starts[0].set_actor_location(unreal.Vector(550, 550, 110), False, True)
    starts[0].set_actor_rotation(unreal.Rotator(yaw=45), True)
    starts[0].set_actor_label("TrialTower_PlayerStart")
    navs = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.NavMeshBoundsVolume)
    if not navs:
        raise RuntimeError("Template navigation volume missing")
    for nav in navs:
        nav.modify()
        nav.get_editor_property("root_component").modify()
        _, extent = nav.get_actor_bounds(False)
        old_scale = nav.get_actor_scale3d()
        nav.set_actor_scale3d(unreal.Vector(old_scale.x * 2300 / extent.x,
                                           old_scale.y * 2300 / extent.y,
                                           old_scale.z * 750 / extent.z))
        new_center, _ = nav.get_actor_bounds(False)
        nav.set_actor_location(nav.get_actor_location() - new_center + unreal.Vector(0, 0, 250), False, True)
    return world


def build(output=None):
    global REPORT
    REPORT = {"passed": False, "map": MAP, "placements": [], "source_packages_saved": False,
              "character_code_modified": False, "internal_floor_size_cm": [3200, 3200],
              "navigation_needs_finalize": True,
              "monster_entry_centers": [[0, 1600, 0], [1600, 0, 0], [0, -1600, 0], [-1600, 0, 0]],
              "clear_combat_center_radius_cm": 1100, "upper_exit": "decorative_only"}
    # Fail before replacing scenery if an imported source is missing.
    for path in (RUINS + "JungleWall_01A", RUINS + "JungleArch_01A", RUINS + "JunglePillarBlock_01A",
                 RUINS + "JungleStairs_Strait01", RUINS + "MonoStatue", RUINS + "Ruins_DecoFloor",
                 AGORA + "Terminus_Pillar_D",
                 "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_A",
                 "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_N"):
        load(path)
    ASSETS.make_directory(DEST + "/Materials")
    stone = material("M_TowerSandstone", (.36, .265, .17))
    dark = material("M_TowerShadowStone", (.105, .078, .05))
    brass = material("M_TowerAgedBronze", (.20, .135, .055), .63, .65)
    finish = material("M_TowerWornFloor", (.70, .48, .28), texture=
                      "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_A", normal=
                      "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_N", tiling=4.5)
    paving = material("M_TowerApproachFloor", (.50, .365, .23), texture=
                      "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_A", normal=
                      "/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_N", tiling=1.5)
    carved = medallion_material()
    world = prepare_world()
    # Continuous collision and separately shaded planes keep imported module seams harmless.
    box("ContinuousFloorCollision", (0, 0, -80), (3360, 3360, 80), stone, collision=True, folder="Floor")
    plane("QuietWornSandstoneFloor", (0, 0, .3), (3200, 3200), finish)
    # A nearly flush carved medallion breaks the paving repetition without
    # adding a collision step, a central obstacle or a glowing combat marker.
    fit("AncientFloorMedallion", RUINS + "Ruins_DecoFloor", (200, 200, .55),
        (1300, 1300, .8), collision=False, override_material=carved, folder="Floor")
    box("OuterFoundation", (0, 0, -260), (4700, 4700, 140), dark, folder="Backdrop")
    for axis in range(2):
        for sign in (-1, 1):
            pos = (0, sign * 1910, -55) if axis == 0 else (sign * 1910, 0, -55)
            size = (560, 760, 55) if axis == 0 else (760, 560, 55)
            box(f"EntryApproach_{axis}_{sign}", pos, size, stone, collision=True, folder="Floor")
            plane(f"EntryPaving_{axis}_{sign}", (pos[0], pos[1], .4), (560, 760), paving,
                  yaw=0 if axis == 0 else 90)
            # Closed offscreen ends reserve spawning space while keeping the player in the prototype.
            cap = (0, sign * 2270, 0) if axis == 0 else (sign * 2270, 0, 0)
            box(f"ApproachEnd_{axis}_{sign}", cap, (560, 90, 200), dark,
                yaw=0 if axis == 0 else 90, collision=True)
    # Each wall has a 560 cm entrance. Near faces are low to preserve the fixed camera view.
    for axis in range(2):
        for sign in (-1, 1):
            yaw = 0 if axis == 0 else 90
            height = 470 if sign > 0 else 115
            for side in (-1, 1):
                coordinate = side * 950
                pos = (coordinate, sign * 1635, 0) if axis == 0 else (sign * 1635, coordinate, 0)
                if sign > 0:
                    # Local Y is the wall length. The far northeast corner
                    # stays open for the separate diagonal ascent.
                    centers = (side * 620, side * 1280) if side < 0 else (680,)
                    for index, center in enumerate(centers):
                        wall_pos = (center, sign * 1635, 0) if axis == 0 else (sign * 1635, center, 0)
                        length = 660 if side < 0 else 800
                        fit(f"CarvedWall_{axis}_{side}_{index}", RUINS + "JungleWall_01A", wall_pos,
                            (170, length, height), yaw=90 if axis == 0 else 0, collision=True)
                else:
                    box(f"LowParapet_{axis}_{side}", pos, (1320, 100, height), stone, yaw, True)
                    box(f"LowParapetCap_{axis}_{side}", (pos[0], pos[1], height),
                        (1340, 124, 24), dark, yaw)
            if sign > 0:
                pos = (0, sign * 1635, 0) if axis == 0 else (sign * 1635, 0, 0)
                arched_gate(f"MonsterArch_{axis}", pos, yaw=90 if axis == 0 else 0)
            for side in (-1, 1):
                coordinate = side * 365
                pos = (coordinate, sign * 1580, 0) if axis == 0 else (sign * 1580, coordinate, 0)
                fit(f"GatePier_{axis}_{sign}_{side}", RUINS + "JunglePillarBlock_01A", pos,
                    (175, 175, 660 if sign > 0 else 145), collision=True)
                if sign > 0:
                    point_light(f"GateWarmth_{axis}_{side}", (pos[0]-55, pos[1]-55, 245), 720, 650)
    # Tall silhouettes live outside the close combat space, along the far rim only.
    for i, (x, y) in enumerate(((-1430, 1515), (1080, 1570), (1570, 1080), (1515, -1430))):
        fit(f"SanctumPillar_{i}", AGORA + "Terminus_Pillar_D", (x, y, 0), (250, 250, 870), collision=True)
    for i, (x, y, yaw) in enumerate(((-1260, 1320, -45), (1320, -1260, 135))):
        box(f"SentinelPlinth_{i}", (x, y, 0), (310, 310, 90), dark, collision=True)
        fit(f"WeatheredSentinel_{i}", RUINS + "MonoStatue", (x, y, 90), (240, 230, 480), yaw=yaw)
    # A diagonal staircase makes the destination legible, while the four side gates remain equal entries.
    stair_center = (1370, 1370, 0)
    fit("AscentToNextFloor", RUINS + "JungleStairs_Strait01", stair_center, (760, 850, 360),
        yaw=135, collision=True)
    box("UpperLanding", (1775, 1775, 270), (660, 660, 100), dark, yaw=45, collision=True)
    for i, (x, y) in enumerate(((1490, 1950), (1950, 1490))):
        fit(f"UpperGatePillar_{i}", RUINS + "JunglePillarBlock_01A", (x, y, 370),
            (200, 200, 730), collision=True)
    arched_gate("UpperGateArch", (1730, 1730, 370), width=850, height=760, depth=180, yaw=45)
    point_light("AscentWarmPool", (1570, 1570, 570), 1800, 900, (1, .72, .36))
    lighting()
    apply_lower_stair_access(save=False)
    ASSETS.make_directory("/Game/TopDown/TrialTower/Maps")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not save Trial Tower map")
    REPORT.update(passed=True, actor_count=len(ACTORS.get_all_level_actors()),
                  default_game_mode=world.get_world_settings().get_editor_property("default_game_mode").get_path_name())
    if output:
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        (target / "environment-build.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    unreal.log("TRIAL_TOWER_ENVIRONMENT " + json.dumps({"passed": True, "map": MAP,
                                                       "actors": REPORT["actor_count"]}))
    return REPORT


def apply_lower_stair_access(output=None, save=True):
    """Remove the optional inlay and allow ordinary movement on the first two treads.

    The imported stair's convex collision starts above the floor. Replace that
    actor's collision with a map-owned ramp and a blocker beyond the second tread;
    neither the shared source mesh nor character movement settings are modified.
    """
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError("Load Trial Tower before changing its stair access")
    actors = ACTORS.get_all_level_actors()
    stairs = [a for a in actors if a.get_actor_label() == "TrialTower_AscentToNextFloor"]
    if len(stairs) != 1:
        raise RuntimeError("Expected exactly one Trial Tower ascent stair")
    removed = []
    for actor in actors:
        label = actor.get_actor_label()
        if label.startswith("TrialTower_OctagonalStoneSeam_") or label in (
                "TrialTower_LowerStairWalkRamp", "TrialTower_UpperStairAccessBlocker"):
            if not ACTORS.destroy_actor(actor):
                raise RuntimeError("Could not remove map-owned actor: " + label)
            removed.append(label)
    stairs[0].modify()
    component = stairs[0].get_component_by_class(unreal.StaticMeshComponent)
    component.modify()
    component.set_collision_profile_name("NoCollision")
    REPORT.setdefault("placements", [])
    dark = load(DEST + "/Materials/M_TowerShadowStone")
    # Inspected render-mesh treads: XY 1070..1160 is Z 58; 1170..1260 is Z 117.
    # A continuous low slope avoids the 58 cm risers exceeding the native step limit.
    start, end, rise, thickness = 1048.0, 1257.0, 120.0, 20.0
    run = (end - start) * math.sqrt(2)
    pitch = math.atan2(rise, run)
    length = math.hypot(run, rise)
    middle = (start + end) * .5
    ramp = box("LowerStairWalkRamp", (0, 0, 0), (length, 740, thickness), dark,
               collision=True, folder="Collision")
    ramp.set_actor_rotation(unreal.Rotator(pitch=math.degrees(pitch), yaw=45), True)
    ramp.set_actor_location(unreal.Vector(
        middle + math.sin(pitch) * thickness / (2 * math.sqrt(2)),
        middle + math.sin(pitch) * thickness / (2 * math.sqrt(2)),
        rise * .5 - math.cos(pitch) * thickness * .5), False, True)
    # The wide barrier meets the existing side walls, preventing a route around it.
    depth = 1250.0
    center = 1267.0 + depth / (2 * math.sqrt(2))
    blocker = box("UpperStairAccessBlocker", (center, center, -25), (depth, 1400, 700),
                  dark, yaw=45, collision=True, folder="Collision")
    for actor in (ramp, blocker):
        actor.set_actor_hidden_in_game(True)
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        comp.set_visibility(False)
        comp.set_cast_shadow(False)
    if save and not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not save Trial Tower stair access")
    result = {"map": MAP, "removed_octagonal_segments": sum("OctagonalStoneSeam" in s for s in removed),
              "lower_treads_accessible": 2, "upper_stairs_blocked": True,
              "entrances_modified": False, "shared_mesh_modified": False,
              "navigation_needs_finalize": True}
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
        (Path(output) / "stair-access-build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def apply_surface_and_start():
    """Apply only the inspected surface/spawn fixes to an already built map."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError("Load Trial Tower before applying its surface patch")
    carved = medallion_material()
    fixed_surface = False
    fixed_start = False
    for actor in ACTORS.get_all_level_actors():
        if actor.get_actor_label() == "TrialTower_AncientFloorMedallion":
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            actor.modify()
            component.modify()
            for slot in range(component.get_num_materials()):
                component.set_material(slot, carved)
            bounds = component.get_editor_property("static_mesh").get_bounding_box()
            sx = 1300 / (bounds.max.x - bounds.min.x)
            sy = 1300 / (bounds.max.y - bounds.min.y)
            sz = .8 / (bounds.max.z - bounds.min.z)
            actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
            actor.set_actor_location(unreal.Vector(
                200 - (bounds.min.x + bounds.max.x) * .5 * sx,
                200 - (bounds.min.y + bounds.max.y) * .5 * sy,
                .55 - bounds.min.z * sz), False, True)
            fixed_surface = True
        if isinstance(actor, unreal.PlayerStart):
            actor.modify()
            actor.get_editor_property("root_component").modify()
            actor.set_actor_location(unreal.Vector(550, 550, 110), False, True)
            fixed_start = True
    if not (fixed_surface and fixed_start):
        raise RuntimeError("Expected medallion and PlayerStart not found")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not save Trial Tower surface/spawn fixes")
    return {"opaque_medallion": True, "original_detail_material_preserved": True,
            "medallion_width_cm": 1300, "player_start": [550, 550, 110],
            "external_actor_packages_explicitly_dirtied": True}


def finalize_navigation(output=None):
    """Persist generated navigation after the editor has finished building it.

    Call on a later editor tick after build(); do not block editor ticks while
    waiting. Saving a newly placed map before the async build finishes is not
    sufficient for this map's OpenLevel runtime navigation.
    """
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError("Load Trial Tower before finalizing its navigation")
    if unreal.NavigationSystemV1.is_navigation_being_built(world):
        raise RuntimeError("Trial Tower navigation is still building; call again on a later tick")
    samples = {"center": (0, 0), "north_entry": (0, 1900), "east_entry": (1900, 0),
               "south_entry": (0, -1900), "west_entry": (-1900, 0)}
    projections = {}
    for name, (x, y) in samples.items():
        hit = unreal.NavigationSystemV1.project_point_to_navigation(
            world, unreal.Vector(x, y, 100), nav_data=None, filter_class=None,
            query_extent=unreal.Vector(100, 100, 250))
        if hit is None:
            raise RuntimeError("Navigation projection failed at " + name)
        projections[name] = [hit.x, hit.y, hit.z]
    meshes = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.RecastNavMesh)
    if not meshes:
        raise RuntimeError("No Recast navigation actor to save")
    for nav in meshes:
        nav.modify()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not persist Trial Tower generated navigation")
    result = {"passed": True, "map": MAP, "navigation_needs_finalize": False,
              "projections": projections, "recast_actors_saved": len(meshes)}
    if output:
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        (target / "navigation-finalize.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def widen_monster_entries(output=None):
    """Refit only the existing gate actors; preserve the rest of the authored hall.

    The original arch reaches the floor at its center. Raise the decoration
    above the passage so its non-colliding silhouette cannot hide approaching
    monsters. Gate piers and corridor rails define the same 900 cm clear lane.
    Call finalize_navigation() on a later tick after this map edit.
    """
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError("Load Trial Tower before widening its entrances")
    actors = {a.get_actor_label(): a for a in ACTORS.get_all_level_actors()}
    changed = []
    REPORT.setdefault("placements", [])

    def refit(name, position, size, yaw=0):
        actor = actors.get("TrialTower_" + name)
        if not actor:
            raise RuntimeError("Missing existing entrance actor: " + name)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        bounds = component.get_editor_property("static_mesh").get_bounding_box()
        dims = (bounds.max.x-bounds.min.x, bounds.max.y-bounds.min.y, bounds.max.z-bounds.min.z)
        scale = tuple(size[i]/dims[i] if dims[i] > .01 else 1.0 for i in range(3))
        local = ((bounds.min.x+bounds.max.x)*.5*scale[0],
                 (bounds.min.y+bounds.max.y)*.5*scale[1], bounds.min.z*scale[2])
        angle = math.radians(yaw)
        rotated = (local[0]*math.cos(angle)-local[1]*math.sin(angle),
                   local[0]*math.sin(angle)+local[1]*math.cos(angle), local[2])
        actor.modify()
        component.modify()
        actor.set_actor_scale3d(unreal.Vector(*scale))
        actor.set_actor_rotation(unreal.Rotator(yaw=yaw), True)
        actor.set_actor_location(unreal.Vector(*(position[i]-rotated[i] for i in range(3))), False, True)
        changed.append(name)

    stone = load(DEST + "/Materials/M_TowerShadowStone")
    for axis in range(2):
        for sign in (-1, 1):
            yaw = 0 if axis == 0 else 90
            pos = (0, sign*1910, -55) if axis == 0 else (sign*1910, 0, -55)
            refit(f"EntryApproach_{axis}_{sign}", pos, (1000, 760, 55), yaw)
            refit(f"EntryPaving_{axis}_{sign}", (pos[0], pos[1], .4), (1000, 760, 0), yaw)
            end = (0, sign*2270, 0) if axis == 0 else (sign*2270, 0, 0)
            refit(f"ApproachEnd_{axis}_{sign}", end, (1100, 90, 200), yaw)
            for side in (-1, 1):
                pier = (side*550, sign*1580, 0) if axis == 0 else (sign*1580, side*550, 0)
                refit(f"GatePier_{axis}_{sign}_{side}", pier, (200, 200, 690 if sign > 0 else 145))
                rail = (side*500, sign*1910, 0) if axis == 0 else (sign*1910, side*500, 0)
                rail_name = f"EntryRail_{axis}_{sign}_{side}"
                if "TrialTower_" + rail_name in actors:
                    refit(rail_name, rail, (100, 760, 130), yaw)
                else:
                    box(rail_name, rail, (100, 760, 130), stone, yaw, True)
                    changed.append(rail_name)
                if sign < 0:
                    wall = (side*1030, sign*1635, 0) if axis == 0 else (sign*1635, side*1030, 0)
                    refit(f"LowParapet_{axis}_{side}", wall, (1160, 100, 115), yaw)
                    refit(f"LowParapetCap_{axis}_{side}", (wall[0], wall[1], 115), (1160, 124, 24), yaw)
            if sign > 0:
                for side, index, center, length in ((-1, 0, -740, 580), (-1, 1, -1320, 580), (1, 0, 765, 630)):
                    wall = (center, 1635, 0) if axis == 0 else (1635, center, 0)
                    refit(f"CarvedWall_{axis}_{side}_{index}", wall, (170, length, 470), 90 if axis == 0 else 0)
                arch_yaw = 90 if axis == 0 else 0
                for side in (-1, 1):
                    angle = math.radians(arch_yaw)
                    arch = (-side*325*math.sin(angle), 1635+side*325*math.cos(angle), 450) if axis == 0 else (1635, side*325, 450)
                    refit(f"MonsterArch_{axis}_{side}", arch, (200, 650, 240), arch_yaw if side < 0 else arch_yaw+180)
                for side in (-1, 1):
                    light = actors.get(f"TrialTower_GateWarmth_{axis}_{side}")
                    if light:
                        light.modify()
                        light.set_actor_location(unreal.Vector(side*550-55, 1525, 245) if axis == 0 else unreal.Vector(1525, side*550-55, 245), False, True)

    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not save widened Trial Tower entries")
    result = {"map": MAP, "clear_width_cm": 900, "overhead_clearance_cm": 450,
              "changed_actors": changed, "spawn_locations_unchanged": True,
              "navigation_needs_finalize": True}
    if output:
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        (target/"entrances-build.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def align_ascent_stair():
    """Point the source mesh's low +Y side toward the hall.

    Source OBJ verification: local Y -250..-200 has Z 103..129, while
    local Y -50..2 has Z 2..44. The original -45 yaw exposed its high back.
    """
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError("Load Trial Tower before aligning its ascent")
    matches = [a for a in ACTORS.get_all_level_actors()
               if a.get_actor_label() == "TrialTower_AscentToNextFloor"]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one Trial Tower ascent stair")
    actor = matches[0]
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    actor.modify()
    component.modify()
    bounds = component.get_editor_property("static_mesh").get_bounding_box()
    scale = actor.get_actor_scale3d()
    local = ((bounds.min.x + bounds.max.x) * .5 * scale.x,
             (bounds.min.y + bounds.max.y) * .5 * scale.y, bounds.min.z * scale.z)
    angle = math.radians(135)
    actor.set_actor_rotation(unreal.Rotator(yaw=135), True)
    actor.set_actor_location(unreal.Vector(
        1370 - local[0] * math.cos(angle) + local[1] * math.sin(angle),
        1370 - local[0] * math.sin(angle) - local[1] * math.cos(angle),
        -local[2]), False, True)
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError("Could not save Trial Tower stair orientation")
    return {"stair_yaw": 135, "source_geometry_direction_verified": True,
            "navigation_needs_finalize": True}


if __name__ == "__main__":
    build(os.environ.get("TRIAL_TOWER_OUTPUT") or os.environ.get("SPARROW_QA_OUTPUT"))

