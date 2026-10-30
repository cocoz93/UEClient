"""S radiance-v10 restoration and a separate textured refinement; R texture tip.

Run author(out) only in the parent's serialized editor. Source packs and installed
Sharp materials are read-only. Base shader strings are copied without alteration.
"""
import hashlib
import json
from pathlib import Path
import runpy

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/SharpReference20261027'
FLOW = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
SHARD = '/Game/TopDown/Characters/Aurora/FX/T_Aurora_FxShard'
V10_HASH = 'abef4e981ecfa549a8f191ad98f43141aa0d1afcd7fd8349fd03140789f194c8'

COMMON = r'''
float2 p=(UV-.5)*2.;
float d=length(p);
float aa=max(length(fwidth(p))*.5,.0025);
float angle=atan2(p.y,p.x);
float2 scroll=p*2.9+float2(-Age*.71+Index*.17,Age*.29);
float field=Texture2DSample(Flow,FlowSampler,scroll).r;
float fine=Texture2DSample(Flow,FlowSampler,p*7.1+float2(Age*.4,-Age*1.3+Index*.21)).g;
float tissue=smoothstep(.19,.73,field+fine*.24);
float3 gold=float3(3.0,1.52,.30);
float3 amber=float3(1.05,.32,.035);
float3 pearl=float3(5.0,4.38,2.9);
'''

MUZZLE = r'''
// The radius is independent of angle/noise: circles remain clean and round.
float unfold=smoothstep(.0,.09,Age);
float compress=smoothstep(.105,.265,Age);
float radius=lerp(lerp(.10,.74,unfold),.20,compress);
float fired=1.-step(10.,ShotAge);
float fade=lerp(1.,1.-smoothstep(.0,.045,ShotAge),fired);
float envelope=smoothstep(0.,.035,Age)*fade*(1.-smoothstep(.57,.64,Age));
float edge=abs(d-radius);
float rim=1.-smoothstep(.005,.005+aa,edge);
float band=exp(-pow((d-radius*.88)/.085,2.));
float outside=exp(-edge*edge/.0040);
float filigree=pow(saturate(tissue),1.7)*band;
float inner=smoothstep(.04,.10,d)*(1.-smoothstep(radius*.68,radius*.94,d));
float movement=.55+.45*sin(angle*2.8-Age*10.5+Index*1.67);
float innerVeil=inner*tissue*(.24+.76*movement);
float along=.58+.42*pow(saturate(cos(angle*2.-Age*8.+Index*.7)),6.);
float seam=exp(-pow((d-radius*.74)/.020,2.))*smoothstep(.38,.65,field)*movement;
float charge=smoothstep(.18,.29,Age)*(1.-fired);
float core=exp(-d*d/.006)*charge;
float3 color=pearl*rim*along*.54+gold*(outside*.59+filigree*.95+seam*.42);
color+=amber*(innerVeil*.80+band*.65)+pearl*core;
float alpha=rim*.52+outside*.27+filigree*.35+innerVeil*.20+seam*.25+core*.85;
return float4(color*envelope,saturate(alpha)*envelope);
'''

RELEASE = r'''
float t=max(ShotAge,0.);
float fired=1.-step(10.,ShotAge);
float alive=(1.-step(.18,t))*step(0.,ShotAge);
float3 color=0.;
float alpha=0.;
// Preserve the two distinct re-ignitions instead of replacing them with a flame plume.
for(int i=0;i<2;++i){
    float local=t-i*.033;
    float on=step(0.,local);
    float gate=on*(1.-smoothstep(.015,.13,local));
    float radius=lerp(.32,.84,pow(saturate(local/.035),.55));
    float edge=abs(d-radius);
    float rim=1.-smoothstep(.006,.006+aa,edge);
    float film=exp(-pow((d-radius*.86)/.10,2.))*(.25+tissue*.75);
    float haze=exp(-edge*edge/.006);
    float stream=film*pow(saturate(fine+.2),2.0);
    color+=gate*(pearl*rim*.56+gold*(film*.95+haze*.45)+amber*stream);
    alpha+=gate*(rim*.52+film*.38+haze*.17);
}
float pulse=exp(-pow((t-.030)/.023,2.))+.75*exp(-pow((t-.083)/.021,2.));
float center=exp(-d*d/.026)*pulse;
float plume=exp(-d*d/.12)*pulse*tissue;
float rays=0.;
for(int k=0;k<11;++k){
    float a=k*2.399963;
    float2 axis=float2(cos(a),sin(a));
    float extent=.25+frac(k*.618)*.46;
    float along=dot(p,axis);
    float across=abs(p.x*axis.y-p.y*axis.x);
    rays+=exp(-pow(across/(.007+aa),2.))*smoothstep(.12,.25,along)
        *(1.-smoothstep(extent*.6,extent,along));
}
float radiate=(1.-smoothstep(.045,.13,t))*step(0.,ShotAge);
color+=pearl*(center*1.55+rays*radiate*.48)+gold*plume*.68;
alpha+=center*.95+plume*.32+rays*radiate*.39;
float gather=smoothstep(.015,.09,Age)*(.65+.35*smoothstep(.21,.35,Age))*(1.-fired);
float chargeCore=exp(-d*d/.009)*gather;
float chargeVeil=exp(-d*d/.052)*gather;
return float4(color*alive+pearl*chargeCore*.72+gold*chargeVeil*.34,
    saturate(alpha)*alive+saturate(chargeCore*.7+chargeVeil*.16));
'''

STREAK = r'''
// Same straight short shaft on all 15 real parallel arrows; no random jagged mesh.
float x=UV.x;
float across=abs(UV.y-.5)*2.;
float a=max(fwidth(across),.006);
float width=lerp(.004,.025,smoothstep(.20,.84,x));
float shaft=(1.-smoothstep(width,width+a,across))*pow(smoothstep(.02,.80,x),1.25)
    *(1.-smoothstep(.95,1.,x));
float headWidth=max(0.,(.99-x)*.92);
float head=(1.-smoothstep(headWidth,headWidth+a,across))*smoothstep(.87,.90,x)
    *(1.-smoothstep(.985,1.,x));
float trail=exp(-across*across/.024)*pow(smoothstep(.03,.80,x),1.7)
    *(1.-smoothstep(.94,1.,x));
float3 c=pearl*shaft*.65+gold*(head*.9+trail*.48)+amber*trail*.32;
return float4(c,saturate(shaft*.82+head*.72+trail*.26));
'''

IMPACT = r'''
float t=max(Age,0.);
float strength=exp(-t*15.)*(1.+.35*exp(-pow((t-.048)/.018,2.)));
float core=exp(-d*d/.036);
float smoke=exp(-d*d/.17)*tissue;
float flare=0.;
for(int k=0;k<13;++k){
    float a=k*2.399963+.2;
    float2 axis=float2(cos(a),sin(a));
    float along=dot(p,axis), across=abs(p.x*axis.y-p.y*axis.x);
    float extent=.38+frac(k*.618)*.40+t*.4;
    flare+=exp(-pow(across/(.007+aa),2.))*smoothstep(.09,.18,along)
        *(1.-smoothstep(extent*.63,extent,along));
}
float soft=exp(-d*d/.19);
float3 c=pearl*(core*2.4+flare*.70)+gold*(smoke*1.4+soft*.50)+amber*smoke*.8;
return float4(c*strength,saturate(core+flare*.68+smoke*.51+soft*.18)*strength);
'''

R_ARROW = r'''
// Aurora's owned image packs the broad facet and thin ridge separately in R/G.
// The picture's point is at V=0; Plane X/UV.x is the actual flight axis.
float2 at=float2(UV.y,1.-UV.x);
float4 shape=Texture2DSample(Shape,ShapeSampler,at);
float body=shape.r;
float ridge=shape.g;
float center=exp(-pow((UV.y-.5)/.024,2.))*smoothstep(.08,.20,UV.x)
    *(1.-smoothstep(.91,1.,UV.x));
float3 c=float3(2.7,1.25,.18)*body+float3(4.2,3.65,2.3)*ridge*.40
    +float3(1.3,.34,.035)*center*.20;
return float4(c,saturate(body*.70+ridge*.55));
'''


# S103 retains the v10 circle geometry and release clock. The interior energy,
# orbiting chips and two release pulses are independent layers inside that shape.
PLUME_COMMON = r'''
float2 p=(UV-.5)*2.;
float d=length(p);
float aa=max(length(fwidth(p))*.45,.0025);
float angle=atan2(p.y,p.x);
float2 drift=float2(-Age*.81+Index*.173,Age*.39);
float4 grain=Texture2DSample(Flow,FlowSampler,p*2.8+drift);
float4 detail=Texture2DSample(Flow,FlowSampler,p*7.7+float2(Age*.53,-Age*1.6+Index*.27));
float field=pow(saturate(grain.r),.55);
float fiber=pow(saturate(detail.g),.58);
float tissue=smoothstep(.13,.74,field+fiber*.25);
float3 gold=float3(3.8,1.83,.25);
float3 bronze=float3(1.65,.48,.035);
float3 pearl=float3(5.0,4.30,2.75);
'''

PLUME_MUZZLE = r'''
float unfold=smoothstep(0.,.09,Age);
float compress=smoothstep(.105,.265,Age);
float radius=lerp(lerp(.10,.74,unfold),.20,compress);
float fired=1.-step(10.,ShotAge);
float live=smoothstep(0.,.035,Age)*lerp(1.,1.-smoothstep(0.,.045,ShotAge),fired);
float edge=abs(d-radius);
// White is confined to the clean rim; the interior keeps an open center.
float rim=1.-smoothstep(.008,.008+aa,edge);
float broad=exp(-pow((d-radius*.89)/max(.021,radius*.105),2.));
float halo=exp(-edge*edge/.0034);
float normalized=d/max(radius,.08);
float inner=smoothstep(.20,.34,normalized)*(1.-smoothstep(.76,.96,normalized));
float revolve=angle*2.-Age*14.+Index*1.7+normalized*5.4;
float swirl=pow(saturate(.5+.5*sin(revolve)),4.);
float companion=pow(saturate(.5+.5*sin(angle*3.+Age*11.-normalized*6.2+Index)),8.);
float energy=inner*(swirl*.82+companion*.44)*(.27+.73*tissue);
float packet=pow(saturate(.5+.5*cos(angle*2.-Age*12.+Index*1.7)),2.8);
float flowBand=broad*smoothstep(.23,.76,tissue)*(.10+.90*packet);
float rimRace=pow(saturate(.5+.5*cos(angle*3.-Age*18.+Index*1.8)),8.);
float rimCrest=exp(-pow((d-radius*.96)/.024,2.))*rimRace;
float chips=0.,chipGlow=0.;
for(int k=0;k<12;++k){
    float seed=frac(k*.618034+Index*.173);
    float phase=k*2.399963+Age*(3.6+seed*4.)+Index;
    float orbit=radius*(.51+.53*seed);
    float2 axis=float2(cos(phase),sin(phase));
    float2 q=p-axis*orbit;
    float tangent=q.x*(-axis.y)+q.y*axis.x;
    float normal=dot(q,axis);
    float width=max(.013+seed*.009,aa*.65);
    float shard=saturate(1.-abs(tangent)/(.023+seed*.028)-abs(normal)/width);
    float flicker=.35+.65*pow(saturate(.5+.5*sin(Age*21.+k*1.9)),3.);
    chips+=shard*flicker;
    chipGlow+=exp(-(tangent*tangent/.003+normal*normal/.0007))*flicker;
}
float charge=smoothstep(.19,.29,Age)*(1.-fired);
float center=exp(-d*d/.0032)*charge;
float3 color=pearl*(rim*.54+rimCrest*.52+chips*.75+center*.68);
color+=gold*(flowBand*.96+energy*1.05+halo*.25+chipGlow*.18);
color+=bronze*(inner*tissue*.21+broad*tissue*packet*.25);
float opacity=rim*.73+flowBand*.43+energy*.52+chips*.76+chipGlow*.08+center*.65;
return float4(color*live,saturate(opacity)*live);
'''

PLUME_RELEASE = r'''
float t=max(ShotAge,0.);
float fired=1.-step(10.,ShotAge);
float3 color=0.;
float opacity=0.;
// Preserve the v10 re-ignition offsets, while the broad membrane travels out
// behind each thin rim instead of turning the entire aperture white.
for(int i=0;i<2;++i){
    float pulseAge=t-i*.033;
    float gate=step(0.,pulseAge)*(1.-smoothstep(.025,.17,pulseAge));
    float progress=saturate(pulseAge/.035);
    float radius=lerp(.32,.84,pow(progress,.55));
    float edge=abs(d-radius);
    float rim=1.-smoothstep(.009,.009+aa,edge);
    float wake=exp(-pow((d-radius*.86)/.083,2.));
    float movement=pow(saturate(.5+.5*sin(angle*3.-pulseAge*35.+d*9.+i)),3.);
    float membrane=wake*smoothstep(.20,.76,tissue)*(.08+.92*movement);
    float subrim=exp(-pow((d-radius*.73)/.025,2.))*smoothstep(.24,.72,fiber)*movement;
    color+=gate*(pearl*rim*.68+gold*(membrane*1.45+subrim*.51)+bronze*membrane*.34);
    opacity+=gate*(rim*.74+membrane*.57+subrim*.25);
}
float chips=0.,dust=0.;
for(int k=0;k<22;++k){
    float seed=frac(k*.618034);
    float spawn=k%2==0 ? .008 : .050;
    float age=t-spawn;
    float live=step(0.,age)*(1.-smoothstep(.06,.17,age));
    float phase=k*2.399963+.16;
    float2 axis=float2(cos(phase),sin(phase));
    float2 q=p-axis*(.20+seed*.16+max(age,0.)*(2.1+seed*1.8));
    float along=dot(q,axis),across=q.x*(-axis.y)+q.y*axis.x;
    float shard=saturate(1.-abs(along)/(.025+seed*.035)-abs(across)/(.008+seed*.009));
    chips+=shard*live;
    dust+=exp(-(along*along/.004+across*across/.0006))*live;
}
float pulse=exp(-pow((t-.017)/.014,2.))+.82*exp(-pow((t-.068)/.017,2.));
float core=exp(-d*d/.0065)*pulse;
float shock=exp(-d*d/.064)*pulse*tissue;
color+=pearl*(core*1.3+chips*.72)+gold*(shock*.80+dust*.27);
opacity+=core*.94+chips*.82+shock*.31+dust*.17;
float gather=smoothstep(.02,.10,Age)*(1.-fired);
float charge=exp(-d*d/.009)*gather*(.5+.5*smoothstep(.20,.35,Age));
float live=fired*(1.-smoothstep(.16,.21,t));
return float4(color*live+gold*charge*.45,saturate(opacity)*live+charge*.25);
'''

PLUME_STREAK = r'''
float x=UV.x;
float lateral=abs(UV.y-.5)*2.;
float aaTrail=max(fwidth(lateral),.006);
float shaftWidth=.014+.015*smoothstep(.18,.85,x);
float shaft=(1.-smoothstep(shaftWidth,shaftWidth+aaTrail,lateral))*smoothstep(.03,.72,x)
    *(1.-smoothstep(.95,1.,x));
float headWidth=max(0.,(.99-x)*1.08);
float head=(1.-smoothstep(headWidth,headWidth+aaTrail,lateral))*smoothstep(.84,.89,x)
    *(1.-smoothstep(.985,1.,x));
float tail=exp(-lateral*lateral/.028)*pow(smoothstep(.02,.83,x),1.3)
    *(1.-smoothstep(.93,1.,x));
float rail=exp(-pow((lateral-.095)/.025,2.))*smoothstep(.28,.71,x)
    *(1.-smoothstep(.83,.96,x));
return float4(pearl*shaft*.88+gold*(head*1.05+tail*.74+rail*.48),
    saturate(shaft*.91+head*.89+tail*.38+rail*.25));
'''

PLUME_IMPACT = r'''
float t=max(Age,0.);
float kick=exp(-t*24.)+.72*exp(-pow((t-.061)/.021,2.));
float core=exp(-d*d/.010)*kick;
float radius=.17+t*2.8;
float thin=exp(-pow((d-radius)/.025,2.))*(1.-smoothstep(.025,.12,t));
float tissueWake=exp(-pow((d-radius*.76)/.10,2.))*tissue*(1.-smoothstep(.05,.19,t));
float rays=0.,chips=0.;
for(int k=0;k<17;++k){
    float seed=frac(k*.618034);
    float a=k*2.399963+.3;
    float2 axis=float2(cos(a),sin(a));
    float along=dot(p,axis),across=abs(p.x*axis.y-p.y*axis.x);
    float extent=.24+seed*.54;
    rays+=exp(-pow(across/(.005+aa),2.))*smoothstep(.04,.17,along)
        *(1.-smoothstep(extent*.6,extent,along));
    float q=along-(.17+max(t-.03,0.)*(2.2+seed*1.4));
    chips+=saturate(1.-abs(q)/(.029+seed*.024)-across/.012)
        *(1.-smoothstep(.07,.18,t));
}
float live=1.-smoothstep(.17,.23,t);
float3 color=pearl*(core*1.6+rays*kick*.73+chips*.63);
color+=gold*(thin*.74+tissueWake*.85)+bronze*tissueWake*.45;
return float4(color*live,saturate(core+rays*kick*.70+chips*.72+thin*.35+tissueWake*.47)*live);
'''


def _author_textured(target, code, shape=False):
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(target)
    signature = hashlib.sha256((code + FLOW + (SHARD if shape else '')).encode()).hexdigest()
    reused = material is not None and unreal.EditorAssetLibrary.get_metadata_tag(material, 'SharpCraftHash') == signature
    if not reused:
        if material is None:
            folder, name = target.rsplit('/', 1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
        assert isinstance(material, unreal.Material), target
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)

        def node(kind, **values):
            obj = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in values.items():
                obj.set_editor_property(key, value)
            return obj

        shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code=code)
        names = ['UV', 'Age', 'ShotAge', 'Index', 'Flow'] + (['Shape'] if shape else [])
        inputs = []
        for name in names:
            item = unreal.CustomInput()
            item.set_editor_property('input_name', name)
            inputs.append(item)
        shader.set_editor_property('inputs', inputs)
        assert lib.connect_material_expressions(node('TextureCoordinate'), '', shader, 'UV')
        for name, value in (('Age', 0.), ('ShotAge', 100.), ('Index', 0.)):
            assert lib.connect_material_expressions(node('ScalarParameter', parameter_name=name, default_value=value), '', shader, name)
        for name, path in ([('Flow', FLOW)] + ([('Shape', SHARD)] if shape else [])):
            texture = unreal.load_asset(path)
            assert isinstance(texture, unreal.Texture2D), path
            assert lib.connect_material_expressions(node('TextureObject', texture=texture), '', shader, name)
        for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
            mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        errors = [str(error) for error in (lib.recompile_material(material) or [])]
        assert not errors, (target, errors)
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'SharpCraftHash', signature)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), target
    return {'asset': target, 'reused': reused, 'surface_hash': signature, 'source_assets_saved': False}


def author(out):
    output = Path(out)
    output.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).with_name('sparrow_sharp_surface.py')
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    assert actual == V10_HASH, ('v10 source changed', actual)
    original = runpy.run_path(str(source))
    rows = []
    exact = {}
    for part, key in (('Muzzle', 'SURFACE'), ('Streak', 'STREAK'), ('Release', 'RELEASE'), ('Impact', 'IMPACT')):
        shader = original[key]
        path = FOLDER + '/Base/M_SharpReference' + part
        row = original['_author_surface'](output, path, shader, indexed=part == 'Muzzle')
        rows.append(row)
        exact[part] = hashlib.sha256(shader.encode('utf-8')).hexdigest()
    for part, shader in (('Muzzle', MUZZLE), ('Streak', STREAK), ('Release', RELEASE), ('Impact', IMPACT)):
        rows.append(_author_textured(FOLDER + '/Refined/M_SharpReference' + part, COMMON + shader))
    for part, shader in (('Muzzle', PLUME_MUZZLE), ('Streak', PLUME_STREAK), ('Release', PLUME_RELEASE), ('Impact', PLUME_IMPACT)):
        rows.append(_author_textured(FOLDER + '/Plume/M_SharpReference' + part, PLUME_COMMON + shader))
    rows.append(_author_textured(FOLDER + '/M_CraftRArrow', R_ARROW, shape=True))
    report = {'passed': True, 'materials': rows, 'v10_source_sha256': actual,
              'v10_shader_sha256': exact, 'base_strings_modified': False,
              'scope': FOLDER, 'source_assets_saved': False,
              'visual_acceptance': 'pending actual normal/form in-game comparison'}
    (output / 'sr-craft-materials.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
