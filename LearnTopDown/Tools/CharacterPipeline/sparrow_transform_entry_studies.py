"""Three transient V transformation entries synchronized to the native wings.

Use sparrow_feedback with SPARROW_FEEDBACK_PARTS='' and this file in
SPARROW_FEEDBACK_STUDIES. No authoring pass, asset saves or native edits are
needed. The parent owns GPU execution, actual video review and integration.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


_PARTICLES = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PARTICLES['Study'], _PARTICLES['_valid']
TAG = unreal.Name('SparrowTransformEntryStudy')
OPTIONS = ('V1', 'V2', 'V3')
DESIGNS = {
    'V1': {'label': '응축 광핵 · 양날개 점화',
           'description': '몸통의 금빛 핵이 좁아진 뒤 펼쳐지는 두 날개를 따라 압력이 빠르게 전달됨'},
    'V2': {'label': '상승 화염 · 날개맥 전파',
           'description': '골반 위에서 올라온 불꽃이 등에서 두 갈래로 갈라져 날개 끝까지 순차적으로 점화됨'},
    'V3': {'label': '순간 파열 · 금빛 잔편',
           'description': '날개가 나타나는 순간 짧은 금빛 파열 세 박자와 양끝의 잔편으로 힘 있게 전개됨'},
}


def _write(out, value):
    (Path(out)/'transform-entry-studies.json').write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def _now(rig):
    return unreal.GameplayStatics.get_time_seconds(rig['world']())


def _forms(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))


class Entry:
    def __init__(self, rig, option):
        self.rig, self.option = rig, option
        self.fx = ParticleStudy(rig, option)
        self.pending, self.motion, self.events = [], [], []
        self.wing, self.wing_bones, self.birth = None, [], None
        self.fallback_anchor_used = False
        self.started = _now(rig)
        if option == 'V1':
            # A compact core contracts before the visible wing expansion.
            self.queue(.10, False, 'muzzle', ('MuzzleGlow', 'Airglow', 'Wisps'), 0, 0., 0.,
                       (3.4, 2.8, 2.8), (.55, .45, .45), .52, 1.1)
        elif option == 'V2':
            for delay, height in ((.12, -48.), (.30, -25.), (.48, 0.)):
                self.queue(delay, False, 'impact', ('Main Flames', 'Wisps'), 0, 0., height,
                           (.55, .55, 1.20), (.28, .28, 1.8), .60, 1.2,
                           end_height=95.)

    def root(self):
        return self.rig['pawn']().get_editor_property('mesh').get_socket_location('spine_03')

    def point(self, side, reach, height):
        root = self.root()
        right = self.rig['pawn']().get_actor_right_vector()
        back = self.rig['pawn']().get_actor_forward_vector()*-1.
        if not side or not reach:
            return root+unreal.Vector(0., 0., height)
        endpoint, extent = None, 0.
        for bone in self.wing_bones if _valid(self.wing) else ():
            point = self.wing.get_socket_location(bone)
            delta = point-root
            projection = (delta.x*right.x+delta.y*right.y+delta.z*right.z)*side
            if projection > extent:
                endpoint, extent = point, projection
        if endpoint is None or extent < 24.:
            # A reported fallback keeps the preview usable if this skeleton's
            # bone names do not expose wing anchors. It is never called a bone lock.
            self.fallback_anchor_used = True
            endpoint = root+right*(side*155.)+back*40.+unreal.Vector(0., 0., 35.)
        return root+(endpoint-root)*reach+unreal.Vector(0., 0., height)

    def queue(self, delay, wing_phase, key, names, side, reach, height,
              scale, end_scale, lifetime, speed, end_reach=None, end_height=None):
        # Readable entry layers at the gameplay camera; the native wing remains
        # the silhouette, while these brief accents distinguish the three rhythms.
        gain = 2.6 if self.option == 'V2' else (2.2 if self.option == 'V3' else 1.45)
        if names == ('Flare',):
            gain = 1.
        scale = tuple(v*gain for v in scale)
        end_scale = tuple(v*gain for v in end_scale)
        self.pending.append({'delay': delay, 'wing_phase': wing_phase, 'key': key,
            'names': names, 'side': side, 'reach': reach, 'height': height,
            'scale': scale, 'end_scale': end_scale, 'lifetime': lifetime, 'speed': speed,
            'end_reach': reach if end_reach is None else end_reach,
            'end_height': height if end_height is None else end_height})

    def unfold(self, form):
        self.birth = _now(self.rig)
        self.wing = next(c for c in form.get_components_by_class(unreal.SkeletalMeshComponent)
                         if c.get_name() == 'SerathWings')
        self.wing_bones = [self.wing.get_bone_name(i) for i in range(self.wing.get_num_bones())
                           if 'wing' in str(self.wing.get_bone_name(i)).lower()]
        if self.option == 'V1':
            self.queue(.48, True, 'impact', ('Flare',), 0, 0., 8.,
                       (.32, .32, .32), (.12, .12, .12), .22, 1.8)
            self.queue(.48, True, 'impact', ('Main Flames', 'Sparks', 'Line Burst'), 0, 0., 6.,
                       (1.15, .85, 1.05), (.28, .22, .30), .38, 1.7)
            for side in (-1, 1):
                self.queue(.50, True, 'shards', ('Flames2',), side, .10, 4.,
                           (.60, .60, 1.15), (.25, .25, .45), .48, 1.4, end_reach=1.02)
                self.queue(.90, True, 'impact', ('Sparks', 'SparkTrailHeads'), side, 1.02, 2.,
                           (1.20, .65, .65), (.35, .22, .22), .34, 1.7)
        elif self.option == 'V2':
            # Four staggered ignition sites travel with the current real wing pose.
            for side in (-1, 1):
                self.queue(.38, True, 'shards', ('Flames2',), side, .05, 20.,
                           (.50, .50, 1.15), (.24, .24, .60), .72, 1.1, end_reach=1.10)
                for reach, delay in ((.26, .50), (.52, .66), (.78, .82), (1.08, .98)):
                    self.queue(delay, True, 'impact', ('Main Flames', 'Sparks'), side, reach, 2.,
                               (.55, .40, .70), (.18, .16, .24), .40, 1.3)
        else:
            # No full-screen Flare, AddFlare, source light or floor dust emitters.
            for delay, size in ((.46, 1.50), (.57, 1.20), (.68, .90)):
                self.queue(delay, True, 'impact', ('Sparks', 'Line Burst'), 0, 0., 8.,
                           (size, size*.72, size*.72), (size*.38, size*.28, size*.28), .30, 1.9)
            self.queue(.48, True, 'impact', ('Main Flames',), 0, 0., 10.,
                       (.80, .55, .70), (.22, .18, .24), .30, 1.9)
            for side in (-1, 1):
                for reach, delay in ((.38, .50), (.72, .61), (1.0, .72)):
                    self.queue(delay, True, 'shards', ('Flames2',), side, reach, 2.,
                               (.50, .38, .75), (.16, .14, .28), .38, 1.8, end_reach=reach+.25)
                self.queue(.90, True, 'impact', ('Sparks', 'SparkTrailHeads'), side, 1.10, 4.,
                           (1.15, .80, .80), (.28, .22, .22), .38, 1.6)

    def tick(self):
        now = _now(self.rig)
        for item in self.pending[:]:
            if item['wing_phase'] and self.birth is None:
                continue
            phase = self.birth if item['wing_phase'] else self.started
            if now-phase < item['delay']:
                continue
            self.pending.remove(item)
            origin = self.point(item['side'], item['reach'], item['height'])
            endpoint = self.point(item['side'], max(item['end_reach'], .9), item['end_height'])
            direction = endpoint-self.root() if item['side'] else unreal.Vector(0., 0., 1.)
            rotation = unreal.MathLibrary.make_rot_from_z(direction)
            # Match native Sparrow PSCs: keep the authored emitter LOD during
            # the short entry instead of distance-culling layers in this camera.
            direct = next(getattr(unreal.ParticleSystemLODMethod, name)
                          for name in dir(unreal.ParticleSystemLODMethod) if 'DIRECT' in name.upper())
            particle = unreal.GameplayStatics.spawn_emitter_at_location(
                self.rig['world'](), self.fx.templates[item['key']], origin, rotation,
                unreal.Vector(*item['scale']), False, unreal.PSCPoolMethod.NONE, False)
            assert particle
            self.fx.effects.append((particle, now+item['lifetime']))
            self.fx.created += 1
            # Editor property writes can reregister a component. Finish those
            # before activation so this non-auto-active PSC stays running.
            particle.set_editor_property('component_tags', [TAG])
            particle.set_editor_property('override_lod_method', True)
            particle.set_editor_property('lod_method', direct)
            particle.set_editor_property('custom_time_dilation', item['speed'])
            particle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            particle.set_editor_property('generate_overlap_events', False)
            particle.activate(True)
            for name in _PARTICLES['EMITTERS'][item['key']]:
                particle.set_emitter_enable(name, name in item['names'])
            self.motion.append((particle, now, item))
            self.events.append({'cast_elapsed': round(now-self.started, 4),
                'wing_elapsed': round(now-self.birth, 4) if self.birth is not None else None,
                'source': item['key'], 'emitters': item['names'], 'side': item['side']})
        for particle, born, item in self.motion[:]:
            if not _valid(particle) or now-born >= item['lifetime']:
                self.motion.remove((particle, born, item))
                continue
            t = min(1., (now-born)/item['lifetime'])
            move = 1.-(1.-t)**2
            reach = item['reach']+(item['end_reach']-item['reach'])*move
            height = item['height']+(item['end_height']-item['height'])*move
            particle.set_world_location(self.point(item['side'], reach, height), False, False)
            scale = [a+(b-a)*move for a, b in zip(item['scale'], item['end_scale'])]
            particle.set_world_scale3d(unreal.Vector(*scale))
        self.fx.tick()

    def close(self):
        self.pending.clear()
        self.motion.clear()
        self.fx.close()


def sequence(rig):
    selected = [s.strip().upper() for s in os.environ.get(
        'SPARROW_TRANSFORM_ENTRY_OPTIONS', 'V1,V2,V3').split(',') if s.strip()]
    assert selected and all(s in OPTIONS for s in selected), selected
    rows = []
    for option in selected:
        rig['switch']('countess')
        yield .20
        rig['switch']('sparrow')
        yield .65
        rig['case']('transform_entry_'+option)
        targets = rig['layout']([(850, 0), (850, 380), (850, -380)])
        yield .20
        body = rig['pawn']().get_editor_property('mesh')
        materials = [body.get_material(i).get_path_name() for i in range(body.get_num_materials())]
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(body.get_skeletal_mesh_asset())
        sections = [[body.is_material_section_shown(i, lod) for i in range(body.get_num_materials())]
                    for lod in range(lods)]
        health = [rig['health'](d) for d in targets]
        study, form, captures = Entry(rig, option), None, []
        started = _now(rig)
        try:
            rig['use']('V', targets[0])
            if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                rig['STATE']['video_clip'] = {'case': 'transform_entry_'+option,
                    'prefix': option+'_entry_video', 'cast_time': started, 'frame_times': []}
            moments = [.28, 1.20, 1.55]
            while _now(rig)-started < 2.20:
                elapsed = _now(rig)-started
                forms = _forms(rig)
                if form is None and forms:
                    rig['check'](len(forms) == 1, option+' uses exactly one native transformation actor')
                    form = forms[0]
                    study.unfold(form)
                study.tick()
                if moments and elapsed >= moments[0]:
                    name = option+'_entry_'+str(round(moments.pop(0)*100)).zfill(3)
                    rig['capture'](name)
                    rig['cmd']('SparrowQA.State '+name)
                    captures.append(name)
                yield 1./rig['FPS']
            rig['finish_video_clip']()
            rig['check'](_valid(form) and study.birth is not None, option+' V input creates the native form')
            rig['check'](study.wing.get_skeletal_mesh_asset().get_path_name().startswith(
                '/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath.'), option+' keeps the original wing mesh')
            rig['check'](form.get_life_span() > 37., option+' preserves the 40-second native duration')
            rig['check'](not study.pending, option+' completed every scheduled entry pulse')
            rig['check']([rig['health'](d) for d in targets] == health, option+' presentation adds no damage')
            rig['check'](study.fx.peak_particles > 0, option+' entry particles actually simulate')
            rig['recovered']()
            row = {'option': option, **DESIGNS[option], 'screenshots': captures,
                'prefix': option+'_entry_video', 'form_spawn_seconds': round(study.birth-started, 4),
                'particle_components_created': study.fx.created,
                'peak_live_particles': study.fx.peak_particles, 'events': study.events,
                'wing_bone_names': [str(b) for b in study.wing_bones],
                'body_relative_fallback_used': study.fallback_anchor_used}
        finally:
            rig['finish_video_clip']()
            study.close()
            if _valid(form):
                form.destroy_actor()
        yield .12
        remaining = [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                     if _valid(p) and TAG in p.get_editor_property('component_tags')]
        rig['check'](not remaining, option+' destroys all temporary entry components')
        rig['check'](not _forms(rig), option+' removes the review form after capture')
        rig['check']([body.get_material(i).get_path_name() for i in range(body.get_num_materials())] == materials,
                     option+' restores the exact pre-cast body materials')
        restored = [[body.is_material_section_shown(i, lod) for i in range(body.get_num_materials())]
                    for lod in range(lods)]
        rig['check'](restored == sections, option+' restores cloak and hood section visibility')
        row['temporary_components_cleaned'] = True
        row['body_and_cloth_restored'] = True
        rows.append(row)
        _write(rig['OUT'], {'passed': False, 'phase': 'in_progress', 'options': rows})
    _write(rig['OUT'], {'passed': True, 'temporary_only': True, 'assets_saved': False,
        'production_wing_materials_or_duration_changed': False,
        'sources': _PARTICLES['SOURCES'], 'options': rows, 'visual_acceptance': 'pending actual video review',
        'limitations': ['Python observes the native form after its creation tick; synchronization may lag one frame.',
                        'Any body-relative wing endpoint fallback is explicitly reported per option.',
                        'This pass verifies presentation cleanup; particle counters are not a performance measurement.']})
