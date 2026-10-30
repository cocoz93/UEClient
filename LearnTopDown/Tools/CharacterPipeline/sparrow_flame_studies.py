"""Dedicated D studies, adopted V3, D route feathers and ascended W finisher surfaces."""
import hashlib
import json
import os
from pathlib import Path

import unreal

ROOT = '/Game/TopDown/Characters/Sparrow/Previews/FlameStudies20261026'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
RAYS = '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays'
LABELS = {'D1': '황금 깃털창', 'D2': '나선 화염 관통', 'D3': '광편 압력 사격',
          'V1': '타오르는 화염 외투', 'V2': '유동 광염 코로나', 'V3': '어깨와 팔의 화염깃'}

COMMON = r'''
float2 p=(UV-.5)*2.;
float x=UV.x;
float r=length(p),a=atan2(p.y,p.x);
float aa=max(length(fwidth(p))*.65,.003);
float n=Texture2DSample(Flow,FlowSampler,UV*float2(2.2,2.8)+float2(-Age*.71,Index*.137)).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*float2(6.1,5.4)+float2(-Age*1.37,Index*.279)).g;
float3 gold=float3(1.65,.52,.035),warm=float3(3.2,1.65,.24),white=float3(4.6,3.6,1.7);
float3 rgb=0.;float alpha=0.;
float fired=1.-step(10.,ShotAge),st=max(0.,ShotAge);
'''

FEATHER = r'''
float bend=sin(x*3.14159265)*.22*sin(Index*1.7);
float y=p.y-bend;
float envelope=pow(saturate(sin(x*3.14159265)),.65);
float width=.50*envelope*(.25+.75*x);
width*=1.-.18*pow(saturate(cos(x*57.-abs(y)*22.)),7.);
float inside=1.-smoothstep(width-aa,width+aa,abs(y));
float shaft=exp(-pow(y/(.010+aa),2.))*envelope;
float barbs=pow(saturate(cos(x*62.-abs(y)*24.)),18.);
float cut=smoothstep(.20,.65,n*.8+fine*.3);
float tissue=inside*(.20+n*.42+fine*.10)*(1.-barbs*.70)*(.35+cut*.65);
float edge=exp(-pow((abs(y)-width)/(.012+aa),2.))*envelope;
float travel=pow(saturate(sin(x*13.-Age*19.+Index)),10.);
float streaming=pow(saturate(sin(x*19.-Age*20.+n*2.6)),4.);
rgb=gold*tissue*1.65+warm*inside*streaming*.45+white*(shaft*.18+edge*travel*.15);
alpha=tissue*.55+inside*streaming*.22+shaft*.20+edge*.11;
'''

SPIRAL = r'''
float taper=pow(saturate(sin(x*3.14159265)),.65);
float bands=0.,seams=0.;
for(int i=0;i<3;++i) {
 float phase=x*5.8-Age*18.+Index*1.4+i*2.094;
 float depth=.5+.5*cos(phase);
 float curve=sin(phase)*(.18+.40*taper);
 float distance=abs(p.y-curve);
 float width=.07+.20*depth;
 float erode=smoothstep(.15,.68,n*.75+fine*.35);
 float tissue=exp(-pow(distance/width,2.))*(.40+erode*.60)*depth;
 bands+=tissue;
 seams+=exp(-pow((distance-width*.45)/(.009+aa),2.))*depth*erode*.35;
}
float head=exp(-pow((p.x-.6)/.18,2.)-pow(p.y/.10,2.));
rgb=(gold*bands*1.45+warm*bands*.85+white*seams*.42)*taper+warm*head;
alpha=(bands*.72+seams*.28)*taper+head*.35;
'''

WAKE = r'''
float curve=sin(x*3.14159265)*.55;
float d=p.y-curve;
float taper=pow(saturate(sin(x*3.14159265)),.7);
float broad=exp(-pow(d/.15,2.))*taper;
float crest=exp(-pow((d+.035)/(.012+aa),2.))*taper;
float erosion=smoothstep(.13,.67,n*.7+fine*.45);
rgb=gold*broad*(.25+erosion)+warm*crest*erosion*.8;
alpha=broad*.42*erosion+crest*.30*erosion;
'''

SHARD = r'''
float width=.60*pow(saturate(sin(x*3.14159265)),.8)*(1.-x*.72);
float d=abs(p.y)-width;
float shape=1.-smoothstep(-aa,aa,d);
float bevel=exp(-pow(d/(.014+aa),2.));
float seam=exp(-pow((p.y-.06*sin(x*4.))/(.010+aa),2.));
float face=.24+.36*step(0.,p.y)+n*.18;
float flash=pow(saturate(sin(x*11.-Age*17.+Index)),8.);
rgb=gold*shape*face*.7+warm*shape*flash*.95+white*(bevel*flash*.12+seam*shape*.15);
alpha=shape*(.24+flash*.28)+bevel*flash*.14+seam*shape*.13;
'''

BURST = r'''
float pulse=exp(-st*24.)+.48*exp(-pow((st-.05)/.018,2.));
float core=exp(-r*r/.035)*pulse;
float torn=pow(saturate(cos(a*5.-r*11.+st*23.+n*2.)),4.);
torn*=exp(-pow((r-(.22+st*1.8))/.22,2.))*(.25+n*.65);
float shards=0.;
for(int i=0;i<20;++i) {
 float h=frac(sin(float(i)*48.12)*1737.4);float angle=i*2.399963;
 float2 axis=float2(cos(angle),sin(angle));float2 q=p-axis*(.08+st*(2.+h*2.5));
 float axial=dot(q,axis),lateral=abs(q.x*axis.y-q.y*axis.x);
 shards+=exp(-pow(axial/(.045+h*.055),2.)-pow(lateral/(.008+h*.012+aa),2.));
}
float charge=exp(-r*r/.04)*Progress;
rgb=lerp(warm*charge,white*(core*.70+shards*.4)+gold*torn*1.5,fired);
alpha=lerp(charge*.35,core*.52+shards*.52+torn*.45,fired);
'''

FIRE_COMMON = r'''
float tongueMass=0.,bright=0.,fringe=0.;
for(int i=0;i<4;++i) {
 float j=float(i);
 float h=frac(sin(j*13.7+Index*4.13)*1773.6);
 float begin=.03+j*.03,end=.80+h*.18;
 float u=saturate((x-begin)/(end-begin));
 float tip=pow(saturate(1.-u),.82);
 float bend=sin(u*4.7-Age*(2.2+h)+Index*.83+j)*.31*u;
 float path=(j-1.5)*.19*tip+bend;
 float wave=sin(x*18.-Age*7.+j*2.8)*.035*x;
 float width=(.24+h*.11)*tip*(.65+.35*sin(u*3.14159));
 float d=abs(p.y-path-wave);
 float support=smoothstep(begin,begin+.08,x)*(1.-smoothstep(end-.10,end,x));
 float surface=exp(-pow(d/max(.007,width),2.))*support;
 float grain=saturate(n*.72+fine*.40);
 float erosion=smoothstep(.14+u*.22,.75,grain+sin(x*39.-Age*11.+j)*.14);
 float flow=pow(saturate(sin(x*13.-Age*(7.+h*2.)+j*2.3+grain*3.)),3.);
 tongueMass+=surface*(.38+erosion*.62);
 bright+=surface*flow*erosion*(1.-u*.45);
 fringe+=exp(-pow((d-width*.73)/(.012+aa),2.))*support*erosion*.18;
}
float ember=0.;
for(int k=0;k<7;++k) {
 float h=frac(sin(k*32.7+Index*4.7)*1732.1);
 float t=frac(Age*(.32+h*.18)+h);
 float2 q=float2(x,p.y)-float2(.4+t*.58,(h-.5)*1.4+sin(t*7.+h)*.12);
 ember+=exp(-dot(q,q)/(.00014+h*.00030))*sin(t*3.14159);
}
'''

MANTLE = FIRE_COMMON + r'''
rgb=gold*tongueMass*1.05+warm*bright*1.15+white*fringe*.45+warm*ember*.9;
alpha=tongueMass*.62+bright*.20+fringe*.25+ember*.5;
'''

CORONA = r'''
float2 q=p;
q.y-=sin(x*3.14159)*.42;
float width=(.06+.30*pow(saturate(sin(x*3.14159)),.8))*(1.-x*.5);
float erode=smoothstep(.16+x*.20,.72,n*.72+fine*.45);
float face=exp(-pow(q.y/width,2.))*pow(saturate(sin(x*3.14159)),.6);
float current=pow(saturate(sin(x*17.-Age*11.+n*3.+Index)),4.);
float split=exp(-pow((abs(q.y)-width*.72)/(.012+aa),2.))*erode;
float tip=exp(-pow((p.x-.30)/.16,2.)-pow(q.y/.12,2.));
rgb=gold*face*(.45+erode)*1.4+warm*face*current*1.1+white*split*.23+warm*tip*.65;
alpha=face*(.40+erode*.5)+split*.28+tip*.35;
'''

CREST = FIRE_COMMON + r'''
float serrate=pow(saturate(cos(p.y*21.+x*13.-Age*5.)),9.)*tongueMass;
rgb=gold*tongueMass*1.15+warm*bright*1.25+white*(fringe*.6+serrate*.13)+warm*ember;
alpha=tongueMass*.68+bright*.23+fringe*.25+ember*.5;
'''

EMBER = r'''
float shape=exp(-pow(p.x/.25,2.)-pow(p.y/.12,2.));
float core=exp(-pow(p.x/.08,2.)-pow(p.y/.055,2.));
float split=exp(-pow((p.y-.18*sin(p.x*5.+Age*4.))/.06,2.))*exp(-pow((p.x+.20)/.35,2.));
rgb=gold*shape+warm*split*.65+white*core*.35;
alpha=shape*.55+core*.35+split*.35;
'''

D_ROUTE_FEATHER = r'''
float camber=sin(x*3.14159265)*.15+x*x*.045;
float y=p.y-camber;
float envelope=pow(saturate(sin(x*3.14159265)),.82);
float width=.33*envelope*(y>0.?1.:.76);
float barbPhase=x*15.-abs(y)/max(width,.025)*.73;
float barb=pow(.5+.5*cos(barbPhase*6.2831853),5.);
float notch=.5+.5*sin(x*73.+Index*5.1)*sin(x*41.+1.7);
float face=1.-smoothstep(width-aa,width+aa,abs(y)+(1.-notch)*.035);
float roots=smoothstep(.035,.12,x)*(1.-smoothstep(.88,1.,x));
float tissue=face*roots*(.40+.22*barb)*(.60+n*.40);
float stem=exp(-abs(y)/(.006+aa*.35))*smoothstep(0.,.04,x)*(1.-smoothstep(.90,1.,x));
float lines=face*roots*barb*.45;
float coverage=tissue+lines*.30+stem*.65;
alpha=min(.82,coverage)*smoothstep(0.,.045,Age);
rgb=(float3(1.10,.52,.085)*tissue+float3(1.65,.93,.22)*lines*.30+float3(3.2,2.35,.90)*stem*.65)/max(coverage,.035);
'''

V_ENTRY_SHAFT = r'''
// World height gives actual horizontal gaps even when the camera-facing plane rotates.
float h=clamp(Position.z-Center.z+525.,0.,1049.999);
int bandIndex=(int)floor(h/70.);
int order=(bandIndex*7+3)%15;
float endTime=.25+(float)order/14.*.24;
float erode=saturate((Age-(endTime-.18))/.18);
float gap=12.*smoothstep(.05,.80,erode);
float within=frac(h/70.)*70.;
float edgeMask=1.-smoothstep(34.-gap,36.-gap,abs(within-35.));
float alive=1.-smoothstep(.80,1.,erode);
float width=lerp(.055+.018*frac(bandIndex*.381),.009,pow(erode,1.45));
float spine=exp(-pow(p.y/(width+aa*.35),2.));
float inner=exp(-pow(p.y/max(width*2.6,.012),2.));
float along=smoothstep(.0,.015,x)*(1.-smoothstep(.985,1.,x));
float silhouette=edgeMask*alive*along;
rgb=(white*spine*.68+warm*inner*(.38+n*.16))*silhouette;
alpha=(spine*.88+inner*.34)*silhouette;
'''

V_ENTRY_IMPACT = r'''
float t=max(0.,Age-.66);
float chips=0.,rays=0.;
for(int i=0;i<23;++i) {
 float h=frac(sin(i*37.7+2.4)*1773.6),angle=i*2.399963;
 float2 axis=float2(cos(angle),sin(angle));
 float2 q=p-axis*(.045+t*(1.4+h*2.1));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 chips+=exp(-pow(along/(.025+h*.055),2.)-pow(side/(.009+h*.014+aa),2.));
 rays+=exp(-pow(side/(.009+aa),2.))*exp(-pow(along/(.055+h*.080),2.));
}
float core=exp(-dot(p,p)/.065)*exp(-t*27.);
float2 polar=float2(a/6.2831853+.5,saturate(r/(.20+t*2.1)));
float3 tissue=Texture2DSample(Rays,RaysSampler,polar+float2(.07,-Age*.21)).rgb;
float radius=.15+min(t,.5)*1.35;
float crown=exp(-pow((r+(n-.5)*.10-radius)/.16,2.))*(.25+tissue.b*.75)*exp(-t*3.7);
float residual=exp(-pow((r-.42)/.20,2.))*smoothstep(.22,.72,n*.65+tissue.r*.4)*exp(-t*3.5);
float burst=exp(-t*6.);
float contactGlow=exp(-dot(p,p)/.30)*(.70+tissue.b*.30)*exp(-t*3.0);
rgb=white*(core*1.6+chips*.35*burst)+warm*(rays*.75*burst+contactGlow*1.15)+gold*(crown*1.9+residual*1.15);
alpha=core*.96+chips*.62*burst+rays*.42*burst+crown*.74+residual*.55+contactGlow*.55;
'''

FINISHER_WING = r'''
float curve=sin(x*3.14159265)*.32;
float y=p.y-curve;
float envelope=pow(saturate(sin(x*3.14159265)),.70);
float width=.36*envelope*(.52+.48*x);
float vane=exp(-pow(y/max(width,.008),4.))*envelope;
float grain=.35+smoothstep(.18,.78,n*.70+fine*.35)*.65;
float plume=pow(saturate(cos(x*40.-abs(y)*24.)),8.);
float streaming=pow(saturate(sin(x*15.-Age*24.+Index*.8+n*2.)),5.);
float spine=exp(-pow(y/(.017+aa),2.))*envelope;
float glow=exp(-pow(y/max(width*1.35,.01),2.))*envelope;
rgb=gold*vane*grain*1.20+warm*(vane*streaming*.90+glow*.20)+white*(spine*.18+vane*plume*streaming*.12);
alpha=vane*grain*.60+spine*.25+glow*.12;
'''

D_CHARGE_VANE = r'''

float bend=sin(x*3.14159)*(.42-.32*Progress)*sin(Index*1.7+Age*2.);
float y=p.y-bend;
float span=pow(saturate(sin(x*3.14159)),.65);
float w=(.32+.14*sin(Index*1.9))*span*(.35+.65*(1.-x));
float3 silk=Texture2DSample(Rays,RaysSampler,float2(frac(x*.8-Age*1.3+Index*.17),p.y*.8+.5)).rgb;
float ribbon=exp(-pow(y/max(.008,w),2.));
float flowing=smoothstep(.18,.73,n*.55+silk.b*.65+fine*.15);
float tear=smoothstep(.08,.35,1.-x)*smoothstep(0.,.07,x);
float edge=exp(-pow((y-w*.2)/(.012+aa),2.))*span;
float beam=pow(saturate(sin(x*9.-Age*22.+Index*1.3)),6.);
float mass=ribbon*(.25+flowing*.75)*tear;
float glow=exp(-pow(y/max(.01,w*2.2),2.))*span;
alpha=saturate(mass*.65+edge*.20*beam+glow*.10);
rgb=lerp(float3(1.15,.35,.02),float3(4.5,2.6,.45),saturate(flowing*.7+beam*.25))+white*edge*beam*.18;

'''

D_CHARGE_CORE = r'''

float span=pow(saturate(sin(x*3.14159)),.8);
float width=.055+.075*(1.-Progress);
float beam=exp(-pow(p.y/width,2.))*span;
float rays=Texture2DSample(Rays,RaysSampler,float2(frac(x-Age*2.1),UV.y)).b;
float curl=exp(-pow((abs(p.y)-.2*sin(x*3.14159)*(1.-Progress))/.025,2.))*span;
float charged=pow(Progress,5.);
alpha=beam*(.25+charged*.6)+curl*rays*.35;
rgb=lerp(float3(1.5,.55,.035),float3(7.0,4.3,1.1),charged)+warm*rays*.5;

'''

V_ENTRY_COLUMN = r'''
float3 q=Position-Center;
float depth=saturate(.5-q.z/max(2.*HalfHeight,1.));
float angle=atan2(q.y,q.x)/6.2831853+.5;
float grain=Texture2DSample(Flow,FlowSampler,float2(angle*16.,depth*1.6-Age*1.8)).g;
float3 tissue=Texture2DSample(Rays,RaysSampler,float2(frac(angle*3.),frac(depth*.50-Age*.7))).rgb;
float side=1.-smoothstep(.85,.99,abs(normalize(Normal).z));
float front=saturate(abs(dot(normalize(Normal),normalize(View))));
float core=smoothstep(.28,.88,front);
float softSide=smoothstep(.015,.48,front);
float lower=smoothstep(0.,.008,depth)*(1.-smoothstep(.855,1.,depth));
float impact=exp(-pow((Age-.665)/.060,2.));
float downward=.82+.18*pow(saturate(sin(depth*15.-Age*39.+grain*.85)),3.);
float fibres=pow(saturate(.5+.5*sin(angle*177.+grain*.45)),14.)*(.25+tissue.b*.75);
float3 rim=float3(1.15,.43,.025)*(1.+tissue.r*.18);
float3 center=float3(.95,.43,.050)*(.88+grain*.12)*downward;
float3 color=lerp(rim,center,core)+float3(2.2,1.25,.24)*(fibres*.46+impact*.14);
// Low-opacity front shell plus sparse brighter fibres, instead of a flat HDR cream fill.
float opacity=(lerp(.12,.24,core)+impact*.025)*softSide;
float visible=side*lower*Strength;
return float4(color*visible,saturate(opacity)*visible);
'''

V_ENTRY_SCATTER = r'''
float t=max(0.,Age-.66);
float flecks=0.,streaks=0.;
for(int j=0;j<35;++j) {
 float seed=frac(sin(j*19.13+4.8)*2733.7),angle=j*2.399963;
 float2 axis=float2(cos(angle),sin(angle));
 float2 q=p-axis*(.10+t*(.65+seed*1.45));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 flecks+=exp(-pow(along/(.018+seed*.032),2.)-pow(side/(.008+aa),2.));
 streaks+=exp(-pow(along/(.040+seed*.045),2.)-pow(side/(.005+aa),2.))*.35;
}
rgb=(warm*flecks+gold*streaks*.85)*exp(-t*3.6);
alpha=(flecks*.68+streaks*.37)*exp(-t*2.5);
'''


V_ENTRY_PRELUDE = r'''
float t=max(0.,Age-.08);
float wave=exp(-pow((r-(.12+t*1.7))/.045,2.))*(.45+n*.55);
float core=exp(-dot(p,p)/.014)*exp(-t*19.);
float dust=pow(saturate(fine*1.8-.52),4.)*exp(-pow((r-.31)/.15,2.));
rgb=warm*wave*.42+white*core*.65+gold*dust*.30;
alpha=wave*.35+core*.60+dust*.20;
'''

V_REVEAL_FLASH = r'''
float t=max(0.,Age-1.16);
float core=exp(-dot(p,p)/.075)*exp(-t*28.);
float aura=exp(-dot(p,p)/.26)*(.30+n*.45)*exp(-t*17.);
float rays=0.,shards=0.;
for(int j=0;j<20;j++) {
 float h=frac(sin(j*31.81+2.7)*2733.7),angle=j*2.399963;
 float2 axis=float2(cos(angle),sin(angle));
 float2 q=p-axis*(.05+t*(1.8+h*2.5));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 rays+=exp(-pow(side/(.009+aa),2.))*exp(-pow(along/(.05+h*.11),2.))*exp(-t*14.);
 shards+=exp(-pow(side/(.013+aa),2.)-pow(along/(.020+h*.035),2.))*exp(-t*7.);
}
rgb=white*core*1.75+warm*(rays*.8+shards*.55)+gold*aura*1.15;
alpha=core*.95+rays*.55+shards*.56+aura*.56;
'''

D_CHARGE_RELEASE = r'''

float span=smoothstep(.0,.07,x)*(1.-smoothstep(.68,1.,x));
float y=p.y-sin(x*7.-st*12.)*.07*(1.-x);
float core=exp(-pow(y/.035,2.))*span;
float swept=exp(-pow(y/(.06+.25*(1.-x)),2.))*span;
float erode=smoothstep(.24+st*1.3,.76,n*.7+fine*.4);
float current=pow(saturate(sin(x*14.-st*44.)),3.);
alpha=(swept*erode*.7+core*.5)*(1.-smoothstep(.04,.22,st));
rgb=lerp(float3(1.3,.40,.015),float3(8.,5.,1.0),saturate(core*.8+current*.35));

'''

END = r'''
float frame=smoothstep(0.,.02,UV.x)*(1.-smoothstep(.98,1.,UV.x))*smoothstep(0.,.02,UV.y)*(1.-smoothstep(.98,1.,UV.y));
return float4(rgb*Strength*frame,saturate(alpha)*Strength*frame);
'''


def author(out, v_entry_only=False):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(NOISE)
    assert texture, NOISE
    rays = unreal.load_asset(RAYS)
    assert rays, RAYS
    rows = []
    for name, body in [('FlameFeather', FEATHER), ('FlameSpiral', SPIRAL), ('FlameWake', WAKE),
                       ('FlameShard', SHARD), ('FlameShotBurst', BURST), ('FlameMantle', MANTLE),
                       ('FlameCorona', CORONA), ('FlameCrest', CREST), ('FlameEmber', EMBER),
                       ('DRouteFeather', D_ROUTE_FEATHER), ('VEntryShaft', V_ENTRY_SHAFT),
                       ('VEntryImpact', V_ENTRY_IMPACT), ('FinisherWing', FINISHER_WING),
                       ('DChargeVane', D_CHARGE_VANE), ('DChargeCore', D_CHARGE_CORE),
                       ('VEntryColumn', V_ENTRY_COLUMN), ('VEntryScatter', V_ENTRY_SCATTER),
                       ('VEntryPrelude', V_ENTRY_PRELUDE), ('VRevealFlash', V_REVEAL_FLASH),
                       ('DChargeRelease', D_CHARGE_RELEASE)]:
        if v_entry_only and not name.startswith('V'):
            continue
        code = body if name == 'VEntryColumn' else COMMON+body+END
        digest = hashlib.sha256(code.encode()).hexdigest()
        path = ROOT+'/M_'+name
        material = unreal.load_asset(path)
        reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'FlameStudyHash') == digest)
        if not reused:
            if material is None:
                folder, asset = path.rsplit('/', 1)
                material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset, folder, unreal.Material, unreal.MaterialFactoryNew())
            assert material, path
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided', name != 'VEntryColumn')
            def node(kind, **props):
                obj = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
                for key, value in props.items(): obj.set_editor_property(key, value)
                return obj
            shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture)}
            if name in ('DChargeVane', 'DChargeCore', 'VEntryImpact', 'VEntryColumn'):
                sources['Rays'] = node('TextureObject', texture=rays)
            if name == 'VEntryShaft':
                sources.update({'Position': node('WorldPosition'), 'Center': node('ObjectPositionWS')})
            if name == 'VEntryColumn':
                sources.update({'Position': node('WorldPosition'), 'Center': node('ObjectPositionWS'),
                                'Normal': node('PixelNormalWS'), 'View': node('CameraVectorWS'),
                                'HalfHeight': node('ScalarParameter', parameter_name='HalfHeight', default_value=500.)})
            for param, default in [('Age', 0.), ('Progress', 0.), ('ShotAge', 100.), ('Index', 0.), ('Strength', 0.)]:
                sources[param] = node('ScalarParameter', parameter_name=param, default_value=default)
            pins = []
            for name in sources:
                pin = unreal.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
            shader.set_editor_property('inputs', pins)
            for name, source in sources.items(): assert lib.connect_material_expressions(source, '', shader, name)
            for prop, rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
                mask = node('ComponentMask', r=rgba[0], g=rgba[1], b=rgba[2], a=rgba[3])
                assert lib.connect_material_expressions(shader, '', mask, '')
                assert lib.connect_material_property(mask, '', prop)
        # A stored graph hash does not prove shader success. GetStatistics waits for
        # this platform resource's compilation in UE 5.8 before we continue to PIE.
        compile_errors = [str(error) for error in (lib.recompile_material(material) or [])]
        stats = lib.get_statistics(material)
        rows.append({'path': path, 'hash': digest, 'reused': reused,
                     'compile_errors': compile_errors, 'compilation_waited': True,
                     'statistics': {'pixel': stats.num_pixel_shader_instructions,
                                    'vertex': stats.num_vertex_shader_instructions,
                                    'samplers': stats.num_samplers}})
        if compile_errors:
            (out/'flame-studies-author.json').write_text(
                json.dumps({'passed': False, 'materials': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
            raise RuntimeError(path + ': ' + '\n'.join(compile_errors))
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'FlameStudyHash', digest)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), path
    # The launch log remains the final check for asynchronous compiler diagnostics.
    log = out/'editor.log'
    shader_failures = [line for line in log.read_text(encoding='utf-8', errors='replace').splitlines()
                       if ROOT in line and ('Failed to compile Material' in line or 'Default Material will be used' in line)] if log.exists() else []
    result = {'passed': not shader_failures, 'materials': rows,
              'shader_log_failures': shader_failures, 'shader_log_available': log.exists(),
              'default_cvars': {'D': 0, 'V': 3}, 'labels': LABELS}
    (out/'flame-studies-author.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    if shader_failures:
        raise RuntimeError('Flame study shader compilation failed: ' + '\n'.join(shader_failures))
    return result


def sequence(rig):
    selected = os.environ.get('SPARROW_FLAME_PARTS', 'D1,D2,D3,V1,V2,V3').split(',')
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    valid = unreal.SystemLibrary.is_valid
    def actors(kind):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), getattr(unreal, kind)) if valid(a)]
    report = {'passed': False, 'fps': rig['FPS'], 'cases': []}
    def save():
        (rig['OUT']/'flame-studies-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        for name in selected:
            if not name: continue
            letter, style = name[0], int(name[1])
            rig['switch']('countess'); yield .2
            rig['switch']('sparrow'); yield .7
            rig['cmd']('CountessComboQA.FlushInput')
            rig['cmd']('Sparrow.FlameStudy.D '+str(style if letter == 'D' else 0))
            rig['cmd']('Sparrow.FlameStudy.V '+str(style if letter == 'V' else 0))
            rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
            rig['case']('Flame_'+name)
            targets = rig['layout']([(420, 0), (700, 0), (600, 370)])
            yield .2
            initial = [rig['health'](a) for a in targets]
            started = now(); rig['use'](letter, offset=(950, 0))
            if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                rig['STATE']['video_clip'] = {'case': name, 'prefix': 'Flame_'+name+'_video', 'cast_time': started, 'frame_times': []}
            row = {'name': name, 'label': LABELS[name], 'seen': False, 'surfaces': 0}
            report['cases'].append(row)
            moments = [.22, .45, .57, .72] if letter == 'D' else [.64, .74, .84, .94, 1.04, 1.08, 1.15, 1.23, 1.48, 1.74, 2.4]
            while now()-started < (1.45 if letter == 'D' else 3.0):
                for study in actors('SparrowFlameStudies'):
                    if study.get_owner() == rig['pawn']():
                        row['seen'] = True
                        row['design'] = study.get_design()
                        row['released'] = row.get('released', False) or study.has_released()
                        row['tracked_distance_cm'] = max(row.get('tracked_distance_cm', 0.), study.get_tracked_distance())
                        parts = [p for p in study.get_components_by_class(unreal.StaticMeshComponent)
                                 if 'SparrowFlameStudySurface' in [str(t) for t in p.component_tags]]
                        row['surfaces'] = max(row['surfaces'], len(parts))
                        row['materials_ready'] = all(p.get_material(0) for p in parts)
                if letter == 'V':
                    for form in actors('SparrowAscensionWings'):
                        wing = next(p for p in form.get_components_by_class(unreal.SkeletalMeshComponent) if p.get_name() == 'SerathWings')
                        row['native_wings_hidden'] = not wing.is_visible()
                if moments and now()-started >= moments[0]:
                    rig['capture']('Flame_'+name+'_'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1./rig['FPS']
            if os.environ.get('NEW_SKILLS_VIDEO') == '1': rig['finish_video_clip']()
            rig['check'](row['seen'] and row['design'] == style and row.get('materials_ready', False), name+' uses the selected native study and authored materials')
            expected = 23 if letter == 'D' else 22 if style == 3 else 15 if style == 2 else 17
            rig['check'](row['surfaces'] == expected, name+' owns only its expected visual surfaces')
            if letter == 'D':
                row['damage'] = [x-rig['health'](a) for x, a in zip(initial, targets)]
                rig['check'](row['released'] and row['damage'] == [65., 65., 0.], name+' preserves native single piercing shot damage')
                rig['check'](not actors('SparrowFlameStudies'), name+' releases all short-lived visual surfaces')
            else:
                rig['check'](row.get('native_wings_hidden', False) == (style != 3), name+' preserves adopted V3 native wings and hides only replacement-study wings')
                rig['check'](rig['skills']().get_ascension_remaining() > 36., name+' preserves the actual V form duration')
                rig['cmd']('Sparrow.FlameStudy.V 0'); yield .1
                rig['check'](not actors('SparrowFlameStudies'), name+' comparison actor retires when the selector returns to zero')
                forms = actors('SparrowAscensionWings')
                restored = bool(forms) and all(next(p for p in form.get_components_by_class(unreal.SkeletalMeshComponent)
                                                   if p.get_name() == 'SerathWings').is_visible() for form in forms)
                rig['check'](restored, name+' restores the existing native wings without cancelling V')
            rig['recovered'](); save()
        report['passed'] = True; save()
    finally:
        rig['cmd']('Sparrow.FlameStudy.D 0')
        rig['cmd']('Sparrow.FlameStudy.V 3')
