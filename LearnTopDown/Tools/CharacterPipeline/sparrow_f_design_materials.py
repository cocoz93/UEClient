"""F designs with real faceted / helical geometry.

author(output) creates only FDesign20261027 assets. Native gameplay remains
owned by SparrowArrow; these meshes have no generated collision. The legacy
F material family is untouched. Native code selects the user's adopted F4.
"""
import hashlib
import json
import math
from pathlib import Path

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/FX/FDesign20261027'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
RAYS = '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays'
FLOW_ART = FOLDER + '/T_FDesignGoldenFlow'


def _flow_art():
    source = Path(unreal.Paths.project_dir()).resolve() / 'Tools/CharacterPipeline/Art/FDesign20261027/GoldFlow.png'
    if not source.is_file():
        raise RuntimeError('F authored flow image is required: ' + str(source))
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    texture = unreal.load_asset(FLOW_ART)
    reused = bool(texture and unreal.EditorAssetLibrary.get_metadata_tag(texture, 'FDesignImageHash') == digest)
    if not reused:
        task = unreal.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': FOLDER,
                           'destination_name': 'T_FDesignGoldenFlow', 'automated': True,
                           'replace_existing': True, 'save': False}.items():
            task.set_editor_property(key, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = unreal.load_asset(FLOW_ART)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError('Cannot import F RGBA flow texture')
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
    texture.set_editor_property('compression_no_alpha', False)
    # Preserve the authored PNG. UE stretches NPOT source dimensions internally
    # so the fine strands receive a regular mip chain at the gameplay camera.
    stretch = getattr(unreal.TexturePowerOfTwoSetting, 'STRETCH_TO_POWER_OF_TWO', None)
    if stretch is not None:
        texture.set_editor_property('power_of_two_mode', stretch)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    texture.set_editor_property('filter', unreal.TextureFilter.TF_TRILINEAR)
    unreal.EditorAssetLibrary.set_metadata_tag(texture, 'FDesignImageHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
    return texture, {'path': FLOW_ART, 'source': str(source), 'hash': digest, 'reused': reused,
                     'channels': 'authored RGB emission and A coverage, no luminance key', 'srgb': True,
                     'mip_sampling': 'UE stretch-to-POT with trilinear mips' if stretch is not None else 'UE texture-group mip default'}

COMMON = r'''
float x=UV.x;
float n=Texture2DSample(Flow,FlowSampler,float2(x*3.2-Age*.72,UV.y*1.7+Index*.137)).r;
float fine=Texture2DSample(Flow,FlowSampler,float2(x*14.-Age*2.7,UV.y*5.+Index*.217)).g;
float3 packed=Texture2DSample(Rays,RaysSampler,float2(frac(x*.82-Age*.44+Index*.17),UV.y)).rgb;
float3 bronze=float3(.82,.19,.025), gold=float3(2.65,1.15,.16), ivory=float3(4.6,3.65,1.65);
float form=1.+Ascended*.10;
'''

FACET = r'''
if (Refinement > .5) {
    float facet=frac(UV.y*8.);
    float seam=1.-smoothstep(.018,.095,min(facet,1.-facet));
    float l=saturate(dot(normalize(SurfaceNormal),normalize(float3(.26,-.37,.88))));
    float sweep=pow(saturate(.5+.5*sin(x*9.-Age*6.+Index*.63)),18.);
    float grain=pow(saturate(n*.5+fine*.5),2.2);
    float3 crystal=lerp(float3(.045,.035,.018),float3(.46,.27,.07),l);
    crystal+=float3(1.9,1.24,.39)*grain*.44;
    crystal+=float3(2.0,1.50,.56)*seam*(.18+l*.35+sweep*.45);
    float inside=exp(-pow((x-.65)/.20,2.))*grain;
    return float4(crystal+gold*inside*.22,(.76+seam*.22)*Envelope);
}
// Signed light leaves a genuinely dark facet. abs(N.L) made every face yellow.
float light=saturate(dot(normalize(SurfaceNormal),normalize(float3(.26,-.37,.88))));
float side=frac(UV.y*4.);
float edge=1.-smoothstep(.012,.075,min(side,1.-side));
float face=floor(min(UV.y,.9999)*4.);
float facetLight=(face==0.?1.:face==1.?.12:face==2.?.42:.06);
float inner=pow(saturate(n*.65+fine*.35),3.);
float3 glass=lerp(float3(.045,.023,.009),float3(.53,.30,.10),facetLight)*(.4+light*.6);
float3 color=glass+float3(1.8,1.18,.43)*inner*.40+float3(4.2,3.2,1.55)*edge*(.35+light*.65);
// Broad amber planes and narrow white-gold ridges, not a uniformly luminous leaf.
return float4(color*form,saturate(.38+facetLight*.27+edge*.55)*Envelope);
'''

RIBBON = r'''
// The new artwork is the visible material, not an optional noise modifier.
// UV flow follows the physical helical strip. Only a small field perturbation
// remains; no analytic centre wire or constant-width filled ribbon is added.
float2 artUV=float2(frac(x*.70-Age*.42+Index*.217),UV.y);
artUV+=float2((n-.5)*.016,(fine-.5)*.035);
float4 art=Texture2DSampleLevel(FlowArt,FlowArtSampler,artUV,1.5);
float ends=smoothstep(.0,.045,x)*(1.-smoothstep(.94,1.,x));
float sideFade=smoothstep(.0,.065,UV.y)*(1.-smoothstep(.935,1.,UV.y));
float raw=pow(saturate(n),.4545);
float density=art.a*ends*sideFade*smoothstep(.22,.56,raw);
float intensity=dot(art.rgb,float3(.3,.55,.15));
float3 color=art.rgb*1.25+float3(1.8,.85,.22)*pow(saturate(intensity),5.);
float fibres=pow(saturate(.5+.5*cos(UV.y*47.+n*3.+x*9.-Age*7.)),6.);
float refined=saturate(density*(.60+fibres*.70));
color=lerp(color,color*.72+float3(2.9,1.65,.35)*fibres*density*.34,Refinement);
return float4(color,lerp(density,refined,Refinement)*.68*Envelope);
'''

FILAMENT = r'''
float2 artUV=float2(frac(x*1.12-Age*1.20+Index*.217),.08+UV.y*.84);
artUV+=float2((n-.5)*.009,(fine-.5)*.016);
float4 art=Texture2DSample(FlowArt,FlowArtSampler,artUV);
float ends=smoothstep(.0,.055,x)*(1.-smoothstep(.90,1.,x));
float sideFade=smoothstep(.0,.06,UV.y)*(1.-smoothstep(.94,1.,UV.y));
float thread=exp(-pow((UV.y-.5)/.032,2.));
return float4(float3(3.4,1.7,.47)*form,thread*(.25+.75*art.a)*ends*Envelope*lerp(1.,.28,Refinement));
'''

FEATHER = r'''
float y=abs(UV.y-.5)*2.;
float width=pow(saturate(sin(x*3.141593)),.65);
float profile=1.-smoothstep(width*.72,width,y);
float spine=exp(-y*65.);
float barbs=pow(saturate(.5+.5*cos(x*67.-y*13.)),5.);
float fineBars=pow(saturate(.5+.5*cos(x*125.+y*11.)),12.);
float glow=profile*(.12+barbs*.78+fineBars*.18)+spine;
float3 col=float3(.18,.055,.008)+float3(2.4,1.35,.30)*saturate(glow);
return float4(col,profile*saturate(.08+barbs*.65+spine)*Envelope);
'''

CORE = r'''
float light=.30+.70*abs(dot(normalize(SurfaceNormal),normalize(float3(.15,-.32,.94))));
float seam=pow(saturate(cos(UV.y*37.7)),22.);
float head=smoothstep(.78,.96,x);
float3 color=lerp(bronze,gold,.35+light*.55)+ivory*(seam*.22+head*.18);
return float4(color*form,saturate(.62+light*.22+head*.12)*Envelope);
'''


def _material(name, body, textures):
    lib = unreal.MaterialEditingLibrary
    path = FOLDER + '/M_FDesign' + name
    code = COMMON + body
    digest = hashlib.sha256((code + NOISE + RAYS + FLOW_ART).encode()).hexdigest()
    material = unreal.load_asset(path)
    reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'FDesignHash') == digest)
    if not reused:
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                path.rsplit('/', 1)[1], FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        if material is None:
            raise RuntimeError('Cannot create ' + path)
        for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET):
            lib.disconnect_material_property(material, prop)
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)

        def node(kind, **props):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for key, value in props.items():
                item.set_editor_property(key, value)
            return item

        shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=textures[0]),
                   'Rays': node('TextureObject', texture=textures[1]), 'FlowArt': node('TextureObject', texture=textures[2]),
                   'SurfaceNormal': node('PixelNormalWS')}
        for key, default in [('Age', 0.), ('Progress', 0.), ('Index', 0.), ('Ascended', 0.), ('Envelope', 1.), ('Refinement', 0.)]:
            sources[key] = node('ScalarParameter', parameter_name=key, default_value=default)
        inputs = []
        for key in sources:
            entry = unreal.CustomInput()
            entry.set_editor_property('input_name', key)
            inputs.append(entry)
        shader.set_editor_property('inputs', inputs)
        for key, source in sources.items():
            if not lib.connect_material_expressions(source, '', shader, key):
                raise RuntimeError('Cannot connect ' + key)
        for prop, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
            mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        if name in ('Ribbon', 'Filament'):
            motion = node('Custom', code='return Normal * sin(UV.x*26.+Age*7.+Index*1.7) * sin(UV.y*3.141593) * '+('4.5' if name == 'Ribbon' else '1.3')+';', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
            motion_sources = {key:sources[key] for key in ('UV','Age','Index')}
            motion_sources['Normal'] = node('VertexNormalWS')
            motion_inputs=[]
            for key in motion_sources:
                entry=unreal.CustomInput();entry.set_editor_property('input_name',key);motion_inputs.append(entry)
            motion.set_editor_property('inputs',motion_inputs)
            for key,source in motion_sources.items():
                assert lib.connect_material_expressions(source,'',motion,key)
            assert lib.connect_material_property(motion,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    errors = [str(item) for item in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError(path + ': ' + '\n'.join(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'FDesignHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material, {'path': path, 'reused': reused, 'hash': digest, 'compile_errors': errors}


def _faceted_geometry(needle=False):
    # X is flight direction. Both ends taper in geometry, not a painted polygon.
    section = ((0., 14.), (13., 0.), (0., -11.), (-10., 0.))
    rings = ((0., .003), (43., 1.), (100., .003))
    if needle:
        section = ((0., 1.5), (2.7, .8), (3.4, -.3), (0., -1.1), (-3.4, -.3), (-2.7, .8))
        rings = ((0., .02), (10., .45), (69., .40), (74., 1.), (91., .50), (100., .002))
    vertices, uvs, faces = [], [], []
    # Duplicate the face boundary so the importer preserves a crisp hard ridge.
    for side in range(len(section)):
        base = len(vertices) + 1
        for x, scale in rings:
            for edge in (side, (side + 1) % len(section)):
                y, z = section[edge]
                vertices.append((x, y * scale, z * scale))
            uvs.extend(((x / 100., side / len(section)), (x / 100., (side + 1) / len(section))))
        for step in range(len(rings) - 1):
            a = base + step * 2
            faces.extend(((a, a + 1, a + 3), (a, a + 3, a + 2)))
    return vertices, uvs, faces


def _crystal_geometry():
    vertices, uvs, faces = [], [], []
    rings=((0.,.025),(20.,.72),(68.,1.),(83.,.57),(100.,.008))
    for side in range(8):
        base=len(vertices)+1
        for x,radius in rings:
            for edge in (side,side+1):
                angle=edge*math.tau/8.
                vertices.append((x,math.cos(angle)*8.5*radius,math.sin(angle)*10.*radius))
                uvs.append((x/100.,edge/8.))
        for step in range(len(rings)-1):
            a=base+step*2
            faces.extend(((a,a+1,a+3),(a,a+3,a+2)))
    return vertices,uvs,faces


def _helix_geometry():
    # One physically open ribbon: 1.12 turns along X, with no cap, fan, shell,
    # circular plane or cone outline. Three instances form separate currents.
    vertices, uvs, faces = [], [], []
    segments, cross_steps = 80, 4
    for step in range(segments + 1):
        u = step / segments
        theta = u * math.tau * 1.05
        radius = 4. + 36. * (1. - u) ** .72
        center = (100. * u, math.cos(theta) * radius, math.sin(theta) * radius)
        taper = max(.015, math.sin(math.pi * u) ** .55)
        width = (19. + 5.5 * math.sin(u * math.pi * 3.)) * taper
        # Radial + axial cross direction gives the strip a visible twisted lip.
        for cross in range(cross_steps + 1):
            v = cross / cross_steps
            offset = (v - .5) * 2. * width
            vertices.append((center[0] + offset * .42,
                             center[1] + math.cos(theta) * offset,
                             center[2] + math.sin(theta) * offset))
            uvs.append((u, v))
    stride = cross_steps + 1
    for step in range(segments):
        for cross in range(cross_steps):
            a = step * stride + cross + 1
            faces.extend(((a, a + 1, a + stride + 1), (a, a + stride + 1, a + stride)))
    return vertices, uvs, faces


def _feather_geometry():
    vertices, uvs, faces = [], [], []
    for step in range(17):
        u = step / 16.
        for cross in range(5):
            v = cross / 4.
            vertices.append((u*100., (v-.5)*40., math.sin(u*math.pi)*7. + (v-.5)**2*18.))
            uvs.append((u,v))
    for step in range(16):
        for cross in range(4):
            a=step*5+cross+1
            faces.extend(((a,a+1,a+6),(a,a+6,a+5)))
    return vertices,uvs,faces


def _mesh(output, name, geometry, material):
    vertices, uvs, faces = geometry
    # Existing Countess importer verifies this X,-Y,Z OBJ convention in game.
    lines = ['o ' + name, 's off']
    lines += ['v %.7f %.7f %.7f' % (x, -y, z) for x, y, z in vertices]
    lines += ['vt %.7f %.7f' % uv for uv in uvs]
    lines += ['f ' + ' '.join('%d/%d' % (i, i) for i in face) for face in faces]
    obj = '\n'.join(lines) + '\n'
    digest = hashlib.sha256(obj.encode()).hexdigest()
    path = FOLDER + '/' + name
    mesh = unreal.load_asset(path)
    reused = bool(mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'FDesignMeshHash') == digest)
    source = output / (name + '.obj')
    if not reused:
        source.write_text(obj, encoding='ascii')
        task = unreal.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': FOLDER, 'destination_name': name,
                           'automated': True, 'replace_existing': True, 'save': False,
                           'factory': unreal.FbxFactory()}.items():
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
        raise RuntimeError('F design mesh import failed: ' + path)
    mesh.set_editor_property('static_materials', [unreal.StaticMaterial(material_interface=material, material_slot_name='Energy')])
    box = mesh.get_bounding_box()
    size = box.max - box.min
    expected = [max(v[axis] for v in vertices) - min(v[axis] for v in vertices) for axis in range(3)]
    actual = [size.x, size.y, size.z]
    if any(abs(a - b) > .05 for a, b in zip(actual, expected)):
        raise RuntimeError('F design imported axes/bounds differ: ' + name + ' ' + str(actual) + ' expected ' + str(expected))
    if mesh.get_num_triangles(0) < len(faces) - 4:
        raise RuntimeError('F design lost geometry: ' + name)
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'FDesignMeshHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    return {'path': path, 'reused': reused, 'hash': digest, 'triangles': mesh.get_num_triangles(0),
            'bounds_size': actual, 'source_obj': str(source), 'generated_collision': False}


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    unreal.EditorAssetLibrary.make_directory(FOLDER)
    textures = [unreal.load_asset(NOISE), unreal.load_asset(RAYS)]
    if not all(textures):
        raise RuntimeError('F design project textures unavailable')
    result = {'passed': False, 'materials': [], 'meshes': [], 'styles': [1, 2, 3, 4], 'installed_style': 0,
              'gameplay_changed': False, 'texture_paths': [NOISE, RAYS, FLOW_ART]}
    try:
        flow_art, result['flow_art'] = _flow_art()
        textures.append(flow_art)
        built = {}
        for name, body in [('Facet', FACET), ('Ribbon', RIBBON), ('Filament', FILAMENT), ('Core', CORE), ('Feather', FEATHER)]:
            built[name], row = _material(name, body, textures)
            result['materials'].append(row)
        for name, geometry, material in [('SM_FDesignCrystal', _crystal_geometry(), built['Facet']),
                                         ('SM_FDesignFacet', _faceted_geometry(), built['Facet']),
                                         ('SM_FDesignNeedle', _faceted_geometry(True), built['Core']),
                                         ('SM_FDesignHelix', _helix_geometry(), built['Ribbon']),
                                         ('SM_FDesignFeather', _feather_geometry(), built['Feather'])]:
            result['meshes'].append(_mesh(output, name, geometry, material))
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (output / 'f-design-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
