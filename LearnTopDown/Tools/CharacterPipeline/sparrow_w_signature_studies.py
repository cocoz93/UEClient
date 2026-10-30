"""Three distinct W signatures in actual PIE; no production or asset writes.

SPARROW_W_SIGNATURE_OPTIONS=W1,W2,W3 filters the normal sequence(rig) hook.
Each 3.6-second clip contains two real W casts and exactly two native 35 hits.
The extra beams/needles/opening arcs are collision-free visual props only.
The parent owns editor/GPU execution and decides actual visual acceptance.
"""
import json
import math
import os
from pathlib import Path
import runpy

import unreal


_LUM = runpy.run_path(str(Path(__file__).with_name('sparrow_luminous_revision_studies.py')))
_ORBIT = _LUM['_BASE']
BaseStudy, valid = _ORBIT['Study'], _LUM['valid']
clamp, smooth = _LUM['clamp'], _LUM['smooth']
OPTIONS = ('W1', 'W2', 'W3')
SIGNATURE_VERSION = 2
DESIGNS = {
    'W1': {
        'label': '백금 압축선',
        'shape': '얇은 직선이 발사 경로를 순간 연결하고, 각진 V자 압축흔적 두 쌍이 옆으로 벌어진 뒤 잘린다.',
        'signature': 'long straight axis / two angular chevron wakes / no native rings',
        'representative_after_native_release': [.10, .25, .45],
    },
    'W2': {
        'label': '삼중 광침 점사',
        'shape': '작은 광침 15개가 5개씩 세 층으로 순차 출발한다. 가는 침과 짧은 발광점이 분리되어 보인다.',
        'signature': 'three optical banks at 0 / .12 / .24 seconds, five needles each',
        'representative_after_native_release': [.10, .25, .45],
        'limitation': '추가 광침은 시각 소품이다. 실제 W 발수·피해·속도는 늘리지 않는다.',
    },
    'W3': {
        'label': '분절 후광 개방',
        'shape': '두 위치의 짧고 두꺼운 백금 arc가 금색 안쪽선과 세 겹을 이루고 좌우로 갈라진다.',
        'signature': 'two opening gates / six chunky segments with three contrasting arc layers / short central arrow',
        'representative_after_native_release': [.10, .25, .45],
    },
}
HIDE_RELEASE_TAGS = {'SparrowReleasePressure', 'SparrowReleaseShards', 'SparrowPiercingReleaseFeathers'}


def write(out, name, data):
    _LUM['write'](out, name, data)


def author(out):
    """Only inspect existing assets and exposed APIs; never compile or save."""
    paths = {key: _ORBIT['MATERIALS'][key] for key in ('soft_line', 'soft_dot')}
    paths.update({'gold': _LUM['GOLD'], 'arrow': _LUM['ARROW'],
                  'plane': '/Engine/BasicShapes/Plane', 'native_impact': _LUM['_PART']['SOURCES']['impact']})
    rows = []
    for key, path in paths.items():
        asset = unreal.load_asset(path)
        assert asset, path
        row = {'key': key, 'path': asset.get_path_name(), 'class': asset.get_class().get_name()}
        if key in ('soft_line', 'soft_dot'):
            names = [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset)]
            assert ('CoreIntensity' if key == 'soft_line' else 'Intensity') in names, (key, names)
            row['scalar_parameters'] = names
        rows.append(row)
    for method in ('get_distance_travelled', 'get_flight_direction', 'get_flight_speed',
                   'get_target_impact_emitter_names', 'is_piercing', 'passes_world'):
        assert hasattr(unreal.SparrowArrow, method), method
    result = {'passed': True, 'sources': rows, 'designs': DESIGNS, 'signature_version': SIGNATURE_VERSION,
              'assets_saved': False, 'production_changed': False,
              'native_contract': '35 damage, 4000 cm/s, piercing and original six-layer impact retained',
              'preview_scope': 'temporary visibility/MIDs and collision-free line/point props only',
              'synchronization': 'release origin and age reconstructed from native distance/speed; observation is frame-quantized'}
    write(out, 'W-signature-sources.json', result)
    return result


def cross(a, b):
    return unreal.Vector(a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x)


class Study(BaseStudy):
    # Reuse the already exercised visibility snapshot operation, not a copy
    # of the full twelve-option study or its unrelated bird/wing assets.
    def hide(self, component):
        _LUM['Study'].hide(self, component)
        # ShotWave::Tick writes visibility again every frame. Reapply only
        # this preview override while retaining its first restoration value.
        component.set_visibility(False)

    def __init__(self, rig, option, targets):
        super().__init__(rig, option)
        self.targets = targets
        self.materials['gold'] = unreal.load_asset(_LUM['GOLD'])
        self.hidden, self.w_materials, self.w_arrows = [], [], []
        self.hidden_paths, self.seen = set(), set()
        self.hidden_actors = {}
        self.impact_seen, self.live_impact = False, False
        self.preparations, self.signature_samples = [], []
        self.native_samples, self.pending_captures = [], []
        self.visible_strokes, self.max_visible_strokes = 0, 0

    def lines(self, count, label):
        rows = [self.plane('soft_line', label+'_'+str(i)) for i in range(count)]
        for row in rows:
            row['mid'].set_scalar_parameter_value('CoreSharpness', 8.)
            row['mid'].set_scalar_parameter_value('GlowSoftness', 2.)
            row['mid'].set_vector_parameter_value('CoreColor', unreal.LinearColor(1., .96, .77, 1.))
            row['mid'].set_vector_parameter_value('GlowColor', unreal.LinearColor(1., .69, .18, 1.))
        return rows

    def line(self, row, start, end, width, strength):
        self.soft_line(row, start, end, width, strength)
        # Narrow optical edges, never a broad fuzzy aura around the shaft.
        row['mid'].set_scalar_parameter_value('GlowIntensity', max(0., strength)*.065)
        if strength > .025:
            self.visible_strokes += 1

    def silence(self, rows):
        for row in rows:
            if valid(row['actor']):
                row['mid'].set_scalar_parameter_value(row['parameter'], 0.)
                if row['parameter'] == 'CoreIntensity':
                    row['mid'].set_scalar_parameter_value('GlowIntensity', 0.)

    def prepare_cast(self):
        count = {'W1': 2, 'W2': 5, 'W3': 4}[self.option]
        self.preparations.append({'born': self.now(), 'release': None,
                                  'parts': self.lines(count, 'preparation')})

    def observe_w(self, arrow):
        if arrow.get_path_name() in self.seen:
            return
        # This records original shaft material/visibility and verifies the
        # native 1.1-wide arrow plus the exact six impact emitter names.
        _LUM['Study'].observe_w(self, arrow)
        item = self.w_arrows[-1]
        for row in item['parts']:
            if valid(row['actor']):
                row['actor'].destroy_actor()
        speed, distance = arrow.get_flight_speed(), arrow.get_distance_travelled()
        assert abs(speed-4000.) < .01 and arrow.is_piercing() and arrow.passes_world()
        direction = arrow.get_flight_direction()
        origin = arrow.get_actor_location()-direction*distance
        right = unreal.Vector(-direction.y, direction.x, 0.)
        right = right/max(.001, right.length())
        item.update({'born': self.now()-distance/speed, 'origin': origin, 'direction': direction,
                     'right': right, 'up': cross(direction, right),
                     'length': min(640., max(320., (self.targets[0].get_actor_location()-origin).length())),
                     'parts': self.lines({'W1': 9, 'W2': 15, 'W3': 73}[self.option], 'signature'),
                     'dots': [self.plane('soft_dot', 'needle_tip_'+str(i)) for i in range(15)] if self.option == 'W2' else [],
                     'retired': False, 'last_hit_count': 0})
        if self.option == 'W1':
            for row in item['parts'][1:]:
                row['mid'].set_scalar_parameter_value('CoreSharpness', 4.5)
        elif self.option == 'W3':
            colors = ((1., .96, .76, 1.), (1., .53, .06, 1.), (1., .73, .24, 1.))
            for gate in range(2):
                for layer, color in enumerate(colors):
                    for segment in range(12):
                        row = item['parts'][1+gate*36+layer*12+segment]
                        row['mid'].set_scalar_parameter_value('CoreSharpness', 3.2)
                        row['mid'].set_vector_parameter_value('CoreColor', unreal.LinearColor(*color))
        prep = next(p for p in self.preparations if p['release'] is None)
        prep['release'] = item['born']
        ordinal = len(self.w_arrows)
        self.native_samples.append({'shot': ordinal, 'speed': speed, 'piercing': True,
                                    'passes_world': True, 'observed_distance_cm': distance,
                                    'observed_release_age': distance/speed})
        if ordinal == 1:
            self.pending_captures.extend((item['born']+delay, delay) for delay in
                                         DESIGNS[self.option]['representative_after_native_release'])

    def suppress_shared_release(self):
        # ShotWave includes large static planes as well as independently
        # spawned PSCs. Hide both only for this comparison; leave impact alone.
        for wave in unreal.GameplayStatics.get_all_actors_of_class(self.rig['world'](), unreal.SparrowShotWave):
            if wave.get_owner() == self.rig['pawn']():
                path = wave.get_path_name()
                if path not in self.hidden_actors:
                    self.hidden_actors[path] = (wave, wave.get_editor_property('hidden'))
                    surfaces = []
                    for component in wave.get_components_by_class(unreal.StaticMeshComponent):
                        material = component.get_material(0)
                        surfaces.append({'component': component.get_name(),
                                         'material': material.get_path_name() if material else None,
                                         'base_material': material.get_base_material().get_path_name() if material else None})
                    self.events.append({'event': 'native_release_actor_hidden', 'actor': path,
                                        'surfaces': surfaces,
                                        'reason': 'AirWave0/1 use M_SparrowShotSplitRing; native Tick overwrites component visibility'})
                # Actor hidden state survives native Wave::Tick SetVisibility.
                # This proven study API leaves collision, lifetime and damage alone.
                wave.set_actor_hidden_in_game(True)
        self.live_impact = False
        for component in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if not valid(component):
                continue
            tags = {str(t) for t in component.get_editor_property('component_tags')}
            if tags.intersection(HIDE_RELEASE_TAGS):
                self.hide(component)
            if 'SparrowPiercingImpact' in tags:
                self.impact_seen = True
                self.live_impact |= component.is_active() and component.get_num_active_particles() > 0

    def preparation(self, prep):
        age = self.now()-prep['born']
        release_age = self.now()-prep['release'] if prep['release'] is not None else None
        strength = smooth(age/.18)*(1.-smooth(release_age/.10) if release_age is not None else .85)
        p, f, r, u = self.rig['skills']().get_arrow_origin(), self.forward, self.right, self.up
        if self.option == 'W1':
            separation = 30.-22.*smooth(age/.48)
            for i, row in enumerate(prep['parts']):
                offset = r*((-1. if i == 0 else 1.)*separation)
                self.line(row, p-f*72.+offset, p+f*30.+offset*.2, 3., strength*1.7)
        elif self.option == 'W2':
            for i, row in enumerate(prep['parts']):
                offset = r*((i-2)*15.)+u*((i%2)*7.)
                self.line(row, p-f*(75.+i*8.)+offset, p-f*15.+offset, 3., strength*1.5)
        else:
            for i, row in enumerate(prep['parts']):
                side, high = (-1. if i < 2 else 1.), (-1. if i%2 == 0 else 1.)
                center = p+f*12.+r*(side*26.)+u*(high*12.)
                self.line(row, center+u*(high*16.), center+r*(side*12.), 4., strength*1.5)

    def pressure(self, item, age):
        p, f, r, u = (item[k] for k in ('origin', 'direction', 'right', 'up'))
        length, parts = item['length'], item['parts']
        head = min(length, max(1., age*4000.))
        axis = 1.-smooth((age-.10)/.36)
        self.line(parts[0], p, p+f*head, 5., axis*3.4)
        opening = smooth((age-.015)/.17)
        envelope = smooth(age/.035)*(1.-smooth((age-.22)/.25))
        for i in range(4):
            side = -1. if i%2 == 0 else 1.
            center = p+f*(length*(.27+.32*(i//2)))
            span = 21.+opening*39.
            tip = center+f*22.+r*(side*opening*7.)
            self.line(parts[1+i], center-f*62.+r*(side*span), tip,
                      8., envelope*2.5)
            self.line(parts[5+i], center-f*83.+r*(side*(span*.72))+u*8.,
                      tip-f*22.+u*8., 4., envelope*1.15)

    def needles(self, item, age):
        p, f, r, u = (item[k] for k in ('origin', 'direction', 'right', 'up'))
        for i, row in enumerate(item['parts']):
            bank, column = divmod(i, 5)
            local = age-bank*.12
            progress = clamp(local/.30)
            envelope = smooth(local/.035)*(1.-smooth((local-.30)/.14))
            spread = 1.-progress*.22
            offset = r*((column-2)*17.*spread)+u*((bank-1)*17.+(column%2)*8.)
            head = p+f*(item['length']*progress)+offset
            self.line(row, head-f*(56.+(column%3)*15.), head, 3.3, envelope*2.3)
            self.soft_dot(item['dots'][i], head, 7., envelope*1.7)

    def gates(self, item, age):
        p, f, r, u = (item[k] for k in ('origin', 'direction', 'right', 'up'))
        arrow = item['actor']
        if valid(arrow):
            head = arrow.get_actor_location()
            self.line(item['parts'][0], head-f*72., head+f*22., 4.2, 2.2)
        for gate in range(2):
            local = age-gate*.08
            opening = smooth((local-.025)/.26)
            envelope = smooth(local/.045)*(1.-smooth((local-.36)/.36))
            center = p+f*(170.+gate*235.+opening*38.)
            radius = 34.+opening*(39.+gate*9.)
            for layer in range(3):
                inner_radius = radius-layer*(5.+opening*4.)
                # Darker warm inner arcs back the white edge without making
                # a filled disc or increasing the original outer diameter.
                axial = center-f*(layer*7.)
                for sector in range(6):
                    middle_angle = math.radians(sector*60.+30.)
                    side = 1. if math.cos(middle_angle) >= 0. else -1.
                    split = r*(side*opening*43.)
                    for segment in range(2):
                        a = math.radians(sector*60.+7.5+segment*22.5)
                        b = a+math.radians(22.5)
                        start = axial+split+r*(math.cos(a)*inner_radius)+u*(math.sin(a)*inner_radius)
                        end = axial+split+r*(math.cos(b)*inner_radius)+u*(math.sin(b)*inner_radius)
                        index = 1+gate*36+layer*12+sector*2+segment
                        self.line(item['parts'][index], start, end,
                                  (14., 10., 5.5)[layer], envelope*(3.3, 1.45, .85)[layer])

    def update(self):
        self.visible_strokes = 0
        self.suppress_shared_release()
        for prep in self.preparations:
            self.preparation(prep)
        for item in self.w_arrows:
            if item['retired']:
                continue
            age = self.now()-item['born']
            if valid(item['actor']):
                item['last_hit_count'] = item['actor'].get_hit_count()
            self.silence(item['parts']+item['dots'])
            if age >= .92:
                for row in item['parts']+item['dots']:
                    if valid(row['actor']):
                        row['actor'].destroy_actor()
                item['retired'] = True
                continue
            {'W1': self.pressure, 'W2': self.needles, 'W3': self.gates}[self.option](item, age)
        self.max_visible_strokes = max(self.max_visible_strokes, self.visible_strokes)
        self.tick()

    def close(self):
        failures = []
        for actor, hidden in self.hidden_actors.values():
            if valid(actor):
                actor.set_actor_hidden_in_game(hidden)
                if actor.get_editor_property('hidden') != hidden:
                    failures.append(actor.get_path_name()+':actor_hidden')
        for component, visible in self.hidden:
            if valid(component):
                component.set_visibility(visible)
                if component.is_visible() != visible:
                    failures.append(component.get_path_name()+':visibility')
        for component, materials in self.w_materials:
            if valid(component):
                for slot, material in enumerate(materials):
                    component.set_material(slot, material)
                    if component.get_material(slot) != material:
                        failures.append(component.get_path_name()+':material')
        failures.extend(super().close())
        return failures


def sequence(rig):
    options = [s.strip().upper() for s in os.environ.get('SPARROW_W_SIGNATURE_OPTIONS', ','.join(OPTIONS)).split(',') if s.strip()]
    assert options and len(set(options)) == len(options) and all(o in OPTIONS for o in options), options
    inventory, results = author(rig['OUT']), []
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    for option in options:
        rig['switch']('countess'); yield .15
        rig['switch']('sparrow'); yield .55
        prefix = 'W_signature_'+option
        rig['case'](prefix)
        targets = rig['layout']([(650, 0), (450, 430), (650, -430)])
        yield .20
        health = [rig['health'](d) for d in targets]
        study, evidence, attempts = Study(rig, option, targets), [], 0
        started, second = now(), False
        try:
            study.prepare_cast()
            rig['use']('W', targets[0])
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {'case': prefix, 'prefix': prefix+'_video',
                                             'cast_time': started, 'frame_times': []}
            while now()-started < 3.6:
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow):
                    if arrow.get_owner() == rig['pawn']() and arrow.actor_has_tag('SparrowChargedArrow'):
                        study.observe_w(arrow)
                if now()-started >= 1.6 and not second:
                    study.prepare_cast(); rig['use']('W', targets[0]); second = True
                study.update()
                if study.live_impact and not evidence and attempts < 3:
                    attempts += 1
                    token = prefix+'_native_impact_'+str(attempts)
                    rig['cmd']('SparrowQA.State '+token)
                    state = json.loads((Path(rig['OUT'])/(token+'.json')).read_text(encoding='utf-8-sig'))
                    live = [p for p in state['effects'] if p['active'] and p['particles'] > 0
                            and 'SparrowChargedImpactRuntime' in p['template']
                            and any(e['renders_surface'] and e['particles'] > 0 for e in p['render_emitters'])]
                    if live:
                        evidence.append({'state': token+'.json', 'live_surface_PSCs': len(live)})
                while study.pending_captures and now() >= study.pending_captures[0][0]:
                    due, delay = study.pending_captures.pop(0)
                    label = prefix+'_release_'+str(round(delay*1000)).zfill(3)+'ms'
                    rig['capture'](label)
                    study.signature_samples.append({'capture': label+'.png', 'after_release_requested': delay,
                                                    'capture_lag_seconds': now()-due,
                                                    'visible_strokes': study.visible_strokes})
                yield 1/rig['FPS']
            rig['finish_video_clip']()
            damage = [before-rig['health'](d) for before, d in zip(health, targets)]
            rig['check'](len(study.seen) == 2, option+' has exactly two real W arrows; optical props add none')
            rig['check'](abs(damage[0]-70.) < .03 and all(abs(d) < .03 for d in damage[1:]),
                         option+' preserves two native 35 damage hits and adds no visual-prop damage')
            rig['check'](study.impact_seen and bool(evidence), option+' keeps the actual live native impact surface emitters')
            rig['check'](len(study.hidden_actors) == 2,
                         option+' isolates both native split-ring release actors from the optical signature')
            rig['check'](len(study.signature_samples) == 3 and study.max_visible_strokes > 5,
                         option+' samples three release-relative signature moments')
            rig['check'](all(i['retired'] for i in study.w_arrows), option+' completes all added optical signatures')
            rig['recovered']()
            row = {'id': option, **DESIGNS[option], 'installed': False, 'video_prefix': prefix+'_video',
                   'duration_seconds': 3.6, 'native_damage': damage, 'native_shots': study.native_samples,
                   'native_impact_evidence': evidence, 'events': study.events,
                   'signature_samples': study.signature_samples,
                   'max_visible_strokes': study.max_visible_strokes,
                   'visual_review': 'pending actual quarter-view capture review'}
        finally:
            rig['finish_video_clip']()
            failures = study.close()
        rig['check'](not failures and not study.effects and not study.planes,
                     option+' restores surviving native visuals and destroys every temporary prop')
        results.append(row)
        write(rig['OUT'], 'W-signature-studies.json', {'passed': len(results) == len(options),
              'signature_version': SIGNATURE_VERSION,
              'studies': results, 'sources': inventory['sources'], 'assets_saved': False,
              'production_changed': False, 'additional_damage_or_gameplay_arrows': False,
              'visual_review': 'pending root actual-screen acceptance'})
        rig['switch']('countess'); yield .25
