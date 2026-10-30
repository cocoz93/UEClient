"""Actual Q normal/form (5s each), F normal/form (2s each) in the existing PIE rig.

NEW_SKILLS_VIDEO=1 records viewport frames. This review loads no alternative
skill preview and saves no project assets. Q_FEATHER_KEYS=Q or F narrows a rerun.
"""
import json
import os
import unreal


def hail_diagnostic(rig):
    """A 1.6 second Q cast: no video, no full-duration gameplay assertions."""
    def path(value):
        return value.get_path_name() if isinstance(value, unreal.Object) else str(value)

    def prop(obj, name):
        try:
            return obj.get_editor_property(name)
        except Exception as error:
            return 'unavailable: ' + str(error)

    def describe(effect):
        row = {'path': path(effect), 'emitters': []}
        if not isinstance(effect, unreal.ParticleSystem):
            return row
        emitters = prop(effect, 'emitters')
        if isinstance(emitters, str):
            row['error'] = emitters
            return row
        for emitter in emitters:
            entry = {'path': path(emitter), 'name': str(prop(emitter, 'emitter_name')), 'lods': []}
            lods = prop(emitter, 'lod_levels')
            if isinstance(lods, str):
                entry['error'] = lods
            else:
                for lod in lods:
                    required, type_data = prop(lod, 'required_module'), prop(lod, 'type_data_module')
                    item = {'enabled': str(prop(lod, 'enabled')),
                            'required_material': path(prop(required, 'material')),
                            'type_data': path(type_data),
                            'override_material': str(prop(type_data, 'override_material')),
                            'mesh': path(prop(type_data, 'mesh')), 'mesh_modules': []}
                    modules = prop(lod, 'modules')
                    if not isinstance(modules, str):
                        for module in modules:
                            if module and module.get_class().get_name() == 'ParticleModuleMeshMaterial':
                                materials = prop(module, 'mesh_materials')
                                item['mesh_modules'].append({
                                    'path': path(module), 'enabled': str(prop(module, 'enabled')),
                                    'materials': materials if isinstance(materials, str) else [path(m) for m in materials]})
                    entry['lods'].append(item)
            row['emitters'].append(entry)
        return row

    report = {'diagnostic_only': True, 'duration': 1.6, 'particles': [], 'templates': {}}
    cmd = rig['cmd']
    cmd('CountessComboQA.FlushInput')
    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    cmd('Sparrow.Hail.Diagnostics 1')
    try:
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .7
        rig['case']('Q_RuntimeMaterialDiagnostic')
        rig['layout']([(420, 0), (700, 0), (600, 370)])
        yield .2
        runtime = prop(rig['skills'](), 'runtime_hail_effect')
        report['runtime_hail_effect'] = path(runtime)
        report['templates'][path(runtime)] = describe(runtime)
        rig['use']('Q', offset=(420, 0))
        yield 1.2
        rig['capture']('Q_runtime_material_diagnostic_t1200')
        world = rig['world']()
        for particle in unreal.ObjectIterator(unreal.ParticleSystemComponent):
            if isinstance(particle, type) or not unreal.SystemLibrary.is_valid(particle):
                continue
            tags = [str(tag) for tag in particle.component_tags]
            if 'SparrowSkillFX' not in tags or particle.get_world() != world:
                continue
            template = prop(particle, 'template')
            report['particles'].append({'path': path(particle), 'tags': tags,
                                        'template': path(template),
                                        'runtime_match': template == runtime if isinstance(runtime, unreal.ParticleSystem) else None,
                                        'runtime_match_evidence': 'See native SparrowQDiagnostic log when the protected property is unavailable.'})
            report['templates'][path(template)] = describe(template)
        yield .4
        report['collected'] = True
    finally:
        (rig['OUT'] / 'q-runtime-material-diagnostic.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        cmd('Sparrow.Hail.Diagnostics 0')
        cmd('CountessComboQA.FlushInput')


def sequence(rig):
    if os.environ.get('Q_FEATHER_DIAGNOSTIC') == '1':
        yield from hail_diagnostic(rig)
        return
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1.0 / rig['FPS']
    keys = [key.strip() for key in os.environ.get('Q_FEATHER_KEYS', 'Q,F').split(',') if key.strip()]
    check(bool(keys) and set(keys) <= {'Q', 'F'}, 'Q/F review uses actual Q and F keys')
    report = {'passed': False, 'fps': rig['FPS'], 'cases': [], 'comparisons': []}

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def valid(value):
        return value is not None and unreal.SystemLibrary.is_valid(value)

    def actors(cls):
        return [value for value in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), cls)
                if valid(value) and value.get_owner() == rig['pawn']()]

    def save():
        (out / 'q-feather-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    cmd('Sparrow.Sharp.Preview 0')
    cmd('Sparrow.Sharp.DetailPreview 0')
    cmd('Sparrow.Sharp.ArtPreview 0')
    try:
        for key in keys:
            pair = {}
            for mode in ('normal', 'form'):
                cmd('CountessComboQA.FlushInput')
                rig['switch']('countess'); yield .2
                rig['switch']('sparrow'); yield .7
                case = key + '_' + mode
                rig['case']('Salvo_' + case)
                targets = rig['layout']([(420, 0), (700, 0), (600, 370)])
                yield .2
                if mode == 'form':
                    rig['use']('V', offset=(950, 0)); yield 1.65
                check((rig['skills']().get_ascension_remaining() > 30) == (mode == 'form'),
                      case + ' starts in its requested actual V state')
                values = rig['skills']().get_editor_property('skills' if key == 'Q' else 'extra_skills')
                definition = values[0 if key == 'Q' else 3]
                definition = {name: float(definition.get_editor_property(name))
                              for name in ('damage', 'action_time', 'range', 'cooldown')}
                row = {'key': key, 'mode': mode, 'definition': definition,
                       'capture_seconds': 5.0 if key == 'Q' else 2.0,
                       'tags': [], 'materials': [], 'arrows': {}, 'actors': {},
                       'max_visible_feathers': 0, 'max_visible_pillars': 0,
                       'feather_visibility': {}, 'damage_events': []}
                report['cases'].append(row)
                pair[mode] = row
                health = [rig['health'](target) for target in targets]
                previous_health = list(health)
                started = now()
                rig['use'](key, offset=(420 if key == 'Q' else 950, 0))
                if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                    rig['STATE']['video_clip'] = {'case': 'Salvo_' + case, 'prefix': case + '_video',
                                                 'cast_time': started, 'frame_times': []}
                moments = [.16, .30, .42, .56, .72, .90, 1.15]
                if key == 'Q':
                    moments += [1.6, 2.25, 3.2, 4.15, 4.7]
                observed_cast = False
                checked_components = set()
                while now() - started < row['capture_seconds']:
                    elapsed = now() - started
                    observed_cast |= rig['skills']().is_casting()
                    if key == 'Q' and rig['skills']().get_active_hail_count() > 0:
                        row.setdefault('first_emission', elapsed)
                    for arrow in actors(unreal.SparrowArrow):
                        row.setdefault('first_emission', elapsed)
                        record = row['arrows'].setdefault(arrow.get_name(), {
                            'first': elapsed, 'speed': arrow.get_flight_speed(),
                            'range': arrow.get_distance_travelled() + arrow.get_remaining_range(),
                            'direction': rig['vec'](arrow.get_flight_direction())})
                        record['last'] = elapsed
                        record['hits'] = arrow.get_hit_count()
                        row['last_arrow_observed'] = elapsed
                    for cls in (unreal.SparrowAscendedShotFX, unreal.SparrowFeatherTrail):
                        for actor in actors(cls):
                            tags = [str(tag) for tag in actor.tags]
                            row['tags'] = sorted(set(row['tags']) | set(tags))
                            record = row['actors'].setdefault(actor.get_name(), {'tags': tags, 'first': elapsed})
                            record['last'] = elapsed
                            visible_feathers, visible_pillars = 0, 0
                            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                                token = actor.get_name() + '/' + component.get_name()
                                if token not in checked_components:
                                    check(component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION,
                                          case + ' added surface has no gameplay collision: ' + token)
                                    checked_components.add(token)
                                if not component.is_visible():
                                    continue
                                material = component.get_material(0)
                                if material:
                                    row['materials'] = sorted(set(row['materials']) | {material.get_base_material().get_path_name()})
                                component_tags = {str(tag) for tag in component.component_tags}
                                if 'SparrowFeatherTrailSurface' in component_tags:
                                    visible_feathers += 1
                                    feather = row['feather_visibility'].setdefault(token, {
                                        'first': elapsed, 'first_position': rig['vec'](component.get_world_location())})
                                    feather['last'] = elapsed
                                    feather['last_position'] = rig['vec'](component.get_world_location())
                                    row['last_feather_observed'] = elapsed
                                if 'RainStreak' in component_tags:
                                    visible_pillars += 1
                            row['max_visible_feathers'] = max(row['max_visible_feathers'], visible_feathers)
                            row['max_visible_pillars'] = max(row['max_visible_pillars'], visible_pillars)
                    current_health = [rig['health'](target) for target in targets]
                    if current_health != previous_health:
                        row['damage_events'].append({'time': elapsed, 'damage': [a-b for a, b in zip(previous_health, current_health)]})
                        previous_health = current_health
                    if moments and elapsed >= moments[0]:
                        rig['capture'](case + '_t' + str(round(moments.pop(0) * 1000)).zfill(4))
                    yield frame
                rig['finish_video_clip']()
                row['damage'] = [a-rig['health'](target) for a, target in zip(health, targets)]
                row['recovered'] = not rig['skills']().is_casting() and not rig['pawn']().is_combat_busy()
                save()
                check(observed_cast and row['recovered'], case + ' casts and returns player control')
                check(all(abs(a-b) < .05 for a, b in zip(row['damage'], [definition['damage'], definition['damage'], 0.])),
                      case + ' preserves actual damage and target coverage')
                check(abs(row['first_emission'] - definition['action_time']) <= frame * 3 + .015,
                      case + ' preserves its actual first emission timing')
                if key == 'Q':
                    check(not row['arrows'] and len(row['damage_events']) == 8 and rig['skills']().get_active_hail_count() == 0,
                          case + ' retains eight hail damage pulses and unchanged lifetime')
                    if mode == 'form':
                        check('SparrowGoldenPillarsUp' in row['tags'] and row['max_visible_pillars'] > 0,
                              case + ' displays actual upward golden pillars')
                    else:
                        check('SparrowAscendedRain' not in row['tags'], case + ' does not create form pillars')
                else:
                    check(len(row['arrows']) == 1 and all(abs(a['speed'] - 5200.) < .01 for a in row['arrows'].values()),
                          case + ' retains one crystal projectile and its speed')
                    check('SparrowFeatherTrail' in row['tags'] and row['max_visible_feathers'] >= 4,
                          case + ' creates visible feathers on the real projectile trail')
                    check(any('/M_AscendedFeather.' in path for path in row['materials']),
                          case + ' loads the dedicated feather surface')
                    row['feather_tail_after_last_arrow'] = row['last_feather_observed'] - row['last_arrow_observed']
                    check(.42 <= row['feather_tail_after_last_arrow'] <= .70,
                          case + ' keeps a short feather residue after the projectile ends')
                    check(not actors(unreal.SparrowFeatherTrail), case + ' fully clears the feather trail after its 0.6s residue')
                save()
            comparison = {'key': key, 'same_definition': pair['normal']['definition'] == pair['form']['definition'],
                          'same_damage': pair['normal']['damage'] == pair['form']['damage']}
            report['comparisons'].append(comparison)
            check(comparison['same_definition'] and comparison['same_damage'], key + ' keeps gameplay identical across normal and V form')
        report['passed'] = True
        save()
    finally:
        cmd('CountessComboQA.FlushInput')
        save()
