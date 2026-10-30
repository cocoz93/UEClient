"""Q-adjacent R/S visual study assets. Default gameplay and original art stay intact."""
import hashlib
import json
from pathlib import Path
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/Celestial20261026'
IMPACT_FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/Impact20261027'
SERAPH_FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/SeraphStudies20261027'
REVISION_FOLDER = '/Game/TopDown/Characters/Sparrow/Materials/ImpactRevision20261027'
PLASMA_TEXTURE = '/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps'
NOISE = '/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_Perlin_Soft_Packed'
IMPACT_TEXTURES = {
    'Rays': '/Game/ParagonSparrow/FX/Textures/Heroes/T_ShieldLightrays',
    'Fire': '/Game/ParagonSparrow/FX/Textures/Fire/T_FireNoiseTile_02',
    'Shock': '/Game/ParagonSparrow/FX/Textures/Masks/T_Shockwave',
    'Flare': '/Game/ParagonSparrow/FX/Textures/Flares/T_SparrowFlare',
}
COMMON = r'''
float2 p=(UV-.5)*2.;
float aa=max(length(fwidth(p))*.60,.004);
float noise=Texture2DSample(Flow,FlowSampler,UV*2.5+float2(-Age*.9,Index*.183)).r;
float detail=Texture2DSample(Flow,FlowSampler,UV*7.1+float2(-Age*2.1,Index*.267)).g;
float3 amber=float3(1.3,.31,.018),gold=float3(3.4,1.65,.28),whitegold=float3(5.1,4.35,2.4);
float released=1.-step(10.,PulseAge);
float kick=released*exp(-max(0.,PulseAge)*18.);
float edge=(1.-smoothstep(.86,1.,abs(p.x)))*(1.-smoothstep(.86,1.,abs(p.y)));
float form=1.+Ascended*.22;
struct Forms {
 float segment(float2 p0,float2 a,float2 b) { float2 ab=b-a;float f=saturate(dot(p0-a,ab)/max(dot(ab,ab),.00001));return length(p0-a-ab*f); }
};
Forms shape;
'''

CRESCENT = r'''
if(Sharp<.5 && Style>2.5){
 float x=UV.x;
 float taper=pow(saturate(sin(x*3.141593)),.72);
 float curve=.10*sin(x*3.141593)*(Index<1.5?1.:-1.);
 float d=p.y-curve;
 float width=(.17+.03*noise)*taper;
 float body=(1.-smoothstep(width-aa*1.8,width+aa*1.8,abs(d)))*smoothstep(.02,.12,x)*(1.-smoothstep(.88,.99,x));
 float grain=.24+.42*noise+.18*detail;
 float channel=pow(saturate(cos(x*19.-Age*18.+Index)),7.);
 float ridge=exp(-pow((d-width*.35)/(.012+aa),2.))*taper;
 float edgecut=exp(-pow((abs(d)-width*.88)/(.013+aa),2.))*taper;
 float sheath=exp(-pow(d/(width+.065),2.))*taper*(.12+detail*.26);
 float chips=pow(saturate(detail*1.9-.78),4.)*exp(-pow((abs(d)-width-.04)/.06,2.))*taper;
 float strength=(.55+.45*Progress)*(1.+kick*.28)*Envelope*form;
 float3 rgb=amber*body*grain*1.4+gold*(body*(.30+channel*.35)+sheath*.5+chips*.5)+whitegold*(ridge*.20+edgecut*.12);
 float alpha=body*(.47+grain*.20)+ridge*.27+edgecut*.23+sheath*.25+chips*.35;
 return float4(rgb*strength*edge,saturate(alpha)*strength*edge);
}
float r=length(p+float2(.16,0.));
float angle=atan2(p.y,p.x+.16);
float mask=smoothstep(-.60,-.12,p.x)*(1.-smoothstep(.83,.95,abs(p.y)));
float seam=abs(r-.72);
float tissue=exp(-pow(seam/.085,2.))*mask*(.32+noise*.54+detail*.23);
float edgecore=exp(-pow((seam-.022)/(.010+aa),2.))*mask;
float vein=exp(-pow((r-.62)/(.012+aa),2.))*mask*(.3+.7*pow(saturate(cos(angle*13.-Age*18.+Index)),7.));
float engraving=pow(saturate(cos(angle*36.+Index*2.)),16.)*exp(-pow(seam/.055,2.))*mask;
float fringe=exp(-pow((r-.83)/.08,2.))*mask*pow(saturate(detail*1.8-.48),3.);
float fragments=0.;
for(int i=0;i<10;i++){
 float a=-1.26+float(i)*.28;
 float2 radial=float2(cos(a),sin(a));
 float2 q=p+float2(.16,0.)-radial*(.77+kick*.08);
 float along=dot(q,radial),side=abs(q.x*radial.y-q.y*radial.x);
 fragments+=1.-smoothstep(.7,1.,abs(along)/(.035+.012*sin(i+Index))+side/.012);
}
float weight=(.45+.55*Progress)*(1.+kick*.4)*form*Envelope;
float3 rgb=amber*tissue+gold*(tissue*.85+vein*.5+fringe*.45)+whitegold*(edgecore*.20+engraving*.12+fragments*.30);
return float4(rgb*weight*edge,saturate(tissue*.60+edgecore*.38+vein*.32+engraving*.22+fringe*.22+fragments*.6)*weight*edge);
'''

PRISM = r'''
if(Sharp<.5){
 float leaves=0.,ridges=0.,dust=0.;
 for(int i=0;i<8;i++){
  float a=float(i)*.785398+Index*.045;
  float h=frac(sin(float(i)*39.71+Index*2.7)*3711.3);
  float2 radial=float2(cos(a),sin(a));
  float2 tangent=float2(-radial.y,radial.x);
  float2 axis=normalize(tangent+radial*(.35+h*.22));
  float2 q=p-radial*(.62+.04*sin(Age*4.+i*1.7+Index));
  float along=dot(q,axis), side=q.x*axis.y-q.y*axis.x;
  float span=.19+h*.085;
  float taper=pow(saturate(1.-abs(along)/span),.70);
  float width=(.068+h*.032)*taper;
  float bounds=1.-smoothstep(span-aa,span+aa,abs(along));
  float leaf=(1.-smoothstep(width-aa,width+aa,abs(side)))*bounds;
  leaves+=leaf*(.35+noise*.42+detail*.17);
  ridges+=exp(-pow((side+width*.24)/(.009+aa),2.))*bounds*taper;
  float2 chip=p-radial*(.81+kick*.065);
  float chipAlong=dot(chip,axis),chipSide=abs(chip.x*axis.y-chip.y*axis.x);
  dust+=(1.-smoothstep(.70,1.,abs(chipAlong)/.043+chipSide/.020))*(.4+.6*h);
 }
 float separation=1.-smoothstep(.24,.43,length(p));
 leaves*=1.-separation;
 float weight=(.56+.44*Progress)*Envelope*form;
 float3 rgb=amber*leaves*1.5+gold*(leaves*.75+dust*.30)+whitegold*(ridges*.18+dust*.22);
 float alpha=leaves*.76+ridges*.30+dust*.47;
 return float4(rgb*weight*edge,saturate(alpha)*weight*edge);
}
float r=Sharp>.5?length(p):abs(p.x)*.75+abs(p.y);
float contour=Sharp>.5?.69:.66;
float band=abs(r-contour);
float tissue=exp(-pow(band/.075,2.))*(.32+noise*.53);
float core=exp(-pow(band/(.010+aa),2.));
float inner=exp(-pow((r-contour+.13)/(.014+aa),2.));
float angle=atan2(p.y,p.x);
float filigree=pow(saturate(cos(angle*(Sharp>.5?12.:8.)+Index)),12.)*exp(-pow(band/.12,2.));
float flow=pow(saturate(cos(r*51.-Age*19.+Index*2.)),9.);
float sparks=pow(saturate(detail*1.8-.66),4.)*exp(-pow((r-contour-.09)/.11,2.));
float3 rgb=amber*tissue+gold*(tissue*(.7+flow*.6)+inner*.25+sparks*.8)+whitegold*(core*.22+filigree*.21);
float alpha=tissue*.58+core*.43+inner*.22+filigree*.30+sparks*.45;
return float4(rgb*Envelope*form*edge,saturate(alpha)*Envelope*edge);
'''

FILAMENT = r'''
float x=UV.x;
float taper=pow(saturate(sin(x*3.141593)),.65);
float curvature=Style<1.5?.20:Style<2.5?-.11:.035;
float y=sin(x*3.141593)*curvature;
float dist=p.y-y;
float width=(.075+.095*taper)*(Style>2.5?.70:1.);
float tissue=exp(-pow(dist/width,2.))*taper*(.2+noise*.55+detail*.22);
float narrow=exp(-pow((dist-width*.20)/(.009+aa),2.))*taper;
float thread=exp(-pow((dist+width*.72)/(.010+aa),2.))*taper;
float running=pow(saturate(cos(x*28.-Age*27.+Index*1.7)),10.);
float broken=exp(-pow((abs(dist)-width*1.45)/.06,2.))*taper*pow(saturate(detail*1.9-.68),3.);
float notch=1.-smoothstep(.72,.90,x);
float tip=exp(-pow((x-.82)/.035,2.))*exp(-pow(dist/.08,2.));
float3 rgb=amber*tissue+gold*(tissue*(.65+running*.9)+broken*.6)+whitegold*(narrow*.30+thread*.12+tip*.30);
float alpha=tissue*.58+narrow*.42+thread*.23+broken*.27+tip*.25;
return float4(rgb*Envelope*form*edge,saturate(alpha)*Envelope*edge);
'''

FRACTURE = r'''
float t=max(0.,PulseAge);
float pieces=0.,trails=0.;
for(int i=0;i<10;i++){
 float h=frac(sin(float(i)*53.7+Index*9.1)*7171.3);
 float ang=float(i)*2.399963+Index*.85;
 float2 axis=float2(cos(ang),sin(ang));
 float2 q=p-axis*(.035+t*(1.7+h*1.3));
 float along=dot(q,axis),side=abs(q.x*axis.y-q.y*axis.x);
 pieces+=1.-smoothstep(.70,1.,abs(along)/(.025+h*.035)+side/(.012+h*.006));
 trails+=exp(-pow(side/(.006+aa),2.))*(1.-smoothstep(.02,.09+h*.06,abs(along)));
}
float snap=exp(-dot(p,p)/.012)*exp(-t*30.);
float3 rgb=gold*trails*.62+whitegold*(pieces*.34+snap*.22);
float alpha=trails*.37+pieces*.63+snap*.35;
return float4(rgb*Envelope*form*edge,saturate(alpha)*Envelope*edge);
'''


# Original PNGs and separate RGB channels were inspected in texture-inspection.
# Shield R contains fine rays, B the torn luminous veil; G is a broad smooth mask.
# Fire RGB are identical. Shock/Flare use R. The explosion atlas is deliberately unused.
IMPACT_COMMON = r'''
float2 p=(UV-.5)*2.;
float aa=max(length(fwidth(p))*.62,.004);
float r=length(p);
float angle=atan2(p.y,p.x)*.159154943+.5;
float fire=Texture2DSample(Fire,FireSampler,UV*1.9+float2(-Age*.90,Index*.137)).r;
float grain=Texture2DSample(Fire,FireSampler,UV*4.3+float2(Age*.37,Index*.279)).r;
float3 amber=float3(1.65,.32,.022),gold=float3(5.8,2.35,.32),ivory=float3(8.0,6.1,3.0);
float released=1.-step(10.,PulseAge);
float kick=released*exp(-max(0.,PulseAge)*29.);
float form=1.+Ascended*.25;
float bounds=(1.-smoothstep(.88,.99,abs(p.x)))*(1.-smoothstep(.88,.99,abs(p.y)));
'''

RECOIL = r'''
float x=UV.x;
float width=.09+x*.90;
float head=released>.5?min(.94,.14+max(0.,PulseAge)*11.82):.10+Progress*.11;
float across=p.y/max(width,.06);
float veil=0.,fibers=0.,hot=0.;
// Three offset pressure folds; no shared straight leading edge across the fan.
for(int i=0;i<3;i++){
 float center=i==0?-.52:(i==1?.02:.54);
 float spread=i==0?.39:(i==1?.37:.43);
 float delay=i==0?.11:(i==1?0.:.065);
 float contour=Texture2DSample(Fire,FireSampler,float2(across*.39+Index*.17+i*.31,Age*.25+i*.113)).r;
 float localHead=head-delay+(contour-.5)*.10;
 float behind=localHead-x;
 float packet=smoothstep(-.018,.018,behind)*(1.-smoothstep(.15,.32,behind));
 float lateral=exp(-pow((across-center)/spread,4.));
 float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(across*.43+.5+Index*.29+i*.217+Age*.08),saturate(behind*3.4))).rgb;
 float mask=lateral*smoothstep(.01,.08,x)*packet*(.48+.52*smoothstep(.12,.58,fire));
 veil+=rays.b*mask;
 fibers+=pow(saturate(rays.r),1.45)*mask*(.32+.68*grain);
 hot+=pow(saturate(rays.r*fire),3.)*mask;
}
float3 rgb=amber*veil*1.45+gold*(veil*.95+fibers*.90)+ivory*hot*.28;
float alpha=veil*.44+fibers*.46+hot*.24;
return float4(rgb*Envelope*form,saturate(alpha)*Envelope*bounds);
'''

PRESSURE = r'''
if(Sharp<.5){
 float y=abs(p.y);
 float width=.12+.30*(1.-y);
 float3 tissue=Texture2DSample(Rays,RaysSampler,float2(frac(p.x*.80+.5+Index*.19+Age*.16),saturate((y-.13)/.78))).rgb;
 float mask=smoothstep(.13,.26,y)*(1.-smoothstep(.78,.96,y))*(1.-smoothstep(width*.50,width,abs(p.x)));
 float veil=tissue.b*(.35+.65*fire)*mask;
 float fibers=tissue.r*(.24+.76*grain)*mask;
 float hot=pow(saturate(tissue.r*fire),3.)*mask;
 float3 rgb=amber*veil*1.2+gold*(veil*.8+fibers*.85)+ivory*hot*.23;
 return float4(rgb*Envelope*form,saturate(veil*.42+fibers*.48+hot*.22)*Envelope*bounds);
}
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(angle+Index*.193+Age*.22),saturate((r-.34)/.58))).rgb;
float shock=Texture2DSample(Shock,ShockSampler,UV).r;
float annulus=smoothstep(.35,.49,r)*(1.-smoothstep(.77,.79,r));
float veil=rays.b*annulus*(.38+.62*fire);
float fibers=rays.r*annulus*(.20+.80*grain);
float body=shock*(.30+.70*fire)*(1.-smoothstep(.77,.80,r));
float rim=exp(-pow((r-.755)/(.014+aa),2.));
float inner=exp(-pow((r-.52)/(.010+aa),2.))*(.20+.80*fire);
float hot=pow(saturate(rays.r*grain),3.)*annulus;
float threeD=.72+.28*cos(atan2(p.y,p.x)-1.4);
float3 rgb=amber*(veil*.9+body*.60)+gold*(veil*.58+body*.75+fibers*.42)+ivory*(rim*.19+inner*.11+hot*.22);
float alpha=veil*.27+body*.41+fibers*.20+rim*.43+inner*.23;
return float4(rgb*Envelope*form*threeD,saturate(alpha)*Envelope*bounds);
'''

ERUPTION = r'''
float t=max(0.,PulseAge);
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(angle+Index*.117+Age*.30),saturate((r-.20)/.78))).rgb;
float shock=Texture2DSample(Shock,ShockSampler,UV).r;
float hollow=smoothstep(.14,.29,r)*(1.-smoothstep(.84,.98,r));
float flame=rays.b*smoothstep(.13,.62,fire)*hollow;
float filaments=pow(saturate(rays.r),1.55)*(.20+.80*grain)*hollow;
float front=pow(shock,1.5)*(.35+.65*fire);
if(Sharp<.5){
 float lobes=smoothstep(.08,.26,abs(p.y))*(1.-smoothstep(.46,.86,abs(p.x)));
 flame*=lobes;
 filaments*=lobes;
 front=0.;
}
float hot=pow(saturate(filaments*1.3),3.)*exp(-t*15.);
float3 rgb=amber*flame*1.5+gold*(flame*.7+filaments*.85+front*.56)+ivory*(hot*.28+front*.12);
float alpha=flame*.36+filaments*.42+front*.37;
return float4(rgb*Envelope*form,saturate(alpha)*Envelope*bounds);
'''

STREAK = r'''
float x=UV.x;
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.y*.91+Index*.217),1.-x)).rgb;
float paths=0.,spines=0.;
for(int i=0;i<3;i++){
 float enabled=Sharp>.5?1.:(i==1?1.:0.);
 float y=p.y-(float(i)-1.)*.28;
 float mask=exp(-pow(y/(.065+.035*fire),2.))*smoothstep(.03,.14,x)*(1.-smoothstep(.80,.97,x));
 paths+=enabled*mask*(.20+rays.r*.55+rays.b*.35)*(.30+.70*grain);
 spines+=enabled*exp(-pow(y/(.012+aa),2.))*exp(-pow((x-.69)/.19,2.));
}
float3 rgb=amber*paths*.65+gold*paths*1.05+ivory*spines*.23;
float alpha=paths*.67+spines*.50;
return float4(rgb*Envelope*form,saturate(alpha)*Envelope*bounds);
'''

EMBER = r'''
float x=UV.x;
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.y*.81+Index*.241),x)).rgb;
float taper=saturate(sin(x*3.141593));
float veil=exp(-pow(p.y/(.14*taper+.018),2.))*(rays.b*.55+rays.r*.45)*(.35+.65*fire);
float core=exp(-pow(p.y/(.022+aa),2.))*exp(-pow((x-.25)/.17,2.));
float flare=Texture2DSample(Flare,FlareSampler,float2((x-.25)*1.8+.5,p.y*1.4+.5)).r;
float3 rgb=amber*veil*.6+gold*veil*1.0+ivory*(core*.30+flare*.18);
float alpha=veil*.69+core*.51+flare*.21;
return float4(rgb*Envelope*form,saturate(alpha)*Envelope*bounds);
'''


TEMPEST = r'''
float x=UV.x;
float curve=.40*sin(x*4.4-.65);
float d=p.y-curve;
float taper=pow(saturate(sin(x*3.141593)),.65);
float width=(.12+.12*fire)*taper;
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(x*.8-Age*1.1+Index*.17),saturate(abs(d)/max(width,.02)))).rgb;
float silhouette=(1.-smoothstep(width*.55,width+aa*2.,abs(d)))*taper;
float tissue=silhouette*(.20+.50*rays.b+.30*fire);
float flow=silhouette*pow(saturate(rays.r*grain*1.6),1.5);
float spine=exp(-pow((d+width*.2)/(.014+aa),2.))*taper*(.2+.8*grain);
float fringe=exp(-pow((abs(d)-width*1.25)/.06,2.))*taper*pow(saturate(fire*1.6-.5),3.);
float3 rgb=amber*tissue*1.2+gold*(tissue*.78+flow*.85+fringe*.45)+ivory*spine*.15;
return float4(rgb*Envelope*form,saturate(tissue*.62+flow*.25+fringe*.20+spine*.23)*Envelope*bounds);
'''

PLASMA = r'''
// The inspected 8x8 atlas has unusable RGB bleed; only the clean alpha is sampled.
float frame=released>.5?min(55.,28.+max(0.,PulseAge)*110.):min(25.,6.+Age*55.);
float f0=floor(frame),f1=min(63.,f0+1.);
float2 a0=(float2(fmod(f0,8.),floor(f0/8.))+clamp(UV,.006,.994))/8.;
float2 a1=(float2(fmod(f1,8.),floor(f1/8.))+clamp(UV,.006,.994))/8.;
float wisp=lerp(Texture2DSample(Plasma,PlasmaSampler,a0).a,Texture2DSample(Plasma,PlasmaSampler,a1).a,frac(frame));
wisp=pow(saturate(wisp*1.8),1.28);
float heat=pow(wisp,3.)*(.35+.65*grain);
float3 rgb=amber*wisp*.70+gold*wisp*1.15+ivory*heat*.18;
return float4(rgb*Envelope*form,saturate(wisp*.65)*Envelope*bounds);
'''

SHARD = r'''
float x=p.x;
float width=.40*pow(saturate(1.-abs(x)/.86),.88);
float asym=p.y+x*.12;
float body=(1.-smoothstep(width-aa,width+aa,abs(asym)))*(1.-smoothstep(.84,.88,abs(x)));
float rift=1.-smoothstep(.018,.046,abs(x-.23-asym*.25));
float rift2=1.-smoothstep(.012,.037,abs(x+.30+asym*.18));
float edgeErode=smoothstep(width*.45,width,abs(asym))*pow(saturate(.65-fire),2.);
body*=(1.-rift*.92)*(1.-rift2*.85)*(1.-edgeErode*.82);
float facet=lerp(.12,.68,step(x*.14,asym));
float secondary=lerp(.60,1.0,step(-x*.25-.045,asym));
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.y*.85+Index*.17-Age*.23),UV.x)).rgb;
float grainFace=body*(.23+fire*.35+rays.b*.29)*secondary;
float sweep=exp(-pow((x*.75+asym*.45-(frac(Age*1.4+Index*.173)*2.-1.))/.07,2.))*body*(.3+.7*rays.r);
float ridge=exp(-pow((asym-x*.14)/(.010+aa),2.))*body*(.3+.7*grain);
float crackLight=(rift+rift2)*body*(.20+.80*fire);
float3 rgb=amber*grainFace*(1.05-facet)+gold*(grainFace*facet*.72+sweep*.26+crackLight*.14)+ivory*ridge*.13;
return float4(rgb*Envelope*form,saturate(body*(.30+grainFace*.32)+ridge*.19+sweep*.13)*Envelope*bounds);
'''

SERAPH_FEATHER = r'''
float x=UV.x;
float center=.16*sin(x*3.141593)-.065;
float d=p.y-center;
float taper=pow(saturate(sin(x*3.141593)),.72);
float width=.32*taper*lerp(.78,1.,step(0.,d));
float shape=(1.-smoothstep(width-aa,width+aa,abs(d)))*smoothstep(.035,.12,x);
float flute=x*16.-abs(d)*9.1;
float cycle=frac(flute);
float notch=(1.-smoothstep(.10,.24,abs(cycle-.5)))*smoothstep(width*.36,width*.95,abs(d));
shape*=1.-notch*.94;
float barb=exp(-pow(min(cycle,1.-cycle)/.10,2.))*shape;
float stem=exp(-pow(d/(.010+aa*.50),2.))*(1.-smoothstep(.93,1.,x));
float rim=exp(-pow((abs(d)-width)/(.012+aa),2.))*taper*(1.-notch);
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(x-Age*.21+Index*.13),saturate(abs(d)/max(width,.015)))).rgb;
float vein=shape*(.12+fire*.24+grain*.16+rays.b*.29);
float shade=lerp(.48,1.,step(0.,d));
float sweep=pow(saturate(sin(x*13.-Age*14.+Index)),12.);
float3 rgb=amber*vein*.9+gold*(vein*.74*shade+barb*.27+rim*.06+stem*.18)+ivory*(stem*.10+barb*sweep*.14);
return float4(rgb*Envelope*form,saturate(vein*.55+barb*.31+stem*.25+rim*.10)*Envelope*bounds);
'''

FAN = r'''
float2 q=p+float2(.23,0.);
float radius=length(q);
float a=atan2(q.y,q.x);
float arc=smoothstep(-1.65,-1.24,a)*(1.-smoothstep(1.35,1.74,a));
float width=.20+.13*pow(saturate(cos(a*.68)),2.);
float seam=radius-(.57+.035*(fire-.5));
float tear=smoothstep(.06,.40,fire*.74+grain*.26);
float band=exp(-pow(seam/width,4.))*arc*(.36+.64*tear);
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(a*.32-Age*.85+Index*.21),saturate((seam+width)/(width*2.)))).rgb;
float tissue=band*(.24+.34*fire+.42*rays.b);
float broken=pow(saturate(rays.r*grain*1.6),2.)*band;
float cutting=exp(-pow((seam-width*.47)/(.018+aa),2.))*arc*(.15+.85*grain);
float fringe=exp(-pow((seam+width*1.12)/.14,2.))*arc*pow(saturate(fire*1.75-.40),3.);
float fissure=(1.-smoothstep(.012,.060,abs(sin(a*9.+Index*.83))))*smoothstep(-width*.6,width*.6,seam);
tissue*=1.-fissure*.75;
float3 rgb=amber*tissue*1.1+gold*(tissue*.76+broken*.70+fringe*.63)+ivory*cutting*.15;
return float4(rgb*Envelope*form,saturate(tissue*.69+broken*.26+fringe*.35+cutting*.20)*Envelope*bounds);
'''


# These surfaces carry a continuous gold body. Texture modulates its depth and flow;
# erosion is concentrated at the perimeter rather than reducing the whole shape to dots.
REVISION_COMMON = r'''
float2 p=(UV-.5)*2.;
float aa=max(length(fwidth(p))*.55,.004);
float fire=Texture2DSample(Fire,FireSampler,UV*1.75+float2(-Age*.67,Index*.137)).r;
float grain=Texture2DSample(Fire,FireSampler,UV*4.1+float2(Age*.29,Index*.279)).r;
float broadNoise=Texture2DSample(Flow,FlowSampler,UV*.85+float2(-Age*.42,Index*.173)).r;
float3 shadegold=float3(.88,.36,.075),gold=float3(3.45,1.92,.46),ivory=float3(7.8,6.75,4.5);
float released=1.-step(10.,PulseAge);
float shotTime=max(0.,PulseAge);
float form=1.+Ascended*.08;
float bounds=(1.-smoothstep(.86,.99,abs(p.x)))*(1.-smoothstep(.86,.99,abs(p.y)));
// The atlas alpha contains the smoke folds; its RGB contains neighbouring-cell bleed.
float atlasFrame=released>.5?min(58.,24.+shotTime*160.):min(32.,13.+Age*49.);
float atlas0=floor(atlasFrame),atlas1=min(63.,atlas0+1.);
float2 atlasLocal=clamp(UV+float2((fire-.5)*.055,(grain-.5)*.045),.006,.994);
float2 atlasUV0=(float2(fmod(atlas0,8.),floor(atlas0/8.))+atlasLocal)/8.;
float2 atlasUV1=(float2(fmod(atlas1,8.),floor(atlas1/8.))+atlasLocal)/8.;
float vapor=lerp(Texture2DSample(Plasma,PlasmaSampler,atlasUV0).a,Texture2DSample(Plasma,PlasmaSampler,atlasUV1).a,frac(atlasFrame));
float vaporBody=pow(saturate(vapor*2.2),.58);
'''

REVISION_WIND = r'''
float2 q=p+float2((broadNoise-.5)*.12,(broadNoise-.5)*.08);
float radius=length(q),angle=atan2(q.y,q.x);
float turn=angle-Age*4.8+Index*1.4;
float curlRadius=.45+.14*sin(turn*1.5)+.05*sin(turn*3.0);
float lateral=abs(radius-curlRadius)/(.25+.045*broadNoise);
float curl=exp(-pow(lateral,4.));
float mouth=pow(saturate(.5+.5*cos(turn-.45)),.40);
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(angle*.15915-Age*.82+Index*.19),saturate((radius-.14)/.68))).rgb;
float tissue=.56+.25*rays.b+.19*vaporBody;
float edge=smoothstep(.48,1.05,lateral);
float erosion=1.-edge*(1.-smoothstep(.10,.48,fire+rays.b*.20))*.70;
float density=curl*mouth*tissue*erosion;
float heat=saturate(broadNoise*.46+rays.r*.36+vaporBody*.18);
float crease=pow(heat,3.2)*(.45+.55*saturate(sin(turn*2.0-Age*12.)));
// Straight-alpha material: coverage is applied only to alpha, not to RGB twice.
float3 rgb=lerp(shadegold,gold,.28+heat*.64)+ivory*crease*.29;
return float4(rgb*form,saturate(density*.82)*Envelope*bounds);
'''

REVISION_MANTLE = r'''
float2 q=p;
q.y+=.17*sin(q.x*3.1+Age*3.5+Index*.8);
float fold=exp(-pow(abs(q.x/.76),4.)-pow(abs((q.y-.10)/.55),4.));
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.x*.83+Age*.58+Index*.27),saturate(UV.y*.85+.05))).rgb;
float innerFold=smoothstep(.025,.13,abs(q.y+.16*q.x));
float density=fold*innerFold*(.50+vaporBody*.30+rays.b*.20);
float perimeter=1.-smoothstep(.18,.72,fold);
density*=1.-perimeter*(1.-smoothstep(.10,.48,fire+vaporBody*.20))*.66;
float heat=saturate(broadNoise*.40+vaporBody*.35+rays.r*.25);
float3 rgb=lerp(shadegold,gold,.25+heat*.62)+ivory*pow(heat,4.)*.34;
return float4(rgb*form,saturate(density*.78)*Envelope*bounds);
'''

REVISION_CORE = r'''
float radius=length(p*float2(1.,1.15));
float pressure=exp(-pow(radius/.62,4.));
float density=pressure*(.46+vaporBody*.38+broadNoise*.16);
float hot=pow(saturate(vapor*2.1),2.)*(released>.5?exp(-shotTime*38.):saturate(Progress));
float3 rgb=lerp(shadegold,gold,.45+fire*.35)+ivory*hot*.42;
return float4(rgb*form,saturate(density*.62)*Envelope*bounds);
'''

REVISION_JET = r'''
float x=UV.x;
float taper=pow(saturate(sin(x*3.141593)),.60);
float width=(.10+.20*(1.-x))*taper;
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.y*.94+Index*.19),saturate(1.-x+Age*.18))).rgb;
float sheet=exp(-pow(abs(p.y/max(width,.025)),4.))*taper*(.38+.42*fire+.20*rays.b);
float flow=sheet*pow(saturate(rays.r*1.3),1.5);
float spines=0.;
for(int i=0;i<3;i++){
 float d=p.y-(float(i)-1.)*.24;
 spines+=exp(-pow(d/(.014+aa),2.))*exp(-pow((x-.70)/.17,2.));
}
float heat=saturate(fire*.40+rays.r*.60);
float3 rgb=lerp(shadegold,gold,.35+heat*.55)+ivory*saturate(spines)*.23;
return float4(rgb*form,saturate(sheet*.66+flow*.18+spines*.24)*Envelope*bounds);
'''

REVISION_SPLINTER = r'''
float emberBody=pow(saturate(vapor*2.4),.62)*smoothstep(.12,.45,fire+vapor*.25);
float hot=pow(saturate(vapor*3.0),3.)*(.35+.65*grain);
float3 rgb=lerp(shadegold,gold,.40+fire*.45)+ivory*hot*.32;
return float4(rgb*form,saturate(emberBody*.68)*Envelope*bounds);
'''

REVISION_SURGE = r'''
float t=max(0.,PulseAge);
float2 q=p+float2((broadNoise-.5)*.10,(broadNoise-.5)*.08);
float radius=length(q),angle=atan2(q.y,q.x);
float turn=angle+t*9.0+Index*.85;
float frontRadius=.46+.13*sin(turn*1.7);
float lateral=abs(radius-frontRadius)/.30;
float pressure=exp(-pow(lateral,4.));
float openArc=pow(saturate(.5+.5*cos(turn-.70)),.36);
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(angle*.15915-t*1.75+Index*.22),saturate(radius*.95))).rgb;
float density=pressure*openArc*(.54+vaporBody*.27+rays.b*.19);
float rootErosion=smoothstep(t*3.0-.10,t*3.0+.16,radius+fire*.22);
density*=rootErosion*(1.-smoothstep(.48,1.0,lateral)*(1.-smoothstep(.10,.48,fire))*.65);
float heat=saturate(broadNoise*.38+rays.r*.40+vaporBody*.22);
float3 rgb=lerp(shadegold,gold,.34+heat*.56)+ivory*pow(heat,3.)*.37;
return float4(rgb*form,saturate(density*.86)*Envelope*bounds);
'''

REVISION_BURST = r'''
float t=max(0.,PulseAge);
float2 q=p+float2((broadNoise-.5)*.08,0.);
float folds=exp(-pow(abs(q.x/.79),4.)-pow(abs((q.y-.10*sin(q.x*4.0))/.64),4.));
float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.x*.90-t*1.25+Index*.21),saturate(UV.y*.94))).rgb;
float tear=smoothstep(.035,.16,abs(q.y+.16*sin(q.x*3.5+Index)));
float tissue=.52+vaporBody*.30+rays.b*.18;
float perimeter=1.-smoothstep(.18,.72,folds);
float density=folds*tear*tissue*(1.-perimeter*(1.-smoothstep(.10,.48,fire+vaporBody*.20))*.70);
float rootErosion=smoothstep(t*3.1-.16,t*3.1+.13,abs(q.y)+vaporBody*.18);
density*=rootErosion;
float heat=saturate(broadNoise*.38+vaporBody*.37+rays.r*.25);
float hot=pow(heat,3.4)*(1.-smoothstep(.035,.105,t));
float3 rgb=lerp(shadegold,gold,.30+heat*.62)+ivory*hot*.45;
return float4(rgb*form,saturate(density*.90)*Envelope*bounds);
'''

REVISION_IMPACT9 = r'''
float t=max(0.,Age);
float open=saturate(t/.075);
float fade=1.-smoothstep(.075,.25,t);
float pressure=0.,veins=0.;
for(int i=0;i<3;i++){
 float side=float(i)-1.;
 float2 q=p-float2(.08+open*.14,side*(.15+open*.15));
 float bend=q.y-side*.20*sin((q.x+.8)*2.4);
 float width=.19+open*.095;
 float shape=exp(-pow(abs(bend/width),4.))*exp(-pow(abs((q.x-.08)/(.48+open*.14)),4.));
 float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.y*.8+i*.21-t*1.4),UV.x)).rgb;
 pressure+=shape*(.38+.38*fire+.24*rays.b)*(i==1?.62:.85);
 veins+=shape*rays.r*(.35+.65*grain);
}
float puncture=exp(-pow(p.x/.16,2.)-pow(p.y/.10,2.))*exp(-t*50.);
float glints=0.;
for(int j=0;j<7;j++){
 float ang=float(j)*2.399963;
 float2 axis=float2(cos(ang),sin(ang));
 float2 q=p-axis*(.15+t*(1.8+frac(float(j)*.37)));
 float along=dot(q,axis),across=q.x*axis.y-q.y*axis.x;
 glints+=exp(-pow(along/.105,2.)-pow(across/(.012+aa),2.));
}
float density=pressure*(.48+vaporBody*.24)+veins*.20+puncture*.30+glints*.26;
float heat=saturate(vaporBody*.46+fire*.35+veins*.25);
float3 rgb=lerp(shadegold,gold,.36+heat*.55)+ivory*(puncture*.24+saturate(glints)*.23);
return float4(rgb*form,saturate(density)*fade*bounds);
'''

REVISION_IMPACT10 = r'''
float t=max(0.,Age);
float body=0.,heat=0.;
for(int i=0;i<3;i++){
 float delay=float(i)*.023;
 float piece=max(0.,t-delay);
 float visible=step(delay,t)*(1.-smoothstep(.055,.17,piece));
 float side=i==0?0.:(i==1?-1.:1.);
 float2 q=p-float2(piece*1.0,side*(.10+piece*1.3));
 float bend=q.y-.16*sin(q.x*3.0+side*.8);
 float shape=exp(-pow(abs(q.x/(.45+piece*2.)),4.)-pow(abs(bend/.28),4.));
 float3 rays=Texture2DSample(Rays,RaysSampler,float2(frac(UV.x*.85-piece*1.4+i*.23),saturate(UV.y))).rgb;
 float tissue=.48+vaporBody*.32+rays.b*.20;
 body+=shape*tissue*visible*.65;
 heat+=shape*(rays.r*.56+vaporBody*.30)*visible*.48;
}
float puncture=exp(-pow(p.x/.13,2.)-pow(p.y/.08,2.))*exp(-t*55.);
float3 rgb=lerp(shadegold,gold,.34+saturate(heat)*.58)+ivory*(pow(saturate(heat),3.)*.26+puncture*.24);
return float4(rgb*form,saturate(body*.72+puncture*.28)*bounds);
'''


def main(output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    lib = unreal.MaterialEditingLibrary
    texture = unreal.load_asset(NOISE)
    assert texture, NOISE
    unreal.EditorAssetLibrary.make_directory(FOLDER)
    unreal.EditorAssetLibrary.make_directory(IMPACT_FOLDER)
    unreal.EditorAssetLibrary.make_directory(SERAPH_FOLDER)
    unreal.EditorAssetLibrary.make_directory(REVISION_FOLDER)
    impact_textures = {name: unreal.load_asset(path) for name, path in IMPACT_TEXTURES.items()}
    assert all(impact_textures.values()), IMPACT_TEXTURES
    plasma = unreal.load_asset(PLASMA_TEXTURE)
    assert plasma, PLASMA_TEXTURE
    rows = []
    entries = [(part, body, False) for part, body in [('Crescent', CRESCENT), ('Prism', PRISM), ('Filament', FILAMENT), ('Fracture', FRACTURE)]]
    entries += [(part, body, True) for part, body in [('Recoil', RECOIL), ('Pressure', PRESSURE), ('Eruption', ERUPTION), ('Streak', STREAK), ('Ember', EMBER)]]
    entries += [(part, body, 2) for part, body in [('Tempest', TEMPEST), ('Plasma', PLASMA), ('Shard', SHARD), ('Feather', SERAPH_FEATHER), ('Fan', FAN)]]
    entries += [(part, body, 3) for part, body in [('RevisionWind', REVISION_WIND), ('RevisionMantle', REVISION_MANTLE),
                ('RevisionCore', REVISION_CORE), ('RevisionJet', REVISION_JET), ('RevisionSplinter', REVISION_SPLINTER),
                ('RevisionSurge', REVISION_SURGE), ('RevisionBurst', REVISION_BURST),
                ('S9Impact', REVISION_IMPACT9), ('S10Impact', REVISION_IMPACT10)]]
    for part, body, recrafted in entries:
        code = (REVISION_COMMON if recrafted == 3 else IMPACT_COMMON if recrafted else COMMON) + body
        digest = hashlib.sha256((code + (json.dumps(IMPACT_TEXTURES, sort_keys=True) if recrafted else '') + (PLASMA_TEXTURE if recrafted >= 2 else '')).encode()).hexdigest()
        path = (REVISION_FOLDER if recrafted == 3 else SERAPH_FOLDER if recrafted == 2 else IMPACT_FOLDER if recrafted else FOLDER) + '/M_Study' + part
        material = unreal.load_asset(path)
        reused = bool(material and unreal.EditorAssetLibrary.get_metadata_tag(material, 'CelestialStudyHash') == digest)
        if not reused:
            if not material:
                folder, name = path.rsplit('/', 1)
                material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
            assert material, path
            lib.disconnect_material_property(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            lib.disconnect_material_property(material, unreal.MaterialProperty.MP_OPACITY)
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
            sources = {'UV': node('TextureCoordinate'), 'Flow': node('TextureObject', texture=texture)}
            if recrafted:
                sources.update({name: node('TextureObject', texture=value) for name, value in impact_textures.items()})
            if recrafted >= 2:
                sources['Plasma'] = node('TextureObject', texture=plasma)
            for parameter, default in [('Age', 0.), ('Progress', 0.), ('PulseAge', 100.), ('Index', 0.),
                                       ('Style', 1.), ('Ascended', 0.), ('Sharp', 0.), ('Envelope', 0.)]:
                sources[parameter] = node('ScalarParameter', parameter_name=parameter, default_value=default)
            pins = []
            for parameter in sources:
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', parameter)
                pins.append(pin)
            shader.set_editor_property('inputs', pins)
            for parameter, source in sources.items():
                assert lib.connect_material_expressions(source, '', shader, parameter)
            for output_property, channels in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                                               (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))]:
                mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
                assert lib.connect_material_expressions(shader, '', mask, '')
                assert lib.connect_material_property(mask, '', output_property)
        errors = [str(error) for error in (lib.recompile_material(material) or [])]
        rows.append({'path': path, 'reused': reused, 'compile_errors': errors})
        if errors:
            (out / 'arsenal-study-materials.json').write_text(json.dumps({'passed': False, 'materials': rows}, indent=2), encoding='utf-8')
            raise RuntimeError(path + ': ' + '\n'.join(errors))
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'CelestialStudyHash', digest)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    report = {'passed': True, 'materials': rows, 'texture': NOISE, 'recrafted_textures': IMPACT_TEXTURES,
              'installed_S': 10, 'installed_R': 0, 'S_preview_candidates': [9],
              'plasma_atlas': {'path': PLASMA_TEXTURE, 'layout': [8, 8], 'channel': 'alpha'},
              'S_revision': 'reart: independent preparation/release surfaces; density in opacity once',
              'archived_candidates_preserved': [1, 2, 3, 5, 6, 7, 8],
              'read_at': 'cast start; pulse only on actual release'}
    (out / 'arsenal-study-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
