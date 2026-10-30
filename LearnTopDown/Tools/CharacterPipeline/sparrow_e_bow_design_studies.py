"""Four E bow designs in PIE, with the installed skill and materials preserved.

Only Previews/EBowForms20261024 receives saved materials. Each actual E cast
retains its native arrow, collision, 60 damage, montage, timing and impact.
The existing bow actor is hidden only during the isolated comparison; a
collision-free plane carries the candidate. No production source is edited.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import runpy

import unreal

BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
ROOT = '/Game/TopDown/Characters/Sparrow/Previews/EBowForms20261024'
OPTIONS = ('B1', 'B2', 'B3', 'B4')
DESIGNS = {
    'B1': {'label': '성익 장궁', 'shape': '두꺼운 굽은 활과 끝의 소용돌이, 활에서 갈라지는 넓은 깃',
           'motion': '몸체가 먼저 열리고 깃이 뒤따라 퍼진 뒤, 앞의 별빛이 한 발로 압축됨',
           'reference': '원본의 굵은 몸체, 휘어진 끝, 뿌리가 붙은 깃과 중앙 섬광을 가장 직접적으로 반영'},
    'B2': {'label': '왕관 문장궁', 'shape': '두 갈래 금속 곡선, 말린 문양과 마름모 보석, 뾰족한 왕관 끝',
           'motion': '문양을 따라 점화된 빛이 보석에 모이고, 앞의 작은 문장이 펼쳐졌다 닫힘'},
    'B3': {'label': '결정 대궁', 'shape': '두꺼운 투명 결정 면과 분리된 외곽 조각, 하얀 모서리',
           'motion': '안쪽에서 바깥쪽으로 결정 조각이 결합하고 발사 때 모서리가 순간 점등됨'},
    'B4': {'label': '태양 화염궁', 'shape': '넓은 황금 화염 몸체, 어두운 틈과 하얗게 타는 가장자리',
           'motion': '활 내부의 불꽃이 양끝으로 흐르고, 시위를 놓으면 전방으로 짧게 터짐'},
}

SHADER = r'''
struct FShape {
    float Segment(float2 p,float2 a,float2 b) {
        float2 d=b-a; return length(p-a-d*saturate(dot(p-a,d)/max(dot(d,d),.001)));
    }
    float2 Curve(float2 a,float2 b,float2 c,float2 d,float t) {
        float u=1.-t; return u*u*u*a+3.*u*u*t*b+3.*u*t*t*c+t*t*t*d;
    }
    float2 Limb(float t) {
        return Curve(float2(0,0),float2(68,58),float2(10,106),float2(-18,155),t);
    }
    float4 Stroke(float distance,float width) {
        float e=distance-width;
        return float4(1.-smoothstep(-.7,.8,e),exp(-abs(e)*1.5),exp(-distance*1.4),exp(-max(e,0.)*.22)*.20);
    }
    float4 Ribbon(float2 p,float2 a,float2 b,float2 c,float2 d,float width) {
        float edge=1000.,spine=1000.;
        for(int i=0;i<18;i++) {
            float t=i/18.,n=(i+1)/18.;
            float distance=Segment(p,Curve(a,b,c,d,t),Curve(a,b,c,d,n));
            edge=min(edge,distance-width*pow(max(sin(n*3.14159265),.001),.7));
            spine=min(spine,distance);
        }
        return float4(1.-smoothstep(-.7,.8,edge),exp(-abs(edge)*1.5),exp(-spine*1.4),exp(-max(edge,0.)*.22)*.20);
    }
};
FShape S;
const float PI=3.14159265;
const int Variant=DESIGN_NUMBER;
float open=smoothstep(.01,.23,Age);
float fan=smoothstep(.07,.29,Age);
float shot=ShotAge>=0. ? Age-ShotAge : -1.;
float pulse=shot>=0. ? exp(-shot*32.) : 0.;
float envelope=open*(shot<0. ? 1. : 1.-smoothstep(.06,.28,shot));
float2 p=(UV-.5)*float2(700,480)+float2(180,0);
float2 q=float2(p.x,abs(p.y)/max(.08,open));
float signY=p.y>=0.?1.:-1.;
float grain=Texture2DSample(Detail,DetailSampler,UV*float2(4.1,3.7)+float2(-Age*.45,Age*.4)).r;
float4 body=0.,trim=0.,feathers=0.;
float ornaments=0.,energy=0.,front=0.,embers=0.;
float nearest=0.,best=1000.;
float bodyEdge=1000.,bodySpine=1000.,fireField=0.;

if(Variant==1) {
    // The reference has a broad curved limb, curled ends and rooted feathers.
    for(int i=0;i<30;i++) {
        float t=i/30.,n=(i+1)/30.;
        float distance=S.Segment(q,S.Limb(t),S.Limb(n));
        bodyEdge=min(bodyEdge,distance-(4.+7.*sin(n*PI)));
        bodySpine=min(bodySpine,distance);
        if(distance<best){best=distance;nearest=n;}
    }
    trim=max(trim,S.Ribbon(q,float2(-18,155),float2(-62,194),float2(30,211),float2(-9,169),3.1));
    for(int j=0;j<6;j++) {
        float t=.30+j*.095;
        float2 root=S.Limb(t);
        float2 tip=root+float2((-72.+j*7.)*fan,22.+j*8.);
        float density=signY>0.?1.:.78;
        feathers=max(feathers,S.Ribbon(q,root,root+float2(-31.*fan,-7.),tip+float2(11.,-24.),tip,(7.3-j*.55)*density));
    }
    trim=max(trim,S.Ribbon(q,float2(0,10),float2(43,60),float2(-12,111),float2(-29,140),1.3));
}
if(Variant==2) {
    for(int i=0;i<26;i++) {
        float t=i/26.,n=(i+1)/26.;
        float2 a=S.Curve(float2(0,0),float2(59,46),float2(27,104),float2(-7,164),t);
        float2 b=S.Curve(float2(0,0),float2(59,46),float2(27,104),float2(-7,164),n);
        float distance=S.Segment(q,a,b);
        bodyEdge=min(bodyEdge,distance-(4.3+2.8*sin(n*PI)));
        bodySpine=min(bodySpine,distance);
        trim=max(trim,S.Stroke(S.Segment(q,a+float2(-16.*sin(t*PI),0),b+float2(-16.*sin(n*PI),0)),1.35));
        if(distance<best){best=distance;nearest=n;}
    }
    for(int j=0;j<3;j++) {
        float2 root=float2(23.-j*5.,38.+j*44.);
        trim=max(trim,S.Ribbon(q,root,root+float2(-61.,-20.),root+float2(-61.,50.),root+float2(-22.,22.),2.3));
        float2 d=q-(root+float2(-20.,20.));
        float gem=abs(d.x)/8.+abs(d.y)/13.;
        ornaments=max(ornaments,exp(-abs(gem-1.)*9.)+exp(-gem*4.)*.9);
    }
    for(int j=0;j<3;j++) {
        float2 root=float2(-7,147);
        float2 tip=float2(-45.+j*27.,185.+(j==1?24.:0.));
        feathers=max(feathers,S.Ribbon(q,root,root+float2((j-1)*14.,24.),tip+float2(2.,-18.),tip,4.0));
    }
}
if(Variant==3) {
    // Broad faceted panels, not another thin curved outline.
    for(int j=0;j<7;j++) {
        float t=j/7.,n=(j+1)/7.;
        float reveal=smoothstep(j*.024,j*.024+.10,Age);
        float2 a=S.Curve(float2(0,0),float2(65,36),float2(50,94),float2(-8,177),t);
        float2 b=S.Curve(float2(0,0),float2(65,36),float2(50,94),float2(-8,177),n);
        a.x+=(1.-reveal)*38.; b.x+=(1.-reveal)*38.;
        float2 axis=normalize(b-a), across=float2(axis.y,-axis.x), center=(a+b)*.5;
        float2 v=q-center;
        float diamond=abs(dot(v,axis))/(length(b-a)*.78)+abs(dot(v,across))/(20.-j*1.0);
        float filled=(1.-smoothstep(.92,1.,diamond))*reveal;
        body.x=max(body.x,filled*(dot(v,across)>0.?.9:.36));
        body.y=max(body.y,exp(-abs(diamond-1.)*13.)*reveal);
        body.z=max(body.z,exp(-abs(dot(v,across))*2.)*filled);
        body.w=max(body.w,exp(-max(diamond-1.,0.)*6.)*.13*reveal);
        if(j>=2) {
            float2 shard=q-(center+float2(-31.-j*2.,6.));
            float sd=abs(shard.x)/6.+abs(shard.y)/17.;
            ornaments=max(ornaments,(exp(-abs(sd-1.)*9.)+(1.-smoothstep(.5,1.,sd))*.26)*reveal);
        }
    }
    trim=max(trim,S.Ribbon(q,float2(0,7),float2(22,72),float2(-45,135),float2(-26,190),1.6));
}
if(Variant==4) {
    q.x+=sin(q.y*.04-Age*11.)*2.3;
    float fire=Texture2DSample(Fire,FireSampler,float2(q.x*.020+sin(q.y*.03-Age*8.)*.12,-q.y*.018+Age*1.8)).r;
    fireField=fire;
    for(int i=0;i<28;i++) {
        float t=i/28.,n=(i+1)/28.;
        float distance=S.Segment(q,S.Limb(t),S.Limb(n));
        float width=7.+sin(n*PI)*12.+(fire-.5)*9.;
        bodyEdge=min(bodyEdge,distance-width);
        bodySpine=min(bodySpine,distance);
        if(distance<best){best=distance;nearest=n;}
    }
    for(int j=0;j<5;j++) {
        float2 root=S.Limb(.20+j*.14);
        float wave=sin(Age*12.+j*1.7)*8.;
        float2 tip=root+float2(-28.-j*7.+wave,37.+j*5.);
        feathers=max(feathers,S.Ribbon(q,root,root+float2(-13.,-4.),tip+float2(16.+wave,-26.),tip,6.-j*.6));
    }
    trim=max(trim,S.Ribbon(q,float2(-18,155),float2(-37,187),float2(19,201),float2(7,173),2.7));
}
if(Variant!=3) {
    // Compute the outside of the united limb once. Per-segment rims would
    // leave repeated end-cap lines across the filled bow surface.
    body=float4(1.-smoothstep(-.7,.8,bodyEdge),exp(-abs(bodyEdge)*1.5),exp(-bodySpine*1.4),exp(-max(bodyEdge,0.)*.22)*.20);
    if(Variant==4) {
        body.x*=.16+.84*smoothstep(.10,.60,fireField);
        body.y*=.40+.60*fireField;
        energy=pow(saturate(fireField),2.)*body.x*2.1;
    }
}

float draw=shot<0.?smoothstep(.06,.31,Age):.14*exp(-shot*25.);
float stringD=S.Segment(q,float2(Variant==3?-8.:-18.,Variant==3?177.:155.),float2(-23.-66.*draw,0));
float stringCore=exp(-stringD*2.6),stringGlow=exp(-stringD*.42)*.10;
float starTime=shot<0.?smoothstep(.12,.31,Age):exp(-shot*45.);
float2 focus=p-float2(64.,0.);
float star=exp(-abs(focus.y)*1.4-abs(focus.x)*.09)+exp(-abs(focus.x)*1.4-abs(focus.y)*.14);
float center=exp(-length(focus)*.12);
front=(star*1.05+center*1.10)*starTime;
float ready=smoothstep(.09,.27,Age)*(shot<0.?1.:1.-smoothstep(0.,.065,shot));
if(Variant==1) {
    for(int j=0;j<3;j++) {
        float2 a=float2(45.+j*24.,52.-j*10.);
        float2 b=float2(101.+j*17.,0.);
        front+=S.Ribbon(float2(p.x,abs(p.y)),a,a+float2(33.,3.),b+float2(-17.,8.),b,1.1).z*ready*.9;
    }
} else if(Variant==2) {
    float2 v=p-float2(86,0);
    float d=abs(v.x)/25.+abs(v.y)/35.;
    front+=exp(-abs(d-1.)*16.)*ready*.85;
    for(int j=0;j<4;j++) {
        float a=j*PI*.5+PI*.25;
        float2 axis=float2(cos(a),sin(a));
        front+=exp(-S.Segment(v,axis*31.,axis*42.)*2.)*ready*.65;
    }
} else if(Variant==3) {
    for(int j=0;j<3;j++) {
        float2 v=p-float2(68.+j*23.,0.);
        float d=abs(v.x)/12.+abs(v.y)/(24.-j*5.);
        front+=exp(-abs(d-1.)*14.)*ready*.75;
    }
} else {
    for(int j=0;j<4;j++) {
        float2 a=float2(17.-j*11.,36.+j*12.);
        float2 b=float2(105.,0.);
        front+=S.Ribbon(float2(p.x,abs(p.y)),a,a+float2(59.,-6.),b+float2(-13.,12.),b,2.4).x*ready*.7;
    }
}
// Short glints open outward from the limbs; no flat glow disc hides the silhouette.
for(int j=0;j<34;j++) {
    float seed=frac(sin(j*127.1+31.7)*43758.5453);
    float born=.025+seed*.16, t=Age-born;
    float life=saturate(t/.3);
    float2 spot=float2(-40.-seed*52.-t*42.,24.+j*5.1+t*100.);
    float2 v=q-spot;
    float glint=exp(-abs(v.x)*1.7-abs(v.y)*.34)+exp(-abs(v.y)*1.8-abs(v.x)*.42);
    embers+=glint*sin(life*PI)*step(0.,t)*.30;
}
float runner=exp(-pow((nearest-saturate(Age/.23))/.12,2.))*(1.-smoothstep(.23,.4,Age));
float3 gold=float3(1.9,.88,.11),white=float3(2.4,2.05,1.32);
float3 color=gold*(body.x*(.34+grain*.28)+body.w+feathers.x*(.31+grain*.19)+feathers.w+trim.w+stringGlow)
    +white*(body.y*.53+body.z*.12+trim.y*.58+trim.z*.24+feathers.y*.42+feathers.z*.19+ornaments*.8+stringCore*.62)
    +gold*energy+white*runner*body.x*.45;
if(Variant==3)color=gold*(body.x*.44+body.w)+white*(body.y*.85+body.z*.20+trim.z*.65+ornaments*.65+stringCore*.6);
color+=float3(2.3,1.8,.54)*(front+embers);
float alpha=saturate(body.x+body.y+body.w+feathers.x+feathers.y+feathers.w+trim.x+trim.y+trim.w+ornaments+stringCore+stringGlow+front+embers);
return float4(color*(1.+pulse*.25),alpha*envelope);
'''


def write(out, name, data):
    (Path(out)/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def production_hashes():
    project=Path(__file__).resolve().parents[2]
    files=['Source/LearnTopDown/SparrowHolyBow.cpp','Source/LearnTopDown/SparrowHolyBow.h',
           'Source/LearnTopDown/SparrowSkillComponent.cpp','Source/LearnTopDown/SparrowArrow.cpp',
           'Content/TopDown/Characters/Sparrow/Materials/M_SparrowHolyBowFeather.uasset',
           'Binaries/Win64/UnrealEditor-LearnTopDown-Win64-DebugGame.dll']
    return {p:hashlib.sha256((project/p).read_bytes()).hexdigest() for p in files}


def author(out):
    before=production_hashes()
    lib=unreal.MaterialEditingLibrary
    texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Energy/Plasma/T_Sparrow_Poster_Tendrils_v2_Seamless')
    assert texture
    for option in OPTIONS:
        path=ROOT+'/M_'+option
        material=unreal.load_asset(path)
        if material is None:
            folder,name=path.rsplit('/',1)
            material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided',True)
        def node(kind,**props):
            n=lib.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
            for key,value in props.items():n.set_editor_property(key,value)
            return n
        custom=node('Custom',code=SHADER.replace('DESIGN_NUMBER',option[1:]),output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        sources={'UV':node('TextureCoordinate'),'Age':node('ScalarParameter',parameter_name='Age',default_value=.28),
                 'ShotAge':node('ScalarParameter',parameter_name='ShotAge',default_value=-1.),
                 'Detail':node('TextureObject',texture=texture),
                 'Fire':node('TextureObject',texture=unreal.load_asset('/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D'))}
        inputs=[]
        for name in sources:
            item=unreal.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
        custom.set_editor_property('inputs',inputs)
        for name,n in sources.items():assert lib.connect_material_expressions(n,'',custom,name)
        for prop,rgba in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),(unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
            mask=node('ComponentMask',r=rgba[0],g=rgba[1],b=rgba[2],a=rgba[3])
            assert lib.connect_material_expressions(custom,'',mask,'')
            assert lib.connect_material_property(mask,'',prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    assert before==production_hashes()
    result={'passed':True,'production_hashes':before,'preview_assets':[ROOT+'/M_'+o for o in OPTIONS],'designs':DESIGNS}
    write(out,'bow-design-materials.json',result)
    return result


class Study(BASE['Study']):
    def __init__(self,rig,option):
        super().__init__(rig,option)
        self.materials['design']=unreal.load_asset(ROOT+'/M_'+option)
        assert self.materials['design']
        self.surface=self.plane('design','BowDesign')
        self.surface['actor'].set_actor_hidden_in_game(True)
        self.hidden={}
        self.bow=None
        self.started=None
        self.shot=-1.

    def update(self,started):
        for bow in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowHolyBow):
            if bow.is_impact() or bow.get_owner()!=self.rig['pawn']():continue
            if self.bow is None:
                self.bow=bow
                self.hidden[bow.get_path_name()]=(bow,bow.get_editor_property('hidden'))
            bow.set_actor_hidden_in_game(True)
            mesh=next(c for c in bow.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='RadiantBow')
            rotation=mesh.get_world_rotation()
            forward=unreal.MathLibrary.get_forward_vector(rotation)
            row=self.surface
            row['actor'].set_actor_location(mesh.get_world_location()+forward*225.,False,True)
            row['actor'].set_actor_rotation(rotation,True)
            row['mesh'].set_world_scale3d(unreal.Vector(8.75,6.0,1.))
            row['actor'].set_actor_hidden_in_game(False)
            if bow.get_shots_observed() and self.shot<0.:self.shot=self.now()-started
        age=self.now()-started
        self.surface['mid'].set_scalar_parameter_value('Age',age)
        self.surface['mid'].set_scalar_parameter_value('ShotAge',self.shot)
        if age>.80:self.surface['actor'].set_actor_hidden_in_game(True)

    def close(self):
        failures=[]
        for actor,hidden in self.hidden.values():
            if BASE['_valid'](actor):
                actor.set_actor_hidden_in_game(hidden)
                if actor.get_editor_property('hidden')!=hidden:failures.append(actor.get_name())
        return failures+super().close()


def sequence(rig):
    before=production_hashes()
    options=[x for x in os.environ.get('SPARROW_BOW_DESIGNS',','.join(OPTIONS)).split(',') if x]
    assert options and all(x in OPTIONS for x in options)
    now=lambda:unreal.GameplayStatics.get_time_seconds(rig['world']())
    rows=[]
    for option in options:
        rig['switch']('countess');yield .2
        rig['switch']('sparrow');yield .7
        rig['cmd']('CountessComboQA.FlushInput')
        prefix='BowDesign_'+option
        rig['case'](prefix)
        targets=rig['layout']([(420,0),(700,0),(600,370)]);yield .2
        health=[rig['health'](t) for t in targets]
        study=Study(rig,option)
        arrows=set();impacts=set();hits=[];old=health[:]
        moments=[.18,.28,.43,.55]
        started=now()
        try:
            rig['use']('E',offset=(950,0))
            rig['STATE']['video_clip']={'case':prefix,'prefix':prefix+'_video','cast_time':started,'frame_times':[]}
            while now()-started<1.35:
                study.update(started)
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowArrow):
                    if arrow.get_owner()==rig['pawn']():arrows.add(arrow.get_name())
                for impact in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowHolyBow):
                    if impact.is_impact():impacts.add(impact.get_name())
                current=[rig['health'](t) for t in targets]
                if current!=old:hits.append({'time':now()-started,'damage':[a-b for a,b in zip(old,current)]});old=current
                if moments and now()-started>=moments[0]:rig['capture'](prefix+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage=[a-rig['health'](t) for a,t in zip(health,targets)]
            rig['check'](len(arrows)==1 and len(hits)==1 and len(impacts)==1,option+' retains one native arrow, contact and damage event')
            rig['check'](abs(damage[0]-60)<.03 and max(damage[1:])<.03,option+' retains 60 damage and no cosmetic damage')
            rig['check'](study.shot>=.30 and len(study.hidden)==1,option+' synchronizes its visual to the native E')
            rig['recovered']()
            row={'id':option,**DESIGNS[option],'installed':False,'native_damage':damage,'hits':hits,'shot_time':study.shot,
                 'video_prefix':prefix+'_video','duration':1.35,'visual_review':'pending actual game frames'}
        finally:
            rig['finish_video_clip']()
            failures=study.close()
        rig['check'](not failures and not study.planes,option+' restores native visibility and clears its preview')
        rows.append(row)
        write(rig['OUT'],'bow-design-studies.json',{'passed':len(rows)==len(options),'studies':rows,'production_changed':False})
    rig['check'](before==production_hashes(),'Production E sources, native material and DebugGame DLL unchanged')
    write(rig['OUT'],'production-preserved.json',{'passed':True,'hashes':before})
