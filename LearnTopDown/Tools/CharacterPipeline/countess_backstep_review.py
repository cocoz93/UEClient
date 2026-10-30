"""Actual-input Countess Space backstep, origin V handoff and movement recovery.

Run through new_skills_probe: NEW_SKILLS_FOCUS=sparrow_feedback,
SPARROW_FEEDBACK_PARTS=, SPARROW_FEEDBACK_STUDIES=this filename.
COUNTESS_BACKSTEP_CASES selects idle,V_baseline,V_handoff,V_after_release,wall,
cancel_Q,cancel_move,switch_pending,queued_move. COUNTESS_BACKSTEP_SHORT=1 selects the three
idle/handoff/already-released cases. Only V_handoff films by default (four seconds).
No assets are saved and no new gameplay damage is introduced by the helper.
"""
import json
import os

import unreal


def sequence(rig):
    out, state, check, cmd = rig['OUT'], rig['STATE'], rig['check'], rig['cmd']
    selected = {name.strip() for name in os.environ.get('COUNTESS_BACKSTEP_CASES', '').split(',') if name.strip()}
    known = {'idle', 'V_baseline', 'V_handoff', 'V_after_release', 'wall', 'cancel_Q', 'cancel_move', 'switch_pending', 'queued_move'}
    check(not selected.difference(known), 'Countess backstep case filter contains valid names')
    if not selected and os.environ.get('COUNTESS_BACKSTEP_SHORT') == '1':
        selected = {'idle', 'V_handoff', 'V_after_release'}
    report = {'passed': False, 'fps': rig['FPS'], 'selected_cases': sorted(selected), 'cases': []}

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def save():
        (out / 'countess-backstep-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def echoes():
        return [actor for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.CountessBackstepEcho)
                if unreal.SystemLibrary.is_valid(actor)]

    def read(label):
        pawn = rig['pawn']()
        movement = pawn.get_editor_property('character_movement')
        mesh = pawn.get_editor_property('mesh')
        anim = mesh.get_anim_instance()
        montage = anim.get_current_active_montage()
        return {'label': label, 'time': now(), 'location': rig['vec'](pawn.get_actor_location()),
                'busy': pawn.is_combat_busy(), 'casting': rig['skills']().is_casting(), 'attacking': pawn.is_attacking(),
                'backstepping': rig['skills']().is_backstepping(), 'mesh_visible': mesh.is_visible(),
                'movement_mode': str(movement.get_editor_property('movement_mode')),
                'root_motion_mode': str(anim.get_editor_property('root_motion_mode')),
                'orient_rotation_to_movement': movement.get_editor_property('orient_rotation_to_movement'),
                'montage': montage.get_name() if montage else None,
                'feedback': rig['skills']().get_input_feedback()}

    def clear():
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()

    def fresh(name):
        rig['switch']('sparrow')
        yield .15
        rig['switch']('countess')
        yield .60
        clear()
        rig['case']('Countess_Space_' + name)
        targets = rig['layout']([(160, 0), (-420, 0), (420, 0)])
        yield .15
        row = {'case': name, 'initial': read(name + '-initial')}
        report['cases'].append(row)
        save()
        return row, targets

    def restore(row):
        after = read(row['case'] + '-recovered')
        row['recovered'] = after
        check(not after['busy'] and not after['casting'] and not after['attacking'] and not after['backstepping'],
              row['case'] + ' clears all movement-blocking combat states')
        for field in ('movement_mode', 'root_motion_mode', 'orient_rotation_to_movement', 'mesh_visible'):
            check(after[field] == row['initial'][field], row['case'] + ' restores ' + field)

    def distance(row, start, facing):
        delta = rig['pawn']().get_actor_location() - start
        backward = -(delta.x * facing.x + delta.y * facing.y)
        side = abs(delta.x * facing.y - delta.y * facing.x)
        row['backward_distance'], row['sideways_distance'] = backward, side
        check(205.0 <= backward <= 235.0 and side < 6.0, row['case'] + ' travels220cm opposite its actual facing')

    def sample_echo(row, echo, origin, moment):
        check(unreal.SystemLibrary.is_valid(echo), row['case'] + ' keeps its origin clone until the handoff ends')
        check(rig['dist'](origin, echo.get_actor_location()) < 2.0, row['case'] + ' keeps the departure clone fixed')
        parts = echo.get_components_by_class(unreal.SkeletalMeshComponent)
        check(len(parts) == 1 and parts[0].get_skeletal_mesh_asset() ==
              rig['pawn']().get_editor_property('mesh').get_skeletal_mesh_asset(), 'departure clone uses the original Countess mesh')
        check(parts[0].get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION, 'departure clone has no collision')
        parent = parts[0].get_material(0).get_base_material().get_path_name()
        check('M_CountessEShadowDissolve' in parent, 'departure clone preserves the existing dark crimson shadow material')
        poses = [part for part in echo.get_components_by_class(unreal.PoseableMeshComponent)
                 if 'CountessBackstepAfterimage' in {str(tag) for tag in part.component_tags}]
        check(len(poses) == 3 and all(part.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION for part in poses),
              'Countess Space owns three collision-free motion snapshots')
        row.setdefault('echo_samples', []).append({'moment': moment, 'location': rig['vec'](echo.get_actor_location()),
            'transferred_actions': echo.get_transferred_action_count(), 'pose_position': parts[0].get_position(),
            'visible_afterimages': sum(part.is_visible() for part in poses), 'material': parent})
        if moment == .10:
            check(any(part.is_visible() for part in poses), 'Countess Space shows its brief motion afterimages')
        if moment >= .45:
            check(not any(part.is_visible() for part in poses), 'Countess Space afterimages fade after the short move')
        save()

    def fresh_move(row):
        before = rig['pawn']().get_actor_location()
        goal = rig['ground'](before.x, before.y + 300.0)
        cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield 1.0 / rig['FPS']
        cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        yield .75
        row['fresh_move_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
        check(row['fresh_move_distance'] > 120.0, row['case'] + ' accepts a fresh move without flushing input')

    rig['switch']('countess')
    yield .65
    check(hasattr(unreal, 'CountessBackstepEcho') and hasattr(rig['skills'](), 'is_backstepping'),
          'native Countess backstep class and state API are loaded')
    cmd('Countess.Skills.IgnoreCooldowns 1')
    definition = rig['skills']().get_editor_property('skills')[1]
    damage = definition.get_editor_property('damage')
    action = definition.get_editor_property('action_time')
    recovery = definition.get_editor_property('recovery_time')
    report['V_definition'] = {'damage': damage, 'action_time': action, 'recovery_time': recovery,
                              'range': definition.get_editor_property('range')}
    save()

    for name in ('V_baseline', 'idle', 'V_handoff', 'V_after_release', 'wall', 'cancel_Q', 'cancel_move', 'switch_pending', 'queued_move'):
        if selected and name not in selected:
            continue
        row, targets = yield from fresh(name)
        rig['aim'](targets[0])
        rate = rig['skills']().get_skill_play_rate(unreal.CountessSkill.BLADE_SIPHON)
        if name == 'V_baseline':
            rig['key']('V')
            yield recovery / rate + .15
            row['health'] = [rig['health'](target) for target in targets]
            check(abs(row['health'][0] - (100.0 - damage)) < .02 and all(abs(h - 100.0) < .02 for h in row['health'][1:]),
                  'shared V release preserves its original damage and range without Space')
            restore(row)
            save()
            continue
        if name in ('idle', 'V_handoff', 'V_after_release', 'cancel_Q', 'cancel_move', 'switch_pending', 'queued_move'):
            video_names = {value.strip() for value in os.environ.get('COUNTESS_BACKSTEP_VIDEO_CASES', 'V_handoff').split(',') if value.strip()}
            filming = os.environ.get('NEW_SKILLS_VIDEO') == '1' and name in video_names
            film_start = now()
            if filming:
                state['video_clip'] = {'case': 'Countess_Space_' + name, 'prefix': 'Countess_Space_' + name + '_video',
                                      'cast_time': film_start, 'frame_times': []}
                yield .25
            v_started = now()
            if name in ('V_handoff', 'V_after_release', 'cancel_move', 'switch_pending'):
                rig['key']('V')
                yield action / rate + min(.06, (recovery - action) / rate * .25) if name == 'V_after_release' else .08
                check(rig['skills']().is_casting(), name + ' begins Space during the real V cast')
            elif name == 'cancel_Q':
                rig['key']('Q')
                yield .04
                check(rig['skills']().is_casting(), 'Q is preparing before the Space cancellation')
            start, facing = rig['pawn']().get_actor_location(), rig['pawn']().get_actor_forward_vector()
            space_started = now()
            rig['key']('SpaceBar')
            yield 1.0 / rig['FPS']
            check(rig['skills']().is_backstepping() and len(echoes()) == 1, name + ' accepts actual Space and creates one clone')
            echo = echoes()[0]
            check(rig['dist'](echo.get_actor_location(), start) < 2.0, 'Countess clone starts at the pre-backstep origin')
            if name == 'switch_pending':
                old = rig['pawn']()
                rig['switch']('sparrow')
                yield max(.65, action / rate)
                check(not unreal.SystemLibrary.is_valid(old) and not echoes(), 'numeric switch removes Countess and its pending departure clone')
                check(all(abs(rig['health'](target) - 100.0) < .02 for target in targets), 'owner switch cancels pending transferred V damage')
                check(not rig['pawn']().is_combat_busy(), 'switched Sparrow is movement-ready')
                save()
                continue
            if name == 'cancel_move':
                delay = .10 - (now() - space_started)
                if delay > .001:
                    yield delay
                check(rig['skills']().is_backstepping(), 'explicit cancellation starts while Countess is moving')
                echo.destroy_actor()
                yield max(.45, action / rate)
                check(not echoes(), 'explicit cancellation destroys the clone and delayed V timer')
                check(all(abs(rig['health'](target) - 100.0) < .02 for target in targets),
                      'cancelled moving clone does not release pending V damage')
                restore(row)
                yield from fresh_move(row)
                save()
                continue
            if name == 'queued_move':
                point = rig['ground'](start.x, start.y + 300.0)
                cmd(f'CountessComboQA.Mouse Press Right {point.x} {point.y} {point.z}')
                yield 1.0 / rig['FPS']
                cmd('CountessInputQA.State countess-backstep-queued-click')
                native = json.loads((out / 'countess-backstep-queued-click.json').read_text(encoding='utf-8-sig'))
                row['pressed_cursor'] = native
                cmd(f'CountessComboQA.Mouse Release Right {point.x} {point.y} {point.z}')
                check(all(key in native for key in ('cursor_goal_x', 'cursor_goal_y', 'cursor_goal_z')),
                      'queued Countess move resolves to a valid navigation target')
                goal = unreal.Vector(native['cursor_goal_x'], native['cursor_goal_y'], native['cursor_goal_z'])
                yield 1.0
                restore(row)
                row['queued_goal_distance'] = rig['dist'](goal, rig['pawn']().get_actor_location())
                check(row['queued_goal_distance'] < 75.0, 'Space recovery consumes the released Countess move click')
                yield from fresh_move(row)
                save()
                continue
            for moment in (.10, .20, .45):
                delay = moment - (now() - space_started)
                if delay > .001:
                    yield delay
                sample_echo(row, echo, start, moment)
                if moment == .10:
                    check(rig['skills']().is_backstepping(), 'Countess move remains active at0.10seconds')
                    for rejected in ('Q', 'V', 'E', 'R', 'A', 'S', 'D', 'F'):
                        rig['key'](rejected)
                    check(len(echoes()) == 1 and rig['skills']().is_backstepping(), 'backstep rejects other actions without replacing its clone')
                if moment == .20:
                    check(not rig['skills']().is_backstepping(), 'Countess movement completes within0.20seconds')
                    distance(row, start, facing)
                rig['capture']('Countess_Space_' + name + '_t' + str(round(moment * 100)).zfill(3))
            release_delay = max(0.0, action / rate - (space_started - v_started)) if name == 'V_handoff' else 0.0
            delay = max(.60, release_delay + .08) - (now() - space_started)
            if delay > .001:
                yield delay
            sample_echo(row, echo, start, .60)
            expected_actions = 1 if name == 'V_handoff' else 0
            check(echo.get_transferred_action_count() == expected_actions, name + ' transfers exactly the pending original V action count')
            row['health'] = [rig['health'](target) for target in targets]
            expected = 100.0 - damage if name in ('V_handoff', 'V_after_release') else 100.0
            check(abs(row['health'][0] - expected) < .02 and all(abs(h - 100.0) < .02 for h in row['health'][1:]),
                  name + ' preserves damage, fixed-origin range and absence of duplicate hits')
            restore(row)
            yield from fresh_move(row)
            if filming:
                delay = 4.0 - (now() - film_start)
                if delay > .001:
                    yield delay
                row['video_seconds'] = now() - film_start
            rig['finish_video_clip']()
            save()
            continue
        if name == 'wall':
            barrier = rig['wall_fixture'](-130)
            try:
                yield .20
                start = rig['pawn']().get_actor_location()
                rig['key']('SpaceBar')
                yield .60
                row['wall_distance'] = rig['dist'](start, rig['pawn']().get_actor_location())
                check(15.0 < row['wall_distance'] < 125.0 and rig['pawn']().get_actor_location().x > start.x - 110.0,
                      'Countess capsule sweep stops before the rear wall')
                restore(row)
                yield from fresh_move(row)
            finally:
                if unreal.SystemLibrary.is_valid(barrier):
                    barrier.destroy_actor()
            save()
    report['passed'] = True
    save()
