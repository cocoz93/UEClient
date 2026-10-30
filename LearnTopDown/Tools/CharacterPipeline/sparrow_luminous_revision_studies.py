"""Twelve transient actual-PIE studies; production code/assets stay untouched.

W/V/A use native input. W preserves native damage/impact; A has an empty lane.
D alternatives are visual installation prototypes (no AI, damage or binding).
SPARROW_LUMINOUS_OPTIONS=W1,W2,W3,V1,V2,V3,A14,A15,A16,D1,D2,D3.
The parent owns all GPU execution. author(out) is a read-only inventory.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
_PART = _BASE['_PART']
BaseStudy, valid = _BASE['Study'], _BASE['_valid']
clamp, smooth = _BASE['_clamp'], _BASE['_smooth']
ROOT = '/Game/TopDown/Characters/Sparrow'
GOLD = ROOT + '/Materials/M_SparrowAscensionGold'
ARROW = '/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow'
HAWK_ROOT = '/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_'
MESHES = {key: '/Engine/BasicShapes/'+key.title() for key in ('cube','cylinder','cone')}
MESHES.update({'arrow': ARROW, **{'hawk_'+part.lower(): HAWK_ROOT+part for part in ('Body','WingR','WingL','Tail')}})
DESIGNS = {
    'W1': {'label': '백금 직선잔광', 'shape': '기존 가는 금속 화살에 짧고 곧은 백금 잔광 한 줄.', 'scope': '실제 W 비행만 비교; 착탄 유지'},
    'W2': {'label': '미세 광침', 'shape': '화살 주변에 길이가 다른 작고 밀집한 빛의 침; 불규칙 화염 없음.', 'scope': '실제 W 비행만 비교; 착탄 유지'},
    'W3': {'label': '깨진 후광', 'shape': '작은 분절 고리 두 개와 가는 중심선; 넓은 화염 아지랑이 없음.', 'scope': '실제 W 비행만 비교; 착탄 유지'},
    'V1': {'label': '가는 화염결', 'shape': '현 날개 실루엣 안의 촘촘한 화염결과 양끝의 짧은 점화.', 'scope': '실제 V 크기 .8 / 입장 1.75배 유지'},
    'V2': {'label': '굵은 화염맥', 'shape': '넓게 흐르는 금색 화염 무늬와 뿌리에서 끝으로 전달되는 불티.', 'scope': '실제 V 크기 .8 / 입장 1.75배 유지'},
    'V3': {'label': '분절 불꽃 가장자리', 'shape': '촘촘하게 끊기는 화염 무늬와 가장자리에만 찍히는 작은 파열.', 'scope': '실제 V 크기 .8 / 입장 1.75배 유지'},
    'A14': {'label': '세공 분절환', 'shape': 'A10의 이중 궤도에 조각난 세공 눈금과 느린 역회전.', 'scope': '기존 A 중심 회전/파열 유지'},
    'A15': {'label': '위상 교차환', 'shape': '서로 다른 경사로 교차하는 두 궤도; 앞뒤 위상 변화가 읽히는 구성.', 'scope': '기존 A 중심 회전/파열 유지'},
    'A16': {'label': '응축 파열환', 'shape': '중심에 가까운 좁은 이중 궤도와 바깥 가장자리의 짧은 파열.', 'scope': '기존 A 중심 회전/파열 유지'},
    'D1': {'label': '황금 매', 'shape': '실제 보유 결정 매 4부위 메시를 황금색으로 조립; 날갯짓하며 세 번 사격 후 소멸.', 'scope': '시각 설치기 시안; 피해/AI/키 연결 없음'},
    'D2': {'label': '황금 자동쇠뇌', 'shape': '삼각 받침·가로 활대·시위·장전 화살이 있는 고정 쇠뇌 두 대.', 'scope': '기본 3D 메시 조립 시안; 피해/AI/키 연결 없음'},
    'D3': {'label': '공중 수정포대', 'shape': '뾰족한 황금 결정과 공전환이 공중에 고정되어 백금 광탄을 발사.', 'scope': '기본 3D 메시 조립 시안; 피해/AI/키 연결 없음'},
}
OPTIONS = tuple(DESIGNS)


def write(out, name, data):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    paths={**_BASE['MATERIALS'], **_PART['SOURCES'], **MESHES, 'gold':GOLD,
           'wing_membrane':ROOT+'/Materials/M_SparrowSerathGoldFlame',
           'wing_splines':ROOT+'/Materials/M_SparrowSerathSplineFlame'}
    rows=[]
    for key,path in paths.items():
        asset=unreal.load_asset(path)
        assert asset, path
        row={'key':key,'path':asset.get_path_name(),'class':asset.get_class().get_name()}
        if key.startswith('wing_'):
            vectors=[str(v) for v in unreal.MaterialEditingLibrary.get_vector_parameter_names(asset)]
            assert {'WingRootPosition','WingSideAxis','WingBackAxis'}.issubset(vectors), (key,vectors)
            row['vectors']=vectors
        rows.append(row)
    result={'sources':rows,'designs':DESIGNS,'assets_saved':False,'production_changed':False,
            'wing_texture_note':'Current custom fire color is fixed; previews vary its actual root-relative sampling axes, not disconnected legacy color parameters.',
            'hawk_evidence':'aurora_bird_art.py and AuroraSkillComponentFDrafts.cpp: +X beak, shoulder (6,+/-12,3), tail (-26,0,0).'}
    write(out,'luminous-revision-sources.json',result)
    return result


def rotation(direction):
    return unreal.MathLibrary.make_rot_from_x(direction)


class Study(BaseStudy):
    def __init__(self, rig, option, targets):
        super().__init__(rig,option)
        self.targets=targets
        self.materials['gold']=unreal.load_asset(GOLD)
        self.meshes={key:unreal.load_asset(path) for key,path in MESHES.items()}
        self.hidden, self.w_arrows, self.sentries, self.shots = [], [], [], []
        self.hidden_paths=set()
        self.w_materials=[]
        self.seen, self.impact_seen, self.shot_log = set(), False, []
        self.form, self.wing, self.wing_birth = None, None, None
        self.wing_slots, self.wing_bones, self.wing_samples = [], [], []
        self.boundaries=[]

    def prop(self, key, label):
        row=self.plane('gold',label)
        row['mesh'].set_static_mesh(self.meshes[key])
        row['mesh'].set_visibility(False)
        return row

    def pose(self,row,point,scale,rot):
        row['actor'].set_actor_location_and_rotation(point,rot,False,True)
        row['mesh'].set_world_scale3d(unreal.Vector(*scale))
        row['mesh'].set_visibility(max(scale)>.001)

    def rod(self,row,a,b,radius,grow=1.):
        delta=b-a
        self.pose(row,(a+b)*.5,(radius/50.*grow,radius/50.*grow,delta.length()/100.*grow),
                  unreal.MathLibrary.make_rot_from_z(delta))

    def hide(self,component):
        if component.get_path_name() in self.hidden_paths:
            return
        self.hidden_paths.add(component.get_path_name())
        self.hidden.append((component,component.is_visible()))
        component.set_visibility(False)

    def observe_w(self,arrow):
        path=arrow.get_path_name()
        if path in self.seen:
            return
        self.seen.add(path)
        names=[str(n) for n in arrow.get_target_impact_emitter_names()]
        assert set(names)=={'Main Flames','Wisps','Flare','Sparks','SparkTrailHeads','Line Burst'},names
        flight=[]
        for component in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            flight.append(component.get_name())
            self.hide(component)
        shaft=next(c for c in arrow.get_components_by_class(unreal.StaticMeshComponent) if c.get_name()=='ArrowMesh')
        scale=shaft.get_editor_property('relative_scale3d')
        assert abs(scale.x-1.1)<.01 and abs(scale.y-1.1)<.01 and abs(scale.z-1.)<.01
        # The source arrow mesh has a default grid slot. The flight study uses
        # the project's actual gold metal surface, without altering its width.
        self.w_materials.append((shaft,[shaft.get_material(i) for i in range(shaft.get_num_materials())]))
        for slot in range(shaft.get_num_materials()):
            shaft.set_material(slot,self.materials['gold'])
        parts=[self.plane('soft_line','w_axis')]
        if self.option=='W2':
            parts.extend(self.plane('soft_line','w_needle_'+str(i)) for i in range(9))
        elif self.option=='W3':
            parts.extend((self.plane('fine','w_split_ring'),self.plane('fracture','w_broken_ring')))
        self.w_arrows.append({'actor':arrow,'parts':parts,'born':self.now()})
        self.events.append({'event':'native_W','time':self.now()-self.born,'hidden_flight_components':flight,
                            'impact_emitters_unchanged':names,'speed':arrow.get_flight_speed()})

    def update_w(self,t):
        for item in self.w_arrows:
            arrow,parts=item['actor'],item['parts']
            if not valid(arrow):
                for row in parts:
                    if valid(row['actor']):
                        row['actor'].destroy_actor()
                continue
            p,f=arrow.get_actor_location(),arrow.get_flight_direction()
            self.soft_line(parts[0],p-f*78.,p+f*42.,9.,2.0)
            if self.option=='W2':
                for i,row in enumerate(parts[1:]):
                    angle=i*2.39996
                    radial=self.right*(math.cos(angle)*(5.+i%3*3.))+self.up*(math.sin(angle)*(5.+i%3*3.))
                    offset=f*(-18.-i*6.)+radial
                    self.soft_line(row,p+offset-f*(13.+i%4*7.),p+offset,4.5,1.5)
            elif self.option=='W3':
                age=self.now()-item['born']
                self.place(parts[1],p-f*8.,(.62,.62,1.),f,age*500.,.62)
                self.place(parts[2],p-f*35.,(.48,.48,1.),f,-age*620.,.42)
        for component in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not valid(component):
                continue
            tags={str(tag) for tag in component.get_editor_property('component_tags')}
            if 'SparrowPiercingImpact' in tags:
                self.impact_seen=True
            # The rejected haze also exists in three separate release effects,
            # outside the arrow actor. Suppress only those in this W study;
            # native piercing muzzle glow and the six-layer impact stay visible.
            if tags.intersection({'SparrowReleasePressure','SparrowReleaseShards','SparrowPiercingReleaseFeathers'}):
                self.hide(component)

    def observe_a(self,arrow):
        if self.arrow_actor is not None:
            return
        self.arrow_actor=arrow
        self.seen.add(arrow.get_path_name())
        for component in arrow.get_components_by_class(unreal.StaticMeshComponent):
            self.native_snapshot.append((component,tuple(component.get_material(i) for i in range(component.get_num_materials()))))
        self.orbits=[self.plane('glyph' if self.option=='A14' else 'fine','orbit_0'),self.plane('fine','orbit_1')]
        if self.option=='A16':
            self.orbits.append(self.plane('fracture','edge_fracture'))

    def update_a(self,t):
        if not valid(self.arrow_actor):
            return
        p=self.arrow_actor.get_actor_location()+self.forward*40.
        fade=clamp((3.35-t)/.35)
        if self.option=='A14':
            self.place(self.orbits[0],p,(2.52,2.52,1.),self.forward,-t*95.,.56*fade)
            self.place(self.orbits[1],p-self.forward*19.,(2.92,2.60,1.),self.forward+self.up*.22,t*145.+35.,.28*fade)
        elif self.option=='A15':
            tilt=.60+.12*math.sin(t*3.)
            self.place(self.orbits[0],p,(2.65,2.65,1.),self.forward+self.right*tilt+self.up*.36,-t*210.,.47*fade)
            self.place(self.orbits[1],p-self.forward*13.,(2.65,2.65,1.),self.forward-self.right*tilt-self.up*.36,t*210.+90.,.47*fade)
        else:
            self.place(self.orbits[0],p,(2.10,2.10,1.),self.forward,-t*240.,.59*fade)
            self.place(self.orbits[1],p-self.forward*12.,(2.32,2.32,1.),self.forward+self.up*.15,t*190.,.30*fade)
            self.place(self.orbits[2],p,(2.40,2.40,1.),self.forward,-t*340.,(.19+.11*abs(math.sin(t*18.)))*fade)
        if t<3.1 and self.now()-self.last_pulse>.22:
            self.last_pulse=self.now()
            theta=t*6.
            radial=self.right*math.cos(theta)+self.up*math.sin(theta)
            key,names=('impact',('Sparks','SparkTrailHeads')) if self.option=='A16' else ('muzzle',('Sparks',))
            self.pulse(key,names,p+radial*(67. if self.option=='A16' else 82.),rotation(radial),
                       (.36,.36,.36),.28,1.8)

    def observe_v(self,form):
        self.form,self.wing_birth=form,self.now()
        self.wing=next(c for c in form.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name()=='SerathWings')
        self.wing_bones=[self.wing.get_bone_name(i) for i in range(self.wing.get_num_bones())
                         if 'wing' in str(self.wing.get_bone_name(i)).lower()]
        for name in ('M12_WingSplines','M13_WingMembrane'):
            slot=self.wing.get_material_index(name)
            original=self.wing.get_material(slot)
            assert slot>=0 and isinstance(original,unreal.MaterialInstanceDynamic)
            mid=unreal.MaterialLibrary.create_dynamic_material_instance(self.rig['world'](),original.get_base_material())
            assert mid
            mid.copy_material_instance_parameters(original,True)
            self.wing.set_material(slot,mid)
            self.wing_slots.append((slot,original,mid))
        self.events.append({'event':'native_V','wing':self.wing.get_skeletal_mesh_asset().get_path_name(),
                            'scale':self.rig['vec'](self.wing.get_world_scale())})

    def wing_point(self,side,reach):
        root=self.rig['pawn']().get_editor_property('mesh').get_socket_location('spine_03')
        right=self.rig['pawn']().get_actor_right_vector()
        candidates=[self.wing.get_socket_location(b) for b in self.wing_bones]
        endpoint=max(candidates,key=lambda p:((p-root).x*right.x+(p-root).y*right.y)*side)
        return root+(endpoint-root)*reach

    def update_v(self,t):
        if not valid(self.form):
            return
        age=self.now()-self.wing_birth
        side_scale,back_scale={'V1':(1.55,.85),'V2':(.63,1.15),'V3':(2.0,1.45)}[self.option]
        # The native shader hardcodes fire color. Change its real sampling field
        # on a transient MID, while copying native root/envelope every frame.
        for slot,original,mid in self.wing_slots:
            for name in ('WingAlpha',):
                mid.set_scalar_parameter_value(name,original.get_scalar_parameter_value(name))
            root=original.get_vector_parameter_value('WingRootPosition')
            mid.set_vector_parameter_value('WingRootPosition',root)
            for name,factor in (('WingSideAxis',side_scale),('WingBackAxis',back_scale)):
                value=original.get_vector_parameter_value(name)
                mid.set_vector_parameter_value(name,unreal.LinearColor(value.r*factor,value.g*factor,value.b*factor,value.a))
        if .16<age<1.12 and self.now()-self.last_pulse>.16:
            self.last_pulse=self.now()
            reach={'V1':1.0,'V2':min(1.,.22+age*.85),'V3':.74+.24*abs(math.sin(age*15.))}[self.option]
            for side in (-1,1):
                p=self.wing_point(side,reach)
                if self.option=='V2':
                    self.pulse('shards',('Flames2',),p,unreal.MathLibrary.make_rot_from_z(self.up),(.28,.24,.35),.23,2.2)
                else:
                    self.pulse('impact',('Sparks','SparkTrailHeads'),p,unreal.Rotator(),
                               (.34,.34,.34) if self.option=='V1' else (.46,.38,.38),.25,2.)
        if len(self.wing_samples)<4 and age>(len(self.wing_samples)+1)*.35:
            self.wing_samples.append({'age':age,'scale':self.rig['vec'](self.wing.get_world_scale()),
                                      'side_field_scale':side_scale,'back_field_scale':back_scale})

    def setup_d(self):
        player=self.rig['pawn']().get_actor_location()
        for index,side in enumerate((-1.,1.)):
            base=player+self.forward*40.+self.right*(side*180.)
            base.z=player.z-88.
            anchor=base+self.up*(175. if self.option=='D1' else 132. if self.option=='D3' else 0.)
            target=self.targets[index].get_actor_location()
            direction=(target-anchor).normal()
            # Keep each installation level; its visual projectile aims at target height.
            flat=unreal.Vector(direction.x,direction.y,0.).normal()
            right=unreal.Vector(-flat.y,flat.x,0.)
            item={'anchor':anchor,'forward':flat,'right':right,'target':target,'parts':[],
                  'index':index,'next_shot':.78+index*.07,'shots':0,'last_shot':-10.,
                  'ring':self.plane('fine','summon_ring_'+str(index))}
            if self.option=='D1':
                item['parts']=[self.prop('hawk_'+part,'hawk_'+part) for part in ('body','wingr','wingl','tail')]
                item['eye']=self.plane('soft_dot','hawk_glow')
            elif self.option=='D2':
                item['parts']=[self.prop('cube','crossbow_stock')]
                item['arms']=[self.prop('cylinder','crossbow_arm_'+str(i)) for i in range(4)]
                item['legs']=[self.prop('cylinder','crossbow_leg_'+str(i)) for i in range(3)]
                item['strings']=[self.plane('soft_line','crossbow_string_'+str(i)) for i in range(2)]
                item['loaded']=self.prop('arrow','loaded_arrow')
            else:
                item['parts']=[self.prop('cone','crystal_upper'),self.prop('cone','crystal_lower')]
                item['core']=self.plane('soft_dot','crystal_core')
                item['orbits']=[self.plane('glyph','crystal_orbit'),self.plane('fine','crystal_orbit_2')]
            self.sentries.append(item)
            self.pulse('impact',('Sparks','SparkTrailHeads'),anchor+self.up*(85. if self.option=='D2' else 0.),
                       unreal.Rotator(),(.70,.70,.70),.45,1.6)

    def fire_prop(self,item,point):
        target=item['target']
        delta=target-point
        direction=delta.normal()
        duration=delta.length()/1250.
        shot={'born':self.now(),'origin':point,'target':target,'direction':direction,'duration':duration,
              'body':self.prop('arrow','display_arrow') if self.option!='D3' else self.plane('soft_dot','crystal_bolt'),
              'trail':self.plane('soft_line','installation_trail'),'done':False}
        self.shots.append(shot)
        item['last_shot']=self.now()-self.born
        item['shots']+=1
        self.shot_log.append({'installation':item['index'],'time':self.now()-self.born,'visual_only':True})
        self.pulse('muzzle',('Sparks',),point,rotation(direction),(.52,.38,.38),.19,1.9)

    def update_d(self,t):
        grow=smooth(t/.40)*(1.-smooth((t-3.0)/.50))
        for item in self.sentries:
            p,f,r=item['anchor'],item['forward'],item['right']
            recoil=max(0.,1.-(t-item['last_shot'])/.15)*10.
            if self.option=='D1':
                center=p+self.up*(math.sin(t*8.+item['index'])*6.)-f*recoil
                size=.95*grow
                self.pose(item['parts'][0],center,(size,)*3,rotation(f))
                for i,side in ((1,1.),(2,-1.)):
                    flap=(10.+32.*math.sin(t*2.*math.pi*3.1+item['index']))*side
                    rot=unreal.MathLibrary.compose_rotators(unreal.Rotator(roll=flap),rotation(f))
                    self.pose(item['parts'][i],center+(f*6.+r*(side*12.)+self.up*3.)*size,(size,)*3,rot)
                self.pose(item['parts'][3],center-f*26.*size,(size,)*3,rotation(f))
                self.soft_dot(item['eye'],center+f*39.+self.up*7.,22.,grow*2.)
                muzzle=center+f*60.
            elif self.option=='D2':
                center=p+self.up*92.-f*recoil
                self.pose(item['parts'][0],center,(1.30*grow,.16*grow,.14*grow),rotation(f))
                for leg,row in enumerate(item['legs']):
                    angle=leg*math.pi*2./3.
                    foot=p+f*(math.cos(angle)*40.)+r*(math.sin(angle)*40.)
                    self.rod(row,foot,center-f*16.,5.,grow)
                for i,(side,a,b) in enumerate(((-1.,0.,.55),(-1.,.55,1.),(1.,0.,.55),(1.,.55,1.))):
                    def arm(u):
                        return center+f*(30.-28.*u*u)+r*(side*85.*u)
                    self.rod(item['arms'][i],arm(a),arm(b),4.,grow)
                for side,row in zip((-1.,1.),item['strings']):
                    self.soft_line(row,center+f*2.+r*(side*85.),center-f*35.,3.,grow*1.15)
                self.pose(item['loaded'],center+f*20.,(.43*grow,.43*grow,.64*grow),
                          unreal.MathLibrary.make_rot_from_z(f*-1.))
                muzzle=center+f*80.
            else:
                center=p+self.up*(math.sin(t*3.+item['index'])*6.)-f*recoil
                yaw=t*45.+item['index']*50.
                self.pose(item['parts'][0],center+self.up*24.,(.60*grow,.60*grow,.80*grow),unreal.Rotator(yaw=yaw))
                self.pose(item['parts'][1],center-self.up*24.,(.60*grow,.60*grow,.80*grow),unreal.Rotator(pitch=180.,yaw=yaw))
                self.soft_dot(item['core'],center,68.,grow*2.1)
                self.place(item['orbits'][0],center,(2.0,2.0,1.),self.up,t*150.,grow*.48)
                self.place(item['orbits'][1],center,(1.85,1.85,1.),f+self.up*.3,-t*110.,grow*.34)
                muzzle=center+f*36.
            item['muzzle']=muzzle
            # The display is explicitly time-driven; it is not target-seeking AI.
            if t>=item['next_shot'] and item['shots']<3:
                self.fire_prop(item,muzzle)
                item['next_shot']+=.72
            self.place(item['ring'],p+self.up*(25. if self.option=='D2' else -25.),(2.30,2.30,1.),
                       self.up,-t*110.,(.40 if t<.55 or t>3.0 else .10)*grow)
            if t>=3.02 and self.once('d_exit_'+str(item['index'])):
                self.pulse('impact',('Sparks','SparkTrailHeads'),muzzle,unreal.Rotator(),(.68,.68,.68),.42,1.7)
        for shot in self.shots:
            if shot['done']:
                continue
            progress=clamp((self.now()-shot['born'])/shot['duration'])
            p=shot['origin']+(shot['target']-shot['origin'])*progress
            if self.option=='D3':
                self.soft_dot(shot['body'],p,31.,3.3)
            else:
                self.pose(shot['body'],p,(.47,.47,.68),unreal.MathLibrary.make_rot_from_z(shot['direction']*-1.))
            self.soft_line(shot['trail'],p-shot['direction']*46.,p,8.,1.65)
            if progress>=1.:
                self.pulse('impact',('Sparks','SparkTrailHeads'),shot['target'],rotation(shot['direction']),(.48,.48,.48),.28,1.9)
                for key in ('body','trail'):
                    if valid(shot[key]['actor']):
                        shot[key]['actor'].destroy_actor()
                shot['done']=True

    def update(self,t):
        if self.option.startswith('W'):
            self.update_w(t)
        elif self.option.startswith('V'):
            self.update_v(t)
        elif self.option.startswith('A'):
            self.update_a(t)
        else:
            self.update_d(t)
        self.tick()
        if t>=self.next_sample:
            self.next_sample+=.20
            active=[p for p,_ in self.effects if valid(p) and p.is_active()]
            self.particle_samples.append({'time':t,'active':len(active),
                                         'particles':sum(p.get_num_active_particles() for p in active)})

    def close(self):
        for component,visible in self.hidden:
            if valid(component):
                component.set_visibility(visible)
        for slot,original,mid in self.wing_slots:
            if valid(self.wing):
                self.wing.set_material(slot,original)
        for component,materials in self.w_materials:
            if valid(component):
                for slot,original in enumerate(materials):
                    component.set_material(slot,original)
        return super().close()


def sequence(rig):
    options=[o.strip().upper() for o in os.environ.get('SPARROW_LUMINOUS_OPTIONS',','.join(OPTIONS)).split(',') if o.strip()]
    assert options and all(o in OPTIONS for o in options),options
    inventory=author(rig['OUT'])
    rows=[]
    checked_types=set()
    now=lambda:unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in options:
        rig['switch']('countess'); yield .15
        rig['switch']('sparrow'); yield .55
        prefix='luminous_'+option
        rig['case'](prefix)
        offsets=[(450,430),(650,-430),(650,430)] if option.startswith('A') else (
            [(620,-160),(620,160),(650,380)] if option.startswith('D') else [(650,0),(450,430),(650,-430)])
        targets=rig['layout'](offsets)
        yield .20
        health=[rig['health'](d) for d in targets]
        study=Study(rig,option,targets)
        started=now()
        moments=([.68,.80,.96,2.38] if option.startswith('W') else [.55,1.10,1.80,3.35])
        evidence=[]
        repeated_w=False
        try:
            if option.startswith('D'):
                study.setup_d()
            else:
                rig['use'](option[0],offset=(550,0)) if option.startswith('A') else rig['use'](option[0],targets[0])
            if os.environ.get('NEW_SKILLS_VIDEO','1')=='1':
                rig['STATE']['video_clip']={'case':prefix,'prefix':prefix+'_video','cast_time':started,'frame_times':[]}
            while now()-started<3.8:
                t=now()-started
                if option.startswith('W'):
                    for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowArrow):
                        if arrow.get_owner()==rig['pawn']() and arrow.actor_has_tag('SparrowChargedArrow'):
                            study.observe_w(arrow)
                    if t>=1.6 and not repeated_w:
                        rig['use']('W',targets[0]); repeated_w=True
                elif option.startswith('A'):
                    for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow):
                        if arrow.get_owner()==rig['pawn']():
                            study.observe_a(arrow)
                elif option.startswith('V') and study.form is None:
                    forms=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowAscensionWings)
                    if forms:
                        assert len(forms)==1
                        study.observe_v(forms[0])
                study.update(t)
                category=option[0]
                if category not in checked_types and .85<t<2.6:
                    if category=='W' or any(valid(p) and p.is_active() and p.get_num_active_particles()>0 for p,_ in study.effects):
                        token=prefix+'_live_psc'
                        rig['cmd']('SparrowQA.State '+token)
                        data=json.loads((Path(rig['OUT'])/(token+'.json')).read_text(encoding='utf-8-sig'))
                        live=[p for p in data['effects'] if p['active'] and p['particles']>0
                              and (('SparrowChargedImpactRuntime' in p['template']) if category=='W'
                                   else p['template'].split('.')[0] in _PART['SOURCES'].values())
                              and any(e['renders_surface'] and e['particles']>0 for e in p['render_emitters'])]
                        if live:
                            checked_types.add(category); evidence.append({'state':token+'.json','live_surface_PSCs':len(live)})
                if moments and t>=moments[0]:
                    rig['capture'](prefix+'_at_'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage=[before-rig['health'](d) for before,d in zip(health,targets)]
            if option.startswith('W'):
                rig['check'](len(study.seen)==2 and study.impact_seen,option+' shows two real W flights and unchanged native impacts')
                rig['check'](abs(damage[0]-70.)<.03 and abs(damage[1])+abs(damage[2])<.03,option+' preserves two native 35 damage hits')
            else:
                rig['check'](all(abs(d)<.001 for d in damage),option+' adds no gameplay damage')
                rig['check'](study.peak_particles>0,option+' has live original surface particles')
            if option.startswith('A'):
                rig['check'](len(study.seen)==1 and valid(study.arrow_actor),option+' preserves one native A')
                rig['check'](abs(study.arrow_actor.get_flight_speed()-160.)<.01 and study.arrow_actor.get_hit_count()==0,
                             option+' preserves speed and avoids target/passive contact')
            elif option.startswith('V'):
                rig['check'](valid(study.form) and len(study.wing_slots)==2,option+' uses the two native Serath wing sections')
                rig['check'](len(study.wing_samples)==4 and all(abs(sample['scale'][0]-.8)<.01 for sample in study.wing_samples),option+' preserves .8 wing scale')
            elif option.startswith('D'):
                rig['check'](len(study.sentries)==2 and all(s['shots']==3 for s in study.sentries),option+' summons two visual installations with three shots each')
                rig['check'](all(s['done'] for s in study.shots),option+' completes visual arrivals before disappearance')
            row={'id':option,**DESIGNS[option],'video_prefix':prefix+'_video','duration':3.8,
                 'installed':False,'native_damage':damage,'events':study.events,'shots':study.shot_log,
                 'particle_samples':study.particle_samples,'peak_particles':study.peak_particles,
                 'native_console_evidence':evidence,'wing_samples':study.wing_samples}
        finally:
            rig['finish_video_clip']()
            failures=study.close()
        rig['check'](not failures and not study.effects,option+' restores native visuals and destroys temporary effects')
        rows.append(row)
        write(rig['OUT'],'luminous-revision-studies.json',{'passed':len(rows)==len(options),'studies':rows,
              'sources':inventory['sources'],'assets_saved':False,'production_changed':False,
              'visual_review':'pending actual quarter-view review','D_gameplay_AI_damage_implemented':False})
        rig['switch']('countess'); yield .25
    rig['check'](set(o[0] for o in options).issubset(checked_types),'each requested category has native live surface-particle evidence')
