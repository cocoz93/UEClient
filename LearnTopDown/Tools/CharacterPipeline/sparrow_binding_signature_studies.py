"""Three visual-only signatures around the installed S input/damage/root lease.

NEW_SKILLS_FOCUS=sparrow_feedback, SPARROW_FEEDBACK_PARTS=,
SPARROW_FEEDBACK_STUDIES=sparrow_binding_signature_studies.py.
SPARROW_BINDING_SIGNATURE_OPTIONS=S1,S2,S3; NEW_SKILLS_VIDEO=1.
Optional SPARROW_BINDING_SIGNATURE_AI=1 repeats one short native AI resume check.
No saves, native edits, source material writes, actor hiding or gameplay changes.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_BASE = runpy.run_path(str(Path(__file__).with_name('sparrow_orbit_arsenal_studies.py')))
_SANCT = runpy.run_path(str(Path(__file__).with_name('sparrow_sanctuary_review.py')))
BaseStudy, valid = _BASE['Study'], _BASE['_valid']
clamp, smooth = _BASE['_clamp'], _BASE['_smooth']
TAG = 'SparrowBindingSignatureStudy'
ARRIVAL, BOUND_END, END = .25, 2.25, 2.70
MESHES = {
    'chain': '/Game/MedievalDungeon/Meshes/Props/SM_Decor_Chains_A',
    'cuff': '/Game/MedievalDungeon/Meshes/Props/SM_Handcuff',
    'feather': '/Game/TopDown/Characters/Aurora/FX/Meshes/SM_Aurora_CrystalHawk_WingR',
    'rune': '/Game/TopDown/Characters/Gideon/FX/SM_Rune_Ring_Inner_NoShards',
    'seal': '/Game/ParagonGideon/FX/Meshes/Heroes/Gideon/SM_Ult_Runes_Inner',
}
SURFACES = {
    'gold': '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold',
    'white': '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho',
}
DESIGNS = {
    'S1': {'label': '황금 사슬', 'shape': '입체 쌍사슬이 전진하고 표적의 몸통을 두 방향으로 감아 쇠고리가 조인다.',
           'geometry': '실제 MedievalDungeon 사슬/수갑 형상에 프로젝트의 황금 실루엣 재질 적용'},
    'S2': {'label': '접히는 광깃 족쇄', 'shape': '가는 광깃 세 개가 도착하면 여덟 깃날이 위로 접혀 표적을 가둔다.',
           'geometry': '보유 CrystalHawk의 깃이 갈라진 날개 부위 메시를 가늘게 정규화'},
    'S3': {'label': '백금 봉인문장', 'shape': '짧은 입체 문장 투사체 뒤에 위아래 인장이 마주 닫히고 작은 문자 잠금이 둘러선다.',
           'geometry': '실제 Gideon 분리 룬 메시와 금속/백금 실루엣 재질'},
}
OPTIONS = tuple(DESIGNS)


def write(out, name, data):
    (Path(out) / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def xyz(v):
    return [v.x, v.y, v.z]


def cross(a, b):
    return unreal.Vector(a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x)


def dot(a, b):
    return a.x*b.x+a.y*b.y+a.z*b.z


def unit(v):
    length = math.sqrt(dot(v, v))
    return v / max(length, .00001)


def author(out):
    Path(out).mkdir(parents=True, exist_ok=True)
    rows = []
    for key, path in {**MESHES, **SURFACES, **_BASE['_PART']['SOURCES']}.items():
        asset = unreal.load_asset(path)
        assert asset, path
        row = {'key': key, 'path': asset.get_path_name(), 'class': asset.get_class().get_name()}
        if key in MESHES:
            box = asset.get_bounding_box()
            row['bounds'] = {'min': xyz(box.min), 'max': xyz(box.max)}
        if key == 'white':
            names = {str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset)}
            assert 'Visibility' in names, (path, sorted(names))
        rows.append(row)
    result = {'passed': True, 'assets_saved': False, 'production_changed': False,
              'sources': rows, 'designs': DESIGNS,
              'particle_mask': ['Sparks', 'SparkTrailHeads'], 'wisps_or_smoke': False,
              'native_contract': 'Actual S: one 12-damage hit, 2-second lease and original AI resume remain native.'}
    write(out, 'binding-signature-sources.json', result)
    return result


class Study(BaseStudy):
    def __init__(self, rig, option, target):
        super().__init__(rig, option)
        self.materials.update({key: unreal.load_asset(path) for key, path in SURFACES.items()})
        self.meshes = {key: unreal.load_asset(path) for key, path in MESHES.items()}
        self.target = target
        self.native, self.native_birth = None, None
        self.hidden, self.hidden_paths = [], set()
        self.commit_seen = False
        self.parts, self.particle_samples = [], []
        self.last_spark = -10.
        self.entry_spark, self.exit_spark = False, False
        if option == 'S1':
            self.chains = [[self.prop('chain', 'white' if i % 2 == 0 else 'gold', 'chain')
                            for i in range(8)] for _ in range(2)]
            self.cuffs = [self.prop('cuff', 'gold', 'cuff') for _ in range(2)]
        elif option == 'S2':
            self.flight = [self.prop('feather', 'white' if i == 1 else 'gold', 'flying_quill') for i in range(3)]
            self.feathers = [self.prop('feather', 'white' if i % 3 == 0 else 'gold', 'folding_quill') for i in range(8)]
        else:
            self.flight = [self.prop('rune', 'white', 'platinum_seal')]
            self.seals = [self.prop('seal', 'gold' if i == 0 else 'white', 'opposed_seal') for i in range(2)]
            self.locks = [self.prop('rune', 'white' if i % 2 else 'gold', 'glyph_lock') for i in range(4)]

    def prop(self, key, material, label):
        row = self.plane(material, label)
        row['mesh'].set_static_mesh(self.meshes[key])
        row['actor'].set_editor_property('tags', [unreal.Name(TAG)])
        row['mesh'].set_editor_property('component_tags', [unreal.Name(TAG)])
        row['mesh'].set_visibility(False)
        for slot in range(max(1, row['mesh'].get_num_materials())):
            row['mesh'].set_material(slot, row['mid'])
        if material == 'white':
            row['mid'].set_vector_parameter_value('BodyTint', unreal.LinearColor(1.4, 1.19, .76, 1.))
            row['mid'].set_scalar_parameter_value('Visibility', 1.)
        box = self.meshes[key].get_bounding_box()
        size = [max(.1, b-a) for a, b in zip(xyz(box.min), xyz(box.max))]
        row.update(size=size, center=(box.min+box.max)*.5, material_key=material)
        row['long'], row['wide'], row['normal'] = sorted(range(3), key=lambda i: size[i], reverse=True)
        self.parts.append(row)
        return row

    def pose(self, row, point, direction, length, width, depth, strength=1., twist=0.):
        strength = clamp(strength)
        row['mesh'].set_visibility(strength > .005)
        if strength <= .005:
            return
        forward = unit(direction)
        hint = self.up if abs(dot(forward, self.up)) < .92 else self.forward
        side = unit(cross(hint, forward))
        radians = math.radians(twist)
        side = side*math.cos(radians)+cross(forward, side)*math.sin(radians)
        axes = [None, None, None]
        axes[row['long']], axes[row['wide']], axes[row['normal']] = forward, side, cross(forward, side)
        if dot(cross(axes[0], axes[1]), axes[2]) < 0:
            axes[row['normal']] = axes[row['normal']] * -1.
        scale = [0., 0., 0.]
        for index, desired in zip((row['long'], row['wide'], row['normal']), (length, width, depth)):
            scale[index] = desired*math.sqrt(strength)/row['size'][index]
        offset = sum((axes[i]*(xyz(row['center'])[i]*scale[i]) for i in range(3)), unreal.Vector())
        row['actor'].set_actor_location_and_rotation(point-offset, unreal.MathLibrary.make_rot_from_xy(axes[0], axes[1]), False, True)
        row['mesh'].set_world_scale3d(unreal.Vector(*scale))
        if row['material_key'] == 'white':
            row['mid'].set_scalar_parameter_value('Visibility', strength)

    def segment(self, row, a, b, width, depth, strength=1., twist=0.):
        delta = b-a
        self.pose(row, (a+b)*.5, delta, math.sqrt(dot(delta, delta)), width, depth, strength, twist)

    def hide(self, component):
        path = component.get_path_name()
        if path not in self.hidden_paths:
            self.hidden_paths.add(path)
            self.hidden.append((component, component.is_visible()))
        component.set_visibility(False)

    def observe(self):
        for actor in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowSanctuary):
            if actor.get_owner() != self.rig['pawn']() or actor.get_bound_target() != self.target:
                continue
            if self.native is None:
                self.native = actor
                self.native_birth = self.now() - (BOUND_END-actor.get_remaining_seconds())
                self.events.append({'event': 'actual_native_S', 'target': self.target.get_name(),
                                    'native': actor.get_name(), 'hidden_scope': 'render components only'})
            self.commit_seen = self.commit_seen or actor.has_committed()
            for component in actor.get_components_by_class(unreal.MeshComponent):
                self.hide(component)
        # Native impact PSCs are world-owned, but their explicit tag identifies the same S/F renderer.
        # This study casts S only. Do not stop the particle simulation, damage actor or root timer.
        for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if valid(particle) and 'SparrowSanctuaryPulse' in {str(t) for t in particle.get_editor_property('component_tags')}:
                self.hide(particle)

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1.):
        # Editor property writes can reregister an inactive-by-default PSC.
        # Set this study's tag before Activate, then mask the live emitters last.
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.templates[key], position, rotation,
            unreal.Vector(*scale), False, unreal.PSCPoolMethod.NONE, False)
        assert particle, (key, names)
        self.effects.append((particle, self.now()+seconds))
        self.created += 1
        direct = next(getattr(unreal.ParticleSystemLODMethod, name)
                      for name in dir(unreal.ParticleSystemLODMethod) if 'DIRECT' in name.upper())
        particle.set_editor_property('component_tags', [unreal.Name(TAG)])
        particle.set_editor_property('override_lod_method', True)
        particle.set_editor_property('lod_method', direct)
        particle.set_editor_property('custom_time_dilation', speed)
        particle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        particle.set_editor_property('generate_overlap_events', False)
        particle.activate(True)
        for name in _BASE['_PART']['EMITTERS'][key]:
            particle.set_emitter_enable(name, name in names)
        return particle

    def chain_point(self, strand, u, age):
        target = self.target.get_actor_location()
        if age < ARRIVAL:
            tip = self.origin+(target-self.origin)*clamp(age/ARRIVAL)
            wave = self.right*(strand*19.*math.sin(u*math.pi)) + self.up*(16.*math.sin(u*math.pi))
            return self.origin+(tip-self.origin)*u+wave
        contract = smooth((age-ARRIVAL)/.30)
        release = smooth((age-BOUND_END)/.42)
        radius = 98.-35.*contract+48.*release
        theta = u*math.pi*2.2+strand*math.pi*.5+age*.35
        return target+self.forward*(math.cos(theta)*radius)+self.right*(math.sin(theta)*radius)+self.up*(-62.+u*135.+release*30.)

    def update_chain(self, age, fade):
        for strand, rows in zip((-1., 1.), self.chains):
            for i, row in enumerate(rows):
                self.segment(row, self.chain_point(strand, i/8., age), self.chain_point(strand, (i+1)/8., age),
                             19.5, 15., fade*smooth(age/.07), i%2*90.)
        lock = smooth((age-ARRIVAL)/.22)*fade
        for i, row in enumerate(self.cuffs):
            self.pose(row, self.target.get_actor_location()+self.right*((i*2-1)*46.)+self.up*(12.+i*24.),
                      self.up, 82.*2./3., 55.*2./3., 22.*2./3., lock, i*90.+age*4.)

    def update_feathers(self, age, fade):
        target = self.target.get_actor_location()
        travel = clamp(age/ARRIVAL)
        direction = unit(target-self.origin)
        for i, row in enumerate(self.flight):
            point = self.origin+(target-self.origin)*travel+self.right*((i-1)*14.)+self.up*(10.*math.sin(travel*math.pi))
            self.pose(row, point, direction, 98.-abs(i-1)*24., 17., 7., fade if age < ARRIVAL else 0., i*29.)
        closing = smooth((age-ARRIVAL)/.32)
        released = smooth((age-BOUND_END)/.42)
        for i, row in enumerate(self.feathers):
            theta = i*math.pi/4.+.12*math.sin(age*2.)
            radial = self.forward*math.cos(theta)+self.right*math.sin(theta)
            base = target+radial*(102.-43.*closing+released*55.)-self.up*47.
            axis = radial*(1.-1.27*closing)+self.up*(.20+.80*closing)
            point = base+unit(axis)*54.+self.up*(released*35.)
            self.pose(row, point, axis, 118., 34., 10., fade*smooth((age-.20)/.17), i%2*17.-8.)

    def update_seals(self, age, fade):
        target = self.target.get_actor_location()
        progress = clamp(age/ARRIVAL)
        self.pose(self.flight[0], self.origin+(target-self.origin)*progress+self.up*8., self.up,
                  64., 64., 10., fade if age < ARRIVAL else 0., age*500.)
        closing = smooth((age-ARRIVAL)/.25)
        release = smooth((age-BOUND_END)/.42)
        for i, row in enumerate(self.seals):
            sign = -1. if i == 0 else 1.
            height = sign*(132.-46.*closing+release*65.)
            angle = math.radians(i*180.+age*(16. if i == 0 else -18.))
            heading = self.forward*math.cos(angle)+self.right*math.sin(angle)
            self.pose(row, target+self.up*height, heading, 205., 205., 18.,
                      fade*smooth((age-.20)/.12), sign*8.)
        for i, row in enumerate(self.locks):
            theta = i*math.pi/2.
            radial = self.forward*math.cos(theta)+self.right*math.sin(theta)
            point = target+radial*(85.-24.*closing+release*35.)+self.up*(i%2*34.-17.)
            self.pose(row, point, self.up, 54., 42., 10., fade*smooth((age-.25)/.15), i*90.)

    def update(self):
        self.observe()
        age = self.now()-(self.native_birth if self.native_birth is not None else self.born)
        fade = 1.-smooth((age-BOUND_END)/(END-BOUND_END))
        if self.option == 'S1': self.update_chain(age, fade)
        elif self.option == 'S2': self.update_feathers(age, fade)
        else: self.update_seals(age, fade)
        if age >= ARRIVAL and not self.entry_spark:
            self.entry_spark = True
            self.pulse('impact', ('Sparks', 'SparkTrailHeads'), self.target.get_actor_location(), unreal.Rotator(),
                       (.52, .52, .52), .34, 1.8)
        if age >= BOUND_END and not self.exit_spark:
            self.exit_spark = True
            self.pulse('impact', ('Sparks', 'SparkTrailHeads'), self.target.get_actor_location(), unreal.Rotator(),
                       (.62, .62, .62), .32, 2.0)
        if .55 < age < 2.12 and age-self.last_spark >= .36:
            self.last_spark = age
            radial = self.right*math.cos(age*7.)+self.up*math.sin(age*7.)
            self.pulse('muzzle', ('Sparks',), self.target.get_actor_location()+radial*54., unreal.Rotator(),
                       (.22, .22, .22), .22, 1.8)
        self.tick()
        self.particle_samples.append({'age': age, 'particles': sum(p.get_num_active_particles() for p, _ in self.effects if valid(p))})
        return age

    def close(self):
        restored = 0
        for component, visible in self.hidden:
            if valid(component):
                component.set_visibility(visible)
                restored += 1
        self.hidden.clear()
        failures = super().close()
        return {'restored_components': restored, 'failures': failures}


def ai_boundary(rig):
    """Optional one-case reuse of the existing native AI fixture; no visual recording."""
    rig['switch']('countess'); yield .15
    rig['switch']('sparrow'); yield .60
    rig['case']('S_signature_AI_resume')
    rig['layout']([(1800, 700), (1800, -700), (1600, 900)])
    yield .20
    origin = rig['pawn']().get_actor_location()
    nav = []
    for x in (430., 550.):
        rig['ground'](origin.x+x, origin.y)
        nav.append(json.loads((Path(rig['OUT'])/'new-skills-ground.json').read_text(encoding='utf-8-sig')))
    rig['check'](all(n['navigation_projected'] for n in nav), 'signature AI fixture has valid start and goal navigation')
    start, goal = nav[0]['nav'], nav[1]['nav']
    before = {a.get_path_name() for a in unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'SparrowSanctuaryQAMovement')}
    fixtures = []
    try:
        token = 'binding_signature_AI'
        rig['cmd'](f'SparrowSanctuaryQA.Movement {token} {start["x"]} {start["y"]} {start["z"]+90.} {goal["x"]} {goal["y"]} {goal["z"]}')
        native = json.loads((Path(rig['OUT'])/(token+'.json')).read_text(encoding='utf-8-sig'))
        fixtures = [a for a in unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'SparrowSanctuaryQAMovement') if a.get_path_name() not in before]
        target = next(a for a in fixtures if a.actor_has_tag(token))
        target.get_editor_property('character_movement').set_editor_property('max_walk_speed', 20.)
        rig['check'](native['path_status'] == 3 and native['tick_enabled'], 'signature AI starts with active native path')
        rig['use']('S', target)
        yield .5
        paused = _SANCT['_state'](rig, 'binding_signature_AI_paused')['movement'][0]
        rig['check'](not paused['tick_enabled'] and paused['path_status'] == 2 and paused['request_id'] == native['request_id'], 'signature S pauses the same AI request')
        fixed = target.get_actor_location()
        yield .45
        rig['check']((target.get_actor_location()-fixed).length() < .1, 'signature native binding retains movement lock')
        yield 1.45
        restored = _SANCT['_state'](rig, 'binding_signature_AI_restored')['movement'][0]
        rig['check'](restored['tick_enabled'] and restored['path_status'] == 3 and restored['request_id'] == native['request_id'], 'signature S expiry restores the same AI request')
        point = target.get_actor_location()
        yield .15
        rig['check']((target.get_actor_location()-point).length() > .1, 'signature restored native AI moves again')
        return {'passed': True, 'initial': native, 'paused': paused, 'restored': restored}
    finally:
        rig['switch']('countess')
        for actor in fixtures:
            if valid(actor): actor.destroy_actor()


def sequence(rig):
    options = [x.strip().upper() for x in os.environ.get('SPARROW_BINDING_SIGNATURE_OPTIONS', ','.join(OPTIONS)).split(',') if x.strip()]
    rig['check'](bool(options) and len(options) == len(set(options)) and all(x in OPTIONS for x in options), 'binding signatures have valid unique options')
    inventory = author(rig['OUT'])
    previous = unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Skills.IgnoreCooldowns')
    report = {'passed': False, 'studies': [], 'sources': inventory['sources'], 'assets_saved': False,
              'production_changed': False, 'installed': False, 'visual_acceptance': 'pending parent actual viewport review',
              'AI_resume': {'run': False, 'native_lease_code_unchanged': True}}
    try:
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
        for option in options:
            rig['switch']('countess'); yield .15
            rig['switch']('sparrow'); yield .60
            rig['case']('S_signature_'+option)
            targets = rig['layout']([(430, 0), (650, 380), (650, -350)])
            yield .20
            initial = [rig['health'](d) for d in targets]
            study = Study(rig, option, targets[0])
            row = {'id': option, **DESIGNS[option], 'video_prefix': 'S_signature_'+option+'_video', 'installed': False}
            moments, samples = [.13, .48, 1.25, 2.45], []
            bound_checked = release_checked = False
            try:
                if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                    rig['STATE']['video_clip'] = {'case': 'S_signature_'+option, 'prefix': row['video_prefix'],
                                                 'cast_time': study.now(), 'frame_times': []}
                yield .20
                rig['use']('S', targets[0])
                study.born = study.now()
                while study.now()-study.born < 3.10:
                    age = study.update()
                    if age >= .65 and not bound_checked:
                        rig['check'](valid(study.native) and study.native.has_committed() and study.native.get_bound_target() == targets[0], option+' keeps one real committed S target')
                        rig['check'](abs(initial[0]-rig['health'](targets[0])-12.) < .01 and str(targets[0].get_combat_status()) == 'GOLD_BIND', option+' preserves native12damage and binding')
                        samples.append({'age': age, 'status': str(targets[0].get_combat_status()), 'damage': initial[0]-rig['health'](targets[0])})
                        bound_checked = True
                    if age >= 2.35 and not release_checked:
                        rig['check'](str(targets[0].get_combat_status()) == 'None', option+' releases binding after the original two-second lease')
                        release_checked = True
                    if moments and age >= moments[0]:
                        rig['capture']('S_signature_'+option+'_t'+str(round(moments.pop(0)*100)).zfill(3))
                    yield 1./rig['FPS']
                rig['finish_video_clip']()
                damage = [h-rig['health'](d) for h, d in zip(initial, targets)]
                rig['check'](bound_checked and release_checked and abs(damage[0]-12.) < .01 and all(abs(d)<.01 for d in damage[1:]), option+' adds no preview damage or extra targets')
                rig['check'](study.peak_particles > 0, option+' has live original spark particles without Wisps')
                rig['check'](not rig['pawn']().is_combat_busy() and not rig['skills']().is_casting(), option+' restores player input after native recovery')
                rig['check'](not valid(study.native), option+' finishes the original sanctuary actor on time')
                row.update(native_damage=damage, samples=samples, native_events=study.events,
                           hidden_components=len(study.hidden), particle_samples=study.particle_samples,
                           peak_particles=study.peak_particles, body_materials_edited=False)
            finally:
                rig['finish_video_clip']()
                row['cleanup'] = study.close()
            rig['check'](not row['cleanup']['failures'] and not rig['tagged'](TAG) and not study.effects, option+' cleans all temporary props and restores native visibility')
            report['studies'].append(row)
            write(rig['OUT'], 'binding-signature-studies.json', report)
        if os.environ.get('SPARROW_BINDING_SIGNATURE_AI') == '1':
            report['AI_resume'] = yield from ai_boundary(rig)
        report['passed'] = True
        write(rig['OUT'], 'binding-signature-studies.json', report)
    finally:
        rig['finish_video_clip']()
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns '+str(previous))
