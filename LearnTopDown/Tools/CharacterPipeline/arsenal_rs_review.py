"""Actual R/S recraft clips in the existing rig; no alternate damage path.

ARSENAL_RS_CASES=S4 and ARSENAL_RS_MODES=normal,form narrow a retry.
NEW_SKILLS_VIDEO=1 captures two seconds per clip. Installed R=0 / S=4 are restored.
"""
import json
import os
import unreal


def sequence(rig):
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    cases = os.environ.get('ARSENAL_RS_CASES', 'S4').split(',')
    modes = os.environ.get('ARSENAL_RS_MODES', 'normal,form').split(',')
    valid_cases = {'R' + str(style) for style in range(1, 5)} | {'S' + str(style) for style in range(1, 11)}
    check(bool(cases) and set(cases) <= valid_cases, 'R/S candidate keys are valid')
    check(bool(modes) and set(modes) <= {'normal', 'form'}, 'R/S candidate forms are valid')
    report = {'passed': False, 'cases': [], 'defaults_restored': False}

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def owned(cls):
        return [actor for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), cls)
                if unreal.SystemLibrary.is_valid(actor) and actor.get_owner() == rig['pawn']()]

    def save():
        (out / 'arsenal-rs-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    for name in ('Preview', 'DetailPreview', 'ArtPreview'):
        cmd('Sparrow.Sharp.' + name + ' 0')
    try:
        for candidate in cases:
            key, style = candidate[0], int(candidate[1:])
            for mode in modes:
                cmd('Sparrow.ArsenalStudy.R 0')
                cmd('Sparrow.ArsenalStudy.S 0')
                cmd('CountessComboQA.FlushInput')
                rig['switch']('countess'); yield .2
                rig['switch']('sparrow'); yield .7
                case = candidate + '_' + mode
                rig['case'](case)
                targets = rig['layout']([(420, 0), (700, 0), (600, 370)] if key == 'R' else
                                        [(260, 0), (650, 0), (320, 230)])
                yield .2
                if mode == 'form':
                    rig['use']('V', offset=(950, 0)); yield 3.0 if os.environ.get('SPARROW_SERAPH_POLISH') == '1' else 1.65
                check((rig['skills']().get_ascension_remaining() > 0) == (mode == 'form'), case + ' uses the requested real V state')
                cmd('Sparrow.ArsenalStudy.' + key + ' ' + str(style))
                health = [rig['health'](target) for target in targets]
                row = {'case': case, 'mode': mode, 'style': style, 'arrows': {}, 'study_tags': [],
                       'materials': [], 'max_pulses': 0, 'visible_components': 0}
                report['cases'].append(row)
                started = now()
                rig['use'](key, offset=(950, 0))
                if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                    rig['STATE']['video_clip'] = {'case': case, 'prefix': case + '_video',
                                                 'cast_time': started, 'frame_times': []}
                moments = [.10, .22, .35, .43, .52, .70, 1.05, 1.40]
                checked_components = set()
                while now() - started < 2.0:
                    elapsed = now() - started
                    for arrow in owned(unreal.SparrowArrow):
                        row['arrows'].setdefault(arrow.get_name(), {'first': elapsed, 'speed': arrow.get_flight_speed()})
                    for study in owned(unreal.SparrowArsenalStudyFX):
                        row['max_pulses'] = max(row['max_pulses'], study.get_pulses())
                        row['study_tags'] = sorted(set(row['study_tags']) | {str(tag) for tag in study.tags})
                        visible = 0
                        for component in study.get_components_by_class(unreal.StaticMeshComponent):
                            token = study.get_name() + '/' + component.get_name()
                            if token not in checked_components:
                                check(component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION,
                                      case + ' study geometry has no collision')
                                checked_components.add(token)
                            if component.is_visible():
                                visible += 1
                                material = component.get_material(0)
                                if material:
                                    row['materials'] = sorted(set(row['materials']) | {material.get_base_material().get_path_name()})
                        row['visible_components'] = max(row['visible_components'], visible)
                    if moments and elapsed >= moments[0]:
                        rig['capture'](case + '_t' + str(round(moments.pop(0) * 1000)).zfill(4))
                    yield 1.0 / rig['FPS']
                rig['finish_video_clip']()
                row['damage'] = [initial - rig['health'](target) for initial, target in zip(health, targets)]
                row['recovered'] = not rig['skills']().is_casting() and not rig['pawn']().is_combat_busy()
                save()
                check(len(row['arrows']) == (310 if key == 'R' else 15), case + ' preserves the actual projectile count')
                check(all(abs(a-b) < .05 for a, b in zip(row['damage'], [60, 60, 60] if key == 'R' else [54, 0, 0])),
                      case + ' preserves native damage and coverage')
                check(row['max_pulses'] == (10 if key == 'R' else 1), case + ' accents track real releases')
                check('SparrowStudy' + candidate in row['study_tags'] and row['visible_components'] > 0,
                      case + ' shows its selected native candidate')
                check(('SparrowStudyAscended' in row['study_tags']) == (mode == 'form'), case + ' uses its own form presentation')
                check(row['recovered'] and not owned(unreal.SparrowArsenalStudyFX), case + ' restores control and clears study actors')
                save()
        report['passed'] = True
    finally:
        cmd('Sparrow.ArsenalStudy.R 0')
        cmd('Sparrow.ArsenalStudy.S 10')
        cmd('CountessComboQA.FlushInput')
        report['defaults_restored'] = True
        save()
