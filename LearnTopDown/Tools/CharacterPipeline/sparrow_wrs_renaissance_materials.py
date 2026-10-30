"""Owned 3-D pressure, firing-rail and close-volley art; no source pack edits."""
import hashlib
import json
import math
from pathlib import Path
import runpy
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/Renaissance20261027'
TEXTURES = {
    'Flow': '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed',
    'Rays': '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays',
    'Plasma': '/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps',
}
COMMON = r'''
float x=UV.x,y=UV.y;
float aa=max(length(fwidth(UV)),.002);
float raw=Texture2DSample(Flow,FlowSampler,float2(x*3.1-Age*.7,y*2.2+Index*.173)).r;
float noise=pow(saturate(raw),.4545);
float fine=Texture2DSample(Flow,FlowSampler,float2(x*12.-Age*1.9,y*6.+Index*.277)).g;
float rays=Texture2DSample(Rays,RaysSampler,float2(frac(x*.7-Age*.9+Index*.13),y)).r;
float3 bronze=float3(.54,.13,.018), gold=float3(2.35,1.02,.13), ivory=float3(4.1,3.35,1.67);
float ends=smoothstep(0.,.055,x)*(1.-smoothstep(.91,1.,x));
float edge=smoothstep(0.,.05,y)*(1.-smoothstep(.95,1.,y));
float form=1.+Ascended*.13;
'''

SHELL = r'''
// Broad amber tissue, a narrow lip and several separated running fibers.
// Interior holes preserve the arrows and actual character silhouette.
float ridges=pow(saturate(.5+.5*cos(y*52.+sin(x*8.-Age*3.)*.7)),20.);
float lip=exp(-pow((x-.70)/(.019+aa),2.));
float second=exp(-pow((x-.42)/(.012+aa),2.));
float turbulence=smoothstep(.23,.62,noise+fine*.20);
float etched=ridges*smoothstep(.18,.74,x)*(1.-smoothstep(.84,.97,x));
float tissue=turbulence*(.16+.42*rays)*ends*edge;
float3 color=bronze*tissue*1.5+gold*(tissue*.65+etched*.40)+ivory*(lip*.44+second*.12);
float alpha=(tissue*.48+etched*.32+lip*.67+second*.20)*edge;
return float4(color*form,saturate(alpha)*Envelope);
'''

W_PRESSURE = r'''
// Separate pressure blades with axial streaks; there is no circumferential rim.
float across=abs(y-.5)*2.;
float taper=pow(saturate(sin(x*3.141593)),.65);
float tissue=smoothstep(.21,.63,noise+fine*.15)*exp(-pow(across/.63,2.))*taper;
float spine=exp(-pow((y-.46)/(.021+aa),2.))*taper;
float rim=exp(-pow((across-.70)/(.035+aa),2.))*taper;
float run=pow(saturate(.5+.5*cos(x*26.-Age*41.+Index*1.7)),6.);
float3 color=bronze*tissue+gold*(tissue*.66+rim*.35+run*tissue*.42)+ivory*spine*.47;
return float4(color,saturate(tissue*.48+spine*.63+rim*.28)*Envelope*edge);
'''

RAIL = r'''
float across=abs(y-.5)*2.;
float stroke=exp(-pow(across/.33,2.));
float ridge=exp(-pow((across-.40)/(.035+aa),2.));
float steps=pow(saturate(.5+.5*cos(x*46.-Age*42.+Index*1.7)),8.);
float running=exp(-pow((x-frac(Age*3.8+Index*.14))/.09,2.));
float core=exp(-pow(across/(.04+aa),2.));
float energy=stroke*(.26+noise*.36+rays*.30)+ridge*.24;
return float4((gold*energy+ivory*(core*.31+running*stroke*.45)+bronze*stroke*steps)*form,
 saturate(energy*.61+core*.32+running*stroke*.40)*ends*Envelope);
'''

FACET = r'''
float facing=saturate(dot(normalize(Normal),normalize(float3(.25,-.32,.91))));
float side=frac(y*4.);
float ridge=1.-smoothstep(.015,.085,min(side,1.-side));
float spine=exp(-pow((x-.68)/.018,2.));
float inner=pow(saturate(noise*.7+fine*.45),4.);
float3 body=lerp(float3(.08,.025,.006),float3(.8,.38,.07),facing);
return float4((body+gold*inner*.30+ivory*(ridge*.39+spine*.14))*form,
 saturate(.26+facing*.28+ridge*.40)*Envelope);
'''

IMPACT = r'''
float2 p=(UV-.5)*2.;
float t=saturate(Age/.25);
float core=exp(-dot(p,p)/(0.009+.025*t));
float raysum=0.,splinter=0.;
for(int i=0;i<9;i++){
 float a=i*2.399963+Index*.3;
 float2 d=float2(cos(a),sin(a));
 float along=dot(p,d),across=abs(p.x*d.y-p.y*d.x);
 float rayLength=.24+frac(sin(i*31.7)*191.3)*.40;
 float rayStroke=exp(-pow(across/(.010+aa),2.))*smoothstep(-.04,.04,along)*(1.-smoothstep(rayLength*.72,rayLength,along));
 raysum+=rayStroke;
 float2 q=p-d*(.15+t*.55);
 splinter+=1.-smoothstep(.7,1.,abs(dot(q,d))/.085+abs(q.x*d.y-q.y*d.x)/.017);
}
float dust=smoothstep(.48,.69,noise+fine*.3)*exp(-pow((length(p)-(.10+t*.5))/.12,2.));
float3 c=ivory*(core*.65+raysum*.46)+gold*(dust*.50+splinter*.60);
return float4(c,saturate(core*.68+raysum*.51+dust*.36+splinter*.65)*Envelope*(1.-smoothstep(.045,.25,Age)));
'''

STREAK = r'''
// A single straight, identical spear profile for every actual parallel shot.
float across=abs(y-.5)*2.;
float shaft=exp(-pow(across/(.026+aa),2.))*smoothstep(.03,.17,x)*(1.-smoothstep(.81,.94,x));
float edgebeam=exp(-pow((across-.065)/(.018+aa),2.))*smoothstep(.10,.27,x)*(1.-smoothstep(.73,.91,x));
float headwidth=saturate((.98-x)/.24)*.62;
float head=(1.-smoothstep(headwidth-aa,headwidth+aa,across))*smoothstep(.69,.73,x)*(1.-step(.98,x));
float hollow=1.-smoothstep(.014,.052,abs(across-headwidth*.82));
float wake=exp(-pow(across/.19,2.))*pow(saturate(x),1.2)*(1.-smoothstep(.73,.91,x));
float3 c=ivory*shaft*.37+gold*(edgebeam*.30+head*.64+head*hollow*.19+wake*.12)+bronze*head*.30;
return float4(c,saturate(shaft*.90+edgebeam*.57+head*.72+wake*.12));
'''

R_ARROW = r'''
float across=abs(y-.5)*2.;
float tail=pow(saturate(x),1.7)*exp(-pow(across/(.025+aa),2.))*(1.-smoothstep(.76,.94,x));
float tipwidth=saturate((.98-x)/.28)*.45;
float head=(1.-smoothstep(tipwidth-aa,tipwidth+aa,across))*smoothstep(.66,.72,x)*(1.-step(.98,x));
float center=exp(-pow(across/(.013+aa),2.))*smoothstep(.22,.72,x)*(1.-step(.98,x));
float rim=exp(-pow((across-tipwidth*.74)/(.018+aa),2.))*head;
float skirt=exp(-pow(across/.16,2.))*pow(saturate(x),3.)*(1.-smoothstep(.72,.90,x));
return float4(gold*(head*.42+tail*.28+skirt*.14)+ivory*(center*.38+rim*.19),
 saturate(head*.76+tail*.68+center*.45+rim*.21+skirt*.09));
'''

S_PLASMA = r'''
// Actual source flipbook, sampled through its alpha channel; the old soft
// analytic ring is absent. Three curved sheets carry separate advancing lobes.
float released=1.-step(10.,PulseAge);
float frame=clamp(6.+Progress*9.+released*max(0.,PulseAge)*110.+Index*3.,0.,62.);
float f0=floor(frame),f1=min(63.,f0+1.);
float2 local=clamp(UV+float2((noise-.5)*.025,(fine-.5)*.028),.006,.994);
float2 uv0=(float2(fmod(f0,8.),floor(f0/8.))+local)/8.;
float2 uv1=(float2(fmod(f1,8.),floor(f1/8.))+local)/8.;
float vapor=lerp(Texture2DSample(Plasma,PlasmaSampler,uv0).a,Texture2DSample(Plasma,PlasmaSampler,uv1).a,frac(frame));
float density=pow(saturate(vapor*2.6),.67);
float across=abs(y-.5)*2.;
float spine=exp(-pow((y-.47-sin(x*8.-Age*3.)*.045)/.038,2.))*density;
float hot=pow(saturate(vapor*1.8),2.8);
float edgefade=smoothstep(.0,.04,y)*(1.-smoothstep(.96,1.,y));
float3 color=lerp(bronze,gold,density)*(.45+density*.8)+ivory*(hot*.21+spine*.15);
return float4(color*form,density*.67*edgefade*ends*Envelope);
'''


def material(name, body):
    lib=unreal.MaterialEditingLibrary
    path=FOLDER+'/M_Ren'+name
    code=COMMON+body
    digest=hashlib.sha256(code.encode()).hexdigest()
    asset=unreal.load_asset(path)
    reused=bool(asset and unreal.EditorAssetLibrary.get_metadata_tag(asset,'RenaissanceHash')==digest)
    if not reused:
        if asset is None:
            asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],FOLDER,unreal.Material,unreal.MaterialFactoryNew())
        for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR,unreal.MaterialProperty.MP_OPACITY):
            lib.disconnect_material_property(asset,prop)
        lib.delete_all_material_expressions(asset)
        asset.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        asset.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        asset.set_editor_property('two_sided',True)
        def node(kind,**props):
            n=lib.create_material_expression(asset,getattr(unreal,'MaterialExpression'+kind))
            for k,v in props.items(): n.set_editor_property(k,v)
            return n
        sources={'UV':node('TextureCoordinate'),'Normal':node('PixelNormalWS')}
        for key,path in TEXTURES.items():
            texture=unreal.load_asset(path)
            if not texture: raise RuntimeError('Missing source texture '+path)
            sources[key]=node('TextureObject',texture=texture)
        for key,default in [('Age',0.),('PulseAge',100.),('Progress',0.),('Index',0.),('Ascended',0.),('Envelope',1.)]:
            sources[key]=node('ScalarParameter',parameter_name=key,default_value=default)
        shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        inputs=[]
        for key in sources:
            item=unreal.CustomInput();item.set_editor_property('input_name',key);inputs.append(item)
        shader.set_editor_property('inputs',inputs)
        for key,source in sources.items(): assert lib.connect_material_expressions(source,'',shader,key)
        for prop,channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
            mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
            assert lib.connect_material_expressions(shader,'',mask,'')
            assert lib.connect_material_property(mask,'',prop)
    errors=[str(e) for e in (lib.recompile_material(asset) or [])]
    if errors: raise RuntimeError(str(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'RenaissanceHash',digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    return asset,{'path':asset.get_path_name(),'hash':digest,'reused':reused}


def shell(kind):
    vertices,uvs,faces=[],[],[]
    longitudinal,around=18,64
    for i in range(longitudinal+1):
        u=i/longitudinal
        # W is split into two open pressure lips; S is a shallow round meniscus.
        radius=(18.+49.*math.sin(u*math.pi*.80)) if kind=='W' else (24.+58.*math.sin(u*math.pi*.70))
        axial=u*(125. if kind=='W' else 38.)
        for j in range(around+1):
            v=j/around
            theta=(v*.80+.10)*math.tau
            r=radius*(1.+.035*math.cos(theta*7.+u*4.))
            vertices.append((axial,r*math.cos(theta),r*math.sin(theta)))
            uvs.append((u,1.-v))
    stride=around+1
    for i in range(longitudinal):
        for j in range(around):
            a=i*stride+j+1
            faces.extend(((a,a+1,a+stride+1),(a,a+stride+1,a+stride)))
    return vertices,uvs,faces


def w_pressure():
    # Two opposed curved slivers. The second rotated native instance makes four;
    # the wide empty angular intervals prevent a bubble/cup silhouette.
    vertices,uvs,faces=[],[],[]
    for blade in range(2):
        base=len(vertices)
        for i in range(33):
            u=i/32.
            radius=18.+38.*math.sin(math.pi*u)**.72
            span=.06+.18*math.sin(math.pi*u)**.65
            for j in range(5):
                v=j/4.
                theta=blade*math.pi+(v-.5)*span+.28*u
                vertices.append((u*125.,radius*math.cos(theta),radius*math.sin(theta)))
                uvs.append((u,1.-v))
        for i in range(32):
            for j in range(4):
                a=base+i*5+j+1
                faces.extend(((a,a+1,a+6),(a,a+6,a+5)))
    return vertices,uvs,faces


def s_plume():
    vertices,uvs,faces=[],[],[]
    for i in range(49):
        u=i/48.
        width=26.+54.*math.sin(math.pi*u)**.72
        for j in range(9):
            v=j/8.
            vertices.append((u*200.,(v-.5)*width*2.,
                             math.sin(u*math.pi*1.35)*18.+math.cos(v*math.pi)*math.sin(u*math.pi)*13.))
            uvs.append((u,1.-v))
    for i in range(48):
        for j in range(8):
            a=i*9+j+1;faces.extend(((a,a+1,a+10),(a,a+10,a+9)))
    return vertices,uvs,faces


def rail():
    vertices,uvs,faces=[],[],[]
    for i in range(25):
        u=i/24.
        width=2.+9.*math.sin(math.pi*u)**.7
        for j in range(5):
            v=j/4.
            vertices.append((u*180.,(v-.5)*width*2.,math.sin(u*math.pi)*9.+(v-.5)**2*8.))
            uvs.append((u,1.-v))
    for i in range(24):
        for j in range(4):
            a=i*5+j+1;faces.extend(((a,a+1,a+6),(a,a+6,a+5)))
    return vertices,uvs,faces


def author(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    unreal.EditorAssetLibrary.make_directory(FOLDER)
    result={'passed':False,'materials':[],'meshes':[],'selectors':{'W':1,'R':5,'S':[11,12]},'source_textures':TEXTURES}
    try:
        # Read the actual built-in plane used by real arrows. This separates an
        # axis/UV reversal from subpixel bloom hiding the pointed head.
        plane=unreal.load_asset('/Engine/BasicShapes/Plane')
        vertices,indices,normals,uvs,tangents=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(plane,0,0)
        result['arrow_plane_uv']=[{'position':[p.x,p.y,p.z],'uv':[uv.x,uv.y]} for p,uv in zip(vertices,uvs)]
        built={}
        for key,code in [('Shell',SHELL),('WPressure',W_PRESSURE),('Rail',RAIL),('Facet',FACET),('Impact',IMPACT),('Streak',STREAK),('RArrow',R_ARROW),('SPlasma',S_PLASMA)]:
            built[key],row=material(key,code);result['materials'].append(row)
        helpers=runpy.run_path(str(Path(__file__).with_name('sparrow_f_design_materials.py')))
        mesh=helpers['_mesh'];mesh.__globals__['FOLDER']=FOLDER
        for name,geo,mat in [('SM_RenWPressure',w_pressure(),built['WPressure']),('SM_RenSLens',shell('S'),built['Shell']),('SM_RenSPlume',s_plume(),built['SPlasma']),('SM_RenRail',rail(),built['Rail']),('SM_RenFacet',helpers['_faceted_geometry'](),built['Facet'])]:
            result['meshes'].append(mesh(output,name,geo,mat))
        result['passed']=True
    finally:
        (output/'wrs-renaissance-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
