"""Observe Space's landing-to-input gap and late visual cleanup with real keys.

Use the existing new_skills_probe Sparrow feedback rig. Set
SPARROW_MOBILITY_BASELINE=1 to record the old control lock without requiring its fix.
No asset writes or forced movement-state repairs are performed.
"""
import json
import os

import unreal


def sequence(rig):
    check, cmd, out = rig['check'], rig['cmd'], rig['OUT']
    frame = 1.0 / rig['FPS']
    baseline = os.environ.get('SPARROW_MOBILITY_BASELINE') == '1'
    report = {'passed': False, 'baseline': baseline, 'fps': rig['FPS'], 'cases': []}

    def save():
        (out / 'sparrow-mobility-recovery.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def rolls():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowGoldRoll)
                if unreal.SystemLibrary.is_valid(a)]

    def native():
        p = rig['pawn']()
        mesh = p.get_editor_property('mesh')
        movement = p.get_editor_property('character_movement')
        return {'visible': mesh.is_visible(),
                'orient': movement.get_editor_property('orient_rotation_to_movement'),
                'root_motion': str(mesh.get_anim_instance().get_editor_property('root_motion_mode'))}

    def mouse(action, goal):
        cmd(f'CountessComboQA.Mouse {action} Right {goal.x} {goal.y} {goal.z}')

    def fresh(transformed, label):
        cmd('CountessComboQA.FlushInput')
        rig['switch']('countess')
        yield .15
        rig['switch']('sparrow')
        yield .65
        rig['layout']([(700, 350), (800, -400), (-500, 500)])
        yield .15
        if transformed:
            rig['key']('V')
            yield 1.65
            check(rig['skills']().get_ascension_remaining() > 30, label + ' starts in V form')
        rig['case'](label)
        return native()

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    try:
        for transformed in (False, True):
            label = 'Space_blink_recovery' if transformed else 'Space_roll_recovery'
            previous = yield from fresh(transformed, label)
            rig['aim'](offset=(550, 0))
            start = rig['pawn']().get_actor_location()
            started = now()
            if os.environ.get('SPARROW_MOBILITY_RECOVERY_VIDEO') == '1':
                rig['STATE']['video_clip'] = {'case': label, 'prefix': label + '_video',
                                             'cast_time': started, 'frame_times': []}
            rig['key']('SpaceBar')
            yield frame
            active = rolls()
            check(len(active) == 1 and rig['skills']().is_rolling(), label + ' starts the native Space action')
            goal = rig['ground'](start.x + 480, start.y + 360)
            mouse('Press', goal)
            yield frame
            mouse('Release', goal)
            row = {'case': label, 'start': rig['vec'](start), 'samples': [], 'before': previous}
            report['cases'].append(row)
            while now() - started < .85:
                p = rig['pawn']()
                row['samples'].append({'elapsed': now() - started, 'location': rig['vec'](p.get_actor_location()),
                                       'rolling': rig['skills']().is_rolling(), 'busy': p.is_combat_busy(),
                                       'actor_count': len(rolls()), 'state': native()})
                yield frame
            if rig['STATE'].get('video_clip'):
                rig['finish_video_clip']()
            arrivals = [s['elapsed'] for s in row['samples'] if s['location'][0] >= start.x + 478]
            unlocks = [s['elapsed'] for s in row['samples'] if not s['rolling']]
            movements = [s['elapsed'] for s in row['samples'] if s['location'][1] > start.y + .5]
            check(bool(arrivals) and bool(unlocks) and bool(movements), label + ' lands, unlocks, and consumes the released move click')
            row['landed_at'] = min(arrivals)
            row['unlocked_at'] = min(unlocks)
            row['first_followup_move_at'] = min(movements)
            row['landing_to_unlock'] = row['unlocked_at'] - row['landed_at']
            row['landing_to_move'] = row['first_followup_move_at'] - row['landed_at']
            row['after'] = native()
            check(row['after'] == previous, label + ' restores visibility, root motion, and movement orientation')
            check(not rolls(), label + ' eventually clears every residual visual actor')
            check(rig['pawn']().get_actor_location().y - start.y > 150, label + ' follows the queued path past the former visual lifetime')
            if not baseline:
                allowance = .035 if transformed else .018
                check(row['landing_to_unlock'] <= allowance + 2 * frame,
                      label + ' has no old presentation-length control tail')
                expected = .065 if transformed else .70 / 2.625
                check(row['unlocked_at'] <= expected + 2 * frame, label + ' returns control at the new landing deadline')
                check(any(not s['rolling'] and s['actor_count'] > 0 for s in row['samples']),
                      label + ' separates fading afterimages from action lock')
            save()

            # A fresh action while the old afterimages are alive must keep its own
            # orientation/root-motion state after that old actor is destroyed.
            label = 'Space_blink_into_A' if transformed else 'Space_roll_into_A'
            previous = yield from fresh(transformed, label)
            rig['aim'](offset=(550, 0))
            rig['key']('SpaceBar')
            yield frame
            elapsed = 0.0
            while rig['skills']().is_rolling() and elapsed < .6:
                yield frame
                elapsed += frame
            had_visual_tail = bool(rolls())
            rig['aim'](offset=(700, 0))
            rig['key']('A')
            yield frame
            check(rig['skills']().is_casting(), label + ' accepts A on first free frame')
            mid = native()
            yield .17
            check(not rolls(), label + ' old Space actor expires during A')
            check(native() == mid, label + ' old visual cleanup does not overwrite the new cast state')
            yield 1.0
            check(not rig['pawn']().is_combat_busy() and native() == previous, label + ' finishes A with the original movement state')
            report['cases'].append({'case': label, 'visual_tail_at_new_cast': had_visual_tail,
                                     'during_new_cast': mid, 'after': native()})
            save()

        report['passed'] = True
        save()
    finally:
        cmd('CountessComboQA.FlushInput')
        save()
