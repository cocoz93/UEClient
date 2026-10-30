"""S4-S6: transient light/particle binding studies around the real native S.

SPARROW_FEEDBACK_STUDIES=sparrow_binding_reforged_studies.py
SPARROW_BINDING_REFORGED_OPTIONS=S4,S5,S6; NEW_SKILLS_VIDEO=1.
No asset save, source material mutation, extra damage, AI or gameplay changes.
The old signature helper supplies only native observation and visibility restore.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_SIGN = runpy.run_path(str(Path(__file__).with_name('sparrow_binding_signature_studies.py')))
_BASE = _SIGN['_BASE']
BaseStudy, NativeStudy = _BASE['Study'], _SIGN['Study']
valid, clamp, smooth = _SIGN['valid'], _SIGN['clamp'], _SIGN['smooth']
TAG = 'SparrowBindingReforgedStudy'
ARRIVAL, BOUND_END, END = .25, 2.25, 2.70
TRAIL = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_Sparrow_PrimaryAttack'
TRAIL_NAMES = ('RibbonTrail', 'DebugRibbon', 'Flare_Big', 'Flare',
               'SparksTrailing', 'Refraction', 'Particle Emitter')
DESIGNS = {
    'S4': {'label': '백금 실결 포박',
           'shape': '세 갈래 빛의 실이 표적에서 교차하고, 허리와 어깨를 비스듬히 감아 조인다. 접점에 짧은 금빛 파열이 맺힌다.',
           'silhouette': '가늘고 긴 비스듬한 교차 결속',
           'sources': ['Primary RibbonTrail', 'Ultimate Main Flames', 'Sparks', 'NoxGlowStrip']},
    'S5': {'label': '솟아오르는 불꽃 결속',
           'shape': '짧은 불꽃 씨앗이 닿으면 발밑 여섯 곳에서 황금 화염편이 솟고, 윗부분이 안쪽으로 말려 표적을 조인다.',
           'silhouette': '아래가 넓고 위에서 안으로 닫히는 여섯 화염줄기',
           'sources': ['Ultimate Flames2', 'Ultimate Main Flames', 'Primary RibbonTrail', 'NoxGlowStrip']},
    'S6': {'label': '금편 압축 잠금',
           'shape': '작은 금빛 핵이 맞은 뒤 백금 파편이 순간 벌어졌다가 세 갈래 소용돌이로 압축된다. 짧게 끊어진 파편 흐름이 몸통에 남는다.',
           'silhouette': '구형으로 벌어졌다 좁게 뭉치는 끊어진 나선 파편',
           'sources': ['Ultimate Flames2', 'Ultimate SparkTrailHeads', 'Primary RibbonTrail', 'NoxGlowStrip']},
}
OPTIONS = tuple(DESIGNS)


def write(out, name, data):
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out)/name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def author(out):
    rows = []
    paths = {**_BASE['_PART']['SOURCES'], 'ribbon': TRAIL,
             'soft_line': _BASE['MATERIALS']['soft_line'],
             'soft_dot': _BASE['MATERIALS']['soft_dot'], 'plane': '/Engine/BasicShapes/Plane'}
    for key, path in paths.items():
        asset = unreal.load_asset(path)
        assert asset, path
        rows.append({'key': key, 'path': asset.get_path_name(), 'class': asset.get_class().get_name()})
    result = {'passed': True, 'sources': rows, 'designs': DESIGNS,
              'assets_saved': False, 'production_changed': False, 'installed': False,
              'source_particle_parameters_unchanged': True,
              'native_contract': 'Native S retains one 12-damage hit and its original two-second root/AI lease.',
              'limitation': 'Only the render layer differs. No new target, AI or damage behavior is authored.'}
    write(out, 'binding-reforged-sources.json', result)
    return result


class Study(NativeStudy):
    def __init__(self, rig, option, target):
        # The rejected physical props are deliberately not constructed.
        BaseStudy.__init__(self, rig, option)
        self.target = target
        self.native, self.native_birth = None, None
        self.hidden, self.hidden_paths = [], set()
        self.commit_seen = False
        self.particle_samples, self.ribbons, self.motion = [], [], []
        self.last_detail, self.last_texture = -10., -10.
        self.last_flight_texture = -10.
        self.trail_asset = unreal.load_asset(TRAIL)
        self.flight = [self.light('flight_'+str(i), platinum=i == 1) for i in range(3)]
        self.flight_core = self.dot('flight_core')
        if option == 'S4':
            self.paths = [[self.light('cross_'+str(i)+'_'+str(j), platinum=i == 1)
                           for j in range(24)] for i in range(3)]
        elif option == 'S5':
            self.paths = [[self.light('rising_'+str(i)+'_'+str(j), platinum=i % 2 == 0)
                           for j in range(12)] for i in range(6)]
        else:
            self.paths = [[self.light('vortex_'+str(i)+'_'+str(j), platinum=j % 3 == 0)
                           for j in range(7)] for i in range(3)]
            self.fragments = [self.light('fragment_'+str(i), platinum=i % 3 != 0) for i in range(12)]
        # Native ribbon noise is useful around the bound target, but its large
        # initial offsets read as zigzag wire during this very short flight.
        # Allocate those hold-only emitters at arrival, never at the bow.

    def light(self, name, platinum=False):
        row = self.plane('soft_line', name)
        row['actor'].set_editor_property('tags', [unreal.Name(TAG)])
        row['mesh'].set_editor_property('component_tags', [unreal.Name(TAG)])
        row['mid'].set_vector_parameter_value('CoreColor', unreal.LinearColor(
            1.0, .96 if platinum else .71, .78 if platinum else .21, 1.0))
        row['mid'].set_vector_parameter_value('GlowColor', unreal.LinearColor(1., .56, .10, 1.))
        row['mid'].set_scalar_parameter_value('CoreSharpness', 3.5)
        return row

    def dot(self, name):
        row = self.plane('soft_dot', name)
        row['actor'].set_editor_property('tags', [unreal.Name(TAG)])
        row['mesh'].set_editor_property('component_tags', [unreal.Name(TAG)])
        row['mid'].set_vector_parameter_value('Color', unreal.LinearColor(1., .85, .48, 1.))
        return row

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1.):
        particle = NativeStudy.pulse(self, key, names, position, rotation, scale, seconds, speed)
        particle.set_editor_property('component_tags', [unreal.Name(TAG)])
        # Component-tag changes may reregister a PSC. Apply the live mask last.
        particle.activate(True)
        for name in _BASE['_PART']['EMITTERS'][key]:
            particle.set_emitter_enable(name, name in names)
        return particle

    def ribbon(self, position, width):
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.trail_asset, position, unreal.Rotator(),
            unreal.Vector(1., width, width), False, unreal.PSCPoolMethod.NONE, False)
        assert particle, TRAIL
        self.effects.append((particle, self.now()+3.2))
        self.created += 1
        direct = next(getattr(unreal.ParticleSystemLODMethod, name)
                      for name in dir(unreal.ParticleSystemLODMethod) if 'DIRECT' in name.upper())
        particle.set_editor_property('component_tags', [unreal.Name(TAG)])
        particle.set_editor_property('override_lod_method', True)
        particle.set_editor_property('lod_method', direct)
        particle.set_editor_property('custom_time_dilation', 1.35)
        particle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        particle.set_editor_property('generate_overlap_events', False)
        particle.activate(True)
        for name in TRAIL_NAMES:
            particle.set_emitter_enable(name, name == 'RibbonTrail')
        return particle

    def draw(self, row, start, end, width, strength):
        self.soft_line(row, start, end, width, strength)
        row['mesh'].set_visibility(strength > .005)

    def crossed(self, index, u, age):
        center = self.target.get_actor_location()
        closing = smooth((age-ARRIVAL)/.30)
        radius = 106.-48.*closing
        # An inclined incomplete loop leaves the target visible between three strands.
        theta = (u*1.70-.85)*math.pi+index*2.094+age*.17
        axis = self.right*math.cos(index*1.9)+self.forward*math.sin(index*1.9)
        return center+axis*(math.cos(theta)*radius)+self.up*(math.sin(theta)*radius*.93)+self.forward*(math.sin(theta)*20.)

    def rising(self, index, u, age):
        center = self.target.get_actor_location()
        closing = smooth((age-ARRIVAL)/.38)
        theta = index*math.pi/3.+.16*math.sin(age*2.+index)
        radial = self.forward*math.cos(theta)+self.right*math.sin(theta)
        radius = (94.-28.*closing)*(1.-.74*u)+math.sin(u*math.pi)*(24.-10.*closing)
        return center+radial*radius+self.up*(-76.+u*(166.+12.*math.sin(age*3.+index)))

    def vortex(self, index, u, age):
        center = self.target.get_actor_location()
        spread = smooth((age-ARRIVAL)/.16)*(1.-smooth((age-.43)/.34))
        radius = 43.+69.*spread
        theta = index*2.094+u*3.4-age*3.6
        return center+self.forward*(math.cos(theta)*radius)+self.right*(math.sin(theta)*radius)+self.up*((u-.5)*116.)

    def flight_update(self, age):
        progress = clamp(age/ARRIVAL)
        target = self.target.get_actor_location()
        direction = _SIGN['unit'](target-self.origin)
        active = (1.-smooth((age-ARRIVAL)/.05))*smooth(age/.05)
        center = self.origin+(target-self.origin)*progress
        for i, row in enumerate(self.flight):
            side = i-1
            if self.option == 'S4':
                # One platinum needle leads; the two thin threads end behind
                # it rather than making three equal prongs at the same depth.
                p = center+self.right*(side*6.)-direction*(15. if side else 0.)
                size, width = (66., 4.2) if side == 0 else (36., 2.3)
                strength = .90 if side == 0 else .42
            elif self.option == 'S5':
                p = center+self.right*(side*3.)-direction*abs(side)*7.
                size, width = (29., 8.5) if side == 0 else (14., 4.)
                strength = .42 if side == 0 else .24
            else:
                # A compact staggered dart bundle; no orbit or moving side-to-
                # side ribbon that could produce an angular corkscrew.
                p = center+self.right*(side*7.)-direction*(abs(side)*11.)+self.up*(side*2.)
                size, width = (33., 4.5) if side == 0 else (22., 3.8)
                strength = .82 if side == 0 else .66
            self.draw(row, p-direction*size, p, width, active*strength)
        self.soft_dot(self.flight_core, center, 7. if self.option == 'S5' else 3.5,
                      active*(.52 if self.option == 'S5' else .22))
        if self.option == 'S5' and .015 < age < ARRIVAL and age-self.last_flight_texture > .055:
            self.last_flight_texture = age
            self.pulse('impact', ('Main Flames',), center-direction*9.,
                       unreal.MathLibrary.make_rot_from_x(direction), (.43, .23, .23), .15, 1.8)
        if age >= ARRIVAL and not self.ribbons:
            for i in range(3):
                if self.option == 'S4':
                    point = self.crossed(i, (age*1.8+i*.31)%1., age)
                elif self.option == 'S5':
                    point = self.rising(i*2, (age*2.1+i*.25)%1., age)
                else:
                    point = self.vortex(i, (age*1.4+i*.2)%1., age)
                self.ribbons.append(self.ribbon(point, 1.50 if self.option == 'S4' else 1.80))

    def update_s4(self, age, envelope):
        for i, rows in enumerate(self.paths):
            for j, row in enumerate(rows):
                count = len(rows)
                self.draw(row, self.crossed(i, j/count, age), self.crossed(i, (j+1)/count, age),
                          5.5, envelope*(.14+.05*math.sin(age*7.+j*.5)))
            if age >= ARRIVAL and valid(self.ribbons[i]):
                self.ribbons[i].set_world_location(self.crossed(i, (age*1.8+i*.31)%1., age), False, True)
        if age >= ARRIVAL and age < BOUND_END and age-self.last_texture > .14:
            self.last_texture = age
            # Source mesh flames carry the moving, eroding body of each strand.
            # The faint subdivided strip only bridges the textured bursts.
            for i in range(3):
                for k in range(2):
                    u = (.21+k*.44+age*.28+i*.12)%1.
                    start = self.crossed(i, u, age)
                    tangent = self.crossed(i, u+.04, age)-start
                    self.pulse('impact', ('Main Flames',), start,
                               unreal.MathLibrary.make_rot_from_x(tangent),
                               (.88, .45, .45), .40, 1.15)

    def update_s5(self, age, envelope):
        rise = smooth((age-ARRIVAL)/.25)
        for i, rows in enumerate(self.paths):
            for j, row in enumerate(rows):
                count = len(rows)
                head = clamp(rise*1.22-j/count)*5.
                self.draw(row, self.rising(i, j/count, age), self.rising(i, (j+1)/count, age),
                          5., envelope*clamp(head)*.095)
        if age >= ARRIVAL:
            for i, particle in enumerate(self.ribbons):
                if valid(particle):
                    particle.set_world_location(self.rising(i*2, (age*2.1+i*.25)%1., age), False, True)
        if age >= ARRIVAL and age < BOUND_END and age-self.last_texture > .16:
            self.last_texture = age
            # Alternate the source bursts instead of six synchronized hard bars.
            phase = int((age-ARRIVAL)/.16)%2
            for i in range(phase, 6, 2):
                point = self.rising(i, .09, age)
                axis = _SIGN['unit'](self.rising(i, .72, age)-point)
                self.pulse('shards', ('Flames2',), point, unreal.MathLibrary.make_rot_from_z(axis),
                           (.60, .60, 1.16), .50, 1.15)
                tip = self.rising(i, .78, age)
                self.pulse('impact', ('Main Flames',), tip,
                           unreal.MathLibrary.make_rot_from_x(self.target.get_actor_location()-tip),
                           (.65, .35, .35), .38, 1.25)

    def update_s6(self, age, envelope):
        for i, rows in enumerate(self.paths):
            for j, row in enumerate(rows):
                # Gaps are intentional: these are travelling fragments, not complete hoop props.
                self.draw(row, self.vortex(i, j/7., age), self.vortex(i, (j+.56)/7., age),
                          5., envelope*(.11+.06*math.sin(age*8.+j)))
            if age >= ARRIVAL and valid(self.ribbons[i]):
                self.ribbons[i].set_world_location(self.vortex(i, (age*1.4+i*.2)%1., age), False, True)
        center = self.target.get_actor_location()
        spread = smooth((age-ARRIVAL)/.14)*(1.-smooth((age-.42)/.38))
        radius = 49.+87.*spread
        for i, row in enumerate(self.fragments):
            angle = i*math.pi/6.-age*(2.8 if i % 2 else 3.4)
            radial = self.right*math.cos(angle)+self.forward*math.sin(angle)
            p = center+radial*radius+self.up*((i%4-1.5)*24.)
            tangent = self.right*-math.sin(angle)+self.forward*math.cos(angle)
            self.draw(row, p-tangent*(18.+spread*10.), p, 7., envelope*.24)
        if age >= ARRIVAL and age < BOUND_END and age-self.last_texture > .14:
            self.last_texture = age
            for i in range(3):
                u = (.24+age*.52+i*.2)%1.
                p = self.vortex(i, u, age)
                self.pulse('shards', ('Flames2',), p, unreal.MathLibrary.make_rot_from_z(center-p),
                           (.48, .48, .72), .42, 1.35)
                self.pulse('impact', ('SparkTrailHeads', 'Sparks'), p,
                           unreal.MathLibrary.make_rot_from_x(center-p),
                           (.24, .24, .24), .27, 1.4)

    def update(self):
        self.observe()
        age = self.now()-(self.native_birth if self.native_birth is not None else self.born)
        fade = 1.-smooth((age-BOUND_END)/(END-BOUND_END))
        envelope = smooth((age-ARRIVAL)/.13)*fade
        self.flight_update(age)
        getattr(self, 'update_'+self.option.lower())(age, envelope)
        target = self.target.get_actor_location()
        if age >= ARRIVAL and self.once('native_hit_visual_arrival'):
            self.pulse('impact', ('Sparks', 'SparkTrailHeads', 'Main Flames'), target,
                       unreal.Rotator(), (.47, .31, .31), .34, 1.7)
        if age >= BOUND_END and self.once('native_root_expired_visual_release'):
            for particle in self.ribbons:
                if valid(particle):
                    particle.deactivate()
            self.pulse('impact', ('Sparks', 'SparkTrailHeads'), target,
                       unreal.Rotator(), (.43, .43, .43), .31, 1.8)
        if ARRIVAL < age < BOUND_END and age-self.last_detail >= .30:
            self.last_detail = age
            self.pulse('muzzle', ('Sparks',), target+self.right*(34.*math.sin(age*8.)),
                       unreal.Rotator(), (.20, .20, .20), .22, 1.8)
        self.tick()
        self.particle_samples.append({'age': round(age, 4), 'particles': sum(
            p.get_num_active_particles() for p, _ in self.effects if valid(p))})
        return age


def sequence(rig):
    options = [x.strip().upper() for x in os.environ.get(
        'SPARROW_BINDING_REFORGED_OPTIONS', ','.join(OPTIONS)).split(',') if x.strip()]
    rig['check'](bool(options) and len(options) == len(set(options)) and all(x in OPTIONS for x in options),
                 'reforged binding has valid unique options')
    inventory = author(rig['OUT'])
    previous = unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Skills.IgnoreCooldowns')
    report = {'passed': False, 'studies': [], 'sources': inventory['sources'],
              'assets_saved': False, 'production_changed': False, 'installed': False,
              'visual_acceptance': 'pending parent actual viewport review',
              'AI_resume': {'run': False, 'native_lease_code_unchanged': True}}
    try:
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
        for option in options:
            rig['switch']('countess'); yield .15
            rig['switch']('sparrow'); yield .60
            prefix = 'S_reforged_'+option
            rig['case'](prefix)
            targets = rig['layout']([(430, 0), (650, 380), (650, -350)])
            yield .20
            initial = [rig['health'](target) for target in targets]
            study = Study(rig, option, targets[0])
            row = {'id': option, **DESIGNS[option], 'video_prefix': prefix+'_video', 'installed': False}
            moments, samples = [.13, .48, .85, 1.40, 2.45], []
            bound_checked = release_checked = False
            try:
                if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                    rig['STATE']['video_clip'] = {'case': prefix, 'prefix': row['video_prefix'],
                                                 'cast_time': study.now(), 'frame_times': []}
                yield .20
                rig['use']('S', targets[0])
                study.born = study.now()
                while study.now()-study.born < 3.10:
                    age = study.update()
                    if age >= .65 and not bound_checked:
                        rig['check'](valid(study.native) and study.native.has_committed()
                                     and study.native.get_bound_target() == targets[0],
                                     option+' keeps the real native committed S target')
                        rig['check'](abs(initial[0]-rig['health'](targets[0])-12.) < .01
                                     and str(targets[0].get_combat_status()) == 'GOLD_BIND',
                                     option+' preserves one native12damage hit and binding')
                        samples.append({'age': age, 'status': str(targets[0].get_combat_status()),
                                        'damage': initial[0]-rig['health'](targets[0])})
                        bound_checked = True
                    if age >= 2.35 and not release_checked:
                        rig['check'](str(targets[0].get_combat_status()) == 'None',
                                     option+' releases after the original two-second lease')
                        release_checked = True
                    if moments and age >= moments[0]:
                        rig['capture'](prefix+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                    yield 1./rig['FPS']
                rig['finish_video_clip']()
                damage = [hp-rig['health'](target) for hp, target in zip(initial, targets)]
                rig['check'](bound_checked and release_checked and abs(damage[0]-12.) < .01
                             and all(abs(value)<.01 for value in damage[1:]),
                             option+' does not add preview damage or extra targets')
                rig['check'](study.peak_particles > 0, option+' has live original textured particle layers')
                rig['check'](not rig['pawn']().is_combat_busy() and not rig['skills']().is_casting(),
                             option+' preserves player input recovery')
                rig['check'](not valid(study.native), option+' finishes the original sanctuary actor on time')
                row.update(native_damage=damage, samples=samples, native_events=study.events,
                           hidden_components=len(study.hidden), particle_samples=study.particle_samples,
                           peak_particles=study.peak_particles, body_materials_edited=False)
            finally:
                rig['finish_video_clip']()
                row['cleanup'] = study.close()
            rig['check'](not row['cleanup']['failures'] and not rig['tagged'](TAG) and not study.effects,
                         option+' removes every temporary ribbon/plane and restores native visibility')
            report['studies'].append(row)
            write(rig['OUT'], 'binding-reforged-studies.json', report)
        if os.environ.get('SPARROW_BINDING_REFORGED_AI') == '1':
            report['AI_resume'] = yield from _SIGN['ai_boundary'](rig)
        report['passed'] = True
        write(rig['OUT'], 'binding-reforged-studies.json', report)
    finally:
        rig['finish_video_clip']()
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns '+str(previous))
