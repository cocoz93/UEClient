"""Author private Q straight outward blades; never modify an existing pack asset."""
import hashlib
import json
import math
import os
from pathlib import Path
import traceback

import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
MATERIAL = '/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut'
MESH = '/Game/TopDown/Characters/Countess/FX/SM_CountessQOutwardCut'
CONTENT = Path(unreal.Paths.project_content_dir()).resolve()
OWNED = {CONTENT / 'TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.uasset',
         CONTENT / 'TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.uasset'}

SHADER = r'''
float age = max(0, Clock - SpawnTime);
float t = saturate(age / max(Duration, 0.001));
float2 p = (UV - 0.5) * 2;
float3 color = 0;
float alpha = 0;
if (Mode < 0.5)
{
    float head = saturate((age - 0.10) / (0.216666667 - 0.10));
    float reveal = 1 - smoothstep(head, head + 0.035, UV.x);
    float fade = pow(saturate(1 - max(0, age - 0.23) / 0.24), 1.7);
    if (UV.y > 1.5)
    {
        // Disconnected, short flecks. This is not another full-width ribbon.
        float v = UV.y - 2;
        float width = pow(saturate(1 - abs(v - 0.5) * 2), 0.65);
        float grain = 0.55 + 0.45 * sin(UV.x * 331 + v * 14);
        alpha = reveal * fade * width * saturate(grain) * 0.78;
        float edge = pow(saturate(1 - abs(v - 0.76) / 0.15), 3);
        color = lerp(float3(0.007, 0.0004, 0.001), float3(1.9, 0.018, 0.035), edge);
    }
    else
    {
        float ends = pow(saturate(sin(UV.x * 3.14159265)), 0.38);
        float v = abs(UV.y - 0.5) * 2;
        float noise = sin(UV.x * 119 + sin(UV.y * 21) * 3)
                    * sin(UV.x * 37 - UV.y * 31);
        float roughEdge = saturate((1 - v + noise * 0.12) * 4);
        float body = roughEdge * ends;
        float core = pow(saturate(1 - v / 0.19), 1.7);
        float filament = pow(saturate(1 - abs(UV.y - 0.67) / 0.055), 2);
        color = lerp(float3(0.009, 0.0006, 0.0015), float3(1.8, 0.012, 0.028), saturate((1-v)*1.2));
        color += float3(15, 7.4, 5.2) * core + float3(4.5, 0.05, 0.10) * filament;
        alpha = reveal * fade * body * 0.92;
    }
}
else if (Mode < 1.5)
{
    float ends = pow(saturate(sin(UV.x * 3.14159265)), 0.7);
    float d = abs(p.y);
    float shape = pow(saturate(1 - d / (0.15 * ends + 0.008)), 2) * ends;
    float core = pow(saturate(1 - d / 0.022), 2) * ends;
    color = float3(5, 0.014, 0.04) * shape + float3(15, 7, 5) * core;
    alpha = shape * pow(1-t, 2);
}
else
{
    float r = length(p);
    float a = atan2(p.y, p.x);
    float rays = pow(abs(cos(a * 2)), 30) * pow(saturate(1-r), 2);
    float center = pow(saturate(1-r/0.25), 3);
    color = float3(6, 0.02, 0.06) * rays + float3(18, 8, 5) * (center + rays * 0.7);
    alpha = saturate(rays + center) * pow(1-t, 2);
}
return float4(color, saturate(alpha));
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_hashes():
    return {str(p.relative_to(CONTENT)): digest(p) for p in CONTENT.rglob('*')
            if p.is_file() and p not in OWNED}


report = {'passed': False, 'asset': MATERIAL, 'mesh': MESH,
          'shader_compile_verified': False, 'original_pack_changed': False}
protected = protected_hashes()
try:
    library = unreal.MaterialEditingLibrary
    material = unreal.load_asset(MATERIAL)
    if material is None:
        folder, name = MATERIAL.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError('Outward material creation failed')
    material.modify()
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    # Rebuild only this owned graph; no assumptions about an earlier failed run.
    library.delete_all_material_expressions(material)

    def node(kind, **properties):
        result = library.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in properties.items():
            result.set_editor_property(key, value)
        return result

    custom = node('Custom', code=SHADER, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                  description='Two straight outward cuts with disconnected blood-black flecks')
    names = ('UV', 'Clock', 'SpawnTime', 'Duration', 'Mode')
    inputs = []
    for name in names:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    custom.set_editor_property('inputs', inputs)
    sources = [node('TextureCoordinate'), node('Time', ignore_pause=False)]
    sources += [node('ScalarParameter', parameter_name=name, default_value=value)
                for name, value in (('SpawnTime', 0), ('Duration', .58), ('Mode', 0))]
    for name, source in zip(names, sources):
        if not library.connect_material_expressions(source, '', custom, name):
            raise RuntimeError('Unconnected custom material input ' + name)
    for channels, prop in ((dict(r=True, g=True, b=True, a=False), unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                           (dict(r=False, g=False, b=False, a=True), unreal.MaterialProperty.MP_OPACITY)):
        mask = node('ComponentMask', **channels)
        pin = library.get_material_expression_input_names(mask)[0]
        if not library.connect_material_expressions(custom, '', mask, pin):
            raise RuntimeError('Unconnected outward output mask')
        if not library.connect_material_property(mask, '', prop):
            raise RuntimeError('Unconnected outward material output')
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Outward material save failed')

    animation = unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Ability_Q')
    hero_mesh = unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Meshes/SM_Countess')
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', hero_mesh)
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    samples = []

    def sockets(side, seconds):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, seconds, options)
        points = [unreal.AnimPoseExtensions.get_socket_pose(pose, 'FX_Weapon' + part + '_' + side,
                  unreal.AnimPoseSpaces.WORLD).translation for part in ('Base', 'Tip')]
        values = [[v.x, v.y, v.z] for v in points]
        samples.append({'side': side, 'seconds': seconds, 'raw_cm': values})
        return values

    vertices, uvs, faces, geometry = [], [], [], []

    def add_quad(points, tex):
        start = len(vertices) + 1
        vertices.extend(points)
        uvs.extend(tex)
        faces.extend([(start, start+1, start+2), (start, start+2, start+3)])

    for side, sign in (('L', 1), ('R', -1)):
        first = sockets(side, .10)
        initial = sockets(side, .15)
        final = sockets(side, 26/120)
        if sign * (final[1][0] - initial[1][0]) <= 100:
            raise RuntimeError('Original weapon outward X axis no longer matches ' + side)
        # The source selects side/initial chest height only. Never connect its curved trajectory.
        y = sum(p[1] for p in initial) / 2
        z = sum(p[2] for p in initial) / 2
        start = [sign*24, y, z]
        end = [final[1][0]*2.6, y + max(-45, min(45, final[1][1]-y)), z-8]
        dx, dy = end[0]-start[0], end[1]-start[1]
        length = math.hypot(dx, dy)
        perpendicular = [-dy/length, dx/length, 0]
        centers = []
        for u in (0, .12, .48, .86, 1):
            centers.append([start[i] + (end[i]-start[i])*u for i in range(3)])
        half_widths = [2, 24, 27, 13, .5]
        for index in range(len(centers)-1):
            ua, ub = (0, .12, .48, .86, 1)[index:index+2]
            ca, cb = centers[index:index+2]
            wa, wb = half_widths[index:index+2]
            add_quad([[c[j] + s*w*perpendicular[j] for j in range(3)]
                      for c, w, s in ((ca, wa, -1), (ca, wa, 1), (cb, wb, 1), (cb, wb, -1))],
                     [[ua, 0], [ua, 1], [ub, 1], [ub, 0]])
        # Small detached dark-red scraps above/below each blade, no connected enclosing surface.
        for index in range(12):
            u = .18 + index*.061
            direction = 1 if index % 2 else -1
            offset = direction * (32 + (index*17 % 37))
            center = [start[j] + (end[j]-start[j])*u + perpendicular[j]*offset for j in range(3)]
            center[2] += (index % 3 - 1)*7
            half_length = 8 + (index*11 % 16)
            half_width = 2.5 + (index*3 % 6)
            along = [dx/length, dy/length, 0]
            points = [[center[j] + a*half_length*along[j] + b*half_width*perpendicular[j]
                       for j in range(3)] for a,b in ((-1,-1),(-1,1),(1,1),(1,-1))]
            du = half_length/length
            add_quad(points, [[u-du, 2], [u-du, 3], [u+du, 3], [u+du, 2]])
        straightness = [math.dist(c, [start[j]+(end[j]-start[j])*u for j in range(3)])
                        for c,u in zip(centers, (0,.12,.48,.86,1))]
        geometry.append({'side': side, 'start_cm': start, 'end_cm': end,
                         'centerline_vertices_cm': centers, 'max_centerline_curve_deviation_cm': max(straightness),
                         'half_widths_cm': half_widths, 'disconnected_fleck_quads': 12,
                         'outward_angle_from_lateral_degrees': math.degrees(math.atan2(abs(dy),abs(dx)))})
    span = max(p[0] for p in vertices)-min(p[0] for p in vertices)
    if not 680 < span < 820:
        raise RuntimeError('Outward total lateral span out of 7m design bound: ' + str(span))
    obj = ['o CountessQOutwardCut']
    # Unreal OBJ importer changes handedness and flips V. Compensate explicitly.
    obj += ['v ' + ' '.join(str(x) for x in (v[0], -v[1], v[2])) for v in vertices]
    obj += ['vt ' + str(u) + ' ' + str(1-v) for u,v in uvs]
    obj += ['f ' + ' '.join(str(i)+'/'+str(i) for i in tri) for tri in faces]
    obj_path = OUT / 'CountessQOutwardCut.obj'
    obj_path.write_text('\n'.join(obj), encoding='utf-8')
    task = unreal.AssetImportTask()
    for key,value in dict(filename=str(obj_path), destination_path=MESH.rsplit('/',1)[0],
                          destination_name=MESH.rsplit('/',1)[1], automated=True,
                          replace_existing=True, save=False, factory=unreal.FbxFactory()).items():
        task.set_editor_property(key,value)
    settings = unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,
                          mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                          import_mesh=True, import_materials=False, import_textures=False).items():
        settings.set_editor_property(key,value)
    data = settings.get_editor_property('static_mesh_import_data')
    for key,value in dict(combine_meshes=True, auto_generate_collision=False, convert_scene=False,
                          convert_scene_unit=False, force_front_x_axis=False, generate_lightmap_u_vs=False).items():
        data.set_editor_property(key,value)
    task.set_editor_property('options',settings)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError('Outward OBJ import failed')
    mesh.set_editor_property('static_materials',[unreal.StaticMaterial(material_interface=material, material_slot_name='OutwardCut')])
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh,False):
        raise RuntimeError('Outward mesh save failed')
    description = mesh.get_static_mesh_description(0)
    imported = []
    for index in range(description.get_vertex_count()):
        value = description.get_vertex_position(unreal.VertexID(index))
        imported.append([value.x,value.y,value.z])
    errors = [min(math.dist(a,b) for b in imported) for a in vertices]
    if max(errors) > .01:
        raise RuntimeError('Outward imported positions differ: ' + str(max(errors)))
    after = protected_hashes()
    changes = [key for key in protected if after.get(key) != protected[key]]
    if changes:
        raise RuntimeError('Protected content changed: ' + str(changes))
    report.update(passed=True, graph_connections_verified=True, blend='Translucent',
                  shader=SHADER, bounds=str(mesh.get_bounds()), geometry=geometry,
                  trajectory_samples=samples, raw_animation_range_seconds=[.1,26/120],
                  source_axis='skeletal mesh local X is lateral; L positive / R negative',
                  centerlines_straight=True, total_lateral_span_cm=span,
                  max_import_position_error_cm=max(errors), imported_vertices=imported,
                  authored_vertex_count=len(vertices), authored_triangle_count=len(faces),
                  protected_content_files=len(protected), protected_content_changes=changes,
                  obj_handedness_compensated=True, obj_uv_v_flip_compensated=True,
                  gameplay_or_original_asset_changes=False)
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'material.json').write_text(json.dumps(report,indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
