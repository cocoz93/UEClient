"""Build an isolated dungeon practice room; imported packs and hero assets stay read-only."""
import json
import math
import os
from pathlib import Path
import sys
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
from baseline import verify
from training_room_resources import budget_material, budget_texture

OUT = Path(os.environ['SPARROW_QA_OUTPUT'])
BASELINE = ROOT / 'Saved/QA/CharacterPipeline/baseline-training-room-20261015/baseline.json'
DEST = '/Game/TopDown/TrainingRoom'
MAP = DEST + '/Maps/Lvl_DarkTrainingRoom'
PACK = '/Game/MedievalDungeon'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {'passed': False, 'map': MAP, 'placements': [], 'source_packages_saved': False}


def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError('Required room asset missing: ' + path)
    return asset


def create_material(name, color, metallic=0.0, roughness=0.7, emission=0.0):
    path = DEST + '/Materials/' + name
    mat = unreal.load_asset(path)
    if mat:
        return mat
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST + '/Materials',
                                                               unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    base = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    base.set_editor_property('constant', unreal.LinearColor(*color, 1))
    lib.connect_material_property(base, '', unreal.MaterialProperty.MP_BASE_COLOR)
    for value, prop, y in ((metallic, unreal.MaterialProperty.MP_METALLIC, 150),
                            (roughness, unreal.MaterialProperty.MP_ROUGHNESS, 250)):
        node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, y)
        node.set_editor_property('r', value)
        lib.connect_material_property(node, '', prop)
    if emission:
        node = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 350)
        node.set_editor_property('constant', unreal.LinearColor(*(v * emission for v in color), 1))
        lib.connect_material_property(node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    return mat


def floor_material():
    """Reuse source albedo/normal without legacy parallax depth behind the collision slab."""
    name = 'M_TrainingStoneFloor'
    path = DEST + '/Materials/' + name
    existing = unreal.load_asset(path)
    lib = unreal.MaterialEditingLibrary
    mat = existing or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST + '/Materials',
                                                               unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    uv = lib.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -650, 0)
    uv.set_editor_property('u_tiling', 1.5)
    uv.set_editor_property('v_tiling', 1.5)
    for suffix, prop, y in (('A', unreal.MaterialProperty.MP_BASE_COLOR, 0),
                             ('N', unreal.MaterialProperty.MP_NORMAL, 200)):
        texture = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, y)
        texture.set_editor_property('texture', budget_texture(load(PACK + '/Textures/T_BrickFloor_Clean_' + suffix)))
        if suffix == 'N':
            texture.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        lib.connect_material_expressions(uv, '', texture, 'UVs')
        if suffix == 'A':
            tint = lib.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, -200)
            tint.set_editor_property('constant', unreal.LinearColor(.16, .18, .22, 1))
            multiply = lib.create_material_expression(mat, unreal.MaterialExpressionMultiply, -100, 0)
            lib.connect_material_expressions(texture, 'RGB', multiply, 'A')
            lib.connect_material_expressions(tint, '', multiply, 'B')
            lib.connect_material_property(multiply, '', prop)
        else:
            lib.connect_material_property(texture, 'RGB', prop)
    rough = lib.create_material_expression(mat, unreal.MaterialExpressionConstant, -100, 400)
    rough.set_editor_property('r', .82)
    lib.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat, False)
    return mat


def mesh(name, path, center, scale=(1, 1, 1), yaw=0, collision=False, material=None):
    asset = load(path)
    box = asset.get_bounding_box()
    local = [(box.min.x + box.max.x) * .5 * scale[0],
             (box.min.y + box.max.y) * .5 * scale[1], box.min.z * scale[2]]
    rad = math.radians(yaw)
    offset = (local[0] * math.cos(rad) - local[1] * math.sin(rad),
              local[0] * math.sin(rad) + local[1] * math.cos(rad), local[2])
    location = unreal.Vector(*(center[i] - offset[i] for i in range(3)))
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, unreal.Rotator(yaw=yaw))
    actor.set_actor_label(name)
    actor.set_folder_path('TrainingRoom/Architecture')
    actor.tags = ['DarkTrainingRoom']
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_static_mesh(asset)
    component.set_mobility(unreal.ComponentMobility.STATIC)
    component.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
    if material:
        for i in range(component.get_num_materials()):
            component.set_material(i, material)
    # Imported unused grid slots must never become visible in this room.
    for i in range(component.get_num_materials()):
        current = component.get_material(i)
        if not current or 'WorldGridMaterial' in current.get_path_name():
            component.set_material(i, load(PACK + '/Materials/M_StoneWall_Inst'))
        component.set_material(i, budget_material(component.get_material(i)))
    actor.set_actor_scale3d(unreal.Vector(*scale))
    report['placements'].append({'name': name, 'mesh': path, 'center': center, 'scale': scale,
                                 'collision': collision})
    return actor


def box(name, center, size, material, yaw=0, collision=False):
    return mesh(name, '/Engine/BasicShapes/Cube', center, tuple(v / 100 for v in size), yaw,
                collision, material)


def light(name, pos, color, intensity, radius=550):
    actor = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*pos))
    actor.set_actor_label(name)
    actor.set_folder_path('TrainingRoom/Lighting')
    comp = actor.get_component_by_class(unreal.PointLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_light_color(unreal.LinearColor(*color, 1))
    comp.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    comp.set_intensity(intensity)
    comp.set_editor_property('attenuation_radius', radius)
    comp.set_editor_property('source_radius', 18.0)
    comp.set_editor_property('cast_shadows', False)
    return actor


def build():
    if not verify(BASELINE)['passed']:
        raise RuntimeError('Protected baseline changed before room build')
    # Rebuild an existing room in-place so World Partition deletes its prior external actors.
    # Repeated template saves to the same path would leave unreferenced actor packages behind.
    world = (unreal.EditorLoadingAndSavingUtils.load_map(MAP)
             if unreal.EditorAssetLibrary.does_asset_exist(MAP)
             else unreal.EditorLoadingAndSavingUtils.new_map_from_template('/Game/TopDown/Lvl_TopDown', False))
    if not world:
        raise RuntimeError('Could not create a private copy of the original gameplay field')
    # Preserve working GameMode and brush-based navigation infrastructure, not old scenery.
    keep = (unreal.WorldSettings, unreal.PlayerStart, unreal.NavMeshBoundsVolume, unreal.RecastNavMesh)
    removed = 0
    for actor in actors.get_all_level_actors():
        if isinstance(actor, keep) or actor.get_class().get_name() in (
                'Brush', 'NavigationSystemConfigActor', 'WorldDataLayers', 'WorldPartitionMiniMap'):
            continue
        if actors.destroy_actor(actor):
            removed += 1
    report['removed_template_actors'] = removed
    world.get_world_settings().set_editor_property('default_game_mode',
        unreal.load_class(None, '/Game/TopDown/Blueprints/BP_CountessGameMode.BP_CountessGameMode_C'))
    starts = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.PlayerStart)
    if len(starts) != 1:
        raise RuntimeError('Expected exactly one preserved PlayerStart')
    starts[0].set_actor_location(unreal.Vector(0, -400, 110), False, True)
    starts[0].set_actor_rotation(unreal.Rotator(yaw=90), True)
    starts[0].set_actor_label('TrainingRoom_PlayerStart')
    navs = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.NavMeshBoundsVolume)
    if not navs:
        raise RuntimeError('Template navigation bounds missing')
    for nav in navs:
        old_center, extent = nav.get_actor_bounds(False)
        old_scale = nav.get_actor_scale3d()
        nav.set_actor_scale3d(unreal.Vector(old_scale.x * 1350 / extent.x,
                                           old_scale.y * 1350 / extent.y,
                                           old_scale.z * 500 / extent.z))
        new_center, _ = nav.get_actor_bounds(False)
        nav.set_actor_location(nav.get_actor_location() - new_center + unreal.Vector(0, 0, 150), False, True)
    stone = create_material('M_TrainingFoundation', (.045, .052, .062), roughness=.85)
    brass = create_material('M_TrainingInlay', (.18, .14, .07), metallic=.65, roughness=.5)
    glow = create_material('M_TrainingCandleGlow', (1, .35, .06), roughness=.5, emission=4)
    # A single solid slab provides continuous collision under all modular floor seams.
    box('Foundation_ContinuousCollision', (0, 0, -90), (2460, 2460, 90), stone, collision=True)
    finish = floor_material()
    for ix in range(4):
        for iy in range(4):
            mesh(f'StoneFloor_{ix}_{iy}', PACK + '/Meshes/Architecture/Dungeon/SM_Floor',
                 (-900 + ix * 600, -900 + iy * 600, .2), material=finish)
    # Quiet metal inlay defines the working area without a bright grid or permanent combat FX.
    for i in range(64):
        angle = i * math.tau / 64
        box(f'ArenaInlay_{i:02}', (860 * math.cos(angle), 860 * math.sin(angle), .25),
            (4, 83, .45), brass, math.degrees(angle))
    for i in range(8):
        angle = i * math.tau / 8
        box(f'ArenaDirection_{i}', (890 * math.cos(angle), 890 * math.sin(angle), .3),
            (58, 6, .4), brass, math.degrees(angle))
    # Tall walls are placed on the far sides of the quarter-view camera; near edges stay low.
    wall_path = PACK + '/Meshes/Architecture/Crypt/SM_Crypt_Wall'
    decor_path = PACK + '/Meshes/Architecture/Crypt/SM_Crypt_Wall_Decorative_A'
    for i in range(4):
        v = -900 + i * 600
        mesh(f'NorthWall_{i}', decor_path if i % 2 else wall_path,
             (v, 1210, 0), (1.2, 1.4, 1.35), collision=True)
        mesh(f'EastWall_{i}', decor_path if i % 2 else wall_path,
             (1210, v, 0), (1.2, 1.4, 1.35), yaw=90, collision=True)
    for axis in (0, 1):
        for i in range(4):
            pos = [-900 + i * 600, -1210, 0] if axis == 0 else [-1210, -900 + i * 600, 0]
            box(f'LowPerimeter_{axis}_{i}', pos, (600, 65, 110) if axis == 0 else (65, 600, 110),
                load(PACK + '/Materials/M_StoneWall_Inst'), collision=True)
    for i, (x, y) in enumerate(((-1000, 1075), (-350, 1075), (350, 1075), (1000, 1075),
                                (1075, -1000), (1075, -350), (1075, 350))):
        mesh(f'Pillar_{i}', PACK + '/Meshes/Architecture/Dungeon/SM_Pillar', (x, y, 0),
             (1.35, 1.35, 1.38), collision=True)
        mesh(f'CandleStand_{i}', PACK + '/Meshes/Props/SM_Candle_Holder',
             (x - 110, y - 100, 0), (.6, .6, .6))
        # Visible flame-shaped solid light sources avoid ambient particle/audio interference.
        mesh(f'CandleFlame_{i}', '/Engine/BasicShapes/Sphere',
             (x - 110, y - 100, 129), (.055, .055, .13), material=glow)
        light(f'WarmLantern_{i}', (x - 110, y - 100, 155), (1, .60, .28), 250, 550)
    # Large arches and statues add depth outside the playable circle.
    for i, (x, y, yaw) in enumerate(((-600, 1200, 90), (600, 1200, 90), (1200, 600, 0))):
        mesh(f'BackdropArch_{i}', PACK + '/Meshes/Architecture/Dungeon/SM_Decorative_Arches',
             (x, y, 0), yaw=yaw)
    for i, (x, y) in enumerate(((-1050, 600), (600, 1050))):
        mesh(f'GuardianBase_{i}', PACK + '/Meshes/Props/SM_Statue_Stand', (x, y, 0), (2, 2, 1.2))
        mesh(f'Guardian_{i}', PACK + '/Meshes/Props/SM_Statue_Hooded', (x, y, 63),
             (1.35, 1.35, 1.35), yaw=-135)
    # Targets retain the proven damage/reset/status actor while using a finished stone model.
    for i, (x, y) in enumerate(((-550, 450), (0, 450), (550, 450))):
        target = actors.spawn_actor_from_class(unreal.KwangTrainingDummy, unreal.Vector(x, y, 90))
        target.set_actor_label(f'TrainingTarget_{i+1}')
        target.tags = ['TrainingRoomTarget']
        target.set_folder_path('TrainingRoom/Targets')
        comp = target.get_component_by_class(unreal.StaticMeshComponent)
        comp.set_static_mesh(load(PACK + '/Meshes/Props/SM_Statue_Hooded'))
        for slot in range(comp.get_num_materials()):
            comp.set_material(slot, budget_material(comp.get_material(slot)))
        comp.set_relative_location(unreal.Vector(0, 0, -90), False, False)
        comp.set_relative_scale3d(unreal.Vector(.8, .8, .85))
        comp.set_relative_rotation(unreal.Rotator(yaw=-90), False, False)
        label = target.get_component_by_class(unreal.TextRenderComponent)
        label.set_world_size(16)
        label.set_relative_location(unreal.Vector(0, 0, 100), False, False)
    sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1000),
                                       unreal.Rotator(pitch=-55, yaw=-35))
    sun.set_actor_label('TrainingRoom_CoolKey')
    sun_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_comp.set_light_color(unreal.LinearColor(.82, .87, 1, 1))
    sun_comp.set_intensity(3.8)
    sun_comp.set_editor_property('forward_shading_priority', 1)
    fill = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 900),
                                        unreal.Rotator(pitch=-35, yaw=45))
    fill.set_actor_label('TrainingRoom_CameraSideFill')
    fill_comp = fill.get_component_by_class(unreal.DirectionalLightComponent)
    fill_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill_comp.set_light_color(unreal.LinearColor(.8, .88, 1, 1))
    fill_comp.set_intensity(1.0)
    fill_comp.set_editor_property('cast_shadows', False)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 800))
    sky.set_actor_label('TrainingRoom_SoftFill')
    sky_comp = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    cubemap = unreal.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')
    if cubemap:
        sky_comp.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        sky_comp.set_cubemap(cubemap)
    sky_comp.set_intensity(1.0)
    sky_comp.set_light_color(unreal.LinearColor(.82, .88, 1, 1))
    pp = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
    pp.set_actor_label('TrainingRoom_ExposureAndGrade')
    pp.set_editor_property('unbound', True)
    settings = pp.get_editor_property('settings')
    for key, value in {'auto_exposure_min_brightness': 0.0, 'auto_exposure_max_brightness': 0.0,
                       'auto_exposure_bias': .5, 'bloom_intensity': .25, 'vignette_intensity': .25,
                       'motion_blur_amount': 0.0}.items():
        settings.set_editor_property('override_' + key, True)
        settings.set_editor_property(key, value)
    pp.set_editor_property('settings', settings)
    fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -80))
    fog.set_actor_label('TrainingRoom_PeripheralHaze')
    fog_comp = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_comp.set_editor_property('fog_density', .008)
    fog_comp.set_editor_property('fog_height_falloff', .3)
    fog_comp.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(.025, .033, .05, 1))
    fog_comp.set_editor_property('start_distance', 900.0)
    unreal.EditorAssetLibrary.make_directory(DEST + '/Maps')
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, MAP):
        raise RuntimeError('Could not save the new practice room')
    preserved = verify(BASELINE)
    report.update(passed=preserved['passed'], baseline_after=preserved,
                  actor_count=len(actors.get_all_level_actors()), default_pawn='Countess',
                  hero_switch='One=Countess, Two=Sparrow', character_code_modified=False)


if __name__ == '__main__':
    try:
        build()
    except Exception as error:
        report.update(passed=False, error=str(error), traceback=traceback.format_exc())
        unreal.log_error(traceback.format_exc())
    finally:
        (OUT / 'build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        unreal.SystemLibrary.quit_editor()
