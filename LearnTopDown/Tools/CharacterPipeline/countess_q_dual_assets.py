"""Build the Q-only, world-sized crescent/rush/impact material without pack edits."""
import json
import os
from pathlib import Path
import traceback
import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
PATH = '/Game/TopDown/Characters/Countess/Materials/M_CountessQDualSweep'

# All positions and time below are local to a transient Q visual. No scene depth,
# camera effect, world position offset or gameplay collision is involved.
SHADER = r'''
float age = max(0, Clock - SpawnTime);
float t = saturate(age / max(Duration, 0.001));
float2 p = (UV - 0.5) * 2;
float3 blood = float3(9.0, 0.025, 0.08);
float3 hot = float3(23.0, 9.0, 6.0);
float shape = 0;
float core = 0;
float fade = pow(1 - t, 1.1);
if (Mode < 0.5)
{
    // UV.x is the measured Ability_Q sample time, UV.y spans the imported blade width (OBJ flips V).
    float head = saturate((age - 0.10) / (0.216666667 - 0.10));
    float revealed = 1 - smoothstep(head, head + 0.045, UV.x);
    // Suppress the crossed-hand wind-up, emphasizing two independent outward cuts.
    float outward = smoothstep(0.20, 0.48, UV.x);
    float ends = pow(saturate(sin(UV.x * 3.14159265)), 0.40) * outward;
    float width = pow(saturate(sin(UV.y * 3.14159265)), 0.70);
    float fibers = 0.92 + 0.08 * sin(UV.y * 45 + UV.x * 19);
    float blade = pow(saturate(1 - abs(UV.y - 0.72) / 0.24), 1.6);
    shape = revealed * ends * (blade * 0.85 + width * 0.16) * fibers;
    float front = pow(saturate(1 - abs(UV.x - head) / 0.10), 2);
    float edge = pow(saturate(1 - abs(UV.y - 0.82) / 0.065), 2);
    core = revealed * ends * (edge * 0.85 + front * blade * 0.75);
    fade = pow(saturate(1 - max(0, age - 0.22) / 0.36), 1.4);
}
else if (Mode < 1.5)
{
    // The actual departure-to-target segment, tapered at both ends.
    float ends = pow(saturate(sin(UV.x * 3.14159265)), 0.7);
    float bend = 0.045 * sin(UV.x * 3.14159265);
    float d = abs(p.y - bend);
    shape = pow(saturate(1 - d / (0.18 * ends + 0.008)), 2) * ends;
    core = pow(saturate(1 - d / 0.023), 2) * ends;
    fade = pow(1 - t, 2.0);
}
else
{
    // A short bright impact at the real damage event, not a permanent cross.
    float r = length(p);
    float a = atan2(p.y, p.x);
    float star = pow(abs(cos(a * 2)), 30);
    float rays = star * pow(saturate(1 - r), 2);
    float center = pow(saturate(1 - r / 0.25), 3);
    float ring = pow(saturate(1 - abs(r - (0.10 + t * 0.65)) / 0.035), 2) * 0.22;
    shape = saturate(rays + center + ring);
    core = center + rays * 0.7;
    fade = pow(1 - t, 2.0);
}
return float4(blood * shape + hot * core, saturate(shape * fade));
'''

report = {'passed': False, 'asset': PATH}
try:
    library = unreal.MaterialEditingLibrary
    material = unreal.load_asset(PATH)
    if material is None:
        folder, name = PATH.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    material.modify()
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    existing = list(library.get_material_expressions(material))
    cursor = 0

    def node(kind, **properties):
        global cursor
        cls = getattr(unreal, 'MaterialExpression' + kind)
        result = existing[cursor] if cursor < len(existing) else library.create_material_expression(material, cls)
        if result.get_class().get_name() != 'MaterialExpression' + kind:
            raise RuntimeError('Unexpected existing Q crescent graph node ' + str(cursor))
        cursor += 1
        for key, value in properties.items():
            result.set_editor_property(key, value)
        return result

    custom = node('Custom', code=SHADER,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                  description='Measured dual weapon sweep / departure ribbon / hit burst')
    names = ('UV', 'Clock', 'SpawnTime', 'Duration', 'Mode')
    inputs = []
    for name in names:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    custom.set_editor_property('inputs', inputs)
    sources = [node('TextureCoordinate'), node('Time', ignore_pause=False)]
    sources += [node('ScalarParameter', parameter_name=name, default_value=value)
                for name, value in (('SpawnTime', 0), ('Duration', .44), ('Mode', 0))]
    for name, source in zip(names, sources):
        if not library.connect_material_expressions(source, '', custom, name):
            raise RuntimeError('Unconnected custom material input ' + name)
    for channels, prop in ((dict(r=True, g=True, b=True, a=False), unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                           (dict(r=False, g=False, b=False, a=True), unreal.MaterialProperty.MP_OPACITY)):
        mask = node('ComponentMask', **channels)
        pin = library.get_material_expression_input_names(mask)[0]
        if not library.connect_material_expressions(custom, '', mask, pin):
            raise RuntimeError('Unconnected crescent output mask')
        if not library.connect_material_property(mask, '', prop):
            raise RuntimeError('Unconnected crescent material output')
    if existing and cursor != len(existing):
        raise RuntimeError('Unexpected unused Q graph nodes')
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Q crescent material save failed')
    # Bake two disconnected ruled strips from the actual authored weapon sockets.
    animation = unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Ability_Q')
    hero_mesh = unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Meshes/SM_Countess')
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('optional_skeletal_mesh', hero_mesh)
    options.set_editor_property('evaluation_type', unreal.AnimDataEvalType.RAW)
    path = '/Game/TopDown/Characters/Countess/FX/SM_CountessQDualSweep'
    evidence = []
    for side in ('L', 'R'):
        rows = []
        for frame in range(12, 27):
            seconds = frame / 120
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, seconds, options)
            names = [f'FX_Weapon{part}_{side}' for part in ('Base', 'Tip')]
            raw = [unreal.AnimPoseExtensions.get_socket_pose(pose, name, unreal.AnimPoseSpaces.WORLD).translation for name in names]
            points = [unreal.Vector(v.x*2.6, 20+(v.y-20)*2.6, 100+(v.z-100)*2.6) for v in raw]
            evidence.append({'side': side, 'seconds': seconds,
                'raw_cm': [[v.x,v.y,v.z] for v in raw], 'mesh_cm': [[v.x,v.y,v.z] for v in points]})
    obj = ['o CountessQDualSweep']
    for row in evidence:
        for v in row['mesh_cm']:
            obj.append('v ' + ' '.join(str(x) for x in (v[0],-v[1],v[2])))
    for row in evidence:
        u=(row['seconds']-.1)/(26/120-.1)
        obj += [f'vt {u} 0',f'vt {u} 1']
    for start in (0,30):
        for i in range(14):
            a=start+i*2+1; b=a+1; c=a+3; d=a+2
            obj += [f'f {a}/{a} {b}/{b} {c}/{c}',f'f {a}/{a} {c}/{c} {d}/{d}']
    obj_path=OUT/'CountessQDualSweep.obj'
    obj_path.write_text('\n'.join(obj))
    task=unreal.AssetImportTask()
    task.set_editor_property('filename',str(obj_path))
    task.set_editor_property('destination_path',path.rsplit('/',1)[0])
    task.set_editor_property('destination_name',path.rsplit('/',1)[1])
    task.set_editor_property('automated',True)
    task.set_editor_property('replace_existing',True)
    task.set_editor_property('save',False)
    task.set_editor_property('factory',unreal.FbxFactory())
    settings=unreal.FbxImportUI()
    settings.set_editor_property('automated_import_should_detect_type',False)
    settings.set_editor_property('mesh_type_to_import',unreal.FBXImportType.FBXIT_STATIC_MESH)
    settings.set_editor_property('import_mesh',True)
    settings.set_editor_property('import_materials',False)
    settings.set_editor_property('import_textures',False)
    data=settings.get_editor_property('static_mesh_import_data')
    for key,value in dict(combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,generate_lightmap_u_vs=False).items():
        data.set_editor_property(key,value)
    task.set_editor_property('options',settings)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sweep=unreal.load_asset(path)
    if sweep is None: raise RuntimeError('Dual mesh OBJ import failed')
    sweep.set_editor_property('static_materials',[unreal.StaticMaterial(material_interface=material, material_slot_name='DualSweep')])
    if not unreal.EditorAssetLibrary.save_loaded_asset(sweep,False):
        raise RuntimeError('Dual sweep mesh save failed')
    report['bounds'] = str(sweep.get_bounds())
    description=sweep.get_static_mesh_description(0)
    vertices=[]
    for index in range(description.get_vertex_count()):
        v=description.get_vertex_position(unreal.VertexID(index))
        vertices.append([v.x,v.y,v.z])
    expected=[v for row in evidence for v in row['mesh_cm']]
    errors=[min(sum((x-y)**2 for x,y in zip(a,b))**.5 for b in vertices) for a in expected]
    if max(errors)>.01: raise RuntimeError('Imported sweep no longer matches measured sockets: '+str(max(errors)))
    report['max_import_position_error_cm']=max(errors)
    report['imported_vertices']=vertices
    report['obj_handedness_compensated']=True
    report['mesh'] = path
    report['trajectory_samples'] = evidence
    report['enlargement_about_chest'] = 2.6
    report['raw_animation_range_seconds'] = [.1,26/120]
    report.update(passed=True, graph_connections_verified=True, shader_compile_verified=False,
                  shader=SHADER, original_pack_changed=False)
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


