"""PIE-only E texture studies; no gameplay, source-pack or production asset edits.

Call author(out) before PIE, then yield from sequence(rig) in new_skills_probe.
All six native arrows and their real target hits drive the presentation. Effects
are selected on PSC instances after activation, never on shared templates.
No flat study planes, procedural rings, asset saves or new damage are used.
"""
import json
import math
import os
from pathlib import Path

import unreal


BASE = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/'
SOURCES = {
    'muzzle': BASE + 'Primary/FX/P_SparrowPrimaryMuzzleFlash',
    'shards': BASE + 'Ultimate/FX/P_Sparrow_Burst',
    'impact': BASE + 'Ultimate/FX/P_Sparrow_UltHit',
}
EMITTERS = {
    'muzzle': ('MuzzleFlare', 'MuzzleGlow', 'AirglowFlash', 'Airglow', 'Ring', 'Wisps', 'Sparks'),
    'shards': ('dustring', 'Flare_Big', 'Light', 'Particle Emitter', 'Shockwave Ring', 'Flames2'),
    'impact': ('Particle Emitter', 'SparkTrailHeads', 'Sparks', 'Flare', 'Main Flames',
               'Wisps', 'AddFlare', 'Line Burst'),
}
WHITE_WISPS = '/Game/ParagonSparrow/FX/Materials/CineRescue/M_Sparrow_Wisps'
OPTIONS = ('E1', 'E2', 'E3')
DESIGNS = {
    'E1': {
        'label': '응축 플라즈마 탄',
        'shape': '짧은 황금 플라즈마 덩어리와 단단한 화살 중심',
        'primary_trail': '이 시전에서만 숨김; 긴 선을 없애고 실제 화살 메시와 짧은 탄 덩어리를 드러냄',
        'native_wisps': '유지, 폭 2.30 / 입자 시간 3.20배로 짧고 굵게 응축',
        'release': '원본 Wisps + AirglowFlash만, 고리와 불티 제외',
        'hit': '실제 피해 발생 위치에서 원본 Wisps의 짧은 파열',
    },
    'E2': {
        'label': '금빛 파편 쇄도',
        'shape': '진행 방향으로 갈라지는 곡면 화염편, 깃털처럼 겹치는 윤곽',
        'primary_trail': '유지, 폭 .75',
        'native_wisps': '이 시전에서만 숨김; 원본 Flames2 메시 입자로 대체',
        'release': '실제 화살별 두 위치에서 곡면 Flames2 묶음; 첫 시안 대비 약 4배 크기, 바닥 원 없음',
        'hit': '실제 피해 때 작은 Flames2 파편으로 연결',
        'limitation': '실제 깃털 에셋은 아니며 SM_ShockwaveFlame의 휘어진 파편을 사용',
    },
    'E3': {
        'label': '백금 화염줄기',
        'shape': '좁은 백금 질감 흐름과 명중 때 옆으로 벌어지는 짧은 파열',
        'primary_trail': '유지, 폭 .65로 가는 중심만 남김',
        'native_wisps': '유지, 폭 1.10 / 시간 .90배; 원본 8x8 Wisps 재질 MID의 RGB 역보정(.26,.36,2.15)',
        'release': 'AirglowFlash만 짧게, 큰 고리 없음',
        'hit': '실제 명중 때 Main Flames 메시 5개의 짧고 납작한 파열',
    },
}


def author(out):
    """Verify the actual source emitters/material interface without saving assets."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for method in ('set_emitter_enable', 'get_num_active_particles', 'set_material'):
        assert hasattr(unreal.ParticleSystemComponent, method), method
    unreal.SystemLibrary.execute_console_command(
        None, 'CharacterPipeline.OutputDirectory "' + out.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(
        None, 'SparrowAssetQA.Dump ' + ' '.join('"' + p + '"' for p in SOURCES.values()))
    native = json.loads((out / 'sparrow-native-inventory.json').read_text(encoding='utf-8-sig'))
    rows = []
    for key, path in SOURCES.items():
        assert unreal.load_asset(path), path
        entry = next(a for a in native['assets'] if a['path'].split('.')[0] == path)
        names = {str(e['properties']['EmitterName']) for e in entry['emitters']}
        assert names == set(EMITTERS[key]), (path, sorted(names))
        rows.append({'key': key, 'path': path, 'emitter_names': sorted(names)})
    material = unreal.load_asset(WHITE_WISPS)
    assert material and 'Param' in [str(x) for x in unreal.MaterialEditingLibrary.get_vector_parameter_names(material)]
    # Both original Wisps use 8x8 SubUV: changing only the instance material is compatible.
    for key in ('muzzle', 'impact'):
        entry = next(a for a in native['assets'] if a['path'].split('.')[0] == SOURCES[key])
        wisp = next(e for e in entry['emitters'] if e['properties']['EmitterName'] == 'Wisps')
        props = wisp['lods'][0]['required']['properties']
        assert int(props['SubImages_Horizontal']) == int(props['SubImages_Vertical']) == 8
    result = {'passed': True, 'sources': rows, 'options': DESIGNS, 'assets_saved': False,
              'source_pack_assets_changed': False, 'production_defaults_changed': False,
              'visual_review': 'pending actual PIE capture',
              'limitation': 'A Python tick observes a native shot/hit after it occurs; preview synchronization may lag by one frame.'}
    (out / 'E-texture-author.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def _valid(obj):
    return obj is not None and unreal.SystemLibrary.is_valid(obj)


class Study:
    def __init__(self, rig, option):
        self.rig, self.option = rig, option
        self.effects, self.snapshots, self.mids = [], [], []
        self.templates = {key: unreal.load_asset(path) for key, path in SOURCES.items()}
        self.created, self.peak_particles = 0, 0
        self.modified_components = {'ArrowTrail': 0, 'RapidArrowFlow': 0}

    def now(self):
        return unreal.GameplayStatics.get_time_seconds(self.rig['world']())

    def pulse(self, key, names, position, rotation, scale, seconds, speed=1.):
        # Activate first: SetEmitterEnable acts on EmitterInstances, which activation creates.
        # This all runs in one Slate callback before the next simulation tick/render.
        particle = unreal.GameplayStatics.spawn_emitter_at_location(
            self.rig['world'](), self.templates[key], position, rotation,
            unreal.Vector(*scale), False, unreal.PSCPoolMethod.NONE, False)
        assert particle, (key, names)
        self.effects.append((particle, self.now() + seconds))
        self.created += 1
        particle.set_editor_property('component_tags', [unreal.Name('SparrowETextureStudy')])
        particle.set_editor_property('custom_time_dilation', speed)
        particle.activate(True)
        for name in EMITTERS[key]:
            particle.set_emitter_enable(name, name in names)
        return particle

    def arrow(self, arrow):
        for particle in arrow.get_components_by_class(unreal.ParticleSystemComponent):
            name = particle.get_name()
            if name not in ('ArrowTrail', 'RapidArrowFlow'):
                continue
            self.modified_components[name] += 1
            self.snapshots.append((particle, particle.is_visible(),
                particle.get_editor_property('relative_scale3d'),
                particle.get_editor_property('custom_time_dilation'), particle.get_material(0)))
            if name == 'ArrowTrail':
                if self.option == 'E1':
                    particle.set_visibility(False)
                else:
                    width = .75 if self.option == 'E2' else .65
                    particle.set_world_scale3d(unreal.Vector(1., width, width))
            elif self.option == 'E1':
                particle.set_world_scale3d(unreal.Vector(1., 2.30, 2.30))
                particle.set_editor_property('custom_time_dilation', 3.20)
            elif self.option == 'E2':
                particle.set_visibility(False)
            else:
                particle.set_world_scale3d(unreal.Vector(1., 1.10, 1.10))
                particle.set_editor_property('custom_time_dilation', .90)
                mid = unreal.MaterialLibrary.create_dynamic_material_instance(
                    self.rig['world'](), unreal.load_asset(WHITE_WISPS))
                assert mid, WHITE_WISPS
                # Native StartColor (3.5,2.8,.55) and peak ColorScale (4,3.6,3)
                # multiply the tint. Inverse compensation makes that peak near-neutral.
                mid.set_vector_parameter_value('Param', unreal.LinearColor(.26, .36, 2.15, 1.))
                particle.set_material(0, mid)
                self.mids.append(mid)
        origin, rotation = arrow.get_actor_location(), arrow.get_actor_rotation()
        if self.option == 'E1':
            self.pulse('muzzle', ('Wisps', 'AirglowFlash'), origin, rotation, (3.5, 2.6, 2.6), .20, 1.8)
        elif self.option == 'E2':
            self.shards(arrow)
        else:
            self.pulse('muzzle', ('AirglowFlash',), origin, rotation, (1.9, .65, .65), .14, 1.4)

    def shards(self, arrow):
        # Original Flames2 velocity points along local Z. Aim Z along the real arrow.
        rotation = unreal.MathLibrary.make_rot_from_z(arrow.get_flight_direction())
        self.pulse('shards', ('Flames2',), arrow.get_actor_location(), rotation,
                   (.42, .42, .62), .34, 2.2)

    def hit(self, target, direction):
        point = target.get_actor_location()
        rotation = unreal.MathLibrary.make_rot_from_x(direction)
        if self.option == 'E1':
            self.pulse('impact', ('Wisps',), point, rotation, (1.25, .75, .75), .30, 2.2)
        elif self.option == 'E2':
            rotation = unreal.MathLibrary.make_rot_from_z(direction)
            self.pulse('shards', ('Flames2',), point, rotation, (.28, .28, .42), .30, 2.4)
        else:
            self.pulse('impact', ('Main Flames',), point, rotation, (.85, .32, .32), .26, 2.2)

    def tick(self):
        active, alive = 0, []
        for particle, deadline in self.effects:
            if not _valid(particle):
                continue
            if self.now() >= deadline:
                particle.deactivate()
                particle.destroy_component(particle)
            else:
                active += particle.get_num_active_particles()
                alive.append((particle, deadline))
        self.effects = alive
        self.peak_particles = max(self.peak_particles, active)

    def close(self):
        for particle, _ in self.effects:
            if _valid(particle):
                particle.deactivate()
                particle.destroy_component(particle)
        self.effects.clear()
        restored = 0
        for particle, visible, scale, speed, material in self.snapshots:
            if _valid(particle):
                particle.set_visibility(visible)
                particle.set_relative_scale3d(scale)
                particle.set_editor_property('custom_time_dilation', speed)
                particle.set_material(0, material)
                restored += 1
        self.snapshots.clear()
        self.mids.clear()
        return restored


def sequence(rig):
    """Three real casts, two equal-time frames plus optional short video per cast."""
    rows = []
    world, pawn, skills = rig['world'], rig['pawn'], rig['skills']
    now = lambda: unreal.GameplayStatics.get_time_seconds(world())
    for index, option in enumerate(OPTIONS):
        if index:
            rig['switch']('countess')
            yield .15
        rig['switch']('sparrow')
        yield .55
        rig['case']('sparrow_E_texture_' + option)
        ds = rig['layout']([(750, 0), (750, 350), (750, -350)])
        yield .25
        study = Study(rig, option)
        seen, arrows, shots, hits = set(), {}, [], []
        stacks = skills().get_relentless_stacks(ds[0])
        expected = sum(10. * (1. + min(stacks + i, 10) * .0175) for i in range(6))
        start_health = last_health = rig['health'](ds[0])
        started = now()
        delta = ds[0].get_actor_location() - skills().get_arrow_origin()
        length = math.sqrt(delta.x ** 2 + delta.y ** 2 + delta.z ** 2)
        direction = unreal.Vector(delta.x / length, delta.y / length, delta.z / length)
        try:
            rig['use']('E', ds[0])
            if os.environ.get('NEW_SKILLS_VIDEO', '1') == '1':
                rig['STATE']['video_clip'] = {
                    'case': 'sparrow_E_texture_' + option, 'prefix': option + '_video',
                    'cast_time': started, 'frame_times': []}
            moments = [.20, .53]
            while now() - started < 1.35:
                elapsed = now() - started
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowArrow):
                    if arrow.get_owner() != pawn() or arrow.get_path_name() in seen:
                        continue
                    seen.add(arrow.get_path_name())
                    study.arrow(arrow)
                    arrows[arrow.get_path_name()] = [arrow, now(), False]
                if option == 'E2':
                    for arrow, born, second in arrows.values():
                        if not second and _valid(arrow) and now() - born >= .08:
                            study.shards(arrow)
                            arrows[arrow.get_path_name()][2] = True
                health = rig['health'](ds[0])
                if health < last_health - .01:
                    study.hit(ds[0], direction)
                    hits.append({'elapsed': round(elapsed, 4), 'damage': round(last_health - health, 4)})
                last_health = health
                study.tick()
                if moments and elapsed >= moments[0]:
                    label = option + '_texture_' + str(len(shots))
                    rig['capture'](label)
                    shots.append({'label': label, 'cast_elapsed': round(elapsed, 4)})
                    moments.pop(0)
                yield 1 / 60
            rig['finish_video_clip']()
            yield .3
            study.tick()
            rig['recovered']()
            rig['check'](len(seen) == 6, 'study observed exactly six native E arrows')
            rig['check'](study.modified_components == {'ArrowTrail': 6, 'RapidArrowFlow': 6},
                         'presentation overrides reached both real components on all six arrows')
            rig['check'](abs(start_health - rig['health'](ds[0]) - expected) < .02,
                         'native E damage and pre-existing Relentless stacks preserved')
            rig['check'](len(shots) == 2, 'both equal-time comparison frames requested')
            row = {'option': option, **DESIGNS[option], 'screenshots': shots,
                   'observed_arrows': len(seen), 'actual_hit_events': hits,
                   'expected_damage': expected, 'actual_damage': start_health - rig['health'](ds[0]),
                   'temporary_PSCs_created': study.created,
                   'modified_component_counts': study.modified_components,
                   'peak_active_preview_particles_reported': study.peak_particles}
        finally:
            rig['finish_video_clip']()
            restored = study.close()
        row['surviving_components_restored'] = restored
        remaining = [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                     if _valid(p) and p.is_active() and
                     unreal.Name('SparrowETextureStudy') in p.get_editor_property('component_tags')]
        rig['check'](not remaining, 'no active temporary study particle components remain')
        row['temporary_effects_cleaned'] = not remaining
        rows.append(row)
    result = {'passed': True, 'revision': 2, 'options': rows, 'source': 'actual native E casts in PIE',
              'production_defaults_changed': False, 'assets_saved': False,
              'visual_review': 'pending', 'selection_required_for_production': True,
              'limitations': ['Particle counters are diagnostic counts, not GPU performance measurements.',
                             'Python observes the real shot/hit after the game tick; overlays may lag by one frame.',
                             'Original native hit flashes remain underneath the candidate impact layers.']}
    (rig['OUT'] / 'E-texture-studies.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
