"""Own E/R fracture, rising slash and obsidian surfaces; no shared asset saves."""
from pathlib import Path
import hashlib
import json
import math
import runpy
import unreal

ROOT = '/Game/TopDown/Characters/Countess/QualityGate20261024'
VERSION = '3'
SOURCES = ('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile',
           '/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M')


def make(name, kind):
    lib = unreal.MaterialEditingLibrary
    material_version = VERSION if kind == 'plume' else '2'
    path = ROOT + '/' + name
    mat = unreal.load_asset(path)
    if mat is None:
        mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if unreal.EditorAssetLibrary.get_metadata_tag(mat, 'RuptureVolumeVersion') == material_version:
        return mat
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if kind == 'spike' else unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT if kind == 'spike' else unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('used_with_spline_meshes', kind == 'cut')
    mat.set_editor_property('opacity_mask_clip_value', .18)
    def node(typ, **props):
        n = lib.create_material_expression(mat, getattr(unreal, 'MaterialExpression'+typ))
        for k,v in props.items(): n.set_editor_property(k,v)
        return n
    def wire(a,p,b,q):
        if not lib.connect_material_expressions(a,p,b,q): raise RuntimeError('Material connection '+q)
    uv = node('TextureCoordinate')
    values = [(uv,'','UV'),(node('Fresnel',exponent=1.,base_reflect_fraction=0.),'','Facing')]
    for i,path in enumerate(SOURCES):
        pan = node('Panner',speed_x=.06 if i==0 else -.04,speed_y=-.26 if i==0 else .12)
        wire(uv,'',pan,'Coordinate')
        tex = node('TextureSample',texture=unreal.load_asset(path))
        wire(pan,'',tex,'UVs')
        values.append((tex,'R','Noise' if i==0 else 'Ink'))
    for n,v in [('RuinErode',0.),('RuinPulse',0.),('CloneOpacity',1.),('ReferenceAge',0.)]:
        values.append((node('ScalarParameter',parameter_name=n,default_value=v),'',n))
    common='''
float n=pow(saturate((Noise-.0075)/.5766),.62);
float ink=pow(saturate((Ink-.0009)/.3131),.42);
float grain=saturate(n*.58+ink*.42);
float ridge=pow(saturate(1-abs(n-ink*.70-.10)*13),3.0);
float life=1-smoothstep(grain*.35+.10,grain*.35+.52,saturate(RuinErode));
'''
    bodies = {
    'ground': '''
float2 p=(UV-.5)*2;
float rad=length(p*float2(.92,1));
float edge=1-smoothstep(.47,.96,rad+(grain-.5)*.31);
float cracks=ridge*smoothstep(.24,.54,grain);
float core=exp(-dot(p,p)*11)*(.25+RuinPulse*.30);
float opacity=edge*(.31+.46*grain)*life*CloneOpacity;
float3 c=float3(.015,.001,.003)+float3(1.5,.018,.032)*(cracks*.68+core);
return float4(c,opacity);
''',
    'spike': '''
float spine=pow(abs(cos(UV.y*6.283185)),10);
float taper=smoothstep(.18,.90,UV.x);
float fractures=ridge*smoothstep(.25,.58,grain);
float3 c=float3(1.45,.015,.030)*(fractures*.65+spine*taper*.62);
c+=float3(.7,.010,.025)*RuinPulse*taper;
float alpha=life*CloneOpacity*(.70+.30*grain);
return float4(c,alpha);
''',
    'cut': '''
float along=pow(saturate(sin(UV.x*3.141593)),.35);
float blade=pow(abs(sin(UV.y*6.283185)),9);
float ribbons=smoothstep(.28,.66,grain);
float3 c=float3(.025,.0004,.003)+float3(1.55,.012,.027)*(blade*.65+ridge*.30);
c+=float3(.22,.003,.009)*ribbons;
float alpha=along*CloneOpacity*life*(.12+.82*ribbons);
return float4(c,alpha);
''',
    'plume': '''
float h=UV.y;
float sides=smoothstep(0,.07,UV.x)*smoothstep(0,.07,1-UV.x);
float top=smoothstep(.35,.88,h);
float detail=lerp(.80+.20*grain,smoothstep(.15,.53,grain),top);
float erosion=1-smoothstep(.15+(1-h)*.45,.48+(1-h)*.45,RuinErode);
float alpha=sides*detail*erosion*CloneOpacity*(.72-.20*top);
float redPatch=smoothstep(.47,.73,grain);
float tip=smoothstep(.82,.99,h)*detail;
float3 c=float3(.025,.0005,.003)+float3(.48,.005,.022)*redPatch;
c+=float3(.88,.009,.031)*(ridge*.26+tip*.45);
return float4(c,alpha);
''',
    'hand': '''
float rim=pow(saturate(Facing),2.0);
float3 c=float3(.035,.001,.005)+float3(.46,.003,.016)*(rim*.65+ridge*.28+grain*grain*.12);
float alpha=(.56+.33*grain)*life*CloneOpacity;
return float4(c,alpha);
'''}
    shader = node('Custom',code=common+bodies[kind],output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for _,_,name in values:
        pin=unreal.CustomInput(); pin.set_editor_property('input_name',name); pins.append(pin)
    shader.set_editor_property('inputs',pins)
    for a,p,name in values: wire(a,p,shader,name)
    for alpha,prop in [(False,unreal.MaterialProperty.MP_EMISSIVE_COLOR),(True,unreal.MaterialProperty.MP_OPACITY_MASK if kind=='spike' else unreal.MaterialProperty.MP_OPACITY)]:
        mask=node('ComponentMask',r=not alpha,g=not alpha,b=not alpha,a=alpha)
        wire(shader,'',mask,lib.get_material_expression_input_names(mask)[0])
        lib.connect_material_property(mask,'',prop)
    if kind=='spike':
        base=node('Constant3Vector',constant=unreal.LinearColor(.045,.012,.020,1))
        lib.connect_material_property(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
        rough=node('Constant',r=.86); lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
        spec=node('Constant',r=.12); lib.connect_material_property(spec,'',unreal.MaterialProperty.MP_SPECULAR)
    errors=lib.recompile_material(mat) or []
    if errors: raise RuntimeError(str(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(mat,'RuptureVolumeVersion',material_version)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat,False): raise RuntimeError('Save '+name)
    return mat


def crest_mesh(output, material):
    path=ROOT+'/SM_CountessRuptureCrest'
    mesh=unreal.load_asset(path)
    if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'CountessCrestVersion')=='1':
        return {'path':path,'reused':True,'triangles':mesh.get_num_triangles(0)}
    vertices,uvs,faces=[],[],[]
    # Three irregular peaks on an open, twisted sheet: there is no closed rim.
    for j in range(33):
        h=j/32
        for i in range(33):
            u=i/32
            s=u*2-1
            width=55-30*math.sin(h*math.pi)+25*h*h
            crest=.69+.22*math.sin(u*math.pi*5+.3)+.09*math.sin(u*math.pi*11)
            x=s*width+19*h*h
            y=18*math.sin(s*math.pi)*math.sin(h*math.pi)+23*h*h*math.cos(u*math.pi*3)
            z=170*h*(1-h*.25+h*.25*crest)+h**4*(crest-.7)*75
            vertices.append((x,y,z)); uvs.append((u,h))
    for j in range(32):
        for i in range(32):
            a=j*33+i+1
            faces.extend(((a,a+1,a+34),(a,a+34,a+33)))
    size=[max(v[k] for v in vertices)-min(v[k] for v in vertices) for k in range(3)]
    importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    return importer(Path(output),material,path,vertices,uvs,faces,'CountessCrestVersion','1',
                    (size[0],size[1]-.2,size[1]+.2,size[2]-.2,size[2]+.2),2040,32)


def author(output):
    files=[Path(unreal.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset') for p in SOURCES]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    materials=[make('M_CountessFractureField','ground'),make('M_CountessBloodObsidian','spike'),make('M_CountessRisingCut','cut'),make('M_CountessRupturePlume','plume'),make('M_CountessDemonPalm','hand')]
    crest=crest_mesh(output,materials[3])
    unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    if not unchanged: raise RuntimeError('Source texture changed')
    result={'passed':True,'version':VERSION,'source_hash_unchanged':unchanged,'materials':[m.get_path_name() for m in materials],'crest_mesh':crest}
    (Path(output)/'countess-rupture-volume.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
