"""Map-owned neutral stone and world-space exterior veil for Trial Tower.

Run apply() in the owned editor, with PIE stopped. Imported packs and character
materials are never saved or edited. The veil preserves the room, four entrance
mouths and the diagonal ascent; only the surrounding world is darkened.
"""
import json
from pathlib import Path
import unreal
import environment as hall

M = unreal.MaterialEditingLibrary
A = unreal.EditorAssetLibrary
DEST = hall.DEST + '/Materials'


def node(mat, kind, **props):
    result = M.create_material_expression(mat, getattr(unreal, 'MaterialExpression' + kind))
    if not result:
        raise RuntimeError('Cannot create material expression ' + kind)
    for name, value in props.items():
        result.set_editor_property(name, value)
    return result


def wire(source, channel, target, name):
    if not M.connect_material_expressions(source, channel, target, name):
        raise RuntimeError('Cannot connect material input ' + name)


def authored_material(name):
    asset = unreal.load_asset(DEST + '/' + name)
    if not asset:
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    if not asset:
        raise RuntimeError('Cannot create ' + name)
    asset.modify()
    M.delete_all_material_expressions(asset)
    return asset


def save_material(asset):
    M.recompile_material(asset)
    if not A.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    return asset


def floor(name, tiling, tint):
    mat = authored_material(name)
    uv = node(mat, 'TextureCoordinate', u_tiling=tiling, v_tiling=tiling)
    color = node(mat, 'TextureSample', texture=hall.load('/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_A'))
    normal = node(mat, 'TextureSample', texture=hall.load('/Game/MedievalDungeon/Textures/T_BrickFloor_Clean_N'),
                  sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wire(uv, '', color, 'UVs'); wire(uv, '', normal, 'UVs')
    grey = node(mat, 'Desaturation')
    amount = node(mat, 'Constant', r=.92)
    wire(color, 'RGB', grey, ''); wire(amount, '', grey, 'Fraction')
    tone = node(mat, 'Constant3Vector', constant=unreal.LinearColor(*tint, 1))
    multiply = node(mat, 'Multiply')
    wire(grey, '', multiply, 'A'); wire(tone, '', multiply, 'B')
    M.connect_material_property(multiply, '', unreal.MaterialProperty.MP_BASE_COLOR)
    M.connect_material_property(normal, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    rough = node(mat, 'Constant', r=.9)
    M.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    return save_material(mat)


def neutral_instance(source):
    if source.get_path_name().startswith(hall.DEST):
        target = source
    else:
        name = 'MI_TowerNeutral_' + source.get_name().removeprefix('MI_').removeprefix('M_')
        path = DEST + '/' + name
        target = unreal.load_asset(path) or A.duplicate_asset(source.get_path_name(), path)
    if not target:
        raise RuntimeError('Cannot copy stone material ' + source.get_path_name())
    target.modify()
    names = {str(name) for name in M.get_vector_parameter_names(target)}
    palette = {'Color1 LightSide': (.23, .245, .26),
               'Color2 LightSide': (.095, .105, .115),
               'MossColor LightSide': (.065, .075, .07)}
    for name, color in palette.items():
        if name in names:
            M.set_material_instance_vector_parameter_value(target, name, unreal.LinearColor(*color, 1))
    for name in names:
        if name.startswith('TintMarble') or name == 'Tint_MarbleStairs':
            M.set_material_instance_vector_parameter_value(target, name, unreal.LinearColor(.36, .39, .42, 1))
    M.update_material_instance(target)
    if not A.save_loaded_asset(target, False):
        raise RuntimeError('Cannot save neutral stone copy')
    return target


VEIL = r'''
// Soft world-space bounds retain real masonry silhouettes, independent of HUD.
float2 p = World.xy;
float2 q = abs(p);
float room = 1.0 - smoothstep(1675.0, 1840.0, max(q.x, q.y));
float doorway = (1.0 - smoothstep(450.0, 550.0, min(q.x, q.y)))
             * (1.0 - smoothstep(2210.0, 2370.0, max(q.x, q.y)));
float2 stair = float2((p.x+p.y-3420.0)*0.70710678, (p.x-p.y)*0.70710678);
float ascent = 1.0 - smoothstep(0.0, 110.0,
                    max(abs(stair.x)-570.0, abs(stair.y)-490.0));
float mask = max(room, max(doorway, ascent));
// The large construction foundation sits below the playable floor.
mask *= smoothstep(-180.0, -65.0, World.z);
return lerp(float3(0.0015,0.0018,0.0022), Scene.rgb, saturate(mask));
'''


def exterior_veil():
    mat = authored_material('M_TowerExteriorVeil')
    mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    mat.set_editor_property('blendable_priority', 50)
    scene = node(mat, 'SceneTexture', scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    world = node(mat, 'WorldPosition')
    shader = node(mat, 'Custom', code=VEIL, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for name in ('Scene', 'World'):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    shader.set_editor_property('inputs', inputs)
    wire(scene, 'Color', shader, 'Scene'); wire(world, '', shader, 'World')
    M.connect_material_property(shader, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    save_material(mat)
    actors = hall.ACTORS.get_all_level_actors()
    existing = [a for a in actors if a.get_actor_label() == 'TrialTower_ExteriorVeil']
    if len(existing) > 1:
        raise RuntimeError('Duplicate exterior veil volume')
    volume = existing[0] if existing else hall.ACTORS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
    volume.modify()
    volume.set_actor_label('TrialTower_ExteriorVeil')
    volume.set_folder_path('TrialTower/Presentation')
    volume.tags = ['TrialTowerEnvironment']
    volume.set_editor_property('unbound', True)
    volume.set_editor_property('priority', 200.0)
    volume.add_or_update_blendable(mat, 1.0)
    return mat


def apply(output=None):
    world = unreal.EditorLoadingAndSavingUtils.load_map(hall.MAP)
    if not world:
        raise RuntimeError('Could not load Trial Tower')
    floor('M_TowerWornFloor', 4.5, (.27, .285, .30))
    floor('M_TowerApproachFloor', 1.5, (.10, .105, .11))
    hall.material('M_TowerSandstone', (.16, .175, .19))
    hall.material('M_TowerShadowStone', (.055, .06, .068))
    hall.material('M_TowerAgedBronze', (.10, .10, .095), .78, .30)
    changed = {}
    for actor in hall.ACTORS.get_all_level_actors():
        label = actor.get_actor_label()
        if not label.startswith('TrialTower_'):
            continue
        actor.modify()
        mesh = actor.get_component_by_class(unreal.StaticMeshComponent)
        if mesh:
            for index, source in enumerate(mesh.get_materials()):
                if isinstance(source, unreal.MaterialInstanceConstant):
                    path = source.get_path_name()
                    if path not in changed:
                        changed[path] = neutral_instance(source)
                    mesh.set_material(index, changed[path])
        if isinstance(actor, unreal.DirectionalLight):
            light = actor.get_component_by_class(unreal.DirectionalLightComponent)
            light.set_light_color(unreal.LinearColor(.94, .97, 1, 1))
            light.set_intensity(2.0 if label.endswith('SunThroughOpenRoof') else .40)
        elif isinstance(actor, unreal.SkyLight):
            light = actor.get_component_by_class(unreal.SkyLightComponent)
            light.set_light_color(unreal.LinearColor(.95, .97, 1, 1))
            light.set_intensity(.55)
        elif isinstance(actor, unreal.PointLight):
            light = actor.get_component_by_class(unreal.PointLightComponent)
            light.set_light_color(unreal.LinearColor(1, .84, .65, 1))
            light.set_intensity(700 if label.endswith('AscentWarmPool') else 280)
        elif isinstance(actor, unreal.ExponentialHeightFog):
            fog = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            fog.set_editor_property('fog_density', .003)
            fog.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(.012, .016, .02, 1))
    veil = exterior_veil()
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, hall.MAP):
        raise RuntimeError('Could not save Trial Tower presentation')
    report = {'map': hall.MAP, 'veil': veil.get_path_name(), 'neutral_materials':
              {k:v.get_path_name() for k,v in changed.items()}, 'character_materials_modified': False}
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
        (Path(output) / 'presentation-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
