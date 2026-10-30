"""Actual V unfold, natural expiry/fold, movement, and immediate recast review.

Run by the parent-owned new_skills_probe PIE rig. No asset writes and no 40s video.
"""
import json
import os

import unreal


def sequence(rig):
    check, cmd, out = rig['check'], rig['cmd'], rig['OUT']
    frame = 1.0 / rig['FPS']
    phase = os.environ.get('SPARROW_NATIVE_WING_PHASE', 'full')
    report = {'passed': False, 'fps': rig['FPS'], 'assets_saved': False, 'phase': phase,
              'entry': [], 'natural_exit': [], 'recast': []}
    valid = unreal.SystemLibrary.is_valid
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())

    def save():
        (out / 'sparrow-native-wing-review.json').write_text(
            json.dumps(report, indent=2), encoding='utf-8')

    def forms():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowAscensionWings) if valid(a)]

    def body():
        mesh = rig['pawn']().get_editor_property('mesh')
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(
            mesh.get_skeletal_mesh_asset())
        return {'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
                'sections': [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())]
                             for lod in range(lods)]}

    def wing_sample(form):
        if not valid(form):
            return {'valid': False}
        part = next(p for p in form.get_components_by_class(unreal.SkeletalMeshComponent)
                    if p.get_name() == 'SerathWings')
        source = rig['pawn']().get_editor_property('mesh')
        origin = source.get_socket_location('spine_03')
        wing_origin = part.get_socket_location('spine_03')
        drift = (wing_origin - origin).length()
        particles = [p for p in form.get_components_by_class(unreal.ParticleSystemComponent)
                     if 'SparrowAscensionEntry' in {str(t) for t in p.component_tags}]
        return {'valid': True, 'name': form.get_name(), 'exiting': form.is_visual_exiting(),
                'animation': str(form.get_wing_animation_name()),
                'position': form.get_wing_animation_position(),
                'visible': part.is_visible(), 'anchor_drift_cm': drift,
                'entry_particle_count': len(particles),
                'entry_visible_count': sum(p.is_visible() for p in particles)}

    def video(label):
        if os.environ.get('NEW_SKILLS_VIDEO') == '1':
            rig['STATE']['video_clip'] = {'case': label, 'prefix': label + '_video',
                                         'cast_time': now(), 'frame_times': []}

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    try:
        rig['switch']('countess'); yield .2
        rig['switch']('sparrow'); yield .7
        cmd('CountessComboQA.FlushInput')
        cmd('Sparrow.FlameStudy.V 3')
        rig['case']('NativeV_entry')
        rig['layout']([(750, 350), (800, -400), (-500, 500)])
        yield .2
        original = body()
        report['normal_body'] = original
        rig['use']('V', offset=(950, 0))
        started = now()
        video('NativeV_entry')
        moments = [.65, .85, .95, 1.05, 1.25, 1.45, 1.58, 1.8, 2.3, 3.2]
        form = None
        while now() - started < 3.3:
            active = forms()
            if active and form is None:
                form = active[0]
                report['form_first_seen'] = now() - started
            if moments and now() - started >= moments[0]:
                stamp = moments.pop(0)
                row = wing_sample(form) if form is not None else {'valid': False}
                row['time'] = now() - started
                report['entry'].append(row)
                rig['capture']('NativeV_entry_t' + str(round(stamp * 1000)).zfill(4))
            yield frame
        rig['finish_video_clip']()
        check(form is not None and valid(form), 'native V keeps one active form after entry')
        check(any(r.get('animation') == 'Wings_Unfold' for r in report['entry']),
              'V entry actually samples the original Wings_Unfold sequence')
        check(report['entry'][-1].get('animation') == 'Idle_Pose_Wings',
              'V finishes unfold in the original open-wing pose')
        check(all(r.get('position', 0.) == 0. for r in report['entry'] if r['time'] < 1.45),
              'V keeps the folded starting pose while the two light stages play')
        check(any(r.get('position', 0.) > .2 for r in report['entry'] if 1.7 < r['time'] < 2.5),
              'V unfolds after the large column impact and half-second pause')
        check(all(r.get('visible') and r.get('anchor_drift_cm', 999.) < 1. for r in report['entry']),
              'original wing mesh remains visible and attached to Sparrow spine')
        check(body() != original, 'active V uses its golden body appearance')
        rig['recovered']()
        save()

        if phase == 'entry':
            report['passed'] = True
            save()
            return

        # Wait in game time, with recording disabled; do not force a lifespan shortcut.
        while rig['skills']().get_ascension_remaining() > .18:
            check(now() - started < 42., 'natural V lifetime is bounded')
            yield min(.5, max(frame, rig['skills']().get_ascension_remaining() - .18))
        rig['case']('NativeV_natural_exit')
        video('NativeV_natural_exit')
        old = form
        exit_observed = None
        move_started = None
        goal = None
        move_released = False
        captured = set()
        while exit_observed is None or now() - exit_observed < .85:
            check(now() - started < 43., 'natural exit observation is bounded')
            row = wing_sample(old)
            row['time_since_cast'] = now() - started
            report['natural_exit'].append(row)
            if row.get('exiting') and exit_observed is None:
                exit_observed = now()
                report['natural_expiry_time'] = now() - started
                report['body_at_expiry'] = body()
                check(rig['skills']().get_ascension_remaining() == 0., 'V status expires before its fold visual ends')
                check(body() == original, 'natural expiry immediately restores all original body materials and sections')
                check(not rig['skills']().is_casting() and not rig['pawn']().is_combat_busy(),
                      'fold tail never holds skill or combat input')
                move_started = rig['pawn']().get_actor_location()
                goal = rig['ground'](move_started.x - 300, move_started.y - 320)
                cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
            elif exit_observed is not None and not move_released:
                cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                move_released = True
            if exit_observed is not None:
                elapsed = now() - exit_observed
                for moment in (.03, .18, .34, .50, .70):
                    if elapsed >= moment and moment not in captured:
                        rig['capture']('NativeV_exit_t' + str(round(moment * 1000)).zfill(4))
                        captured.add(moment)
                if elapsed >= .25 and 'move_during_fold_cm' not in report:
                    report['move_during_fold_cm'] = rig['dist'](move_started, rig['pawn']().get_actor_location())
            yield frame
        rig['finish_video_clip']()
        check(any(r.get('animation') == 'Wings_Fold' and r.get('position', 0.) > .4
                  for r in report['natural_exit']), 'natural expiry plays the original Wings_Fold clip')
        check(not valid(old), 'fold visual retires after its short tail')
        check(report['move_during_fold_cm'] > 2., 'actual move input moves the character while the wing fold remains')
        check(body() == original, 'fold destruction preserves already-restored body appearance')
        report['post_exit_body'] = body()
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()
        save()

        rig['case']('NativeV_exit_recast')
        rig['layout']([(750, 350), (800, -400), (-500, 500)])
        yield .15
        rig['use']('V', offset=(950, 0))
        yield 2.0
        old = next(a for a in forms() if not a.is_visual_exiting())
        rig['recovered']()
        old.begin_visual_exit()
        check(body() == original, 'explicit visual exit restores body before immediate recast')
        recast_started = now()
        video('NativeV_exit_recast')
        rig['use']('V', offset=(950, 0))
        yield frame
        check(rig['skills']().is_casting(), 'real V key input is accepted while the previous Fold is still visible')
        new_form = None
        new_body = None
        while now() - recast_started < 2.2:
            active = forms()
            candidates = [a for a in active if a != old and not a.is_visual_exiting()]
            if candidates and new_form is None:
                new_form = candidates[0]
                new_body = body()
                report['new_form_time'] = now() - recast_started
                report['old_alive_when_new_started'] = valid(old)
            report['recast'].append({'time': now() - recast_started, 'old_valid': valid(old),
                                     'form_names': [a.get_name() for a in active]})
            yield frame
        rig['capture']('NativeV_recast_preserved')
        rig['finish_video_clip']()
        check(new_form is not None and valid(new_form) and not valid(old), 'new V survives the previous wing actor ending')
        check(new_body != original and body() == new_body, 'previous EndPlay cannot overwrite the new golden appearance')
        check(rig['skills']().get_ascension_remaining() > 37., 'new V owns its full independent duration')
        rig['recovered']()
        report['passed'] = True
        save()
    finally:
        rig['finish_video_clip']()
        cmd('CountessComboQA.FlushInput')
        save()
