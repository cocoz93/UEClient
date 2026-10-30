"""Opt-in Sharp Shooter surface studies. Production S assets are read-only.

Sparrow.Sharp.DetailPreview=1..4 changes presentation, with the installed C1
layout, release timing, parallel projectiles and damage left intact.
"""
import hashlib
import json
import os
from pathlib import Path
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/SharpDetails20261026'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
DESIGNS = {1: '백금 겹빛', 2: '황금 성진', 3: '광사 흐름', 4: '집중 파열'}
VERSION = 2

COMMON = r'''
const float style=STYLE;
const float PI=3.14159265;
float2 p=(UV-.5)*2.;
float d=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.55,.0025);
float n=Texture2DSample(Flow,FlowSampler,UV*2.3+float2(Age*.13,-Age*.31)+Index*.17).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*7.1+float2(-Age*.42,Age*.27)).g;
float3 white=float3(7.2,6.7,5.5);
float3 gold=float3(6.5,3.5,.65);
'''

MUZZLE = r'''
float fired=1.-step(10.,ShotAge);
float fade=lerp(1.,1.-smoothstep(.008,.065,ShotAge),fired);
float squeeze=smoothstep(.105,.265,Age);
float radius=lerp(lerp(.10,.74,smoothstep(0.,.09,Age)),.20,squeeze);
float edge=abs(d-radius);
float rim=(1.-smoothstep(.005,.005+aa,edge))*(.65+.35*sin(a*3.-Age*6.+Index));
float soft=exp(-edge*edge/.0065);
float inside=(1.-smoothstep(radius*.72,radius*.98,d));
float charge=smoothstep(.015,.10,Age)*(.55+.45*squeeze);
float core=exp(-d*d/.012)*charge;
float energy=inside*pow(saturate(.28+n*.8+fine*.25),1.5)*charge;
float3 rgb=white*(rim*.65+core*.9)+gold*(soft*.65+energy*.48);
float alpha=rim*.48+soft*.28+core*.5+energy*.24;
if(style<1.5) {
    // Complete circular outlines with several softly separated luminous bands.
    float inner=exp(-pow((d-radius*.83)/.045,2.));
    float outer=exp(-pow((d-radius*1.055)/.010,2.));
    float satin=inside*pow(saturate(.2+n*.85+fine*.35),1.2);
    float lace=pow(saturate(cos(a*4.+Index+d*8.-Age*8.)),6.)
        *exp(-pow((d-radius*.86)/.105,2.));
    rgb+=white*(inner*.55+outer*.48+lace*.85+satin*.80);
    alpha+=inner*.34+outer*.20+lace*.32+satin*.47;
} else if(style<2.5) {
    // Discrete drifting stars, with a continuous clean ring underneath.
    float dust=0.; float stars=0.;
    for(int i=0;i<36;++i) {
        float h=frac(sin(float(i)*71.31+Index*13.7)*173.17);
        float angle=float(i)*2.39996+Index*.81+Age*(.12+h*.35);
        float rr=radius*lerp(.25,1.08,frac(h*7.13));
        float2 delta=p-float2(cos(angle),sin(angle))*rr;
        float blink=.40+.60*pow(saturate(sin(Age*(11.+h*13.)+h*31.)),2.);
        dust+=(exp(-dot(delta,delta)/(.00025+h*.00055))
             +.28*exp(-dot(delta,delta)/(.002+h*.002)))*blink;
        stars+=(exp(-pow(delta.x/.005,2.)-pow(delta.y/.045,2.))
              +exp(-pow(delta.y/.005,2.)-pow(delta.x/.045,2.)))*blink*.45;
    }
    float grit=inside*pow(saturate(.15+fine*1.25),4.)*.70;
    rgb+=gold*(dust*2.0+grit+energy*.55)+white*stars*1.4;
    alpha+=dust*.85+stars*.55+grit*.45+energy*.25;
} else if(style<3.5) {
    // Fine light fibers inside the stable circular boundary; never distort it.
    float fiber=pow(saturate(cos(a*5.+d*15.-Age*18.+n*4.+Index)),7.);
    float fiber2=pow(saturate(cos(a*9.-d*12.+Age*9.+fine*3.)),12.);
    float veil=inside*pow(saturate(.15+n*1.2),1.1);
    float strands=(fiber*.8+fiber2*.35)*inside*smoothstep(.045,.13,d);
    rgb+=gold*veil*.65+white*(strands*1.20+veil*.42);
    alpha+=veil*.50+strands*.50;
} else {
    // Short needles of energy converge on the center; the base circle stays whole.
    float sector=floor((a+PI)*3.8197);
    float h=frac(sin(sector*31.73+Index*7.1)*179.7);
    float needle=pow(saturate(cos(a*7.+Index*.7+Age*12.)),45.)*smoothstep(.25,.70,n);
    float gate=smoothstep(radius*.35,radius*.6,d)*(1.-smoothstep(radius*.88,radius*1.09,d));
    float fleck=pow(saturate(.15+fine*1.25),4.)*gate;
    float surge=exp(-pow((Age-.075)/.035,2.))*.7+squeeze*.6;
    rgb+=white*(needle*gate*(1.2+surge)+core*surge*1.4)+gold*(fleck*1.2+energy*.65);
    alpha+=needle*gate*.55+fleck*.45+core*surge*.3+energy*.22;
}
float envelope=smoothstep(0.,.025,Age)*fade;
return float4(rgb*envelope,saturate(alpha)*envelope);
'''

RELEASE = r'''
float fired=1.-step(10.,ShotAge);
float t=max(ShotAge,0.);
float alive=(1.-smoothstep(.16,.235,t))*fired;
float charge=(1.-fired)*smoothstep(.015,.11,Age);
float chargeCloud=exp(-d*d/.10)*pow(saturate(n*.8+fine*.3),1.8);
float chargeCore=exp(-d*d/.012)*(.6+.4*smoothstep(.19,.34,Age));
float3 rgb=(white*chargeCore*.55+gold*chargeCloud*.40)*charge;
float alpha=(chargeCore*.35+chargeCloud*.20)*charge;
float pulse=exp(-pow((t-.025)/.024,2.))+.65*exp(-pow((t-.082)/.030,2.));
float core=exp(-d*d/.022)*pulse;
float cloud=exp(-d*d/.14)*pow(saturate(.18+n*.9+fine*.3),1.2)*pulse;
float burst=0.; float rings=0.; float dust=0.;
if(style<1.5) {
    for(int i=0;i<3;++i) {
        float age=t-float(i)*.022;
        float radius=lerp(.15,.51+float(i)*.135,saturate(age/.11));
        rings+=exp(-pow((d-radius)/(.009+aa),2.))*step(0.,age)*(1.-smoothstep(.04,.18,age));
    }
    burst=pow(saturate(cos(a*18.+n)),34.)*exp(-pow((d-(.14+t*2.4))/.15,2.))*(1.-smoothstep(.07,.19,t));
    rgb+=alive*(white*(rings*.55+burst*.65+core*1.7)+gold*cloud*.8);
    alpha+=alive*(rings*.34+burst*.36+core*.85+cloud*.28);
} else if(style<2.5) {
    for(int i=0;i<34;++i) {
        float h=frac(sin(float(i)*47.77)*177.31);
        float angle=float(i)*2.39996;
        float rr=.08+t*(1.7+h*3.0);
        float2 delta=p-float2(cos(angle),sin(angle))*rr;
        dust+=exp(-dot(delta,delta)/(.00012+h*.00028))*(1.-smoothstep(.08,.23,t));
    }
    rings=exp(-pow((d-(.2+t*2.8))/.012,2.))*(1.-smoothstep(.03,.10,t));
    rgb+=alive*(gold*(dust*3.2+cloud*1.4)+white*(core*1.8+rings*.4));
    alpha+=alive*(dust*.9+cloud*.40+core*.85+rings*.28);
} else if(style<3.5) {
    float fibers=pow(saturate(cos(a*8.+d*15.-t*27.+n*4.)),9.);
    float billow=exp(-pow((d-(.20+t*1.9))/.23,2.))*pow(saturate(.15+n*1.2),1.2);
    burst=fibers*billow;
    rings=exp(-pow((d-(.19+t*2.4))/.012,2.))*(1.-smoothstep(.06,.18,t));
    rgb+=alive*(white*(burst*1.5+core*1.7+rings*.35)+float3(2.1,1.8,1.15)*billow*.75);
    alpha+=alive*(burst*.62+core*.85+rings*.22+billow*.24);
} else {
    float sector=floor((a+PI)*4.45634);
    float h=frac(sin(sector*37.19)*133.71);
    float spikes=pow(saturate(cos(a*14.)),100.);
    burst=spikes*smoothstep(.10,.24,d)*(1.-smoothstep(.37+h*.2+t*.7,.56+h*.2+t*.7,d));
    float ringA=exp(-pow((d-(.18+t*3.9))/.009,2.))*(1.-smoothstep(.025,.12,t));
    float ringB=exp(-pow((d-(.13+max(0.,t-.050)*3.0))/.012,2.))*step(.050,t)*(1.-smoothstep(.09,.19,t));
    rgb+=alive*(white*(core*2.7+burst*1.6*(1.-smoothstep(.04,.12,t))+ringA*.45+ringB*.65)+gold*cloud*.65);
    alpha+=alive*(core*.95+burst*.64*(1.-smoothstep(.04,.12,t))+ringA*.3+ringB*.4+cloud*.25);
}
return float4(rgb,saturate(alpha));
'''

STREAK = r'''
float x=UV.x;
float y=abs(p.y);
float aaY=max(fwidth(y),.005);
float taper=pow(smoothstep(.01,.88,x),1.8)*(1.-smoothstep(.97,1.,x));
float shaft=(1.-smoothstep(.008,.008+aaY,y))*taper;
float tip=exp(-pow((x-.92)/.043,2.)-pow(y/.11,2.));
float sheath=exp(-y*y/.016)*taper;
float detail=0.;
if(style<1.5) {
    detail=exp(-pow((y-.045)/.008,2.))*taper*.4;
} else if(style<2.5) {
    detail=pow(saturate(sin(x*112.)),20.)*exp(-pow((y-.08)/.035,2.))*taper*.75;
} else if(style<3.5) {
    detail=exp(-pow((p.y-.045*sin(x*19.))/.008,2.))*taper*.5
        +exp(-pow((p.y+.055*sin(x*21.+1.))/.008,2.))*taper*.4;
    sheath*=1.5;
} else {
    float headW=max(0.,(.98-x)*1.35);
    detail=(1.-smoothstep(headW,headW+aaY,y))*smoothstep(.85,.9,x)*(1.-smoothstep(.965,.98,x))*.8;
}
float3 rgb=white*(shaft+tip*1.4)+gold*(sheath*.55+detail);
return float4(rgb,saturate(shaft*.72+tip*.8+sheath*.20+detail*.5));
'''

IMPACT = r'''
float t=max(Age,0.);
float life=1.-smoothstep(.13,.20,t);
float core=exp(-d*d/.032)*exp(-t*16.);
float cloud=exp(-d*d/.26)*pow(saturate(n*.95+fine*.4),1.8)*exp(-t*9.);
float spikes=0.; float layers=0.; float dust=0.;
if(style<1.5) {
    for(int i=0;i<3;++i) {
        float r=.15+float(i)*.14+t*(1.8-float(i)*.3);
        layers+=exp(-pow((d-r)/(.012+aa),2.))*exp(-t*(11.+float(i)*3.));
    }
    spikes=pow(saturate(cos(a*18.+.4)),55.)*smoothstep(.12,.25,d)*(1.-smoothstep(.47+t,.75+t,d))*exp(-t*16.);
} else if(style<2.5) {
    for(int i=0;i<30;++i) {
        float h=frac(sin(float(i)*49.1)*133.17);
        float angle=float(i)*2.39996;
        float2 delta=p-float2(cos(angle),sin(angle))*(.13+h*.22+t*(1.5+h));
        dust+=exp(-dot(delta,delta)/(.00018+h*.0005))*exp(-t*7.);
    }
    cloud*=1.4;
} else if(style<3.5) {
    spikes=pow(saturate(cos(a*27.+d*22.-t*12.+n*1.5)),25.)
        *exp(-pow((d-(.30+t*1.4))/.25,2.))*exp(-t*8.);
    cloud*=1.55;
} else {
    float h=frac(sin(floor((a+PI)*4.45634)*43.3)*171.7);
    spikes=pow(saturate(cos(a*14.)),100.)*smoothstep(.12,.22,d)
        *(1.-smoothstep(.44+h*.21+t,.67+h*.21+t,d))*exp(-t*12.);
    layers=exp(-pow((d-(.16+t*4.1))/.013,2.))*exp(-t*13.);
    core*=1.55;
}
float3 rgb=white*(core*2.7+spikes*1.2+layers*.6)+gold*(cloud*.8+dust*2.5);
return float4(rgb*life,saturate(core+spikes*.75+layers*.36+cloud*.35+dust*.85)*life);
'''


FLOW_COMMON = r'''
const float PI=3.14159265;
float2 p=(UV-.5)*2.;
float d=length(p);
float a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.55,.0025);
float n=Texture2DSample(Flow,FlowSampler,UV*3.+float2(Age*.28,-Age*.75)+Index*.13).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*8.+float2(-Age*.8,Age*.3)).g;
float3 white=float3(9.,8.0,5.5);
float3 gold=float3(5.5,2.6,.28);
'''

FLOW_MUZZLE = r'''
float fired=1.-step(10.,ShotAge);
float shrink=smoothstep(.14,.32,Age);
float radius=lerp(lerp(.12,.79,smoothstep(0.,.075,Age)),.235,shrink);
float edge=abs(d-radius);
float phase=frac(a/(2.*PI)-Age*(2.4+Index*.11)+Index*.19);
float arc=exp(-phase*11.)+.72*exp(-frac(phase+.52)*14.);
float head=exp(-pow(min(phase,1.-phase)/.021,2.));
float rim=exp(-pow(edge/(.007+aa),2.));
float band=exp(-pow(edge/(.020+arc*.025),2.))*arc;
float haze=exp(-pow(edge/.14,2.))*arc*lerp(.55,1.25,n);
float inner=exp(-pow((d-radius*.84)/.008,2.))*pow(saturate(cos(a*2.-Age*12.+Index)),3.);
float spiral=pow(saturate(cos(a*2.+d*12.-Age*21.+Index*1.7)),16.);
float feed=spiral*smoothstep(.055,.13,d)*(1.-smoothstep(radius*.68,radius*.95,d))
    *smoothstep(.055,.15,Age)*(1.-smoothstep(.29,.355,Age));
float flecks=pow(saturate(fine*1.35),9.)*exp(-pow((d-radius)/.11,2.))*.35;
float kernel=exp(-d*d/.0016)*smoothstep(.24,.35,Age);
float preFade=1.-fired*smoothstep(0.,.055,ShotAge);
float envelope=smoothstep(0.,.035,Age)*preFade;
float3 rgb=white*(rim*.30+band*.85+head*haze*.8+kernel*1.5)
    +gold*(haze*1.35+band*.7+inner*.8+feed*1.1+flecks);
float alpha=rim*.40+band*.60+haze*.28+inner*.32+feed*.48+flecks*.30+kernel*.65;
return float4(rgb*envelope,saturate(alpha)*envelope);
'''

FLOW_RELEASE = r'''
float fired=1.-step(10.,ShotAge);
float t=max(0.,ShotAge);
float life=(1.-smoothstep(.17,.245,t))*fired;
float r1=.12+saturate(t/.12)*.72;
float r2=.13+saturate((t-.055)/.13)*.80;
float wave1=exp(-pow((d-r1)/(.014+aa),2.))*(1.-smoothstep(.035,.16,t));
float wave2=exp(-pow((d-r2)/(.022+aa),2.))*smoothstep(.045,.065,t)*(1.-smoothstep(.12,.23,t));
float rimHaze=exp(-pow((d-r1)/.065,2.))*.25+exp(-pow((d-r2)/.075,2.))*.18*step(.055,t);
float blast=0.;
for(int i=0;i<13;++i) {
    float h=frac(sin(float(i)*31.77)*131.73);
    float angle=float(i)*2.39996;
    float2 dir=float2(cos(angle),sin(angle));
    float axial=dot(p,dir);
    float across=abs(p.x*dir.y-p.y*dir.x);
    float tip=.12+t*(2.5+h*3.);
    blast+=exp(-pow(across/(.006+h*.009+aa),2.))
        *smoothstep(tip-.19-h*.12,tip-.04,axial)*(1.-smoothstep(tip,tip+.035,axial));
}
float pulse=exp(-pow((t-.018)/.019,2.))+.7*exp(-pow((t-.072)/.021,2.));
float core=exp(-d*d/.008)*pulse;
float3 rgb=white*(core*2.+wave1*.85+wave2+blast*.8)+gold*(rimHaze+blast*.6);
return float4(rgb*life,saturate(core*.9+wave1*.50+wave2*.6+blast*.45+rimHaze*.20)*life);
'''

FLOW_PATH = r'''
float x=UV.x;
float fired=1.-step(10.,ShotAge);
float3 rgb=0.; float alpha=0.;
if(fired<.5) {
    float energy=0.; float glow=0.;
    for(int i=0;i<2;++i) {
        float phase=float(i)*3.14+Index*.9;
        float center=sin(x*4.-Age*12.+phase)*(.28*(1.-x));
        float dy=p.y-center;
        float head=frac(Age*3.3+float(i)*.31+Index*.07);
        float taper=smoothstep(head-.44,head-.07,x)*(1.-smoothstep(head,head+.025,x));
        energy+=exp(-pow(dy/(.008+aa),2.))*taper;
        glow+=exp(-pow(dy/.135,2.))*taper*pow(saturate(.28+n*.8+fine*.3),1.4);
    }
    float life=smoothstep(.045,.105,Age)*(1.-smoothstep(.31,.375,Age));
    float bounds=smoothstep(.01,.08,x)*(1.-smoothstep(.97,1.,x));
    rgb=(white*energy*.45+gold*glow*1.25)*life*bounds;
    alpha=(energy*.40+glow*.40)*life*bounds;
} else {
    float t=max(0.,ShotAge);
    float head=t*6000./max(PathLength,1.);
    float trail=smoothstep(head-.48,head-.07,x)*(1.-smoothstep(head,head+.012,x));
    float beamCore=exp(-pow(p.y/(.018+aa),2.));
    float shoulders=exp(-pow((abs(p.y)-.16)/.009,2.));
    float pulse=exp(-pow((x-head)/.027,2.))*exp(-p.y*p.y/.034);
    float residue=exp(-t*24.)*smoothstep(.005,.04,t)*smoothstep(.02,.12,x)*(1.-smoothstep(.82,1.,x));
    float shred=pow(saturate(n*.7+fine*.6),3.)*exp(-p.y*p.y/.14)*residue;
    float bounds=smoothstep(0.,.012,x)*(1.-smoothstep(.985,1.,x));
    float life=1.-smoothstep(.085,.17,t);
    rgb=(white*(beamCore*trail*1.5+pulse*2.+shoulders*residue*.18)+gold*(shred*1.4+beamCore*residue*.10))*life*bounds;
    alpha=(beamCore*trail*.80+pulse*.80+shoulders*residue*.20+shred*.35+beamCore*residue*.10)*life*bounds;
}
return float4(rgb,saturate(alpha));
'''

FLOW_STREAK = r'''
float x=UV.x;
float width=abs(p.y);
float taper=smoothstep(.01,.90,x)*(1.-smoothstep(.975,1.,x));
float shaft=exp(-pow(width/(.014+aa),2.))*taper;
float tip=exp(-pow((x-.92)/.048,2.)-pow(width/.08,2.));
float halo=exp(-width*width/.018)*taper;
float ridge=exp(-pow((width-.06)/.010,2.))*pow(taper,2.)*.40;
return float4(white*(shaft*.8+tip*1.5)+gold*(halo*.45+ridge),
    saturate(shaft*.65+tip*.8+halo*.16+ridge*.45));
'''

FLOW_IMPACT = r'''
float t=max(0.,Age);
float2 q=float2((UV.x-.32)*2.,p.y);
float core=exp(-dot(q,q)/.008)*exp(-t*25.);
float shafts=0.; float haze=0.;
for(int i=0;i<16;++i) {
    float h=frac(sin(float(i)*51.7)*173.31);
    float angle=lerp(-1.32,1.32,h);
    if(i<3) angle+=PI;
    float2 dir=float2(cos(angle),sin(angle));
    float axial=dot(q,dir);
    float lateral=abs(q.x*dir.y-q.y*dir.x);
    float tip=.07+t*(2.6+h*3.2);
    float shape=smoothstep(tip-.12-h*.15,tip-.025,axial)*(1.-smoothstep(tip,tip+.035,axial));
    shafts+=exp(-pow(lateral/(.006+h*.010+aa),2.))*shape;
    haze+=exp(-pow(lateral/(.028+h*.03),2.))*shape*.3;
}
float ring=exp(-pow((length(q)-(.08+t*3.4))/.015,2.))*exp(-t*16.);
float mist=exp(-pow((q.x-.16)/.4,2.)-pow(q.y/.24,2.))
    *pow(saturate(n*.9+fine*.45),3.)*exp(-t*15.);
float fade=1.-smoothstep(.12,.20,t);
float3 rgb=white*(core*3.+shafts*1.4+ring*.7)+gold*(haze*1.1+mist*.7);
return float4(rgb*fade,saturate(core*.95+shafts*.65+ring*.4+haze*.25+mist*.24)*fade);
'''


def author(out):
    out = Path(out)
    project = Path(__file__).resolve().parents[2]
    protected = list((project/'Content/TopDown/Characters/Sparrow/Materials').glob('M_SparrowSharp*.uasset'))
    hashes = lambda: {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before = hashes()
    texture = unreal.load_asset(NOISE)
    assert texture, NOISE
    lib = unreal.MaterialEditingLibrary
    rows = []
    flow_study = os.environ.get('SPARROW_SHARP_FLOW_STUDY') == '1'
    designs = {5: '광류 응축 · 전방 파열'} if flow_study else DESIGNS
    parts = [('Muzzle', FLOW_MUZZLE), ('Release', FLOW_RELEASE), ('Streak', FLOW_STREAK),
             ('Impact', FLOW_IMPACT), ('Flow', FLOW_PATH)] if flow_study else [
                 ('Muzzle', MUZZLE), ('Release', RELEASE), ('Streak', STREAK), ('Impact', IMPACT)]
    for style in designs:
        for part, body in parts:
            path = f'{FOLDER}/M_SharpT{style}{part}'
            code = ((FLOW_COMMON if flow_study else COMMON)+body).replace('STYLE', str(float(style)))
            signature = hashlib.sha256(code.encode()).hexdigest()
            material = unreal.load_asset(path)
            reused = material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'SharpDetailHash') == signature
            if not reused:
                if material is None:
                    folder, name = path.rsplit('/', 1)
                    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
                assert material, path
                lib.delete_all_material_expressions(material)
                material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
                material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
                material.set_editor_property('two_sided', True)
                def node(kind, **props):
                    obj = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
                    for key, value in props.items(): obj.set_editor_property(key, value)
                    return obj
                shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
                sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture)}
                params = [('Age', 0.), ('ShotAge', 100.), ('Index', 0.)]
                if flow_study: params.append(('PathLength', 450.))
                for param, default in params:
                    sources[param] = node('ScalarParameter', parameter_name=param, default_value=default)
                inputs = []
                for name in sources:
                    pin = unreal.CustomInput(); pin.set_editor_property('input_name', name); inputs.append(pin)
                shader.set_editor_property('inputs', inputs)
                for name, source in sources.items(): assert lib.connect_material_expressions(source, '', shader, name)
                for prop, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                                       (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))]:
                    mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
                    assert lib.connect_material_expressions(shader, '', mask, '')
                    assert lib.connect_material_property(mask, '', prop)
                lib.recompile_material(material)
                unreal.EditorAssetLibrary.set_metadata_tag(material, 'SharpDetailHash', signature)
                assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), path
            rows.append({'style':style,'part':part,'path':path,'hash':signature,'reused':bool(reused)})
    assert before == hashes(), 'Production S materials changed'
    result = {'passed':True,'version':1 if flow_study else VERSION,'designs':designs,'materials':rows,'source_texture':NOISE,
              'production_materials_unchanged':True,'default_style':0,'gameplay_changed':False}
    (out/'sharp-detail-materials.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
