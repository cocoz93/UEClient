"""Owned W fifth-shot contact: compressed core, two tearing fronts, short sparks."""
import hashlib
import json
from pathlib import Path
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/ImpactRevision20261027'
SHADER = r'''

float2 p=(UV-.5)*2;
float r=length(p),a=atan2(p.y,p.x),t=max(Age,0);
float frame=min(61.,t*145.);
float f0=floor(frame),f1=min(63.,f0+1.);
float2 atlas0=(float2(fmod(f0,8.),floor(f0/8.))+UV)/8.;
float2 atlas1=(float2(fmod(f1,8.),floor(f1/8.))+UV)/8.;
float plasma=lerp(Texture2DSample(Plasma,PlasmaSampler,atlas0).a,Texture2DSample(Plasma,PlasmaSampler,atlas1).a,frac(frame));
float n=Texture2DSample(Flow,FlowSampler,float2(a/6.2831853+.5,r-t*.8)*2.).r;
float head=exp(-dot(p*float2(1.1,1.7),p*float2(1.1,1.7))*20.)*exp(-t*36.);
float radius=.10+pow(t,.6)*1.7;
float arc=exp(-pow((r-radius-(n-.5)*.08)/.035,2.))*(.35+n*.65)*exp(-t*8.);
float curl=0.;
for(int k=0;k<3;k++){
 float angle=k*2.094+t*8.;
 float delta=atan2(sin(a-angle),cos(a-angle));
 float spiral=.16+delta*.11+t*1.1;
 float lobe=exp(-pow((r-spiral)/.10,2.))*smoothstep(-1.2,-.6,delta)*(1.-smoothstep(.65,1.3,delta));
 curl+=lobe*(.25+plasma*.8+n*.3)*exp(-t*7.5);
}
float needle=exp(-pow(p.y/.018,2.))*(1.-smoothstep(.1,.85,abs(p.x)))*exp(-t*22.);
float mass=plasma*exp(-t*3.8)*(.3+.7*saturate(1.-r));
float fade=1.-smoothstep(.26,.44,t);
float alpha=saturate(head+curl*.6+arc*.65+needle*.6+mass*.45)*fade;
float hot=saturate(head+needle*.7+plasma*.45);
float3 color=lerp(float3(1.1,.28,.012),float3(6.5,3.1,.35),saturate(n*.55+mass));
color=lerp(color,float3(16,11,3.5),hot);
return float4(color,alpha);

'''

def author(out):
    lib=unreal.MaterialEditingLibrary
    path=FOLDER+'/M_WFinisherImpact'
    digest=hashlib.sha256(SHADER.encode()).hexdigest()
    mat=unreal.load_asset(path)
    reused=bool(mat and unreal.EditorAssetLibrary.get_metadata_tag(mat,'ImpactRevisionHash')==digest)
    if not reused:
        if not mat:
            mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_WFinisherImpact',FOLDER,unreal.Material,unreal.MaterialFactoryNew())
        lib.disconnect_material_property(mat,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        lib.disconnect_material_property(mat,unreal.MaterialProperty.MP_OPACITY)
        lib.delete_all_material_expressions(mat)
        mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided',True)
        def node(kind,**props):
            item=lib.create_material_expression(mat,getattr(unreal,'MaterialExpression'+kind))
            for k,v in props.items(): item.set_editor_property(k,v)
            return item
        sources={'UV':node('TextureCoordinate'),'Age':node('ScalarParameter',parameter_name='Age',default_value=0.),
                 'Flow':node('TextureObject',texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Wind_Blur')),
                 'Plasma':node('TextureObject',texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps'))}
        custom=node('Custom',code=SHADER,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        pins=[]
        for name in sources:
            pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
        custom.set_editor_property('inputs',pins)
        for name,source in sources.items(): assert lib.connect_material_expressions(source,'',custom,name)
        for prop,channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
            mask=node('ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
            assert lib.connect_material_expressions(custom,'',mask,'')
            assert lib.connect_material_property(mask,'',prop)
    errors=[str(x) for x in (lib.recompile_material(mat) or [])]
    assert not errors,errors
    unreal.EditorAssetLibrary.set_metadata_tag(mat,'ImpactRevisionHash',digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
    result={'passed':True,'material':path,'reused':reused,'compile_errors':errors}
    (Path(out)/'w-finisher-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
