"""One energy-oriented revision per requested skill; shared PIE tooling.

E/A are installed presentation changes. Q/S/D/F/B are isolated real-input
previews until their new visual direction has been reviewed.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal

HELPER=runpy.run_path(str(Path(__file__).with_name('sparrow_e_design_materials.py')))
BASE=runpy.run_path(str(Path(__file__).with_name('sparrow_polish_studies.py')))
BaseStudy,valid,clamp=BASE['Study'],BASE['valid'],BASE['clamp']
ROOT='/Game/TopDown/Characters/Sparrow/Materials/EnergyFeedback20261028'
DESIGNS={
    'A5':('53번 + 새 화살','왼쪽은 53번의 작은 나선 파편 꼬리, 오른쪽은 현재 새 화살'),
    'A4':('기존 · 신규 쌍화살','기존 화살과 새 타원 궤적 화살이 약간 떨어져 함께 전진'),
    'S6':('S 롤백','이번 Harmony 재작업 전 기본 S 표현으로 복원'),
    'Q3':('광창 낙하','굵기가 다른 광창이 한 번에 꽂히고 짧은 접촉 파열과 옅은 지속광으로 연결'),
    'E5':('갈고리 · 겹날 활','손잡이 양옆의 갈고리와 양끝 겹날을 강조하고 연결부를 가늘게 제작'),
    'A3':('타원 잔류 궤적','중앙 화살을 감싸는 두 흐름이 타원을 돌며 가는 질감의 잔류 궤적을 남김'),
    'S5':('압축 사격','양옆에서 곡선 광류가 발사점으로 접히고 근거리 밀집 사격으로 이어짐'),
    'D5':('활 결속 사격','실제 활의 양끝에서 활시위 쪽으로 에너지가 모인 뒤 관통 사격'),
    'F5':('흡수 · 각인 화살','빛이 흡수된 뒤 갈라진 촉과 깃이 있는 세공 화살을 발사'),
    'B4':('쌍점 단광','출발과 실제 도착점에 짧고 강한 접촉광과 방향성 파열'),
    'Q2':('광핵 낙하','상공에서 응축된 광핵이 굵은 한 타로 낙하하고 지면에서 불꽃이 폭발'),
    'E4':('첨예 깃활 · E1 문양','가느다란 활 몸통과 뾰족한 중앙·끝, 문양 등장 후 실제 사격과 소멸'),
    'A2':('타원 공전','타원을 따라 도는 두 갈래 화염과 짧은 접선 잔광'),
    'S4':('압축 · 화염 파열','겹광륜이 화염을 중심으로 끌어들인 뒤 전방으로 터짐'),
    'D4':('활 응축 · 순간 분출','활의 위아래 불꽃이 발사점에 모였다가 관통탄과 함께 짧게 분출'),
    'F4':('흡수 핵 · 장창 화살','작은 빛과 불꽃을 흡수한 뒤 날카로운 촉·긴 축·화살깃이 펼쳐져 발사'),
    'B3':('쌍점 섬광 파열','출발은 빠르게 압축, 도착은 순간적으로 벌어지는 짧고 강한 파열'),
}

JET=r'''
float u=saturate(UV.x), v=UV.y-.5;
float n=Texture2DSample(Flow,FlowSampler,float2(u*1.8-Age*1.6,UV.y*2.1+Index*.17)).r;
float d=Texture2DSample(Flow,FlowSampler,float2(u*4.3-Age*2.8,UV.y*5.2)).g;
float warp=(n-.5)*.13*sin(u*3.14159);
float width=(.055+.28*pow(1.-u,.8))*(.72+.28*d);
float body=pow(saturate(1.-abs(v+warp)/width),1.2);
float core=exp(-pow((v+warp*.4)/(.012+.025*(1.-u)),2.));
float ends=smoothstep(0.,.09,u)*(1.-smoothstep(.88,1.,u));
float torn=smoothstep(.11,.57,n*.68+d*.5+body*.25);
float alpha=saturate((body*torn*.88+core*.40)*ends*Envelope);
float3 rgb=lerp(float3(1.5,.25,.018),float3(3.8,2.2,.65),saturate(body*.7+core*.5));
return float4(rgb,alpha);
'''
FRONT=r'''
float2 p=(UV-.5)*2.;float r=length(p);float a=atan2(p.y,p.x);
float n=Texture2DSample(Flow,FlowSampler,p*1.7+float2(Age*.5,-Age*.8)).r;
float b=Texture2DSample(Flow,FlowSampler,p*4.1+float2(-Age*.7,Age*.2)).g;
float rim=exp(-pow((r-(.72+(n-.5)*.09))/.10,2.));
float center=exp(-r*r*10.);
float tongues=pow(saturate(.5+.5*sin(a*7.+n*4.-Age*3.)),3.);
float field=pow(saturate(1.-r),1.4)*smoothstep(.23,.75,n*.75+b*.45);
float alpha=saturate((rim*(.32+.65*tongues)+field*.7+center*.30)*Envelope);
return float4(float3(3.4,1.45,.17)*(1.+center*.25),alpha);
'''
ELLIPSE=r'''
float2 p=(UV-.5)*2.;float r=length(p);float a=atan2(p.y,p.x)/6.283185+.5;
float phase=frac(a-Age*.18), second=frac(phase+.5);
float n=Texture2DSample(Flow,FlowSampler,float2(a*2.1-Age*.32,r*2.)).r;
float tail=pow(1.-saturate(min(phase,second)/.34),.75);
float width=.028+.10*tail;
float band=pow(saturate(1.-abs(r-(.69+(n-.5)*.065))/width),.70);
float tears=smoothstep(.09,.66,n*.75+band*.45);
return float4(float3(2.7,1.25,.20),band*tail*tears*Envelope*.88);
'''
PLASMA=r'''
float frame=12.+frac(Age*1.3+Index*.137)*43.;float cell=floor(frame);
float2 uv=saturate(UV*.94+.03);
float2 uv0=(float2(fmod(cell,8.),floor(cell/8.))+uv)/8.;
float2 uv1=(float2(fmod(cell+1.,8.),floor((cell+1.)/8.))+uv)/8.;
float density=lerp(Texture2DSample(Flow,FlowSampler,uv0).a,Texture2DSample(Flow,FlowSampler,uv1).a,frac(frame));
float edge=smoothstep(0.,.06,UV.x)*(1.-smoothstep(.94,1.,UV.x))*smoothstep(0.,.06,UV.y)*(1.-smoothstep(.94,1.,UV.y));
float alpha=pow(saturate(density),.77)*edge*Envelope;
return float4(lerp(float3(1.6,.30,.018),float3(4.0,2.35,.72),saturate(density*1.4)),alpha);
'''
METAL=r'''
float3 n=normalize(Normal);
float facet=pow(abs(dot(n,normalize(float3(.25,-.4,.82)))),3.);
float grain=Texture2DSample(Flow,FlowSampler,float2(UV.x*6.-Age*.12,UV.y*2.)).r;
float ridge=pow(saturate(.5+.5*sin(UV.y*25.1327)),16.);
float3 rgb=lerp(float3(.55,.19,.015),float3(3.5,2.7,1.12),facet*.85+ridge*.15);
return float4(rgb*(.84+grain*.16),Envelope);
'''
LANCE=r'''
float u=saturate(UV.x),y=abs(UV.y-.5);
float headStart=.71,headEnd=.985;
float headWidth=(headEnd-u)/(headEnd-headStart)*.27;
float head=(1.-smoothstep(headWidth-.009,headWidth+.006,y))*smoothstep(headStart-.005,headStart+.006,u)*(1.-step(headEnd,u));
float shaft=(1.-smoothstep(.012,.022,y))*smoothstep(.07,.12,u)*(1.-smoothstep(.82,.87,u));
float tailU=saturate((u-.035)/.18);
float featherWidth=.20*(1.-tailU);
float tail=(1.-smoothstep(featherWidth-.008,featherWidth+.008,y))*smoothstep(.03,.05,u)*(1.-smoothstep(.20,.23,u));
float notch=smoothstep(.035,.055,y+.15*tailU);
tail*=notch;
float n=Texture2DSample(Flow,FlowSampler,float2(u*6.-Age*.8,UV.y*3.)).r;
float bevel=exp(-pow((y-headWidth+.022)/.012,2.))*head;
float midrib=exp(-pow(y/.008,2.));
float fill=saturate(head+shaft+tail);
float edge=saturate(bevel+midrib*.6+tail*(.35+.4*n));
float3 rgb=lerp(float3(1.10,.32,.025),float3(3.6,2.7,1.25),edge);
return float4(rgb,fill*Envelope);
'''

def author(output):
    output=Path(output)
    source=Path(__file__).resolve().parent/'ArtSources/EnergyFeedback20261028/FeatherBow-sharp.png'
    task=unreal.AssetImportTask()
    meshroot=HELPER['MESH_ROOT']
    for key,value in {'filename':str(source),'destination_path':meshroot,'destination_name':'T_E9SharpBow',
                      'automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=unreal.load_asset(meshroot+'/T_E9SharpBow');assert texture
    for key,value in {'srgb':True,'never_stream':True,'compression_no_alpha':False,
                      'compression_settings':unreal.TextureCompressionSettings.TC_BC7,
                      'address_x':unreal.TextureAddress.TA_CLAMP,'address_y':unreal.TextureAddress.TA_CLAMP}.items():
        texture.set_editor_property(key,value)
    texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
    import hashlib
    unreal.EditorAssetLibrary.set_metadata_tag(texture,'E8ImageHash',hashlib.sha256(source.read_bytes()).hexdigest())
    assert unreal.EditorAssetLibrary.save_loaded_asset(texture,False)
    flow=unreal.load_asset(HELPER['FLOW']);art=unreal.load_asset(HELPER['ART'])
    rows=[]
    _,row=HELPER['_material']('M_E9FeatherBow',HELPER['PLUME_BOW'],flow,art,texture);rows.append(row)
    for name,code in (('M_EllipseWisps',ELLIPSE),('M_LanceMetal',METAL)):
        _,row=HELPER['_material'](name,code,flow,art,folder=ROOT);rows.append(row)
    plasma=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Energy/T_Plasma_Wisps');assert plasma
    for name in ('M_EnergyJet','M_EnergyFront'):
        _,row=HELPER['_material'](name,PLASMA,plasma,art,folder=ROOT);rows.append(row)
    # A real eight-sided shaft, four bevelled head facets and four tail vanes.
    vertices=[];uvs=[];faces=[]
    def vertex(p,uv):vertices.append(p);uvs.append(uv);return len(vertices)
    rings=[]
    for x,radius in ((-248.,3.5),(-154.,4.),(122.,3.7),(152.,5.)):
        rings.append([vertex((x,math.cos(i*math.tau/8.)*radius,math.sin(i*math.tau/8.)*radius),((x+260.)/520.,i/8.)) for i in range(8)])
    for a,b in zip(rings,rings[1:]):
        for i in range(8):j=(i+1)%8;faces.extend([(a[i],b[i],b[j]),(a[i],b[j],a[j])])
    tip=vertex((260.,0.,0.),(1.,.5));back=vertex((116.,0.,0.),(.72,.5))
    rim=[vertex((136.,math.cos(i*math.tau/4.)*42.,math.sin(i*math.tau/4.)*22.),(.76,i/4.)) for i in range(4)]
    for i in range(4):j=(i+1)%4;faces.extend([(rim[i],tip,rim[j]),(rim[j],back,rim[i])])
    for i in range(4):
        a=i*math.tau/4.;y,z=math.cos(a),math.sin(a)
        ids=[vertex(p,uv) for p,uv in (((-253.,y*4.,z*4.),(.01,.5)),((-243.,y*36.,z*36.),(.03,.9)),((-153.,y*11.,z*11.),(.21,.7)),((-178.,y*3.,z*3.),(.16,.5)))]
        faces.extend([(ids[0],ids[1],ids[2]),(ids[0],ids[2],ids[3])])
    import hashlib
    digest=hashlib.sha256(repr((vertices,uvs,faces)).encode()).hexdigest()
    material=unreal.load_asset(ROOT+'/M_LanceMetal')
    path=HELPER['MESH_ROOT']+'/SM_FLongLance'
    mesh=unreal.load_asset(path)
    if not mesh or unreal.EditorAssetLibrary.get_metadata_tag(mesh,'EnergyLance')!=digest:
        importer=runpy.run_path(str(Path(__file__).with_name('countess_ruin_surface.py')))['_import_mesh']
        row=importer(output,material,path,vertices,uvs,faces,'EnergyLance',digest,(513.,83.,85.,71.,73.),len(faces)-2,8)
        rows.append(row)
    result={'passed':True,'materials':rows,'source_image':str(source),'shared_old_texture_modified':False}
    (output/'energy-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

class Study(BaseStudy):
    def __init__(self,rig,option):
        super().__init__(rig,option)
        self.energy=[]
        for i in range(28 if option=='F4' else 18):self.energy.append(self.energy_part('M_EnergyJet'))
        self.fronts=[self.energy_part('M_EnergyFront') for _ in range(6)]
        self.lances=[self.energy_part('M_LanceArrow') for _ in range(3)]
        for row in self.lances:
            row['mesh'].set_static_mesh(unreal.load_asset(HELPER['MESH_ROOT']+'/SM_FLongLance'))
            row['mid']=row['mesh'].create_dynamic_material_instance(0,unreal.load_asset(ROOT+'/M_LanceMetal'))
            row['mid'].set_scalar_parameter_value('Envelope',0.)
        self.impact_at=None
        self.arrival_at=None
        self.seen=set()
        self.q_center=rig['ground'](self.start.x+420.,self.start.y) if option=='Q2' else None
        self.metrics=[]

    def energy_part(self,name):
        row=self.plane('soft_dot',name)
        row['mid']=row['mesh'].create_dynamic_material_instance(0,unreal.load_asset(ROOT+'/'+('M_LanceMetal' if name=='M_LanceArrow' else name)))
        row['mid'].set_scalar_parameter_value('Envelope',0.)
        row['mid'].set_scalar_parameter_value('Index',self.serial*.71)
        return row

    def card(self,row,p,direction,length,width,power,age,normal=None):
        camera=unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](),0).get_camera_location()
        row['actor'].set_actor_location(p,False,True)
        row['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(direction,normal or camera-p),True)
        row['mesh'].set_world_scale3d(unreal.Vector(length/100.,width/100.,1.))
        row['mid'].set_scalar_parameter_value('Envelope',max(0.,power))
        row['mid'].set_scalar_parameter_value('Age',age)

    def lance(self,row,p,direction,length,width,power,age):
        self.card(row,p,direction,100.,100.,power,age,self.up)
        row['mesh'].set_world_scale3d(unreal.Vector(length/520.,width/84.,width/84.))

    def clear_energy(self):
        self.reset_draw()
        for row in self.energy+self.fronts+self.lances:row['mid'].set_scalar_parameter_value('Envelope',0.)

    def once(self,token,key,names,p,rotation,scale,lifetime,speed):
        if token in self.emitted:return
        self.emitted.add(token);self.pulse(key,names,p,rotation,scale,lifetime,speed)

    def update(self,age):
        self.clear_energy()
        key=self.option[0];pawn=self.rig['pawn']();f=pawn.get_actor_forward_vector()
        f=unreal.Vector(f.x,f.y,0.);right=unreal.Vector(-f.y,f.x,0.);up=self.up
        mesh=pawn.get_editor_property('mesh');anchor=mesh.get_socket_location('arrow_anchor')+up*6.
        arrows=[a for a in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowArrow)
                if valid(a) and a.get_owner()==pawn]
        if arrows and self.shot_at is None:self.shot_at=age
        shot=-1. if self.shot_at is None else age-self.shot_at
        if key=='Q':
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowAscendedShotFX):
                if actor.get_owner()==pawn and actor.actor_has_tag('SparrowAscendedRain'):actor.set_actor_hidden_in_game(True)
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowAscensionAccent):
                if actor.actor_has_tag('SparrowQGroundImpact'):actor.set_actor_hidden_in_game(True)
            center=self.q_center+up*12.;t=age-.66
            # A compact overhead ignition converges, then one tapered light mass falls.
            if t<0.:
                u=clamp(age/.60);c=center+up*(360.-u*60.)
                for i in range(10):
                    a=i*2.39996+age*1.3;r=(260.-u*220.)
                    p=c+right*math.cos(a)*r+f*math.sin(a)*r*.72
                    self.card(self.energy[i],p,c-p,120.,70.,u*.85,age)
                self.card(self.fronts[1],c,f,90.+u*50.,90.+u*50.,u,age)
            elif t<.18:
                u=clamp(t/.16);tip=center+up*(520.*(1.-u)**2)
                self.card(self.energy[15],tip+up*200.,-up,600.,170.,1.5,age)
                for i in range(4):self.card(self.energy[i],tip+up*(160.+i*110.),-up,340.,100.+i*14.,1.,age)
            if t>=.16:
                local=t-.16;fade=(1.-clamp(local/.42))**1.8
                self.once('Qimpact','impact',('Main Flames','Wisps','Sparks'),center,unreal.Rotator(),(1.8,1.8,1.0),.38,2.5)
                self.card(self.fronts[0],center+up*3.,f,170.+local*1800.,170.+local*1800.,fade,age,up)
                for i in range(8):
                    a=i*math.tau/8.;d=right*math.cos(a)+f*math.sin(a)
                    self.card(self.energy[i],center+d*(60.+local*520.)+up*20.,d,180.,65.,fade,age)
                self.card(self.fronts[1],center+up*50.,f,220.*fade,180.*fade,fade*1.5,age)
        elif key in ('S','D'):
            center=anchor+f*(66. if key=='S' else 18.)
            charge=clamp(age/(.32 if key=='S' else .23));release=(1.-clamp(shot/.14)) if shot>=0. else 1.
            count=6 if key=='S' else 4
            for i in range(count):
                a=i*math.tau/count+age*(1.8 if key=='S' else -.9)
                radial=right*math.cos(a)+up*math.sin(a)
                radius=(110. if key=='S' else 67.)*(1.-charge*.57)
                p=center+radial*radius-f*(1.-charge)*35.
                d=-radial*.75+f*.4
                self.card(self.energy[i],p,d,94.+charge*30.,72. if key=='S' else 56.,charge*.95*release,age)
            if shot<0.:
                self.card(self.fronts[0],center,f,72.-charge*30.,72.-charge*30.,charge*.55,age)
                for moment in ((.10,.24) if key=='S' else (.08,.17)):
                    if age>=moment:self.once('charge'+str(moment),'shards',('Flames2',),center,unreal.MathLibrary.make_rot_from_z(f),(.21,.21,.30),.15,2.1)
            else:
                power=(1.-clamp(shot/.18))**1.4
                for i in range(4):
                    d=f+right*(i-1.5)*.13+up*((i%2-.5)*.25)
                    self.card(self.energy[i+8],center+f*(40.+shot*550.),d,210. if key=='S' else 165.,84. if key=='S' else 61.,power,age)
                self.once('release','muzzle',('Wisps','Sparks','AirglowFlash'),center,unreal.MathLibrary.make_rot_from_x(f),(.70,.43,.43),.16,2.6)
        elif key=='F':
            # Hide this cast's old assembly only. Native projectiles still drive movement/hits.
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](),unreal.SparrowGatherShot):
                if actor.get_owner()==pawn:actor.set_actor_hidden_in_game(True)
            center=anchor+f*85.
            if shot<0.:
                charge=clamp(age/.92)
                for i,row in enumerate(self.energy[:22]):
                    u=(age*(.66+i%3*.05)+i/22.)%1.
                    a=i*2.39996+u*.72
                    radial=right*math.cos(a)+up*math.sin(a)
                    radius=(1.-u)**1.5*(95.+i%4*16.)
                    p=center+radial*radius-f*(1.-u)*(65.+i%3*22.)
                    d=center-p;d=d/max(d.length(),.001)
                    self.card(row,p,d,15.+(1.-u)*48.,10.+(1.-u)*13.,(math.sin(u*math.pi)**.6)*clamp(age/.15)*.75,age)
                self.card(self.fronts[0],center,f,72.-charge*30.,72.-charge*30.,charge*.60,age)
                # The arrow is one resolved form at the end; fragments are absorbed light.
                deploy=clamp((age-.78)/.16)
                self.lance(self.lances[0],anchor+f*118.,f,520.*deploy,84.,deploy,age)
            else:
                for i,arrow in enumerate(arrows[:3]):
                    d=arrow.get_velocity();d=d/max(d.length(),.001)
                    if d.length()<.1:d=f
                    # Native F6 static/particle visuals stay hidden on this preview instance.
                    for component in arrow.get_components_by_class(unreal.PrimitiveComponent):
                        component.set_visibility(False,True)
                    p=arrow.get_actor_location()
                    self.lance(self.lances[i],p-d*260.,d,520.,84.,1.,age)
                    self.card(self.energy[i],p-d*340.,d,220.,33.,.8,age)
                self.once('release','muzzle',('Wisps','Sparks','AirglowFlash'),anchor+f*50.,unreal.MathLibrary.make_rot_from_x(f),(.85,.40,.40),.16,2.6)
        elif key=='B':
            point=pawn.get_actor_location()
            if not self.arrived and (point-self.start).length()>10.:
                self.arrived=True;self.end=point;self.arrival_at=age
            for place,p in enumerate((self.start,self.end)):
                if place and not self.arrived:continue
                local=age-(self.arrival_at if place else 0.)
                fade=(1.-clamp(local/.18))**1.5
                p=p-up*24.
                self.once('burst'+str(place),'impact',('Main Flames','Wisps','Sparks'),p,unreal.Rotator(),(.54,.54,.67),.18,3.5)
                self.card(self.fronts[place],p,f,100.+local*420.,140.+local*240.,fade*1.5,age)
                for i in range(6):
                    a=i*math.tau/6.+.22
                    d=right*math.cos(a)+up*math.sin(a)
                    p2=p+d*(18.+local*240.)
                    self.card(self.energy[place*6+i],p2,d*(1. if place else -1.),80.,22.,fade,age)
        self.tick()

def sequence(rig):
    native=os.environ.get('SPARROW_ENERGY_NATIVE')=='1'
    selected=os.environ.get('SPARROW_ENERGY_CASES',','.join(DESIGNS)).split(',')
    report={'passed':False,'cases':[]};out=Path(rig['OUT']);frame=1./rig['FPS']
    rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
    try:
        for option in selected:
            key=option[0]
            modes=(os.environ.get('SPARROW_ENERGY_MODES','normal,form').split(',') if native else ['normal','form']) if key not in ('Q','B') and (native or key in ('E','A')) else ['form'] if key in ('Q','B') else ['normal']
            for mode in modes:
                rig['switch']('countess');yield .15
                rig['switch']('sparrow');yield .6
                targets=rig['layout']([(600,0),(800,-350),(900,500)] if option in ('A4','A5') else [(700,350),(800,-350),(900,500)] if key in ('A','B','F') else [(700,0),(700,350),(900,500)])
                yield .2
                if mode=='form':rig['use']('V',offset=(950,0));yield 2.1
                rig['aim'](offset=(420 if key=='Q' else 950,0))
                ident=option+'_'+mode;rig['case'](ident)
                start=unreal.GameplayStatics.get_time_seconds(rig['world']())
                before=rig['pawn']().get_actor_location()
                study=None if native or key in ('E','A') else Study(rig,option)
                rig['STATE']['video_clip']={'case':ident,'prefix':ident+'_video','cast_time':start,'frame_times':[]}
                rig['key']('SpaceBar' if key=='B' else key)
                duration=2.6 if key=='A' else (4.1 if native else 2.3) if key=='Q' else 1.6 if key=='F' else .7 if key=='B' else 1.2
                moments=[.067,.10,.16,.25,.32,.40,.55,.80,.93,1.03,1.10,1.23,1.5]
                saw_busy=False;arrows=set();samples=[];saw_harmony_s=False
                try:
                    while True:
                        age=unreal.GameplayStatics.get_time_seconds(rig['world']())-start
                        if age>duration:break
                        saw_busy|=rig['pawn']().is_combat_busy()
                        if study:study.update(age)
                        for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowArrow):
                            if a.get_owner()==rig['pawn']():arrows.add(a.get_name())
                        if option=='S6':
                            saw_harmony_s |= any(a.actor_has_tag('SparrowHarmony_S') for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowHarmonyFX))
                        if key=='E':
                            for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowEDesignVisual):
                                if a.get_owner()!=rig['pawn']():continue
                                parts=[]
                                for c in a.get_components_by_class(unreal.StaticMeshComponent):
                                    if c.component_has_tag('ERegaliaSeal'):
                                        material=c.get_material(0)
                                        parts.append({'name':c.get_name(),'envelope':material.get_scalar_parameter_value('Envelope')})
                                if parts:samples.append({'age':age,'arrow_count':len(arrows),'seal':parts})
                        if moments and age>=moments[0]:rig['capture'](ident+'_t'+str(round(moments.pop(0)*1000)).zfill(4))
                        yield frame
                    rig['finish_video_clip']()
                    rig['check'](saw_busy,ident+' actual input cast')
                    rig['check'](not rig['pawn']().is_combat_busy(),ident+' native control recovered')
                    if key=='E':
                        rig['check'](len(arrows)==1,ident+' single real arrow')
                        rig['check'](any(s['arrow_count']==0 and s['seal'][0]['envelope']>.1 for s in samples),ident+' seal before shot')
                        rig['check'](any(s['arrow_count']>0 and s['seal'][0]['envelope']<.01 for s in samples),ident+' seal removed after shot')
                    if key=='A':
                        gears=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow)
                        rig['check'](len(gears)==1 and abs(gears[0].get_flight_speed()-160.)<.01,ident+' retains160cm/s')
                    if option in ('A4','A5'):
                        rig['check'](len(arrows)==1 and gears[0].actor_has_tag('SparrowPairedA'),ident+' two visuals share original single projectile')
                        parts=[c for c in gears[0].get_components_by_class(unreal.SceneComponent) if c.get_name() in ('ArrowMesh','ArrowTrail','SawRotor','CondensedCore')]
                        offsets=[float(c.get_editor_property('relative_location').y) for c in parts]
                        rig['check'](len(parts)==4 and all(abs(y+80.)<.01 for y in offsets),ident+' legacy visuals occupy left lane')
                        fx=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowHarmonyFX) if a.actor_has_tag('SparrowHarmony_A')]
                        rig['check'](len(fx)==1,ident+' new arrow presentation follows same projectile')
                        samples.append({'legacy_offsets_y':offsets,'center_spacing_cm':160.})
                        if option=='A5':
                            rings=[c for c in gears[0].get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith('FeatherRing')]
                            surfaces=[c.get_material(0).get_editor_property('parent').get_path_name() for c in rings]
                            scales=[c.get_editor_property('relative_scale3d') for c in rings]
                            rig['check'](len(rings)==2 and all('M_SparrowGearFeather.' in m for m in surfaces) and all(abs(s.x-s.y)<.001 for s in scales),ident+' history53 original round feather rings restored')
                            shards=[a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowAscensionAccent) if a.get_owner()==rig['pawn']() and a.actor_has_tag('SparrowLegacySpiralA4Accent')]
                            right=gears[0].get_actor_right_vector();center=gears[0].get_actor_location()
                            lanes=[]
                            for shard in shards:
                                d=shard.get_actor_location()-center
                                lanes.append(d.x*right.x+d.y*right.y+d.z*right.z)
                            rig['check'](len(lanes)>=2 and all(-106.<y<-54. for y in lanes),ident+' history53 compact spiral particles follow left arrow')
                            samples.append({'ring_surfaces':surfaces,'spiral_lane_offsets':lanes})
                        yield 2.2
                        rig['check'](abs(rig['health'](targets[0])-10.)<.01 and rig['health'](targets[1])==100.,ident+' original90damage once and lateral exclusion')
                    if option=='S6':
                        rig['check'](len(arrows)==15 and not saw_harmony_s,ident+' original15arrows and no rejected Harmony S')
                    if key=='B':rig['check']((native or study.arrived) and abs((rig['pawn']().get_actor_location()-before).length()-480.)<3.,ident+' actual480cm blink')
                    if native:
                        move_start=rig['pawn']().get_actor_location();move_goal=rig['ground'](move_start.x+230.,move_start.y+140.)
                        rig['cmd'](f'CountessComboQA.Mouse Move Right {move_goal.x} {move_goal.y} {move_goal.z}')
                        rig['cmd'](f'CountessComboQA.Mouse Press Right {move_goal.x} {move_goal.y} {move_goal.z}')
                        yield .24
                        rig['cmd'](f'CountessComboQA.Mouse Release Right {move_goal.x} {move_goal.y} {move_goal.z}')
                        rig['check']((rig['pawn']().get_actor_location()-move_start).length()>25.,ident+' actual mouse movement after cast')
                    report['cases'].append({'id':ident,'label':DESIGNS[option][0],'description':DESIGNS[option][1],
                        'duration':duration,'arrows':len(arrows),'installed':native or key in ('E','A'),'visual_only':not native and key not in ('E','A'),'samples':samples})
                finally:
                    rig['finish_video_clip']()
                    if study:study.close()
                (out/'polish-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                if key=='Q':yield 3.
        if native and any(option.startswith('F') for option in selected):
            rig['switch']('sparrow');yield .4
            rig['aim'](offset=(950,0));rig['key']('F');yield .10
            rig['switch']('countess');yield .16
            remaining=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowHarmonyFX)
            rig['check'](not remaining,'F pre-shot cancellation and character switch clean owned presentation')
        if any(option in ('A4','A5','S6') for option in selected):
            rig['switch']('countess');yield .16
            remaining=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowHarmonyFX)
            rig['check'](not remaining,'A/S owner switch removes remaining visual actors')
        report['passed']=True
    finally:(out/'polish-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
