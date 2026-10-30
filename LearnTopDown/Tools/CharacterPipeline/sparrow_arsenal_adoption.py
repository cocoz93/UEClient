"""Authored D convergence / F release materials; existing E facet texture is reused."""
import hashlib
import json
from pathlib import Path
import runpy
import unreal

FOLDER='/Game/TopDown/Characters/Sparrow/Materials/Arsenal20261026'
NOISE='/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
CRYSTAL_FLOW='/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_PerlinPlasma_Noisey_Packed'
COMMON=r'''
float2 p=(UV-.5)*2.;
float aa=max(length(fwidth(p))*.6,.003);
float r=length(p); float a=atan2(p.y,p.x);
float n=Texture2DSample(Flow,FlowSampler,UV*2.3+float2(-Age*1.7,Index*.13)).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*8.+float2(-Age*4.8,Index*.31)).g;
float3 gold=float3(1.65,.48,.035), warm=float3(3.4,1.7,.36), white=float3(5.2,4.,1.8);
float fired=1.-step(10.,ShotAge), t=max(0.,ShotAge);
float open=smoothstep(.01,.13,Progress);
'''

# This packed source is marked sRGB. Restore only its authored density range;
# never change the shared texture asset or apply this to D's different source.
PLASMA_DENSITY = r'''
struct FPlasmaDensity {
 float Read(float linearValue) {
  float v=saturate(linearValue);
  return v<=.0031308 ? v*12.92 : 1.055*pow(v,1./2.4)-.055;
 }
};
FPlasmaDensity Density;
'''

RIBBON=r'''
float x=UV.x;
float bend=sin(x*3.14159)*(.24+.13*sin(Index*2.4+Age*8.))*(1.-Progress*.8);
float d=p.y-bend;
float taper=pow(saturate(sin(x*3.14159)),.7);
float width=(.09+.10*taper)*(1.-Progress*.45);
float tissue=exp(-pow(d/width,2.))*taper*(.2+n*.7+fine*.45);
float seam=exp(-pow(d/(.008+aa),2.))*taper;
float pulse=pow(saturate(cos(x*18.-Progress*36.+Index*1.4)),8.);
float fringe=exp(-pow((abs(d)-width*1.6)/(.012+aa),2.))*taper*pow(saturate(fine*1.7-.4),4.);
float sparks=pow(saturate(sin(x*67.-Progress*82.+Index*3.)),38.)*exp(-pow((abs(d)-width*2.6)/.12,2.))*taper;
float fade=open*(1.-fired*smoothstep(0.,.06,t));
float3 rgb=gold*tissue*1.5+warm*tissue*pulse+white*(seam*(.12+pulse*.7)+fringe*.35+sparks*.5);
float alpha=tissue*.75+seam*.55+fringe*.5+sparks*.7;
return float4(rgb*fade,saturate(alpha)*fade);
'''
RELEASE=r'''
float charge=exp(-r*r/.025)*pow(saturate(Progress),3.);
float iris=pow(saturate(cos(a*7.+Age*25.)),14.)*exp(-pow((r-.16)/.075,2.))*Progress;
float kick=exp(-t*30.);
float core=exp(-r*r/.022)*kick;
float rays=pow(saturate(cos(a*9.+Index*.6)),26.)*exp(-pow((r-(.10+t*3.))/ .24,2.))*exp(-t*14.);
float sheet=pow(saturate(cos(a*3.-r*9.-t*26.)),4.)*smoothstep(.08,.20,r)*(1.-smoothstep(.48+t,.85+t,r))*(.2+n*.8)*exp(-t*14.);
float shards=0.;
for(int i=0;i<22;i++) {
 float h=frac(sin(float(i)*41.72+Index)*1874.3); float ang=float(i)*2.399963;
 float2 axis=float2(cos(ang),sin(ang)); float2 q=p-axis*(.07+t*(1.8+h*3.));
 float x=dot(q,axis), y=abs(q.x*axis.y-q.y*axis.x);
 float shard=(1.-smoothstep(.8,1.,abs(x)/(.045+h*.07)+y/(.009+h*.012)));
 shards+=shard;
}
float cross=(exp(-pow(p.y/(.008+aa),2.))*exp(-p.x*p.x/.32)+exp(-pow(p.x/(.008+aa),2.))*exp(-p.y*p.y/.14))*kick;
float fade=1.-smoothstep(.10,.25,t);
float3 rgb=lerp(warm*(charge*.75+iris*.35),white*(core*1.4+cross*.65+shards*.6)+warm*rays*.8+gold*sheet*1.2,fired);
float alpha=lerp(charge*.55+iris*.30,core*.9+cross*.65+shards*.75+rays*.6+sheet*.45,fired);
return float4(rgb*open*lerp(1.,fade,fired),saturate(alpha)*open*lerp(1.,fade,fired));
'''

# F folds flowing amber crystal faces into one long, white-hot cutting lance.
# This same central surface continues on the real projectile after release.
CRYSTAL_FOLD=r'''
// UV belongs to Sparrow's real curved ShockwaveFlame mesh: V=1 is its open
// rear mouth, V=0 its forward tip. Light moves across a 3D surface, not a card.
float axial=1.-UV.y;
float theta=UV.x*6.2831853;
float noise=Texture2DSample(Flow,FlowSampler,float2(UV.x*2.0+Clock*.12,UV.y*1.8+Clock*1.3+Index*.17)).r;
float detail=Texture2DSample(Flow,FlowSampler,float2(UV.x*6.0-Clock*.35,UV.y*5.0+Clock*2.7)).g;
noise=Density.Read(noise); detail=Density.Read(detail);
float wrapped=theta-axial*5.2-Progress*5.6+Index*2.1+noise*1.15;
float stream=pow(saturate((cos(wrapped)+.18)/1.18),.90);
float broken=smoothstep(.18,.70,noise*.68+detail*.58);
float ends=smoothstep(.0,.12,UV.y)*(1.-smoothstep(.78,.99,UV.y));
float tear=smoothstep(.20,.69,noise*.85+detail*.54);
float body=stream*(.18+tear*.82)*ends;
float lip=pow(saturate(cos(wrapped+.32)),14.)*ends*(.15+detail*.85);
float fineFlow=pow(saturate(cos(theta*7.+axial*16.-Clock*16.+noise*1.2)),10.)*body;
float cavity=smoothstep(.66,.88,detail)*(1.-smoothstep(.28,.48,noise));
float edgeFade=.42+.58*(1.-smoothstep(.62,.98,Facing));
float opacity=body*(1.-cavity*.88)*edgeFade;
float depth=.28+.72*(1.-Facing);
float heat=smoothstep(.52,.91,Progress);
float3 color=float3(.38,.12,.012)+float3(2.4,1.15,.19)*pow(tear,1.4)*depth;
color+=float3(3.4,2.15,.65)*(lip*.80+fineFlow*.58);
color+=float3(4.4,3.6,1.7)*lip*heat*.26;
// Emission and coverage stay separate; low-density flow is not dimmed twice.
return float4(color,saturate(opacity*.66+lip*.19*edgeFade)*Envelope);
'''

CRYSTAL_FRAGMENT=r'''
// Interrupted light currents travel toward the compressed nucleus.
float x=UV.x;
float width=.10+.24*pow(saturate(sin(x*3.14159)),.70);
float center=.10*sin(x*5.1+Index)+.045*sin(x*13.-Clock*7.);
float y=p.y-center;
float bounds=smoothstep(.01,.16,x)*(1.-smoothstep(.80,.995,x));
float field=Texture2DSample(Flow,FlowSampler,float2(x*3.1-Clock*2.1,y*2.6+Index*.21)).g;
field=Density.Read(field);
float current=exp(-pow(y/width,2.))*bounds*pow(saturate(field*1.35-.20),1.25);
float breaks=.16+.84*pow(saturate(cos(x*13.-Clock*20.+Index)),4.);
float pulse=exp(-pow(y/max(.015,fwidth(y)*.35),2.))*bounds*saturate(.028/max(fwidth(y),.028))*breaks;
float3 rgb=float3(2.1,.91,.14)*current*1.25+float3(4.8,3.8,1.8)*pulse*.31;
float alpha=current*.61+pulse*.34;
return float4(rgb*Envelope,saturate(alpha)*Envelope);
'''

CRYSTAL_ARROW=r'''
// The same curved mesh narrows around the physical arrow and continues in flight.
float axial=1.-UV.y;
float theta=UV.x*6.2831853;
float field=Texture2DSample(Flow,FlowSampler,float2(UV.x*2.-Clock*.2,UV.y*2.6+Clock*3.1)).r;
float detail=Texture2DSample(Flow,FlowSampler,float2(UV.x*7.+Clock*.4,UV.y*7.+Clock*5.4)).g;
field=Density.Read(field); detail=Density.Read(detail);
float twist=theta*2.-axial*9.+Clock*21.+field*1.15;
float stream=pow(saturate((cos(twist)+.34)/1.34),1.6);
float ends=smoothstep(.0,.07,UV.y)*(1.-smoothstep(.73,.995,UV.y));
float tear=smoothstep(.19,.68,field*.82+detail*.52);
float body=stream*(.12+tear*.88)*ends;
float split=pow(saturate(cos(twist+.23)),16.)*ends*(.22+detail*.78);
float crest=pow(saturate(sin(axial*39.-Clock*38.+detail)),12.)*body;
float colorDepth=.25+.75*(1.-Facing);
float edgeFade=.42+.58*(1.-smoothstep(.62,.98,Facing));
float3 color=float3(.22,.065,.006)+float3(2.15,1.0,.16)*colorDepth*pow(tear,1.3)
 +float3(3.5,2.1,.65)*(split*.55+crest*.40);
return float4(color,saturate(body*.58+split*.24+crest*.13)*edgeFade*Envelope);
'''


CRYSTAL_SOLID=r'''
float grain=Texture2DSample(Flow,FlowSampler,UV*4.+float2(Clock*.2,-Clock*1.4)).r;
grain=Density.Read(grain);
float veins=pow(saturate(1.-abs(grain-.42)*11.),3.);
float edge=pow(saturate(Facing),2.4);
float hot=smoothstep(.52,.94,Progress);
float3 color=float3(.045,.012,.001)+float3(1.8,.92,.16)*(grain*.12+edge*.18)
 +float3(4.0,3.0,1.2)*(veins*.55+edge*.16)*hot;
return float4(color,Envelope*(.16+veins*.58+edge*.13));
'''

CRYSTAL_RELEASE=r'''
float launch=exp(-t*32.)+.48*exp(-pow((t-.036)/.015,2.));
float bounds=smoothstep(-.95,-.68,p.x)*(1.-smoothstep(.82,1.,p.x));
float bend=.10+.38*pow(saturate((p.x+1.)*.5),.55)+t*.7;
float pressure=exp(-pow((abs(p.y)-bend)/(.040+aa*.35),2.))*bounds;
float field=Texture2DSample(Flow,FlowSampler,float2(UV.x*2.-t*8.,p.y*1.7)).r;
float tear=Texture2DSample(Flow,FlowSampler,float2(UV.x*5.-t*12.,p.y*5.1)).g;
float envelope=exp(-t*15.);
float splitFace=exp(-pow((abs(p.y)-bend*.65)/.16,2.))*bounds*pow(saturate(field*1.4-.18),1.5)*envelope;
float spine=exp(-pow(p.y/max(.011,aa*.35),2.))*exp(-pow((p.x-.10)/.65,2.))*launch;
float front=exp(-pow((p.x-(-.35+t*9.))/.036,2.))*exp(-pow(p.y/(.22+t*.6),2.))*exp(-t*26.);
float fissures=pow(saturate(cos(p.x*19.-p.y*8.-t*60.)),16.)*splitFace*tear;
float3 rgb=float3(1.6,.58,.07)*splitFace*2.+float3(2.8,1.65,.37)*(pressure*.65*envelope+fissures*.55)+float3(5.3,4.5,2.6)*(spine*.80+front*.44);
float alpha=splitFace*.65+pressure*.42*envelope+spine*.65+front*.38;
float fade=fired*(1.-smoothstep(.11,.22,t))*Envelope;
return float4(rgb*fade,saturate(alpha)*fade);
'''

CRYSTAL_IMPACT=r'''
float age=max(Age,0.);
float pulse=exp(-age*40.)+.55*exp(-pow((age-.045)/.014,2.));
float core=exp(-pow(p.x/.14,2.)-pow(p.y/.17,2.))*pulse;
float cut=exp(-pow(p.y/(.007+aa),2.))*exp(-p.x*p.x/.60)*pulse;
float fragments=0.;
for(int i=0;i<18;i++) {
 float h=frac(sin(float(i)*41.73)*1757.9);
 float angle=(h-.5)*4.1;
 float2 axis=float2(cos(angle),sin(angle));
 float2 q=p-axis*(.045+age*(1.6+h*3.8));
 float along=dot(q,axis), lateral=q.x*axis.y-q.y*axis.x;
 float shard=exp(-pow(along/(.035+h*.075),2.)-pow(lateral/(.007+h*.012+aa),2.));
 fragments+=shard*(.35+h*.65);
}
float curve=.16+.34*pow(saturate(abs(p.x)),.7)+age*1.1;
float fissure=exp(-pow((abs(p.y)-curve)/(.010+aa),2.))*exp(-p.x*p.x/.24)*(1.-smoothstep(.04,.15,age));
float shear=pow(saturate(cos(atan2(p.y,p.x)*3.-r*14.+age*26.)),10.)*exp(-pow((r-(.16+age*2.1))/.08,2.))*(.2+n*.8);
float fade=1.-smoothstep(.10,.20,age);
float3 rgb=white*(core*1.05+cut*.90+fragments*.46)+warm*(fragments*.8+fissure*.7)+gold*shear*1.8;
float alpha=core*.9+cut*.85+fragments*.65+fissure*.50+shear*.45;
return float4(rgb*fade*Envelope,saturate(alpha)*fade*Envelope);
'''

def author(out):
    out=Path(out)
    lib=unreal.MaterialEditingLibrary
    texture=unreal.load_asset(NOISE)
    assert texture
    crystal_texture=unreal.load_asset(CRYSTAL_FLOW)
    assert crystal_texture,CRYSTAL_FLOW
    rows=[]
    for name,body in [('GatherRibbon',RIBBON),('GatherRelease',RELEASE),
                      ('GatherCrystalFold',CRYSTAL_FOLD),('GatherCrystalFragment',CRYSTAL_FRAGMENT),
                      ('GatherCrystalArrow',CRYSTAL_ARROW),('GatherCrystalSolid',CRYSTAL_SOLID),('GatherCrystalRelease',CRYSTAL_RELEASE),
                      ('GatherCrystalImpact',CRYSTAL_IMPACT)]:
        path=f'{FOLDER}/M_{name}'; code=COMMON+(PLASMA_DENSITY if name in ('GatherCrystalFold','GatherCrystalFragment','GatherCrystalArrow','GatherCrystalSolid') else '')+body
        signature=hashlib.sha256((code+(CRYSTAL_FLOW if 'GatherCrystal' in name else '')).encode()).hexdigest()
        material=unreal.load_asset(path)
        reused=bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material,'ArsenalHash')==signature)
        if not reused:
            if not material:
                folder,asset=path.rsplit('/',1)
                material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset,folder,unreal.Material,unreal.MaterialFactoryNew())
            assert material
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided',True)
            def node(kind,**props):
                obj=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
                for key,value in props.items():obj.set_editor_property(key,value)
                return obj
            shader=node('Custom',code=code,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            sources={'UV':node('TextureCoordinate'),'Flow':node('TextureObject',texture=crystal_texture if 'GatherCrystal' in name else texture)}
            if 'GatherCrystal' in name:
                sources['Clock']=node('Time')
                if name in ('GatherCrystalFold','GatherCrystalArrow','GatherCrystalSolid'):
                    sources['Facing']=node('Fresnel',exponent=1.0,base_reflect_fraction=0.0)
            for param,default in [('Age',0.),('Progress',1. if 'GatherCrystal' in name else 0.),('ShotAge',100.),('Index',0.),('Crystal',0.),('Envelope',1.)]:
                sources[param]=node('ScalarParameter',parameter_name=param,default_value=default)
            inputs=[]
            for name in sources:
                pin=unreal.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
            shader.set_editor_property('inputs',inputs)
            for name,source in sources.items():assert lib.connect_material_expressions(source,'',shader,name)
            for prop,channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
                mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
                assert lib.connect_material_expressions(shader,'',mask,'')
                assert lib.connect_material_property(mask,'',prop)
            lib.recompile_material(material)
            unreal.EditorAssetLibrary.set_metadata_tag(material,'ArsenalHash',signature)
            assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
        rows.append({'path':path,'hash':signature,'reused':reused})
    saw=runpy.run_path(str(Path(__file__).with_name('sparrow_saw_vortex_materials.py')))['author'](out)
    result={'passed':saw['passed'],'materials':rows,'saw':saw}
    (out/'arsenal-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
