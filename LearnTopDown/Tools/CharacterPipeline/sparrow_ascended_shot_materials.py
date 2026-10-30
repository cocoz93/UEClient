"""Dedicated ascended Q/W/R surfaces; normal Sparrow materials are not changed."""
import hashlib
import json
from pathlib import Path
import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/AscendedArsenal20261026'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
RAYS = '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays'
COMMON = r'''
float2 p=(UV-.5)*2.;
float aa=max(length(fwidth(p))*.55,.003);
float n=Texture2DSample(Flow,FlowSampler,UV*2.8+float2(-Age*1.3,Index*.173)).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*9.2+float2(-Age*3.8,Index*.217)).g;
float3 amber=float3(1.5,.42,.025), gold=float3(3.1,1.45,.22), ivory=float3(4.2,3.35,1.85);
float fired=1.-step(10.,PulseAge);
float release=exp(-max(0.,PulseAge)*16.)*fired;
float edge=(1.-smoothstep(.86,1.,abs(p.x)))*(1.-smoothstep(.86,1.,abs(p.y)));
'''

BOW_FLOW = r'''
float t=max(0.,PulseAge);
float x=UV.x;
float taper=pow(saturate(sin(x*3.141593)),.68);
float bend=sin(x*3.141593)*(.23+.035*sin(Age*7.+Index*1.9));
float d=p.y-bend*(1.-Progress*.28);
float width=(.14+.12*taper)*(Skill<.5?.72:1.);
float tissue=exp(-pow(d/width,2.))*taper*(.25+n*.5+fine*.28);
float crest=exp(-pow((d-width*.2)/(.010+aa),2.))*taper;
float seam=exp(-pow((d+width*.75)/(.013+aa),2.))*taper;
float bands=pow(saturate(cos(x*25.-Age*21.+Index*2.1)),10.);
float fringe=exp(-pow((abs(d)-width*1.2)/(.052+aa),2.))*taper*pow(saturate(fine*1.7-.35),4.);
float small=pow(saturate(sin(x*93.-Age*57.+Index*3.2)),36.)*exp(-pow((abs(d)-width*1.8)/.075,2.))*taper;
float pulse=lerp(.32+.53*Progress,.65+release,step(2.,Skill));
float fade=smoothstep(.0,.09,Age)*Envelope;
if(Skill<2.)fade*=lerp(1.,exp(-t*10.),fired);
float3 rgb=amber*tissue*1.2+gold*(tissue*bands*.65+fringe*.55)+ivory*(crest*(.17+bands*.26)+seam*.09+small*.32);
float alpha=tissue*.65+crest*.30+seam*.13+fringe*.34+small*.38;
return float4(rgb*pulse*fade*edge,saturate(alpha*pulse)*fade*edge);
'''

BOW_PULSE = r'''
float t=max(0.,PulseAge);
float r=length(p), a=atan2(p.y,p.x);
float live=fired*(1.-smoothstep(.10,.23,t))*Envelope;
float rays=0., splinters=0., arc=0.;
for(int i=0;i<12;i++){
 float h=frac(sin(float(i)*49.17+Index*.9)*1387.23);
 float ang=float(i)*2.399963+Index*.47;
 float2 axis=float2(cos(ang),sin(ang));
 float center=.075+t*(1.4+h*1.8);
 float2 q=p-axis*center;
 float along=dot(q,axis), side=abs(q.x*axis.y-q.y*axis.x);
 float ray=exp(-pow(side/(.006+aa+h*.004),2.))*(1.-smoothstep(.025,.075+h*.06,abs(along)));
 float chip=1.-smoothstep(.65,1.,abs(along)/(.022+h*.026)+side/(.010+h*.008));
 rays+=ray*(.45+h*.4);splinters+=chip;
}
float wave=.13+t*2.8;
float sectors=pow(saturate(cos(a*5.+Index*.6)),5.);
arc=exp(-pow((r-wave)/(.014+aa),2.))*sectors*(.3+n*.7)*exp(-t*11.);
float slit=exp(-pow(p.y/(.008+aa),2.))*exp(-pow(p.x/.12,2.))*exp(-t*29.);
float density=Skill>2.?.65:1.;
float3 rgb=gold*(arc*.75+rays*.55)+ivory*(splinters*.45+slit*.55)+amber*rays*.4;
float alpha=arc*.38+rays*.30+splinters*.60+slit*.55;
return float4(rgb*live*density*edge,saturate(alpha)*live*density*edge);
'''

RAIN_STREAK = r'''
float x=UV.x;
float nose=smoothstep(.925,.999,x);
float rounded=max(.008,sqrt(saturate(1.-nose*nose)));
float bounds=smoothstep(.0,.025,x)*(1.-smoothstep(.980,1.,x));
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(p.y*.32+.5+Index*.197),x*.36-Age*.8)).rgb;
float bend=(.012*sin(x*17.-Age*12.+Index)+.006*(n-.5))*(1.-nose);
float y=p.y-bend;
float shaft=exp(-pow(y/(.065*rounded+aa*.42),2.))*bounds;
float body=exp(-pow(y/max(.003,.245*rounded),4.))*bounds*(.86+n*.14);
float veil=exp(-pow(y/(.34*rounded+.025*n),2.))*bounds*(.42+rays.b*.58);
float filaments=0.,knots=0.,sideFlow=0.;
for(int i=0;i<4;i++){
 float offset=(float(i)-1.5)*.17*rounded;
 float d=y-offset-.009*sin(x*13.-Age*11.+i*1.7)*(1.-nose);
 float pulse=pow(saturate(cos(x*22.-Age*25.+i*1.7)),12.);
 filaments+=exp(-pow(d/(.007+aa*.55),2.))*bounds*(.35+.50*pulse);
 knots+=pulse*exp(-pow(d/.025,2.))*bounds;
 float outward=(i<2?-1.:1.)*(.29+.05*sin(x*18.-Age*19.+i*2.1))*rounded;
 sideFlow+=exp(-pow((p.y-outward)/(.030+aa),2.))*bounds*(.25+pow(saturate(sin(x*27.-Age*31.+i*1.6)),5.)*.75);
}
float head=exp(-pow((x-.967)/.043,2.)-pow(p.y/.49,2.))*(1.-smoothstep(.985,1.,x));
float headCore=exp(-pow((x-.963)/.027,2.)-pow(p.y/.20,2.))*(1.-smoothstep(.985,1.,x));
float ground=exp(-pow((x-.975)/.055,2.))*exp(-pow(p.y/.48,2.));
float impact=exp(-pow((Progress-.940)/.055,2.));
float fade=smoothstep(.0,.045,Progress)*(1.-smoothstep(1.10,1.45,Progress))*Envelope;
float3 rgb=amber*(veil*.42+sideFlow*.45)+gold*(body*1.05+veil*.55+filaments*.48+head*.80+sideFlow*.85)+ivory*(shaft*1.12+knots*.11+headCore*.55+ground*impact*1.5);
float alpha=body*.63+veil*.22+filaments*.29+shaft*.88+head*.40+headCore*.42+sideFlow*.34+ground*impact*.85;
return float4(rgb*fade,saturate(alpha)*fade);
'''

RAIN_HEAD = r'''
float t=max(0.,Progress-.82),press=smoothstep(.42,.82,Progress);
float spine=exp(-pow(p.y/.105,2.))*smoothstep(-.96,-.65,p.x)*(1.-smoothstep(.12,.87,p.x));
float width=.12+.035*saturate(p.x+.6);
float flow=Texture2DSample(Flow,FlowSampler,float2(UV.x*2.2-Age*1.4,UV.y*3.7+Index*.17)).g;
float mantle=exp(-pow(p.y/(width*1.9),2.))*exp(-pow((p.x+.12)/.55,2.))*(.50+flow*.50);
float tip=exp(-pow((p.x+.63)/.17,2.)-pow(p.y/.11,2.));
float glow=exp(-pow((p.x+.38)/.43,2.)-pow(p.y/.30,2.))*(.5+n*.5);
float snap=exp(-t*44.)*step(.82,Progress);
float fade=smoothstep(0.,.07,Progress)*(1.-smoothstep(.83,1.02,Progress))*Envelope;
float3 rgb=float3(1.55,.55,.045)*(mantle*.82+glow*.30)+float3(3.1,1.85,.48)*(spine*.72+tip*(.42+press*.25))+ivory*tip*snap*.8;
float alpha=mantle*.50+spine*.77+tip*.48+glow*.14;
return float4(rgb*fade*edge,saturate(alpha)*fade*edge);
'''

RAIN_CONTACT = r'''
float t=max(0.,Progress-.92);
float rays=0.,chips=0.;
for(int i=0;i<26;i++){
 float h=frac(sin(float(i)*43.13+Index*3.1)*4813.7);
 float a=float(i)*2.399963+Index*1.2;
 float2 axis=float2(cos(a),sin(a));
 float2 q=p-axis*(.035+t*(1.5+h*1.8));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 rays+=exp(-pow(side/(.009+aa),2.))*(1.-smoothstep(.016,.050+h*.045,abs(along)))*exp(-t*13.);
 chips+=1.-smoothstep(.7,1.,abs(along)/(.018+h*.032)+side/(.010+h*.012));
}
float r=length(p), angle=atan2(p.y,p.x)/6.2831853+.5;
float3 tissue=Texture2DSample(Rays,RaysSampler,float2(frac(angle+Index*.173),saturate(r/(.24+t*2.5)))).rgb;
float warp=(n-.5)*.15+(fine-.5)*.050;
float pressureRadius=t<.07?lerp(.25,.14,smoothstep(0.,.07,t)):.14+(t-.07)*1.75;
float pressure=exp(-pow((r+warp*.55-pressureRadius)/(.085+aa),2.))*(.58+smoothstep(.18,.65,n*.75+tissue.b*.48)*.42)*exp(-t*5.5);
float plate=exp(-pow(r/.31,4.))*(.62+tissue.b*.38)*exp(-t*13.);
float fissures=pow(saturate(tissue.r),1.4)*smoothstep(.20,.61,n)*exp(-r*2.7)*exp(-t*4.5);
float debris=smoothstep(.34,.69,n*.76+fine*.31)*exp(-pow((r-(.14+t*1.50))/.15,2.))*exp(-t*4.4);
float hit=exp(-dot(p,p)/.032)*exp(-t*42.);
float weight=exp(-dot(p,p)/.12)*(.30+n*.35)*exp(-t*17.);
float fade=(1.-smoothstep(.36,.56,t))*Envelope;
float3 rgb=amber*(pressure*1.25+debris*1.25)+gold*(rays*.52+pressure*1.25+fissures*1.50+weight*1.15+plate*1.5)+ivory*(chips*.33+hit*2.2);
float alpha=rays*.28+chips*.56+hit*.94+pressure*.68+fissures*.58+debris*.42+weight*.45+plate*.64;
return float4(rgb*fade*edge,saturate(alpha)*fade*edge);
'''

RAIN_FLARE = r'''
float t=max(0.,Progress-.92), x=UV.x;
float spread=.16+x*.53;
float3 tissue=Texture2DSample(Rays,RaysSampler,float2(frac(p.y*.40+.5+Index*.173),saturate(x-t*.85))).rgb;
float mask=exp(-pow(p.y/spread,4.))*smoothstep(0.,.08,x)*(1.-smoothstep(.34+t*.90,.70+t*.45,x));
float flame=tissue.b*mask*(.32+fine*.68);
float streak=tissue.r*mask*(.55+n*.45);
float core=exp(-pow((x-.16)/.12,2.)-pow(p.y/.24,2.))*exp(-t*34.);
float burst=exp(-pow((x-.21)/.20,2.)-pow(p.y/.52,2.))*exp(-t*22.);
float fade=(1.-smoothstep(.25,.51,t))*Envelope;
float3 rgb=amber*flame*1.25+gold*(flame*1.1+streak*.78+burst*.75)+ivory*(core*1.8+streak*.22);
return float4(rgb*fade,saturate(flame*.62+streak*.43+core*.88+burst*.40)*fade*edge);
'''

CONTACT = r'''
float rays=0.,shards=0.,secondary=0.;
float span=Skill>2.?.16:.22;
float t=Age;
for(int i=0;i<18;i++){
 float h=frac(sin(float(i)*31.87+Index*8.3)*2571.9);
 float a=(float(i)*2.399963+Index*.81);
 float2 axis=float2(cos(a),sin(a));
 float2 q=p-axis*(.03+t*(1.6+h*2.7));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 float dash=1.-smoothstep(.65,1.,abs(along)/(.035+h*.035)+side/(.010+h*.010));
 shards+=dash;
 rays+=exp(-pow(side/(.006+aa),2.))*(1.-smoothstep(.018,.10+h*.035,abs(along)))*(.2+h*.4);
 float t2=max(0.,t-.045),r2=.025+t2*(1.7+h*2.0);
 float2 q2=p-axis*r2;
 secondary+=(1.-smoothstep(.7,1.,abs(dot(q2,axis))/.035+abs(q2.x*axis.y-q2.y*axis.x)/.010))*smoothstep(.04,.05,t)*exp(-t2*12.);
}
float core=exp(-dot(p,p)/.008)*exp(-t*30.);
float slash=exp(-pow(p.y/(.008+aa),2.))*exp(-p.x*p.x/.060)*exp(-t*24.);
float tissue=exp(-dot(p,p)/.09)*(1.-exp(-dot(p,p)/.018))*(.1+n*.40)*exp(-t*19.);
float fade=(1.-smoothstep(span*.60,span,t))*Envelope;
float intensity=Skill>2.?.70:1.;
float3 rgb=amber*tissue*1.7+gold*(rays*.80+shards*.40)+ivory*(shards*.25+secondary*.48+core*.85+slash*.45);
float alpha=tissue*.20+rays*.24+shards*.62+secondary*.47+core*.72+slash*.50;
return float4(rgb*fade*intensity*edge,saturate(alpha)*fade*edge);
'''

FEATHER = r'''
struct FFeatherCurve {
 float2 Curve(float u) {
  float v=1.-u;
  return float2(-.88,-.08)*v*v*v+3.*float2(-.33,-.32)*v*v*u
       +3.*float2(.32,.24)*v*u*u+float2(.89,.06)*u*u*u;
 }
};
FFeatherCurve feather;
float nearest=0.,distance=100.,signedDistance=0.;
float2 previous=feather.Curve(0.);
for(int i=1;i<=24;i++){
 float u=float(i)/24.;float2 current=feather.Curve(u);
 float2 segment=current-previous;
 float along=saturate(dot(p-previous,segment)/max(dot(segment,segment),.00001));
 float2 offset=p-(previous+segment*along);float d=length(offset);
 if(d<distance){distance=d;nearest=(float(i)-1.+along)/24.;signedDistance=(segment.x*offset.y-segment.y*offset.x)/max(length(segment),.0001);}
 previous=current;
}
float taper=pow(saturate(sin(nearest*3.141593)),.74);
float width=.29*taper*lerp(.78,1.,step(0.,signedDistance));
float shape=(1.-smoothstep(width-aa,width+aa,distance))*smoothstep(.07,.13,nearest);
float flute=nearest*16.-abs(signedDistance)*8.8+sin(nearest*9.+Index)*.13;
float barb=exp(-pow((frac(flute)-.5)/.075,2.))*shape;
float notch=pow(saturate(cos(flute*6.283185)),17.)*smoothstep(width*.62,width,distance);
shape*=1.-notch*.76;
float stem=exp(-pow(distance/(.009+aa*.45),2.))*(1.-smoothstep(.94,1.,nearest));
float rim=exp(-pow((distance-width)/(.012+aa),2.))*smoothstep(.12,.20,nearest)*(1.-notch);
float veins=shape*(.28+n*.30+fine*.14);
float glint=pow(saturate(sin(nearest*11.-Age*9.+Index*1.9)),10.);
float shimmer=pow(saturate(fine*1.6-.45),5.)*shape;
float fade=smoothstep(.0,.022,Age)*Envelope;
float3 rgb=amber*veins*1.15+gold*(shape*.35+barb*.30+rim*.23)
          +ivory*(stem*.52+barb*(.08+glint*.16)+shimmer*.20);
float alpha=shape*.53+stem*.48+barb*.24+rim*.20;
return float4(rgb*fade*(1.+Skill*.16)*edge,saturate(alpha)*fade*edge);
'''


def author(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(NOISE)
    assert texture, NOISE
    rays = unreal.load_asset(RAYS)
    assert rays, RAYS
    rows = []
    for name, body in [('BowFlow', BOW_FLOW), ('BowPulse', BOW_PULSE),
                       ('RainStreak', RAIN_STREAK), ('RainHead', RAIN_HEAD), ('RainContact', RAIN_CONTACT), ('RainFlare', RAIN_FLARE),
                       ('Contact', CONTACT), ('Feather', FEATHER)]:
        path = f'{FOLDER}/M_Ascended{name}'
        code = COMMON + body
        signature = hashlib.sha256(code.encode()).hexdigest()
        material = unreal.load_asset(path)
        reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'AscendedShotHash') == signature)
        if not reused:
            if not material:
                folder, asset = path.rsplit('/', 1)
                material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset, folder, unreal.Material, unreal.MaterialFactoryNew())
            assert material, path
            # Detach completed graph outputs before rebuilding; old masks otherwise
            # emit misleading temporary "Missing ComponentMask input" warnings.
            lib.disconnect_material_property(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            lib.disconnect_material_property(material, unreal.MaterialProperty.MP_OPACITY)
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided', True)

            def node(kind, **props):
                obj = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
                for key, value in props.items():
                    obj.set_editor_property(key, value)
                return obj

            shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture)}
            if name.startswith('Rain'):
                sources['Rays'] = node('TextureObject', texture=rays)
            for param, default in [('Age', 0.), ('Progress', 0.), ('PulseAge', 100.), ('Index', 0.), ('Skill', 0.), ('Envelope', 1.)]:
                sources[param] = node('ScalarParameter', parameter_name=param, default_value=default)
            inputs = []
            for param in sources:
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', param)
                inputs.append(pin)
            shader.set_editor_property('inputs', inputs)
            for param, source in sources.items():
                assert lib.connect_material_expressions(source, '', shader, param)
            for prop, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                                   (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
                mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
                assert lib.connect_material_expressions(shader, '', mask, '')
                assert lib.connect_material_property(mask, '', prop)
        # UE 5.8 returns the final platform compiler errors from RecompileMaterial.
        # Also validate reused assets: a saved hash alone cannot prove a shader compiled.
        compile_errors = [str(error) for error in (lib.recompile_material(material) or [])]
        rows.append({'path': path, 'hash': signature, 'reused': reused, 'compile_errors': compile_errors})
        if compile_errors:
            (out / 'ascended-shot-materials.json').write_text(
                json.dumps({'passed': False, 'materials': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
            raise RuntimeError(path + ': ' + '\n'.join(compile_errors))
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'AscendedShotHash', signature)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result = {'passed': True, 'materials': rows, 'normal_materials_changed': False,
              'texture': NOISE, 'packed_channels': {'r': 'broad flow', 'g': 'fine breakup'}}
    (out / 'ascended-shot-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
