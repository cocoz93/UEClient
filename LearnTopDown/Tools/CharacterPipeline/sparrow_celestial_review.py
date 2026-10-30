"""Scoped reuse of native input/capture checks for the celestial refinement."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy
import shutil
import unreal


def author(out):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    results = []
    for filename, function in [('sparrow_ascended_shot_materials.py', 'author'),
                               ('sparrow_arsenal_study_materials.py', 'main'),
                               ('sparrow_flame_studies.py', 'author'),
                               ('sparrow_arsenal_adoption.py', 'author'),
                               ('sparrow_ascended_arsenal_materials.py', 'author')]:
        result = runpy.run_path(str(folder / filename))[function](out)
        assert result['passed'], filename
        results.append({'file': filename, 'passed': True})
    return {'passed': True, 'authors': results}


def sequence(rig):
    folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1. / rig['FPS']
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())

    @contextmanager
    def environment(values):
        saved = {key: os.environ.get(key) for key in values}
        os.environ.update(values)
        try:
            yield
        finally:
            for key, value in saved.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value

    def reuse(name, values, report, target):
        with environment(values):
            yield from runpy.run_path(str(folder / name))['sequence'](rig)
        shutil.copyfile(out / report, out / target)

    mode = os.environ.get('SPARROW_CELESTIAL_PHASE', 'applied')
    cmd('Sparrow.FlameStudy.V 3')
    cmd('Sparrow.FlameStudy.D 0')
    seraph = os.environ.get('SPARROW_SERAPH_POLISH') == '1'
    redesign = seraph or os.environ.get('SPARROW_ASCENDED_RECRAFT') == '1'
    cmd('Sparrow.ArsenalStudy.R ' + ('4' if redesign and not seraph else '0'))
    cmd('Sparrow.ArsenalStudy.S ' + ('4' if redesign else '0'))
    if mode == 'applied':
        yield from reuse('sparrow_ascended_arsenal_review.py',
                         {'SPARROW_ASCENDED_KEYS': os.environ.get('SPARROW_CELESTIAL_KEYS', 'W,F,A,D'),
                          'SPARROW_ASCENDED_MODES': 'normal,form'},
                         'sparrow-ascended-arsenal.json', 'celestial-applied.json')
        if os.environ.get('SPARROW_CELESTIAL_SKIP_Q') != '1':
            yield from reuse('sparrow_ascended_arsenal_review.py',
                             {'SPARROW_ASCENDED_KEYS': 'Q', 'SPARROW_ASCENDED_MODES': 'form'},
                             'sparrow-ascended-arsenal.json', 'celestial-q.json')
        return
    if mode != 'recovery': raise ValueError(mode)
    for form in (False, True):
        yield from reuse('sparrow_recovery_timing.py',
                         {'SPARROW_RECOVERY_KEYS': 'W,F', 'SPARROW_RECOVERY_FORM': str(int(form))},
                         'sparrow-recovery-timing.json', 'celestial-recovery-' + ('form' if form else 'normal') + '.json')

    report = {'passed': False, 'fps': rig['FPS'], 'cases': []}
    def save():
        (out / 'celestial-cancel.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    def fresh():
        cmd('CountessComboQA.FlushInput')
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .7
        rig['layout']([(420, 0), (700, 0), (600, 370)]); yield .15
        rig['use']('V', offset=(950, 0)); yield 3.0 if seraph else 1.65
    def arrows():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow)
                if unreal.SystemLibrary.is_valid(a) and a.get_owner() == rig['pawn']()]
    def wings():
        return [{'name': actor.get_name(), 'animation': str(actor.get_wing_animation_name()),
                 'attack': actor.is_wing_attack_active(), 'exiting': actor.is_visual_exiting(),
                 'position': actor.get_wing_animation_position()}
                for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings)
                if unreal.SystemLibrary.is_valid(actor) and actor.get_owner() == rig['pawn']()]

    for key in ('W', 'F'):
        yield from fresh()
        rig['case']('Celestial_cancel_' + key)
        row = {'key': key, 'arrows': {}, 'cancelled': False}
        report['cases'].append(row)
        if seraph and key == 'W':
            row['wing_initial'] = wings()
            row['form_remaining_initial'] = rig['skills']().get_ascension_remaining()
            save()
            check(len(row['wing_initial']) == 1 and row['wing_initial'][0]['animation'] == 'Idle_Pose_Wings',
                  'W cancellation starts with one native idle wing actor')
        rig['use'](key, offset=(950, 0)); started = now()
        while now() - started < (2.25 if seraph else 2.):
            elapsed = now() - started
            for arrow in arrows(): row['arrows'].setdefault(arrow.get_name(), elapsed)
            if not row['cancelled'] and ((key == 'W' and len(row['arrows']) == 4 and elapsed >= 1.32) or (key == 'F' and elapsed >= .12)):
                anim = rig['pawn']().get_editor_property('mesh').get_anim_instance()
                montage = anim.get_current_active_montage()
                check(montage is not None, key + ' cancellation has a real active montage')
                if seraph and key == 'W':
                    row['wing_at_cancel'] = wings()
                    save()
                    check(len(row['wing_at_cancel']) == 1 and not row['wing_at_cancel'][0]['attack'] and
                          row['wing_at_cancel'][0]['animation'] == 'Idle_Pose_Wings',
                          'W cancellation preserves idle wings before the pending fifth shot')
                anim.montage_stop(.035, montage)
                row['cancelled'] = True
            yield frame
        check(row['cancelled'] and len(row['arrows']) == (4 if key == 'W' else 0), key + ' cancellation removes all future shots')
        check(not rig['skills']().is_casting() and not rig['pawn']().is_combat_busy(), key + ' cancellation restores action control')
        if key == 'W':
            if seraph:
                row['wing_after_cancel'] = wings()
                row['form_remaining_after_cancel'] = rig['skills']().get_ascension_remaining()
                save()
                check(len(row['wing_after_cancel']) == 1 and
                      row['wing_after_cancel'][0]['name'] == row['wing_initial'][0]['name'] and
                      row['wing_after_cancel'][0]['animation'] == 'Idle_Pose_Wings' and
                      not row['wing_after_cancel'][0]['attack'] and not row['wing_after_cancel'][0]['exiting'],
                      'interrupted W cancels its native wing attack and restores the same idle wings')
                check(35. < row['form_remaining_after_cancel'] < row['form_remaining_initial'],
                      'interrupted W preserves the ongoing transformation lifetime')
            else:
                folds = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowFlameStudies)
                         if 'SparrowWFinisherFX' in [str(t) for t in a.tags]]
                check(not folds, 'interrupted W leaves no separate wing-fold actor')
            if redesign and not seraph:
                forms = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowFlameStudies)
                         if a.get_owner() == rig['pawn']() and a.is_form_study()]
                check(len(forms) == 1 and not forms[0].is_folding_form() and rig['skills']().get_ascension_remaining() > 35.,
                      'W interruption restores the same ongoing V3 form instead of destroying it')
        row['recast_arrows'] = {}
        rig['use'](key, offset=(950, 0)); started = now()
        while now() - started < (2.25 if seraph else 2.):
            for arrow in arrows(): row['recast_arrows'].setdefault(arrow.get_name(), now()-started)
            yield frame
        check(len(row['recast_arrows']) == (5 if key == 'W' else 3), key + ' can be cast again completely after interruption')
        check(not rig['skills']().is_casting() and not rig['pawn']().is_combat_busy(), key + ' recast restores action control')
        if seraph and key == 'W':
            row['wing_after_recast'] = wings()
            save()
            check(len(row['wing_after_recast']) == 1 and
                  row['wing_after_recast'][0]['name'] == row['wing_initial'][0]['name'] and
                  row['wing_after_recast'][0]['animation'] == 'Idle_Pose_Wings' and
                  not row['wing_after_recast'][0]['attack'] and rig['skills']().get_ascension_remaining() > 30.,
                  'recast W returns the same native wings to idle without ending V')
        save()
    report['passed'] = True
    save()
