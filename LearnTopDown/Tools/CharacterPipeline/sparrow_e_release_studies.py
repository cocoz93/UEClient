"""E opening/release studies. Native shot, damage and animation remain unchanged.

Preview-only bow and contact surfaces are attached to observed native events.
The earlier shape studies remain reproducible and installed assets are untouched.
"""
import os
from pathlib import Path
import runpy
import unreal

OLD = runpy.run_path(str(Path(__file__).with_name('sparrow_e_bow_design_studies.py')))
BASE = OLD['BASE']
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/ERelease20261024'
OPTIONS = ('C1', 'C2', 'C3')
DESIGNS = {
    'C1': {'label': '천익 개방', 'shape': '금빛 활에서 긴 깃이 차례로 펴지고, 바깥쪽 잔광이 뒤따름',
           'motion': '중심 점화 → 활 개방 → 깃의 연쇄 전개 → 한 발과 두 겹의 짧은 접촉 파열'},
    'C2': {'label': '광휘 현궁', 'shape': '세 겹의 넓은 빛줄기가 휘감겨 활을 만들고, 표면의 빛이 흐름',
           'motion': '엇갈리는 곡선의 개방 → 시위로 빛 응축 → 단발과 사선 교차 타격'},
    'C3': {'label': '뇌광 성궁', 'shape': '분리된 굵은 활 조각들이 결합하며 금백색 번개로 연결됨',
           'motion': '조각 집결 → 활 전체 전류 → 한 발 관통광과 명중점의 두 차례 균열'},
}

SHADER = r'''
struct FShape {
 float Seg(float2 p,float2 a,float2 b){float2 v=b-a;return length(p-a-v*saturate(dot(p-a,v)/max(dot(v,v),.001)));}
 float2 Bez(float2 a,float2 b,float2 c,float2 d,float t){float u=1.-t;return a*u*u*u+3.*b*u*u*t+3.*c*u*t*t+d*t*t*t;}
 float4 Rib(float2 p,float2 a,float2 b,float2 c,float2 d,float w,float reveal){
  float edge=1000.,spine=1000.;
  for(int i=0;i<20;i++){float t=i/20.,n=min((i+1)/20.,reveal);if(t>=reveal)break;
   float dist=Seg(p,Bez(a,b,c,d,t),Bez(a,b,c,d,n));
   edge=min(edge,dist-w*pow(max(sin((t+n)*1.5707963),.0001),.65));spine=min(spine,dist);}
  return float4(1.-smoothstep(-.7,.9,edge),exp(-abs(edge)*1.7),exp(-spine*2.),exp(-max(edge,0.)*.15)*.16);
 }
 float Hash(float x){return frac(sin(x*127.1+71.7)*43758.5453);}
 float Star(float2 p,float size){p/=max(size,.001);return exp(-abs(p.x)*1.25-abs(p.y)*.095)+exp(-abs(p.y)*1.3-abs(p.x)*.08);}
};
FShape F;
const float PI=3.14159265;
const int V=DESIGN_NUMBER;
float3 gold=float3(2.3,.88,.09),ivory=float3(3.2,2.65,1.64);
float3 col=0.;float alpha=0.;
if(Mode>.5){
 // Cosmetic contacts are born only when the real native arrow contacts.
 float2 p=(UV-.5)*400.;float t=Age;
 for(int burst=0;burst<2;burst++){
  float a=t-burst*.058;if(a<0.||a>.26)continue;
  float fade=1.-smoothstep(.025,.24,a),shock=exp(-a*42.);
  float2 q=p-float2(burst*12.,0.);
  float axial=exp(-abs(q.y)*.55-abs(q.x)*.035)*shock;
  float cross=F.Star(q,float(burst==0?2.4:1.6))*shock;
  col+=ivory*(axial*2.+cross*.85);alpha=max(alpha,saturate(axial+cross));
  for(int j=0;j<34;j++){
   float seed=F.Hash(j+burst*43.);
   float angle=j*2.39996+burst*.6;
   float2 axis=float2(cos(angle),sin(angle));
   float r=10.+a*(170.+seed*200.);
   float len=(8.+seed*24.)*fade;
   float2 tip=axis*(r+len);float2 start=axis*r;
   float dist=F.Seg(q,start,tip),streak=exp(-dist*(V==1?1.0:1.7))*fade;
   col+=lerp(gold,ivory,seed)*streak*.85;alpha=max(alpha,streak);
  }
  if(V==1){
   for(int j=0;j<3;j++){
    float2 end=float2(66.+j*15.,(j-1)*42.);float2 p1=float2(-22.,(j-1)*7.);
    float slash=exp(-F.Seg(q,p1,end)*1.2)*exp(-a*21.);
    col+=ivory*slash*1.2;alpha=max(alpha,slash);
   }
  }else if(V==2){
   for(int j=0;j<3;j++){
    float angle=.6+j*.85,ca=cos(angle),sa=sin(angle);
    float2 s=float2(q.x*ca+q.y*sa,-q.x*sa+q.y*ca);
    float slash=exp(-abs(s.y)*1.25)*pow(saturate(1.-abs(s.x)/110.),.55)*exp(-a*18.);
    col+=ivory*slash*1.4;alpha=max(alpha,slash);
   }
  }else{
   for(int j=0;j<7;j++){
    float angle=j*2.*PI/7.+.2;float2 axis=float2(cos(angle),sin(angle)),across=float2(-axis.y,axis.x);
    float2 prev=axis*6.;float bolt=1000.;
    for(int k=1;k<7;k++){
     float2 next=axis*(k*14.+a*70.)+across*(F.Hash(j*11.+k)*2.-1.)*12.;
     bolt=min(bolt,F.Seg(q,prev,next));prev=next;}
    float b=exp(-bolt*2.)*exp(-a*16.);col+=ivory*b*1.2+gold*exp(-bolt*.3)*b*.3;alpha=max(alpha,b);
   }
  }
 }
 return float4(col,alpha);
}
float shot=ShotAge>=0.?Age-ShotAge:-1.;
float opened=smoothstep(.015,.23,Age);
float env=smoothstep(.005,.035,Age)*(shot<0.?1.:1.-smoothstep(.025,.24,shot));
float recoil=shot<0.?0.:sin(min(shot/.16,1.)*PI)*10.;
float2 p=(UV-.5)*float2(900,700)+float2(240,0);
float2 q=float2(p.x+recoil,abs(p.y));
float side=p.y>=0.?1.:-1.;
float grain=Texture2DSample(Detail,DetailSampler,UV*float2(5.,4.)+float2(-Age*.8,Age*.4)).r;
float fire=Texture2DSample(Fire,FireSampler,float2(p.x*.015+Age*.5,q.y*.014-Age*1.6)).r;
float4 body=0.,feathers=0.,trim=0.;float lace=0.,sparks=0.,wisps=0.;
float2 a=float2(-5.,0.);
float2 b=float2(72.+(1.-opened)*64.,52.*opened);
float2 c=float2(27.+(1.-opened)*75.,133.*opened);
float2 d=float2(-22.+(1.-opened)*110.,201.*opened);
float reveal=smoothstep(.015,.15,Age);
if(V==1){
 body=F.Rib(q,a,b,c,d,11.5,reveal);
 trim=F.Rib(q,d,d+float2(-48.,32.),d+float2(36.,70.),d+float2(12.,13.),3.1,smoothstep(.13,.25,Age));
 for(int j=0;j<8;j++){
  float f=smoothstep(.055+j*.014,.15+j*.014,Age);
  float t=.25+j*.078;float2 root=F.Bez(a,b,c,d,t);
  float2 tip=root+float2((-80.+j*5.)*f,18.+j*7.*f);
  float4 feather=F.Rib(q,root,root+float2(-30.*f,-15.*f),tip+float2(14.,-34.),tip,7.7-j*.55,f);
  feathers=max(feathers,feather);
  float4 vein=F.Rib(q,root,root+float2(-26.*f,-5.),tip+float2(9.,-23.),tip,0.8,f);
  lace+=vein.z*.32;
 }
 trim=max(trim,F.Rib(q,float2(-7.,10.),b+float2(-12.,0.),c+float2(-14.,-6.),d+float2(-8.,-7.),1.2,reveal));
}else if(V==2){
 for(int j=0;j<3;j++){
  float op=smoothstep(.025+j*.035,.19+j*.025,Age);
  float shift=j*18.;float spread=1.-op;
  float2 bb=float2(85.+shift,39.+spread*70.);
  float2 cc=float2(47.-j*36.,140.*op);
  float2 dd=float2(-38.-j*23.,(194.-j*18.)*op);
  float4 ribbon=F.Rib(q,float2(-5.+j*6.,0.),bb,cc,dd,10.-j*1.6,op);
  body=max(body,ribbon);
  trim=max(trim,F.Rib(q,dd,dd+float2(-40.,38.),dd+float2(43.,50.),dd+float2(20.,6.),2.7,op));
  float4 echo=F.Rib(q-float2(-8.*spread,10.*spread),float2(-5.+j*6.,0.),bb+float2(-17.,10.),cc+float2(-18.,0.),dd+float2(-10.,10.),2.2,op);
  wisps+=echo.x*(.25+.75*fire)*.52;
 }
 for(int j=0;j<5;j++){
  float2 root=F.Bez(a,b,c,d,.28+j*.12);float f=smoothstep(.08+j*.018,.22+j*.012,Age);
  feathers=max(feathers,F.Rib(q,root,root+float2(-36.,-18.),root+float2(-78.,27.),root+float2(-49.,54.),4.8,f));
 }
}else{
 // A recurve with strong solid shoulders, split by small dark joints.
 body=F.Rib(q,a,b,c,d,12.7,reveal);
 float joints=1.-smoothstep(.03,.13,abs(sin(q.y*.14)));
 body.x*=1.-joints*.68;
 for(int j=0;j<8;j++){
  float t=j/8.,n=(j+.91)/8.;float form=smoothstep(.015+j*.017,.11+j*.018,Age);
  float2 aa=F.Bez(a,b,c,d,t),dd=F.Bez(a,b,c,d,n);
  float2 delta=float2((1.-form)*(28.+j*5.),(1.-form)*j*7.);
  float4 segment=F.Rib(q,aa+delta,lerp(aa,dd,.33)+delta,lerp(aa,dd,.67)+delta,dd+delta,9.+sin(t*PI)*4.5,1.);
  if(j>1){float2 root=dd+delta;feathers=max(feathers,F.Rib(q,root,root+float2(-18.,-4.),root+float2(-30.,14.),root+float2(-25.,29.),3.2,form));}
 }
 for(int j=0;j<2;j++){
  float bolt=1000.;float2 prev=float2(-3.,0.);
  for(int k=1;k<25;k++){
   float t=k/24.;float2 next=F.Bez(a,b,c,d,t)+float2(sin(t*91.+Age*52.+j*3.)*8.+(j-.5)*13.,0.);
   bolt=min(bolt,F.Seg(q,prev,next));prev=next;}
  lace+=exp(-bolt*1.8)*smoothstep(.06,.23,Age);
 }
 trim=F.Rib(q,d,d+float2(-45.,26.),d+float2(-16.,65.),d+float2(18.,32.),3.,reveal);
}
// The moving outer silhouette is a brief opening echo, not a permanent flat halo.
for(int j=0;j<2;j++){
 float delay=.035+j*.045;float op=smoothstep(delay,delay+.16,Age);
 float f=sin(op*PI)*(1.-smoothstep(.22,.32,Age));
 float4 echo=F.Rib(q,float2(-7.,0.),b+float2(-20.-j*13.,20.),c+float2(-27.-j*18.,20.),d+float2(-24.-j*20.,16.),2.0,op);
 wisps+=echo.x*f*.52;
}
// Short outward sparks along the unfolding tips, followed by inward motes.
for(int j=0;j<56;j++){
 float seed=F.Hash(j),born=.035+seed*.17,t=Age-born,life=saturate(t/.26);
 float2 root=F.Bez(a,b,c,d,.15+F.Hash(j+17.)*.83);
 float2 velocity=float2(-90.-seed*130.,40.+seed*100.);
 float2 loc=root+velocity*t;
 float2 tail=loc-velocity*.035;
 float value=exp(-F.Seg(q,loc,tail)*2.2)*sin(life*PI)*step(0.,t);
 sparks+=value*.55;
 if(j<18){float travel=saturate((Age-.12)/.19);float2 loc2=lerp(float2(-105.+seed*230.,70.+seed*115.),float2(54.,0.),travel);
 sparks+=F.Star(p-float2(loc2.x,loc2.y*side),.42)*sin(travel*PI)*.35;}
}
float draw=shot<0.?smoothstep(.06,.31,Age):.1*exp(-shot*25.);
float stringD=F.Seg(q,d,float2(-25.-60.*draw,0.));
float stringCore=exp(-stringD*2.3),stringHaze=exp(-stringD*.33)*.12;
float ready=smoothstep(.15,.32,Age)*(shot<0.?1.:exp(-shot*40.));
float2 focus=p-float2(48.,0.);
float focal=(F.Star(focus,1.3)+exp(-length(focus)*.12)*.35)*ready;
// Small curved converging ribbons lead the eye into the single release.
float front=0.;
for(int j=0;j<2;j++){
 float4 r=F.Rib(float2(p.x,abs(p.y)),float2(34.+j*18.,52.+j*9.),float2(68.+j*18.,59.),float2(90.+j*14.,12.),float2(108.+j*10.,0.),1.4,ready);
 front+=r.z*.6+r.w*.15;
}
float release=0.,wake=0.;
if(shot>=0.&&shot<.11){
 float length=230.+shot*1400.,tail=10.+shot*900.;
 release=exp(-F.Seg(p,float2(tail,0.),float2(length,0.))*1.3)*(1.-smoothstep(.035,.10,shot));
 for(int j=0;j<12;j++){
  float y=(F.Hash(j+54.)-.5)*40.,x=40.+F.Hash(j+8.)*130.+shot*1600.;
  wake+=exp(-F.Seg(p,float2(x,y),float2(x+25.,y*.5))*1.5)*(1.-smoothstep(.025,.09,shot))*.45;
 }
}
float shade=.23+.31*grain;
if(V==2)shade=.14+pow(fire,.7)*.56;
col=gold*(body.x*shade+body.w+feathers.x*(.25+grain*.24)+feathers.w+trim.w+wisps+stringHaze)
 +ivory*(body.y*.63+body.z*.08+feathers.y*.55+feathers.z*.12+trim.y*.62+trim.z*.13+lace*.65+sparks+stringCore*.65+focal+front)
 +ivory*(release*1.7+wake);
alpha=saturate(body.x+body.w+body.y+feathers.x+feathers.w+trim.x+trim.w+lace+wisps+sparks+stringCore+stringHaze+focal+front+release+wake);
return float4(col,alpha*env);
'''


def author(out):
    before=OLD['production_hashes']()
    lib=unreal.MaterialEditingLibrary
    textures={'Detail':unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless'),
              'Fire':unreal.load_asset('/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D')}
    for option in OPTIONS:
        path=ROOT+'/M_'+option
        material=unreal.load_asset(path)
        if not material:
            folder,name=path.rsplit('/',1)
            material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
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
        for name,value in [('Age',.25),('ShotAge',-1.),('Mode',0.)]:
            inputs[name]=node('ScalarParameter',parameter_name=name,default_value=value)
        for name,texture in textures.items():
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
    assert before==OLD['production_hashes']()
    result={'passed':True,'production_hashes':before,'assets':[ROOT+'/M_'+o for o in OPTIONS]}
    OLD['write'](out,'release-materials.json',result)
    return result


class Study(BASE['Study']):
    def __init__(self,rig,option):
        super().__init__(rig,option)
        self.materials['design']=unreal.load_asset(ROOT+'/M_'+option)
        assert self.materials['design']
        self.surface=self.plane('design','ReleaseBow')
        self.contact=self.plane('design','ReleaseContact')
        self.contact['mid'].set_scalar_parameter_value('Mode',1.)
        for row in [self.surface,self.contact]:row['actor'].set_actor_hidden_in_game(True)
        self.hidden={};self.impact_hidden={};self.shot=-1.;self.contact_time=None
        self.rotation=None

    def update(self,started):
        age=self.now()-started
        for bow in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowHolyBow):
            if bow.is_impact():
                if self.contact_time is None:
                    self.contact_time=self.now()
                    self.impact_hidden[bow.get_path_name()]=(bow,bow.get_editor_property('hidden'))
                    self.contact['actor'].set_actor_location(bow.get_actor_location(),False,True)
                    if self.rotation:self.contact['actor'].set_actor_rotation(self.rotation,True)
                    self.contact['mesh'].set_world_scale3d(unreal.Vector(4.8,4.8,1.))
                bow.set_actor_hidden_in_game(True)
                continue
            if bow.get_owner()!=self.rig['pawn']():continue
            if bow.get_path_name() not in self.hidden:self.hidden[bow.get_path_name()]=(bow,bow.get_editor_property('hidden'))
            bow.set_actor_hidden_in_game(True)
            mesh=next(c for c in bow.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='RadiantBow')
            self.rotation=mesh.get_world_rotation()
            forward=unreal.MathLibrary.get_forward_vector(self.rotation)
            self.surface['actor'].set_actor_location(mesh.get_world_location()+forward*288.,False,True)
            self.surface['actor'].set_actor_rotation(self.rotation,True)
            self.surface['mesh'].set_world_scale3d(unreal.Vector(10.8,8.4,1.))
            self.surface['actor'].set_actor_hidden_in_game(False)
            if bow.get_shots_observed() and self.shot<0.:self.shot=age
        self.surface['mid'].set_scalar_parameter_value('Age',age)
        self.surface['mid'].set_scalar_parameter_value('ShotAge',self.shot)
        if age>.8:self.surface['actor'].set_actor_hidden_in_game(True)
        if self.contact_time is not None:
            t=self.now()-self.contact_time
            self.contact['mid'].set_scalar_parameter_value('Age',t)
            self.contact['actor'].set_actor_hidden_in_game(t>.33)

    def close(self):
        failures=[]
        for actor,hidden in [*self.hidden.values(),*self.impact_hidden.values()]:
            if BASE['_valid'](actor):
                actor.set_actor_hidden_in_game(hidden)
                if actor.get_editor_property('hidden')!=hidden:failures.append(actor.get_name())
        return failures+super().close()


def sequence(rig):
    # Reuse the established one-arrow/60-damage/recovery/cleanup capture harness.
    # Only this isolated runpy namespace is configured; no earlier script changes.
    scope=OLD['sequence'].__globals__
    scope.update(OPTIONS=OPTIONS,DESIGNS=DESIGNS,Study=Study)
    yield from OLD['sequence'](rig)
