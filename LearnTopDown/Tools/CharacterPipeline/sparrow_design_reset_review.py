"""Scoped design-reset author/capture wrapper for the existing new_skills_probe rig.

NEW_SKILLS_AUTHOR points here. For PIE use NEW_SKILLS_FOCUS=sparrow_feedback,
SPARROW_FEEDBACK_PARTS=, SPARROW_FEEDBACK_STUDIES=sparrow_design_reset_review.py.
SPARROW_DESIGN_RESET_PHASE=all|refine|qw|v|a|f limits actual captures; NEW_SKILLS_VIDEO=1
records the same gameplay viewport. Candidate selectors always return to zero.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import runpy
import shutil

import unreal


@contextmanager
def environment(values):
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def author(out):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    selected = os.environ.get('SPARROW_DESIGN_RESET_AUTHOR', 'qwv,a,f').split(',')
    definitions = []
    if 'qwv' in selected:
        definitions += [('sparrow_ascended_shot_materials.py', {})]
    if 'qwv' in selected or 'v' in selected:
        definitions += [('sparrow_flame_studies.py', {'v_entry_only': True})]
    if 'a' in selected:
        definitions += [('sparrow_saw_vortex_materials.py', {}),
                        ('sparrow_sun_arrow_materials.py', {})]
    if 'f' in selected:
        definitions += [('sparrow_f_design_materials.py', {})]
    if not definitions:
        raise ValueError('Unknown SPARROW_DESIGN_RESET_AUTHOR: ' + ','.join(selected))
    rows = []
    for name, kwargs in definitions:
        result = runpy.run_path(str(folder / name))['author'](out, **kwargs)
        assert result['passed'], name
        rows.append({'file': name, 'passed': True, 'parameters': kwargs})
    result = {'passed': True, 'authors': rows, 'visual_acceptance': 'pending actual capture review'}
    (Path(out) / 'design-reset-author.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def sequence(rig):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1.0 / rig['FPS']
    phase = os.environ.get('SPARROW_DESIGN_RESET_PHASE', 'all')
    if phase not in ('all', 'refine', 'qw', 'v', 'a', 'f'):
        raise ValueError(phase)
    report = {'passed': False, 'phase': phase, 'fps': rig['FPS'], 'cases': [],
              'visual_acceptance': 'pending actual capture review'}
    selector_a, selector_f = 'Sparrow.SunArrow.Style', 'Sparrow.FDesign.Style'

    def save():
        (out / 'design-reset-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def reuse(name, values, label, source_report, observer=None):
        scoped = dict(rig)
        scoped['case'] = lambda value: rig['case'](label + '_' + value)

        def capture(value):
            # V gets local-FX-age stills below, avoiding two screenshot commands
            # on the same frame while retaining the native wing state samples.
            if observer is not None and value.startswith('NativeV_entry_t'):
                return
            rig['capture'](label + '_' + value)

        scoped['capture'] = capture
        with environment(values):
            generator = runpy.run_path(str(folder / name))['sequence'](scoped)
            try:
                for delay in generator:
                    clip = rig['STATE'].get('video_clip')
                    if clip and not clip['prefix'].startswith(label + '_'):
                        clip['prefix'] = label + '_' + clip['prefix']
                        clip['case'] = label + '_' + clip['case']
                    if observer is not None:
                        observer()
                    yield delay
            finally:
                generator.close()
        destination = out / (label + '.json')
        shutil.copyfile(out / source_report, destination)
        data = json.loads(destination.read_text(encoding='utf-8'))
        check(data['passed'], label + ' reused scoped checks pass')
        report['cases'].append({'label': label, 'report': destination.name, 'passed': True})
        save()

    def arsenal(keys, modes, label):
        yield from reuse('sparrow_ascended_arsenal_review.py',
                         {'SPARROW_ASCENDED_KEYS': keys, 'SPARROW_ASCENDED_MODES': modes},
                         label, 'sparrow-ascended-arsenal.json')

    def parts(row, actor_tag):
        return [part for actor in row['actors'].values() if actor_tag in actor['tags']
                for part in actor['components']]

    settings = {'SPARROW_SERAPH_POLISH': '1', 'SPARROW_ASCENDED_RECRAFT': '1',
                'SPARROW_REART_Q_SYNC': '0', 'ASCENDED_ARSENAL_RECOVERY': '0'}
    try:
        cmd(selector_a + ' 0')
        cmd(selector_f + ' 0')
        cmd('Sparrow.FlameStudy.V 3')
        cmd('Sparrow.FlameStudy.D 0')
        with environment(settings):
            if phase in ('all', 'qw'):
                yield from arsenal('Q,W', 'form', 'Reset_QW')
                data = json.loads((out / 'Reset_QW.json').read_text(encoding='utf-8'))
                q = next(row for row in data['cases'] if row['key'] == 'Q')
                w = next(row for row in data['cases'] if row['key'] == 'W')
                rain_parts = parts(q, 'SparrowAscendedRain')
                counts = {tag: sum(tag in part['tags'] for part in rain_parts)
                          for tag in ('RainStreak', 'RainContact', 'RainFlare')}
                check(counts == dict.fromkeys(counts, 24),
                      'restored Q has three shafts in each of eight timing groups, with contact and flare planes')
                source = (folder.parent.parent / 'Source/LearnTopDown/SparrowAscendedShotFX.h').read_text(encoding='utf-8-sig')
                constant = lambda name: float(re.search(name + r'\s*=\s*([\d.]+)f;', source)[1])
                delay, interval = constant('RainContactDelay'), constant('RainContactInterval')
                expected = [q['first_emission_observed'] + delay + i * interval for i in range(8)]
                check(len(q['hits']) == 8 and all(abs(hit['elapsed'] - t) <= 2 * frame + .006
                                                for hit, t in zip(q['hits'], expected)),
                      'restored Q planes retain eight contact-synchronized damage pulses')
                bow = parts(w, 'SparrowAscendedBow')
                bow_counts = {tag: sum(tag in part['tags'] for part in bow) for tag in ('BowFlow', 'BowPulse')}
                check(bow_counts == {'BowFlow': 0, 'BowPulse': 2},
                      'W removes only the six front bow-flow ornaments and retains two outlet pulses')
                check(len(w['arrows']) == 5, 'form W preserves its four shots plus one finisher')
                shot_times = sorted(arrow['observed'] for arrow in w['arrows'].values())
                check(max(b - a for a, b in zip(shot_times[:3], shot_times[1:4])) < .30 and
                      shot_times[4] - shot_times[3] > .33,
                      'form W keeps four rapid shots followed by the held fifth-shot release')
                report['qw'] = {'rain_surfaces': counts, 'expected_damage_times': expected,
                                'Q_damage': q['damage'], 'W_bow_surfaces': bow_counts,
                                'W_shot_times': shot_times, 'W_damage': w['damage']}
                save()

            if phase in ('all', 'refine', 'v'):
                samples, captures = [], set()
                local_moments = (.04, .14, .24, .34, .44, .49, .52, .60, .67, .95, 1.16, 1.25)

                def observe_v():
                    for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowFlameStudies):
                        if not unreal.SystemLibrary.is_valid(actor) or actor.get_owner() != rig['pawn']() or not actor.is_form_study():
                            continue
                        surfaces = actor.get_components_by_class(unreal.StaticMeshComponent)
                        column = next((part for part in surfaces if part.get_material(0) and
                                       part.get_material(0).get_base_material().get_name() == 'M_VEntryColumn'), None)
                        if column is None:
                            continue
                        material = column.get_material(0)
                        age = material.get_scalar_parameter_value('Age')
                        if age > 1.40 or (samples and abs(samples[-1]['age'] - age) < frame * .4):
                            continue
                        row = {'age': age, 'column_strength': material.get_scalar_parameter_value('Strength'),
                               'column_tip_z': column.get_world_location().z - column.get_world_scale().z * 50.0}
                        thin = next((part for part in surfaces if part.get_material(0) and
                                     part.get_material(0).get_base_material().get_name() == 'M_VEntryShaft'), None)
                        row['thin_strength'] = thin.get_material(0).get_scalar_parameter_value('Strength') if thin else None
                        for form in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings):
                            if form.get_owner() == rig['pawn']():
                                row['wing_animation'] = str(form.get_wing_animation_name())
                                row['wing_position'] = form.get_wing_animation_position()
                        samples.append(row)
                        for moment in local_moments:
                            if age >= moment and moment not in captures:
                                captures.add(moment)
                                rig['capture']('Reset_V_local_t' + str(round(moment * 1000)).zfill(4))
                                break

                yield from reuse('sparrow_native_wing_review.py', {'SPARROW_NATIVE_WING_PHASE': 'entry'},
                                 'Reset_V', 'sparrow-native-wing-review.json', observe_v)
                descent = [row for row in samples if .55 <= row['age'] <= .68]
                check(len(descent) >= 3 and descent[0]['column_tip_z'] - descent[-1]['column_tip_z'] > 500.,
                      'V large column moves downward before the 0.66s contact')
                gap = [row for row in samples if .501 <= row['age'] < .54]
                check(gap and all(row['column_strength'] == 0. and row['thin_strength'] == 0. for row in gap),
                      'V has a real gap after segmented prelude retirement and before the large column')
                check(all(row.get('wing_position', 0.) == 0. for row in samples if row['age'] < 1.16 - frame),
                      'V native wings wait until the contact plus half-second reveal')
                check(any(row.get('wing_position', 0.) > .02 for row in samples if row['age'] >= 1.16 + 2 * frame),
                      'V native wings actually unfold after the 1.16s reveal')
                report['v'] = {'samples': samples, 'local_stills': sorted(captures),
                               'segmented_shader_visual_status': 'actual captured frames require visual review; geometry timing alone is not proof'}
                save()

            if phase in ('all', 'refine', 'a'):
                cmd(selector_a + ' 1')
                check(unreal.SystemLibrary.get_console_variable_int_value(selector_a) == 1,
                      'A preview selector enables the small-sun candidate')
                yield from arsenal('A', 'normal,form', 'Reset_A1')
                cmd(selector_a + ' 0')

            if phase in ('all', 'refine', 'f'):
                for style, modes in ((1, 'normal,form'), (2, 'normal')):
                    cmd(selector_f + ' ' + str(style))
                    label = 'Reset_F' + str(style)
                    yield from arsenal('F', modes, label)
                    data = json.loads((out / (label + '.json')).read_text(encoding='utf-8'))
                    for row in data['cases']:
                        arrows = [actor for actor in row['actors'].values() if actor['class'] == 'SparrowArrow']
                        check(arrows and all('SparrowFDesign' + str(style) in actor['tags'] for actor in arrows),
                              label + '_' + row['mode'] + ' copies the selected design onto each real arrow')
                cmd(selector_f + ' 0')
            report['passed'] = True
    finally:
        cmd(selector_a + ' 0')
        cmd(selector_f + ' 0')
        cmd('CountessComboQA.FlushInput')
        report['candidate_defaults_restored'] = {
            name: unreal.SystemLibrary.get_console_variable_int_value(name) for name in (selector_a, selector_f)}
        save()
