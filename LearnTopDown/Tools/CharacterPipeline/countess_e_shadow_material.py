"""E-private clone dissolve; retain the accepted Q clone's color and Fresnel graph."""
import json
from pathlib import Path
import unreal

SOURCE='/Game/TopDown/Characters/Countess/Materials/M_CountessSkillShadowCloneDetailed'
TARGET='/Game/TopDown/Characters/Countess/Materials/M_CountessEShadowDissolve'


def author(output):
    lib=unreal.MaterialEditingLibrary
    material=unreal.load_asset(TARGET)
    if material is None:material=unreal.EditorAssetLibrary.duplicate_asset(SOURCE,TARGET)
    assert material is not None
    # Reuse a completed private graph on later runs, rather than wrapping opacity twice.
    version=unreal.EditorAssetLibrary.get_metadata_tag(material,'CountessEDissolveVersion')
    if version=='2':
        return {'asset':TARGET,'reused':True}
    if version=='1':
        expressions=lib.get_material_expressions(material)
        shader=next(n for n in expressions if n.get_class().get_name()=='MaterialExpressionCustom')
        shader.set_editor_property('code',shader.get_editor_property('code').replace('*28,opacity','*8,opacity'))
        alpha=next(n for n in expressions if n.get_class().get_name()=='MaterialExpressionComponentMask' and n.get_editor_property('a'))
        _darken_dissolve(material,alpha)
        lib.recompile_material(material)
        unreal.EditorAssetLibrary.set_metadata_tag(material,'CountessEDissolveVersion','2')
        assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
        result={'asset':TARGET,'passed':True,'fade_seconds':.45,'fragment_drift_scale_cm':8,'darkens_during_dissolve':True}
        (Path(output)/'shadow-dissolve-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        return result
    original=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_OPACITY)
    original_output=lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_OPACITY)
    assert original is not None
    def node(kind,**props):
        item=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for k,v in props.items():item.set_editor_property(k,v)
        return item
    uv=node('TextureCoordinate',u_tiling=5.0,v_tiling=5.0)
    pan=node('Panner',speed_x=.12,speed_y=.2)
    assert lib.connect_material_expressions(uv,'',pan,'Coordinate')
    texture=node('TextureSample',texture=unreal.load_asset('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_TilingNoise12'))
    assert lib.connect_material_expressions(pan,'',texture,'UVs')
    custom=node('Custom',code='''
float t=saturate((Clock-Start)/max(Duration,0.01));
float breakup=1-smoothstep(Noise*.6+.08,Noise*.6+.30,t);
float opacity=breakup*pow(1-t,.6);
float3 drift=float3(sin(UV.y*31+Noise*13),cos(UV.x*27+Noise*9),.8+Noise);
return float4(drift*pow(t,1.2)*8,opacity);
''',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for name in ('UV','Noise','Clock','Start','Duration'):
        pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for expression,pin,source_output in [(uv,'UV',''),(texture,'Noise','R'),(node('Time'),'Clock',''),
                (node('ScalarParameter',parameter_name='DissolveStart',default_value=1000000.0),'Start',''),
                (node('ScalarParameter',parameter_name='DissolveDuration',default_value=.45),'Duration','')]:
        assert lib.connect_material_expressions(expression,source_output,custom,pin)
    alpha=node('ComponentMask',r=False,g=False,b=False,a=True)
    drift=node('ComponentMask',r=True,g=True,b=True,a=False)
    assert lib.connect_material_expressions(custom,'',alpha,lib.get_material_expression_input_names(alpha)[0])
    assert lib.connect_material_expressions(custom,'',drift,lib.get_material_expression_input_names(drift)[0])
    multiply=node('Multiply')
    assert lib.connect_material_expressions(original,original_output,multiply,'A')
    assert lib.connect_material_expressions(alpha,'',multiply,'B')
    assert lib.connect_material_property(multiply,'',unreal.MaterialProperty.MP_OPACITY)
    assert lib.connect_material_property(drift,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    _darken_dissolve(material,alpha)
    lib.recompile_material(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material,'CountessEDissolveVersion','2')
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    result={'asset':TARGET,'source':SOURCE,'preserved_original_color_graph':True,'fade_seconds':.45,'fragment_drift_scale_cm':8,'darkens_during_dissolve':True,'passed':True}
    (Path(output)/'shadow-dissolve-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def _darken_dissolve(material,alpha):
    lib=unreal.MaterialEditingLibrary
    color=lib.get_material_property_input_node(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    output=lib.get_material_property_input_node_output_name(material,unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    multiply=lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
    assert lib.connect_material_expressions(color,output,multiply,'A')
    assert lib.connect_material_expressions(alpha,'',multiply,'B')
    assert lib.connect_material_property(multiply,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)


def author_blade_trail(output):
    """Textured Q blood palette on the existing socket-driven trail, not a static slash plane."""
    lib=unreal.MaterialEditingLibrary
    path='/Game/TopDown/Characters/Countess/Materials/M_CountessESharpBladeTrail'
    material=unreal.load_asset(path)
    if material is None:
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_CountessESharpBladeTrail',path.rsplit('/',1)[0],unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('used_with_beam_trails',True)
    material.set_editor_property('used_with_particle_sprites',True)
    def node(kind,**props):
        x=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for k,v in props.items():x.set_editor_property(k,v)
        return x
    uv=node('TextureCoordinate')
    tiling=node('Multiply',const_b=1.0)
    assert lib.connect_material_expressions(uv,'',tiling,'A')
    scale=node('Constant2Vector',r=3.5,g=1.2)
    assert lib.connect_material_expressions(scale,'',tiling,'B')
    pan=node('Panner',speed_x=0.0,speed_y=0.0)
    assert lib.connect_material_expressions(tiling,'',pan,'Coordinate')
    sample=node('TextureSample',texture=unreal.load_asset('/Game/ParagonCountess/FX/Textures/Tile/Noise/T_TilingNoise12'))
    assert lib.connect_material_expressions(pan,'',sample,'UVs')
    shader=node('Custom',code='''
float v=abs(UV.y-.5)*2;
float band=1-smoothstep(.55,.72,v);
float grain=smoothstep(.16,.86,Noise);
float edge=exp(-pow((v-.57)/.17,2));
float fade=pow(saturate(1-Age),.65);
float tail=1-smoothstep(.08,.85,UV.x);
float alpha=saturate(band*(.10+.70*grain+.22*edge)*fade*tail);
// Same low-green, muted blood red as Q; no white/orange hot core.
float3 color=lerp(float3(.008,.0004,.0015),float3(.65,.0018,.014),saturate(grain*.55+edge*.65));
color+=float3(.50,.004,.018)*edge*edge*(.3+.7*grain);
return float4(color*.5,alpha);
''',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for name in ('UV','Noise','Age'):
        pin=unreal.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    shader.set_editor_property('inputs',pins)
    assert lib.connect_material_expressions(uv,'',shader,'UV')
    assert lib.connect_material_expressions(sample,'R',shader,'Noise')
    assert lib.connect_material_expressions(node('ParticleRelativeTime'),'',shader,'Age')
    for prop,rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
        mask=node('ComponentMask',r=rgba[0],g=rgba[1],b=rgba[2],a=rgba[3])
        assert lib.connect_material_expressions(shader,'',mask,lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask,'',prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    result={'passed':True,'asset':path,'source_noise':'Countess T_TilingNoise12','Q_blood_rgb':[.65,.0018,.014],'brightness_multiplier':.5,'newest_trail_fraction':.85,'physical_history_seconds':.085,'texture_flow':False,'socket_driven':True,'white_orange_core':False}
    (Path(output)/'e-blade-trail-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def author_sharp_trail(output):
    source='/Game/ParagonCountess/FX/Particles/p_CountessMeleeTrail'
    path='/Game/TopDown/Characters/Countess/FX/P_CountessESharpTrail'
    asset=unreal.load_asset(path)
    if asset is None:asset=unreal.EditorAssetLibrary.duplicate_asset(source,path)
    assert asset is not None
    modules=[];lifetimes=[]
    for obj in unreal.ObjectIterator(unreal.ParticleModule):
        if not obj.get_path_name().startswith(path+'.P_CountessESharpTrail:'):continue
        kind=obj.get_class().get_name()
        if kind=='ParticleModuleTypeDataAnimTrail':
            for name,value in [('bEnablePreviousTangentRecalculation',False),('bTangentRecalculationEveryFrame',False),('DistanceTessellationStepSize',0.0),('TangentTessellationStepSize',0.0),('WidthTessellationStepSize',0.0)]:
                obj.set_editor_property(name,value)
            modules.append(obj.get_path_name())
        elif kind.startswith('ParticleModuleLifetime'):
            dist=obj.get_editor_property('lifetime').get_editor_property('distribution')
            assert dist.get_path_name().startswith(path+'.P_CountessESharpTrail:')
            cls=dist.get_class().get_name()
            if cls=='DistributionFloatConstant':dist.set_editor_property('constant',.085)
            elif cls=='DistributionFloatUniform':
                dist.set_editor_property('min',.085);dist.set_editor_property('max',.085)
            else:raise RuntimeError('Unreviewed trail lifetime distribution '+cls)
            lifetimes.append(dist.get_path_name())
    assert modules and lifetimes,'E private trail must contain actual AnimTrail and lifetime modules'
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    result={'passed':True,'asset':path,'source':source,'lifetime_seconds':.085,'spline_tangent_and_tessellation_disabled':True,'animtrail_modules':modules,'lifetime_distributions':lifetimes}
    (Path(output)/'e-sharp-particle.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def author_target_cuts(output):
    lib=unreal.MaterialEditingLibrary
    folder='/Game/TopDown/Characters/Countess/Materials'
    name='M_CountessETargetCut'
    material=unreal.load_asset(folder+'/'+name)
    if material is None:material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    def node(kind,**props):
        x=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for k,v in props.items():x.set_editor_property(k,v)
        return x
    shader=node('Custom',code='''
float age=Clock-SpawnTime;
if(age<0 || age>Duration)return float4(0,0,0,0);
float t=saturate(age/max(Duration,.001));
float taper=pow(saturate(sin(UV.x*3.14159265)),.45);
float v=abs(UV.y-.5)*2;
float width=.035+.26*taper;
float body=1-smoothstep(width*.55,width,v);
float razor=(1-smoothstep(.012,.055,v))*taper;
float grain=.78+.22*sin(UV.x*157+UV.y*9);
float fade=smoothstep(0,.006,age)*pow(1-t,1.2);
float3 blood=float3(1.0,.006,.024)*body*grain;
float3 white=float3(3.2,2.6,2.5)*razor*pow(1-t,1.5);
return float4((blood+white)*Energy,saturate((body*.8+razor*.2)*fade));
''',output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for n in ('UV','Clock','SpawnTime','Duration','Energy'):
        pin=unreal.CustomInput();pin.set_editor_property('input_name',n);pins.append(pin)
    shader.set_editor_property('inputs',pins)
    for expression,pin in [(node('TextureCoordinate'),'UV'),(node('Time'),'Clock'),(node('ScalarParameter',parameter_name='SpawnTime',default_value=0),'SpawnTime'),(node('ScalarParameter',parameter_name='Duration',default_value=.11),'Duration'),(node('ScalarParameter',parameter_name='Energy',default_value=1),'Energy')]:
        assert lib.connect_material_expressions(expression,'',shader,pin)
    for prop,rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))]:
        mask=node('ComponentMask',r=rgba[0],g=rgba[1],b=rgba[2],a=rgba[3])
        assert lib.connect_material_expressions(shader,'',mask,lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask,'',prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    result={'passed':True,'asset':folder+'/'+name,'shape':'straight tapered red blade with thin white razor','lifetime_seconds':.11,'weapon_motion_dependency':False}
    (Path(output)/'e-target-cut-material.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
