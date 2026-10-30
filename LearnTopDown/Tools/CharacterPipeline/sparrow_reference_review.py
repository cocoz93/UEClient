"""Use the existing actual-input PIE rig for the new S/D and E appearance.

SPARROW_REFERENCE_PARTS=E,S,D (visual) or S_cancel,D_cancel,S_wall,D_wall,
S_switch,D_switch,S_cooldown,D_cooldown,S_form,D_form,F.
Form cases keep the native damage checks, then use Space, left-click and
right-click without relocating the player. No asset saves or synthetic damage.
"""
import json
import os
import unreal


def sequence(rig):
    selected = os.environ.get('SPARROW_REFERENCE_PARTS', 'E,S,D').split(',')
    report = {'passed': False, 'fps': rig['FPS'], 'cases': []}
    frame = 1 / rig['FPS']
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())

    def save():
        (rig['OUT'] / 'sparrow-reference-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def objects(name):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), getattr(unreal, name))
                if unreal.SystemLibrary.is_valid(a)]

    def snapshot():
        pawn = rig['pawn']()
        move = pawn.get_editor_property('character_movement')
        return {'casting': rig['skills']().is_casting(), 'active': rig['skills']().get_active_skill_number(),
                'busy': pawn.is_combat_busy(), 'mode': str(move.get_editor_property('movement_mode')),
                'orient': move.get_editor_property('orient_rotation_to_movement'),
                'root': str(pawn.get_editor_property('mesh').get_anim_instance().get_editor_property('root_motion_mode'))}

    for name in selected:
        if not name:
            continue
        letter = name.split('_')[0]
        sharp_style = int(name[3:]) if name.startswith('S_C') else 0
        detail_style = int(name.split('_')[1][1:]) if name.startswith('S_T') else 0
        art_style = detail_style - 5 if 6 <= detail_style <= 11 else 0
        visual_case = name in ('E', 'S', 'D', 'F') or (name.startswith(('S_C', 'S_T')) and name.count('_') == 1)
        rig['cmd']('Sparrow.Sharp.Preview ' + str(sharp_style))
        rig['cmd']('Sparrow.Sharp.DetailPreview ' + str(0 if art_style else detail_style))
        rig['cmd']('Sparrow.Sharp.ArtPreview ' + str(art_style))
        rig['check'](letter in ('E', 'S', 'D', 'F'), 'known reference review key')
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .7
        rig['cmd']('CountessComboQA.FlushInput')
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns ' + ('0' if name.endswith('cooldown') else '1'))
        rig['case']('Reference_' + name)
        offsets = [(420, 0), (700, 0), (600, 370)]
        if letter == 'S':
            offsets = [(260, 0), (650, 0), (320, 230)]
            if name == 'S_spread':
                offsets = [(260, -40), (380, 40), (650, 0)]
        targets = rig['layout'](offsets)
        yield .2
        row = {'name': name, 'initial': snapshot(), 'arrows': {}, 'waves': 0, 'hits': []}
        if letter == 'E':
            row['holy_bow'] = {'seen': False, 'materials_ready': False, 'shots': 0}
            row['holy_impacts'] = []
        report['cases'].append(row); save()
        wall = rig['wall_fixture'](170 if letter == 'S' else 250) if name.endswith('wall') else None
        try:
            if name.endswith('form'):
                rig['use']('V', offset=(950, 0))
                yield 1.65
                rig['recovered']()
                row['form_remaining_at_cast'] = rig['skills']().get_ascension_remaining()
                rig['check'](row['form_remaining_at_cast'] > 37 and len(objects('SparrowAscensionWings')) == 1,
                             name + ' starts inside the actual V transformation')
                row['initial'] = snapshot()
                save()
            started = now()
            rig['use'](letter, offset=(950, 0))
            if visual_case and os.environ.get('NEW_SKILLS_VIDEO') == '1':
                rig['STATE']['video_clip'] = {'case': name, 'prefix': 'Reference_' + name + '_video',
                                             'cast_time': started, 'frame_times': []}
            yield frame
            rig['check'](rig['skills']().is_casting(), name + ' actual key starts casting')
            rig['check'](rig['skills']().get_active_skill_number() == {'E': 3, 'S': 10, 'D': 11, 'F': 12}[letter],
                         name + ' keeps the requested HUD slot')
            old = [rig['health'](d) for d in targets]
            moments = [.18, .28, .38, .43, .50, .75] if letter == 'E' else [.10, .25, .40, .53, .57, .65, .75]
            if letter == 'S':
                moments = [.10, .20, .30, .36, .40, .43, .47, .53, .60, .75]
            cancelled = False
            while now() - started < {'E': 1.7}.get(letter, 1.25):
                elapsed = now() - started
                for a in objects('SparrowArrow'):
                    if a.get_owner() == rig['pawn']():
                        row.setdefault('first_arrow_observed', elapsed)
                        row['arrows'].setdefault(a.get_name(), {'speed': a.get_flight_speed(), 'piercing': a.is_piercing(),
                                                               'world_pass': a.passes_world(), 'tags': [str(t) for t in a.tags]})
                        if letter == 'S':
                            if 'impact_emitters' not in row:
                                row['impact_emitters'] = [str(n) for n in a.get_target_impact_emitter_names()]
                                row['impact_has_lights'] = a.has_impact_light_modules()
                            origin = a.get_actor_location() - a.get_flight_direction() * a.get_distance_travelled()
                            row['arrows'][a.get_name()]['origin'] = [origin.x, origin.y, origin.z]
                            row['arrows'][a.get_name()]['range'] = a.get_remaining_range() + a.get_distance_travelled()
                            direction = a.get_flight_direction()
                            row['arrows'][a.get_name()]['direction'] = [direction.x, direction.y, direction.z]
                for a in objects('SparrowSharpVolley'):
                    row['waves'] = max(row['waves'], a.get_waves_fired())
                    if art_style:
                        surfaces = [c for c in a.get_components_by_class(unreal.StaticMeshComponent)
                                    if 'SparrowSharpArt' in [str(t) for t in c.component_tags]]
                        row['art_surfaces'] = max(row.get('art_surfaces', 0), len(surfaces))
                        row['art_materials'] = sorted({c.get_material(0).get_path_name() for c in surfaces if c.get_material(0)})
                    if a.get_release_origins():
                        row['aperture_origins'] = [[v.x, v.y, v.z] for v in a.get_release_origins()]
                    if detail_style == 5:
                        flows = [c for c in a.get_components_by_class(unreal.StaticMeshComponent)
                                 if 'SparrowSharpFlow' in [str(t) for t in c.component_tags]]
                        row['flow_count'] = max(row.get('flow_count', 0), len(flows))
                        row['flow_materials_ready'] = all(c.get_material(0) for c in flows) and len(flows) == 5
                        if wall and a.get_waves_fired():
                            for c in flows:
                                if c.is_visible():
                                    forward = unreal.MathLibrary.get_forward_vector(c.get_world_rotation())
                                    end = c.get_world_location() + forward * (c.get_world_scale().x * 50.)
                                    clearance = wall.get_actor_location().x - 15. - end.x
                                    row['min_flow_wall_clearance'] = min(row.get('min_flow_wall_clearance', clearance), clearance)
                if letter in ('D', 'F'):
                    for gather in objects('SparrowGatherShot'):
                        parts = gather.get_components_by_class(unreal.StaticMeshComponent)
                        row['gather_surfaces'] = max(row.get('gather_surfaces', 0), len(parts))
                        row['gather_materials_ready'] = all(c.get_material(0) for c in parts)
                    row['barrier_count'] = max(row.get('barrier_count', 0), len(objects('SparrowSanctuary')))
                if letter == 'S':
                    for impact in objects('SparrowSharpImpact'):
                        row.setdefault('sharp_impacts', {}).setdefault(impact.get_name(), elapsed)
                if letter == 'E':
                    for bow in objects('SparrowHolyBow'):
                        if bow.is_impact():
                            if bow.get_name() not in row['holy_impacts']:
                                row['holy_impacts'].append(bow.get_name())
                            continue
                        row['holy_bow']['seen'] = True
                        row['holy_bow']['materials_ready'] |= bow.has_valid_materials()
                        row['holy_bow']['shots'] = max(row['holy_bow']['shots'], bow.get_shots_observed())
                health = [rig['health'](d) for d in targets]
                if health != old:
                    row['hits'].append({'elapsed': elapsed, 'damage': [a-b for a, b in zip(old, health)]}); old = health
                if not cancelled and elapsed >= .10 and name.endswith(('cancel', 'switch', 'queued_move')):
                    if name.endswith(('cancel', 'queued_move')):
                        if name in ('E_move_cancel', 'S_queued_move'):
                            position = rig['pawn']().get_actor_location()
                            row['move_requested_from'] = [position.x, position.y, position.z]
                            destination = rig['ground'](position.x, position.y + 250)
                            rig['cmd'](f'CountessComboQA.Mouse Press Right {destination.x} {destination.y} {destination.z}')
                            if name == 'S_queued_move':
                                # Sparrow deliberately finishes attacks and retains one movement click.
                                yield frame
                                rig['cmd'](f'CountessComboQA.Mouse Release Right {destination.x} {destination.y} {destination.z}')
                        else:
                            rig['cmd']('SparrowSanctuaryQA.Cancel')
                    else:
                        rig['switch']('countess')
                    cancelled = True
                if moments and elapsed >= moments[0] and visual_case:
                    rig['capture']('Reference_' + name + '_t' + str(round(moments.pop(0)*100)).zfill(3))
                yield frame
            rig['finish_video_clip']()
            row['damage'] = [100-rig['health'](d) for d in targets]
            if art_style:
                expected_surfaces = {1:2, 2:3, 3:3, 4:3, 5:14, 6:12}[art_style]
                rig['check'](row.get('art_surfaces') == expected_surfaces and len(row.get('art_materials', [])) == expected_surfaces,
                             name + ' loads authored spatial surfaces for the selected art design')
                rig['check'](not objects('SparrowSharpVolley'), name + ' clears all art surfaces with their owner')
            if detail_style == 5:
                rig['check'](row.get('flow_count') == 5 and row.get('flow_materials_ready'),
                             name + ' loads five authored directional energy paths')
                rig['check'](not objects('SparrowSharpVolley'), name + ' clears all flow surfaces with their owner')
                if wall:
                    rig['check'](row.get('min_flow_wall_clearance', 0.) >= -.1,
                                 name + ' visible energy paths end before the wall front face')
            if name.endswith(('cancel', 'switch', 'wall')):
                rig['check'](max(row['damage']) < .03, name + ' leaves no hits after rejection/cancel/boundary')
            elif letter == 'S':
                rig['check'](row['waves'] == 1 and len(row['arrows']) == 15, name + ' emits one close-range fifteen-arrow bundle')
                expected = [54, 54, 0] if name == 'S_spread' else [54, 0, 0]
                rig['check'](all(abs(a-b) < .03 for a, b in zip(row['damage'], expected)),
                             name + ' hits nearby targets once for 54 and excludes distant/off-axis targets')
                rig['check'](.37 <= row['first_arrow_observed'] <= .45, name + ' gathers before one release')
                origins = row.get('aperture_origins', [])
                rig['check'](len(origins) == 5 and len({tuple(round(x, 1) for x in p) for p in origins}) == 5,
                             name + ' releases from five distinct visible apertures')
                rig['check'](all(min(sum((x-y)**2 for x, y in zip(a['origin'], p)) for p in origins) <= 64.1
                                 for a in row['arrows'].values()), name + ' real arrow starts remain inside visible apertures')
                directions = [a['direction'] for a in row['arrows'].values()]
                rig['check'](all(sum((x-y)**2 for x, y in zip(d, directions[0])) < .00000001 for d in directions),
                             name + ' all fifteen arrows remain parallel')
                rig['check'](all(abs(a['range']-450) < .1 for a in row['arrows'].values()), name + ' all arrows have 450cm reach')
                rig['check'](len(row.get('sharp_impacts', {})) == sum(v > 0 for v in row['damage']),
                             name + ' creates one contact glow per damaged target')
                rig['check'](not objects('SparrowSharpImpact'), name + ' clears short contact glows')
            elif letter == 'D':
                rig['check'](len(row['arrows']) == 1, name + ' emits one real piercing arrow')
                rig['check'](all(abs(v-65) < .03 for v in row['damage'][:2]) and row['damage'][2] < .03,
                             name + ' pierces aligned targets for 65 each and excludes off-axis target')
            elif letter == 'F':
                rig['check'](len(row['arrows']) == 1, name + ' emits one real crystal arrow')
                rig['check'](all(abs(v-80) < .03 for v in row['damage'][:2]) and row['damage'][2] < .03,
                             name + ' crystal shot pierces aligned targets once for 80 each')
                rig['check'](.49 <= row['first_arrow_observed'] <= .57, name + ' gathers before its single release')
            elif letter == 'E':
                rig['check'](len(row['arrows']) == 1, 'E emits exactly one real native arrow')
                rig['check'](abs(row['damage'][0] - 60) < .03 and max(row['damage'][1:]) < .03,
                             'E applies the full base 60 once to the first target only')
                rig['check'](len(row['hits']) == 1 and len(row['holy_impacts']) == 1,
                             'E layered impact is one contact and does not produce extra damage events')
                rig['check'](.30 <= row['first_arrow_observed'] <= .42, 'E opens its bow before the first projectile')
                rig['check'](row['holy_bow']['shots'] == 1, 'E visual follows one actual successful emission')
            if letter == 'E':
                rig['check'](row['holy_bow']['seen'] and row['holy_bow']['materials_ready'], 'E uses the authored bow material')
                rig['check'](not objects('SparrowHolyBow'), name + ' leaves no bow or wave actor after recovery/cancel/switch')
                if name == 'E_move_cancel':
                    rig['cmd']('CountessComboQA.FlushInput')
            if letter in ('D', 'F'):
                rig['check'](row.get('barrier_count', 0) == 0, name + ' does not spawn the removed counter barrier')
                rig['check'](row.get('gather_surfaces') == (26 if letter == 'D' else 14) and row.get('gather_materials_ready'),
                             name + ' loads its complete spatial charge effect')
                rig['check'](not objects('SparrowGatherShot'), name + ' clears charge and release surfaces')
            if name == 'S_queued_move':
                position = rig['pawn']().get_actor_location()
                row['queued_move_distance'] = rig['dist'](unreal.Vector(*row['move_requested_from']), position)
                rig['check'](row['queued_move_distance'] > 120, name + ' executes the queued movement after the shot')
                rig['cmd']('CountessComboQA.FlushInput')
            if name.endswith('switch'):
                rig['check'](not objects('SparrowSharpVolley') and not objects('SparrowArrow'), name + ' owner transition removes casts/arrows')
            else:
                rig['recovered']()
                end = snapshot(); row['recovered'] = end
                rig['check'](all(end[k] == row['initial'][k] for k in ('mode', 'orient', 'root')), name + ' restores movement/rotation/root mode')
                if name.endswith('cooldown'):
                    rig['use'](letter, offset=(950, 0)); yield frame
                    row['repeat_feedback'] = rig['skills']().get_input_feedback()
                    rig['check'](not rig['skills']().is_casting() and row['repeat_feedback'] == 'Cooldown',
                                 name + ' immediate repeat is rejected by the real cooldown')
                if name.endswith('form'):
                    # The side route avoids the aligned damage fixtures; all input
                    # recovery checks continue from the actual blink destination.
                    before_blink = rig['pawn']().get_actor_location()
                    rig['aim'](offset=(0, -550))
                    rig['key']('SpaceBar')
                    yield frame
                    blink = objects('SparrowGoldRoll')
                    rig['check'](len(blink) == 1 and rig['skills']().get_active_skill_number() == 18,
                                 name + ' accepts actual Space after the completed cast')
                    row['blink'] = {'teleport': blink[0].is_teleporting(), 'duration': blink[0].get_roll_duration()}
                    rig['check'](row['blink']['teleport'] and abs(row['blink']['duration'] - .14) < .001,
                                 name + ' selects the transformed 0.14 second blink')
                    yield .45
                    rig['recovered']()
                    row['blink']['distance'] = rig['dist'](before_blink, rig['pawn']().get_actor_location())
                    row['blink']['restored'] = snapshot()
                    rig['check'](abs(row['blink']['distance'] - 480) < 3 and not objects('SparrowGoldRoll'),
                                 name + ' completes the real blink and clears its actor')
                    rig['check'](all(row['blink']['restored'][k] == row['initial'][k] for k in ('mode', 'orient', 'root')),
                                 name + ' restores movement/rotation/root mode after blink')
                    rig['check'](rig['skills']().get_ascension_remaining() > 30 and
                                 len(objects('SparrowAscensionWings')) == 1 and
                                 rig['pawn']().get_editor_property('mesh').is_visible(),
                                 name + ' keeps the transformed body and wings after blink')
                    rig['check'](not objects('SparrowArrow'), name + ' previous skill arrows finish before the basic attack')
                    basic = {'health_before': rig['health'](targets[0]), 'arrows': [], 'attacking_observed': False}
                    row['basic_after_blink'] = basic
                    point = rig['aim'](targets[0])
                    rig['cmd'](f'CountessComboQA.Mouse Press Left {point.x} {point.y} {point.z}')
                    yield frame
                    basic['attacking_observed'] = rig['pawn']().is_attacking()
                    rig['cmd'](f'CountessComboQA.Mouse Release Left {point.x} {point.y} {point.z}')
                    basic_started = now()
                    while now() - basic_started < 1.2:
                        basic['attacking_observed'] |= rig['pawn']().is_attacking()
                        for arrow in objects('SparrowArrow'):
                            if arrow.get_owner() == rig['pawn']() and arrow.get_name() not in basic['arrows']:
                                basic['arrows'].append(arrow.get_name())
                        yield frame
                    basic['damage'] = basic['health_before'] - rig['health'](targets[0])
                    rig['check'](basic['attacking_observed'] and basic['arrows'] and basic['damage'] > 0,
                                 name + ' accepts a real left click and its native basic arrow hits')
                    rig['recovered']()
                    rig['check'](not rig['pawn']().is_attacking(), name + ' single basic click returns to idle')
                    save()
                before = rig['pawn']().get_actor_location()
                point = rig['ground'](before.x, before.y + 250)
                rig['cmd'](f'CountessComboQA.Mouse Press Right {point.x} {point.y} {point.z}')
                yield frame
                rig['cmd'](f'CountessComboQA.Mouse Release Right {point.x} {point.y} {point.z}')
                yield .75
                row['move_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
                rig['check'](row['move_distance'] > 120, name + ' accepts actual movement after recovery')
            save()
        finally:
            rig['finish_video_clip']()
            rig['cmd']('CountessComboQA.FlushInput')
            if wall and unreal.SystemLibrary.is_valid(wall):
                wall.destroy_actor()
            rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
            rig['cmd']('Sparrow.Sharp.Preview 0')
            rig['cmd']('Sparrow.Sharp.DetailPreview 0')
            rig['cmd']('Sparrow.Sharp.ArtPreview 0')
            save()
    report['passed'] = True; save()
