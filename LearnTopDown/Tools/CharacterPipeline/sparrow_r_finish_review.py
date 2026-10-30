"""R native impact texture without large Flare/light; A retains the three Flare bursts.

SPARROW_HIT_FLASH_CASES=R,A,A_wall,A_owner_cleanup,R_cancel,R_S_restore selects scoped repair cases.
"""
import json
import os
import unreal


GOLD_MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowAscensionGold.M_SparrowAscensionGold'


def material_chain(material):
    """Keep the actual MID parent path; a material instance name is not its base asset name."""
    rows = []
    visited = set()
    while material is not None and material.get_path_name() not in visited:
        path = material.get_path_name()
        visited.add(path)
        row = {'path': path, 'class': material.get_class().get_name()}
        rows.append(row)
        if not isinstance(material, unreal.MaterialInstance):
            break
        try:
            material = material.get_editor_property('parent')
        except Exception as exc:
            row['parent_read_error'] = str(exc)
            break
    return rows


def uses_gold(material):
    return any(row['path'] == GOLD_MATERIAL for row in material_chain(material))


def sequence(rig):
    selected = {s.strip() for s in os.environ.get(
        'SPARROW_HIT_FLASH_CASES', 'R,A,A_wall,A_owner_cleanup').split(',') if s.strip()}
    rig['check'](not selected.difference({'R', 'A', 'A_wall', 'A_owner_cleanup', 'R_cancel', 'R_S_restore'}),
                 'hit flash case filter contains known cases')
    report = {'passed': False, 'cases': sorted(selected), 'R_emitters': [], 'A_flashes': {}}

    def save():
        (rig['OUT'] / 'sparrow-r-finish-review.json').write_text(
            json.dumps(report, indent=2), encoding='utf-8')

    def flashes():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowTransferredHitFlash) if unreal.SystemLibrary.is_valid(a)]

    def record(name):
        if os.environ.get('NEW_SKILLS_VIDEO') == '1':
            rig['STATE']['video_clip'] = {
                'case': name, 'prefix': name + '_video',
                'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                'frame_times': []}

    def audit_r_emitters():
        arrows = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow)
                  if 'SparrowMultishotArrow' in {str(t) for t in a.tags}]
        rig['check'](bool(arrows), 'real R arrows are present for emitter audit')
        for arrow in arrows[:3]:
            target = [str(n) for n in arrow.get_target_impact_emitter_names()]
            wall = [str(n) for n in arrow.get_world_impact_emitter_names()]
            light_modules = arrow.has_impact_light_modules()
            report['R_emitters'].append({'target': target, 'wall': wall, 'has_light_modules': light_modules})
            for names in (target, wall):
                rig['check']({'Main Flames', 'Wisps', 'Sparks'}.issubset(names),
                             'R target and wall retain native flame, wisp and spark impact layers')
                rig['check'](not any('flare' in n.lower() or 'light' in n.lower() or
                                     n == 'Particle Emitter' for n in names),
                             'R impact excludes only large Flare and light emitters')
            rig['check'](not light_modules, 'R impact has no particle light modules')
        save()

    def observe_a(label):
        for flash in flashes():
            entry = report['A_flashes'].setdefault(flash.get_name(), {
                'case': label, 'max_pulses': 0, 'location': rig['vec'](flash.get_actor_location())})
            entry['max_pulses'] = max(entry['max_pulses'], flash.get_pulse_count())

    def fresh(name):
        rig['switch']('countess')
        yield .2
        rig['switch']('sparrow')
        yield .7
        rig['case'](name)
        targets = rig['layout']([(340, 0), (600, 0), (600, 350)])
        yield .2
        return targets

    save()
    if 'R' in selected:
        yield from r_sequence(rig, record, audit_r_emitters, report)
    if 'R_cancel' in selected or 'R_S_restore' in selected:
        yield from bow_restore_sequence(rig, selected, report)
    if 'A' in selected:
        targets = yield from fresh('A_transferred_flash')
        rig['use']('A', targets[0])
        record('A_transferred_flash')
        captured = False
        flight_crackle_seen = False
        arrow_checked = False
        for _ in range(round(4.2 * rig['FPS'])):
            yield 1.0 / rig['FPS']
            observe_a('A')
            arrows = rig['tagged']('SparrowGearArrow')
            if arrows and not arrow_checked:
                arrow = arrows[0]
                tip = next(c for c in arrow.get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'ArrowMesh')
                scale = tip.get_editor_property('relative_scale3d')
                rig['check'](abs(arrow.get_flight_speed()-160.) < .01 and arrow.is_piercing(),
                             'shorter A preserves160speed and piercing')
                rig['check'](abs(scale.x-1.35) < .001 and abs(scale.z-1.1475) < .001,
                             'A arrow length is15percent shorter without narrowing its width')
                arrow_checked = True
            if arrows and any(unreal.Name('SparrowGearFlightCrackle') in c.get_editor_property('component_tags')
                              for c in arrows[0].get_components_by_class(unreal.ParticleSystemComponent)):
                flight_crackle_seen = True
            if not captured and any(f.get_pulse_count() == 3 for f in flashes()):
                rig['capture']('A_transferred_flash_three_bursts')
                captured = True
        rig['finish_video_clip']()
        rig['recovered']()
        rig['check'](captured, 'A performs three transferred Flare bursts at a real impact')
        rig['check'](arrow_checked and flight_crackle_seen, 'A has short owned crackles during flight')
        rig['check'](abs(rig['health'](targets[0]) - 10.) < .02 and
                     abs(rig['health'](targets[1]) - 10.) < .02,
                     'A still deals90damage once to each pierced target with no burst damage')
        rig['check'](abs(rig['health'](targets[2]) - 100.) < .02,
                     'A excludes the off-axis target')
        rows = [v for v in report['A_flashes'].values() if v['case'] == 'A']
        rig['check'](len(rows) == 2 and all(v['max_pulses'] == 3 for v in rows),
                     'two A hits each create exactly three cosmetic pulses')
        save()
    if 'A_wall' in selected:
        targets = yield from fresh('A_wall_flash_survives_projectile')
        barrier = rig['wall_fixture'](250)
        try:
            rig['use']('A', targets[0])
            saw_finished_flash = False
            for _ in range(round(2.4 * rig['FPS'])):
                yield 1.0 / rig['FPS']
                observe_a('A_wall')
                if any(f.get_pulse_count() == 3 for f in flashes()):
                    rig['check'](not rig['tagged']('SparrowGearArrow'),
                                 'A projectile has retired while its third wall flash still plays')
                    rig['capture']('A_wall_flash_after_projectile')
                    saw_finished_flash = True
                    break
            rig['check'](saw_finished_flash, 'wall flash completes all three pulses after A retires')
            rig['check'](all(abs(rig['health'](d) - 100.) < .02 for d in targets),
                         'A wall flashes add no damage behind the wall')
            yield .4
            rig['check'](not flashes(), 'wall flash actors expire after the short burst')
        finally:
            if unreal.SystemLibrary.is_valid(barrier):
                barrier.destroy_actor()
        save()
    if 'A_owner_cleanup' in selected:
        targets = yield from fresh('A_flash_owner_cleanup')
        rig['use']('A', targets[0])
        saw_flash = False
        for _ in range(round(2.8 * rig['FPS'])):
            yield 1.0 / rig['FPS']
            if flashes():
                saw_flash = True
                break
        rig['check'](saw_flash, 'owner cleanup begins during a real A impact burst')
        before = [rig['health'](d) for d in targets]
        rig['switch']('countess')
        yield .2
        rig['check'](not flashes(), 'owner switch removes transferred flash actors and pending pulses')
        yield .4
        rig['check']([rig['health'](d) for d in targets] == before,
                     'owner cleanup leaves no delayed A or cosmetic burst damage')
        save()
    report.update(passed=True, expected_arrows=186, expected_waves=6, expected_R_damage=60,
                  transferred_flash_scale=0.65 * (2.0 / 3.0), user_aesthetic_acceptance='pending')
    save()


def r_sequence(rig, record, audit_r_emitters, report):
    rig['switch']('sparrow')
    yield .8
    rig['case']('R_clean_finish')
    targets = rig['layout']([(650, 0), (250, 650), (250, -650)])
    yield .2
    mesh = rig['pawn']().get_editor_property('mesh')
    bow_slot = mesh.get_material_index('M17_Bow')
    rig['check'](bow_slot == 6, 'R targets the audited bow-only Rogue material slot')
    originals = [mesh.get_material(i) for i in range(mesh.get_num_materials())]
    requested_at = unreal.GameplayStatics.get_time_seconds(rig['world']())
    rig['use']('R', targets[0])
    report['R_bow_input'] = {'requested_at': requested_at, 'bow_slot': bow_slot,
        'queued_before_input_tick': {'casting': rig['skills']().is_casting(),
            'active_skill': rig['skills']().get_active_skill_number(),
            'material': material_chain(mesh.get_material(bow_slot))}}
    record('R_clean_finish')
    # Console key commands enqueue Enhanced Input; inspect its first processed frame, not the queueing callback.
    yield 1. / rig['FPS']
    accepted_at = unreal.GameplayStatics.get_time_seconds(rig['world']())
    elapsed = accepted_at - requested_at
    report['R_bow_input']['first_processed_frame'] = {
        'time': accepted_at, 'elapsed_seconds': elapsed, 'fps': rig['FPS'],
        'casting': rig['skills']().is_casting(), 'active_skill': rig['skills']().get_active_skill_number(),
        'feedback': str(rig['skills']().get_input_feedback()),
        'changed_slots': [i for i in range(len(originals)) if mesh.get_material(i) != originals[i]],
        'material': material_chain(mesh.get_material(bow_slot)),
        'tint_actors': [a.get_path_name() for a in rig['tagged']('SparrowMultishotBowTint')]}
    (rig['OUT'] / 'sparrow-r-finish-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    rig['check'](rig['skills']().is_casting() and mesh.get_material(bow_slot) != originals[bow_slot] and
                 uses_gold(mesh.get_material(bow_slot)), 'R bow is gold on the first processed input frame')
    rig['check'](all(mesh.get_material(i) == originals[i] for i in range(len(originals)) if i != bow_slot),
                 'R tint leaves the body string and arrow slots unchanged')
    observed_scales = []
    for label, moment in (('first', .16), ('dense', .32), ('last_wave', .61),
                          ('bow_decay', .78), ('target_decay', .96), ('end', 1.20)):
        while elapsed < moment-0.0001:
            step = min(1./rig['FPS'], moment-elapsed)
            yield step
            elapsed += step
            for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
                if unreal.SystemLibrary.is_valid(particle) and particle.is_active() and \
                        unreal.Name('SparrowMultishotImpact') in particle.get_editor_property('component_tags'):
                    observed_scales.append(round(particle.get_world_scale().x, 5))
        rig['capture']('R_clean_finish_' + label)
        if label == 'first':
            audit_r_emitters()
    yield .4
    rig['finish_video_clip']()
    rig['recovered']()
    rig['check'](all(mesh.get_material(i) == originals[i] for i in range(len(originals))) and
                 not rig['tagged']('SparrowMultishotBowTint'), 'R completion restores the exact original bow material')
    rig['check'](observed_scales and any(abs(v-.325) < .001 for v in observed_scales),
                 'actual R target impact component has half-size .325 scale')
    report['R_impact_scales'] = sorted(set(observed_scales))
    rig['check'](abs(rig['health'](targets[0]) - 40.) < .02,
                 'R retains60damage from six shared-hit waves')
    rig['check'](abs(rig['health'](targets[1]) - 100.) < .02 and
                 abs(rig['health'](targets[2]) - 100.) < .02,
                 'R excludes far side fixtures')
    rig['switch']('countess')
    yield .4


def bow_restore_sequence(rig, selected, report):
    rig['switch']('sparrow')
    yield .7
    mesh = rig['pawn']().get_editor_property('mesh')
    original = mesh.get_material(6)
    if 'R_cancel' in selected:
        rig['case']('R_immediate_bow_cancel')
        targets = rig['layout']([(650, 0), (250, 650), (250, -650)])
        rig['use']('R', targets[0])
        yield .04
        mesh.get_anim_instance().montage_stop(.02)
        yield .2
        rig['check'](mesh.get_material(6) == original and not rig['tagged']('SparrowMultishotBowTint'),
                     'R cancellation restores bow tint before any wave release')
        rig['check'](all(rig['health'](d) == 100 for d in targets), 'early R cancellation releases no damage')
        rig['recovered']()
    if 'R_S_restore' in selected:
        rig['case']('R_bow_S_restoration')
        targets = rig['layout']([(650, 0), (250, 650), (250, -650)])
        rig['use']('V', targets[0])
        yield 1.6
        forms = rig['tagged']('SparrowAscensionWings')
        rig['check'](len(forms) == 1, 'S form is present before R tint overlap')
        rig['use']('R', targets[0])
        yield .18
        # Exercise S's actual EndPlay restoration during R without waiting40seconds for its timer.
        forms[0].destroy_actor()
        yield .08
        rig['check'](uses_gold(mesh.get_material(6)),
                     'R keeps an immediate gold bow when S restores the body during its cast')
        yield 1.0
        rig['check'](mesh.get_material(6) == original and not rig['tagged']('SparrowMultishotBowTint'),
                     'R restores the post-S bow instead of reviving the expired S material')
        rig['recovered']()
        report['R_S_restore'] = 'real S actor EndPlay during R; no duration change'
