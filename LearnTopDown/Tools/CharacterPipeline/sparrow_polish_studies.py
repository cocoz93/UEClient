"""Feedback-led visual overlays on current Sparrow skills, using the existing PIE rig.

Only W/A's separately reviewed native presentation is installed. Other designs
are transient comparisons: no saved assets, gameplay overrides, or key bindings.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal

BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
BaseStudy, valid, clamp = BASE['Study'], BASE['_valid'], BASE['_clamp']
TAG = unreal.Name('SparrowPolish20261028')
DESIGNS = {
    'Q1': ('일제 낙광', '가는 빛줄기 28개가 같은 순간 지면을 찍고 짧은 접촉광만 남음'),
    'E1': ('중앙 겹깃 문장', '기존 깃활의 중앙에 작은 겹깃과 마름모 광핵을 연결'),
    'E2': ('이중 깃맥', '중앙에서 양쪽 활 몸체로 두 겹의 금빛 광맥이 흐름'),
    'E3': ('불사조 심장', '중앙의 짧은 화염깃과 비대칭 불꽃결이 시위 쪽으로 모임'),
    'S1': ('분절 광륜', '기존 대소 겹원 바깥을 끊어진 빛테와 정렬된 작은 광편으로 보강'),
    'S2': ('나선 수렴', '네 가닥 광류가 원의 바깥에서 안으로 감겨 들어간 뒤 짧게 방출'),
    'S3': ('깃날 파열', '원 테두리에 날카로운 깃광편이 겹치고 발사 때 전방으로 열림'),
    'D1': ('깃결 점화', '실제 장식 활에 붙은 깃맥을 점화하고 발사 때 작은 금빛 불티'),
    'D2': ('쌍깃 수렴', '짧은 두 깃바람이 현재 활 둘레에서 발사점으로 모임'),
    'D3': ('별광 세공', '장식 활의 중앙과 끝에 짧은 별광·보조깃을 붙임'),
    'F1': ('결정 균열광', '현재 조립 화살 둘레에 짧은 결정 능선과 금빛 내부 균열을 보강'),
    'F2': ('삼중 결정 흐름', '세 갈래 결정 조각이 현재 중앙 화살로 정렬되어 흡수'),
    'F3': ('백금 파쇄광', '얇은 백금 파편이 앞뒤에서 모이고 발사 때 작게 분리'),
    'B1': ('출발 수축 · 도착 개방', '출발점의 짧은 수축광과 실제 도착점의 얇은 깃빛 파열'),
    'B2': ('쌍점 깃잔광', '두 지점에 서로 반대 방향으로 흐르는 짧은 깃빛과 작은 불티'),
    'W': ('원 배치 반전', '기존 W0의 두 원 크기 순서를 교환한 적용본'),
    'A': ('나선 꼬리 정돈', '기존 A4의 넓은 세 흐름을 좁고 짧은 두 흐름으로 정돈한 적용본'),
}


class Study(BaseStudy):
    instance_serial = 0

    def __init__(self, rig, option):
        Study.instance_serial += 1
        self.spawn_label = option+'_'+str(Study.instance_serial)
        super().__init__(rig, option)
        self.lines = [self.plane('soft_line', 'filament') for _ in range(100 if option == 'Q1' else 60)]
        self.dots = [self.plane('soft_dot', 'mote') for _ in range(28 if option == 'Q1' else 18)]
        self.art = []
        self.emitted = set()
        self.hidden = []
        self.start = rig['pawn']().get_actor_location()
        self.q_center = rig['ground'](self.start.x+420., self.start.y) if option == 'Q1' else None
        self.end = self.start
        self.arrived = False
        self.shot_at = None
        self.arrow_names = set()
        for row in self.planes:
            row['actor'].set_editor_property('tags', [TAG])

    def plane(self, material, label):
        option=self.option
        self.option=self.spawn_label
        try:
            return super().plane(material,label)
        finally:
            self.option=option

    def reset_draw(self):
        self.line_index = 0
        for row in self.lines:
            row['mid'].set_scalar_parameter_value('CoreIntensity', 0.)
            row['mid'].set_scalar_parameter_value('GlowIntensity', 0.)
        for row in self.dots:
            row['mid'].set_scalar_parameter_value('Intensity', 0.)

    def line(self, a, b, width, power):
        if self.line_index >= len(self.lines) or power <= 0.: return
        factor = 1. if self.option[0] in ('Q','B') else 1.5
        self.soft_line(self.lines[self.line_index], a, b, width*factor, power*factor)
        self.line_index += 1

    def curve(self, points, width, power):
        for a, b in zip(points, points[1:]): self.line(a, b, width, power)

    def arc(self, p, axis1, axis2, radius, start, extent, width, power, count=7):
        points = [p + axis1*(math.cos(start+extent*i/count)*radius)
                  + axis2*(math.sin(start+extent*i/count)*radius) for i in range(count+1)]
        self.curve(points, width, power)

    def feather(self, p, direction, side, length, width, power):
        tip = p+direction*length+side*width*.45
        self.line(p, tip, 2.2, power*1.1)
        for sign in (-1., 1.):
            points = [p, p+direction*length*.28+side*width*sign,
                      p+direction*length*.66+side*width*sign*.76, tip]
            self.curve(points, 3.8, power*.75)

    def art_part(self, mesh, material):
        row = self.plane('soft_dot', 'attached_feather')
        row['actor'].set_editor_property('tags', [TAG])
        row['mesh'].set_static_mesh(mesh)
        row['mid'] = row['mesh'].create_dynamic_material_instance(0, material)
        row['mid'].set_scalar_parameter_value('Envelope', 0.)
        self.art.append(row)
        return row

    def update(self, age):
        self.reset_draw()
        key, variant = self.option[0], int(self.option[1:])
        pawn = self.rig['pawn']()
        f = pawn.get_actor_forward_vector()
        f = unreal.Vector(f.x, f.y, 0.)
        right, up = unreal.Vector(-f.y, f.x, 0.), self.up
        mesh = pawn.get_editor_property('mesh')
        anchor = mesh.get_socket_location('arrow_anchor') + up*6.
        for arrow in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowArrow):
            if valid(arrow) and arrow.get_owner() == pawn:
                self.arrow_names.add(arrow.get_name())
                if self.shot_at is None: self.shot_at = age
        shot = -1. if self.shot_at is None else age-self.shot_at
        charge = clamp(age/.12)
        fade = 1. if shot < 0. else (1.-clamp(shot/.19))**1.5
        if variant==2 and key in ('E','S','D','F') and shot<0.:
            accents=(.36,.69,.88) if key=='F' else (.08,.20) if key=='E' else (.08,.15) if key=='D' else (.10,.24)
            for pulse_time in accents:
                token='texture_'+str(pulse_time)
                if age<pulse_time or token in self.emitted:continue
                self.emitted.add(token)
                if key=='E':
                    for sign in (-1.,1.):
                        p=anchor+right*sign*45.-f*12.
                        self.pulse('shards',('Flames2',),p,unreal.MathLibrary.make_rot_from_z(-right*sign+f*.25),(.17,.17,.25),.20,2.1)
                elif key=='S':
                    center=anchor+f*70.
                    for n in range(4):
                        a=n*math.tau/4.+pulse_time*2.
                        radial=right*math.cos(a)+up*math.sin(a)
                        self.pulse('shards',('Flames2',),center+radial*72.,unreal.MathLibrary.make_rot_from_z(-radial+f*.3),(.16,.16,.25),.19,2.1)
                elif key=='D':
                    center=mesh.get_socket_location('BowEmitterSocket')
                    for sign in (-1.,1.):
                        self.pulse('shards',('Flames2',),center+up*sign*48.,unreal.MathLibrary.make_rot_from_z(-up*sign+f*.35),(.18,.18,.28),.20,2.)
                else:
                    for n in range(3):
                        a=n*math.tau/3.;radial=right*math.cos(a)+up*math.sin(a)
                        self.pulse('shards',('Flames2',),anchor+f*85.+radial*26.,unreal.MathLibrary.make_rot_from_z(f-radial*.6),(.15,.15,.22),.19,2.2)
        if key == 'Q':
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowAscendedShotFX):
                if actor.get_owner() == pawn and actor.actor_has_tag('SparrowAscendedRain'):
                    actor.set_actor_hidden_in_game(True)
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowAscensionAccent):
                if actor.actor_has_tag('SparrowQGroundImpact'): actor.set_actor_hidden_in_game(True)
            center = self.q_center
            t = age-1.04
            for i in range(28):
                angle = i*2.399963
                radius = math.sqrt((i+.5)/28.)*620.
                p = center+right*(math.cos(angle)*radius)+f*(math.sin(angle)*radius)
                if -.09 <= t < .29:
                    head = max(0., -t/.09)*1250.
                    power = (1.-clamp(max(t, 0.)/.29))**1.8
                    self.line(p+up*head, p+up*(head+1250.), 5.5 if i%4 else 10., power*(2.6 if i%4 else 3.6))
                    if t >= 0.:
                        self.line(p-right*20., p+right*20., 5., power*2.)
                        self.soft_dot(self.dots[i], p+up*7., 22.+i%3*5., power*2.1)
            return
        if key == 'E':
            for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowEDesignVisual):
                if actor.get_owner() != pawn: continue
                native = next((c for c in actor.get_components_by_class(unreal.StaticMeshComponent)
                               if c.component_has_tag('ERegaliaBow')), None)
                if native and not self.art and variant == 1:
                    row = self.art_part(native.get_editor_property('static_mesh'), native.get_material(0))
                    row['source'] = native
            if self.art:
                row = self.art[0]
                row['actor'].set_actor_location(anchor+up*3.-f*7., False, True)
                row['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(f, up), True)
                row['mesh'].set_world_scale3d(unreal.Vector(.48,.48,1.))
                for name,value in {'Age':age,'Open':charge,'Draw':clamp(age/.32),'Envelope':fade*.82}.items():
                    row['mid'].set_scalar_parameter_value(name,value)
            if variant == 1:
                for sign in (-1.,1.):
                    self.line(anchor,anchor+right*sign*24.-f*31.,4.,charge*fade*1.8)
                    self.line(anchor+right*sign*24.-f*31.,anchor-f*57.,3.,charge*fade*1.4)
                    self.feather(anchor+right*sign*22.,right*sign-f*.35,f,78.,18.,charge*fade*1.7)
            elif variant == 2:
                for sign in (-1.,1.):
                    for lane in range(2):
                        points = [anchor+right*sign*(u*155.)-f*(u*u*65.+lane*9.)+up*(4.+lane*5.)
                                  for u in (0.,.2,.4,.6,.8,1.)]
                        self.curve(points,3.+lane,charge*fade*(1.8-lane*.45))
                    for n in range(3):
                        p=anchor+right*sign*(24.+n*27.)-f*(n*n*6.)
                        self.feather(p,right*sign-f*.65,f,42.,9.,charge*fade*1.4)
            else:
                for sign in (-1.,1.):
                    for n in range(3):
                        p=anchor+right*sign*(12.+n*12.)
                        self.feather(p,right*sign-f*.75,f,64.-n*9.,14.,charge*fade*(1.6-n*.2))
                if age>.12 and 'plume' not in self.emitted:
                    self.emitted.add('plume')
                    self.pulse('shards',('Flames2',),anchor,unreal.MathLibrary.make_rot_from_z(f),(.19,.19,.25),.22,2.2)
            self.soft_dot(self.dots[0],anchor,10.+4.*math.sin(age*20.),charge*fade*2.)
        elif key == 'S':
            center = anchor+f*70.
            envelope = charge*(1.-clamp(max(0.,age-.38)/.24))
            if variant == 1:
                for n in range(6):
                    self.arc(center,right,up,85.,n*math.tau/6.+age*.5,.57,4.,envelope*1.55,5)
                for i,row in enumerate(self.dots[:12]):
                    a=i*math.tau/12.+age*.6
                    self.soft_dot(row,center+right*math.cos(a)*91.+up*math.sin(a)*91.,5.,envelope*1.1)
            elif variant == 2:
                for n in range(4):
                    points=[]
                    for i in range(12):
                        u=i/11.; a=n*math.tau/4.+u*1.6+age*2.
                        r=(110.-u*64.)*(1.-clamp(age/.48)*.23)
                        points.append(center+right*(math.cos(a)*r)+up*(math.sin(a)*r)-f*(u*22.))
                    self.curve(points,4.,envelope*1.75)
            else:
                for n in range(8):
                    a=n*math.tau/8.+.22
                    radial=right*math.cos(a)+up*math.sin(a)
                    tangent=-right*math.sin(a)+up*math.cos(a)
                    self.feather(center+radial*64.,radial*.55+tangent*.8,tangent,42.,9.,envelope*1.9)
            if age>=.38 and 'release' not in self.emitted:
                self.emitted.add('release')
                self.pulse('muzzle',('Wisps','Sparks'),center,unreal.MathLibrary.make_rot_from_x(f),(.90,.50,.50),.17,2.1)
        elif key == 'D':
            center=mesh.get_socket_location('BowEmitterSocket')
            envelope=charge*fade
            if variant == 1:
                for sign in (-1.,1.):
                    for n in range(3):
                        self.feather(center+up*sign*(12.+n*18.),up*sign-f*.35,f,46.,10.,envelope*1.7)
            elif variant == 2:
                for sign in (-1.,1.):
                    points=[center+up*sign*(80.*(1.-u))-f*(38.*math.sin(math.pi*u))
                            +right*sign*math.sin(math.pi*u)*12. for u in (0.,.2,.4,.6,.8,1.)]
                    self.curve(points,5.,envelope*2.)
                    self.feather(points[1],-up*sign+f*.4,right,40.,8.,envelope*1.6)
            else:
                for n in (-1,0,1):
                    p=center+up*n*54.
                    self.line(p-right*10.,p+right*10.,3.,envelope*2.3)
                    self.line(p-up*15.,p+up*15.,3.,envelope*1.9)
                    self.soft_dot(self.dots[n+1],p,8.,envelope)
            if shot>=0. and 'release' not in self.emitted:
                self.emitted.add('release')
                self.pulse('muzzle',('Sparks',),center,unreal.MathLibrary.make_rot_from_x(f),(.62,.30,.30),.16,2.)
        elif key == 'F':
            center=anchor+f*100.
            envelope=clamp(age/.22)*fade
            if variant == 1:
                for n in range(5):
                    p=center+f*(-45.+n*22.)
                    side=right*((-1 if n%2 else 1)*13.)+up*((n%3-1)*9.)
                    self.line(p-side,p+f*24.+side*.5,3.5,envelope*2.)
                    self.line(p+f*24.+side*.5,p+f*40.-side*.4,2.5,envelope*1.6)
                for sign in (-1.,1.):
                    self.line(center-f*67.+right*sign*12.,center+f*84.,3.,envelope*1.5)
            elif variant == 2:
                for n in range(3):
                    a=n*math.tau/3.
                    radial=right*math.cos(a)+up*math.sin(a)
                    t=(age*.70+n*.25)%1.
                    p=center-f*(95.*(1.-t))+radial*(48.*(1.-t))
                    self.feather(p,f,radial,35.,7.,envelope*1.9)
                    self.line(p-f*20.,p,3.,envelope*1.2)
            else:
                for n in range(8):
                    t=(age*.8+n*.125)%1.; a=n*2.39996
                    radial=right*math.cos(a)+up*math.sin(a)
                    p=center+f*(80.-t*160.)+radial*(15.+(1.-abs(t-.5)*2.)*20.)
                    self.line(p-radial*6.-f*8.,p+radial*6.+f*8.,4.,envelope*1.7)
                    self.line(p+radial*6.+f*8.,p+f*19.,2.5,envelope)
            if shot>=0. and 'release' not in self.emitted:
                self.emitted.add('release')
                self.pulse('shards',('Flames2',),center,unreal.MathLibrary.make_rot_from_z(f),(.20,.20,.28),.18,2.3)
        elif key == 'B':
            point=pawn.get_actor_location()
            if not self.arrived and (point-self.start).length()>10.:
                self.arrived=True; self.end=point
                self.pulse('impact',('Sparks','Main Flames'),self.end-up*20.,unreal.Rotator(),(.42,.42,.56),.24,2.)
            for place,p in enumerate((self.start,self.end)):
                if place and not self.arrived: continue
                local=max(0.,age-(.04 if place else 0.))
                envelope=(1.-clamp(local/.42))**1.6
                radius=(48.-local*90.) if not place else (20.+local*130.)
                center=p-up*35.
                if variant==1:
                    for n in range(3):
                        self.arc(center,right,up,max(radius,2.),n*math.tau/3.+place*.4,.95,5.,envelope*1.9,7)
                    self.line(center-up*28.,center+up*100.,8.,envelope*1.35)
                else:
                    for n in range(4):
                        a=n*math.tau/4.+local*1.8
                        radial=right*math.cos(a)+up*math.sin(a)
                        tangent=-right*math.sin(a)+up*math.cos(a)
                        self.feather(center+radial*radius,radial*(1. if place else -1.)+tangent*.5,tangent,40.,10.,envelope*1.8)
            for i,row in enumerate(self.dots[:12]):
                p=(self.end if i%2 else self.start)-up*35.
                a=i*2.4; r=15.+age*70.
                self.soft_dot(row,p+right*math.cos(a)*r+up*(math.sin(a)*r+20.),5.,(1.-clamp(age/.4))*1.5)
        self.tick()


def sequence(rig):
    selected=os.environ.get('SPARROW_POLISH_CASES',','.join(DESIGNS)).split(',')
    modes=os.environ.get('SPARROW_POLISH_MODES','normal').split(',')
    skip=set(os.environ.get('SPARROW_POLISH_SKIP','').split(','))
    report={'passed':False,'visual_only_candidates':True,'saved_assets':False,'cases':[]}
    frame=1./rig['FPS']; out=Path(rig['OUT'])
    rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
    try:
        for option in selected:
            assert option in DESIGNS,option
            key=option[0]
            for mode in (['form'] if key in ('Q','B') else modes):
                if option+'_'+mode in skip: continue
                rig['switch']('countess');yield .15
                rig['switch']('sparrow');yield .65
                targets=rig['layout']([(700,350),(800,-350),(900,500)] if key in ('A','B') else [(260,0),(700,0),(700,350)])
                yield .2
                if mode=='form': rig['use']('V',offset=(950,0));yield 2.1
                rig['aim'](offset=(420 if key=='Q' else 950,0))
                ident=option+'_'+mode
                rig['case'](ident)
                start=unreal.GameplayStatics.get_time_seconds(rig['world']())
                study=None if key in ('W','A') else Study(rig,option)
                rig['STATE']['video_clip']={'case':ident,'prefix':ident+'_video','cast_time':start,'frame_times':[]}
                rig['key']('SpaceBar' if key=='B' else key)
                duration=2.5 if key=='A' else 2.2 if key in ('Q','W') else 1.65 if key=='F' else 1.25 if key=='B' else 1.2
                moments=([.25,.80,1.00,1.10,1.23,1.40] if key=='Q' else [.067,.133,.233,.40] if key=='B'
                         else [.16,.25,.32,.40,.55,.80,1.10,1.5])
                observations=[]; saw_busy=False; arrows=set(); rings=[]
                try:
                    while True:
                        age=unreal.GameplayStatics.get_time_seconds(rig['world']())-start
                        if age>duration: break
                        saw_busy|=rig['pawn']().is_combat_busy()
                        if study: study.update(age)
                        for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowArrow):
                            if a.get_owner()==rig['pawn'](): arrows.add(a.get_name())
                        if key=='W':
                            for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowShotWave):
                                parts=[c for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.get_name().startswith('AirWave') and c.is_visible()]
                                if len(parts)==2:
                                    rings.append([{'name':p.get_name(),'scale':rig['vec'](p.get_world_scale()),'relative':rig['vec'](p.get_editor_property('relative_location'))} for p in parts])
                        if key=='B': observations.append(rig['vec'](rig['pawn']().get_actor_location()))
                        if moments and age>=moments[0]: rig['capture'](ident+'_t'+str(round(moments.pop(0)*1000)).zfill(4))
                        yield frame
                    rig['finish_video_clip']()
                    rig['check'](saw_busy,ident+' uses actual input and cast')
                    rig['check'](not rig['pawn']().is_combat_busy(),ident+' returns control after the native action')
                    if key=='W': rig['check'](len(arrows)==(5 if mode=='form' else 4),ident+' retains shot count')
                    if key=='A':
                        native=unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow)
                        rig['check'](len(native)==1 and abs(native[0].get_flight_speed()-160.)<.01,ident+' retains slow160cm/s gear')
                    if key=='B':
                        delta=(rig['pawn']().get_actor_location()-study.start).length()
                        rig['check'](study.arrived and abs(delta-480.)<3.,ident+' actual blink retains480cm')
                    report['cases'].append({'id':ident,'label':DESIGNS[option][0],'description':DESIGNS[option][1],
                        'duration':duration,'arrows':len(arrows),'positions':observations,'ring_samples':rings,
                        'installed':key in ('W','A'),'visual_only':key not in ('W','A')})
                finally:
                    rig['finish_video_clip']()
                    if study: study.close()
                (out/'polish-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                if key=='Q':yield 3.
        report['passed']=True
    finally:
        (out/'polish-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
