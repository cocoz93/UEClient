"""S broad gold-flame wings and one attached D shadow. Root owns UE execution.

Only project-owned assets are saved. The wing mesh is generated from explicit
Bezier bands, rather than imported character geometry or skeletal tendrils.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


MESH = '/Game/TopDown/Characters/Sparrow/Meshes/SM_SparrowEnergyWings'
MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowEnergyWings'
SHADOW = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShadowPartner'
FIRE = '/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D'


def _write(output, name, value):
    (Path(output) / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _normal(v):
    length = max(math.sqrt(sum(x*x for x in v)), 1e-6)
    return tuple(x / length for x in v)


def _curve(points, t):
    return tuple((1-t)**3*points[0][i] + 3*(1-t)**2*t*points[1][i] +
                 3*(1-t)*t*t*points[2][i] + t**3*points[3][i] for i in range(3))


def _wing_obj(path):
    """Centimeters; X is behind the body, Y is bilateral, Z is up.

    Three overlapping broad flame bands replace the rejected seven hooked
    tendrils and physical forks. Crosswise subdivisions let the flame fringe
    move without bending the entire wing as a solid plate.
    """
    vertices, uvs, faces = [], [], []
    segments, across_segments = 32, 8
    bands = (((-18, 8, 20), (-32, 65, 72), (-38, 135, 62), (-34, 205, 110)),
             ((-20, 7, 14), (-38, 68, 43), (-46, 142, 26), (-54, 220, 34)),
             ((-22, 8, 7), (-43, 62, 12), (-68, 120, -3), (-88, 178, -20)))
    for side in (-1, 1):
        for strand, source_points in enumerate(bands):
            points = tuple((p[0], p[1]*side, p[2]) for p in source_points)
            for crossing in range(2):
                start = len(vertices)
                for step in range(segments+1):
                    t = step/segments
                    p = _curve(points, t)
                    left, right = _curve(points, max(0, t-.003)), _curve(points, min(1, t+.003))
                    tangent = _normal(tuple(b-a for a, b in zip(left, right)))
                    axis = _normal(_cross(tangent, (1, 0, 0)))
                    if crossing:
                        other = _normal(_cross(tangent, axis))
                        axis = tuple(a*.5+b*.866 for a, b in zip(axis, other))
                    width = (54+strand*3) * (.52+.78*math.sin(math.pi*t)**.55)*(1-t*.45)
                    width *= .93+.10*math.sin(t*8+strand*1.4)
                    for across in range(across_segments+1):
                        v = across/across_segments
                        vertices.append(tuple(a+b*width*(v-.5) for a, b in zip(p, axis)))
                        uvs.append((strand*2+.01+t*.98, v))
                row = across_segments+1
                for step in range(segments):
                    for across in range(across_segments):
                        a = start+step*row+across+1
                        faces.extend(((a, a+1, a+row+1), (a, a+row+1, a+row)))
    lines = ['# Sparrow project-owned curved energy wings; no original asset conversion.', 'o EnergyWings']
    lines += ['v %.7f %.7f %.7f' % v for v in vertices]
    lines += ['vt %.7f %.7f' % uv for uv in uvs]
    lines += ['f '+' '.join('%d/%d' % (v, v) for v in face) for face in faces]
    path.write_text('\n'.join(lines)+'\n', encoding='ascii')
    return {'curves': 6, 'tip_forks': 0, 'crossed_ribbons': 12, 'vertices': len(vertices), 'triangles': len(faces),
            'bounds_cm': [[min(v[i] for v in vertices), max(v[i] for v in vertices)] for i in range(3)]}


def author(output):
    root = Path(unreal.Paths.project_dir()).resolve()
    output = Path(output).resolve()
    assert output.is_relative_to(root/'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True, exist_ok=True)
    source = output/'SM_SparrowEnergyWings.obj'
    geometry = _wing_obj(source)
    options = unreal.FbxImportUI()
    for key, value in {'import_mesh': True, 'import_as_skeletal': False, 'import_materials': False,
                       'import_textures': False, 'automated_import_should_detect_type': False,
                       'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH}.items():
        options.set_editor_property(key, value)
    data = options.get_editor_property('static_mesh_import_data')
    for key, value in {'combine_meshes': True, 'auto_generate_collision': False,
                       'generate_lightmap_u_vs': False, 'convert_scene': False,
                       'convert_scene_unit': False}.items():
        data.set_editor_property(key, value)
    task = unreal.AssetImportTask()
    for key, value in {'filename': str(source), 'destination_path': MESH.rsplit('/', 1)[0],
                       'destination_name': MESH.rsplit('/', 1)[1], 'automated': True,
                       'replace_existing': True, 'replace_existing_settings': True,
                       'save': False, 'options': options, 'factory': unreal.FbxFactory()}.items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(MESH)
    assert isinstance(mesh, unreal.StaticMesh), task.get_editor_property('imported_object_paths')
    helper = runpy.run_path(str(root/'Tools/CharacterPipeline/sparrow_s_silhouette.py'))
    node, wire, lib = helper['_node'], helper['_wire'], unreal.MaterialEditingLibrary
    material = helper['_material'](MATERIAL, False)
    texture = unreal.load_asset(FIRE)
    assert isinstance(texture, unreal.Texture2D)
    shader = helper['_custom'](material, '''
float u = saturate((frac(UV.x)-0.01)/0.98);
float phase = floor(UV.x/2.0)*1.731;
float drift = Clock*.43+phase;
float2 flowUV = float2(u*1.65-drift, UV.y*1.4+sin(u*7.0-Clock*1.8+phase)*.14);
float flowA = Texture2DSample(Fire, FireSampler, flowUV).r;
float flowB = Texture2DSample(Fire, FireSampler, flowUV*float2(1.8,.87)+float2(.37,-drift*.27)).g;
float heat = saturate(flowA*.74+flowB*.26);
float centre = .5+sin(u*7.0-Clock*1.6+phase)*.07;
float across = abs(UV.y-centre)*2.0;
float tornEdge = across+(.48-heat)*.62+sin(u*19.0-Clock*3.0+phase)*.055;
float edge = 1.0-smoothstep(.46,1.03,tornEdge);
float burning = smoothstep(.055,.56,heat)*edge;
float rootHeat = exp(-u*3.5)*saturate(1.0-across)*.72;
float fringe = edge*heat*.14;
float root = smoothstep(0.0,.018,u);
float tip = 1.0-smoothstep(.65,1.0,u);
float reveal = 1.0-smoothstep(Growth-.13, Growth+.02, u);
float pulse = .91+.09*sin(Clock*2.2-u*5.0+phase);
float alpha = saturate((burning*.82+rootHeat*.57+fringe)*root*tip*reveal*Envelope*pulse)*.72;
// Restrict white heat to the shoulder root and sparse transient pockets.
// The rest of the broad, overlapping bands stays translucent saturated gold.
float rootGlow = (1.0-smoothstep(.10,.31,u))*(.56+.30*heat);
float hotPocket = pow(smoothstep(.76,.98,heat),3.0)*.20;
hotPocket *= .5+.5*sin(u*13.0-Clock*1.8+phase);
float hot = saturate(rootGlow+hotPocket)*pow(saturate(1.0-across),.56);
float3 gold = float3(1.85,.70,.015);
float3 whiteGold = float3(5.2,4.5,2.1);
float3 color = lerp(gold,whiteGold,hot)*(.55+.45*heat);
return float4(color, alpha);
''', ('UV', 'Clock', 'Envelope', 'Growth', 'Fire'), unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    uv, clock = node(material, 'TextureCoordinate'), node(material, 'Time')
    wire(uv, shader, 'UV')
    wire(clock, shader, 'Clock')
    wire(node(material, 'ScalarParameter', parameter_name='Envelope', default_value=0.0), shader, 'Envelope')
    wire(node(material, 'ScalarParameter', parameter_name='Growth', default_value=0.0), shader, 'Growth')
    wire(node(material, 'TextureObject', texture=texture), shader, 'Fire')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node(material, 'ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        wire(shader, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    wpo = helper['_custom'](material, '''
float u = saturate((frac(UV.x)-.01)/.98);
float phase = floor(UV.x/2.0)*1.731;
float fringe = pow(abs(UV.y*2.0-1.0),1.4);
float sway = sin(Clock*1.5-u*5.0+phase)*u;
return float3(sway*3.2, sin(Clock*1.2+phase+u*5.0)*u*3.2,
              sway*4.0+sin(Clock*2.8-u*12.0+phase)*u*fringe*6.5);
''', ('UV', 'Clock'), unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    wire(uv, wpo, 'UV')
    wire(clock, wpo, 'Clock')
    assert lib.connect_material_property(wpo, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    lib.recompile_material(material)
    mesh.set_material(0, material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    # The attached D shadow has a continuous silhouette and simple opacity.
    # Shared Echo Visibility also dissolves noise, so it is deliberately untouched.
    shadow = helper['_material'](SHADOW, False)
    silhouette = helper['_custom'](shadow, '''
float rim = saturate(Facing);
float3 tint = BodyTint*(.66+.16*rim);
return float4(tint,saturate(Visibility)*(.23+.12*rim));
''', ('Facing','BodyTint','Visibility'), unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    wire(node(shadow, 'Fresnel', exponent=2.0, base_reflect_fraction=.02), silhouette, 'Facing')
    wire(node(shadow, 'VectorParameter', parameter_name='BodyTint',
              default_value=unreal.LinearColor(.95,.60,.12,1.0)), silhouette, 'BodyTint')
    wire(node(shadow, 'ScalarParameter', parameter_name='Visibility', default_value=0.0), silhouette, 'Visibility')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
        mask = node(shadow,'ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
        wire(silhouette,mask,lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask,'',prop)
    lib.recompile_material(shadow)
    assert unreal.EditorAssetLibrary.save_loaded_asset(shadow,False)
    bounds = mesh.get_bounds()
    report = {'passed': True, 'mesh': MESH, 'material': MATERIAL, 'shadow_material': SHADOW, 'fire_texture': FIRE,
              'geometry': geometry, 'imported_bounds_cm': [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z],
              'source_pack_saved': False,
              'reference': 'https://news.blizzard.com/en-gb/article/13407835/wings-of-valor-now-available',
              'reference_frames_reviewed': ['valor-000.png','valor-011.png','valor-022.png'],
              'intent': 'Three translucent saturated gold-flame bands per side, white-gold limited to roots and sparse heat pockets, torn moving fringe. No hooked skeleton or physical forks.',
              'material_revision': 'valor-gold-translucency-r2', 'opacity_multiplier': .72,
              'gold_rgb': [1.85,.70,.015], 'white_heat_root_u': [.10,.31]}
    _write(output, 'sparrow-energy-author.json', report)
    return report


def _clip(rig, name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name+'_video',
                                    'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()), 'frame_times': []}


def _clones(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))


def _vec(v):
    return [v.x, v.y, v.z]


def sequence(rig):
    report = {'passed': False, 'D': {}, 'S': {}}
    rig['switch']('sparrow')
    yield .7
    ds = rig['layout']([(900, 0), (1250, 0), (900, 420)])
    yield .2
    pawn = rig['pawn']()
    mesh = pawn.get_editor_property('mesh')
    lod_count = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(mesh.get_skeletal_mesh_asset())
    original_materials = [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())]
    original_sections = [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())]
                         for lod in range(lod_count)]
    _clip(rig, 'D_single_shadow_partner')
    rig['use']('D', ds[0])
    yield 1.0
    clones = _clones(rig)
    rig['check'](len(clones) == 1, 'D creates one shadow partner')
    clone = clones[0]
    delta = clone.get_actor_location()-pawn.get_actor_location()
    rig['check'](35 < delta.length() < 55, 'D shadow stays about45cm from the owner')
    rig['check'](delta.dot(pawn.get_actor_forward_vector()) < -35, 'D shadow starts directly behind the owner')
    shadow_mesh = clone.get_components_by_class(unreal.SkeletalMeshComponent)[0]
    rig['check'](shadow_mesh.get_material(0).get_base_material().get_path_name().startswith(SHADOW+'.'),
                 'D uses its own continuous gold silhouette material')
    start = pawn.get_actor_location()
    samples = []
    for offset in (unreal.Vector(0, 260, 0), unreal.Vector(-240, 120, 0)):
        goal = rig['ground'](start.x+offset.x, start.y+offset.y)
        rig['cmd'](f'CountessComboQA.Mouse Move Left {goal.x} {goal.y} {goal.z}')
        rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield 1.0/rig['FPS']
        rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        for _ in range(18):
            yield 1.0/30.0
            samples.append({'owner': _vec(pawn.get_actor_location()), 'partner': _vec(clone.get_actor_location()),
                            'speed': pawn.get_velocity().length()})
    pawn.get_controller().stop_movement()
    yield .25
    rot = pawn.get_actor_rotation()
    pawn.set_actor_rotation(unreal.Rotator(rot.pitch,rot.yaw+180.0,rot.roll),True)
    yield 1.0/rig['FPS']
    expected = pawn.get_actor_location()-pawn.get_actor_forward_vector()*45.0+pawn.get_actor_right_vector()*6.0
    turn_error = (clone.get_actor_location()-expected).length()
    rig['check'](turn_error < 1.0, 'D shadow follows a stationary180degree turn without formation delay')
    count = clone.get_echo_shot_count()
    rig['use']('W', ds[0])
    yield .9
    rig['check'](clone.get_echo_shot_count() == count+1, 'single D partner mirrors W once')
    rig['check'](max(s['speed'] for s in samples) > 100, 'D clip includes actual locomotion')
    rig['capture']('D_single_partner_after_W')
    rig['finish_video_clip']()
    report['D'] = {'count': len(clones), 'samples': samples, 'echo_shots': clone.get_echo_shot_count(),
                   'damage_scale': .3, 'rear_offset_cm': 45, 'stationary_turn_error_cm': turn_error,
                   'material': SHADOW, 'opacity_range': [.23,.35]}

    _clip(rig, 'S_energy_strands')
    rig['use']('S', ds[0])
    yield .5
    actors = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))
    rig['check'](len(actors) == 1, 'S creates one wing actor')
    wings = actors[0]
    parts = [p for p in wings.get_components_by_class(unreal.StaticMeshComponent)
             if 'SparrowEnergyWings' in [str(t) for t in p.get_editor_property('component_tags')]]
    # Timers can create this actor on the exact game frame of the .50s probe.
    # ConfigureVisual starts hidden and the actor's first Tick raises Envelope.
    # Record the allocation state, then wait at most six simulation samples;
    # an absent component or a permanently hidden form still fails the check.
    state = {'time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
             'actor': wings.get_name(), 'initial_part_count': len(parts),
             'initial_visible': [p.is_visible() for p in parts], 'wait_samples': 0,
             'all_static_parts': [{'name': p.get_name(),
                                   'tags': [str(t) for t in p.get_editor_property('component_tags')],
                                   'visible': p.is_visible()}
                                  for p in wings.get_components_by_class(unreal.StaticMeshComponent)]}
    for attempt in range(6):
        if len(parts) == 1 and parts[0].is_visible():
            break
        yield .05
        state['wait_samples'] = attempt+1
    state['final_visible'] = [p.is_visible() for p in parts]
    source_wings = [p for p in wings.get_components_by_class(unreal.SkeletalMeshComponent)
                    if p.get_name() == 'SerathWings']
    state['original_wing_meshes'] = [{'name': p.get_name(), 'visible': p.is_visible()} for p in source_wings]
    _write(rig['OUT'], 'sparrow-energy-visibility.json', state)
    rig['check'](len(parts) == 1 and parts[0].is_visible(), 'S uses the new broad gold-flame wing mesh')
    rig['check'](len(source_wings) == 1 and not source_wings[0].is_visible(), 'S hides original rigid feather geometry')
    rig['check'](not any('WingFlameWisp' in p.get_name() for p in wings.get_components_by_class(unreal.StaticMeshComponent)),
                 'S has no six-card flame overlay')
    rig['check'](rig['skills']().get_ascension_remaining() > 39.0, 'S keeps40second lifetime')
    rig['capture']('S_energy_unfurl')
    yield 1.1
    rig['capture']('S_energy_hold')
    yield 1.2
    rig['finish_video_clip']()
    rig['check'](all(len(c.get_components_by_class(unreal.SkeletalMeshComponent)) == 1 for c in _clones(rig)),
                 'D shadow partner remains wingless during S')
    report['S'] = {'geometry': MESH, 'material': MATERIAL, 'remaining': rig['skills']().get_ascension_remaining()}
    # Expire the real form actor now to check source restoration without a40second idle wait.
    wings.destroy_actor()
    yield .1
    restored = [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())]
    rig['check'](restored == original_materials, 'S restores every original material')
    restored_sections = [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())]
                         for lod in range(lod_count)]
    rig['check'](restored_sections == original_sections, 'S restores cloak and hood sections')
    rig['switch']('countess')
    yield .25
    rig['check'](not _clones(rig), 'D partner retires when its owner is replaced')
    report['passed'] = True
    _write(rig['OUT'], 'sparrow-energy-partner.json', report)
