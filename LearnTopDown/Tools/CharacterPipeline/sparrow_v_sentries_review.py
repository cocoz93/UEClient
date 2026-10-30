"""Installed V2 and native eight-second D sentries, with short actual PIE clips.

Use as a sparrow_feedback study. This helper never authors assets or modifies
native presentation; only fixture placement and normal controller input vary.
The parent owns editor/GPU execution and visual acceptance.
"""
import json
import math
import os
from pathlib import Path

import unreal


def _valid(value):
    return value is not None and unreal.SystemLibrary.is_valid(value)


def _now(rig):
    return unreal.GameplayStatics.get_time_seconds(rig['world']())


def _mirrors(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher))


def _wings(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings))


def _arrows(rig):
    return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow)
            if a.actor_has_tag('SparrowSentryArrow')]


def _clip(rig, name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name+'_video',
            'cast_time': _now(rig), 'frame_times': []}


def _sections(mesh):
    lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(mesh.get_skeletal_mesh_asset())
    return [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())]
            for lod in range(lods)]


def _materials(mesh):
    return [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())]


def sequence(rig):
    short = os.environ.get('SPARROW_VD_SHORT') == '1'
    rows = {}
    rig['switch']('countess')
    yield .2
    rig['switch']('sparrow')
    yield .65
    ds = rig['layout']([(650, -165), (650, 165), (850, 350)])
    yield .2
    body = rig['pawn']().get_editor_property('mesh')
    original_materials, original_sections = _materials(body), _sections(body)
    _clip(rig, 'V2_native_faster_unfold')
    start, observed, peak = _now(rig), None, 0
    seen = set()
    rig['use']('V', ds[0])
    moments = [.72, 1.05, 1.65]
    while _now(rig)-start < 2.30:
        elapsed = _now(rig)-start
        forms = _wings(rig)
        if forms and observed is None:
            rig['check'](len(forms) == 1, 'V creates exactly one native wing actor')
            wing = next(c for c in forms[0].get_components_by_class(unreal.SkeletalMeshComponent)
                        if c.get_name() == 'SerathWings')
            observed = {'play_rate_during_unfold': wing.get_play_rate(),
                'relative_scale': [wing.get_editor_property('relative_scale3d').x,
                                   wing.get_editor_property('relative_scale3d').y,
                                   wing.get_editor_property('relative_scale3d').z]}
            rig['check'](abs(observed['play_rate_during_unfold']-1.4) < .001, 'V unfolding is .8 times 1.75 = 1.4 play rate')
            rig['check'](all(abs(v-.8) < .001 for v in observed['relative_scale']), 'V retains its anchored shape at .8 scale')
        particles = [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                     if _valid(p) and unreal.Name('SparrowAscensionEntry') in p.get_editor_property('component_tags')]
        seen.update(p.get_path_name() for p in particles)
        peak = max(peak, sum(p.get_num_active_particles() for p in particles if p.is_active()))
        if moments and elapsed >= moments[0]:
            rig['capture']('V2_native_'+str(round(moments.pop(0)*100)).zfill(3))
        yield 1./rig['FPS']
    rig['recovered']()
    rig['check'](observed is not None and len(seen) == 12 and peak > 0,
                 'V2 emits twelve active native wing-local ignition, flame and tip accents')
    rig['check'](rig['skills']().get_ascension_remaining() > 37., 'V preserves the forty-second transformation')
    rig['check'](not [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                     if _valid(p) and unreal.Name('SparrowAscensionEntry') in p.get_editor_property('component_tags')],
                 'all short V entry components retire while the burning native wings remain')
    rows['V'] = {**observed, 'entry_components_seen': len(seen), 'peak_active_particles': peak,
        'clip_prefix': 'V2_native_faster_unfold_video', 'source': 'installed native V; no preview overlay'}

    # Native D is observed while V is still active: capes must belong to D, with
    # the player's hidden cloth and burning wings left untouched.
    _clip(rig, 'D_native_fixed_sentries')
    ds = rig['layout']([(650, -165), (650, 165), (850, 350)])
    yield .15
    player_start = rig['pawn']().get_actor_location()
    damage = float(rig['skills']().get_editor_property('basic_attack_damage'))*.30
    health = [rig['health'](d) for d in ds]
    history, health_events, fixed, clones = {}, [], {}, []
    started = _now(rig)
    cycle = rig['pawn']().get_basic_attack_cycle_seconds()
    rig['use']('D', ds[0])
    moved, move_sent, held, max_drift = False, False, False, 0.
    closed_video, e_sent, e_before, e_after, lifespan_probe = False, False, None, None, None
    try:
        while _now(rig)-started < 8.55:
            elapsed = _now(rig)-started
            actors = _mirrors(rig)
            if len(actors) == 2 and not clones:
                clones = actors
                for actor in clones:
                    key = actor.get_path_name()
                    fixed[key] = actor.get_actor_location()
                    history[key] = {'last_count': 0, 'shot_times': []}
                    mesh = next(c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)
                                if c.get_name() == 'MirrorArcherMesh')
                    for slot_name in ('M08_Cloak', 'M16_CloakStraps'):
                        slot = mesh.get_material_index(slot_name)
                        rig['check'](slot >= 0 and mesh.is_material_section_shown(slot, 0), 'D independently restores '+slot_name+' during V')
                    hood = mesh.get_material_index('M14_CloakHood')
                    rig['check'](hood >= 0 and not mesh.is_material_section_shown(hood, 0), 'D keeps its bare head')
                    rig['check'](len(actor.get_components_by_class(unreal.SkeletalMeshComponent)) == 1,
                                 'D does not copy V wings')
            for actor in clones:
                if not _valid(actor):
                    continue
                key, count = actor.get_path_name(), actor.get_echo_shot_count()
                max_drift = max(max_drift, (actor.get_actor_location()-fixed[key]).length())
                state = history[key]
                if count > state['last_count']:
                    rig['check'](count-state['last_count'] == 1, 'one autonomous D arrow per sentry attack')
                    state['shot_times'].append(elapsed)
                    state['last_count'] = count
            current = [rig['health'](d) for d in ds]
            for index, (before, after) in enumerate(zip(health, current)):
                loss = before-after
                if loss > .01:
                    rig['check'](abs(loss/damage-round(loss/damage)) < .002,
                                 'D target damage remains an integer count of thirty-percent basic shots')
                    health_events.append({'time': round(elapsed, 4), 'target': index, 'loss': round(loss, 4)})
            health = current
            if elapsed >= .9 and not move_sent:
                goal = rig['ground'](player_start.x+300., player_start.y+380.)
                rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                held, move_sent = True, True
            elif held:
                rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                held = False
            moved = moved or (rig['pawn']().get_actor_location()-player_start).length() > 120.
            if elapsed >= 1.8 and elapsed < 1.8+1.5/rig['FPS']:
                rig['capture']('D_native_fixed_while_player_moves')
            if elapsed >= 4.5 and not closed_video:
                rig['finish_video_clip']()
                closed_video = True
            if not short and elapsed >= 4.65 and not e_sent:
                e_before = [a.get_echo_shot_count() for a in clones]
                rig['use']('E', offset=(-450, 150))
                e_sent = True
            if elapsed >= 5.95 and e_sent and e_after is None:
                e_after = [a.get_echo_shot_count() for a in clones]
            if lifespan_probe is None and 7.95 <= elapsed < 8.10:
                lifespan_probe = sum(_valid(a) for a in clones)
            yield 1./rig['FPS']
        rig['check'](len(clones) == 2 and moved and max_drift < .01,
                     'two native D sentries remain fixed while the actual player moves')
        rig['check'](health_events, 'native sentry projectiles actually hit training targets')
        if not short:
            max_allowed = math.ceil(1.4/cycle)+1
            rig['check'](e_before is not None and e_after is not None and
                         all(0 < b-a <= max_allowed for a, b in zip(e_before, e_after)),
                         'E six-shot event does not multiply D autonomous shots')
        intervals = []
        for state in history.values():
            times = state['shot_times']
            intervals.extend(b-a for a, b in zip(times, times[1:]))
        rig['check'](intervals and all(abs(value-cycle) <= 2./rig['FPS']+.015 for value in intervals),
                     'D shot cadence matches the actual character montage and restart delay')
        rig['check'](lifespan_probe == 2 and not _mirrors(rig), 'D remains eight seconds from action then expires')
        rig['check'](rig['skills']().get_ascension_remaining() > 28., 'D expiration leaves the ongoing V form alive')
        rig['check'](all(rig['skills']().get_relentless_stacks(d) == 0 for d in ds),
                     'autonomous D shots neither gain nor apply Relentless stacks')
        rows['D'] = {'clip_prefix': 'D_native_fixed_sentries_video', 'expected_cycle': cycle,
            'observed_intervals': intervals, 'expected_damage_per_shot': damage, 'health_events': health_events,
            'max_drift_cm': max_drift, 'player_moved': moved, 'shot_counts': [s['last_count'] for s in history.values()],
            'e_before': e_before, 'e_after': e_after, 'alive_near_eight_seconds': lifespan_probe}
    finally:
        rig['finish_video_clip']()
        if held:
            rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
    for form in _wings(rig):
        form.destroy_actor()
    yield .12
    rig['check'](_materials(body) == original_materials and _sections(body) == original_sections,
                 'V restores exact pre-cast materials and all cloth section states after D coexistence')

    if short:
        rig['switch']('countess')
        yield .2
        rig['check'](not _mirrors(rig) and not _arrows(rig) and not _wings(rig),
                     'short V/D repeat ends with no native sentries, arrows or wing form')
        (Path(rig['OUT'])/'V-D-installed-review.json').write_text(json.dumps(
            {'passed': True, 'short_repeat': True,
             'source': 'actual installed V/D inputs and right-click movement; repeated cadence and lifetime checks',
             'assets_saved': False, 'visual_acceptance': 'pending parent actual viewport review', 'results': rows,
             'omitted_repeated_cases': ['E event-copy check', 'late-entering no-target damage', 'preparation cancellation']},
            ensure_ascii=False, indent=2), encoding='utf-8')
        return

    # Enemy-free launch must be a real zero-damage visual arrow. Move a fixture
    # into one already launched arrow before the next attack can acquire it.
    rig['switch']('countess')
    yield .2
    rig['switch']('sparrow')
    yield .65
    rig['case']('D_no_target_and_switch_cleanup')
    dummies = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.KwangTrainingDummy))
    locations = [(d, d.get_actor_location()) for d in dummies]
    try:
        origin = rig['pawn']().get_actor_location()
        for index, dummy in enumerate(dummies):
            dummy.reset_dummy()
            dummy.set_actor_location(origin+unreal.Vector(4000., 4000.+index*200., 0.), False, True)
        rig['use']('D', offset=(600, 0))
        start, found = _now(rig), None
        while _now(rig)-start < 1.2:
            arrows = _arrows(rig)
            if arrows:
                found = arrows[0]
                break
            yield 1./rig['FPS']
        rig['check'](_valid(found), 'D still sends visual arrows along its cast direction without enemies')
        dummy = dummies[0]
        before = rig['health'](dummy)
        dummy.set_actor_location(found.get_actor_location()+found.get_flight_direction()*90., False, True)
        yield .08
        rig['check'](rig['health'](dummy) == before, 'an enemy-free launched arrow retains zero damage if a target later enters its path')
        rig['switch']('countess')
        yield .2
        rig['check'](not _mirrors(rig) and not _arrows(rig), 'character switching clears both native sentries and their owned arrows')
        rows['empty_target'] = {'visual_arrow_observed': True, 'late_target_damage': 0, 'switch_cleanup': True}
    finally:
        for dummy, location in locations:
            if _valid(dummy):
                dummy.set_actor_location(location, False, True)
                dummy.reset_dummy()

    rig['switch']('sparrow')
    yield .65
    rig['case']('D_cancel_during_preparation')
    ds = rig['layout']([(650, -165), (650, 165), (850, 350)])
    rig['use']('D', ds[0])
    yield .05
    rig['check'](len(_mirrors(rig)) == 2 and all(not a.is_active() for a in _mirrors(rig)),
                 'D prepares exactly two inactive sentries before its action')
    rig['switch']('countess')
    yield .20
    rig['check'](not _mirrors(rig) and not _arrows(rig) and not _wings(rig),
                 'interrupting preparation destroys both pending sentries without a shot or retained form')
    rows['preparation_cancel_cleanup'] = True
    (Path(rig['OUT'])/'V-D-installed-review.json').write_text(json.dumps(
        {'passed': True, 'source': 'actual installed native skills through normal V/D/E and right-click inputs',
         'assets_saved': False, 'visual_acceptance': 'pending parent actual viewport review', 'results': rows},
        ensure_ascii=False, indent=2), encoding='utf-8')
