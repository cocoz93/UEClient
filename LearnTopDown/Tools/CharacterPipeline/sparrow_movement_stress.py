"""Real-input regression for short move clicks while Sparrow is combat-busy.

Run through new_skills_probe with NEW_SKILLS_FOCUS=sparrow_feedback,
SPARROW_FEEDBACK_PARTS= and SPARROW_FEEDBACK_STUDIES=this filename.
SPARROW_MOVEMENT_BASELINE=1 records old dropped-input behavior without requiring
the pending-click fix. It still requires recovery and fresh clicks to work.
No project assets are saved and no native state is forcibly reset between casts.
"""
import json
import os

import unreal


def sequence(rig):
    out, state = rig['OUT'], rig['STATE']
    baseline = os.environ.get('SPARROW_MOVEMENT_BASELINE') == '1'
    check, cmd = rig['check'], rig['cmd']
    report = {'passed': False, 'baseline': baseline, 'cases': [], 'stress': []}
    if os.environ.get('SPARROW_MOVEMENT_TRACE') == '1':
        cmd('Character.Input.TraceMove 1')

    def save():
        (out / 'sparrow-movement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def read(label):
        p = rig['pawn']()
        movement = p.get_editor_property('character_movement')
        anim = p.get_editor_property('mesh').get_anim_instance()
        montage = anim.get_current_active_montage()
        cmd('CountessInputQA.State movement-' + label)
        native = json.loads((out / ('movement-' + label + '.json')).read_text(encoding='utf-8-sig'))
        row = {'label': label, 'time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
               'location': rig['vec'](p.get_actor_location()), 'busy': p.is_combat_busy(),
               'attacking': p.is_attacking(), 'casting': rig['skills']().is_casting(),
               'movement_mode': str(movement.get_editor_property('movement_mode')),
               'root_motion_mode': str(anim.get_editor_property('root_motion_mode')),
               'orient_rotation_to_movement': movement.get_editor_property('orient_rotation_to_movement'),
               'montage': montage.get_name() if montage else None, 'native': native}
        return row

    def mouse(action, button, q):
        cmd(f'CountessComboQA.Mouse {action} {button} {q.x} {q.y} {q.z}')

    def clear():
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()

    def idle_matches(row, initial):
        return (not row['busy'] and not row['casting'] and not row['attacking'] and
                row['movement_mode'] == initial['movement_mode'] and
                row['root_motion_mode'] == initial['root_motion_mode'] and
                row['orient_rotation_to_movement'] == initial['orient_rotation_to_movement'])

    rig['switch']('sparrow')
    yield .8
    initial = read('initial')
    report['initial'] = initial
    check(not initial['busy'], 'initial Sparrow is not combat-busy')

    # A short click ends before the cast. Move the pointer afterwards to prove
    # that recovery uses the requested world point, not a later cursor position.
    for letter in os.environ.get('SPARROW_MOVEMENT_CASES', 'Q,W,E,R,A,S,D,Basic').split(','):
        rig['case']('movement_short_click_' + letter)
        clear()
        rig['layout']([(550, 0), (700, 350), (700, -350)])
        yield .2
        start = rig['pawn']().get_actor_location()
        shot = rig['aim'](offset=(450, 0))
        if letter == 'Basic':
            mouse('Press', 'Left', shot)
            yield .05
            mouse('Release', 'Left', shot)
        else:
            rig['key'](letter)
        yield .10
        during = read(letter + '-during')
        check(during['busy'], letter + ' begins a real combat action')
        goal = rig['ground'](state['origin'].x - 350, state['origin'].y - 250)
        mouse('Press', 'Right', goal)
        yield 1.0 / rig['FPS']
        mouse('Release', 'Right', goal)
        yield 1.0 / rig['FPS']
        opposite = rig['ground'](state['origin'].x + 350, state['origin'].y + 250)
        mouse('Move', 'Left', opposite)
        yield 2.2
        recovered = read(letter + '-recovered')
        moved = rig['dist'](start, rig['pawn']().get_actor_location())
        row = {'skill': letter, 'during': during, 'recovered': recovered,
               'distance_after_short_click': moved, 'saved_goal': rig['vec'](goal),
               'distance_to_goal': rig['dist'](goal, rig['pawn']().get_actor_location())}
        report['cases'].append(row)
        save()
        check(idle_matches(recovered, initial), letter + ' clears busy state and restores movement/root-motion settings')
        if not baseline:
            check(row['distance_to_goal'] < 50, letter + ' short move click survives recovery and uses saved position')
        # Distinguish a lost click from a permanent lock by making a fresh one.
        clear()
        rig['layout']([(550, 0), (700, 350), (700, -350)])
        yield .1
        mouse('Press', 'Right', goal)
        yield 1.0 / rig['FPS']
        mouse('Release', 'Right', goal)
        yield .9
        fresh = read(letter + '-fresh')
        row['fresh_click'] = fresh
        check(rig['dist'](start, rig['pawn']().get_actor_location()) > 150,
              letter + ' accepts a fresh move click after recovery')
        save()

    if os.environ.get('SPARROW_MOVEMENT_QUICK') == '1':
        report['passed'] = True
        save()
        return

    # Keep effects and buff lifetimes alive while interleaving basic attacks,
    # rejected skill keys during casts, holds, taps and explicit interruptions.
    for index in range(16):
        letter = ('Q', 'W', 'E', 'R', 'A', 'S', 'D', 'F', 'SpaceBar', 'S', 'A', 'D', 'SpaceBar', 'F', 'W', 'R')[index]
        rig['case']('movement_stress_' + str(index) + '_' + letter)
        clear()
        rig['layout']([(550, 0), (700, 350), (700, -350)])
        yield .12
        shot = rig['aim'](offset=(450, 0))
        mouse('Press', 'Left', shot)
        yield .08
        rig['key'](letter)
        yield .08
        for key in ('Q', 'W', 'E', 'R', 'A', 'S', 'D', 'F', 'SpaceBar'):
            rig['key'](key)
        yield .08
        mouse('Release', 'Left', shot)
        goal = rig['ground'](state['origin'].x - 350, state['origin'].y - 250)
        mouse('Press', 'Right', goal)
        yield .08 if index % 2 else .6
        mouse('Release', 'Right', goal)
        yield 2.1
        row = read('stress-' + str(index))
        row['skill'] = letter
        report['stress'].append(row)
        save()
        check(idle_matches(row, initial), 'stress ' + str(index) + ' leaves no persistent cast, attack or root-motion lock')
        # This final click is unconditional; its failure is a genuine remaining
        # movement blockage, not an expected pre-fix short-click loss.
        clear()
        before = rig['pawn']().get_actor_location()
        fresh_goal = rig['ground'](before.x + 300, before.y)
        mouse('Press', 'Right', fresh_goal)
        yield 1.0 / rig['FPS']
        mouse('Release', 'Right', fresh_goal)
        yield .7
        check(rig['dist'](before, rig['pawn']().get_actor_location()) > 100,
              'stress ' + str(index) + ' fresh movement remains functional')

    rig['case']('movement_focus_flush')
    clear()
    rig['layout']([(550, 0), (700, 350), (700, -350)])
    yield .2
    rig['use']('Q', offset=(450, 0))
    yield .1
    start = rig['pawn']().get_actor_location()
    goal = rig['ground'](state['origin'].x - 350, state['origin'].y - 250)
    mouse('Press', 'Right', goal)
    yield 1.0 / rig['FPS']
    mouse('Release', 'Right', goal)
    yield 1.0 / rig['FPS']
    cmd('CountessComboQA.FlushInput')
    yield 2.2
    check(rig['dist'](start, rig['pawn']().get_actor_location()) < 2,
          'focus flush discards the queued movement')

    rig['case']('movement_character_switch')
    rig['use']('Q', offset=(450, 0))
    yield .1
    mouse('Press', 'Right', goal)
    yield 1.0 / rig['FPS']
    mouse('Release', 'Right', goal)
    rig['switch']('countess')
    yield 2.2
    check(not rig['pawn']().is_combat_busy(), 'switch clears previous combat state')
    check(rig['dist'](start, rig['pawn']().get_actor_location()) < 5,
          'Countess does not inherit a pending Sparrow movement')
    mouse('Press', 'Right', goal)
    yield .2
    mouse('Release', 'Right', goal)
    yield .7
    check(rig['dist'](start, rig['pawn']().get_actor_location()) > 150,
          'Countess movement still works after the switch')
    rig['switch']('sparrow')
    yield .8
    check(not rig['pawn']().is_combat_busy(), 'switching back leaves no combat lock')
    if os.environ.get('SPARROW_MOVEMENT_VIDEO') == '1':
        rig['case']('Q_short_move_recovery')
        clear()
        rig['layout']([(550, 0), (700, 350), (700, -350)])
        yield .2
        rig['use']('Q', offset=(450, 0))
        yield .85
        check(rig['pawn']().is_combat_busy(), 'video starts during the Q recovery')
        start = rig['pawn']().get_actor_location()
        state['video_clip'] = {'case': 'Q_short_move_recovery', 'prefix': 'Q_short_move_recovery_video',
                               'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                               'frame_times': []}
        goal = rig['ground'](state['origin'].x - 350, state['origin'].y - 250)
        mouse('Press', 'Right', goal)
        yield 1.0 / rig['FPS']
        mouse('Release', 'Right', goal)
        yield 1.4 - 1.0 / rig['FPS']
        rig['finish_video_clip']()
        moved = rig['dist'](start, rig['pawn']().get_actor_location())
        report['video_distance_after_short_click'] = moved
        check(moved > 100, 'video shows movement after Q using the released click')
    report['dropped_short_clicks'] = [row['skill'] for row in report['cases']
                                    if row['distance_after_short_click'] < 2]
    report['passed'] = True
    save()
