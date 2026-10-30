"""Textured Ruin surface and dense blade geometry on project-owned assets.

author(output) saves only the Ruin material and its three owned solid meshes.
Source packs stay untouched; Ruin uses solid pieces and a private end erosion.
"""
import hashlib
import json
import math
from pathlib import Path

import unreal


SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve'
TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessRuinShadow'
MESH = '/Game/TopDown/Characters/Countess/FX/SM_CountessRuinClawBlade'
SHARD = '/Game/TopDown/Characters/Countess/FX/SM_CountessRuinShard'
CRATER = '/Game/TopDown/Characters/Countess/FX/SM_CountessRuinFracture'
VERSION = '5'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
INK = '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'


def _claw_mesh(output, material):
    mesh = unreal.load_asset(MESH)
    if mesh is not None and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CountessRuinClawVersion') == '2':
        return {'path': MESH, 'reused': True, 'triangles': mesh.get_num_triangles(0)}
    # Eight-sided asymmetric ridge, 32 axial segments; both ends really taper.
    # The raised spine receives lighting independently from the thin cutting edge.
    # The importer receives (X,-Y,Z), matching the already verified Q OBJ route.
    vertices, uvs, faces = [], [], []
    section = ((0., 1.5), (2.8, .8), (4., 0.), (1.8, -.65),
               (0., -1.1), (-3., -.45), (-4., 0.), (-1.7, .9))
    for step in range(33):
        u = step / 32.
        width = max(.003, math.sin(math.pi * u) ** .65 * (.55 + .45 * u))
        for side, (y, z) in enumerate(section):
            vertices.append((u * 100., y * width, z * width))
            uvs.append((u, side / 8.))
    for step in range(32):
        for side in range(8):
            a = step * 8 + side + 1
            b = step * 8 + (side + 1) % 8 + 1
            c, d = b + 8, a + 8
            faces.extend(((a, b, c), (a, c, d)))
    return _import_mesh(output, material, MESH, vertices, uvs, faces,
                        'CountessRuinClawVersion', '2', (100., 5., 8.1, 1.9, 2.8), 480, 32)


def _shard_mesh(output, material):
    mesh = unreal.load_asset(SHARD)
    if mesh is not None and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CountessRuinShardVersion') == '1':
        return {'path': SHARD, 'reused': True, 'triangles': mesh.get_num_triangles(0)}
    # A bent, chipped prism with a broad root and offset tip. Its cross-section
    # has real depth; it is neither the old ten-triangle wedge nor a flat card.
    section = ((0., 6.), (6., 3.), (8., 0.), (5., -5.),
               (0., -4.), (-7., -2.), (-6., 2.), (-2., 4.))
    rings = ((0., .48, 0., 0.), (23., .96, -2., .6),
             (52., .78, 2.8, -1.2), (79., .44, 3.3, 2.), (100., .006, 6., 3.))
    vertices, uvs, faces = [], [], []
    for step, (x, scale, cy, cz) in enumerate(rings):
        for side, (y, z) in enumerate(section):
            vertices.append((x, cy + y * scale, cz + z * scale))
            uvs.append((x / 100., side / 8.))
    for step in range(4):
        for side in range(8):
            a, b = step * 8 + side + 1, step * 8 + (side + 1) % 8 + 1
            faces.extend(((a, b, b + 8), (a, b + 8, a + 8)))
    for side in range(1, 7):
        faces.extend(((1, side + 2, side + 1), (33, 33 + side, 34 + side)))
    return _import_mesh(output, material, SHARD, vertices, uvs, faces,
                        'CountessRuinShardVersion', '1', (100., 13., 19., 9., 12.), 70, 4)


def _import_mesh(output, material, path, vertices, uvs, faces, marker, version, bounds, minimum, segments):
    name = path.rsplit('/', 1)[1]
    lines = ['o ' + name]
    lines += ['v %.7f %.7f %.7f' % (x, -y, z) for x, y, z in vertices]
    lines += ['vt %.7f %.7f' % uv for uv in uvs]
    lines += ['f ' + ' '.join('%d/%d' % (i, i) for i in face) for face in faces]
    source = output / (name + '.obj')
    source.write_text('\n'.join(lines) + '\n', encoding='ascii')
    task = unreal.AssetImportTask()
    for key, value in {'filename': str(source), 'destination_path': path.rsplit('/', 1)[0],
                       'destination_name': name, 'automated': True,
                       'replace_existing': True, 'save': False, 'factory': unreal.FbxFactory()}.items():
        task.set_editor_property(key, value)
    settings = unreal.FbxImportUI()
    for key, value in {'automated_import_should_detect_type': False,
                       'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH,
                       'import_mesh': True, 'import_materials': False, 'import_textures': False}.items():
        settings.set_editor_property(key, value)
    data = settings.get_editor_property('static_mesh_import_data')
    for key, value in {'combine_meshes': True, 'auto_generate_collision': False,
                       'convert_scene': False, 'convert_scene_unit': False,
                       'force_front_x_axis': False, 'generate_lightmap_u_vs': False}.items():
        data.set_editor_property(key, value)
    task.set_editor_property('options', settings)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError('Ruin mesh import failed: ' + str(task.get_editor_property('imported_object_paths')))
    mesh.set_editor_property('static_materials', [unreal.StaticMaterial(material_interface=material, material_slot_name='RuinBlade')])
    box = mesh.get_bounding_box()
    size = box.max - box.min
    if abs(size.x - bounds[0]) > .01 or not (bounds[1] < size.y < bounds[2]) or not (bounds[3] < size.z < bounds[4]):
        raise RuntimeError('Imported Ruin axes differ from authored geometry: ' + name + ' ' + str(size))
    triangles = mesh.get_num_triangles(0)
    if triangles < minimum:
        raise RuntimeError('Ruin mesh lost subdivisions: ' + name + ' ' + str(triangles))
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, marker, version)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Cannot save Ruin mesh ' + path)
    return {'path': path, 'segments': segments, 'triangles': triangles, 'source_obj': str(source),
            'bounds_size': [size.x, size.y, size.z]}


def _crater_mesh(output, material):
    mesh = unreal.load_asset(CRATER)
    if mesh is not None and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CountessRuinFractureVersion') == '2':
        return {'path': CRATER, 'reused': True, 'triangles': mesh.get_num_triangles(0)}
    vertices, uvs, faces = [], [], []
    # Offset compact rocks replace the broad radial wedge tops, which looked
    # like a paper fan in the actual quarter view. Each has six irregular rim
    # points and an off-centre raised ridge; the bottom stays below the floor.
    rocks = ((-70., -40., 33., 29.), (-15., -76., 35., 28.),
             (62., -47., 31., 37.), (79., 36., 29., 33.),
             (20., 76., 38., 28.), (-70., 47., 32., 36.), (-10., 3., 35., 30.))
    for i, (cx, cy, sx, sy) in enumerate(rocks):
        base = len(vertices) + 1
        rim = []
        for side in range(6):
            angle = side * math.pi / 3 + i * .41
            radius = .84 + ((i * 3 + side * 7) % 5) * .065
            rim.append((cx + math.cos(angle) * sx * radius,
                        cy + math.sin(angle) * sy * radius, 5. + (i + side * 3) % 5 * 2.5))
        for top in (False, True):
            for x, y, z in rim:
                vertices.append((x, y, z if top else -14.))
                uvs.append(((x + 140.) / 280., (y + 140.) / 280.))
        vertices.append((cx + math.sin(i * 1.9) * 8., cy + math.cos(i * .8) * 7., 31. + i % 3 * 7.))
        uvs.append(((cx + 140.) / 280., (cy + 140.) / 280.))
        peak = base + 12
        for side in range(6):
            a, b = base + side, base + (side + 1) % 6
            faces.extend(((a, b, b + 6), (a, b + 6, a + 6), (a + 6, b + 6, peak)))
        for side in range(1, 5):
            faces.append((base, base + side + 1, base + side))
    size = [max(v[a] for v in vertices) - min(v[a] for v in vertices) for a in range(3)]
    bounds = (size[0], size[1] - .1, size[1] + .1, size[2] - .1, size[2] + .1)
    return _import_mesh(output, material, CRATER, vertices, uvs, faces,
                        'CountessRuinFractureVersion', '2', bounds, 150, 7)


def _surface(material):
    lib = unreal.MaterialEditingLibrary
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessRuinSurfaceVersion') == VERSION:
        return
    alpha = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY)
    if alpha is None:
        raise RuntimeError('Existing Ruin opacity is missing')
    # V4 also stops using the clone's coverage/drift for solid fragments. Those
    # disconnected source nodes remain in this copy; the original is untouched.
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('opacity_mask_clip_value', .24)
    material.set_editor_property('two_sided', True)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for name, value in props.items():
            item.set_editor_property(name, value)
        return item

    def wire(a, channel, b, pin):
        if not lib.connect_material_expressions(a, channel, b, pin):
            raise RuntimeError('Cannot connect Ruin surface ' + pin)

    def inputs(names):
        result = []
        for name in names:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', name)
            result.append(pin)
        return result

    position = node('Subtract')
    wire(node('WorldPosition'), '', position, 'A')
    wire(node('ActorPositionWS'), '', position, 'B')
    uv = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT2,
              code='return float2(dot(Position,float3(.018,.009,.005)),dot(Position,float3(-.006,.014,.021)));')
    uv.set_editor_property('inputs', inputs(('Position',)))
    wire(position, '', uv, 'Position')
    samples = []
    for path, sx, sy in ((NOISE, .035, -.08), (INK, -.045, .025)):
        texture = unreal.load_asset(path)
        if texture is None:
            raise RuntimeError('Missing Ruin texture ' + path)
        pan = node('Panner', speed_x=sx, speed_y=sy)
        sample = node('TextureSample', texture=texture)
        wire(uv, '', pan, 'Coordinate')
        wire(pan, '', sample, 'UVs')
        samples.append(sample)
    values = (
        (samples[0], 'R', 'Noise'), (samples[1], 'R', 'Ink'),
        (node('TextureCoordinate'), '', 'UV'),
        (node('ScalarParameter', parameter_name='RuinProfile', default_value=1.), '', 'Profile'),
        (node('ScalarParameter', parameter_name='RuinEnergy', default_value=1.), '', 'Energy'),
        (node('ScalarParameter', parameter_name='RuinErode', default_value=0.), '', 'Erode'),
        (node('ScalarParameter', parameter_name='RuinPulse', default_value=0.), '', 'Pulse'))
    body = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, code='''
float n=pow(saturate((Noise-.0075)/(.5841-.0075)),.55);
float ink=pow(saturate((Ink-.0009)/(.3140-.0009)),.30);
float grain=saturate(n*.57+ink*.43);
if(Profile<.5) return lerp(float3(.026,.024,.026),float3(.075,.064,.067),grain*grain);
return lerp(float3(.023,.017,.020),float3(.115,.073,.080),grain*grain);
''')
    emission = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, code='''
float n=pow(saturate((Noise-.0075)/(.5841-.0075)),.55);
float ink=pow(saturate((Ink-.0009)/(.3140-.0009)),.30);
float grain=saturate(n*.57+ink*.43);
float vein=pow(saturate(1-abs(n-ink*.66-.15)*27),3.2);
vein*=smoothstep(.36,.64,grain);
float v=frac(UV.y);
float edgeDistance=min(abs(v-.25),abs(v-.75));
float edge=(1-smoothstep(.009,.031,edgeDistance))*smoothstep(.015,.11,UV.x);
edge*=smoothstep(.005,.08,1-UV.x)*(.65+.35*ink);
float profile0=1-step(.5,Profile);
float profile1=step(.5,Profile)*(1-step(1.5,Profile));
float profile2=step(1.5,Profile)*(1-step(2.5,Profile));
float profile3=step(2.5,Profile);
float crackStrength=.20*profile0+.44*profile1+.14*profile2;
float edgeStrength=.64*profile1+1.0*profile2;
float3 cracks=float3(.72,.012,.025)*vein*crackStrength;
float3 rim=float3(.82,.018,.030)*edge*edgeStrength;
float3 ignition=float3(1.30,.055,.030)*saturate(Pulse)*(vein*.30+edge*.20);
float3 core=float3(1.55,.042,.024)*(.25+.75*pow(grain,2))*(.40+.60*saturate(Pulse));
return ((cracks+rim+ignition)*(1-profile3)+core*profile3)*saturate(Energy);
''')
    coverage = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1, code='''
float grain=pow(saturate((Noise-.0075)/(.5841-.0075)),.55);
float field=saturate(.30+.55*(1-saturate(UV.x))+.15*grain);
return saturate((field-saturate(Erode))*16);
''')
    roughness = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                     code='return Profile<.5 ? .88 : .48;')
    metal = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1,
                code='return Profile<.5 ? 0.0 : .18;')
    for shader in (body, emission, coverage, roughness, metal):
        shader.set_editor_property('inputs', inputs(tuple(item[2] for item in values)))
        for source, channel, name in values:
            wire(source, channel, shader, name)
    connections = ((body, unreal.MaterialProperty.MP_BASE_COLOR),
                   (emission, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                   (coverage, unreal.MaterialProperty.MP_OPACITY_MASK),
                   (node('Constant3Vector', constant=unreal.LinearColor(0., 0., 0., 0.)), unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET),
                   (roughness, unreal.MaterialProperty.MP_ROUGHNESS),
                   (node('Constant', r=.42), unreal.MaterialProperty.MP_SPECULAR),
                   (metal, unreal.MaterialProperty.MP_METALLIC))
    for source, prop in connections:
        if not lib.connect_material_property(source, '', prop):
            raise RuntimeError('Cannot connect lit Ruin property ' + str(prop))
    if lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY) != alpha:
        raise RuntimeError('Disconnected source opacity changed unexpectedly')
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessRuinSurfaceVersion', VERSION)


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source_file = Path(unreal.Paths.project_content_dir()) / (SOURCE.removeprefix('/Game/') + '.uasset')
    source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
    material = unreal.load_asset(TARGET)
    if material is None:
        material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if not isinstance(material, unreal.Material):
        raise RuntimeError('Ruin shadow is not a private Material')
    material.set_editor_property('used_with_spline_meshes', True)
    _surface(material)
    errors = [str(e) for e in (unreal.MaterialEditingLibrary.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('Ruin shadow compile failed: ' + repr(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save private Ruin shadow')
    mesh = _claw_mesh(output, material)
    shard = _shard_mesh(output, material)
    crater = _crater_mesh(output, material)
    result = {'passed': True, 'saved_asset': TARGET, 'source': SOURCE,
              'source_hash_unchanged': source_hash == hashlib.sha256(source_file.read_bytes()).hexdigest(),
              'surface_version': VERSION, 'preserved_opacity_dissolve_graph': False,
              'surface': 'solid masked default-lit obsidian; sparse animated cracks, thin UV cutting edges, small core; private tip-led erosion at end, no clone coverage/drift or emissive Fresnel',
              'blend_mode': str(material.get_editor_property('blend_mode')),
              'shading_model': str(material.get_editor_property('shading_model')),
              'source_dissolve_alpha_reused_as_opacity_mask': False,
              'source_clone_nodes_disconnected_only_in_owned_copy': True,
              'mesh': mesh, 'shard_mesh': shard, 'crater_mesh': crater,
              'used_with_spline_meshes': bool(material.get_editor_property('used_with_spline_meshes'))}
    if not result['source_hash_unchanged']:
        raise RuntimeError('Unexpected source package change')
    (output / 'countess-ruin-surface.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
