"""A/V strong swept cuts with a broad short ink wake; project-owned assets only."""
import hashlib
import json
import math
import runpy
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Countess/QualityGate20261024'
MATERIAL = ROOT + '/M_CountessSweptCut'
MESH = ROOT + '/SM_CountessSweptCut'
SHADOW = ROOT + '/M_CountessStrikeShadow'
VERSION = '3'
SURFACE_VERSION = '2'
TEXTURES = ('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile',
            '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M')


def _material():
    material = unreal.load_asset(MATERIAL)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            MATERIAL.rsplit('/', 1)[1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessSweptCutVersion') == SURFACE_VERSION:
        return material
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **props):
        item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, value in props.items():
            item.set_editor_property(key, value)
        return item

    def wire(source, channel, target, pin):
        if not lib.connect_material_expressions(source, channel, target, pin):
            raise RuntimeError('Cannot connect Countess swept cut: ' + pin)

    uv = node('TextureCoordinate')
    values = [(uv, '', 'UV')]
    for index, path in enumerate(TEXTURES):
        sample = node('TextureSample', texture=unreal.load_asset(path))
        pan = node('Panner', speed_x=-.68 if index == 0 else -.30, speed_y=.08 if index == 0 else -.10)
        wire(uv, '', pan, 'Coordinate')
        wire(pan, '', sample, 'UVs')
        values.append((sample, 'R', 'Noise' if index == 0 else 'Ink'))
    for name, default in (('CutStrength', 1.), ('CutTail', 0.)):
        values.append((node('ScalarParameter', parameter_name=name, default_value=default), '', name))
    shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
float n=pow(saturate((Noise-.0075)/.5766),.55);
float ink=pow(saturate((Ink-.0009)/.3131),.38);
float grain=saturate(n*.55+ink*.45);
float tip=smoothstep(0,.06,UV.x)*smoothstep(0,.055,1-UV.x);
float tornFront=smoothstep(.23,.57,grain+sin(UV.x*31+ink*8)*.11);
float front=smoothstep(.77,.94,UV.y)*(1-smoothstep(.98,1,UV.y))*tornFront;
float leading=smoothstep(.22,.82,UV.x);
float wake=smoothstep(.025,.26,UV.y+grain*.16)*smoothstep(0,.08,1-UV.y);
float torn=smoothstep(.12,.43,grain+(UV.y-.5)*.18);
float band=pow(saturate(1-abs(n-ink*.7-.12)*15),2.0);
float tail=saturate(CutTail);
float strength=saturate(CutStrength);
float alpha=tip*wake*torn*strength*(.64+.25*grain)*lerp(1,.72,tail);
float3 body=lerp(float3(.026,.0008,.004),float3(.20,.004,.018),grain*grain);
float3 edge=float3(1.75,.014,.039)*front*(.35+.65*leading)*(.55+.45*ink);
float3 currents=float3(.84,.005,.033)*band*.28;
float3 color=(body+currents+edge*(1-tail))*lerp(.60,1.0,strength);
return float4(color,alpha);
''')
    pins = []
    for source, channel, name in values:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shader.set_editor_property('inputs', pins)
    for source, channel, name in values:
        wire(source, channel, shader, name)
    for channel, prop in (('RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR), ('A', unreal.MaterialProperty.MP_OPACITY)):
        mask = node('ComponentMask', r=channel == 'RGB', g=channel == 'RGB', b=channel == 'RGB', a=channel == 'A')
        wire(shader, '', mask, lib.get_material_expression_input_names(mask)[0])
        if not lib.connect_material_property(mask, '', prop):
            raise RuntimeError('Cannot connect swept cut output')
    errors = [str(e) for e in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('Swept cut shader errors: ' + repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessSweptCutVersion', SURFACE_VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save swept cut material')
    return material


def _shadow_material():
    material = unreal.load_asset(SHADOW)
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            SHADOW.rsplit('/', 1)[1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessStrikeShadowVersion') == VERSION:
        return material
    lib = unreal.MaterialEditingLibrary
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True, 'used_with_skeletal_mesh': True,
                       'used_with_clothing': True,
                       'dither_opacity_mask': False}.items():
        material.set_editor_property(key, value)
    graph_type = runpy.run_path(str(Path(__file__).with_name('countess_inferno_surface.py')))['_Graph']
    graph = graph_type(material)
    relative = graph.node('Subtract')
    graph.wire(graph.node('WorldPosition'), '', relative, 'A')
    graph.wire(graph.node('ObjectPositionWS'), '', relative, 'B')
    uv = graph.custom('return float2(dot(Position,float3(.011,.005,.003)),dot(Position,float3(-.003,.008,.013)));',
                      ('Position',), unreal.CustomMaterialOutputType.CMOT_FLOAT2)
    graph.wire(relative, '', uv, 'Position')
    noise, ink = graph.ink_samples(uv)
    shader = graph.custom('''
float n=pow(saturate((Noise-.0075)/.5766),.55);
float ink=pow(saturate((Ink-.0009)/.3131),.38);
float grain=saturate(n*.52+ink*.48);
float shape=.32+.68*saturate(dot(normalize(Normal),normalize(float3(.35,-.40,.84))));
float etched=pow(saturate(1-abs(n-ink*.62-.16)*12),3)*.08;
float rim=pow(saturate(Facing),2.7)*(.55+.45*grain);
float3 body=lerp(float3(.095,.002,.009),float3(.24,.005,.019),grain)*shape;
float3 ridge=float3(.25,.003,.012)*rim+float3(.24,.003,.010)*etched;
float t=saturate((Clock-Start)/max(Duration,.01));
float erode=1-smoothstep(grain*.45+.12,grain*.45+.51,t);
float alpha=(.91+.055*grain)*erode*pow(1-t,.65);
return float4((body+ridge)*max(Energy,0)*pow(1-t,.45),alpha);
''', ('Noise','Ink','Normal','Facing','Energy','Clock','Start','Duration'),
                          unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    for expression, channel, pin in (
        (noise,'R','Noise'),(ink,'R','Ink'),(graph.node('PixelNormalWS'),'','Normal'),
        (graph.node('Fresnel',exponent=1.0,base_reflect_fraction=.015),'','Facing'),
        (graph.scalar('InfernoEnergy',1.),'','Energy'),(graph.node('Time'),'','Clock'),
        (graph.scalar('DissolveStart',1000000.),'','Start'),
        (graph.scalar('DissolveDuration',.18),'','Duration')):
        graph.wire(expression,channel,shader,pin)
    graph.output(shader,unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False))
    graph.output(shader,unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))
    errors = [str(e) for e in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError('Strike shadow shader errors: ' + repr(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessStrikeShadowVersion', VERSION)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save strike shadow material')
    return material


def _mesh(output, material):
    mesh = unreal.load_asset(MESH)
    if mesh is not None and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'CountessSweptCutMeshVersion') == SURFACE_VERSION:
        return {'path': MESH, 'reused': True, 'triangles': mesh.get_num_triangles(0)}
    vertices, uvs, faces = [], [], []
    for i in range(49):
        u = i / 48
        angle = math.radians(-82 + 164 * u)
        width = 78 * max(.004, math.sin(math.pi*u)**.48) * (.73+.27*u)
        for j in range(13):
            v = j / 12
            radius = 116 - (1-v)*width
            height = 17*math.sin(angle*1.35)+25*math.sin(math.pi*u)*math.sin(math.pi*v)
            vertices.append((radius*math.cos(angle), radius*math.sin(angle), height))
            uvs.append((u,v))
    for i in range(48):
        for j in range(12):
            a=i*13+j+1
            faces.extend(((a,a+1,a+14),(a,a+14,a+13)))
    size=[max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3)]
    bounds=(size[0],size[1]-.2,size[1]+.2,size[2]-.2,size[2]+.2)
    importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    return importer(output,material,MESH,vertices,uvs,faces,'CountessSweptCutMeshVersion',SURFACE_VERSION,bounds,1148,48)


def author(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    files=[Path(unreal.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset') for p in TEXTURES]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    material=_material()
    shadow=_shadow_material()
    shadow_usage={key:bool(shadow.get_editor_property(key))
                  for key in ('used_with_skeletal_mesh','used_with_clothing')}
    if not all(shadow_usage.values()):
        raise RuntimeError('Strike shadow renderer usage incomplete: ' + repr(shadow_usage))
    mesh=_mesh(output,material)
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in before.items())
    if not unchanged:
        raise RuntimeError('Unexpected source texture change')
    result={'passed':True,'material':MATERIAL,'shadow':shadow.get_path_name(),'shadow_usage':shadow_usage,
            'mesh':mesh,'source_hash_unchanged':unchanged,'version':VERSION,'surface_version':SURFACE_VERSION,
            'scope':'A/V main swept cutting edge and short broad textured wake; no Ruin/D/S/Space asset saves'}
    (output/'countess-inferno-signature.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
