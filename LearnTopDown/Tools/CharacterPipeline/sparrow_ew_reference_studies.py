"""Five reference-led E/W bow studies in isolated PIE; no runtime installation.

The reference's layered bow, bright inner veins and outward release are adapted
to Sparrow's gold/white palette. Native single projectiles and hits own timing.
"""
import os
from pathlib import Path
import runpy
import struct
import unreal

OLD = runpy.run_path(str(Path(__file__).with_name('sparrow_e_release_studies.py')))
BASE = OLD['BASE']
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/EWReference20261024'
OPTIONS = ('G1', 'G2', 'G3', 'G4', 'G5')
DESIGNS = {
    'G1': {'label': '성익 대궁', 'shape': '레퍼런스의 넓은 깃 몸체와 밝은 내부 결. 긴 깃이 뿌리부터 펼쳐지고 전방으로 광압이 터진다.', 'motion': '연속 깃 전개 → 시위 응축 → 짧은 전방 파열'},
    'G2': {'label': '삼중 광익궁', 'shape': '높이가 다른 세 활이 앞뒤로 엇갈려 펼쳐지고, 세 시위가 하나의 발사점으로 모인다.', 'motion': '세 층 개방 → 중앙 합류 → 교차 잔광'},
    'G3': {'label': '결정 파쇄궁', 'shape': '긴 결정 칼날과 어두운 금빛 면을 가진 각진 활. 발사 때 끝부분에서 작은 결정 조각이 튄다.', 'motion': '조각 결합 → 균열 점화 → 짧고 날카로운 파쇄'},
    'G4': {'label': '불사조 화염궁', 'shape': '활에 연결된 넓은 깃 자체가 황금 불꽃으로 일렁인다. 두 흐름이 발사점에 감겨 들어간다.', 'motion': '깃불 개방 → 화염 수렴 → 짧은 불꽃 후류'},
    'G5': {'label': '백금 뇌광궁', 'shape': '긴 백금 활과 뒤쪽의 짧은 이중 잔상. 몸체의 전류가 전방의 한 축으로 수렴한다.', 'motion': '긴 활 점화 → 전류 집결 → 강한 직선 섬광과 두 번의 짧은 접촉'},
}

FAMILY_ROOT = '/Game/TopDown/Characters/Sparrow/Previews/BowFamily20261024'
FAMILY_OPTIONS = ('R1', 'R2', 'R3', 'R4')
FAMILY_DESIGNS = {
    'R1': {'label': '세 활 순차 개방', 'shape': '분리된 작은 활 세 개가 서로 다른 위치에서 펼쳐지고 한 발의 발사점으로 시위가 모임.', 'motion': '위 → 중앙 → 아래 개방, 시위 합류, 동시에 짧게 반동'},
    'R2': {'label': '곡문 부채광궁', 'shape': '곡선 몸체가 먼저 열리고 뒤쪽 부채꼴 광선이 늦게 확장됨.', 'motion': '곡문 개방 → 뒤 광선 확장 → 한 점 응축'},
    'R3': {'label': '겹활 연쇄 개방', 'shape': '겹친 몸체의 안쪽·중간·바깥 층이 차례로 열리고 하나의 시위로 연결됨.', 'motion': '세 깊이의 몸체 전개 → 단발 반동'},
    'R4': {'label': '강화 대궁', 'shape': '굵고 큰 주몸체가 빠르게 펼쳐지고 긴 시위가 강하게 당겨짐.', 'motion': '큰 몸체 개방 → 강한 응축 → 짧은 반동과 소멸'},
}
FAMILY_ART = {
    'R1': ('sparrow-short-bow-family-20261024/art/R1.png',
           [(475, 18, 765, 453), (825, 220, 1190, 800), (470, 575, 752, 1008)]),
    'R2': ('sparrow-short-bow-family-20261024/art/R2.png', [(0, 0, 1448, 1086)]),
    'R3': ('sparrow-short-bow-study-20261024/art/C1.png', [(0, 0, 1448, 1086)]),
    'R4': ('sparrow-short-bow-family-20261024/art/R4-v2.png', [(0, 0, 1448, 1086)]),
}

# Opaque source paintings stay untouched. Pixel-space keying, separation and
# opening are evaluated at runtime in this preview-only material namespace.
FAMILY_SHADER = r'''
struct FFamily {
 float Seg(float2 p,float2 a,float2 b){float2 d=b-a;return length(p-a-d*saturate(dot(p-a,d)/max(dot(d,d),.001)));}
 float Hash(float x){return frac(sin(x*17.17+6.31)*9281.73);}
 float Star(float2 p){return exp(-abs(p.x)*.08-abs(p.y)*.9)+exp(-abs(p.x)*1.2-abs(p.y)*.12);}
 float Key(float3 c){
  float lum=dot(c,float3(.2126,.7152,.0722));
  float warm=smoothstep(-.004,.045,c.r-c.b);
  float neutral=smoothstep(.22,.60,min(c.r,min(c.g,c.b)));
  return smoothstep(.028,.115,lum)*max(warm,neutral);
 }
};
FFamily F;
const int V=DESIGN_NUMBER;
const float PI=3.14159265;
float2 p=(UV-.5)*float2(1100.,760.)+float2(110.,0.);
if(Mode>.5){
 // Preserve the reference study's two compact native-hit pulses. Only its
 // optional G3/G5 lightning is excluded from these four bow-family choices.
 float2 hp=(UV-.5)*400.;
 float3 impactColor=0.;float impactAlpha=0.;
 for(int b=0;b<2;b++){
  float t=Age-b*.055;if(t<0.||t>.24)continue;
  float fade=exp(-t*19.),shock=exp(-t*47.);
  float2 q=hp-float2(b*8.,0.);
  float core=F.Star(q)*shock+exp(-abs(q.y)*.64-abs(q.x)*.022)*shock*.65;
  impactColor+=float3(3.2,2.9,2.05)*core;impactAlpha=max(impactAlpha,saturate(core));
  for(int i=0;i<42;i++){
   float h=frac(sin((i+b*52.)*127.1+71.7)*43758.5453),a=i*2.39996;
   float2 dir=float2(cos(a),sin(a));
   float r=7.+t*(180.+h*220.);
   float d=F.Seg(q,dir*r,dir*(r+9.+h*25.));
   float spark=exp(-d*1.5)*fade;
   impactColor+=lerp(float3(2.15,.88,.13),float3(3.2,2.9,2.05),h)*spark;
   impactAlpha=max(impactAlpha,spark);
  }
 }
 return float4(impactColor,impactAlpha);
}
float shot=ShotAge<0.?-1.:max(Age-ShotAge,0.);
float charge=max(Charge,.15);
float releaseFade=shot<0.?1.:1.-smoothstep(.035,.195,shot);
float recoil=shot<0.?0.:sin(saturate(shot/.12)*PI)*(V==4?18.:10.);
float envelope=smoothstep(.006,.035,Age)*releaseFade;
float3 premult=0.;float coverage=0.,stringLight=0.;
int parts=V==1||V==3?3:V==2?2:1;
for(int layer=0;layer<3;layer++){
 if(layer>=parts)break;
 float delay=V==1?layer*.038:V==2?layer*.085:V==3?layer*.040:0.;
 float opened=smoothstep(.012+delay,charge*.73+delay*.4,Age);
 float draw=smoothstep(charge*.42,charge,Age)*(shot<0.?1.:exp(-shot*55.));
 float2 pivot=float2(710.,522.),place=float2(86.,0.);
 float2 artScale=float2(.56,.57);
 float4 crop=float4(0.,0.,1448.,1086.);
 float2 topTip=float2(810.,178.),bottomTip=float2(810.,866.);
 float2 oldNock=float2(1053.,522.);
 if(V==1){
  if(layer==0){pivot=float2(510.,260.);place=float2(-20.,137.);artScale=.50;crop=float4(475.,18.,765.,453.);topTip=float2(617.,105.);bottomTip=float2(684.,354.);oldNock=float2(713.,225.);}
  if(layer==1){pivot=float2(897.,520.);place=float2(104.,0.);artScale=.48;crop=float4(825.,220.,1190.,800.);topTip=float2(1028.,327.);bottomTip=float2(1036.,680.);oldNock=float2(1143.,515.);}
  if(layer==2){pivot=float2(520.,765.);place=float2(-30.,-133.);artScale=.48;crop=float4(470.,575.,752.,1008.);topTip=float2(654.,649.);bottomTip=float2(613.,910.);oldNock=float2(717.,792.);}
 }else if(V==3){pivot=float2(540.,525.);artScale=float2(.50,.54);topTip=float2(965.,320.);bottomTip=float2(973.,721.);oldNock=float2(1203.,525.);}
 else if(V==4){pivot=float2(607.,533.);place=float2(107.,0.);artScale=float2(.49,.60);topTip=float2(938.,338.);bottomTip=float2(938.,721.);oldNock=float2(1181.,534.);}
 float2 q=p-place+float2(recoil,0.);
 if(V==3)q.x+=(1.-opened)*(layer-1)*26.;
 // Negative X maps all LEFT-firing source art into local +X firing.
 float2 src=pivot-float2(q.x/artScale.x,q.y/(artScale.y*max(.13,opened)));
 if(V==2&&layer==1){
  float fanScale=.48+.52*opened;
  src.x=870.+(src.x-870.)/fanScale;
 }
 float bounds=step(crop.x,src.x)*step(src.x,crop.z)*step(crop.y,src.y)*step(src.y,crop.w);
 float4 tex=Texture2DSample(BowArt,BowArtSampler,saturate(src/float2(1448.,1086.)));
 float mask=F.Key(tex.rgb)*bounds;
 // Every source arrow is removed from its painting. Native E owns the only
 // released arrow; the painted strings are replaced by animated strings.
 float arrowGap=0.,oldString=0.;
 if(V==1){
  float2 arrowStart=layer==0?float2(315.,289.):layer==1?float2(658.,520.):float2(317.,739.);
  float axis=F.Seg(src,arrowStart,oldNock+float2(25.,0.));
  arrowGap=1.-smoothstep(17.,24.,axis);
  oldString=1.-smoothstep(5.,11.,min(F.Seg(src,topTip,oldNock),F.Seg(src,bottomTip,oldNock)));
 }else{
  float cy=V==4?533.:V==3?525.:522.;
  float axis=abs(src.y-cy);
  float arrowWidth=V==4?22.:V==3?10.:15.;
  arrowGap=(1.-smoothstep(arrowWidth,arrowWidth+7.,axis))*step(120.,src.x);
  float tipWidth=V==4?72.:V==3?50.:68.;
  arrowGap=max(arrowGap,(1.-smoothstep(tipWidth,tipWidth+9.,axis))*(1.-smoothstep(V==4?440.:V==3?390.:480.,V==4?505.:V==3?455.:565.,src.x)));
  oldString=1.-smoothstep(5.,11.,min(F.Seg(src,topTip,oldNock),F.Seg(src,bottomTip,oldNock)));
  if(V==3){
   float aux=min(F.Seg(src,float2(490.,267.),float2(905.,245.)),F.Seg(src,float2(485.,781.),float2(907.,795.)));
   arrowGap=max(arrowGap,1.-smoothstep(5.,10.,aux));
   // Two additional painted strings cross open space, not the bow's carved
   // surface. Protect intersections whose off-string pixels contain body art.
   for(int extra=0;extra<2;extra++){
    float2 a=extra==0?float2(700.,366.):float2(730.,687.);
    float2 b=float2(1203.,525.),dir=normalize(b-a),normal=float2(-dir.y,dir.x);
    float3 sideA=Texture2DSample(BowArt,BowArtSampler,saturate((src+normal*15.)/float2(1448.,1086.))).rgb;
    float3 sideB=Texture2DSample(BowArt,BowArtSampler,saturate((src-normal*15.)/float2(1448.,1086.))).rgb;
    float isolated=1.-smoothstep(.12,.65,max(F.Key(sideA),F.Key(sideB)));
    oldString=max(oldString,(1.-smoothstep(6.,12.,F.Seg(src,a,b)))*isolated);
   }
  }
  if(V==4)oldString*=smoothstep(943.,967.,src.x);
 }
 float oldNockMask=1.-smoothstep(V==1?15.:25.,V==1?25.:38.,length(src-oldNock));
 // Preserve the small carved grip where the painted shaft crosses the bow.
 float gripKeep=(1.-smoothstep(11.,24.,abs(src.x-pivot.x)))*(1.-smoothstep(15.,35.,abs(src.y-pivot.y)));
 mask*=1.-max(arrowGap*(1.-gripKeep),max(oldString*(1.-gripKeep),oldNockMask));
 if(V>=1&&V<=4){
  // Reconstruct only the carved bow crossing from its two off-axis sides.
  // Sampling outside the removed shaft band restores body continuity without
  // restoring any painted arrow, arrowhead, or straight central shaft.
  float axisY=pivot.y;
  if(V==1){
   float2 arrowStart=layer==0?float2(315.,289.):layer==1?float2(658.,520.):float2(317.,739.);
   axisY=lerp(arrowStart.y,oldNock.y,(src.x-arrowStart.x)/(oldNock.x-arrowStart.x));
  }
  float halfBand=V==1?29.:V==2?27.:V==3?23.:36.;
  float2 upperUV=float2(src.x,axisY-halfBand)/float2(1448.,1086.);
  float2 lowerUV=float2(src.x,axisY+halfBand)/float2(1448.,1086.);
  float3 upper=Texture2DSample(BowArt,BowArtSampler,saturate(upperUV)).rgb;
  float3 lower=Texture2DSample(BowArt,BowArtSampler,saturate(lowerUV)).rgb;
  float bodyAcross=min(F.Key(upper),F.Key(lower));
  float bodyWidth=V==1?1.-smoothstep(22.,39.,abs(src.x-pivot.x)):
                  V==2?smoothstep(575.,615.,src.x)*(1.-smoothstep(810.,848.,src.x)):
                  V==3?smoothstep(420.,456.,src.x)*(1.-smoothstep(650.,686.,src.x)):
                  smoothstep(520.,552.,src.x)*(1.-smoothstep(685.,725.,src.x));
  float bridge=(1.-smoothstep(halfBand-7.,halfBand,abs(src.y-axisY)))*bodyWidth*bodyAcross*bounds;
  float3 bridgeColor=lerp(upper,lower,saturate((src.y-axisY+halfBand)/(halfBand*2.)));
  tex.rgb=lerp(tex.rgb,bridgeColor,bridge);
  mask=max(mask,bridge);
 }
 if(V==2){
  float yy=abs(src.y-522.);
  float fan=smoothstep(-8.,13.,src.x-(970.-yy*.66))*smoothstep(130.,180.,yy);
  mask*=layer==0?1.-fan:fan;
 }else if(V==3){
  float yy=abs(src.y-525.);
  float inner=1.-smoothstep(176.,190.,yy),outer=smoothstep(340.,354.,yy);
  mask*=layer==0?inner:layer==1?(1.-inner)*(1.-outer):outer;
 }
 float centerReveal=1.-smoothstep(opened*.58-.035,opened*.58+.025,abs((src.y-pivot.y)/(crop.w-crop.y)));
 mask*=centerReveal*envelope*.92;
 float grain=Texture2DSample(Detail,DetailSampler,src/float2(330.,260.)+float2(Age*.23,-Age*.35)).r;
 float3 paint=tex.rgb*(1.08+draw*(V==4?.57:.26))*(.87+.20*grain);
 // Each disjoint painted component is composited once, with unpremultiplied
 // output color, avoiding both opaque navy cards and doubled alpha loss.
 premult+=paint*mask*(1.-coverage);
 coverage+=mask*(1.-coverage);
 if(V==3&&layer!=0)continue;
 if(V==2&&layer!=0)continue;
 float2 endpointA=place+(pivot-topTip)*artScale*float2(1.,opened)-float2(recoil,0.);
 float2 endpointB=place+(pivot-bottomTip)*artScale*float2(1.,opened)-float2(recoil,0.);
 float2 nock=place+float2(-38.-draw*(V==4?112.:75.),0.);
 if(V==1)nock=lerp(nock,float2(-24.,0.),smoothstep(.50,.96,draw));
 float sd=min(F.Seg(p,endpointA,nock),F.Seg(p,endpointB,nock));
 stringLight+=exp(-sd*1.8)*draw*opened*.43;
}
float focus=0.;
if(shot<0.){
 float tighten=smoothstep(charge*.63,charge,Age);
 focus=exp(-abs(p.x+24.)*.24-abs(p.y)*.52)*tighten*.44;
}
float snap=shot<0.?0.:exp(-shot*65.)*exp(-abs(p.x-20.)*.11-abs(p.y)*.70)*.65;
float light=(stringLight+focus)*envelope+snap;
float3 color=premult/max(coverage,.002)+float3(2.1,1.82,1.15)*light;
return float4(color,saturate(coverage+light));
'''

SHADER = r'''
struct FShape {
 float Seg(float2 p,float2 a,float2 b){float2 v=b-a;return length(p-a-v*saturate(dot(p-a,v)/max(dot(v,v),.001)));}
 float2 Bez(float2 a,float2 b,float2 c,float2 d,float t){float u=1.-t;return a*u*u*u+3.*b*u*u*t+3.*c*u*t*t+d*t*t*t;}
 float4 Rib(float2 p,float2 a,float2 b,float2 c,float2 d,float w,float reveal){
  float edge=1000.,spine=1000.,localWidth=1.;
  for(int i=0;i<14;i++){float t=i/14.,n=min((i+1)/14.,reveal);if(t>=reveal)break;
   float dist=Seg(p,Bez(a,b,c,d,t),Bez(a,b,c,d,n));
   float width=w*pow(max(sin((t+n)*1.5707963),.001),.7);
   if(dist-width<edge){edge=dist-width;localWidth=max(width,1.);spine=dist;}}
  return float4(1.-smoothstep(-1.,1.3,edge),exp(-abs(edge)*1.1),exp(-max(edge,0.)*.16)*.18,exp(-spine/localWidth*4.2));
 }
 float Hash(float x){return frac(sin(x*127.1+71.7)*43758.5453);}
 float Star(float2 p){return exp(-abs(p.x)*.08-abs(p.y)*.9)+exp(-abs(p.x)*1.2-abs(p.y)*.12);}
};
FShape F;
const int V=DESIGN_NUMBER;
const float PI=3.14159265;
float3 gold=float3(2.15,.88,.13),amber=float3(.45,.12,.012),white=float3(3.2,2.9,2.05);
float3 col=0.;float alpha=0.;
if(Mode>.5){
 float2 p=(UV-.5)*400.;
 for(int b=0;b<2;b++){
  float t=Age-b*.055;if(t<0.||t>.24)continue;
  float fade=exp(-t*19.),shock=exp(-t*47.);
  float2 q=p-float2(b*8.,0.);
  float core=F.Star(q)*shock+exp(-abs(q.y)*.64-abs(q.x)*.022)*shock*.65;
  col+=white*core;alpha=max(alpha,saturate(core));
  for(int i=0;i<42;i++){
   float h=F.Hash(i+b*52.),a=i*2.39996;
   float2 dir=float2(cos(a),sin(a));
   float r=7.+t*(180.+h*220.);
   float d=F.Seg(q,dir*r,dir*(r+9.+h*25.));
   float spark=exp(-d*1.5)*fade;
   col+=lerp(gold,white,h)*spark;alpha=max(alpha,spark);
  }
  if(V==3||V==5){
   for(int j=0;j<6;j++){
    float a=j*PI/3.+.2;float2 dir=float2(cos(a),sin(a)),n=float2(-dir.y,dir.x);
    float dist=1000.;float2 prev=0.;
    for(int k=1;k<5;k++){float2 next=dir*k*17.+n*(F.Hash(j*10.+k)*2.-1.)*11.;dist=min(dist,F.Seg(q,prev,next));prev=next;}
    float spark=exp(-dist*1.7)*fade;col+=white*spark*.6;alpha=max(alpha,spark);
   }
  }
 }
 return float4(col,alpha);
}
float shot=ShotAge<0.?-1.:Age-ShotAge;
float charge=max(Charge,.15);
float opened=smoothstep(.015,charge*.72,Age);
float fade=smoothstep(.005,.035,Age)*(shot<0.?1.:1.-smoothstep(.055,.24,shot));
float recoil=shot<0.?0.:sin(saturate(shot/.15)*PI)*15.;
float2 p=(UV-.5)*float2(1300.,760.)+float2(390.,0.);
float2 q=float2(p.x+recoil,abs(p.y)/max(.14,opened));
float grain=Texture2DSample(Detail,DetailSampler,UV*float2(3.9,4.6)+float2(-Age*.5,Age*.27)).r;
float fine=Texture2DSample(Detail,DetailSampler,UV*float2(9.,7.)+float2(Age*.31,-Age*.5)).g;
float fire=Texture2DSample(Fire,FireSampler,float2(q.x*.012+Age*.5,q.y*.009-Age*1.25)).r;
float4 body=0.,feathers=0.;float veins=0.,halo=0.,sparks=0.;
float2 a=float2(0.,0.),b=float2(82.,72.),c=float2(112.,200.),d=float2(-30.,274.);
if(V==1){
 body=F.Rib(q,a,b,c,d,13.,opened);
 for(int j=0;j<10;j++){
  float u=.16+j*.077;float2 root=F.Bez(a,b,c,d,u);
  float unfold=smoothstep(.02+j*.008,charge*.72+j*.007,Age);
  float2 tip=root+float2(-102.-j*3.,60.+j*5.);
  float4 f=F.Rib(q,root,root+float2(-55.,-16.),tip+float2(30.,-36.),tip,13.-j*.52,unfold);
  feathers=max(feathers,f);veins+=f.w*(.2+.6*fine)*.45;
 }
}else if(V==2){
 for(int j=0;j<3;j++){
  float h=1.-j*.18,x=j*49.;float reveal=smoothstep(.02+j*.04,charge*.8,Age);
  float2 qa=float2(q.x-x,q.y/max(h,.1));
  float4 r=F.Rib(qa,a,b,c,d,10.-j*1.2,reveal);body=max(body,r);
  for(int k=0;k<5;k++){
   float2 root=F.Bez(a,b,c,d,.24+k*.14),tip=root+float2(-58.,68.);
   feathers=max(feathers,F.Rib(qa,root,root+float2(-30.,-8.),tip+float2(26.,-32.),tip,9.,reveal));
  }
  float draw=smoothstep(charge*.35,charge,Age);
  float sd=F.Seg(qa,d,float2(-90.*draw,0.));veins+=exp(-sd*1.4)*.43;
 }
}else if(V==3){
 body=F.Rib(q,a,float2(22,100),float2(100,170),float2(10,300),16.,opened);
 for(int j=0;j<7;j++){
  float u=.12+j*.13;float2 root=F.Bez(a,float2(22,100),float2(100,170),float2(10,300),u);
  float2 tip=root+float2(-116.+j*6.,55.+j*5.);
  float4 f=F.Rib(q,root,root+float2(-16.,30.),tip+float2(12.,-6.),tip,23.-j*1.0,smoothstep(.01+j*.022,charge*.8,Age));
  feathers=max(feathers,f);
  float seam=exp(-F.Seg(q,root+float2(-8,12),tip)*1.3);veins+=seam*.7;
 }
}else if(V==4){
 q.x+=(fire-.45)*10.;
 body=F.Rib(q,a,b,c,d,18.,opened);
 for(int j=0;j<8;j++){
  float2 root=F.Bez(a,b,c,d,.12+j*.11),tip=root+float2(-120.-j*4.,80.+j*5.);
  feathers=max(feathers,F.Rib(q,root,root+float2(-70.,-42.),tip+float2(58.,-54.),tip,21.-j*.9,smoothstep(j*.012,charge*.77,Age)));
 }
 float4 stream=F.Rib(q,float2(-52,162),float2(70,150),float2(122,70),float2(76,0),8.,opened);
 veins=stream.x*fire*.7;halo=stream.z*fire;
}else{
 d=float2(-16.,315.);
 body=F.Rib(q,a,float2(68,90),float2(72,235),d,15.,opened);
 for(int j=0;j<6;j++){
  float2 root=F.Bez(a,float2(68,90),float2(72,235),d,.17+j*.14),tip=root+float2(-92.,85.);
  feathers=max(feathers,F.Rib(q,root,root+float2(-38,12),tip+float2(35,-40),tip,15.,opened));
 }
 for(int j=0;j<2;j++){
  float4 ghost=F.Rib(q+float2(38.+j*34.,0.),a,float2(68,90),float2(72,235),d,5.,opened);
  halo+=ghost.x*.13+ghost.z*.25;
 }
 for(int j=0;j<3;j++){
  float dist=1000.;float2 prev=float2(-8.,0.);
  for(int k=1;k<13;k++){float t=k/12.;float2 next=F.Bez(a,float2(68,90),float2(72,235),d,t)+float2(sin(k*2.6+j*3.+Age*24.)*12.,0.);dist=min(dist,F.Seg(q,prev,next));prev=next;}
  veins+=exp(-dist*1.7)*(.3+.22*sin(Age*49.+j));
 }
}
float fill=max(body.x,feathers.x),rim=max(body.y,feathers.y),core=max(body.w,feathers.w);
// The generated RGBA sprite supplies sculpted surfaces; UV animation owns unfolding.
float3 artColor=0.;float artAlpha=0.;
for(int layer=0;layer<3;layer++){
 if(V!=2&&layer>0)break;
 float layerScale=V==2?1.-layer*.19:V==5?1.08:1.;
 float layerX=V==2?layer*82.:0.;
 float layerOpen=smoothstep(.012+layer*.045,charge*.78,Age);
 float2 ap=float2(p.x+recoil-layerX,p.y/max(.12,layerOpen))/layerScale;
 if(V==3){ap.x+=sin(floor(abs(ap.y)/48.)*2.4+Age*15.)*(1.-layerOpen)*20.;}
 if(V==4){ap.x+=(fire-.5)*9.;ap.y+=sin(ap.x*.025+Age*16.)*3.;}
 if(V==5){ap.x*=1.28;}
 float2 auv=float2(ap.x/420.+(V==3?.63:.665),(V==3?.49:.505)-ap.y/630.);
 float inBounds=step(0.,auv.x)*step(auv.x,1.)*step(0.,auv.y)*step(auv.y,1.);
 float4 art=Texture2DSample(BowArt,BowArtSampler,saturate(auv));
 float aa=pow(art.a,1.35)*inBounds;
 float reveal=1.-smoothstep(layerOpen*.57-.045,layerOpen*.57+.025,abs(auv.y-.505));
 aa*=reveal;
 if(V==4){aa*=saturate(.72+fire*.75);}
 float3 ac=art.rgb*(.88+.22*grain);
 if(V==3)ac*=float3(.85,.92,1.2);
 if(V==4)ac*=float3(1.5,.78,.36);
 if(V==5){float bright=dot(ac,float3(.25,.6,.15));ac=lerp(ac,bright*float3(1.05,1.03,.87),.78);}
 float movingVein=pow(saturate(fine),4.)*aa*.45;
 ac+=float3(1.4,.85,.3)*movingVein;
 artColor=lerp(artColor,ac,aa);
 artAlpha=max(artAlpha,aa);
}
float textureShade=saturate(.14+grain*.45+fine*.28);
float erosion=1.;
if(V==4){erosion=saturate(fire*2.0+core*.38-.12);textureShade=.15+fire*.9;rim*=erosion*.32;}
float facet=V==3 ? .52+.48*step(.5,frac(q.x*.024+q.y*.018)) : 1.;
float draw=smoothstep(charge*.3,charge,Age)*(shot<0.?1.:exp(-shot*40.));
float sd=F.Seg(q,float2(-100.,292.),float2(-150.*draw,0.));float stringLight=exp(-sd*1.5)*opened*(V==3?0.:1.);
float ready=smoothstep(charge*.42,charge,Age)*(shot<0.?1.:exp(-shot*40.));
float focal=F.Star(p-float2(50.,0.))*ready;
for(int j=0;j<60;j++){
 float h=F.Hash(j),birth=.018+h*charge*.6,t=Age-birth;
 float life=saturate(t/.22);float2 root=F.Bez(a,b,c,d,.1+F.Hash(j+61)*.9);
 float2 vel=float2(-70.-h*180.,30.+h*90.);float2 loc=root+vel*t;
 sparks+=exp(-F.Seg(q,loc,loc-vel*.025)*1.8)*sin(life*PI)*step(0.,t)*.55;
}
float flare=0.,rays=0.,wake=0.;
if(shot>=0.&&shot<.18){
 float energy=exp(-shot*23.);
 float2 center=float2(54.,0.);
 flare=F.Star(p-center)*energy*1.8;
 float spread=V==2?1.5:V==5?.45:1.;
 for(int j=0;j<9;j++){
  float angle=(j-4)*.058*spread;float2 dir=float2(cos(angle),sin(angle));
  float from=36.+shot*2100.,to=from+110.+F.Hash(j)*140.;
  float dist=F.Seg(p,center+dir*from,center+dir*to);
  rays+=exp(-dist*(j==4?.85:1.8))*energy*(j==4?1.2:.43);
 }
 if(V==4)wake=exp(-abs(p.y)*.045)*smoothstep(24.,80.,p.x)*(1.-smoothstep(260.,450.,p.x))*fire*energy*.4;
}
float geometry=V==3?0.:V==4?.08:.025;
col=artColor+gold*(fill*textureShade*geometry*facet+halo*.3+wake)
 +white*(rim*geometry*.09+veins*(V==5?.55:.10)+stringLight*.28+focal*.45+sparks*.5+flare+rays);
alpha=saturate(artAlpha+fill*erosion*geometry+halo*.3+veins*(V==5?.4:.1)+stringLight+focal+sparks+flare+rays+wake);
return float4(col,alpha*fade);
'''


def _family_info(option):
    relative, crops = FAMILY_ART[option]
    source = Path(__file__).parents[2]/'Saved/QA/CharacterPipeline'/relative
    with source.open('rb') as stream:
        header = stream.read(24)
    assert header[:8] == b'\x89PNG\r\n\x1a\n', str(source)
    width, height = struct.unpack('>II', header[16:24])
    assert (width, height) == (1448, 1086), (source, width, height)
    return {'family_branch': True, 'source_image': str(source), 'source_size_px': [width, height],
            'texture': FAMILY_ROOT+'/T_'+option,
            'crop_px': crops, 'crop_uv': [[x0/width, y0/height, x1/width, y1/height] for x0, y0, x1, y1 in crops],
            'flip_source_x': True, 'plane_cm': [1100., 760.], 'plane_forward_shift_cm': 110.,
            'background_key': 'linear luminance plus warm or bright neutral; navy rejected in shader',
            'static_arrow': 'removed except small carved grip; one native E projectile',
            'static_string': 'removed and redrawn with procedural draw and release'}


def _author_family(out):
    before = OLD['OLD']['production_hashes']()
    selected = [s.strip() for s in os.environ.get('SPARROW_EW_AUTHOR', ','.join(FAMILY_OPTIONS)).split(',') if s.strip()]
    assert selected and all(s in FAMILY_OPTIONS for s in selected), selected
    lib = unreal.MaterialEditingLibrary
    infos = {}
    for option in selected:
        info = _family_info(option)
        infos[option] = info
        texture = unreal.load_asset(info['texture'])
        if not texture:
            task = unreal.AssetImportTask()
            for key, value in dict(filename=info['source_image'], destination_path=FAMILY_ROOT,
                                   destination_name='T_'+option, automated=True, replace_existing=False, save=True).items():
                task.set_editor_property(key, value)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            texture = unreal.load_asset(info['texture'])
        assert texture
        # Key thresholds are linear values; imported source RGB is sRGB.
        texture.set_editor_property('srgb', True)
        assert unreal.EditorAssetLibrary.save_loaded_asset(texture, False)
        path = FAMILY_ROOT+'/M_'+option
        material = unreal.load_asset(path)
        if not material:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_'+option, FAMILY_ROOT, unreal.Material, unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        def node(kind, **props):
            expression = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in props.items():expression.set_editor_property(key, value)
            return expression
        custom = node('Custom', code=FAMILY_SHADER.replace('DESIGN_NUMBER', option[1:]), output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        detail = unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless')
        assert detail
        sources = {'UV': node('TextureCoordinate'), 'BowArt': node('TextureObject', texture=texture),
                   'Detail': node('TextureObject', texture=detail)}
        for name, value in [('Age', .25), ('ShotAge', -1.), ('Mode', 0.), ('Charge', .32)]:
            sources[name] = node('ScalarParameter', parameter_name=name, default_value=value)
        args = []
        for name in sources:
            arg = unreal.CustomInput();arg.set_editor_property('input_name', name);args.append(arg)
        custom.set_editor_property('inputs', args)
        for name, expression in sources.items():assert lib.connect_material_expressions(expression, '', custom, name)
        for prop, rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR, (1,1,1,0)), (unreal.MaterialProperty.MP_OPACITY, (0,0,0,1))]:
            mask = node('ComponentMask', r=bool(rgba[0]), g=bool(rgba[1]), b=bool(rgba[2]), a=bool(rgba[3]))
            assert lib.connect_material_expressions(custom, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    assert before == OLD['OLD']['production_hashes']()
    result = {'passed': True, 'family_branch': True, 'assets': [FAMILY_ROOT+'/M_'+o for o in selected],
              'production_changed': False, 'designs': {o: {**FAMILY_DESIGNS[o], **infos[o]} for o in selected}}
    BASE['_write'](out, 'bow-family-materials.json', result)
    return result


def author(out):
    if os.environ.get('SPARROW_EW_FAMILY') == '1':
        return _author_family(out)
    before = OLD['OLD']['production_hashes']()
    lib = unreal.MaterialEditingLibrary
    art_path = ROOT+'/T_GoldBow'
    for texture_name,file in [('T_GoldBow','gold-bow.png'),('T_CrystalBow','crystal-bow.png')]:
        if unreal.load_asset(ROOT+'/'+texture_name):continue
        source = Path(__file__).parents[2]/'Saved/QA/CharacterPipeline/sparrow-ew-reference-20261024/art'/file
        assert source.exists()
        task = unreal.AssetImportTask()
        for key,value in dict(filename=str(source),destination_path=ROOT,destination_name=texture_name,automated=True,replace_existing=False,save=True).items():
            task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    textures = {'Detail': unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'),
                'Fire': unreal.load_asset('/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D'),
                'BowArt': unreal.load_asset(art_path)}
    selected = os.environ.get('SPARROW_EW_AUTHOR', ','.join(OPTIONS)).split(',')
    for option in selected:
        assert option in OPTIONS
        path = ROOT+'/M_'+option
        material = unreal.load_asset(path)
        if not material:
            folder, name = path.rsplit('/',1)
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided',True)
        def node(kind,**props):
            n=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
            for k,v in props.items():n.set_editor_property(k,v)
            return n
        custom=node('Custom',code=SHADER.replace('DESIGN_NUMBER',option[1:]),output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        inputs={'UV':node('TextureCoordinate')}
        for name,value in [('Age',.25),('ShotAge',-1.),('Mode',0.),('Charge',.32)]:
            inputs[name]=node('ScalarParameter',parameter_name=name,default_value=value)
        for name,texture in textures.items():
            if name=='BowArt' and option=='G3':texture=unreal.load_asset(ROOT+'/T_CrystalBow')
            assert texture
            inputs[name]=node('TextureObject',texture=texture)
        args=[]
        for name in inputs:
            arg=unreal.CustomInput();arg.set_editor_property('input_name',name);args.append(arg)
        custom.set_editor_property('inputs',args)
        for name,n in inputs.items():assert lib.connect_material_expressions(n,'',custom,name)
        for prop,rgba in [(unreal.MaterialProperty.MP_EMISSIVE_COLOR,(1,1,1,0)),(unreal.MaterialProperty.MP_OPACITY,(0,0,0,1))]:
            mask=node('ComponentMask',r=bool(rgba[0]),g=bool(rgba[1]),b=bool(rgba[2]),a=bool(rgba[3]))
            assert lib.connect_material_expressions(custom,'',mask,'')
            assert lib.connect_material_property(mask,'',prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    assert before==OLD['OLD']['production_hashes']()
    result={'passed':True,'assets':[ROOT+'/M_'+o for o in selected],'production_changed':False,'reference':'https://www.youtube.com/shorts/zAkT93h6o8k'}
    BASE['_write'](out,'ew-reference-materials.json',result)
    return result


class Study(BASE['Study']):
    def __init__(self,rig,option,skill):
        super().__init__(rig,skill+'_'+option)
        self.skill=skill
        self.family=option in FAMILY_OPTIONS
        self.materials['design']=unreal.load_asset((FAMILY_ROOT if self.family else ROOT)+'/M_'+option)
        assert self.materials['design']
        self.surface=self.plane('design','ReferenceBow')
        self.surface['mid'].set_scalar_parameter_value('Charge',.32 if skill=='E' else .45)
        self.surface['actor'].set_actor_hidden_in_game(True)
        self.contacts=[];self.hidden={};self.shot=-1.;self.fired=False
        self.rotation=None
        self.release_origin=None

    def hide(self,actor):
        if actor.get_path_name() not in self.hidden:self.hidden[actor.get_path_name()]=(actor,actor.get_editor_property('hidden'))
        actor.set_actor_hidden_in_game(True)

    def contact(self,position,t):
        row=self.plane('design','ReferenceImpact')
        row['mid'].set_scalar_parameter_value('Mode',1.)
        row['actor'].set_actor_location(position,False,True)
        if self.rotation:row['actor'].set_actor_rotation(self.rotation,True)
        row['mesh'].set_world_scale3d(unreal.Vector(3.6,3.6,1.))
        row['born']=t
        self.contacts.append(row)
        self.pulse('impact',('Sparks','SparkTrailHeads'),position,unreal.Rotator(),(.4,.4,.4),.2,1.7)

    def update(self,t):
        self.origin=self.rig['skills']().get_arrow_origin()
        if self.family and self.shot>=0.:
            if self.release_origin is None:self.release_origin=self.origin
            self.origin=self.release_origin
        camera=unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](),0).get_camera_location()
        self.rotation=unreal.MathLibrary.make_rot_from_xz(self.forward,camera-self.origin)
        if self.skill=='E':
            for bow in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowHolyBow):
                if bow.get_owner()==self.rig['pawn']() or bow.is_impact():self.hide(bow)
        else:
            for wave in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowShotWave):
                if wave.get_owner()==self.rig['pawn']():self.hide(wave)
        row=self.surface
        row['actor'].set_actor_location(self.origin+self.forward*(110. if self.family else 390.),False,True)
        row['actor'].set_actor_rotation(self.rotation,True)
        row['mesh'].set_world_scale3d(unreal.Vector(11. if self.family else 13.,7.6,1.))
        row['mid'].set_scalar_parameter_value('Age',t)
        row['mid'].set_scalar_parameter_value('ShotAge',self.shot)
        row['actor'].set_actor_hidden_in_game(t>.92)
        if self.shot>=0. and not self.fired:
            self.fired=True
            self.pulse('muzzle',('Sparks',),self.origin,self.rotation,(.65,.65,.65),.18,2.)
        for contact in self.contacts:
            age=t-contact['born']
            contact['mid'].set_scalar_parameter_value('Age',age)
            contact['actor'].set_actor_hidden_in_game(age>.28)
        self.tick()

    def close(self):
        failures=[]
        for actor,hidden in self.hidden.values():
            if BASE['_valid'](actor):
                actor.set_actor_hidden_in_game(hidden)
                if actor.get_editor_property('hidden')!=hidden:failures.append(actor.get_name())
        return failures+super().close()


def sequence(rig):
    before=OLD['OLD']['production_hashes']()
    family=os.environ.get('SPARROW_EW_FAMILY')=='1'
    options=FAMILY_OPTIONS if family else OPTIONS
    designs=FAMILY_DESIGNS if family else DESIGNS
    if os.environ.get('SPARROW_QA_COMPACT_MEMORY')=='1':
        rig['cmd']('r.Streaming.PoolSize 384');rig['cmd']('r.Shadow.Virtual.MaxPhysicalPages 512');yield .5
    selected=os.environ.get('SPARROW_EW_OPTIONS',','.join(options)).split(',')
    skills=['E'] if family else os.environ.get('SPARROW_EW_SKILLS','E,W').split(',')
    skip=set(filter(None,os.environ.get('SPARROW_EW_SKIP','').split(',')))
    expected_count=sum(skill+'_'+option not in skip for skill in skills for option in selected)
    assert all(o in options for o in selected) and all(s in ('E','W') for s in skills)
    rows=[]
    now=lambda:unreal.GameplayStatics.get_time_seconds(rig['world']())
    for skill in skills:
        for option in selected:
            if skill+'_'+option in skip:continue
            rig['switch']('countess');yield .2
            rig['switch']('sparrow');yield .65
            rig['cmd']('CountessComboQA.FlushInput')
            prefix=('BowFamily_' if family else 'EW_')+skill+'_'+option
            rig['case'](prefix)
            targets=rig['layout']([(540,0),(700,280),(780,-280)]);yield .2
            initial=[rig['health'](target) for target in targets];previous=initial[:]
            study=Study(rig,option,skill)
            seen=set();hits=[];started=now()
            moments=[.18,.28,.40,.48,.58] if skill=='E' else [.22,.36,.48,.58,.70]
            try:
                rig['use'](skill,offset=(1100,0))
                rig['STATE']['video_clip']={'case':prefix,'prefix':prefix+'_video','cast_time':started,'frame_times':[]}
                while now()-started<1.40:
                    t=now()-started
                    for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowArrow):
                        if arrow.get_owner()==rig['pawn']() and arrow.get_path_name() not in seen:
                            seen.add(arrow.get_path_name())
                            if study.shot<0.:study.shot=t-arrow.get_distance_travelled()/max(arrow.get_flight_speed(),1.)
                    current=[rig['health'](target) for target in targets]
                    for i,(old,new) in enumerate(zip(previous,current)):
                        if new<old-.01:
                            hits.append({'target':i,'time':t,'damage':old-new})
                            study.contact(targets[i].get_actor_location(),t)
                    previous=current
                    study.update(t)
                    if moments and t>=moments[0]:rig['capture'](prefix+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                    yield 1/rig['FPS']
                rig['finish_video_clip']()
                damage=[old-rig['health'](target) for old,target in zip(initial,targets)]
                expected=60. if skill=='E' else 35.
                rig['check'](len(seen)==1 and len(hits)==1, prefix+' preserves one native projectile and one damage event')
                rig['check'](abs(damage[0]-expected)<.03 and max(damage[1:])<.03,prefix+' preserves native damage with cosmetic layers only')
                rig['check'](study.shot>=.25 and len(study.contacts)==1,prefix+' synchronizes release and impact to observed native events')
                rig['recovered']()
                row={'id':option if family else skill+'_'+option,'skill':skill,'design':option,**designs[option],'installed':False,'video_prefix':prefix+'_video','damage':damage,'hits':hits,'shot_time':study.shot,'native_arrows':len(seen),'visual_review':'pending actual frames'}
                if family:row.update(_family_info(option), fps=rig['FPS'], duration_seconds=1.40)
            finally:
                rig['finish_video_clip']()
                failures=study.close()
            rig['check'](not failures and not study.planes and not study.effects,prefix+' restores visibility and clears temporary props')
            rows.append(row)
            BASE['_write'](rig['OUT'],'bow-family-studies.json' if family else 'ew-reference-studies.json',{'passed':len(rows)==expected_count,'studies':rows,'production_changed':False,'family_branch':family})
    rig['check'](before==OLD['OLD']['production_hashes'](),'Production E sources, material and DebugGame module preserved')
    BASE['_write'](rig['OUT'],'production-preserved.json',{'passed':True,'hashes':before})
