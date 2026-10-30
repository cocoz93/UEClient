"""Actual-input Countess reforge review; no asset saves or direct gameplay damage.

new_skills_probe: NEW_SKILLS_FOCUS=sparrow_feedback, SPARROW_FEEDBACK_PARTS=,
SPARROW_FEEDBACK_STUDIES=countess_reforge_review.py. NEW_SKILLS_VIDEO=1 films
continuous current-camera frames, with a 0.20s lead-in and no synthetic frames.
COUNTESS_REFORGE_MODE=visual (default) films E,R,A,S,D,V; PARTS=E,R,... filters
that list and may also select F,Space. Functional mode uses PARTS=S,V,INPUT,F,
SWITCH,W by default. COUNTESS_REFORGE_CASES optionally selects S_chain,V_space,
queued_move,rejected_attack,F_safety,switch_cleanup,empty_W for a focused repeat.
Every case starts from a new Countess and reset 100HP fixtures. A failed check
stops the runner and leaves its report/captures intact for diagnosis.
"""
import json
import os

import unreal


DEFINITIONS = {
    'E': {'slot': 2, 'commit': .32, 'recovery': .80, 'damage': 55., 'target': (450, 0),
          'times': (.40, .65, 1.05), 'end': 1.80, 'kind': 'CountessRuinVisual'},
    'R': {'slot': 3, 'commit': .50, 'recovery': 1., 'damage': 90., 'target': (250, 0),
          'times': (.58, .76, 1.10), 'end': 2.10, 'kind': 'CountessRuinVisual'},
    'A': {'slot': 8, 'commit': .22, 'recovery': .75, 'damage': 60., 'target': (300, 0),
          'times': (.48, 1., 1.65, 2.20), 'end': 2.75, 'kind': 'CountessInfernoVisual'},
    'S': {'slot': 9, 'commit': .18, 'recovery': .85, 'damage': 24., 'target': (160, 0),
          'times': (.32, .45, .65, 1.35), 'end': 1.80, 'kind': 'CountessDemonForm'},
    'D': {'slot': 10, 'commit': .18, 'recovery': .62, 'damage': 54., 'target': (300, 0),
          'times': (.28, .43, .62), 'end': 1.35, 'kind': 'CountessRuinVisual'},
    'V': {'slot': 16, 'commit': .40, 'recovery': 3.8, 'damage': 84., 'target': (120, 0),
          'times': (.65, 1.20, 2.25, 3.35), 'end': 4.15, 'kind': 'CountessInfernoVisual'},
}
VISUAL_CLASSES = ('CountessRuinVisual', 'CountessInfernoVisual', 'CountessDemonForm', 'CountessBackstepEcho', 'CountessRebirthFX')
FUNCTIONAL_PARTS = {'S_chain': 'S', 'V_space': 'V', 'queued_move': 'INPUT',
                    'rejected_attack': 'INPUT', 'F_safety': 'F', 'switch_cleanup': 'SWITCH', 'empty_W': 'W'}


def sequence(rig):
    out, state, check, cmd = rig['OUT'], rig['STATE'], rig['check'], rig['cmd']
    mode = os.environ.get('COUNTESS_REFORGE_MODE', 'visual')
    check(mode in ('visual', 'functional'), 'Countess reforge mode is visual or functional')
    default_parts = 'E,R,A,S,D,V' if mode == 'visual' else 'S,V,INPUT,F,SWITCH,W'
    parts = {x.strip() for x in os.environ.get('COUNTESS_REFORGE_PARTS', default_parts).split(',') if x.strip()}
    cases = {x.strip() for x in os.environ.get('COUNTESS_REFORGE_CASES', '').split(',') if x.strip()}
    check(parts and parts <= (set(DEFINITIONS) | {'Q', 'F', 'Space', 'INPUT', 'SWITCH', 'W'}), 'valid reforge part filter')
    check(cases <= set(FUNCTIONAL_PARTS), 'valid functional case filter')
    frame = 1.0 / rig['FPS']
    report = {'passed': False, 'mode': mode, 'fps': rig['FPS'], 'parts': sorted(parts), 'cases': [],
              'assets_saved': False, 'visual_acceptance': 'pending actual viewport review',
              'definitions': DEFINITIONS, 'input_clock': 'elapsed game seconds since queued key; next input tick observed'}

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def save():
        (out / 'countess-reforge-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def actors(name):
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), getattr(unreal, name))
                if unreal.SystemLibrary.is_valid(a)]

    def residue():
        return unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'CountessCursorBlinkResidue')

    def body():
        mesh = rig['pawn']().get_editor_property('mesh')
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(mesh.get_skeletal_mesh_asset())
        return {'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
                'bases': [mesh.get_material(i).get_base_material().get_path_name() for i in range(mesh.get_num_materials())],
                'sections': [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())] for lod in range(lods)],
                'relative_location': rig['vec'](mesh.get_editor_property('relative_location')), 'visible': mesh.is_visible()}

    def snapshot(label, native=False):
        pawn, skills = rig['pawn'](), rig['skills']()
        movement = pawn.get_editor_property('character_movement')
        anim = pawn.get_editor_property('mesh').get_anim_instance()
        row = {'label': label, 'time': now(), 'location': rig['vec'](pawn.get_actor_location()),
               'active': skills.get_active_skill_number(), 'casting': skills.is_casting(),
               'busy': pawn.is_combat_busy(), 'attacking': pawn.is_attacking(),
               'form_remaining': skills.get_demon_form_remaining(), 'body': body(),
               'movement_mode': str(movement.get_editor_property('movement_mode')),
               'orient': movement.get_editor_property('orient_rotation_to_movement'),
               'root_motion': str(anim.get_editor_property('root_motion_mode')),
               'feedback': skills.get_input_feedback(), 'visuals': {name: [a.get_name() for a in actors(name)] for name in VISUAL_CLASSES}}
        if native:
            token = 'reforge-' + label
            cmd('CountessInputQA.State ' + token)
            row['input'] = json.loads((out / (token + '.json')).read_text(encoding='utf-8-sig'))
        return row

    def mouse(action, button, point):
        cmd(f'CountessComboQA.Mouse {action} {button} {point.x} {point.y} {point.z}')

    def until(start, elapsed):
        delay = elapsed - (now() - start)
        if delay > .0001:
            yield delay

    def fresh(name, offsets=None):
        rig['switch']('sparrow')
        yield .20
        rig['switch']('countess')
        yield .65
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()
        rig['case']('Countess_reforge_' + name)
        targets = rig['layout'](offsets or [(650, 450), (650, -450), (300, 650)])
        yield .20
        row = {'case': name, 'initial': snapshot(name + '-initial'), 'samples': []}
        report['cases'].append(row)
        save()
        return row, targets

    def restored(row, materials=True):
        sample = snapshot(row['case'] + '-recovered')
        row['recovered'] = sample
        save()
        check(not sample['casting'] and not sample['busy'] and not sample['attacking'] and sample['active'] == 0,
              row['case'] + ' restores idle input state')
        for name in ('movement_mode', 'orient', 'root_motion'):
            check(sample[name] == row['initial'][name], row['case'] + ' restores ' + name)
        check(sample['body']['relative_location'] == row['initial']['body']['relative_location'] and sample['body']['visible'],
              row['case'] + ' restores exact mesh-relative position and visibility')
        if materials:
            check(sample['body']['materials'] == row['initial']['body']['materials'] and
                  sample['body']['sections'] == row['initial']['body']['sections'], row['case'] + ' restores original materials and sections')

    def fresh_move(row):
        before = rig['pawn']().get_actor_location()
        point = rig['ground'](before.x, before.y + 280)
        mouse('Press', 'Right', point)
        yield frame
        mouse('Release', 'Right', point)
        yield .75
        row['fresh_move_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
        save()
        check(row['fresh_move_distance'] > 120, row['case'] + ' accepts a fresh move after recovery')

    def cast(key, offset=(550, 0)):
        rig['aim'](offset=offset)
        began = now()
        rig['key']('SpaceBar' if key == 'Space' else key)
        yield frame
        if key in DEFINITIONS:
            check(rig['skills']().get_active_skill_number() == DEFINITIONS[key]['slot'] + 1,
                  key + ' actual input selects its new active slot')
        return began

    def visual_sample(row, key, elapsed):
        sample = snapshot(key + '-' + str(round(elapsed * 100)))
        visible = []
        for actor in actors(DEFINITIONS[key]['kind']):
            meshes = actor.get_components_by_class(unreal.MeshComponent)
            particles = actor.get_components_by_class(unreal.ParticleSystemComponent)
            visible.append({'name': actor.get_name(), 'meshes': len(meshes),
                'visible_meshes': sum(c.is_visible() for c in meshes), 'active_particles': sum(c.is_active() for c in particles),
                'live_particles': sum(c.get_num_active_particles() for c in particles),
                'particle_detail': [{'template': c.get_editor_property('template').get_path_name() if c.get_editor_property('template') else None,
                                     'live': c.get_num_active_particles(), 'active': c.is_active()} for c in particles],
                'age': actor.get_age() if hasattr(actor, 'get_age') else actor.get_visual_age(),
                'position': rig['vec'](actor.get_actor_location())})
        sample['presentation'] = visible
        if elapsed == {'E': .65, 'R': .76, 'D': .43, 'S': .45, 'A': 1., 'V': 1.2}.get(key):
            token = 'quality-fx-' + key
            cmd('SparrowQA.State ' + token)
            sample['native_particle_receipt'] = token + '.json'
        row['samples'].append(sample)
        save()
        check(visible and any(v['visible_meshes'] or v['active_particles'] for v in visible),
              key + ' owns active rendered components at its sampled phase')
        rig['capture']('Countess_reforge_' + key + '_t' + str(round(elapsed * 100)).zfill(3))

    def damage(row, targets, amount):
        row['health'] = [rig['health'](d) for d in targets]
        save()
        check(abs(row['health'][0] - (100.0 - amount)) < .05, row['case'] + ' applies expected total damage ' + str(amount))
        check(all(abs(v - 100.0) < .05 for v in row['health'][1:]), row['case'] + ' leaves out-of-range targets intact')

    def selected(name):
        return name in cases if cases else FUNCTIONAL_PARTS[name] in parts

    rig['switch']('countess')
    yield .7
    check(all(hasattr(unreal, name) for name in VISUAL_CLASSES) and hasattr(rig['skills'](), 'get_demon_form_remaining'),
          'reforge runtime classes and form state API are loaded')
    cmd('Countess.Skills.IgnoreCooldowns 1')
    save()
    try:
        if mode == 'visual':
            if 'Q' in parts:
                row, targets = yield from fresh('Q', [(450, 0), (650, 450), (650, -450)])
                if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                    state['video_clip'] = {'case': state['case'], 'prefix': 'Countess_reforge_Q_video',
                                          'cast_time': now(), 'frame_times': []}
                yield .20
                before = rig['pawn']().get_actor_location()
                rig['aim'](d=targets[0])
                began = now()
                rig['key']('Q')
                yield frame
                check(rig['skills']().is_casting(), 'Q actual target input begins cast')
                for at in (.08, .22, .35, .55, .95):
                    yield from until(began, at)
                    row['samples'].append(snapshot('Q-' + str(round(at * 100))))
                    if at == .35:
                        row['contact_particles'] = []
                        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.Actor):
                            for effect in actor.get_components_by_class(unreal.ParticleSystemComponent):
                                if effect.get_num_active_particles() > 0:
                                    template = effect.get_editor_property('template')
                                    row['contact_particles'].append({'owner': actor.get_name(),
                                        'template': template.get_path_name() if template else None,
                                        'live': effect.get_num_active_particles(),
                                        'materials': [effect.get_material(i).get_path_name() if effect.get_material(i) else None
                                                      for i in range(effect.get_num_materials())]})
                    rig['capture']('Countess_reforge_Q_t' + str(round(at * 100)).zfill(3))
                damage(row, targets, 35.)
                check(rig['dist'](before, rig['pawn']().get_actor_location()) > 250,
                      'Q reaches its target while retaining return state')
                restored(row)
                yield from until(began, 1.15)
                rig['key']('Q')
                yield .80
                rig['capture']('Countess_reforge_Q_return')
                row['return_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
                check(row['return_distance'] < 5., 'Q second input returns to original point')
                damage(row, targets, 35.)
                rig['finish_video_clip']()
                restored(row)
                yield from fresh_move(row)
            for key in ('E', 'R', 'A', 'S', 'D', 'V', 'F', 'Space'):
                if key not in parts:
                    continue
                definition = DEFINITIONS.get(key)
                offsets = [definition['target'], (650, 450), (650, -450)] if definition else None
                row, targets = yield from fresh(key, offsets)
                if os.environ.get('NEW_SKILLS_VIDEO') == '1':
                    state['video_clip'] = {'case': state['case'], 'prefix': 'Countess_reforge_' + key + '_video',
                                           'cast_time': now(), 'frame_times': []}
                yield .20
                before = rig['pawn']().get_actor_location()
                began = yield from cast(key, (450, 0) if key == 'E' else (500, 0))
                row['input_at'] = began
                if definition:
                    for at in definition['times']:
                        yield from until(began, at)
                        visual_sample(row, key, at)
                    yield from until(began, definition['end'])
                    damage(row, targets, definition['damage'])
                else:
                    for at in (.10, .25, .45):
                        yield from until(began, at)
                        rig['capture']('Countess_reforge_' + key + '_t' + str(round(at * 100)).zfill(3))
                    yield from until(began, 1.)
                    row['travel_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
                    row['move_result'] = snapshot(key + '-travel')
                    save()
                    check((450 < row['travel_distance'] < 550) if key == 'F' else (205 < row['travel_distance'] < 235),
                          key + ' reaches its expected destination')
                rig['finish_video_clip']()
                restored(row, materials=key != 'S')
                if key == 'S':
                    check(21.0 < rig['skills']().get_demon_form_remaining() < 24.0, 'S continues its24second form after casting')
                else:
                    check(not actors('CountessRuinVisual') and not actors('CountessInfernoVisual'), key + ' retires its finite field')
                yield from fresh_move(row)
            report['passed'] = True
            save()
            return

        if selected('S_chain'):
            row, targets = yield from fresh('S_chain', [(450, 300), (650, -450), (650, 450)])
            began = yield from cast('S')
            yield from until(began, 1.)
            form_body = body()
            check(form_body['materials'] != row['initial']['body']['materials'] and len(actors('CountessDemonForm')) == 1,
                  'S replaces the whole body material while preserving one form actor')
            check(form_body['sections'] == row['initial']['body']['sections'], 'S preserves source section visibility')
            began = yield from cast('E', (450, 300))
            yield from until(began, 1.6)
            check(abs(rig['health'](targets[0]) - 34.) < .05, 'S amplifies E55 to66 damage')
            began = yield from cast('V')
            yield from until(began, .95)
            field = actors('CountessInfernoVisual')
            check(len(field) == 1, 'S plus V creates one installed storm')
            center = field[0].get_field_center()
            check(body()['relative_location'][2] > row['initial']['body']['relative_location'][2] + 40, 'V visibly lifts the mesh')
            check(body()['materials'] == form_body['materials'], 'V preserves S materials')
            yield from cast('Space')
            yield .30
            check(body()['materials'] == form_body['materials'] and body()['relative_location'] == row['initial']['body']['relative_location'],
                  'Space preserves S and restores V mesh offset')
            check(unreal.SystemLibrary.is_valid(field[0]) and rig['dist'](center, field[0].get_field_center()) < 2,
                  'Space leaves the installed V field fixed')
            before = rig['pawn']().get_actor_location()
            yield from cast('F', (300, 250))
            yield .15
            check(rig['dist'](before, rig['pawn']().get_actor_location()) > 200 and body()['materials'] == form_body['materials'],
                  'F blinks while retaining S materials')
            row['form_during_chain'] = snapshot('S-chain-mobility')
            yield rig['skills']().get_demon_form_remaining() + .15
            check(not actors('CountessDemonForm') and rig['skills']().get_demon_form_remaining() <= .001,
                  'S expires naturally after24seconds')
            restored(row)
            yield from fresh_move(row)
            save()

        if selected('V_space'):
            row, targets = yield from fresh('V_space', [(120, 0), (650, 450), (650, -450)])
            began = yield from cast('V')
            yield from until(began, .95)
            field = actors('CountessInfernoVisual')
            check(len(field) == 1, 'V installs one field before Space')
            center = field[0].get_field_center()
            before = rig['pawn']().get_actor_location()
            yield from cast('Space')
            yield .30
            row['space_distance'] = rig['dist'](before, rig['pawn']().get_actor_location())
            check(205 < row['space_distance'] < 235, 'V can be exited with actual Space backstep')
            check(unreal.SystemLibrary.is_valid(field[0]) and rig['dist'](center, field[0].get_field_center()) < 2,
                  'V field stays at the original cast origin after Space')
            restored(row)
            yield from until(began, 4.20)
            damage(row, targets, 84.)
            check(not actors('CountessInfernoVisual'), 'V finishes all12pulses and then removes its field')
            yield from fresh_move(row)
            save()

        for name in ('queued_move', 'rejected_attack'):
            if not selected(name):
                continue
            row, targets = yield from fresh(name)
            began = yield from cast('R')
            yield from until(began, .15)
            start = rig['pawn']().get_actor_location()
            goal = None
            for index, (dx, dy) in enumerate(((0, 300), (-300, 250), (300, 250), (0, -300))):
                point = rig['ground'](start.x + dx, start.y + dy)
                mouse('Move', 'Right', point)
                probe = snapshot(name + '-nav-' + str(index), native=True)
                row.setdefault('nav_preflight', []).append(probe)
                native = probe['input']
                keys = ('cursor_goal_x', 'cursor_goal_y', 'cursor_goal_z')
                if native.get('navigation_ready') and all(k in native for k in keys) and native.get('cursor_goal_distance', 0) > 150:
                    goal = unreal.Vector(*(native[k] for k in keys))
                    mouse('Press', 'Right', point)
                    yield frame
                    row['pressed_input'] = snapshot(name + '-pressed', native=True)
                    mouse('Release', 'Right', point)
                    break
            save()
            check(goal is not None and row['pressed_input']['busy'] and row['pressed_input']['input'].get('right_mouse_held'),
                  name + ' queues a valid cursor/nav click during the cast')
            if name == 'rejected_attack':
                mouse('Press', 'Left', targets[0].get_actor_location())
                yield frame
                mouse('Release', 'Left', targets[0].get_actor_location())
                yield frame
                check(not rig['pawn']().is_attacking() and rig['skills']().get_active_skill_number() == 4,
                      'rejected basic attack preserves the active R cast')
            yield from until(began, 2.)
            row['queued_distance'] = rig['dist'](start, rig['pawn']().get_actor_location())
            row['goal_distance'] = rig['dist'](goal, rig['pawn']().get_actor_location())
            row['after_queue'] = snapshot(name + '-result', native=True)
            save()
            check(row['queued_distance'] > 120 and row['goal_distance'] < 120, name + ' consumes the queued click after recovery')
            restored(row)
            yield from fresh_move(row)

        if selected('F_safety'):
            row, targets = yield from fresh('F_safety')
            cmd('Countess.Skills.IgnoreCooldowns 0')
            start = rig['pawn']().get_actor_location()
            began = yield from cast('F', (500, 0))
            yield .10
            landing = rig['pawn']().get_actor_location()
            check(450 < rig['dist'](start, landing) < 550 and abs(landing.z - start.z) < 8, 'F lands safely on cursor ground')
            check(bool(residue()), 'F leaves its short crimson travel residue')
            yield from cast('F', (0, 0))
            yield .10
            check(rig['dist'](landing, rig['pawn']().get_actor_location()) < 2 and 'cooldown' in rig['skills']().get_input_feedback().lower(),
                  'F rejects a second input during its six second cooldown')
            before = rig['pawn']().get_actor_location()
            yield from cast('Space')
            yield .30
            check(205 < rig['dist'](before, rig['pawn']().get_actor_location()) < 235, 'Space cooldown is independent of F')
            yield from until(began, 6.25)
            before = rig['pawn']().get_actor_location()
            yield from cast('F', (500, 250))
            yield .15
            check(rig['dist'](before, rig['pawn']().get_actor_location()) > 200, 'F accepts input after its six second cooldown')
            restored(row)
            cmd('Countess.Skills.IgnoreCooldowns 1')
            row, targets = yield from fresh('F_wall')
            wall = rig['wall_fixture'](250)
            try:
                yield .2
                start = rig['pawn']().get_actor_location()
                yield from cast('F', (500, 0))
                yield .15
                check(rig['dist'](start, rig['pawn']().get_actor_location()) < 2 and not residue(),
                      'F rejects a destination behind a solid wall without leaving a false travel echo')
                restored(row)
            finally:
                if unreal.SystemLibrary.is_valid(wall):
                    wall.destroy_actor()
            yield .25
            yield from fresh_move(row)
            save()

        if selected('empty_W'):
            row, targets = yield from fresh('empty_W')
            before = rig['pawn']().get_actor_location()
            rig['aim'](targets[0])
            rig['key']('W')
            yield .35
            check(not rig['skills']().is_casting() and rig['dist'](before, rig['pawn']().get_actor_location()) < 2 and
                  all(rig['health'](d) == 100 for d in targets), 'W remains empty after the old entry is removed')
            restored(row)
            save()

        if selected('switch_cleanup'):
            for key in ('E', 'R', 'A', 'S', 'D', 'V', 'F', 'Space'):
                row, targets = yield from fresh('switch_' + key)
                began = yield from cast(key, (450, 0))
                yield from until(began, DEFINITIONS[key]['commit'] + .10 if key in DEFINITIONS else .08)
                owned = [a for name in VISUAL_CLASSES for a in actors(name)] + list(residue())
                check(bool(owned), key + ' has a live visual before owner switch')
                old_pawn = rig['pawn']()
                hp = [rig['health'](d) for d in targets]
                rig['switch']('sparrow')
                yield .35
                check(not unreal.SystemLibrary.is_valid(old_pawn) and not any(unreal.SystemLibrary.is_valid(a) for a in owned),
                      key + ' owner switch removes its live visuals')
                check(not any(actors(name) for name in VISUAL_CLASSES) and not residue(), key + ' leaves no reforge actor after switch')
                yield .45
                check([rig['health'](d) for d in targets] == hp, key + ' owner cleanup cancels remaining damage pulses')
                check(not rig['pawn']().is_combat_busy(), key + ' switch leaves the next character unlocked')
                save()
        report['passed'] = True
        save()
    finally:
        rig['finish_video_clip']()
        cmd('Countess.Skills.IgnoreCooldowns 1')
