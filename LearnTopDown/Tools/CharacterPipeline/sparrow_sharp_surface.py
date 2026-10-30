"""Author S Sharp Shooter's overlapping charge, compression and second release ring.

Only project-owned materials are saved. Five native planes share this one
aperture surface; their world positions are also the real arrow origins. The parent runs
author(out) before its serialized editor/PIE check.
"""
import hashlib
import json
from pathlib import Path

import unreal


TARGET = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSharpMuzzle'
VERSION = '10'

SURFACE = r'''
float2 p=(UV-.5)*2.;
float unfold=smoothstep(.0,.09,Age);
float compress=smoothstep(.105,.265,Age);
float fired=1.-step(10.,ShotAge);
float fade=lerp(1.,1.-smoothstep(.0,.045,ShotAge),fired);
float charge=smoothstep(.18,.29,Age)*(1.-fired);
float aa=max(length(fwidth(p))*.5,.0025);
float radius=lerp(lerp(.10,.74,unfold),.20,compress);
float d=length(p);
float angle=atan2(p.y,p.x);
// Clean circle geometry; only luminosity and the soft interior layer flow.
float flow=.72+.28*sin(angle*3.-Age*9.+Index*1.7);
float edge=abs(d-radius);
float rim=(1.-smoothstep(.004,.004+aa,edge))*flow;
float halo=exp(-edge*edge/.0036);
float veil=exp(-pow((d-radius*.82)/.13,2.))*(.55+.45*sin(angle*4.+d*19.-Age*13.+Index));
float chargeCore=exp(-d*d/.007)*charge;
float focus=exp(-d*d/.045)*charge;
float3 color=float3(2.9,2.8,2.5)*rim+float3(1.6,1.4,1.05)*halo;
color+=float3(1.4,1.25,.98)*veil*.6;
color+=float3(5.6,5.2,4.3)*chargeCore+float3(2.0,1.6,.9)*focus*.6;
float alpha=saturate(rim*.48+halo*.25+veil*.10+chargeCore*.75+focus*.18);
float envelope=smoothstep(0.,.035,Age)*fade*(1.-smoothstep(.57,.64,Age));
return float4(color*envelope,alpha*envelope);
'''


RELEASE = r'''
float2 p=(UV-.5)*2.;
float d=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.6,.003);
float t=max(ShotAge,0.);
float alive=(1.-step(.16,t))*step(0.,ShotAge);
float fired=1.-step(10.,ShotAge);
float3 color=0.;
float alpha=0.;
for(int i=0;i<2;++i) {
    float age=t-i*.033;
    float on=step(0.,age);
    float envelope=on*(1.-smoothstep(.012,.11,age));
    float radius=lerp(.32,.84,pow(saturate(age/.035),.55));
    float edge=abs(d-radius);
    float rim=(1.-smoothstep(.004,.004+aa,edge))*(.75+.25*sin(a*3.-t*15.));
    float corona=exp(-edge*edge/.0055);
    color+=envelope*(float3(3.2,3.0,2.4)*rim+float3(2.0,1.6,.9)*corona);
    alpha+=envelope*(rim*.38+corona*.19);
}
float pulse=exp(-pow((t-.030)/.027,2.))+exp(-pow((t-.083)/.026,2.))*.80;
float core=exp(-d*d/.038)*pulse;
float aura=exp(-d*d/.13)*pulse;
float rays=pow(saturate(cos(a*13.+.35)),38.)
    *smoothstep(.13,.25,d)*(1.-smoothstep(.32+t*1.8,.48+t*1.8,d))
    *(1.-smoothstep(.015,.075,t));
color+=float3(13.0,12.4,10.5)*core+float3(3.5,2.8,1.5)*(aura*.85+rays);
alpha+=core+aura*.38+rays*.45;
float gather=smoothstep(.015,.09,Age)*(.65+.35*smoothstep(.21,.35,Age))*(1.-fired);
float center=exp(-d*d/.009)*gather;
float mist=exp(-d*d/.055)*gather;
float3 chargeColor=float3(4.4,4.2,3.6)*center+float3(1.8,1.5,.9)*mist*.55;
return float4(color*alive+chargeColor,saturate(alpha)*alive+saturate(center*.7+mist*.18));
'''


def _author_surface(out, target, surface, opaque=False, indexed=False):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(target)
    signature = hashlib.sha256(surface.encode('utf-8')).hexdigest()
    reused = material is not None and unreal.EditorAssetLibrary.get_metadata_tag(
        material, 'SharpMuzzleSurfaceHash') == signature
    if not reused:
        if material is None:
            folder, name = target.rsplit('/', 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, unreal.Material, unreal.MaterialFactoryNew())
        assert isinstance(material, unreal.Material), target
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_OPAQUE if opaque else unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)

        def node(kind, **values):
            result = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in values.items():
                result.set_editor_property(key, value)
            return result

        shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code=surface)
        inputs = []
        for name in (('UV', 'Age', 'ShotAge', 'Index') if indexed else ('UV', 'Age', 'ShotAge')):
            item = unreal.CustomInput()
            item.set_editor_property('input_name', name)
            inputs.append(item)
        shader.set_editor_property('inputs', inputs)
        for source, pin in ((node('TextureCoordinate'), 'UV'),
                            (node('ScalarParameter', parameter_name='Age', default_value=0.), 'Age'),
                            (node('ScalarParameter', parameter_name='ShotAge', default_value=100.), 'ShotAge')):
            assert lib.connect_material_expressions(source, '', shader, pin), pin
        if indexed:
            assert lib.connect_material_expressions(node('ScalarParameter', parameter_name='Index', default_value=0.), '', shader, 'Index')
        for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
            mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        errors = [str(error) for error in (lib.recompile_material(material) or [])]
        assert not errors, errors
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'SharpMuzzleSurfaceHash', signature)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), target
    result = {'passed': True, 'version': VERSION, 'asset': target, 'reused': reused,
              'surface_hash': signature, 'saved_scope': [target], 'source_assets_saved': False,
              'apertures': 5, 'plane_size_cm': 180., 'initial_ring_diameter_cm': 133.2,
              'compressed_ring_diameter_cm': 36., 'open_seconds': .09,
              'compression_seconds': [.105, .265], 'second_wave_seconds': [0., .16],
              'surface_detail': 'large overlapping outlines contract, then a separate double-pulse release ring',
              'reference': 'J2JoIe01BEI 431.09-431.79: charge then close-range bundle release',
              'gameplay_changed_by_author': False, 'visual_acceptance': 'pending actual PIE review'}
    
    return result


STREAK = r'''
float x=UV.x;
float y=abs(UV.y-.5)*2.;
float aa=max(fwidth(y),.008);
float width=lerp(.004,.030,smoothstep(.20,.84,x));
float tail=pow(smoothstep(.02,.80,x),1.3)*(1.-smoothstep(.95,1.,x));
float shaft=(1.-smoothstep(width,width+aa,y))*tail;
float headWidth=max(0.,(.99-x)*.95);
float head=(1.-smoothstep(headWidth,headWidth+aa,y))
    *smoothstep(.89,.91,x)*(1.-smoothstep(.985,1.,x));
float sheath=exp(-y*y/.030)*pow(smoothstep(.03,.80,x),1.6)*(1.-smoothstep(.94,1.,x));
float3 color=float3(5.4,5.2,4.5)*(shaft+head*.65)+float3(2.2,1.8,.9)*sheath;
return float4(color,saturate(shaft*.85+head*.65+sheath*.25));
'''


IMPACT = r'''
float2 p=(UV-.5)*2.;
float d=length(p);
float a=atan2(p.y,p.x);
float t=max(Age,0.);
float strength=exp(-t*17.)*(1.+.40*exp(-pow((t-.045)/.018,2.)));
float core=exp(-d*d/.042);
float halo=exp(-d*d/.19);
float sector=floor((a+3.141593)*3.183099);
float variation=frac(sin(sector*47.17+3.1)*173.31);
float radial=pow(saturate(cos(a*10.)),100.)
    *smoothstep(.13,.25,d)*(1.-smoothstep(.40+variation*.24+t*.9,.63+variation*.21+t*.9,d));
float crossGlow=exp(-pow(p.x/.014,2.)-pow(p.y/.53,2.))
    +exp(-pow(p.y/.012,2.)-pow(p.x/.61,2.));
float3 color=float3(16.,15.4,13.2)*core+float3(4.5,3.8,2.3)*halo
    +float3(7.,6.7,5.6)*(radial+crossGlow*.55);
float alpha=saturate(core+halo*.35+radial*.75+crossGlow*.42)*strength;
return float4(color*strength,alpha);
'''


def author(out):
    rows=[_author_surface(out,TARGET,SURFACE,indexed=True),
          _author_surface(out,TARGET.replace('Muzzle','Streak'),STREAK),
          _author_surface(out,TARGET.replace('Muzzle','Release'),RELEASE),
          _author_surface(out,TARGET.replace('Muzzle','Impact'),IMPACT)]
    result={'passed':True,'version':VERSION,'materials':rows,'saved_scope':[row['asset'] for row in rows]}
    (Path(out)/'sharp-muzzle-surface.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
