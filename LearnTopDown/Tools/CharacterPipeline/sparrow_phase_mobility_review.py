"""Native Space blink while V is active. Uses the existing input/capture rig.

SPARROW_PHASE_SHORT=1 repeats only blink and cancellation at the second FPS.
The former roll helper still owns normal roll poses, walls and basic recovery.
"""
import json
import os

import unreal


def sequence(rig):
    check, cmd, out = rig['check'], rig['cmd'], rig['OUT']
    frame = 1.0 / rig['FPS']
    short = os.environ.get('SPARROW_PHASE_SHORT') == '1'
    report = {'passed': False, 'fps': rig['FPS'], 'short': short, 'cases': []}

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def valid(actor):
        return actor is not None and unreal.SystemLibrary.is_valid(actor)

    def actors(cls):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), cls) if valid(a)]

    def body():
        pawn = rig['pawn']()
        mesh = pawn.get_editor_property('mesh')
        movement = pawn.get_editor_property('character_movement')
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(mesh.get_skeletal_mesh_asset())
        return {'visible': mesh.is_visible(),
                'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
                'sections': [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())] for lod in range(lods)],
                'root_motion': str(mesh.get_anim_instance().get_editor_property('root_motion_mode')),
                'orient': movement.get_editor_property('orient_rotation_to_movement')}

    def save():
        (out/'sparrow-phase-mobility.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def fresh(name):
        rig['switch']('countess')
        yield .2
        rig['switch']('sparrow')
        yield .65
        rig['case'](name)
        rig['layout']([(700, 350), (800, -400), (-500, 500)])
        yield .2
        normal = body()
        rig['key']('V')
        yield 1.65
        check(len(actors(unreal.SparrowAscensionWings)) == 1, name+' starts with native V wings')
        check(rig['skills']().get_ascension_remaining() > 37, name+' starts during the actual V lifetime')
        row = {'case': name, 'normal': normal, 'transformed': body(), 'samples': []}
        report['cases'].append(row)
        save()
        return row

    def start(row):
        rig['aim'](offset=(550, 0))
        row['start'] = rig['vec'](rig['pawn']().get_actor_location())
        row['input_at'] = now()
        rig['key']('SpaceBar')
        yield frame
        active = actors(unreal.SparrowGoldRoll)
        check(len(active) == 1 and rig['skills']().get_active_skill_number() == 18, row['case']+' activates one Space actor')
        actor = active[0]
        check(actor.is_teleporting() and abs(actor.get_roll_duration()-.14) < .001, row['case']+' selects native0.14s teleport mode')
        return actor

    def restored(row, state):
        check(not actors(unreal.SparrowGoldRoll) and not rig['skills']().is_rolling(), row['case']+' clears mobility actor and lock')
        rig['recovered']()
        row['restored'] = body()
        check(row['restored'] == state, row['case']+' restores visibility, materials, sections, root motion and orientation')
        save()

    def fresh_move(row):
        before = rig['pawn']().get_actor_location()
        goal = rig['ground'](before.x, before.y+300)
        cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield frame
        cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        yield .7
        row['fresh_move_cm'] = rig['dist'](before, rig['pawn']().get_actor_location())
        check(row['fresh_move_cm'] > 150, row['case']+' accepts actual movement after recovery')
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    try:
        row = yield from fresh('Space_V_blink')
        if os.environ.get('NEW_SKILLS_VIDEO') == '1':
            rig['STATE']['video_clip'] = {'case': row['case'], 'prefix': row['case']+'_video', 'cast_time': now(), 'frame_times': []}
        yield .25
        actor = yield from start(row)
        captures = set()
        while now()-row['input_at'] < .45:
            position = rig['pawn']().get_actor_location()
            elapsed = now()-row['input_at']
            components = actor.get_components_by_class(unreal.SkeletalMeshComponent) if valid(actor) else []
            roll_visible = any(part.is_visible() for part in components if part.get_name() == 'RollSilhouette')
            row['samples'].append({'elapsed': elapsed, 'position': rig['vec'](position), 'roll_visible': roll_visible,
                                   'moving': rig['skills']().is_rolling()})
            check(not roll_visible, 'transformed blink never renders the roll donor')
            for moment in (.067, .10, .20):
                if elapsed >= moment and moment not in captures:
                    rig['capture']('Space_V_blink_t'+str(round(moment*1000)))
                    captures.add(moment)
            yield frame
        start_x = row['start'][0]
        distances = [sample['position'][0]-start_x for sample in row['samples']]
        row['travel_samples_cm'] = distances
        check(all(abs(d) < 3 or abs(d-480) < 3 for d in distances), 'blink positions are only departure or destination, never interpolated travel')
        check(abs(distances[-1]-480) < 3, 'transformed Space keeps480cm travel')
        busy = [s['elapsed'] for s in row['samples'] if s['moving']]
        check(busy and max(busy) <= .14+2*frame, 'blink movement lock ends within0.14s plus input/frame observation tolerance')
        yield .65
        restored(row, row['transformed'])
        check(len(actors(unreal.SparrowAscensionWings)) == 1, 'blink preserves the same V form')
        yield from fresh_move(row)

        row = yield from fresh('Space_V_cancel')
        actor = yield from start(row)
        actor.destroy_actor()
        yield .2
        restored(row, row['transformed'])
        yield from fresh_move(row)

        if not short:
            row = yield from fresh('Space_V_wall')
            wall = rig['wall_fixture'](250)
            try:
                yield .1
                yield from start(row)
                yield .4
                distance = rig['pawn']().get_actor_location().x-row['start'][0]
                row['travel_cm'] = distance
                check(100 < distance < 235, 'blink respects the original capsule wall stop')
                restored(row, row['transformed'])
            finally:
                if valid(wall):
                    wall.destroy_actor()
            yield from fresh_move(row)

            row = yield from fresh('Space_V_expiry_during_blink')
            yield from start(row)
            actors(unreal.SparrowAscensionWings)[0].destroy_actor()
            yield .35
            restored(row, row['normal'])
            check(rig['skills']().get_ascension_remaining() == 0, 'V ending mid-blink leaves the normal body and no stale form')
            yield from fresh_move(row)

            row = yield from fresh('Space_V_switch')
            yield from start(row)
            old = rig['pawn']()
            rig['switch']('countess')
            yield .4
            check(not valid(old) and not actors(unreal.SparrowGoldRoll) and not actors(unreal.SparrowAscensionWings),
                  'switch destroys old pawn, blink and form together')
            check(rig['pawn']().get_editor_property('mesh').is_visible() and not rig['pawn']().is_combat_busy(),
                  'Countess is visible and unlocked after a mid-blink switch')

            row = yield from fresh('Space_shared_cooldown')
            cmd('Sparrow.Skills.IgnoreCooldowns 0')
            yield from start(row)
            yield .3
            actors(unreal.SparrowAscensionWings)[0].destroy_actor()
            yield .1
            before = rig['pawn']().get_actor_location()
            rig['key']('SpaceBar')
            yield .1
            check(not actors(unreal.SparrowGoldRoll) and rig['dist'](before, rig['pawn']().get_actor_location()) < 2,
                  'normal roll cannot bypass the blink shared cooldown after form expires')
            check('cooldown' in rig['skills']().get_input_feedback().lower(), 'shared cooldown reports rejection')
            yield max(.01, 6.2-(now()-row['input_at']))
            rig['aim'](offset=(900, 0))
            rig['key']('SpaceBar')
            yield frame
            normal_roll = actors(unreal.SparrowGoldRoll)
            check(len(normal_roll) == 1 and not normal_roll[0].is_teleporting() and abs(normal_roll[0].get_roll_duration()-.4) < .001,
                  'Space returns to0.40s roll when V ends and cooldown elapses')
            yield .6
            restored(row, row['normal'])
            yield from fresh_move(row)
        report['passed'] = True
        save()
    finally:
        save()
        cmd('Sparrow.Skills.IgnoreCooldowns 1')
