"""Seven PIE-only quarter-view studies; no asset saves or new gameplay bindings.

A10-A13 add layers around the unchanged real A cast. Its lane contains no target;
the native projectile is removed before leaving this isolated presentation.
N1-N3 are moving visual props/PSCs only, not implemented gameplay abilities.
Use SPARROW_ORBIT_OPTIONS to select cases; sequence(rig) uses new_skills_probe.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_PART = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PART['Study'], _PART['_valid']
TAG = unreal.Name('SparrowOrbitArsenalStudy')
ROOT = '/Game/TopDown/Characters/Sparrow'
MATERIALS = {
    'fine': ROOT + '/Previews/WRefined20261022/M_WOptionA1',
    'glyph': ROOT + '/Previews/WRefined20261022/M_WOptionA2',
    'fracture': ROOT + '/Previews/WRefined20261022/M_WOptionA4',
    'line': ROOT + '/Materials/M_SparrowShotWindAxis',
    'soft_line': '/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip',
    'soft_dot': '/Game/TopDown/Characters/Gideon/FX/M_NoxSpark',
}
PARAMETERS = {'line': 'Envelope', 'soft_line': 'CoreIntensity', 'soft_dot': 'Intensity'}
DESIGNS = {
    'A10': {'label': '이중 공전환', 'role': 'A 외곽 보강',
            'shape': '얇은 두 궤도가 서로 반대로 돌며 기존 회전부와 빠직 파열을 감싼다.',
            'sources': ['fine', 'muzzle: Sparks']},
    'A11': {'label': '파열 톱니환', 'role': 'A 외곽 보강',
            'shape': '끊어진 톱니 외곽에서 짧은 금빛 파편이 번갈아 튄다. 중심 회전은 그대로 유지한다.',
            'sources': ['fracture', 'shards: Flames2']},
    'A12': {'label': '쌍갈고리 후류', 'role': 'A 측면 보강',
            'shape': '회전부 뒤 양옆에 짧고 연속된 금빛 갈고리 곡선이 흐르고, 화염편과 불티가 뒤따른다.',
            'sources': ['soft_line', 'shards: Flames2', 'muzzle: Wisps / Sparks']},
    'A13': {'label': '나선 잔륜', 'role': 'A 후류 보강',
            'shape': '뒤로 갈수록 작고 희미해지는 세 개의 짧은 잔륜과 불티로 전진 압력을 만든다.',
            'sources': ['glyph', 'muzzle: Sparks']},
    'N1': {'label': '황금 결박', 'role': '단일 대상 군중제어 제안',
           'shape': '적을 향한 빛이 도착하면 수평·수직 고리가 좁아지며 잠기고, 파편으로 해제된다.',
           'sources': ['fine', 'glyph', 'line', 'muzzle: Sparks', 'impact: Sparks / SparkTrailHeads'],
           'not_implemented': '속박·이동 제한·피해 판정 없음'},
    'N2': {'label': '반격막', 'role': '전방 방향 방어 제안',
           'shape': '활 앞에 세로 방어륜이 펼쳐진 뒤 비교용 빛 조각 세 개를 받아 흩뜨리고 접힌다.',
           'sources': ['fine', 'glyph', 'line', 'impact: Sparks / SparkTrailHeads'],
           'not_implemented': '비교용 입사광은 적 투사체가 아니며 방어·반사·피해 판정 없음'},
    'N3': {'label': '빛의 회수', 'role': '회복 또는 자원 회수 제안',
           'shape': '둥근 백금 핵 세 개가 부드러운 금빛 꼬리를 끌며 곡선을 따라 활로 모여 흡수된다.',
           'sources': ['fine', 'soft_line', 'soft_dot', 'muzzle: Wisps / Sparks', 'impact: Wisps'],
           'not_implemented': '생명력 흡수·회복·자원 변경 없음'},
}
OPTIONS = tuple(DESIGNS)


def _write(out, name, value):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    """Read-only inventory; unlike older study authors, this never compiles/saves."""
    paths = {**MATERIALS, **_PART['SOURCES'], 'plane': '/Engine/BasicShapes/Plane'}
    rows = []
    for key, path in paths.items():
        asset = unreal.load_asset(path)
        assert asset, path
        row = {'key': key, 'path': asset.get_path_name(), 'class': asset.get_class().get_name()}
        if key in MATERIALS:
            parameters = [str(p) for p in unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset)]
            assert PARAMETERS.get(key, 'Strength') in parameters, (path, parameters)
            row['scalar_parameters'] = parameters
        rows.append(row)
    result = {'assets_saved': False, 'production_changed': False, 'sources': rows, 'designs': DESIGNS}
    _write(out, 'orbit-arsenal-sources.json', result)
    return result


def _clamp(value):
    return max(0., min(1., value))


def _smooth(value):
    value = _clamp(value)
    return value * value * (3. - 2. * value)


def _plane_rotation(normal, spin=0.):
    # ComposeRotators applies local Z spin first, then aligns the plane normal.
    return unreal.MathLibrary.compose_rotators(
        unreal.Rotator(yaw=spin), unreal.MathLibrary.make_rot_from_z(normal))


class Study(ParticleStudy):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.planes, self.arrow_actor, self.native_snapshot = [], None, []
        self.serial, self.last_pulse, self.last_trail = 0, -100., -100.
        self.events, self.particle_samples = [], []
        self.materials = {key: unreal.load_asset(path) for key, path in MATERIALS.items()}
        self.plane_mesh = unreal.load_asset('/Engine/BasicShapes/Plane')
        self.forward, self.right, self.up = unreal.Vector(1, 0, 0), unreal.Vector(0, 1, 0), unreal.Vector(0, 0, 1)
        self.origin = rig['skills']().get_arrow_origin()
        self.born = self.now()
        self.next_sample = .2
        self.phase_events = set()

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1.):
        # Finish all properties before Activate: editor property writes can
        # reregister the component. Emitter masks require live instances.
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.templates[key], position, rotation,
            unreal.Vector(*scale), False, unreal.PSCPoolMethod.NONE, False)
        assert particle, (key, names)
        self.effects.append((particle, self.now() + seconds))
        self.created += 1
        direct = next(getattr(unreal.ParticleSystemLODMethod, name)
                      for name in dir(unreal.ParticleSystemLODMethod) if 'DIRECT' in name.upper())
        particle.set_editor_property('component_tags', [TAG])
        particle.set_editor_property('override_lod_method', True)
        particle.set_editor_property('lod_method', direct)
        particle.set_editor_property('custom_time_dilation', speed)
        particle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        particle.set_editor_property('generate_overlap_events', False)
        particle.activate(True)
        for name in _PART['EMITTERS'][key]:
            particle.set_emitter_enable(name, name in names)
        return particle

    def plane(self, material, label):
        self.serial += 1
        name = 'OrbitStudy_' + self.option + '_' + str(self.serial)
        p = self.origin
        self.rig['cmd'](f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {p.x} {p.y} {p.z}')
        actor = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(
            self.rig['world'](), unreal.StaticMeshActor) if a.get_name() == name)
        actor.set_actor_enable_collision(False)
        actor.set_life_span(6.)
        actor.set_editor_property('tags', [TAG])
        mesh = actor.get_editor_property('static_mesh_component')
        mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        mesh.set_editor_property('generate_overlap_events', False)
        mesh.set_editor_property('can_ever_affect_navigation', False)
        mesh.set_editor_property('cast_shadow', False)
        mesh.set_static_mesh(self.plane_mesh)
        mid = mesh.create_dynamic_material_instance(0, self.materials[material])
        assert mid, material
        row = {'actor': actor, 'mesh': mesh, 'mid': mid, 'label': label,
               'parameter': PARAMETERS.get(material, 'Strength')}
        if material == 'soft_line':
            mid.set_vector_parameter_value('CoreColor', unreal.LinearColor(1., .90, .60, 1.))
            mid.set_vector_parameter_value('GlowColor', unreal.LinearColor(1., .60, .12, 1.))
            mid.set_scalar_parameter_value('CoreSharpness', 6.)
            mid.set_scalar_parameter_value('GlowSoftness', 1.7)
            mid.set_scalar_parameter_value('GlowIntensity', 0.)
        elif material == 'soft_dot':
            mid.set_vector_parameter_value('Color', unreal.LinearColor(1., .88, .48, 1.))
            mid.set_scalar_parameter_value('Softness', 2.)
        mid.set_scalar_parameter_value(row['parameter'], 0.)
        self.planes.append(row)
        return row

    def place(self, row, position, scale, normal, spin, strength):
        row['actor'].set_actor_location(position, False, True)
        row['actor'].set_actor_rotation(_plane_rotation(normal, spin), True)
        row['mesh'].set_world_scale3d(unreal.Vector(*scale))
        row['mid'].set_scalar_parameter_value(row['parameter'], max(0., strength))

    def glint(self, row, position, direction, length=1., width=.4, strength=.8):
        row['actor'].set_actor_location(position, False, True)
        row['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_x(direction), True)
        row['mesh'].set_world_scale3d(unreal.Vector(length, width, 1.))
        row['mid'].set_scalar_parameter_value(row['parameter'], strength)

    def soft_line(self, row, start, end, width, strength):
        # The production SparrowSkillVisual uses this same camera-facing
        # strip and parameter interface. Each short segment follows the curve.
        middle=(start+end)*.5
        delta=end-start
        length=math.sqrt(delta.x*delta.x+delta.y*delta.y+delta.z*delta.z)
        camera=unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](),0).get_camera_location()
        row['actor'].set_actor_location(middle,False,True)
        if length>.01:
            row['actor'].set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(delta,camera-middle),True)
        row['mesh'].set_world_scale3d(unreal.Vector(max(length,.01)*1.035/100.,width/100.,1.))
        row['mid'].set_scalar_parameter_value('CoreIntensity',strength)
        row['mid'].set_scalar_parameter_value('GlowIntensity',strength*.18)

    def soft_dot(self, row, point, size, strength):
        camera=unreal.GameplayStatics.get_player_camera_manager(self.rig['world'](),0).get_camera_location()
        self.place(row,point,(size/100.,size/100.,1.),camera-point,0.,strength)

    def mote_point(self, index, progress):
        progress=_clamp(progress)
        source=self.mote_origins[index]
        bow=self.origin+self.forward*12.
        curve=self.up*(math.sin(progress*math.pi)*90.)+self.right*(math.sin(progress*math.pi)*(index-1)*95.)
        return source+(bow-source)*_smooth(progress)+curve

    def observe_arrow(self, arrow):
        self.arrow_actor = arrow
        # Read-only proof that the native rotation/core/trail weren't replaced.
        for component in arrow.get_components_by_class(unreal.StaticMeshComponent):
            self.native_snapshot.append((component, tuple(component.get_material(i)
                                        for i in range(component.get_num_materials()))))
        if self.option == 'A10':
            self.plane('fine', 'outer_orbit'); self.plane('fine', 'tilted_orbit')
        elif self.option == 'A11':
            self.plane('fracture', 'fractured_saw_halo')
        elif self.option == 'A12':
            self.hooks=[[self.plane('soft_line','hook_'+str(side)+'_'+str(i))
                         for i in range(10)] for side in (-1,1)]
        elif self.option == 'A13':
            for index in range(3):
                self.plane('glyph', 'wake_orbit_' + str(index))
        self.events.append({'event': 'native_A_observed', 'time': self.now()-self.born,
                            'speed': arrow.get_flight_speed(), 'piercing': arrow.is_piercing()})

    def a_update(self, elapsed):
        arrow = self.arrow_actor
        if not _valid(arrow):
            return
        p, f = arrow.get_actor_location(), arrow.get_flight_direction()
        center = p + f*40.
        fade = _clamp((3.25-elapsed)/.35)
        if self.option == 'A10':
            self.place(self.planes[0], center-f*5., (2.42, 2.42, 1.), f, -elapsed*180., .48*fade)
            self.place(self.planes[1], center-f*21., (2.78, 2.40, 1.),
                       f+self.up*.28, elapsed*135.+55., .30*fade)
        elif self.option == 'A11':
            self.place(self.planes[0], center-f*8., (2.38, 2.38, 1.), f,
                       -elapsed*290., (.44+.10*math.sin(elapsed*31.))*fade)
        elif self.option == 'A12':
            for side,rows in zip((-1.,1.),self.hooks):
                points=[]
                for i in range(11):
                    u=i/10.
                    spread=38.+80.*math.sin(math.pi*u*.88)
                    points.append(p+f*(18.-138.*u)+self.right*(side*spread)
                                  +self.up*(15.+22.*math.sin(math.pi*u)+3.*math.sin(elapsed*9.+u*5.)))
                for i,row in enumerate(rows):
                    taper=1.-i/11.
                    self.soft_line(row,points[i],points[i+1],14.+13.*taper,
                                   fade*(1.15+1.45*taper)*(.91+.09*math.sin(elapsed*12.-i*.7)))
        elif self.option == 'A13':
            for i, row in enumerate(self.planes):
                size = 2.02-i*.36
                self.place(row, center-f*(28.+i*38.), (size, size, 1.), f,
                           elapsed*(220. if i%2 else -210.)+i*45., (.40-i*.10)*fade)
        cadence = .18 if self.option == 'A12' else .28
        if elapsed < 2.95 and self.now()-self.last_pulse >= cadence:
            self.last_pulse = self.now()
            phase = elapsed*5.5
            radial = self.right*math.cos(phase)+self.up*math.sin(phase)
            if self.option == 'A10':
                self.pulse('muzzle', ('Sparks',), center+radial*77.,
                           unreal.MathLibrary.make_rot_from_x(radial), (.46,.46,.46), .30, 1.4)
            elif self.option == 'A11':
                self.pulse('shards', ('Flames2',), center+radial*64.,
                           unreal.MathLibrary.make_rot_from_z(radial), (.22,.22,.31), .30, 1.9)
            elif self.option == 'A12':
                for side in (-1.,1.):
                    q = p-f*24.+self.right*(side*40.)+self.up*12.
                    direction = f*-1.+self.right*(side*.8)+self.up*.12
                    self.pulse('shards', ('Flames2',), q,
                               unreal.MathLibrary.make_rot_from_z(direction), (.31,.31,.60), .40, 1.7)
                    self.pulse('muzzle', ('Sparks',), p-f*100.+self.right*(side*70.)+self.up*15.,
                               unreal.MathLibrary.make_rot_from_x(direction), (.42,.42,.42), .32, 1.6)
                self.pulse('muzzle', ('Wisps',), p-f*36.,
                           unreal.MathLibrary.make_rot_from_x(f*-1.), (.62,.37,.37), .26, 2.)
            else:
                self.pulse('muzzle', ('Sparks',), p-f*90.+radial*20.,
                           unreal.MathLibrary.make_rot_from_x(f*-1.), (.42,.42,.42), .28, 1.8)

    def setup_new(self, targets):
        self.target = targets[0].get_actor_location()
        if self.option == 'N1':
            self.rings = [self.plane('glyph' if i<2 else 'fine', 'binding_'+str(i)) for i in range(4)]
            self.darts = [self.plane('line', 'binding_arrival')]
        elif self.option == 'N2':
            self.rings = [self.plane('glyph' if i == 0 else 'fine', 'guard_'+str(i)) for i in range(3)]
            self.darts = [self.plane('line', 'visual_incident_light_'+str(i)) for i in range(3)]
        else:
            self.rings = [self.plane('fine', 'absorption_lip')]
            self.darts = [self.plane('soft_dot', 'returning_mote_'+str(i)) for i in range(3)]
            self.mote_glows = [self.plane('soft_dot', 'mote_glow_'+str(i)) for i in range(3)]
            for row in self.mote_glows:
                row['mid'].set_vector_parameter_value('Color',unreal.LinearColor(1.,.60,.10,1.))
                row['mid'].set_scalar_parameter_value('Softness',1.5)
            self.mote_tails=[[self.plane('soft_line','mote_tail_'+str(i)+'_'+str(j))
                             for j in range(8)] for i in range(3)]
            self.mote_origins = [self.origin+self.forward*(260.+i*50.)+self.right*((i-1)*190.)
                                 +self.up*(25.+i*16.) for i in range(3)]

    def once(self, key):
        if key in self.phase_events:
            return False
        self.phase_events.add(key)
        self.events.append({'event': key, 'time': self.now()-self.born})
        return True

    def new_update(self, t):
        if self.option == 'N1':
            arrival = _clamp(t/.55)
            position = self.origin+(self.target-self.origin)*arrival
            self.glint(self.darts[0], position, self.target-self.origin, 1.1,.45, .8 if t < .55 else 0.)
            envelope = _smooth((t-.48)/.22)*(1.-_smooth((t-2.55)/.58))
            contraction = 1.-_smooth((t-.55)/.45)
            for i,row in enumerate(self.rings):
                normal = self.up if i<2 else (self.forward if i == 2 else self.right)
                height = (-48. if i == 0 else 50.) if i<2 else 0.
                size = 2.20+contraction*.95 if i<2 else 3.0+contraction*.75
                scale = (size,size,1.) if i<2 else (size,size*.62,1.)
                self.place(row,self.target+self.up*height,scale,normal,t*(38. if i%2 else -45.),envelope*(.57 if i<2 else .31))
            if .55 <= t < 2.6 and self.now()-self.last_pulse > .30:
                self.last_pulse=self.now()
                self.pulse('muzzle',('Sparks',),self.target+self.right*(54.*math.sin(t*8.)),
                           unreal.Rotator(),(.55,.55,.55),.32,1.4)
            if t>=2.6 and self.once('binding_releases'):
                self.pulse('impact',('Sparks','SparkTrailHeads'),self.target,unreal.Rotator(),(.85,.85,.85),.55,1.5)
        elif self.option == 'N2':
            center = self.origin+self.forward*110.
            envelope = _smooth(t/.40)*(1.-_smooth((t-2.55)/.65))
            for i,row in enumerate(self.rings):
                size = (3.45 if i == 0 else 2.70)*(.45+.55*_smooth(t/.4))
                normal = self.forward+self.right*((i-1)*.27)
                self.place(row,center+self.forward*i*10.,(size,size*.72,1.),normal,
                           (-1. if i%2 else 1.)*t*32.,envelope*(.55 if i == 0 else .29))
            for i,row in enumerate(self.darts):
                begin=.72+i*.55
                progress=_clamp((t-begin)/.38)
                endpoint=center+self.right*((i-1)*53.)+self.up*((i%2)*34.)
                position=endpoint+self.forward*(390.*(1.-progress))
                self.glint(row,position,self.forward*-1.,.88,.33,.85 if begin<=t<begin+.38 else 0.)
                if t>=begin+.38 and self.once('visual_light_intercept_'+str(i)):
                    self.pulse('impact',('Sparks','SparkTrailHeads'),endpoint,
                               unreal.MathLibrary.make_rot_from_x(self.forward),(.85,.65,.65),.46,1.5)
        else:
            absorb = 0.
            for i,row in enumerate(self.darts):
                begin=.40+i*.30
                progress=_clamp((t-begin)/1.30)
                bow=self.origin+self.forward*12.
                position=self.mote_point(i,progress)
                strength=1. if begin<=t<begin+1.30 else 0.
                self.soft_dot(row,position,43.,strength*4.8)
                self.soft_dot(self.mote_glows[i],position,83.,strength*.70)
                for j,tail in enumerate(self.mote_tails[i]):
                    # The fading tail samples the same curved return path,
                    # rather than orienting a rectangular stamp toward the bow.
                    a=max(0.,progress-j*.035)
                    b=max(0.,progress-(j+1)*.035)
                    taper=1.-j/8.
                    self.soft_line(tail,self.mote_point(i,a),self.mote_point(i,b),
                                   8.+18.*taper,strength*(.25+1.55*taper) if a>b else 0.)
                if strength and self.now()-self.last_trail>.105:
                    self.pulse('muzzle',('Wisps','Sparks'),position,
                               unreal.Rotator(),(.68,.56,.56),.30,1.6)
                hit_time=begin+1.30
                absorb=max(absorb,_clamp(1.-abs(t-hit_time)/.30))
                if t>=hit_time and self.once('mote_absorbed_'+str(i)):
                    self.pulse('impact',('Wisps',),bow,unreal.Rotator(),(.80,.52,.52),.38,1.7)
            if self.now()-self.last_trail>.105:
                self.last_trail=self.now()
            self.place(self.rings[0],self.origin+self.forward*14.,(1.65,1.65,1.),
                       self.forward,-t*150.,absorb*.54)

    def update(self, elapsed):
        if self.option.startswith('A'):
            self.a_update(elapsed)
        else:
            self.new_update(elapsed)
        self.tick()
        if elapsed >= self.next_sample:
            self.next_sample += .2
            active=[p for p,_ in self.effects if _valid(p) and p.is_active()]
            self.particle_samples.append({'elapsed':round(elapsed,4),'active_PSCs':len(active),
                'live_particles':sum(p.get_num_active_particles() for p in active)})

    def close(self):
        failures=[]
        for component,materials in self.native_snapshot:
            if _valid(component) and tuple(component.get_material(i) for i in range(component.get_num_materials())) != materials:
                failures.append(component.get_path_name())
        for row in self.planes:
            if _valid(row['actor']):
                row['actor'].destroy_actor()
        self.planes.clear()
        if _valid(self.arrow_actor):
            self.arrow_actor.destroy_actor()
        super().close()
        return failures


def sequence(rig):
    selected=[x.strip().upper() for x in os.environ.get('SPARROW_ORBIT_OPTIONS',','.join(OPTIONS)).split(',') if x.strip()]
    assert selected and all(x in OPTIONS for x in selected),selected
    inventory=author(rig['OUT'])
    rows=[]
    console_evidence=None
    now=lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in selected:
        rig['switch']('countess'); yield .15
        rig['switch']('sparrow'); yield .55
        prefix='orbit_'+option
        rig['case'](prefix)
        # All A targets are outside the full native 1800 cm forward lane.
        offsets=[(450,430),(650,-430),(900,430)] if option.startswith('A') else [(430,0),(650,380),(650,-380)]
        targets=rig['layout'](offsets)
        yield .20
        initial=[rig['health'](target) for target in targets]
        study=Study(rig,option)
        started=now()
        seen=set()
        moments=[.85,1.55,2.45,3.35]
        row={'id':option,**DESIGNS[option],'video_prefix':prefix+'_video','visual_only':True,
             'installed':False,'gameplay_role_implemented':False,'duration_seconds':3.6}
        try:
            if option.startswith('A'):
                rig['use']('A',offset=(550,0))
            else:
                study.setup_new(targets)
            if os.environ.get('NEW_SKILLS_VIDEO','1')=='1':
                rig['STATE']['video_clip']={'case':prefix,'prefix':prefix+'_video','cast_time':started,'frame_times':[]}
            while now()-started<3.6:
                elapsed=now()-started
                if option.startswith('A'):
                    for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowGearArrow):
                        if arrow.get_owner()==rig['pawn']() and arrow.get_path_name() not in seen:
                            seen.add(arrow.get_path_name()); study.observe_arrow(arrow)
                study.update(elapsed)
                # Once across this run, prove rendered emitters contain live particles.
                if console_evidence is None and elapsed>=1.10 and any(
                        _valid(p) and p.is_active() and p.get_num_active_particles()>0 for p,_ in study.effects):
                    token=prefix+'_psc_state'
                    rig['cmd']('SparrowQA.State '+token)
                    state=json.loads((Path(rig['OUT'])/(token+'.json')).read_text(encoding='utf-8-sig'))
                    known=tuple(_PART['SOURCES'].values())
                    visible=[effect for effect in state['effects'] if effect['active'] and effect['particles']>0
                             and effect['template'].split('.')[0] in known
                             and any(e['renders_surface'] and e['particles']>0 for e in effect['render_emitters'])]
                    rig['check'](bool(visible),'original study PSCs contain active surface particles')
                    console_evidence={'file':token+'.json','elapsed':elapsed,'visible_effects':visible}
                if moments and elapsed>=moments[0]:
                    rig['capture'](prefix+'_at_'+str(round(moments.pop(0)*100)).zfill(3))
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            health_delta=[before-rig['health'](target) for before,target in zip(initial,targets)]
            row.update({'target_health_delta':health_delta,'native_A_projectiles':len(seen),
                'events':study.events,'PSC_created':study.created,'peak_live_particles':study.peak_particles,
                'particle_samples':study.particle_samples})
            rig['check'](all(abs(change)<.001 for change in health_delta),option+' has no gameplay damage')
            rig['check'](study.peak_particles>0 and any(s['active_PSCs']>0 and s['live_particles']>0
                         for s in study.particle_samples),option+' renders active original particles')
            if option.startswith('A'):
                rig['check'](len(seen)==1,option+' retains one real native A projectile')
                rig['check'](_valid(study.arrow_actor) and abs(study.arrow_actor.get_flight_speed()-160.)<.01,
                             option+' retains native 160 cm/s flight through the empty lane')
                rig['check'](study.arrow_actor.get_hit_count()==0,option+' has no target contacts or passive hits')
        finally:
            rig['finish_video_clip']()
            failures=study.close()
        rig['check'](not failures,option+' preserves all native A mesh materials')
        rig['check'](not rig['tagged'](str(TAG)) and not study.effects,option+' cleans temporary actors and PSCs')
        row['cleanup_passed']=True
        rows.append(row)
        _write(rig['OUT'],'orbit-arsenal-studies.json',{
            'passed':len(rows)==len(selected),'studies':rows,'representative_PSC_evidence':console_evidence,
            'sources':inventory['sources'],'assets_saved':False,'production_changed':False,
            'visual_review':'pending actual quarter-view video review',
            'note':'N1/N2/N3 show proposed roles with visual props; no gameplay ability or key binding is installed.'})
        yield .15
    rig['check'](console_evidence is not None,'one representative native particle snapshot was checked')
