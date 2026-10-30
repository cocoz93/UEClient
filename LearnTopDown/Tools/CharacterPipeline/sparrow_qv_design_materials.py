"""Q1-5 / V1-4 opt-in game designs. Does not change installed materials.

The original open/faceted candidates remain preserved. Q4/5 and V4 add uncapped
light volumes and soft horizontal illumination, with no opaque ground decal.
The generated GoldFlow artwork supplies actual RGBA material structure.
author(output) is run by the parent in the single Unreal authoring session.
"""
import hashlib
import json
import math
from pathlib import Path

import unreal

ROOT = '/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027'
ART = '/Game/TopDown/Characters/Sparrow/FX/FDesign20261027/T_FDesignGoldenFlow'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
RAYS = '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays'
PLASMA = '/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps'

COMMON = r'''
float x=UV.x, y=UV.y;
float n=Texture2DSample(Flow,FlowSampler,UV*float2(2.7,3.5)+float2(Age*.63,Index*.173)).r;
float fine=Texture2DSample(Flow,FlowSampler,UV*float2(8.,6.)+float2(Age*1.8,Index*.137)).g;
float aa=max(fwidth(y)*.7,.003);
float3 amber=float3(.48,.105,.012), gold=float3(2.4,1.0,.15), white=float3(4.4,3.5,1.8);
float endFade=smoothstep(.0,.014,x)*(1.-smoothstep(.965,1.,x));
float2 flowUV=float2(frac(x*1.18+Age*.68+Index*.137),y);
flowUV+=float2((n-.5)*.014,(fine-.5)*.026);
float4 art=Texture2DSample(FlowArt,FlowArtSampler,flowUV);
'''

Q_BEAM = r'''
if(Style>2.5){
 float face=saturate(dot(normalize(SurfaceNormal),normalize(float3(.29,-.38,.87))));
 float side=frac(y*6.);
 float facetBreak=.24+.76*smoothstep(.26,.64,n*.50+fine*.50);
 float edge=exp(-pow((side-.045)/.026,2.))*(.20+.60*fine)*facetBreak;
 float fold=smoothstep(.22,.52,face);
 float3 color=lerp(float3(.075,.030,.012),art.rgb*(1.12+face*.80),.31+fold*.69)+white*edge*.16;
 color+=float3(.018,.012,.055)*(1.-face)*art.a;
 return float4(color,saturate(.19+art.a*.33+edge*.28)*Envelope*endFade);
}
if(Style>1.5){
 // A broad streaming material with empty channels, not an outline or painted rod.
 float bunch=exp(-x*8.)*smoothstep(-.15,.025,ContactAge);
 float4 lower=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.78+Age*.94+Index*.27),.10+y*.80));
 float density=lerp(art.a,lower.a,bunch*.75);
 float3 color=lerp(art.rgb,lower.rgb,bunch*.75)*(2.5+bunch*.75);
 return float4(color,saturate(density*.88)*Envelope*endFade);
}
float taper=max(.035,smoothstep(.0,.14,x));
float v=(y-.5)/taper+.5;
float4 lance=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.9+Age*.92+Index*.137),v));
float bounds=step(0.,v)*step(v,1.);
float center=y-.5-(n-.5)*.015;
float core=exp(-pow(center/(.022*taper+aa*.45),2.));
float tip=exp(-x*25.);
float3 color=lance.rgb*2.8+white*core*(.40+tip*.40);
float density=lance.a*.76+core*.46;
return float4(color,saturate(density)*bounds*Envelope*endFade);
'''

Q_VEIL = r'''
if(Style>2.5){
 float3 color=lerp(gold,white,.50+.30*fine);
 return float4(color,.82*Envelope*endFade);
}
float4 silk=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.73+Age*(Style>1.5?.92:1.15)+Index*.19),y));
float edge=smoothstep(.0,.055,y)*(1.-smoothstep(.945,1.,y));
return float4(silk.rgb*(Style>1.5?2.4:2.9),silk.a*(Style>1.5?.64:.48)*Envelope*edge*endFade);
'''

CONTACT = r'''
float t=max(0.,ContactAge);
float ray=floor(UV.y*.5), localY=frac(UV.y);
float random=frac(sin(ray*71.17+Index*1.9)*431.71);
float4 ground=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.83-t*.75+random),.08+localY*.84));
// Each fracture loses different sections; no continuous roots or concentric cuts.
float segment=frac(x*(3.2+random*.8)+random*3.1);
float gaps=smoothstep(.08,.19,segment)*(1.-smoothstep(.57,.73,segment));
float stop=1.-smoothstep(.48+random*.12,.82,x);
float sparkCenter=.12+random*.16+t*(.75+random*.8);
float spark=exp(-pow((x-sparkCenter)/.035,2.)-pow((localY-.5)/.17,2.))*(1.-smoothstep(.05,.22,t));
float core=exp(-x*19.)*exp(-t*23.);
float3 color=ground.rgb*1.75+white*(core*.52+spark*.48);
float density=ground.a*.63*gaps*stop+core*.45+spark*.62;
return float4(color,saturate(density)*endFade*Envelope);
'''

BURST = r'''
float t=max(0.,ContactAge);
float4 burst=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.90-t*.88+Index*.23),y));
float side=smoothstep(.0,.075,y)*(1.-smoothstep(.925,1.,y));
if(Style>2.5){
 float face=saturate(dot(normalize(SurfaceNormal),normalize(float3(.32,-.42,.85))));
 float3 color=burst.rgb*(1.0+face*2.2)+white*pow(face,5.)*.22;
 return float4(color,(.25+burst.a*.52)*Envelope*endFade);
}
float holes=.24+.76*smoothstep(.24,.69,fine*.58+n*.42);
return float4(burst.rgb*2.65,burst.a*.88*holes*Envelope*side*endFade);
'''

V_PRELUDE = r'''
// Independent horizontal omissions. Nothing closes around the character.
float phase=x*7.1;
float band=floor(phase), local=frac(phase);
float random=frac(sin(band*37.17+1.7)*437.13);
float cutAt=.10+random*.40;
float keep=smoothstep(cutAt,cutAt+.035,local)*(1.-smoothstep(.91,.99,local));
float erosion=smoothstep(.12+random*.20,.42+random*.04,Age);
keep*=1.-smoothstep(.0,.70,erosion-(1.-local)*.40);
float4 thin=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.82+Age*.93),y));
float core=exp(-pow((y-.5)/(.035+aa),2.));
float3 color=thin.rgb*2.5+white*core*.23;
return float4(color,saturate(thin.a*.78+core*.22)*keep*Envelope*endFade);
'''

V_COLUMN = r'''
float t=max(0.,ContactAge);
float side=smoothstep(.0,.045,y)*(1.-smoothstep(.955,1.,y));
if(Style<1.5){
 // Broad soft body, with warm interiors and local white fibres from the image.
 float4 soft=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.65+Age*.74+Index*.29),.08+y*.84));
 float veil=exp(-pow((y-.5)/.35,4.))*(.18+.30*n);
 float3 color=soft.rgb*2.35+amber*veil;
 return float4(color,saturate(soft.a*.62+veil*.20)*Envelope*side*endFade);
}
if(Style<2.5){
 float2 uv=float2(frac(x*.96+Age*.96+Index*.19),y+(n-.5)*.035);
 float4 silk=Texture2DSample(FlowArt,FlowArtSampler,uv);
 float channels=.50+.50*smoothstep(.18,.75,Texture2DSample(Flow,FlowSampler,float2(y*4.,x*.8+Age*.5)).r);
 return float4(silk.rgb*2.7,silk.a*channels*.86*Envelope*side*endFade);
}
float2 uv=float2(frac(x*1.35+Age*1.27+Index*.13),y+(fine-.5)*.05);
float4 corona=Texture2DSample(FlowArt,FlowArtSampler,uv);
float fire=Texture2DSample(Flow,FlowSampler,float2(y*3.3,x*6.+Age*2.9)).g;
float fingers=smoothstep(.12,.55,fire+(1.-x)*.12);
float3 color=corona.rgb*(2.9+pow(fire,5.)*.8);
return float4(color,corona.a*(.46+fingers*.54)*Envelope*side*endFade);
'''

V_REVEAL = r'''
float t=max(0.,Age-1.16);
float4 flash=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x+Index*.1-t*2.),y));
float hot=exp(-x*7.)*exp(-t*30.);
return float4(flash.rgb*3.0+white*hot*.45,saturate(flash.a*.66+hot*.27)*Envelope*endFade);
'''

V_WING_FLOW = r'''
float4 wing=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.82-Age*.83+Index*.37),y));
float end=smoothstep(.0,.055,x)*(1.-smoothstep(.80,1.,x));
float edge=smoothstep(.0,.06,y)*(1.-smoothstep(.94,1.,y));
return float4(wing.rgb*2.65,wing.a*.80*Envelope*edge*end);
'''

# Q4/5: a stationary celestial opening feeds light into the ground. These
# materials deliberately have a continuous soft body, not a narrow alpha-cut
# artwork streak. The old Q1-3/V1-3 material bodies above remain unchanged.
CELESTIAL_APERTURE = r'''
float r=saturate(UV.x), a=UV.y*6.2831853;
float2 p=float2(cos(a),sin(a))*r;
float cloud=Texture2DSample(Flow,FlowSampler,p*1.6+float2(Age*.08,Index*.13)).r;
float center=exp(-pow(r/.48,2.));
float ring=exp(-pow((r-(.67+(cloud-.5)*.018))/.105,2.));
float inner=exp(-pow((r-.47)/.07,2.));
float rimGlow=exp(-pow((r-.66)/.26,2.));
float rimWeight=Style>4.5?.42:1.;
float3 color=lerp(float3(2.2,1.25,.35),float3(4.2,3.7,2.5),saturate(center*.80+inner*.25));
color+=float3(.5,.34,.09)*cloud;
float density=center*.12+(ring*.40+inner*.09)*rimWeight+rimGlow*.075;
return float4(color,saturate(density)*(1.-smoothstep(.88,1.,r))*Envelope);
'''

CELESTIAL_COLUMN = r'''
float v=frac(UV.y);
// The shaft is vertical. Removing the view's height component keeps the bright
// optical axis stable in the quarter-view instead of dimming it with elevation.
float3 acrossView=float3(ViewDirection.xy,0.)/max(length(ViewDirection.xy),.0001);
float facing=saturate(abs(dot(normalize(SurfaceNormal),acrossView)));
float side=pow(facing,1.35);
float2 coordinates=float2(frac(x*.20+Age*.70+Index*.173),.08+v*.84);
float4 fibres=Texture2DSample(FlowArt,FlowArtSampler,coordinates);
float longFlow=Texture2DSample(Flow,FlowSampler,float2(v*19.,x*.20-Age*.60+Index*.23)).r;
float fineFlow=Texture2DSample(Flow,FlowSampler,float2(v*43.+Index*.31,x*.65-Age*1.5)).g;
float flow=longFlow*.58+fineFlow*.42;
float core=pow(facing,Style>4.5?52.:64.);
float filaments=pow(smoothstep(.23,.78,flow),1.6);
float3 outerGold=lerp(float3(.86,.29,.035),float3(2.65,1.34,.22),filaments);
outerGold+=fibres.rgb*.10;
// White is confined to the optical axis; the surrounding field stays gold and
// varies in longitudinal density instead of whitening a broad cylinder wall.
float3 color=lerp(outerGold,float3(6.8,6.2,5.15),pow(core,.55));
float axialCore=smoothstep(0.,.10,x)*(1.-smoothstep(.92,1.,x));
float axialHalo=smoothstep(0.,.23,x)*(1.-smoothstep(.82,1.,x));
float density=core*.66*axialCore+(.025+filaments*.25+fibres.a*.045)*side*axialHalo;
return float4(color,density*Envelope);
'''

CELESTIAL_POOL = r'''
float r=saturate(UV.x), a=UV.y*6.2831853;
float t=max(0.,ContactAge);
float2 p=float2(cos(a),sin(a))*r;
float cloud=Texture2DSample(Flow,FlowSampler,p*2.4+float2(-t*.21,Index*.19)).r;
float detail=Texture2DSample(Flow,FlowSampler,p*6.8+float2(t*.7,Index*.31)).g;
float hot=exp(-pow(r/.27,2.))*exp(-t*16.);
float body=exp(-pow(r/.65,2.))*(.30+cloud*.70);
float waveRadius=.16+t*1.72;
float wave=exp(-pow((r-waveRadius)/(.055+cloud*.04),2.));
float echo=exp(-pow((r-(waveRadius-.17))/.035,2.))*.36;
float broken=.26+.74*smoothstep(.18,.72,detail*.55+cloud*.45);
float3 color=lerp(float3(1.85,.96,.18),float3(4.6,4.0,2.9),saturate(hot*.92+wave*.25));
float density=hot*.60+body*.12+(wave+echo)*broken*.19;
return float4(color,saturate(density)*(1.-smoothstep(.82,1.,r))*Envelope);
'''

CELESTIAL_PLUME = r'''
float v=frac(UV.y), strand=floor(UV.y*.5);
float2 uv=float2(frac(x*.71-Age*.52+strand*.137),.06+v*.88);
float4 glow=Texture2DSample(FlowArt,FlowArtSampler,uv);
float billow=Texture2DSample(Flow,FlowSampler,float2(v*2.4,x*2.6-Age*1.3+strand*.23)).r;
float side=smoothstep(0.,.15,v)*(1.-smoothstep(.85,1.,v));
float top=1.-smoothstep(.53+billow*.17,1.,x);
float3 color=lerp(float3(1.35,.70,.15),float3(2.2,1.45,.55),billow*.54)+glow.rgb*.56;
float gaps=.20+.80*smoothstep(.22,.66,billow*.60+glow.a*.40);
float density=(billow*.075+glow.a*.17)*gaps*side*top;
return float4(color,density*Envelope);
'''

CELESTIAL_SCATTER = r'''
float u=UV.x,v=frac(UV.y),particle=floor(UV.y*.5);
float center=exp(-pow((u-.5)/.32,2.)-pow((v-.5)/.24,2.));
float fade=1.-smoothstep(.08+frac(particle*.713)*.30,.56,max(0.,ContactAge));
float3 color=lerp(float3(2.4,1.25,.22),float3(5.2,4.3,2.8),frac(particle*.617));
return float4(color,center*.82*fade*Envelope);
'''

V_PRIME_RAY = r'''
// No scrolling mask, displacement or horizontal omissions: one straight ray.
float facing=saturate(abs(dot(normalize(SurfaceNormal),normalize(ViewDirection))));
float core=pow(facing,1.6);
float halo=pow(facing,.55);
float3 color=lerp(float3(2.1,1.4,.48),float3(4.8,4.3,3.1),core);
return float4(color,(core*.66+halo*.22)*Envelope*endFade);
'''

V_CELESTIAL_COLUMN = r'''
float v=frac(UV.y);
float3 acrossView=float3(ViewDirection.xy,0.)/max(length(ViewDirection.xy),.0001);
float facing=saturate(abs(dot(normalize(SurfaceNormal),acrossView)));
float2 uv=float2(frac(x*.16+Age*.94+Index*.17),.04+v*.92);
float4 flame=Texture2DSample(FlowArt,FlowArtSampler,uv);
float longFlow=Texture2DSample(Flow,FlowSampler,float2(v*11.,x*.24-Age*.84+Index*.3)).r;
float fineFlow=Texture2DSample(Flow,FlowSampler,float2(v*31.,x*.85-Age*1.9+Index*.17)).g;
float flow=longFlow*.62+fineFlow*.38;
float edge=pow(facing,1.35);
float core=pow(facing,72.);
float filaments=pow(smoothstep(.22,.77,flow),1.5);
float3 outerGold=lerp(float3(.84,.27,.028),float3(2.75,1.30,.18),filaments);
outerGold+=flame.rgb*.12;
float3 color=lerp(outerGold,float3(7.0,6.25,5.05),pow(core,.55));
float axialCore=smoothstep(0.,.095,x)*(1.-smoothstep(.93,1.,x));
float axialHalo=smoothstep(0.,.22,x)*(1.-smoothstep(.82,1.,x));
float density=core*.62*axialCore+(.025+filaments*.27+flame.a*.05)*edge*axialHalo;
return float4(color,density*Envelope);
'''

# V6 retains the V4 palette and body. Only the lower axial fade is removed so
# the ray and column remain connected to the traced ground instead of floating.
V_ANCHORED_RAY = V_PRIME_RAY.replace('*Envelope*endFade', '*Envelope*(1.-smoothstep(.965,1.,x))')
V_ANCHORED_COLUMN = V_CELESTIAL_COLUMN.replace(
    'smoothstep(0.,.095,x)*(1.-smoothstep(.93,1.,x))', '(1.-smoothstep(.93,1.,x))').replace(
    'smoothstep(0.,.22,x)*(1.-smoothstep(.82,1.,x))', '(1.-smoothstep(.82,1.,x))')
V_ANCHORED_CONTACT = r'''
float r=saturate(UV.x), a=UV.y*6.2831853;
float2 p=float2(cos(a),sin(a))*r;
float cloud=Texture2DSample(Flow,FlowSampler,p*2.2+float2(Age*.19,Index*.13)).r;
float grains=Texture2DSample(Flow,FlowSampler,p*6.2+float2(-Age*.37,Index*.21)).g;
float body=exp(-pow(r/.64,4.));
float core=exp(-pow(r/.20,2.));
float edge=1.-smoothstep(.85,1.,r);
float texture=.54+.46*smoothstep(.16,.73,cloud*.68+grains*.32);
float3 color=lerp(float3(1.85,.96,.18),float3(4.6,4.0,2.9),core*.63);
return float4(color,(body*.20*texture+core*.28)*edge*Envelope);
'''


# Renaissance materials use translucent, curved light sheets and separated
# contact detail. Old candidates are retained for an honest gameplay comparison.
DAWN_CURTAINS = r'''
float u=saturate(UV.x), v=frac(UV.y), lane=floor(UV.y*.5);
float2 uv=float2(frac(u*.38+Age*.57+lane*.137+Index*.113),v);
float4 silk=Texture2DSample(FlowArt,FlowArtSampler,uv);
float2 turbulenceUV=float2(v*3.6+lane*.3,u*2.8-Age*.94+Index*.17);
float turbulence=Texture2DSample(Flow,FlowSampler,turbulenceUV).r;
// This source is an 8x8 flipbook. RGB carries lighting and padding; density is A.
float cell=16.+floor(frac(Age*.35+lane*.137+Index*.19)*32.);
float2 plasmaUV=(float2(fmod(cell,8.),floor(cell/8.))+float2(.10+u*.80,.08+v*.84))/8.;
float wisps=saturate(Texture2DSample(Plasma,PlasmaSampler,plasmaUV).a*3.);
float edge=pow(saturate(sin(v*3.14159265)),.82);
float ridge=exp(-pow((v-.5-(turbulence-.5)*.13)/.043,2.));
float broken=smoothstep(.16,.68,turbulence*.58+silk.a*.42);
float hem=smoothstep(.0,.012,u)*(1.-smoothstep(.73,1.,u));
float ripples=.54+.46*smoothstep(.18,.67,wisps*.50+turbulence*.50);
// The first game render read as eight white wires: a continuous narrow ridge
// was brighter than the whole sheet. Broad flowing density now owns the shape;
// tiny irregular hot patches remain disconnected along its length.
float body=pow(saturate(turbulence*.70+silk.a*.30),.72);
float density=(.38*body+silk.a*.12+ridge*.015)*edge*hem*ripples;
float hot=smoothstep(.65,.84,turbulence*.58+silk.a*.42)*ridge;
float3 color=lerp(float3(.65,.30,.058),float3(2.25,1.43,.43),body);
color+=float3(1.65,1.45,.75)*hot*.25;
return float4(color,density*Envelope);
'''

DAWN_CORE = r'''
float3 acrossView=float3(ViewDirection.xy,0.)/max(length(ViewDirection.xy),.0001);
float face=saturate(abs(dot(normalize(SurfaceNormal),acrossView)));
float core=pow(face,1.5), halo=pow(face,.6);
float taper=smoothstep(.0,.018,x)*(1.-smoothstep(.83,1.,x));
float pressure=exp(-max(0.,ContactAge)*18.);
float3 color=lerp(float3(1.8,1.1,.31),float3(4.2,3.9,2.8),core);
return float4(color,(core*.42+halo*.13)*taper*Envelope*(.7+pressure*.3));
'''

DAWN_OVERTURE = r'''
float v=frac(UV.y), mote=floor(abs(UV.y)*.5);
float shape=exp(-pow((x-.5)/.20,2.)-pow((v-.5)/.16,2.));
float flicker=.48+.52*pow(saturate(sin(Age*13.+mote*1.7)),2.);
return float4(float3(2.7,1.9,.65),shape*flicker*Envelope*.75);
'''

DAWN_POOL = r'''
float r=saturate(UV.x), a=UV.y*6.2831853, t=max(0.,ContactAge);
float2 p=float2(cos(a),sin(a))*r;
float warp=Texture2DSample(Flow,FlowSampler,p*2.+float2(t*.5,Index*.13)).r;
float cell=16.+floor(saturate(t/.55)*31.);
float2 plasmaUV=(float2(fmod(cell,8.),floor(cell/8.))+p*.43+.5)/8.;
float wisps=saturate(Texture2DSample(Plasma,PlasmaSampler,plasmaUV).a*3.);
float caustic=pow(smoothstep(.18,.70,wisps*.58+warp*.42),2.);
float body=exp(-pow(r/.43,2.));
float hot=exp(-pow(r/.15,2.))*exp(-t*24.);
float sweep=exp(-pow((r-(.13+t*1.65))/.105,2.));
float flow=(.13+caustic*.87)*(body*.18+sweep*.11)*exp(-t*9.);
float3 color=lerp(float3(.82,.37,.048),float3(2.1,1.36,.36),caustic*.70)+float3(2.9,2.5,1.65)*hot;
return float4(color,(flow+hot*.45)*(1.-smoothstep(.75,1.,r))*Envelope);
'''

DAWN_SHOCK = r'''
float u=UV.x,v=frac(UV.y), ray=floor(UV.y*.5), t=max(0.,ContactAge);
float seed=frac(sin(ray*37.7+Index*.82)*4371.17);
float2 uv=float2(frac(u*.61-t*.82+seed),v);
float4 fire=Texture2DSample(FlowArt,FlowArtSampler,uv);
float side=pow(saturate(sin(v*3.14159265)),.65);
float groove=Texture2DSample(Flow,FlowSampler,float2(u*3.1-t*1.8,v*2.+seed)).g;
float rim=exp(-pow((v-.5-(groove-.5)*.05)/.052,2.));
float tail=smoothstep(.0,.08,u)*(1.-smoothstep(.62,1.,u));
float erosion=1.-smoothstep(.03,.90,t*2.5-groove*.24-u*.25);
float gaps=.25+.75*smoothstep(.16,.70,groove);
float3 color=lerp(float3(.62,.22,.030),float3(2.6,1.75,.48),fire.a)+float3(2.4,2.1,1.2)*rim*.04;
return float4(color,(fire.a*.46+rim*.025)*side*tail*erosion*gaps*Envelope);
'''

DAWN_SPARKS = r'''
float v=frac(UV.y), particle=floor(abs(UV.y)*.5);
float core=exp(-pow((x-.5)/.30,2.)-pow((v-.5)/.18,2.));
float halo=exp(-pow((x-.5)/.42,2.)-pow((v-.5)/.36,2.));
float t=max(0.,ContactAge), seed=frac(particle*.617);
float fade=1.-smoothstep(.17+seed*.25,.67,t);
float3 color=lerp(float3(1.8,.72,.10),float3(4.1,3.15,1.15),seed);
return float4(color,(core*.72+halo*.10)*fade*Envelope);
'''

DAWN_SPEARS = r'''
float v=frac(UV.y), lane=floor(UV.y*.5);
float bevel=exp(-pow((v-.5)/.11,2.));
float side=pow(saturate(sin(v*3.14159265)),.5);
float grain=Texture2DSample(Flow,FlowSampler,float2(x*3.-Age*1.5,v*2.+lane*.31)).r;
float tail=1.-smoothstep(.55,1.,x);
float3 color=lerp(float3(.85,.40,.055),float3(3.3,2.6,1.15),bevel*.65+grain*.22);
return float4(color,(.33+bevel*.38+grain*.13)*side*tail*Envelope);
'''

DAWN_V_CORE = r'''
float3 acrossView=float3(ViewDirection.xy,0.)/max(length(ViewDirection.xy),.0001);
float face=saturate(abs(dot(normalize(SurfaceNormal),acrossView)));
float flow=Texture2DSample(Flow,FlowSampler,float2(UV.y*11.,x*.8-Age*1.3)).r;
float core=pow(face,3.3), halo=pow(face,1.1);
float axial=smoothstep(.0,.02,x)*(1.-smoothstep(.90,1.,x));
float3 color=lerp(float3(1.9,.92,.17),float3(4.8,4.3,2.9),core*.76+flow*.12);
return float4(color,(core*.47+halo*.12)*axial*Envelope);
'''

DAWN_V_CURTAINS = DAWN_CURTAINS.replace('.38*body', '.42*body').replace(
    'float3(.65,.30,.058)', 'float3(.76,.34,.065)').replace('(.73,1.,u)', '(.88,1.,u)').replace('(.0,.012,u)', '(.0,.008,u)')


def _material(name, body, textures):
    lib = unreal.MaterialEditingLibrary
    path = ROOT + '/M_' + name
    code = COMMON + body
    digest = hashlib.sha256((code + ART + NOISE + RAYS + (PLASMA if name.startswith('Dawn') else '')).encode()).hexdigest()
    material = unreal.load_asset(path)
    reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'QVDesignHash') == digest)
    if not reused:
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_' + name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
        if material is None:
            raise RuntimeError('Cannot create ' + path)
        for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY):
            lib.disconnect_material_property(material, prop)
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)

        def node(kind, **props):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
            for key, value in props.items():
                item.set_editor_property(key, value)
            return item

        shader = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources = {'UV': node('TextureCoordinate'), 'SurfaceNormal': node('PixelNormalWS'),
                   'ViewDirection': node('CameraVectorWS')}
        sources.update({key: node('TextureObject', texture=texture) for key, texture in textures.items()})
        for key, value in [('Age', 0.), ('ContactAge', -1.), ('Index', 0.), ('Style', 1.), ('Envelope', 1.)]:
            sources[key] = node('ScalarParameter', parameter_name=key, default_value=value)
        pins = []
        for key in sources:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', key)
            pins.append(pin)
        shader.set_editor_property('inputs', pins)
        for key, source in sources.items():
            assert lib.connect_material_expressions(source, '', shader, key)
        for prop, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
            mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
            assert lib.connect_material_expressions(shader, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
    errors = [str(item) for item in (lib.recompile_material(material) or [])]
    if errors:
        raise RuntimeError(path + ': ' + '\n'.join(errors))
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'QVDesignHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    return material, {'path': path, 'reused': reused, 'hash': digest, 'compile_errors': errors}


def _flux_fold():
    vertices, uvs, faces = [], [], []
    steps, across = 40, 16
    for i in range(steps + 1):
        u = i / steps
        for j in range(across + 1):
            v = j / across
            depth = math.sin(v * math.pi * 3.6 + u * 2.5) * (7. + u * 4.)
            depth += math.sin(u * math.tau) * 5.
            vertices.append((u * 100., (v - .5) * 100., depth))
            uvs.append((u, v))
    stride = across + 1
    for i in range(steps):
        for j in range(across):
            a = i * stride + j + 1
            faces.extend(((a, a + 1, a + stride + 1), (a, a + stride + 1, a + stride)))
    return vertices, uvs, faces


def _prism():
    vertices, uvs, faces = [], [], []
    rings = ((0., .002), (18., .55), (48., 1.), (76., .66), (100., .045))
    for side in range(6):
        base = len(vertices) + 1
        for x, scale in rings:
            for edge in (side, side + 1):
                a = edge * math.tau / 6
                vertices.append((x, math.cos(a) * 50. * scale, math.sin(a) * 50. * scale))
                uvs.append((x / 100., edge / 6.))
        for step in range(len(rings) - 1):
            a = base + step * 2
            faces.extend(((a, a + 1, a + 3), (a, a + 3, a + 2)))
    return vertices, uvs, faces


def _frays(crown=False):
    vertices, uvs, faces = [], [], []
    count, steps = (12, 14) if crown else (15, 14)
    for ray in range(count):
        angle = ray * 2.399963
        axis = (math.cos(angle), math.sin(angle))
        lateral = (-axis[1], axis[0])
        length = 66. + (ray % 5) * 8.
        width = 10. + (ray % 3) * 3. if crown else 2.2 + (ray % 4) * .85
        base = len(vertices) + 1
        for i in range(steps + 1):
            u = i / steps
            bend = math.sin(u * (7. + ray % 3) + ray * 1.7) * (10. if crown else 7.) * u
            radius = 2. + u * length
            height = (math.sin(u * 1.9) * (24. + (ray % 4) * 7.)) if crown else 1.5 + u * .4
            taper = max(.014, math.sin(math.pi * u) ** .55)
            for side in (0., 1.):
                offset = bend + (side - .5) * 2. * width * taper
                vertices.append((axis[0] * radius + lateral[0] * offset,
                                 axis[1] * radius + lateral[1] * offset, height))
                uvs.append((u, side if crown else side + ray * 2.))
        for i in range(steps):
            a = base + i * 2
            faces.extend(((a, a + 1, a + 3), (a, a + 3, a + 2)))
        if not crown:
            # Two angular forks connect to the same ground fracture; no disc underneath.
            for branch in (0, 1):
                root = .34 + branch * .23
                a = angle + (1. if ray % 2 else -1.) * (.45 + branch * .17)
                start = (axis[0] * length * root, axis[1] * length * root, 2.)
                first = len(vertices) + 1
                for i in range(4):
                    u = i / 3.
                    for side in (-1., 1.):
                        vertices.append((start[0] + math.cos(a) * u * 28. - math.sin(a) * side * (1.7 - u * 1.5),
                                         start[1] + math.sin(a) * u * 28. + math.cos(a) * side * (1.7 - u * 1.5), 2.))
                        uvs.append((root + u * .25, (side + 1.) * .5 + ray * 2.))
                for i in range(3):
                    k = first + i * 2
                    faces.extend(((k, k + 1, k + 3), (k, k + 3, k + 2)))
    return vertices, uvs, faces


def _shard_crown():
    vertices, uvs, faces = [], [], []
    source, source_uv, source_faces = _prism()
    for piece in range(9):
        angle = piece * 2.399963
        axis = (math.cos(angle), math.sin(angle), .42 + (piece % 3) * .18)
        norm = sum(v * v for v in axis) ** .5
        axis = tuple(v / norm for v in axis)
        right = (-math.sin(angle), math.cos(angle), 0.)
        up = (-axis[2] * math.cos(angle), -axis[2] * math.sin(angle), math.sqrt(axis[0] ** 2 + axis[1] ** 2))
        origin = (math.cos(angle) * (24. + (piece % 3) * 12.), math.sin(angle) * (24. + (piece % 3) * 12.), 8. + (piece % 4) * 8.)
        base = len(vertices)
        for x, y, z in source:
            values = [origin[k] + axis[k] * x * (.27 + (piece % 3) * .06) + right[k] * y * .065 + up[k] * z * .065 for k in range(3)]
            vertices.append(tuple(values))
        uvs.extend(source_uv)
        faces.extend(tuple(i + base for i in f) for f in source_faces)
    return vertices, uvs, faces


def _straight_volume():
    """Uncapped axial light volume; view-facing opacity softens its silhouette.

    The previous three crossed sheets exposed a sharp star at the advancing
    end. A round section has no sheet corners and keeps the V precursor straight.
    """
    vertices, uvs, faces = [], [], []
    steps, segments = 24, 48
    for i in range(steps + 1):
        u = i / steps
        for j in range(segments + 1):
            v = j / segments
            angle = v * math.tau
            vertices.append((u * 100., math.cos(angle) * 50., math.sin(angle) * 50.))
            uvs.append((u, v))
    for i in range(steps):
        for j in range(segments):
            a = i * (segments + 1) + j + 1
            faces.extend(((a, a + 1, a + segments + 2), (a, a + segments + 2, a + segments + 1)))
    return vertices, uvs, faces


def _celestial_disc():
    """A shallow horizontal light source, with radial material coordinates."""
    vertices, uvs, faces = [], [], []
    rings, segments = 16, 64
    for ring in range(rings + 1):
        r = .001 + .999 * ring / rings
        for segment in range(segments + 1):
            turn = segment / segments
            angle = turn * math.tau
            vertices.append((math.cos(angle) * r * 100., math.sin(angle) * r * 100., (1. - r) * 2.))
            uvs.append((r, turn))
    for ring in range(rings):
        for segment in range(segments):
            a = ring * (segments + 1) + segment + 1
            faces.extend(((a, a + 1, a + segments + 2), (a, a + segments + 2, a + segments + 1)))
    return vertices, uvs, faces


def _contact_billow():
    """Broad curved plumes lift out of the illuminated contact, not radial rods."""
    vertices, uvs, faces = [], [], []
    steps, across = 18, 10
    for petal in range(5):
        angle = petal * 2.399963
        axis = (math.cos(angle), math.sin(angle))
        side = (-math.sin(angle), math.cos(angle))
        base = len(vertices)
        for i in range(steps + 1):
            u = i / steps
            radius = 18. + math.sin(u * 1.8) * (60. + petal % 3 * 11.)
            height = 4. + u * (38. + petal % 4 * 12.)
            half_width = (30. + petal % 3 * 7.) * (.65 + math.sin(u * 2.4) * .35)
            for j in range(across + 1):
                v = j / across
                width = (v - .5) * 2. * half_width
                curve = math.sin(v * math.pi) * 8. * math.sin(u * 2.3)
                vertices.append((axis[0] * (radius + curve) + side[0] * width,
                                 axis[1] * (radius + curve) + side[1] * width, height))
                uvs.append((u, v + petal * 2.))
        for i in range(steps):
            for j in range(across):
                a = base + i * (across + 1) + j + 1
                faces.extend(((a, a + 1, a + across + 2), (a, a + across + 2, a + across + 1)))
    return vertices, uvs, faces


def _contact_spray():
    vertices, uvs, faces = [], [], []
    for particle in range(42):
        angle = particle * 2.399963
        radius = 19. + (particle * 37 % 81)
        height = 4. + (particle * 17 % 89)
        origin = (math.cos(angle) * radius, math.sin(angle) * radius, height)
        along = (math.cos(angle) * .65, math.sin(angle) * .65, .76)
        side = (-math.sin(angle), math.cos(angle), 0.)
        length, width = 5. + particle % 5 * 1.7, 1.1 + particle % 3 * .45
        base = len(vertices)
        for u, v in ((0., 0.), (1., 0.), (1., 1.), (0., 1.)):
            vertices.append(tuple(origin[k] + along[k] * (u - .5) * length + side[k] * (v - .5) * width for k in range(3)))
            uvs.append((u, v + particle * 2.))
        faces.extend(((base + 1, base + 2, base + 3), (base + 1, base + 3, base + 4)))
    return vertices, uvs, faces


def _dawn_curtains():
    """Eight curved open sheets. No cylindrical wall or evenly lit solid shaft."""
    vertices, uvs, faces = [], [], []
    steps, across = 36, 10
    for lane in range(8):
        base = len(vertices)
        angle = lane * math.tau / 8.
        for i in range(steps + 1):
            u = i / steps
            turning = angle + math.sin(u * 3.1 + lane * .73) * .23
            radius = (8. + u * 18.) + math.sin(u * 5.2 + lane * .81) * (4. + u * 5.)
            width = (15. + lane % 3 * 4.) * (.42 + math.sin(u * math.pi) * .58)
            for j in range(across + 1):
                v = j / across
                side = (v - .5) * 2. * width
                billow = math.sin(v * math.pi) * math.sin(u * 4. + lane) * 7.
                vertices.append((u * 100., math.cos(turning) * (radius + billow) - math.sin(turning) * side,
                                 math.sin(turning) * (radius + billow) + math.cos(turning) * side))
                uvs.append((u, v + lane * 2.))
        for i in range(steps):
            for j in range(across):
                a = base + i * (across + 1) + j + 1
                faces.extend(((a, a + 1, a + across + 2), (a, a + across + 2, a + across + 1)))
    return vertices, uvs, faces


def _dawn_shock():
    """Tapered curved radial tongues, separated by dark gaps rather than a ring."""
    vertices, uvs, faces = [], [], []
    steps, across = 18, 6
    for ray in range(23):
        base = len(vertices)
        angle = ray * 2.399963
        length = 62. + ray * 23 % 47
        width = 4.5 + ray % 4 * 1.65
        for i in range(steps + 1):
            u = i / steps
            arc = angle + math.sin(u * 2.1) * (.13 if ray % 2 else -.21)
            radius = 6. + u * length
            height = math.sin(u * 2.2) * (9. + ray % 5 * 4.)
            # Keep a sub-pixel finite tip so import does not remove collapsed
            # end triangles and their UV lane endpoints.
            profile = max(.012, math.sin(u * math.pi) ** .60)
            for j in range(across + 1):
                v = j / across
                offset = (v - .5) * 2. * width * profile
                vertices.append((math.cos(arc) * radius - math.sin(arc) * offset,
                                 math.sin(arc) * radius + math.cos(arc) * offset,
                                 height + math.sin(v * math.pi) * 3. * profile))
                uvs.append((u, v + ray * 2.))
        for i in range(steps):
            for j in range(across):
                a = base + i * (across + 1) + j + 1
                faces.extend(((a, a + 1, a + across + 2), (a, a + across + 2, a + across + 1)))
    return vertices, uvs, faces


def _dawn_spears():
    """Four short parallel light lances with recognizable pointed fronts."""
    vertices, uvs, faces = [], [], []
    for spear in range(4):
        angle = spear * 2.399963
        oy, oz = math.cos(angle) * (11. + spear * 6.), math.sin(angle) * (11. + spear * 6.)
        # Crossed ribbons preserve the tapered arrow silhouette in quarter view.
        for plane in range(2):
            base = len(vertices)
            for x, width in ((0., .01), (12., 7.), (22., 2.2), (76., .01)):
                for side in (-1., 1.):
                    vertices.append((x + spear % 2 * 9., oy + (side * width if plane == 0 else 0.),
                                     oz + (side * width if plane == 1 else 0.)))
                    uvs.append((x / 76., (side + 1.) * .5 + spear * 2.))
            for step in range(3):
                a = base + step * 2 + 1
                faces.extend(((a, a + 1, a + 3), (a, a + 3, a + 2)))
    return vertices, uvs, faces


def _mesh(output, name, geometry, material):
    vertices, uvs, faces = geometry
    lines = ['o ' + name, 's off' if 'Prism' in name or 'Shard' in name else 's 1']
    lines += ['v %.7f %.7f %.7f' % (x, -y, z) for x, y, z in vertices]
    # UE's OBJ/FBX importer applies V=1-V. Preserve the new multi-lane coordinates
    # only for the new meshes, without reinterpreting any old candidate's UVs.
    exported_uvs = [(u, 1. - v) for u, v in uvs] if 'Dawn' in name else uvs
    lines += ['vt %.7f %.7f' % uv for uv in exported_uvs]
    lines += ['f ' + ' '.join('%d/%d' % (i, i) for i in face) for face in faces]
    obj = '\n'.join(lines) + '\n'
    digest = hashlib.sha256(obj.encode()).hexdigest()
    path = ROOT + '/' + name
    mesh = unreal.load_asset(path)
    reused = bool(mesh and unreal.EditorAssetLibrary.get_metadata_tag(mesh, 'QVGeometryHash') == digest)
    source = output / (name + '.obj')
    if not reused:
        source.write_text(obj, encoding='ascii')
        task = unreal.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': ROOT, 'destination_name': name,
                           'automated': True, 'replace_existing': True, 'save': False, 'factory': unreal.FbxFactory()}.items():
            task.set_editor_property(key, value)
        settings = unreal.FbxImportUI()
        for key, value in {'automated_import_should_detect_type': False,
                           'mesh_type_to_import': unreal.FBXImportType.FBXIT_STATIC_MESH,
                           'import_mesh': True, 'import_materials': False, 'import_textures': False}.items():
            settings.set_editor_property(key, value)
        data = settings.get_editor_property('static_mesh_import_data')
        for key, value in {'combine_meshes': True, 'auto_generate_collision': False, 'convert_scene': False,
                           'convert_scene_unit': False, 'force_front_x_axis': False, 'generate_lightmap_u_vs': False}.items():
            data.set_editor_property(key, value)
        task.set_editor_property('options', settings)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError('Cannot import ' + path)
    mesh.set_editor_property('static_materials', [unreal.StaticMaterial(material_interface=material, material_slot_name='Flux')])
    box = mesh.get_bounding_box()
    actual = [box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z]
    expected = [max(v[k] for v in vertices) - min(v[k] for v in vertices) for k in range(3)]
    if any(abs(a - b) > .05 for a, b in zip(actual, expected)) or mesh.get_num_triangles(0) < len(faces) - 6:
        raise RuntimeError('Imported QV geometry differs: ' + name + ' ' + str(actual))
    uv_range = None
    if 'Dawn' in name:
        section = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
        imported_uvs = section[3]
        uv_range = [min(p.y for p in imported_uvs), max(p.y for p in imported_uvs)]
        expected_uv = [min(p[1] for p in uvs), max(p[1] for p in uvs)]
        if any(abs(a - b) > .02 for a, b in zip(uv_range, expected_uv)):
            raise RuntimeError('Dawn UV lanes differ: ' + name + ' ' + str(uv_range))
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, 'QVGeometryHash', digest)
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    return {'path': path, 'reused': reused, 'hash': digest, 'bounds': actual, 'triangles': mesh.get_num_triangles(0), 'generated_collision': False, 'dawn_uv_range': uv_range}


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    unreal.EditorAssetLibrary.make_directory(ROOT)
    textures = {key: unreal.load_asset(path) for key, path in [('FlowArt', ART), ('Flow', NOISE), ('Rays', RAYS)]}
    result = {'passed': False, 'materials': [], 'meshes': [], 'Q_default': 0, 'V_default': 0,
              'Q_candidates': [1, 2, 3, 4, 5, 6], 'V_candidates': [1, 2, 3, 4, 5], 'installed_materials_changed': False,
              'damage_or_state_duration_changed': False, 'art_texture': ART}
    try:
        if not all(textures.values()):
            raise RuntimeError('QV texture missing; author existing F GoldFlow first if unavailable')
        materials = {}
        for name, body in [('QBeam', Q_BEAM), ('QVeil', Q_VEIL), ('Contact', CONTACT), ('Burst', BURST),
                           ('VPrelude', V_PRELUDE), ('VColumn', V_COLUMN), ('VReveal', V_REVEAL), ('VWingFlow', V_WING_FLOW),
                           ('CelestialAperture', CELESTIAL_APERTURE), ('CelestialColumn', CELESTIAL_COLUMN),
                           ('CelestialPool', CELESTIAL_POOL), ('CelestialPlume', CELESTIAL_PLUME),
                           ('CelestialScatter', CELESTIAL_SCATTER), ('VPrimeRay', V_PRIME_RAY),
                           ('VCelestialColumn', V_CELESTIAL_COLUMN), ('DawnCurtains', DAWN_CURTAINS), ('DawnCore', DAWN_CORE),
                           ('DawnOverture', DAWN_OVERTURE), ('DawnPool', DAWN_POOL), ('DawnShock', DAWN_SHOCK),
                           ('DawnSparks', DAWN_SPARKS), ('DawnSpears', DAWN_SPEARS), ('DawnVCore', DAWN_V_CORE),
                           ('DawnVCurtains', DAWN_V_CURTAINS)]:
            selected_textures = dict(textures)
            if name.startswith('Dawn'):
                selected_textures['Plasma'] = unreal.load_asset(PLASMA)
                if not selected_textures['Plasma']:
                    raise RuntimeError('Missing existing Sparrow plasma texture')
            materials[name], row = _material(name, body, selected_textures)
            result['materials'].append(row)
        for name, geometry, material in [('SM_QVFluxFold', _flux_fold(), materials['QBeam']),
                                         ('SM_QVPrism', _prism(), materials['QBeam']),
                                         ('SM_QVGroundFray', _frays(), materials['Contact']),
                                         ('SM_QVFlameCrown', _frays(True), materials['Burst']),
                                         ('SM_QVShardCrown', _shard_crown(), materials['Burst']),
                                         ('SM_QVStraightVolume', _straight_volume(), materials['CelestialColumn']),
                                         ('SM_QVCelestialDisc', _celestial_disc(), materials['CelestialAperture']),
                                         ('SM_QVContactBillow', _contact_billow(), materials['CelestialPlume']),
                                         ('SM_QVContactSpray', _contact_spray(), materials['CelestialScatter']),
                                         ('SM_QVDawnCurtains', _dawn_curtains(), materials['DawnCurtains']),
                                         ('SM_QVDawnShock', _dawn_shock(), materials['DawnShock']),
                                         ('SM_QVDawnSpears', _dawn_spears(), materials['DawnSpears'])]:
            result['meshes'].append(_mesh(output, name, geometry, material))
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (output / 'qv-design-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


PLUME_CORE = r'''
// Axis-centred ribbon: the bright core no longer lives on a wide shell's front.
float side=y-.5;
float core=exp(-pow(side/.16,2.));
float skirt=exp(-pow(side/.40,2.))*.16;
float flow=Texture2DSample(Flow,FlowSampler,float2(y*2.+Index*.13,x*3.2+Age*1.9)).r;
float lower=smoothstep(0.,.009,x), upper=1.-smoothstep(.90,1.,x);
float3 color=lerp(float3(2.05,.91,.14),float3(3.25,2.65,1.24),core);
return float4(color,(core*(.64+flow*.16)+skirt)*lower*upper*Envelope);
'''

PLUME_VEIL = r'''
float side=abs(y-.5)*2.;
float edge=pow(saturate(1.-side*side),1.65);
// Narrow, irregular longitudinal fibres; opacity, not white exposure, supplies volume.
float flow=Texture2DSample(Flow,FlowSampler,float2(y*9.+Index*.31,x*.82+Age*1.24)).r;
float detail=Texture2DSample(Flow,FlowSampler,float2(y*29.+Index*.07,x*1.9+Age*2.05)).g;
float fibre=pow(smoothstep(.27,.77,flow*.62+detail*.38),2.);
float ribbon=pow(saturate(1.-side),.8)*(.07+.21*fibre);
float grain=Texture2DSample(FlowArt,FlowArtSampler,float2(frac(x*.24+Age*.68),.07+y*.86)).a;
float axial=smoothstep(0.,.012,x)*(1.-smoothstep(.84,1.,x));
float3 color=lerp(float3(.70,.19,.018),float3(2.5,1.14,.16),fibre);
return float4(color,(ribbon+grain*.045)*edge*axial*Envelope);
'''

PLUME_TIP = r'''
float side=(y-.5)*2.;
float hot=exp(-pow(side/.23,2.)-pow((x-.15)/.16,2.));
float mist=exp(-pow(side/.72,2.)-pow((x-.22)/.30,2.));
float fibres=smoothstep(.25,.70,n*.6+fine*.4);
float3 color=lerp(float3(1.2,.40,.035),float3(3.25,2.14,.72),hot);
return float4(color,(hot*.55+mist*fibres*.23)*smoothstep(0.,.03,x)*Envelope);
'''

PLUME_CONTACT = r'''
float t=max(ContactAge,0.);
float radial=exp(-pow(x/.53,2.));
float crushed=pow(saturate(1.-x),2.3);
float tex=Texture2DSample(Flow,FlowSampler,float2(x*2.7,y*5.3+Index*.3)+float2(t*.43,0)).r;
float grain=smoothstep(.14,.72,tex);
float flash=exp(-t*15.);
float3 color=lerp(float3(.72,.24,.025),float3(2.7,1.34,.26),crushed);
color+=float3(.65,.49,.20)*flash*crushed;
return float4(color,(radial*.18+crushed*(.32+flash*.26))*(.48+.52*grain)*Envelope);
'''

PLUME_BURST = r'''
float v=frac(y), t=max(ContactAge,0.);
// T_Plasma_Wisps is an 8x8 atlas. B contains bright padding; only A is density.
// Sampling max(RGB) filled the curved support mesh and exposed flat gold petals.
float laneSeed=frac(floor(y)*.754877+Index*.231);
float frame=clamp(12.+t*88.+laneSeed*8.,0.,62.);
float f0=floor(frame), f1=min(63.,f0+1.);
float2 localUV=clamp(float2(v,1.-x)+float2((fine-.5)*.018,(n-.5)*.016),.006,.994);
float2 atlas0=(float2(fmod(f0,8.),floor(f0/8.))+localUV)/8.;
float2 atlas1=(float2(fmod(f1,8.),floor(f1/8.))+localUV)/8.;
float vapor=lerp(Texture2DSample(Plasma,PlasmaSampler,atlas0).a,
                 Texture2DSample(Plasma,PlasmaSampler,atlas1).a,frac(frame));
float density=pow(saturate(vapor*2.6),.67);
float hot=pow(saturate(vapor*1.8),2.4);
float edge=smoothstep(0.,.07,v)*(1.-smoothstep(.93,1.,v));
float hem=smoothstep(0.,.025,x)*(1.-smoothstep(.84,1.,x));
float3 color=lerp(float3(.48,.115,.009),float3(2.5,1.12,.14),density);
color+=float3(.54,.40,.15)*hot;
return float4(color,density*.78*edge*hem*Envelope);
'''

PLUME_SPARKS = r'''
float v=frac(y), t=max(ContactAge,0.);
float axialMask=smoothstep(0.,.10,x)*(1.-smoothstep(.70,1.,x));
float side=pow(saturate(1.-abs(v-.5)*2.),1.2);
float particle=floor(y*.5);
float keep=1.-smoothstep(.18+frac(particle*.618)*.12,.34+frac(particle*.618)*.16,t);
return float4(float3(3.0,1.75,.38),axialMask*side*keep*Envelope*.8);
'''


def _light_ribbon():
    """A centre-axis light surface. No cylinder front wall or end cap."""
    vertices, uvs, faces = [], [], []
    rows, columns = 24, 12
    for row in range(rows + 1):
        for column in range(columns + 1):
            u, v = row / rows, column / columns
            vertices.append((u * 100., (v - .5) * 100., 0.))
            uvs.append((u, v))
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column + 1
            faces.extend(((a, a + 1, a + columns + 2), (a, a + columns + 2, a + columns + 1)))
    return vertices, uvs, faces


def author_plume(output):
    """Q8 / V7 only. Original Q, V4/V6 and source pack assets stay unchanged."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    textures = {key: unreal.load_asset(path) for key, path in
                [('FlowArt', ART), ('Flow', NOISE), ('Rays', RAYS), ('Plasma', PLASMA)]}
    result = {'passed': False, 'materials': [], 'meshes': [], 'Q_candidate': 8, 'V_candidate': 7,
              'normal_Q_unchanged': True, 'damage_or_state_duration_changed': False}
    try:
        if not all(textures.values()):
            raise RuntimeError('Missing an existing source texture for Q8/V7')
        materials = {}
        for name, body in [('PlumeCore', PLUME_CORE), ('PlumeVeil', PLUME_VEIL), ('PlumeTip', PLUME_TIP),
                           ('PlumeContact', PLUME_CONTACT), ('PlumeBurst', PLUME_BURST), ('PlumeSparks', PLUME_SPARKS)]:
            materials[name], row = _material(name, body, textures)
            result['materials'].append(row)
        result['meshes'].append(_mesh(output, 'SM_QVLightRibbon', _light_ribbon(), materials['PlumeCore']))
        for name in ('SM_QVCelestialDisc', 'SM_QVContactBillow', 'SM_QVContactSpray', 'SM_QVGroundFray'):
            if not unreal.load_asset(ROOT + '/' + name):
                raise RuntimeError('Existing visual mesh missing: ' + name)
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (output / 'qv-plume-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def author_v6(output):
    """Clone the connected final V4 surfaces, including their soft lower edge."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    textures = {key: unreal.load_asset(path) for key, path in [('FlowArt', ART), ('Flow', NOISE), ('Rays', RAYS)]}
    result = {'passed': False, 'materials': [], 'selector': 6, 'geometry_changed': False,
              'Q_changed': False, 'default_changed': False, 'brightness_palette_changed': False}
    try:
        if not all(textures.values()):
            raise RuntimeError('V6 source texture missing')
        for name in ('SM_QVStraightVolume', 'SM_QVCelestialDisc', 'SM_QVContactBillow', 'SM_QVGroundFray'):
            if not unreal.load_asset(ROOT + '/' + name):
                raise RuntimeError('V4 geometry missing: ' + name)
        lib = unreal.MaterialEditingLibrary
        for source_name, target_name, replacements in (
                ('VPrimeRay', 'V4GroundedRay', []),
                ('VCelestialColumn', 'V4GroundedColumn', [])):
            source_path, target_path = ROOT + '/M_' + source_name, ROOT + '/M_' + target_name
            source = unreal.load_asset(source_path)
            target = unreal.load_asset(target_path) or unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
            assert isinstance(source, unreal.Material) and isinstance(target, unreal.Material)
            target_nodes = [n for n in lib.get_material_expressions(target)
                            if n.get_class().get_name() == 'MaterialExpressionCustom']
            # Use the final V4 graph shown in V4_form_t1050/t1650, not the older
            # disconnected core-12 draft from refined60. Preserve its lower fade;
            # shortening that fade exposed the front of the cylinder as a cut cap.
            connected_custom, seen = [], set()
            pending = [lib.get_material_property_input_node(source, prop) for prop in
                       (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY)]
            while pending:
                expression = pending.pop()
                if expression is None or expression.get_path_name() in seen:
                    continue
                seen.add(expression.get_path_name())
                if expression.get_class().get_name() == 'MaterialExpressionCustom':
                    connected_custom.append(expression)
                pending.extend(n for n in lib.get_inputs_for_material_expression(source, expression) if n is not None)
            assert len(connected_custom) == 1, 'Ambiguous live V4 graph: ' + source_name
            connected_source = connected_custom[0]
            source_node = connected_source
            target_nodes = [n for n in target_nodes if n.get_name() == connected_source.get_name()]
            assert len(target_nodes) == 1, 'Connected V4 shader absent from clone: ' + target_name
            target_node = target_nodes[0]
            live_inputs = [n for n in lib.get_inputs_for_material_expression(source, connected_source) if n is not None]
            clone_inputs = [n for n in lib.get_inputs_for_material_expression(target, target_node) if n is not None]
            assert len(live_inputs) == len(clone_inputs) > 0, 'Copied V4 Custom inputs differ'
            original = str(source_node.get_editor_property('code'))
            code = original
            for old, new in replacements:
                assert code.count(old) == 1, 'Stored V4 source differs: ' + old
                code = code.replace(old, new)
            target_node.set_editor_property('code', code)
            before = _q7_property_inputs(target)
            for prop in (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY):
                mask = lib.get_material_property_input_node(target, prop)
                assert mask and mask.get_class().get_name() == 'MaterialExpressionComponentMask'
                assert lib.connect_material_expressions(target_node, '', mask,
                                                         lib.get_material_expression_input_names(mask)[0])
            assert before == _q7_property_inputs(target)
            errors = [str(e) for e in (lib.recompile_material(target) or [])]
            assert not errors, '\n'.join(errors)
            assert str(source_node.get_editor_property('code')) == original
            assert unreal.EditorAssetLibrary.save_loaded_asset(target, False)
            result['materials'].append({'source': source_path, 'path': target_path,
                                        'source_code_hash': hashlib.sha256(original.encode()).hexdigest(),
                                        'restored_source_shader': source_node.get_name(),
                                        'connected_target_shader': target_node.get_name(),
                                        'connected_input_count': len(clone_inputs),
                                        'source_shader_unchanged': code == original,
                                        'soft_lower_edge_preserved': True, 'compile_errors': errors})
        _, row = _material('VAnchoredContact', V_ANCHORED_CONTACT, textures)
        result['materials'].append(row)
        result['passed'] = True
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        (output / 'v6-grounded-materials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def audit_v6_geometry(output):
    """Read the imported axial pivot and the actual stored V4/V6 shaders."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'read_only': True, 'assets_saved': False, 'meshes': [], 'materials': []}
    for name in ('SM_QVStraightVolume', 'SM_QVCelestialDisc'):
        mesh = unreal.load_asset(ROOT + '/' + name)
        box = mesh.get_bounding_box()
        section = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0)
        vertices, uvs = section[0], section[3]
        row = {'name': name, 'box_min': [box.min.x, box.min.y, box.min.z],
               'box_max': [box.max.x, box.max.y, box.max.z], 'vertex_count': len(vertices)}
        row['vertex_min'] = [min(getattr(v, axis) for v in vertices) for axis in ('x', 'y', 'z')]
        row['vertex_max'] = [max(getattr(v, axis) for v in vertices) for axis in ('x', 'y', 'z')]
        row['uv_range'] = [[min(getattr(v, axis) for v in uvs), max(getattr(v, axis) for v in uvs)] for axis in ('x', 'y')]
        report['meshes'].append(row)
    lib = unreal.MaterialEditingLibrary
    for name in ('VCelestialColumn', 'VAnchoredColumn', 'VPrimeRay', 'VAnchoredRay',
                 'CelestialPool', 'VAnchoredContact'):
        material = unreal.load_asset(ROOT + '/M_' + name)
        row = {'name': name, 'custom_code': [], 'textures': []}
        for node in lib.get_material_expressions(material):
            if node.get_class().get_name() == 'MaterialExpressionCustom':
                row['custom_code'].append({'node': node.get_name(), 'code': str(node.get_editor_property('code'))})
        row['textures'] = [texture.get_path_name() for texture in lib.get_material_used_textures(material)]
        report['materials'].append(row)
    report['passed'] = True
    (output / 'v6-geometry-material-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


# Q7 reuses the authored projectile/contact surfaces, not Gideon's skill logic.
# The original particle timing, opacity, spline deformation and UVs are retained.
Q7_ROOT = ROOT + '/Q7SourceGold'
Q7_SYSTEMS = {
    'Projectile': '/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_Projectile',
    'Contact': '/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Primary/FX/P_Gideon_Primary_HitWorld',
}
Q7_MARKER = 'Q7 final emission gold mapping v1'
Q7_GOLD = r'''
// Preserve the original animated value detail, then remove only the hue.
// maxRGB preserves the source purple's energy without multiplying blue into gold.
float energy=max(0.,max(Source.r,max(Source.g,Source.b)));
float hot=smoothstep(.65,3.2,energy);
float3 tint=lerp(float3(1.,.39,.055),float3(1.,.86,.48),hot*.58);
// A soft shoulder keeps source HDR spikes from making broad white explosions.
float shoulder=energy<=3.0?energy:3.0+(energy-3.0)/(1.0+(energy-3.0)/3.0);
return tint*shoulder;
'''


def _q7_owned_path(source):
    package = source.get_path_name().split('.')[0]
    suffix = hashlib.sha256(package.encode()).hexdigest()[:8]
    return Q7_ROOT + '/' + source.get_name() + '_' + suffix + '_Gold'


def _q7_property_inputs(material):
    lib = unreal.MaterialEditingLibrary
    result = {}
    for name in ('EMISSIVE_COLOR', 'BASE_COLOR', 'OPACITY', 'OPACITY_MASK',
                 'WORLD_POSITION_OFFSET', 'REFRACTION', 'NORMAL'):
        prop = getattr(unreal.MaterialProperty, 'MP_' + name)
        expression = lib.get_material_property_input_node(material, prop)
        result[name] = {'node': expression.get_name() if expression else None,
                        'output': str(lib.get_material_property_input_node_output_name(material, prop))
                                  if expression else None}
    return result


def _q7_source_read():
    lib = unreal.MaterialEditingLibrary
    sources, systems, material_map, limitations = {}, [], {}, []
    for label, path in Q7_SYSTEMS.items():
        source = unreal.load_asset(path)
        assert isinstance(source, unreal.ParticleSystem), path
        sources[label] = source
        prefix = source.get_path_name() + ':'
        row = {'label': label, 'source': path, 'required_materials': [], 'mesh_slots': [],
               'light_modules': [], 'mesh_material_modules': [], 'color_module_classes': []}
        for obj in unreal.ObjectIterator(unreal.Object):
            if isinstance(obj, type):
                continue
            try:
                object_path = obj.get_path_name()
            except (TypeError, RuntimeError):
                continue
            if not object_path.startswith(prefix):
                continue
            kind = obj.get_class().get_name()
            if kind == 'ParticleModuleRequired':
                material = obj.get_editor_property('material')
                if material:
                    material_map[material.get_path_name()] = material
                    row['required_materials'].append({'module': obj.get_name(),
                                                       'material': material.get_path_name()})
            elif kind == 'ParticleModuleTypeDataMesh':
                mesh = obj.get_editor_property('mesh')
                if mesh:
                    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
                        material = slot.get_editor_property('material_interface')
                        if material:
                            material_map[material.get_path_name()] = material
                            row['mesh_slots'].append({'mesh': mesh.get_path_name(), 'slot': index,
                                                      'material': material.get_path_name()})
            elif kind == 'ParticleModuleMeshMaterial':
                module_row = {'module': obj.get_name(), 'materials': []}
                try:
                    for material in obj.get_editor_property('mesh_materials'):
                        if material:
                            material_map[material.get_path_name()] = material
                            module_row['materials'].append(material.get_path_name())
                except Exception as error:
                    module_row['protected'] = str(error)
                    limitations.append('Native mesh-material resolution required: ' + object_path)
                row['mesh_material_modules'].append(module_row)
            elif 'ParticleModuleLight' in kind:
                row['light_modules'].append(obj.get_name())
            elif kind.startswith('ParticleModuleColor'):
                row['color_module_classes'].append(kind)
        systems.append(row)
    materials = []
    for path, material in sorted(material_map.items()):
        base = material.get_base_material()
        instance = isinstance(material, unreal.MaterialInstanceConstant)
        row = {'source': path, 'base': base.get_path_name(), 'target': _q7_owned_path(material),
               'class': material.get_class().get_name(), 'inputs': _q7_property_inputs(base),
               'blend_mode': str(base.get_editor_property('blend_mode')),
               'scalars': {}, 'vectors': {}, 'texture_paths': [], 'parent_chain': []}
        for name in lib.get_scalar_parameter_names(material):
            row['scalars'][str(name)] = (lib.get_material_instance_scalar_parameter_value(material, name)
                                         if instance else lib.get_material_default_scalar_parameter_value(base, name))
        for name in lib.get_vector_parameter_names(material):
            color = (lib.get_material_instance_vector_parameter_value(material, name)
                     if instance else lib.get_material_default_vector_parameter_value(base, name))
            row['vectors'][str(name)] = [color.r, color.g, color.b, color.a]
        row['texture_paths'] = [texture.get_path_name() for texture in lib.get_material_used_textures(base)]
        parent = material
        while isinstance(parent, unreal.MaterialInstanceConstant):
            parent = parent.get_editor_property('parent')
            assert parent, 'Missing source parent: ' + path
            row['parent_chain'].append(parent.get_path_name())
        materials.append(row)
    return sources, material_map, {'passed': True, 'read_only': True, 'assets_saved': False,
                                 'systems': systems, 'materials': materials, 'limitations': limitations,
                                 'normal_Q_changed': False,
                                 'native_clone_must_strip_lights': True,
                                 'protected_color_curves_need_no_edit': True}


def audit_q7(output):
    """Read exact source graph/mesh-material routes; no compilation or asset writes."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    _, _, report = _q7_source_read()
    (output / 'q7-source-color-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def author_q7(output):
    """Clone complete MIC parent chains; wrap only final emission, never source assets.

    Native Q7 will transient-clone the source ParticleSystems, replace required and
    mesh-module materials using this manifest, and remove their dynamic lights.
    This author does not save particle systems or change ordinary Q/defaults.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    _, originals, audit = _q7_source_read()
    (output / 'q7-source-color-audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    report = {'passed': False, 'materials': [], 'source_file_hashes': {}, 'normal_Q_changed': False,
              'native_material_resolution_required': audit['limitations'],
              'particles_saved': False, 'default_changed': False}
    copies = {}

    def source_hash(source):
        package = source.get_path_name().split('.')[0]
        assert package.startswith('/Game/'), package
        file = Path(unreal.Paths.project_content_dir()) / (package[len('/Game/'):] + '.uasset')
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        report['source_file_hashes'][str(file)] = digest

    def clone(source):
        key = source.get_path_name()
        if key in copies:
            return copies[key]
        source_hash(source)
        target_path = _q7_owned_path(source)
        target = unreal.load_asset(target_path)
        if target is None:
            target = unreal.EditorAssetLibrary.duplicate_asset(key.split('.')[0], target_path)
        assert target and target.get_class() == source.get_class(), target_path
        tag = unreal.EditorAssetLibrary.get_metadata_tag(target, 'Q7SourceMaterial')
        assert not tag or tag == key, 'Unrelated target material: ' + target_path
        row = {'source': key, 'target': target_path, 'class': target.get_class().get_name()}
        if isinstance(source, unreal.MaterialInstanceConstant):
            # Duplicating every link preserves static switches and inherited/local
            # parameter overrides. Flattening to the base would silently lose them.
            original_parent = source.get_editor_property('parent')
            assert original_parent
            copied_parent = clone(original_parent)
            lib.set_material_instance_parent(target, copied_parent)
            lib.update_material_instance(target)
            row['parent'] = copied_parent.get_path_name()
        else:
            assert isinstance(source, unreal.Material), key
            before = _q7_property_inputs(source)
            wrappers = [node for node in lib.get_material_expressions(target)
                        if node.get_editor_property('desc') == Q7_MARKER]
            assert len(wrappers) <= 1, 'Repeated Q7 output wrapper'
            if before['EMISSIVE_COLOR']['node']:
                if wrappers:
                    wrapper = wrappers[0]
                else:
                    previous = lib.get_material_property_input_node(target, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                    pin_name = lib.get_material_property_input_node_output_name(target, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                    wrapper = lib.create_material_expression(target, unreal.MaterialExpressionCustom)
                    wrapper.set_editor_property('desc', Q7_MARKER)
                    wrapper.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
                    pin = unreal.CustomInput()
                    pin.set_editor_property('input_name', 'Source')
                    wrapper.set_editor_property('inputs', [pin])
                    assert lib.connect_material_expressions(previous, pin_name, wrapper, 'Source')
                wrapper.set_editor_property('code', Q7_GOLD)
                assert lib.connect_material_property(wrapper, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            after = _q7_property_inputs(target)
            for name, value in before.items():
                if name != 'EMISSIVE_COLOR':
                    assert after[name] == value, 'Q7 changed original ' + name + ': ' + key
            errors = [str(error) for error in (lib.recompile_material(target) or [])]
            assert not errors, '\n'.join(errors)
            row['emissive_wrapped'] = bool(before['EMISSIVE_COLOR']['node'])
            row['other_outputs_preserved'] = True
        unreal.EditorAssetLibrary.set_metadata_tag(target, 'Q7SourceMaterial', key)
        assert unreal.EditorAssetLibrary.save_loaded_asset(target, False)
        copies[key] = target
        report['materials'].append(row)
        return target

    try:
        unreal.EditorAssetLibrary.make_directory(Q7_ROOT)
        for original in originals.values():
            clone(original)
        for file, digest in report['source_file_hashes'].items():
            assert hashlib.sha256(Path(file).read_bytes()).hexdigest() == digest, 'Source material changed: ' + file
        report['source_files_unchanged'] = True
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (output / 'q7-gold-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
