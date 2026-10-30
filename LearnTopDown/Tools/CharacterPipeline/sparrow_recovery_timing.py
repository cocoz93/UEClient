"""Real mouse-input timing at the projectile/recovery boundary.

Q/W/A/S/D/F queue a released right-click before firing. E/R keep their existing
move-cancel contract and receive the click after the actual shot/final volley.
SPARROW_RECOVERY_BASELINE=1 records the old delay; no state is forcibly unlocked.
SPARROW_RECOVERY_KEYS selects comma-separated keys, default Q,W,E,R,A,S,D,F.
SPARROW_RECOVERY_FORM=1 performs the same input regression inside native V form.
"""
import json
import os
import re

import unreal


def sequence(rig):
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    frame = 1.0 / rig['FPS']
    baseline = os.environ.get('SPARROW_RECOVERY_BASELINE') == '1'
    transformed = os.environ.get('SPARROW_RECOVERY_FORM') == '1'
    report = {'passed': False, 'fps': rig['FPS'], 'baseline': baseline, 'transformed': transformed, 'cases': []}
    old_tail = {'Q': .12, 'W': .10, 'E': .28, 'R': .32, 'A': .48, 'S': .30, 'D': .22, 'F': .22}

    def save():
        (out / 'sparrow-recovery-timing.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def native():
        pawn = rig['pawn']()
        movement = pawn.get_editor_property('character_movement')
        anim = pawn.get_editor_property('mesh').get_anim_instance()
        montage = anim.get_current_active_montage()
        return {'busy': pawn.is_combat_busy(), 'casting': rig['skills']().is_casting(),
                'root': str(anim.get_editor_property('root_motion_mode')),
                'orient': movement.get_editor_property('orient_rotation_to_movement'),
                'montage': montage.get_name() if montage else None,
                'position': rig['vec'](pawn.get_actor_location())}

    def objects(cls):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), cls)
                if unreal.SystemLibrary.is_valid(a)]

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    cmd('Character.Input.TraceMove 1')
    try:
        for key in os.environ.get('SPARROW_RECOVERY_KEYS', 'Q,W,E,R,A,S,D,F').split(','):
            if not key:
                continue
            check(key in old_tail, 'known recovery timing key ' + key)
            cmd('CountessComboQA.FlushInput')
            rig['switch']('countess'); yield .2
            rig['switch']('sparrow'); yield .65
            rig['case']('Recovery_' + key)
            targets = rig['layout']([(260 if key == 'S' else 420, 0), (700, 0), (600, 370)])
            yield .15
            navigation_probe = rig.get('recovery_navigation_probe')
            navigation = []
            initial_location = rig['pawn']().get_actor_location()
            requested_goal = unreal.Vector(initial_location.x - 300, initial_location.y - 320, initial_location.z)
            if navigation_probe:
                navigation.append(navigation_probe(key, 'before_form', requested_goal))
            if transformed:
                rig['use']('V', offset=(950, 0))
                yield 1.65
                check(rig['skills']().get_ascension_remaining() > 35, key + ' recovery review starts inside native V form')
            initial = native()
            health = [rig['health'](a) for a in targets]
            start = rig['pawn']().get_actor_location()
            goal = rig['ground'](start.x - 300, start.y - 320)
            rig['aim'](offset=(420 if key == 'Q' else 950, 0))
            started = now()
            row = {'key': key, 'started_at': started, 'old_definition_tail': old_tail[key],
                   'initial': initial, 'samples': [], 'arrows': {}, 'spawn_batches': [],
                   'input_policy': 'after_last_shot' if key in ('E', 'R') else 'before_shot'}
            if navigation_probe:
                navigation.append(navigation_probe(key, 'before_cast', requested_goal))
                row['navigation'] = navigation
            nav_moments = [.10, .40, .50, .56, .65, .80, 1.00, 1.50, 1.95]
            report['cases'].append(row)
            rig['key'](key)
            pressed_at = None
            released = False
            seen_cast = False
            first_move = None
            last_spawn = None
            fired_at = None
            while now() - started < (3.4 if key == 'A' else 2.5 if key == 'W' and transformed else 2.0):
                elapsed = now() - started
                snap = native()
                seen_cast |= snap['casting']
                new_arrows = []
                for arrow in objects(unreal.SparrowArrow):
                    if arrow.get_owner() != rig['pawn']() or arrow.get_name() in row['arrows']:
                        continue
                    row['arrows'][arrow.get_name()] = {'observed': elapsed,
                                                      'speed': arrow.get_flight_speed(),
                                                      'tags': [str(tag) for tag in arrow.tags]}
                    new_arrows.append(arrow.get_name())
                if new_arrows:
                    last_spawn = elapsed
                    fired_at = elapsed if fired_at is None else fired_at
                    row['spawn_batches'].append({'elapsed': elapsed, 'count': len(new_arrows)})
                if key == 'Q' and rig['skills']().get_active_hail_count() > 0 and fired_at is None:
                    fired_at = elapsed
                damage = [before - rig['health'](a) for a, before in zip(targets, health)]
                if max(damage) > .01 and fired_at is None:
                    fired_at = elapsed
                    row['emission_observation'] = 'first real damage; projectile lifetime shorter than observation step'
                if first_move is None and rig['dist'](start, rig['pawn']().get_actor_location()) > .5:
                    first_move = elapsed
                snap.update({'elapsed': elapsed, 'damage': damage})
                row['samples'].append(snap)
                if navigation_probe and nav_moments and elapsed + 1e-5 >= nav_moments[0]:
                    moment = nav_moments.pop(0)
                    navigation.append(navigation_probe(key, 'cast_' + str(round(moment * 1000)), requested_goal))
                ready_for_click = elapsed >= .10
                if key == 'E':
                    ready_for_click = fired_at is not None and elapsed >= fired_at + .04
                elif key == 'R':
                    ready_for_click = len(row['spawn_batches']) >= 10 and elapsed >= last_spawn + .04
                if pressed_at is None and ready_for_click:
                    cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                    pressed_at = elapsed
                    row['right_press_at'] = elapsed
                elif pressed_at is not None and not released and elapsed >= pressed_at + frame - 1e-5:
                    cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                    released = True
                yield frame
            row['first_emission_observed_at'] = fired_at
            row['last_projectile_batch_observed_at'] = last_spawn
            row['first_move_at'] = first_move
            row['damage'] = [before - rig['health'](a) for a, before in zip(targets, health)]
            row['after'] = native()
            row['last_shot_to_move'] = None if first_move is None or fired_at is None else first_move - (last_spawn if key in ('W', 'R') else fired_at)
            row['click_to_move'] = None if first_move is None or pressed_at is None else first_move - pressed_at
            save()
            check(seen_cast, key + ' starts a real native cast')
            check(fired_at is not None and max(row['damage']) > .01, key + ' still emits and damages a real target with the move request')
            if key == 'R':
                check(len(row['spawn_batches']) == 10 and len(row['arrows']) == 310,
                      'R fires all ten native waves before the recovery move')
            elif key == 'W':
                check(len(row['arrows']) == (5 if transformed else 4), 'W completes its native shots including the form finisher before recovery')
            elif key in ('A', 'D', 'F', 'E'):
                check(len(row['arrows']) == (3 if key == 'F' and transformed else 1) or (key == 'E' and max(row['damage']) >= 59.99),
                      key + ' completes its native emission count')
            elif key == 'S':
                check(len(row['arrows']) >= 1 and abs(row['damage'][0] - 54) < .03,
                      'S preserves the real close burst damage')
            check(first_move is not None and rig['dist'](start, rig['pawn']().get_actor_location()) > 150,
                  key + ' consumes the released move click and continues moving')
            check(not row['after']['busy'] and not row['after']['casting'] and
                  all(row['after'][field] == initial[field] for field in ('root', 'orient')),
                  key + ' restores action, root-motion and orientation state')
            if not baseline:
                # Two engine ticks plus the short post-shot/animation blend allowance.
                allowance = .085 + 3 * frame
                reference = max(pressed_at, last_spawn if key in ('W', 'R') else fired_at)
                check(first_move is not None and first_move - reference <= allowance,
                      key + ' no longer waits for the original long recovery tail')
            save()
        log = out / 'editor.log'
        if log.exists():
            lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
            trace = re.compile(r'TOPDOWN_MOVE_INPUT event=(\S+) t=([\d.]+).*pathAllowed=(\d+) path=(\S+)')
            entries = []
            for line in lines:
                match = trace.search(line)
                if match:
                    entries.append({'event': match[1], 'time': float(match[2]),
                                    'path_allowed': bool(int(match[3])), 'path_status': match[4]})
            for row in report['cases']:
                row['native_path_trace'] = [entry for entry in entries
                                            if row['started_at'] <= entry['time'] <= row['started_at'] + 2]
        report['passed'] = True
        save()
    finally:
        cmd('Character.Input.TraceMove 0')
        cmd('CountessComboQA.FlushInput')
        save()
