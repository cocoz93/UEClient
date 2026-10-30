"""Owned sculpted bow/arrow and path-aware materials; source packs stay read-only."""
import hashlib
import json
import math
from pathlib import Path
import runpy
import unreal

ROOT='/Game/TopDown/Characters/Sparrow/FX/Harmony20261028'
FLOW='/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'

METAL=r'''
float3 normal=normalize(Normal);
float t=UV.x,v=UV.y;
float face=pow(abs(dot(normal,normalize(float3(.18,-.4,.89)))),2.3);
float fine=Texture2DSample(Flow,FlowSampler,float2(t*5.-Age*.13,v*3.)).g;
float ridge=pow(abs(cos(v*6.283185)),14.);
float carving=pow(saturate(sin(t*47.+sin(v*17.)*.8)),22.)*.11;
float3 amber=float3(.30,.095,.018),gold=float3(1.35,.72,.18),ivory=float3(2.25,1.85,.98);
float3 rgb=lerp(amber,gold,face*.72+fine*.13);
rgb=lerp(rgb,ivory,ridge*.48+face*.20)+gold*(carving+Pulse*.20);
return float4(rgb,Envelope*smoothstep(0.,.035,Open));
'''
CURRENT=r'''
float path=Start+UV.x*Span;
float y=UV.y-.5;
float coarse=Texture2DSample(Flow,FlowSampler,float2(path*1.2-Age*.92,UV.y*1.8+Seed)).r;
float detail=Texture2DSample(Flow,FlowSampler,float2(path*4.7-Age*1.7,UV.y*4.6)).g;
float warp=(coarse-.5)*.12;
float edge=pow(saturate(1.-abs(y+warp)/(.36+detail*.07)),1.7);
float fibers=pow(saturate(.5+.5*sin(y*54.+coarse*5.+path*14.)),8.);
float core=exp(-pow((y+warp*.35)/.055,2.));
float density=edge*(.22+.78*smoothstep(.06,.68,coarse*.7+detail*.45))+core*.25;
float3 rgb=lerp(float3(1.25,.32,.04),float3(3.,2.15,.78),core*.55+fibers*.25);
return float4(rgb,saturate(density*Alpha));
'''
LIGHT=r'''
float2 p=(UV-.5)*2.;float r=length(p);
float center=exp(-r*r*35.);float glow=exp(-r*r*4.3);
float a=center*.8+glow*.19;
return float4(float3(3.2,2.15,.75),a*Alpha);
'''

RELIEF=r'''
float4 art=Texture2DSample(Art,ArtSampler,UV);
float3 n=normalize(Normal);
float facet=.70+.30*abs(dot(n,normalize(float3(.22,-.4,.88))));
float l=dot(art.rgb,float3(.30,.59,.11));
float ridge=smoothstep(.40,.90,l);
float moving=Texture2DSample(Flow,FlowSampler,float2(UV.x*4.-Age*.55,UV.y*5.)).r;
float reveal=1.-smoothstep(Open-.03,Open+.04,abs(UV.x-.5)*2.);
float3 rgb=art.rgb*.82*facet+float3(1.4,.65,.10)*ridge*moving*.045;
return float4(rgb*(1.+Pulse*.10),art.a*Envelope*reveal);
'''

def material(name,code,art=None):
    path=ROOT+'/'+name;lib=unreal.MaterialEditingLibrary
    digest=hashlib.sha256((code+FLOW+(art.get_path_name() if art else '')).encode()).hexdigest()
    mat=unreal.load_asset(path)
    if mat and unreal.EditorAssetLibrary.get_metadata_tag(mat,'HarmonyMaterial')==digest:return mat
    if not mat:mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,ROOT,unreal.Material,unreal.MaterialFactoryNew())
    assert mat
    lib.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True)
    def node(kind,**props):
        n=lib.create_material_expression(mat,getattr(unreal,'MaterialExpression'+kind))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    sources={'UV':node('TextureCoordinate'),'Flow':node('TextureObject',texture=unreal.load_asset(FLOW))}
    if art:sources['Art']=node('TextureObject',texture=art)
    if 'normalize(Normal)' in code:sources['Normal']=node('PixelNormalWS')
    for k,v in (('Age',0.),('Envelope',1.),('Open',1.),('Pulse',0.)):
        sources[k]=node('ScalarParameter',parameter_name=k,default_value=v)
    for i,k in enumerate(('Start','Span','Alpha','Seed')):
        data=node('PerInstanceCustomData',data_index=i,const_default_value=1. if k=='Alpha' else 0.)
        interp=node('VertexInterpolator');assert lib.connect_material_expressions(data,'',interp,'VS')
        sources[k]=interp
    inputs=[]
    for k,n in sources.items():
        pin=unreal.CustomInput();pin.set_editor_property('input_name',k);inputs.append(pin)
    shader.set_editor_property('inputs',inputs)
    for k,n in sources.items():assert lib.connect_material_expressions(n,'',shader,k)
    for prop,rgba in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
        mask=node('ComponentMask',r=rgba[0],g=rgba[1],b=rgba[2],a=rgba[3]);lib.connect_material_expressions(shader,'',mask,'');lib.connect_material_property(mask,'',prop)
    lib.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    lib.recompile_material(mat);unreal.EditorAssetLibrary.set_metadata_tag(mat,'HarmonyMaterial',digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    return mat

class Shape:
    def __init__(self):self.v=[];self.uv=[];self.faces=[]
    def vertex(self,p,uv):self.v.append(p);self.uv.append(uv);return len(self.v)
    def loft(self,point,width,depth,steps=24,sides=8):
        rings=[]
        for i in range(steps+1):
            t=i/steps;p=point(t);a=point(max(0.,t-.001));b=point(min(1.,t+.001))
            dx,dy=b[0]-a[0],b[1]-a[1];size=max(.0001,math.hypot(dx,dy));nx,ny=-dy/size,dx/size
            ring=[]
            for j in range(sides):
                angle=j*math.tau/sides
                ring.append(self.vertex((p[0]+nx*width(t)*math.cos(angle),p[1]+ny*width(t)*math.cos(angle),p[2]+depth(t)*math.sin(angle)),(t,j/sides)))
            rings.append(ring)
        for a,b in zip(rings,rings[1:]):
            for j in range(sides):k=(j+1)%sides;self.faces.extend(((a[j],b[j],b[k]),(a[j],b[k],a[k])))
        for ring,flip in ((rings[0],True),(rings[-1],False)):
            for j in range(1,sides-1):self.faces.append((ring[0],ring[j+1],ring[j]) if flip else (ring[0],ring[j],ring[j+1]))
    def blade(self,a,b,c,width,thickness=3.,steps=24):
        def point(t):return tuple((1-t)**2*a[i]+2*(1-t)*t*b[i]+t*t*c[i] for i in range(3))
        self.loft(point,lambda t:max(.025,width*math.sin(t*math.pi)**.8*(1.-t*.25)),lambda t:max(.025,thickness*math.sin(t*math.pi)**.7),steps,6)

def bow():
    s=Shape()
    for sign in (-1.,1.):
        def point(t):return (-110.*t*t,sign*205.*t,math.sin(t*math.pi)*2.)
        s.loft(point,lambda t:3.8-t*1.1,lambda t:3.1,48,8)
        # Four large masses: inner hooked clusters and outer staggered blade fans.
        for j,(end,control,width,z) in enumerate((((-177.,208.),(-138.,157.),19.,4.),((-147.,245.),(-137.,206.),19.,9.),((-107.,263.),(-96.,218.),16.,14.),((-60.,245.),(-61.,201.),14.,8.),((-22.,220.),(-32.,181.),10.,2.))):
            a=(-52.-j*2.,sign*(148.+j*5.),z);b=(control[0],sign*control[1],z+4.);c=(end[0],sign*end[1],z)
            s.blade(a,b,c,width,3.1)
        for j,(x,y,w) in enumerate(((83.,69.,18.),(56.,42.,12.),(48.,106.,10.))):
            s.blade((-12.,sign*(58.+j*4.),6.+j*3.),(35.+j*8.,sign*(37.+j*22.),14.),(x,sign*y,5.),w,4.)
        # Carved secondary ridges remain attached to the large plate roots.
        for j in range(3):s.blade((-37.-j*7.,sign*(127.+j*17.),16.),(-63.-j*10.,sign*(160.+j*17.),19.),(-84.-j*13.,sign*(188.+j*17.),14.),3.2,1.1,16)
    s.loft(lambda t:(0.,(t-.5)*25.,0.),lambda t:3.6,lambda t:4.8,10,8)
    return s

def arrow():
    s=Shape()
    # 320cm sculpted arrow: slender shaft, split hooked head and four carved vanes.
    s.loft(lambda t:(-160.+t*287.,0.,0.),lambda t:2.0+math.sin(t*math.pi)*.65,lambda t:2.,36,8)
    s.blade((72.,0.,0.),(122.,0.,0.),(160.,0.,0.),5.,4.,24)
    for sign in (-1.,1.):
        for j in range(2):
            s.blade((60.-j*17.,sign*(2.+j*2.),j*2.),(92.-j*14.,sign*(23.-j*5.),j*2.+4.),(150.-j*27.,sign*(1.+j*8.),j*1.),8.5-j*2.,3.)
        for j in range(3):s.blade((-151.+j*12.,sign*2.,4.),(-153.+j*10.,sign*(23.-j*3.),6.),(-90.+j*8.,sign*(7.+j*2.),2.),7.-j,2.,18)
    # Two orthogonal vanes add thickness without a large flat triangular fin.
    s2=Shape()
    for sign in (-1.,1.):s2.blade((-152.,sign*2.,0.),(-153.,sign*19.,0.),(-84.,sign*4.,0.),6.,1.7,18)
    base=len(s.v);s.v.extend((x,z,y) for x,y,z in s2.v);s.uv.extend(s2.uv);s.faces.extend(tuple(i+base for i in f) for f in s2.faces)
    return s

def author(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    mats={name:material(name,code) for name,code in (('M_CarvedGold',METAL),('M_WovenCurrent',CURRENT),('M_BoundLight',LIGHT))}
    artroot=Path(__file__).resolve().parent/'ArtSources/Harmony20261028'
    for kind in ('bow','arrow'):
        task=unreal.AssetImportTask()
        for k,v in {'filename':str(artroot/(kind+'-relief.png')),'destination_path':ROOT,'destination_name':'T_'+kind.title()+'Relief','automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(k,v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture=unreal.load_asset(ROOT+'/T_'+kind.title()+'Relief');assert texture
        for k,v in {'srgb':True,'never_stream':True,'compression_no_alpha':False,'compression_settings':unreal.TextureCompressionSettings.TC_BC7,
                    'address_x':unreal.TextureAddress.TA_CLAMP,'address_y':unreal.TextureAddress.TA_CLAMP}.items():texture.set_editor_property(k,v)
        texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
        unreal.EditorAssetLibrary.save_loaded_asset(texture,False)
        mats['M_'+kind.title()+'Relief']=material('M_'+kind.title()+'Relief',RELIEF,texture)
    importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
    rows=[]
    for name,kind in (('SM_ReferenceBow','bow'),('SM_CarvedArrow','arrow')):
        data=json.loads((artroot/(kind+'-relief.json')).read_text(encoding='utf-8'));shape=Shape();shape.v=data['vertices'];shape.uv=[tuple(uv) for uv in data['uvs']];shape.faces=data['faces']
        digest=hashlib.sha256(repr((shape.v,shape.uv,shape.faces)).encode()).hexdigest();path=ROOT+'/'+name
        mesh=unreal.load_asset(path)
        if mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh,'HarmonyShape')==digest:rows.append({'path':path,'reused':True});continue
        extent=[max(p[i] for p in shape.v)-min(p[i] for p in shape.v) for i in range(3)]
        # Shared OBJ importer flips V. Wrapped sculpted UVs have no directional image to reverse.
        row=importer(output,mats['M_'+kind.title()+'Relief'],path,shape.v,shape.uv,shape.faces,'HarmonyShape',digest,(extent[0],extent[1]-.1,extent[1]+.1,extent[2]-.1,extent[2]+.1),len(shape.faces)-16,24)
        rows.append(row)
    result={'passed':True,'meshes':rows,'materials':[m.get_path_name() for m in mats.values()],'source_pack_changed':False}
    (output/'harmony-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
