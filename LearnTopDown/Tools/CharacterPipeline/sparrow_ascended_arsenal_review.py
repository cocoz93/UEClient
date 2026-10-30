"""Normal/V-form comparisons from actual skill keys in the existing PIE rig.

SPARROW_ASCENDED_KEYS=Q,W,E,R,A,S,D,F selects skills. SPARROW_ASCENDED_MODES
defaults to normal,form. NEW_SKILLS_VIDEO=1 captures consecutive viewport PNGs:
4.4s for Q, 3.4s for A, 2s for the other skills. Named stills are always kept.
ASCENDED_ARSENAL_RECOVERY=1 additionally reuses the real-input recovery timing
review with V active. No source, animation, material, or project asset is saved.
SPARROW_SERAPH_POLISH=1 checks native HolyFlap/Idle poses and settles V for 3s.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

import unreal


def sequence(rig):
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1.0 / rig['FPS']
    seraph = os.environ.get('SPARROW_SERAPH_POLISH') == '1'
    recraft = seraph or os.environ.get('SPARROW_ASCENDED_RECRAFT') == '1'
    design_review = os.environ.get('SPARROW_GAME_DESIGN_REVIEW') == '1'
    e_design = unreal.SystemLibrary.get_console_variable_int_value('Sparrow.EDesign.Style') if design_review else 0
    keys = [x.strip() for x in os.environ.get('SPARROW_ASCENDED_KEYS', 'Q,W,E,R,A,S,D,F').split(',') if x.strip()]
    modes = [x.strip() for x in os.environ.get('SPARROW_ASCENDED_MODES', 'normal,form').split(',') if x.strip()]
    check(set(keys) <= set('QWERASDF') and bool(keys), 'known ascended arsenal skill keys')
    check(set(modes) <= {'normal', 'form'} and bool(modes), 'known normal/form review modes')
    source = Path(unreal.Paths.project_dir()) / 'Source' / 'LearnTopDown'
    sharp_text = (source / 'SparrowSharpVolley.cpp').read_text(encoding='utf-8-sig')
    skill_text = (source / 'SparrowSkillComponent.cpp').read_text(encoding='utf-8-sig')
    extra_text = (source / 'SparrowSkillComponentExtras.cpp').read_text(encoding='utf-8-sig')

    def constant(text, name):
        match = re.search(r'constexpr\s+(?:float|int32)\s+' + re.escape(name) + r'\s*=\s*([\d.]+)f?\s*;', text)
        if not match:
            raise AssertionError('Cannot verify source constant ' + name)
        return float(match[1])

    sharp_match = re.search(r'Skills->SpawnArrow\(Direction,\s*([\d.]+)f,\s*ShotRange,\s*ShotSpeed', sharp_text)
    check(bool(sharp_match), 'S damage contract is readable from its actual native SpawnArrow call')
    sharp_damage = float(sharp_match[1])
    sharp_count = int(constant(sharp_text, 'ApertureCount')) * 3  # native Lane=-1..1 loop
    r_count = int(constant(skill_text, 'MultishotWaveCount') * constant(skill_text, 'MultishotArrowsPerWave'))
    contract = {'S_damage': sharp_damage, 'S_arrows': sharp_count, 'R_arrows': r_count,
                'R_waves': int(constant(skill_text, 'MultishotWaveCount')),
                'W_arrows': int(constant(skill_text, 'PiercingShotCount')),
                'S_action': constant(sharp_text, 'FirstShot'), 'S_speed': constant(sharp_text, 'ShotSpeed'),
                'A_speed': constant(extra_text, 'GearSpeed'),
                'Q_pulses': int(constant(skill_text, 'HailPulseCount'))}
    report = {'passed': False, 'fps': rig['FPS'], 'keys': keys, 'modes': modes,
              'source_contract': contract, 'source_hashes': {
                  name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                  for name in ('SparrowSharpVolley.cpp', 'SparrowSkillComponent.cpp', 'SparrowSkillComponentExtras.cpp')},
              'cases': [], 'comparisons': []}
    paths = ('/AscendedArsenal20261026/', '/ArsenalAscended20261026/')
    form_tags = {'Q': {'SparrowAscendedBow', 'SparrowAscendedRain'},
                 'W': {'SparrowAscendedBow', 'SparrowAscendedContact'},
                 'E': {'SparrowAscendedHolyBow'},
                 'R': {'SparrowAscendedBow', 'SparrowAscendedContact'},
                 'A': {'SparrowAscendedGear'}, 'S': {'SparrowAscendedSharp'},
                 'D': {'SparrowAscendedGather'}, 'F': {'SparrowAscendedGather'}}
    count_tags = {} if recraft else {'S': ('SparrowSharpArt', 2, 4), 'D': ('SparrowGatherSurface', 26, 36)}
    classes = [getattr(unreal, name) for name in (
        'SparrowArrow', 'SparrowHolyBow', 'SparrowSharpVolley', 'SparrowSharpImpact',
        'SparrowGatherShot', 'SparrowAscendedShotFX')]
    if recraft:
        classes += [unreal.SparrowFlameStudies, unreal.SparrowFeatherTrail, unreal.SparrowArsenalStudyFX]
    if os.environ.get('SPARROW_REART_Q_SYNC') == '1':
        classes += [unreal.SparrowAscensionAccent]

    def save():
        (out / 'sparrow-ascended-arsenal.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def valid(obj):
        return obj is not None and unreal.SystemLibrary.is_valid(obj)

    def objects(cls):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), cls) if valid(a)]

    def owned(actor):
        for _ in range(4):
            if not valid(actor):
                return False
            if actor == rig['pawn']():
                return True
            actor = actor.get_owner()
        return False

    def state():
        pawn = rig['pawn']()
        movement = pawn.get_editor_property('character_movement')
        return {'casting': rig['skills']().is_casting(), 'busy': pawn.is_combat_busy(),
                'root': str(pawn.get_editor_property('mesh').get_anim_instance().get_editor_property('root_motion_mode')),
                'orient': movement.get_editor_property('orient_rotation_to_movement'),
                'visible': pawn.get_editor_property('mesh').is_visible(),
                'mode': str(movement.get_editor_property('movement_mode')),
                'form_remaining': rig['skills']().get_ascension_remaining()}

    def definition(key):
        if key == 'S':
            return {'damage': sharp_damage, 'action_time': contract['S_action'], 'source': 'native SharpVolley'}
        if key in 'QWER':
            values = rig['skills']().get_editor_property('skills')
            value = values['QWER'.index(key)]
        else:
            values = rig['skills']().get_editor_property('extra_skills')
            value = values[{'A': 0, 'D': 2, 'F': 3}[key]]
        return {field: float(value.get_editor_property(field))
                for field in ('damage', 'action_time', 'recovery_time', 'cooldown', 'range')}

    def material_paths(component):
        return sorted({material.get_base_material().get_path_name()
                       for index in range(component.get_num_materials())
                       if (material := component.get_material(index)) is not None})

    def wing_state():
        return [{'name': actor.get_name(), 'animation': str(actor.get_wing_animation_name()),
                 'position': actor.get_wing_animation_position(), 'attack': actor.is_wing_attack_active(),
                 'exiting': actor.is_visual_exiting()}
                for actor in objects(unreal.SparrowAscensionWings) if owned(actor)]

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    cmd('Sparrow.Sharp.Preview 0')
    cmd('Sparrow.Sharp.DetailPreview 0')
    cmd('Sparrow.Sharp.ArtPreview 0')
    if seraph and not design_review:
        cmd('Sparrow.ArsenalStudy.R 0')
    try:
        for key in keys:
            pair = {}
            for mode in modes:
                transformed = mode == 'form'
                cmd('CountessComboQA.FlushInput')
                old = rig['pawn']()
                old_was_sparrow = isinstance(old, unreal.SparrowCharacter)
                rig['switch']('countess'); yield .2
                if old_was_sparrow:
                    check(not valid(old) or old != rig['pawn'](), 'review switch changes the previous Sparrow owner')
                rig['switch']('sparrow'); yield .7
                case = key + '_' + mode
                rig['case']('Ascended_' + case)
                offsets = [(420, 0), (700, 0), (600, 370)]
                if key == 'S':
                    offsets = [(260, 0), (650, 0), (320, 230)]
                elif key == 'Q' and recraft:
                    offsets = [(420, 0), (-230, 0), (-380, 0)]
                elif key == 'A':
                    offsets = [(390, 0), (700, 350), (700, -350)]
                elif key == 'E' and e_design == 2:
                    offsets = [(330, 0), (700, 0), (330, 420)]
                targets = rig['layout'](offsets)
                if key == 'Q' and recraft:
                    check(max(t.get_actor_location().z for t in targets)-min(t.get_actor_location().z for t in targets)<20., 'Q boundary targets share the same floor height')
                yield .2
                if transformed:
                    rig['use']('V', offset=(950, 0))
                    yield 3.0 if seraph else 1.65
                    check(rig['skills']().get_ascension_remaining() > 35, case + ' starts in actual V form')
                else:
                    check(rig['skills']().get_ascension_remaining() == 0, case + ' starts outside V form')
                check(not rig['pawn']().is_combat_busy(), case + ' starts from a recovered action state')
                row = {'key': key, 'mode': mode, 'initial': state(), 'definition': definition(key),
                       'arrows': {}, 'actors': {}, 'hits': [], 'form_materials': [],
                       'form_tags': [], 'visible_form_components': [], 'max_tagged_surfaces': 0,
                       'capture_seconds': 4.4 if key == 'Q' else 3.4 if key == 'A' else 2.25 if seraph and key == 'W' else 2.0}
                report['cases'].append(row)
                pair[mode] = row
                health = [rig['health'](target) for target in targets]
                if transformed:
                    row['wing_components'] = [
                        {'name': component.get_name(), 'world_scale': rig['vec'](component.get_world_scale())}
                        for actor in objects(unreal.SparrowAscensionWings)
                        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent)]
                if seraph and key == 'W' and transformed:
                    row['wing_initial'] = wing_state()
                    row['wing_samples'] = []
                    check(len(row['wing_initial']) == 1 and row['wing_initial'][0]['animation'] == 'Idle_Pose_Wings' and
                          not row['wing_initial'][0]['attack'], case + ' begins with one native idle wing actor')
                started = now()
                rig['use'](key, offset=(420 if key == 'Q' or (key == 'E' and e_design >= 3) else 950, 0))
                if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                    rig['STATE']['video_clip'] = {'case': 'Ascended_' + case, 'prefix': case + '_video',
                                                 'cast_time': started, 'frame_times': []}
                moments = [.16, .32, .43, .57, .75, 1.25]
                if key == 'W' and transformed:
                    moments += [1.33, 1.45, 1.55, 1.70]
                    if seraph:
                        moments += [1.85, 2.05, 2.20]
                if key == 'Q':
                    moments += [2.25, 3.75, 4.25]
                elif key == 'Q' and recraft:
                    offsets = [(420, 0), (-230, 0), (-380, 0)]
                elif key == 'A':
                    moments += [1.9, 2.5, 3.2]
                actor_parts = {}
                observed_cast = False
                last_health = list(health)
                while now() - started < row['capture_seconds']:
                    elapsed = now() - started
                    if key == 'E' and e_design >= 7 and elapsed >= .30 and 'horizontal_bow' not in row:
                        mesh=rig['pawn']().get_editor_property('mesh')
                        axis=mesh.get_socket_location('bow_string_top')-mesh.get_socket_location('bow_string_bott')
                        span=(axis.x*axis.x+axis.y*axis.y+axis.z*axis.z)**.5
                        row['horizontal_bow']={'span':span,'vertical_fraction':abs(axis.z)/max(span,.001)}
                        check(row['horizontal_bow']['vertical_fraction'] < .25, case+' actual shooting pose keeps bow horizontal')
                        if os.environ.get('SPARROW_CRAFT_TEXTURE_AUDIT') == '1': cmd('ListTextures -alphasort')
                    observed_cast |= rig['skills']().is_casting()
                    if observed_cast and not rig['skills']().is_casting():
                        row.setdefault('control_recovered_at', elapsed)
                    if key == 'Q' and rig['skills']().get_active_hail_count():
                        row.setdefault('first_emission_observed', elapsed)
                    if key == 'E' and e_design == 2 and any(b.get_shots_observed() > 0 for b in objects(unreal.SparrowHolyBow) if owned(b) and not b.is_impact()):
                        row.setdefault('first_emission_observed', elapsed)
                    if seraph and key == 'W' and transformed:
                        for sample in wing_state():
                            row['wing_samples'].append({'elapsed': elapsed, **sample})
                    for cls in classes:
                        for actor in objects(cls):
                            if not owned(actor):
                                continue
                            actor_name = actor.get_name()
                            if recraft and not seraph and key == 'W' and transformed and isinstance(actor, unreal.SparrowFlameStudies) and actor.is_form_study():
                                row.setdefault('fold_actor_names', [])
                                if actor_name not in row['fold_actor_names']: row['fold_actor_names'].append(actor_name)
                                row['fold_max'] = max(row.get('fold_max', 0.), actor.get_form_fold_amount())
                                row['fold_active_at_end'] = actor.is_folding_form()
                            if actor_name not in row['actors']:
                                parts = actor.get_components_by_class(unreal.StaticMeshComponent)
                                actor_parts[actor_name] = parts
                                tags = [str(tag) for tag in actor.tags]
                                record = {'class': actor.get_class().get_name(), 'tags': tags,
                                          'first_observed': elapsed, 'components': []}
                                row['actors'][actor_name] = record
                                row['form_tags'] = sorted(set(row['form_tags']) | {tag for tag in tags if tag.startswith('SparrowAscended')})
                                for component in parts:
                                    bases = material_paths(component)
                                    component_record = {'name': component.get_name(), 'tags': [str(t) for t in component.component_tags],
                                                        'materials': bases, 'collision': str(component.get_collision_enabled())}
                                    record['components'].append(component_record)
                                    if any(any(prefix in base for prefix in paths) for base in bases):
                                        row['form_materials'] = sorted(set(row['form_materials']) | set(bases))
                                        check(component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION,
                                              case + ' form surface is visual-only and has no collision')
                                if key in count_tags:
                                    tag = count_tags[key][0]
                                    row['max_tagged_surfaces'] = max(row['max_tagged_surfaces'],
                                        sum(tag in item['tags'] for item in record['components']))
                            if isinstance(actor, unreal.SparrowArrow):
                                row.setdefault('first_emission_observed', elapsed)
                                if actor_name not in row['arrows']:
                                    direction = actor.get_flight_direction()
                                    row['arrows'][actor_name] = {'observed': elapsed, 'speed': actor.get_flight_speed(),
                                                                 'origin': rig['vec'](actor.get_actor_location() - direction * actor.get_distance_travelled()),
                                                                 'range': actor.get_remaining_range() + actor.get_distance_travelled(),
                                                                 'direction': rig['vec'](direction), 'hits': actor.get_hit_count()}
                                row['arrows'][actor_name]['hits'] = actor.get_hit_count()
                            if isinstance(actor, unreal.SparrowSharpVolley):
                                row['sharp_waves'] = max(row.get('sharp_waves', 0), actor.get_waves_fired())
                            # Component visibility is sampled after initialization too;
                            # merely allocating a form material does not prove it rendered.
                            for component, record in zip(actor_parts[actor_name], row['actors'][actor_name]['components']):
                                token = actor_name + '/' + component.get_name()
                                if token not in row['visible_form_components'] and component.is_visible() and \
                                        any(any(prefix in base for prefix in paths) for base in record['materials']):
                                    row['visible_form_components'].append(token)
                    current_health = [rig['health'](target) for target in targets]
                    if current_health != last_health:
                        row['hits'].append({'elapsed': elapsed, 'damage': [a-b for a, b in zip(last_health, current_health)]})
                        last_health = current_health
                    if moments and elapsed >= moments[0]:
                        rig['capture'](case + '_t' + str(round(moments.pop(0) * 1000)).zfill(4))
                    yield frame
                rig['finish_video_clip']()
                row['damage'] = [a-rig['health'](target) for a, target in zip(health, targets)]
                row['recovered'] = state()
                save()
                check(observed_cast and not row['recovered']['busy'] and not row['recovered']['casting'],
                      case + ' runs the actual cast and returns control')
                check(all(row['recovered'][field] == row['initial'][field] for field in ('root', 'orient', 'mode', 'visible')),
                      case + ' restores root motion, locomotion mode, orientation and visibility')
                expected_count = 0 if key == 'Q' else contract['R_arrows'] if key == 'R' else sharp_count if key == 'S' else contract['W_arrows'] + int(transformed) if key == 'W' else 3 if key == 'F' and transformed else 1
                if key == 'E' and e_design >= 2:
                    expected_count = 0 if e_design == 2 else 5 if 3 <= e_design <= 5 else 1
                check(len(row['arrows']) == expected_count, case + ' preserves native projectile count ' + str(expected_count))
                damage = row['definition']['damage']
                expected = [damage, damage, damage] if key == 'R' else \
                    [damage, damage, 0] if key in ('Q', 'W', 'D', 'F') else [damage, 0, 0]
                if key == 'Q' and recraft:
                    expected = [damage, damage if transformed else 0, 0]
                check(all(abs(a-b) < .05 for a, b in zip(row['damage'], expected)),
                      case + ' preserves native damage and target coverage')
                check(abs(row['first_emission_observed'] - row['definition']['action_time']) <= 3 * frame + .015,
                      case + ' preserves the authored first emission time')
                if key == 'Q':
                    check(len(row['hits']) == contract['Q_pulses'] and rig['skills']().get_active_hail_count() == 0,
                          case + ' completes the same eight-pulse hail lifetime')
                    if transformed and os.environ.get('SPARROW_REART_Q_SYNC') == '1':
                        expected_contacts=[row['first_emission_observed']+.82+i*.37 for i in range(8)]
                        row['expected_contact_times']=expected_contacts
                        check(len(row['hits'])==8 and all(abs(hit['elapsed']-contact)<=2*frame+.006
                              for hit,contact in zip(row['hits'],expected_contacts)),
                              case+' damage starts at the descending light contact and follows all eight contacts')
                        contacts=[record for record in row['actors'].values() if 'SparrowQGroundImpact' in record['tags']]
                        check(len(contacts)==8,case+' creates eight live initialized ground contact accents')
                if key == 'A':
                    check(all(abs(arrow['speed'] - contract['A_speed']) < .01 for arrow in row['arrows'].values()),
                          case + ' keeps the slow gear speed')
                if key == 'S':
                    check(row.get('sharp_waves') == 1 and len({tuple(a['direction']) for a in row['arrows'].values()}) == 1,
                          case + ' keeps one parallel close-range burst')
                if seraph and key == 'W' and transformed:
                    row['wing_final'] = wing_state()
                    holy = [sample for sample in row['wing_samples'] if sample['animation'] == 'E_Ability_Wing_Flap_Holy' and sample['attack']]
                    check(not holy and all(sample['animation'] == 'Idle_Pose_Wings' and not sample['attack'] for sample in row['wing_samples']),
                          'W fifth shot never changes the native idle wing pose')
                    final_arrows = [record for record in row['actors'].values() if record['class'] == 'SparrowArrow' and 'SparrowWFinalImpact' in record['tags']]
                    final_contacts = [record for record in row['actors'].values() if record['class'] == 'SparrowSharpImpact' and 'SparrowWFinalImpact' in record['tags']]
                    check(len(final_arrows) == 1 and bool(final_contacts),
                          'only the fifth W arrow creates the new actual-hit fracture effect')
                    check({sample['name'] for sample in row['wing_samples']} == {row['wing_initial'][0]['name']},
                          'W reuses the same native wing actor throughout its finishing shot')
                    check(len(row['wing_final']) == 1 and row['wing_final'][0]['name'] == row['wing_initial'][0]['name'] and
                          row['wing_final'][0]['animation'] == 'Idle_Pose_Wings' and not row['wing_final'][0]['attack'] and
                          not row['wing_final'][0]['exiting'] and rig['skills']().get_ascension_remaining() > 25,
                          'W restores native idle wings while keeping the same V transformation active')
                elif recraft and key == 'W' and transformed:
                    check(row.get('fold_max', 0.) > .90 and not row.get('fold_active_at_end', True),
                          'W folds the existing V3 surfaces and restores them after release')
                    check(len(row.get('fold_actor_names', [])) == 1,
                          'W keeps one existing V3 actor through its finishing shot')
                if key == 'F' and transformed:
                    check(len({tuple(a['direction']) for a in row['arrows'].values()}) == 1,
                          case + ' keeps all three real arrows parallel')
                    origins = [a['origin'] for a in row['arrows'].values()]
                    distances = sorted(sum((a-b)**2 for a, b in zip(origins[i], origins[j]))**.5
                                       for i, j in ((0, 1), (0, 2), (1, 2)))
                    check(all(abs(a-b) < .5 for a, b in zip(distances, [55.5698, 55.5698, 56.])),
                          case + ' keeps the three arrow origins in a triangle instead of a fan')
                if key in count_tags:
                    expected_surfaces = count_tags[key][2 if transformed else 1]
                    check(row['max_tagged_surfaces'] == expected_surfaces,
                          case + ' loads the correct normal/form spatial surface count')
                if transformed and not recraft:
                    check(form_tags[key] <= set(row['form_tags']), case + ' creates its own form-specific actor tags')
                    if not design_review:
                        check(bool(row['form_materials']) and bool(row['visible_form_components']),
                              case + ' loads and visibly enables the form-only material surfaces')
                    check(rig['skills']().get_ascension_remaining() > 25, case + ' preserves the same active V form')
                elif not transformed and not recraft:
                    check(not row['form_tags'] and not row['form_materials'], case + ' leaves normal skill effects unmodified by form materials')
                save()
            if set(pair) == {'normal', 'form'}:
                normal, form = pair['normal'], pair['form']
                comparison = {'key': key, 'same_definition': normal['definition'] == form['definition'],
                              'same_damage': all(abs(a-b) < .0001 for a,b in zip(normal['damage'], form['damage'])),
                              'normal_first_emission': normal['first_emission_observed'],
                              'form_first_emission': form['first_emission_observed']}
                report['comparisons'].append(comparison)
                check(comparison['same_definition'] and (comparison['same_damage'] or (recraft and key == 'Q')), key + ' normal/form differ in presentation while retaining gameplay values')
                check(abs(comparison['normal_first_emission'] - comparison['form_first_emission']) <= frame + .001,
                      key + ' normal/form emit on the same frame schedule')
                save()
        if os.environ.get('ASCENDED_ARSENAL_RECOVERY') == '1':
            reviewer = Path(unreal.Paths.project_dir()) / 'Tools' / 'CharacterPipeline' / 'sparrow_recovery_timing.py'
            spec = importlib.util.spec_from_file_location('sparrow_form_recovery_review', reviewer)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            saved = {name: os.environ.get(name) for name in ('SPARROW_RECOVERY_FORM', 'SPARROW_RECOVERY_KEYS')}
            try:
                os.environ['SPARROW_RECOVERY_FORM'] = '1'
                os.environ['SPARROW_RECOVERY_KEYS'] = ','.join(keys)
                yield from module.sequence(rig)
                report['form_recovery'] = json.loads((out / 'sparrow-recovery-timing.json').read_text(encoding='utf-8'))
            finally:
                for name, value in saved.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
        if 'Q' in keys and 'form' in modes:
            # A ground skill remains legal at the caster's own feet, where the
            # aim vector has no planar length. The bow must still use facing.
            cmd('CountessComboQA.FlushInput')
            rig['switch']('countess'); yield .2
            rig['switch']('sparrow'); yield .7
            rig['case']('Ascended_Q_self')
            rig['layout']([(650, 0), (700, 350), (700, -350)])
            yield .15
            rig['use']('V', offset=(950, 0)); yield 3.0 if seraph else 1.65
            rig['use']('Q', offset=(0, 0))
            self_started = now()
            self_row = {'tags': [], 'visible_surfaces': 0, 'hail_seen': False}
            while now() - self_started < .70:
                self_row['hail_seen'] |= rig['skills']().get_active_hail_count() > 0
                for actor in objects(unreal.SparrowAscendedShotFX):
                    if not owned(actor):
                        continue
                    self_row['tags'] = sorted(set(self_row['tags']) | {str(tag) for tag in actor.tags})
                    self_row['visible_surfaces'] = max(self_row['visible_surfaces'], sum(
                        component.is_visible() for component in actor.get_components_by_class(unreal.StaticMeshComponent)))
                yield frame
            rig['capture']('Q_form_self_t0700')
            check(self_row['hail_seen'] and {'SparrowAscendedBow', 'SparrowAscendedRain'} <= set(self_row['tags']),
                  'form Q at own feet keeps native rain and both form-only presentations')
            check(self_row['visible_surfaces'] > 0 and not rig['pawn']().is_combat_busy(),
                  'form Q at own feet visibly renders and leaves no casting lock')
            report['self_ground_Q'] = self_row
            rig['switch']('countess'); yield .2
            check(not objects(unreal.SparrowAscendedShotFX), 'owner switch clears remaining self-cast form Q effects')
            rig['switch']('sparrow'); yield .65
        report['passed'] = True
        save()
    finally:
        cmd('CountessComboQA.FlushInput')
        save()
