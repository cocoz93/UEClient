"""D decision prototype: two stationary eight-second gold archer sentries.

This never invokes D or any native damage projectile. Skeletons, arrow meshes,
and original particle emitters are transient PIE presentation only. The parent
owns GPU execution and actual video review; no authoring or build is needed.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


_BOW = runpy.run_path(str(Path(__file__).with_name('sparrow_bow_audit.py')))
_PARTICLES = runpy.run_path(str(Path(__file__).with_name('sparrow_e_texture_studies.py')))
ParticleStudy, _valid = _PARTICLES['Study'], _PARTICLES['_valid']
TAG = unreal.Name('SparrowSentryDecisionStudy')
ANIMATION = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/Primary_Fire_Fast'
ECHO = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionEcho'
GOLD = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold'
ARROW = '/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow'
TRAIL = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Primary/FX/P_Sparrow_PrimaryAttack'
TRAIL_EMITTERS = ('RibbonTrail', 'DebugRibbon', 'Flare_Big', 'Flare',
                  'SparksTrailing', 'Refraction', 'Particle Emitter')
PREFIX = 'D_stationary_two_sentries'
LIFETIME, CADENCE, SPEED = 8., .72, 1200.


def _now(rig):
    return unreal.GameplayStatics.get_time_seconds(rig['world']())


def _vec(value):
    return [round(value.x, 4), round(value.y, 4), round(value.z, 4)]


def _owned_actors(rig):
    return [a for a in unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), TAG) if _valid(a)]


class Study:
    def __init__(self, rig, targets):
        self.rig, self.targets = rig, targets
        self.fx = ParticleStudy(rig, 'sentry')
        self.sentries, self.arrows, self.actors, self.shots, self.impacts = [], [], [], [], []
        self.started, self.serial, self.max_drift = _now(rig), 0, 0.
        self.native = rig['pawn']().get_editor_property('mesh')
        self.source_mesh = self.native.get_skeletal_mesh_asset()
        self.animation, self.echo = unreal.load_asset(ANIMATION), unreal.load_asset(ECHO)
        self.gold = unreal.load_asset(GOLD)
        self.arrow_mesh, self.trail = unreal.load_asset(ARROW), unreal.load_asset(TRAIL)
        assert isinstance(self.animation, unreal.AnimSequence) and self.echo and self.gold and self.arrow_mesh and self.trail
        assert self.animation.get_editor_property('skeleton') == self.source_mesh.get_editor_property('skeleton')

    def pulse(self, key, names, location, rotation, scale, lifetime, speed=1.):
        if key == 'sentry_trail':
            particle = unreal.GameplayStatics.spawn_emitter_at_location(
                self.rig['world'](), self.trail, location, rotation, unreal.Vector(*scale),
                False, unreal.PSCPoolMethod.NONE, False)
            assert particle
            self.fx.effects.append((particle, _now(self.rig)+lifetime))
            self.fx.created += 1
            particle.set_editor_property('custom_time_dilation', speed)
            particle.activate(True)
            for name in TRAIL_EMITTERS:
                particle.set_emitter_enable(name, name in names)
        else:
            particle = self.fx.pulse(key, names, location, rotation, scale, lifetime, speed)
        particle.set_editor_property('component_tags', [TAG])
        particle.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        particle.set_editor_property('generate_overlap_events', False)
        # Editor-property writes may reregister this non-auto-active component.
        # Activate after those writes, then reapply this instance's emitter mask.
        particle.activate(True)
        for name in TRAIL_EMITTERS if key == 'sentry_trail' else _PARTICLES['EMITTERS'][key]:
            particle.set_emitter_enable(name, name in names)
        return particle

    def spawn(self):
        start = self.native.get_world_transform()
        forward = self.rig['pawn']().get_actor_forward_vector()
        right = self.rig['pawn']().get_actor_right_vector()
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(self.source_mesh)
        hidden = [self.native.get_material_index(name) for name in ('M16_CloakStraps', 'M08_Cloak', 'M14_CloakHood')]
        assert all(index >= 0 for index in hidden), 'named cloak, straps and hood sections are required'
        for index, side in enumerate((-1., 1.)):
            actor = _BOW['spawn_preview'](self.rig['world'](), self.rig['cmd'])
            self.actors.append(actor)
            actor.set_editor_property('tags', [TAG])
            actor.set_life_span(LIFETIME)
            mesh = actor.get_editor_property('skeletal_mesh_component')
            mesh.set_skeletal_mesh_asset(self.source_mesh)
            mesh.set_editor_property('disable_cloth_simulation', True)
            mesh.set_forced_lod(1)
            mesh.set_cast_shadow(False)
            mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            mid = mesh.create_dynamic_material_instance(0, self.echo)
            assert mid
            mid.set_scalar_parameter_value('Visibility', .9)
            mid.set_vector_parameter_value('BodyTint', unreal.LinearColor(.95, .60, .12, 1.))
            for slot in range(mesh.get_num_materials()):
                mesh.set_material(slot, mid)
            for lod in range(lods):
                for slot in hidden:
                    mesh.show_material_section(slot, -1, False, lod)
            position = start.translation-forward*130.+right*(side*165.)
            actor.set_actor_location_and_rotation(position, start.rotation.rotator(), False, True)
            mesh.play_animation(self.animation, True)
            mesh.set_play_rate(0.)
            mesh.set_position(0., False)
            self.sentries.append({'actor': actor, 'mesh': mesh, 'mid': mid,
                'fixed_location': actor.get_actor_location(), 'rotation': actor.get_actor_rotation(),
                'started_animation': False, 'offset': index*.10, 'next_shot': .16+index*.10,
                'direction': None, 'range': None, 'target': self.targets[index],
                'shots': 0, 'shots_after_player_moved': 0})
        self.started = _now(self.rig)

    def fire(self, sentry, player_moved):
        mesh = sentry['mesh']
        assert mesh.does_socket_exist('arrow_anchor'), 'use the real bow anchor, never an invented muzzle'
        origin = mesh.get_socket_location('arrow_anchor')
        if sentry['direction'] is None:
            delta = sentry['target'].get_actor_location()-origin
            sentry['range'] = delta.length()
            sentry['direction'] = delta/sentry['range']
        direction = sentry['direction']
        duration = sentry['range']/SPEED
        self.serial += 1
        name = 'SparrowSentryArrow_'+str(round(self.started*1000))+'_'+str(self.serial)
        self.rig['cmd'](f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {origin.x} {origin.y} {origin.z}')
        actor = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(
            self.rig['world'](), unreal.StaticMeshActor) if a.get_name() == name), None)
        assert actor, name
        self.actors.append(actor)
        actor.set_editor_property('tags', [TAG])
        actor.set_actor_enable_collision(False)
        actor.set_life_span(1.5)
        arrow = actor.get_editor_property('static_mesh_component')
        arrow.set_mobility(unreal.ComponentMobility.MOVABLE)
        arrow.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        arrow.set_editor_property('generate_overlap_events', False)
        arrow.set_editor_property('can_ever_affect_navigation', False)
        arrow.set_cast_shadow(False)
        arrow.set_static_mesh(self.arrow_mesh)
        # The real source arrow points down local -Z, as documented by SparrowArrow.cpp.
        actor.set_actor_rotation(unreal.MathLibrary.make_rot_from_z(direction*-1.), True)
        arrow.set_world_scale3d(unreal.Vector(.55, .55, .65))
        for slot in range(max(1, arrow.get_num_materials())):
            arrow.set_material(slot, self.gold)
        trail = self.pulse('sentry_trail', ('RibbonTrail', 'SparksTrailing'), origin,
            unreal.MathLibrary.make_rot_from_x(direction), (1., .48, .48), duration+.04)
        self.pulse('muzzle', ('Wisps', 'Sparks'), origin,
            unreal.MathLibrary.make_rot_from_x(direction), (.55, .38, .38), .19, 2.)
        self.arrows.append({'actor': actor, 'trail': trail, 'origin': origin,
            'direction': direction, 'range': sentry['range'], 'born': _now(self.rig), 'duration': duration})
        sentry['shots'] += 1
        sentry['shots_after_player_moved'] += int(player_moved)
        self.shots.append({'seconds': round(_now(self.rig)-self.started, 4),
            'sentry': self.sentries.index(sentry), 'origin': _vec(origin), 'direction': _vec(direction),
            'visual_only': True})

    def tick(self, player_moved):
        now, age = _now(self.rig), _now(self.rig)-self.started
        for sentry in self.sentries:
            if not _valid(sentry['actor']):
                continue
            drift = (sentry['actor'].get_actor_location()-sentry['fixed_location']).length()
            self.max_drift = max(self.max_drift, drift)
            if not sentry['started_animation'] and age >= sentry['offset']:
                rate_scale = max(abs(self.animation.get_editor_property('rate_scale')), .001)
                sentry['mesh'].set_play_rate(self.animation.get_play_length()/(CADENCE*rate_scale))
                sentry['started_animation'] = True
            if age >= sentry['next_shot'] and age < LIFETIME-.65:
                self.fire(sentry, player_moved)
                sentry['next_shot'] += CADENCE
            # Only this instance's material fades; the asset and real D are untouched.
            visibility = min(1., age/.18, max(0., (LIFETIME-age)/.28))*.9
            sentry['mid'].set_scalar_parameter_value('Visibility', visibility)
        for arrow in self.arrows[:]:
            elapsed = now-arrow['born']
            distance = min(arrow['range'], elapsed*SPEED)
            point = arrow['origin']+arrow['direction']*distance
            if _valid(arrow['actor']):
                arrow['actor'].set_actor_location(point, False, True)
            if _valid(arrow['trail']):
                arrow['trail'].set_world_location(point, False, False)
            if elapsed >= arrow['duration']:
                if _valid(arrow['actor']):
                    arrow['actor'].destroy_actor()
                if _valid(arrow['trail']):
                    arrow['trail'].deactivate()
                    arrow['trail'].destroy_component(arrow['trail'])
                self.pulse('impact', ('Sparks', 'Wisps'), point,
                    unreal.MathLibrary.make_rot_from_x(arrow['direction']), (.40, .24, .24), .25, 2.)
                self.impacts.append({'seconds': round(age, 4), 'position': _vec(point), 'visual_only': True})
                self.arrows.remove(arrow)
        self.fx.tick()

    def close(self):
        self.fx.close()
        self.arrows.clear()
        for actor in self.actors:
            if _valid(actor):
                actor.destroy_actor()
        self.actors.clear()


def sequence(rig):
    rig['switch']('countess')
    yield .2
    rig['switch']('sparrow')
    yield .65
    rig['case'](PREFIX+'_prototype_only')
    targets = rig['layout']([(650, -165), (650, 165), (850, 400)])
    yield .2
    rig['check'](not _owned_actors(rig), 'no old stationary-sentry prototype actors remain')
    native_count = len(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))
    health = [rig['health'](d) for d in targets]
    pawn_start = rig['pawn']().get_actor_location()
    study = Study(rig, targets)
    moved, movement_sent, video_finished, held = False, False, False, False
    lifetime_sample = None
    try:
        study.spawn()
        if os.environ.get('NEW_SKILLS_VIDEO') == '1':
            rig['STATE']['video_clip'] = {'case': PREFIX+'_prototype_only',
                'prefix': PREFIX+'_video', 'cast_time': study.started, 'frame_times': []}
        captures = [.45, 1.7, 3.5]
        while _now(rig)-study.started < LIFETIME+.22:
            age = _now(rig)-study.started
            if not movement_sent and age >= .9:
                goal = rig['ground'](pawn_start.x+300., pawn_start.y+380.)
                rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                held, movement_sent = True, True
            elif held:
                rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                held = False
            moved = moved or (rig['pawn']().get_actor_location()-pawn_start).length() > 120.
            study.tick(moved)
            if captures and age >= captures[0]:
                moment = captures.pop(0)
                rig['capture'](PREFIX+'_'+str(round(moment*100)).zfill(3))
            if age >= 4.5 and not video_finished:
                rig['finish_video_clip']()
                video_finished = True
            if lifetime_sample is None and 7.80 <= age < 7.95:
                lifetime_sample = {'seconds': round(age, 4),
                    'living_sentries': sum(_valid(s['actor']) for s in study.sentries)}
            yield 1./rig['FPS']
        rig['check'](moved, 'the real player moves by right-click while the prototype fires')
        rig['check'](study.max_drift < .01, 'both sentries remain at their spawn locations while the player moves')
        rig['check'](all(s['shots_after_player_moved'] >= 4 for s in study.sentries),
                     'both fixed sentries continue repeated shots after the player has moved')
        rig['check'](lifetime_sample and lifetime_sample['living_sentries'] == 2,
                     'both sentries remain present near the end of the full eight-second lifetime')
        rig['check'](all(not _valid(s['actor']) for s in study.sentries),
                     'both prototype sentries expire automatically after eight seconds')
        rig['check']([rig['health'](d) for d in targets] == health,
                     'all prototype projectiles and impact effects deal zero damage')
        rig['check'](len(unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowMirrorArcher)) == native_count,
            'the prototype does not invoke or modify native D partner actors')
        report = {'passed': True, 'name': 'D 고정 설치형 황금 궁수 2명',
            'prototype_only': True, 'installed': False, 'D_key_invoked': False, 'assets_saved': False,
            'lifetime_seconds': LIFETIME, 'video_seconds': 4.5, 'cadence_seconds': CADENCE,
            'arrow_speed_cm_per_second': SPEED, 'native_animation': ANIMATION,
            'native_mesh': study.source_mesh.get_path_name(), 'echo_material': ECHO,
            'arrow_mesh': ARROW, 'trail_particle': TRAIL, 'fixed_aim_directions': True,
            'positions': [_vec(s['fixed_location']) for s in study.sentries],
            'maximum_stationary_drift_cm': study.max_drift, 'player_moved': moved,
            'shots_per_sentry': [s['shots'] for s in study.sentries],
            'shots_after_player_moved': [s['shots_after_player_moved'] for s in study.sentries],
            'lifetime_sample': lifetime_sample, 'shots': study.shots, 'visual_impacts': study.impacts,
            'clip': {'case': PREFIX+'_prototype_only', 'prefix': PREFIX+'_video',
                     'source': 'actual PIE prototype presentation', 'visual_only_no_damage': True},
            'visual_acceptance': 'pending actual game video review',
            'limitations': ['This is a visual decision prototype, not an installed D replacement.',
                            'It has fixed aim and visual arrivals; target acquisition, collision and damage are not implemented.',
                            'The existing native attack animation is looped; no new animation or asset is saved.']}
    finally:
        rig['finish_video_clip']()
        if held:
            rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        study.close()
    yield .12
    remaining_fx = [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                    if _valid(p) and TAG in p.get_editor_property('component_tags')]
    rig['check'](not _owned_actors(rig) and not remaining_fx,
                 'all temporary stationary-sentry actors, arrows and particles are destroyed')
    report['temporary_actors_and_particles_cleaned'] = True
    (Path(rig['OUT'])/'sentry-decision-study.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
