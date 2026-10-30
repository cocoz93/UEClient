"""Focused actual-input checks for reforge dynamic sight and V -> Space handoff.

Use new_skills_probe with NEW_SKILLS_FOCUS=sparrow_feedback,
SPARROW_FEEDBACK_PARTS=, SPARROW_FEEDBACK_STUDIES=countess_reforge_boundary_review.py.
COUNTESS_REFORGE_BOUNDARIES optionally filters E_wall,R_wall,A_wall,D_wall,V_wall,
V_pending_space,V_pending_switch. No gameplay/asset edits, direct damage or video.
Walls are temporary WorldDynamic fixtures; Visibility Ignore is the positive control.
"""
import json
import math
import os

import unreal


def sequence(rig):
    out, check, cmd = rig['OUT'], rig['check'], rig['cmd']
    allowed = {'E_wall', 'R_wall', 'A_wall', 'D_wall', 'V_wall', 'V_pending_space', 'V_pending_switch'}
    selected = {x.strip() for x in os.environ.get('COUNTESS_REFORGE_BOUNDARIES', ','.join(sorted(allowed))).split(',') if x.strip()}
    check(selected and selected <= allowed, 'valid Countess boundary filter')
    frame = 1. / rig['FPS']
    report = {'passed': False, 'fps': rig['FPS'], 'cases': [], 'assets_saved': False,
              'input_clock': 'queued real key then next input tick; handoff tolerance 3 frames'}
    walls = []

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def save():
        (out / 'countess-reforge-boundary-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def enum_member(type_names, suffix):
        normalized = ''.join(c for c in suffix.upper() if c.isalnum())
        diagnostics = report.setdefault('enum_resolution', {})
        for type_name in type_names:
            kind = getattr(unreal, type_name, None)
            if kind is None:
                diagnostics[type_name] = {'missing': True}
                continue
            names = [n for n in dir(kind) if not n.startswith('_')]
            matches = [n for n in names if ''.join(c for c in n.upper() if c.isalnum()).endswith(normalized)]
            diagnostics[type_name + '.' + suffix] = {'names': names, 'matches': matches}
            if len(matches) == 1:
                save()
                return getattr(kind, matches[0])
        save()
        raise RuntimeError('Cannot resolve enum ' + repr(type_names) + '.' + suffix + ': ' + repr(diagnostics))

    world_dynamic = enum_member(('CollisionChannel',), 'WORLDDYNAMIC')
    visibility = enum_member(('CollisionChannel',), 'VISIBILITY')
    block = enum_member(('CollisionResponseType', 'CollisionResponse'), 'BLOCK')
    ignore = enum_member(('CollisionResponseType', 'CollisionResponse'), 'IGNORE')

    def fields():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.CountessInfernoVisual)
                if unreal.SystemLibrary.is_valid(a)]

    def xy_distance(a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def body_state():
        pawn = rig['pawn']()
        mesh = pawn.get_editor_property('mesh')
        movement = pawn.get_editor_property('character_movement')
        return {'relative': rig['vec'](mesh.get_editor_property('relative_location')),
                'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
                'visible': mesh.is_visible(), 'orient': movement.get_editor_property('orient_rotation_to_movement'),
                'movement': str(movement.get_editor_property('movement_mode')),
                'root_motion': str(mesh.get_anim_instance().get_editor_property('root_motion_mode'))}

    def sample(row, label, targets):
        p, skills = rig['pawn'](), rig['skills']()
        data = {'label': label, 'time': now(), 'location': rig['vec'](p.get_actor_location()),
                'health': [rig['health'](d) for d in targets], 'active': skills.get_active_skill_number(),
                'casting': skills.is_casting(), 'busy': p.is_combat_busy(), 'feedback': skills.get_input_feedback(),
                'body': body_state(), 'fields': [{'name': a.get_name(), 'age': a.get_visual_age(),
                    'center': rig['vec'](a.get_field_center())} for a in fields()]}
        row['samples'].append(data)
        save()
        return data

    def until(start, elapsed):
        delay = elapsed - (now() - start)
        if delay > .0001:
            yield delay

    def fresh(name, target=(350, 0)):
        rig['switch']('sparrow')
        yield .20
        rig['switch']('countess')
        yield .65
        cmd('CountessComboQA.FlushInput')
        rig['case']('Countess_boundary_' + name)
        targets = rig['layout']([target, (650, 450), (650, -450)])
        yield .20
        row = {'case': name, 'samples': []}
        report['cases'].append(row)
        initial = sample(row, 'initial', targets)
        row['initial_body'] = initial['body']
        save()
        return row, targets

    def cast(key, offset=(180, 0), active=None):
        # A visible point before the wall preserves +X direction for damage checks.
        rig['aim'](offset=offset)
        queued = now()
        rig['key']('SpaceBar' if key == 'Space' else key)
        yield frame
        if active is not None:
            check(rig['skills']().get_active_skill_number() == active, key + ' selects its expected actual slot')
        return queued

    def recovered(row, targets):
        data = sample(row, 'recovered', targets)
        check(data['active'] == 0 and not data['casting'] and not data['busy'], row['case'] + ' recovers input state')
        check(data['body'] == row['initial_body'], row['case'] + ' restores mesh, materials and movement settings')

    def dynamic_wall(row):
        actor = rig['wall_fixture'](250)
        walls.append(actor)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        component.set_collision_object_type(world_dynamic)
        row['wall'] = {'name': actor.get_name(), 'object_type': str(component.get_collision_object_type()),
                       'visibility': str(component.get_collision_response_to_channel(visibility))}
        save()
        check(component.get_collision_object_type() == world_dynamic and
              component.get_collision_response_to_channel(visibility) == block,
              'fixture is a WorldDynamic object that blocks Visibility')
        return actor, component

    cmd('Countess.Skills.IgnoreCooldowns 1')
    save()
    try:
        if 'E_wall' in selected:
            row, targets = yield from fresh('E_wall', (450, 0))
            wall, component = dynamic_wall(row)
            try:
                yield frame
                cmd('Countess.Skills.IgnoreCooldowns 0')
                # A camera ray can legitimately select the near face of this wall.
                # Test the exact behind-wall point through the public skill entry,
                # then use real keyboard input for the unobstructed positive case.
                point = rig['ground'](rig['STATE']['origin'].x + 450, rig['STATE']['origin'].y)
                accepted = rig['skills']().try_use_skill_slot(2, point, None)
                row['blocked_input'] = 'public TryUseSkillSlot with exact behind-wall ground'
                check(not accepted, 'E public skill entry rejects an explicit ground point behind a dynamic wall')
                yield .15
                data = sample(row, 'blocked', targets)
                check(not data['casting'] and data['active'] == 0 and data['feedback'] == 'No clear ground',
                      'E rejects ground behind a dynamic Visibility wall')
                check(all(h == 100 for h in data['health']), 'rejected E deals no damage')
                component.set_collision_response_to_channel(visibility, ignore)
                started = yield from cast('E', (450, 0), 3)
                yield from until(started, 1.80)
                data = sample(row, 'visibility_ignore_control', targets)
                check(abs(data['health'][0] - 45) < .05 and data['health'][1:] == [100., 100.],
                      'E rejection consumes no cooldown; Visibility Ignore permits normal55 damage')
                recovered(row, targets)
            finally:
                cmd('Countess.Skills.IgnoreCooldowns 1')
                wall.destroy_actor()

        for key, active, duration, maximum in [('R', 4, 2.1, 90), ('A', 9, 2.75, 60),
                                               ('D', 11, 1.35, 54), ('V', 17, 4.2, 84)]:
            if key + '_wall' not in selected:
                continue
            row, targets = yield from fresh(key + '_wall')
            wall, component = dynamic_wall(row)
            try:
                yield frame
                started = yield from cast(key, active=active)
                yield from until(started, duration)
                data = sample(row, 'visibility_block', targets)
                check(data['health'] == [100., 100., 100.], key + ' does not damage across a dynamic Visibility wall')
                recovered(row, targets)
                component.set_collision_response_to_channel(visibility, ignore)
                started = yield from cast(key, active=active)
                yield from until(started, duration)
                data = sample(row, 'visibility_ignore_control', targets)
                dealt = 100 - data['health'][0]
                check(0 < dealt <= maximum + .05 and data['health'][1:] == [100., 100.],
                      key + ' positive control proves the same target is reachable when Visibility ignores the wall')
                recovered(row, targets)
            finally:
                wall.destroy_actor()

        for name in ('V_pending_space', 'V_pending_switch'):
            if name not in selected:
                continue
            row, targets = yield from fresh(name, (120, 0))
            origin = rig['pawn']().get_actor_location()
            started = yield from cast('V', active=17)
            row['queued_at'] = started
            yield from until(started, .20)
            data = sample(row, 'before_space', targets)
            check(data['active'] == 17 and not data['fields'], 'V is still uncommitted when Space is requested')
            row['space_at'] = yield from cast('Space', active=18)
            sample(row, 'space_started', targets)
            if name == 'V_pending_switch':
                old = rig['pawn']()
                rig['switch']('sparrow')
                yield .70
                check(not unreal.SystemLibrary.is_valid(old) and not fields(), 'switching owner cancels the uncommitted V handoff timer')
                yield 3.5
                row['health_after_switch'] = [rig['health'](d) for d in targets]
                save()
                check(row['health_after_switch'] == [100., 100., 100.] and not fields(), 'cancelled handoff leaves no later storm or damage')
                continue

            seen = set()
            first_at = None
            row['handoff_monitor'] = {'samples': 0, 'max_fields': 0, 'max_origin_drift_cm': 0.}
            while now() - started < 4.20:
                live = fields()
                monitor = row['handoff_monitor']
                monitor['samples'] += 1
                monitor['max_fields'] = max(monitor['max_fields'], len(live))
                if len(live) > 1:
                    sample(row, 'duplicate_storm_failure', targets)
                    check(False, 'pending V handoff never duplicates its installed storm')
                if live:
                    field = live[0]
                    seen.add(field.get_name())
                    drift = xy_distance(field.get_field_center(), origin)
                    monitor['max_origin_drift_cm'] = max(monitor['max_origin_drift_cm'], drift)
                    if drift >= .5:
                        sample(row, 'storm_origin_failure', targets)
                        check(False, 'handoff field remains at the original cast position')
                    if first_at is None:
                        first_at = now() - started
                        row['field_first_seen'] = first_at
                        sample(row, 'storm_born', targets)
                        check(.40 - frame <= first_at <= .40 + 3 * frame + .001,
                              'V releases at its original commitment time after Space, within input/tick quantization')
                yield frame
            data = sample(row, 'storm_finished', targets)
            row['unique_fields'] = sorted(seen)
            row['travel'] = xy_distance(rig['pawn']().get_actor_location(), origin)
            save()
            check(len(seen) == 1 and first_at is not None and not fields(), 'one handoff storm appears then expires')
            check(row['handoff_monitor']['max_fields'] == 1 and row['handoff_monitor']['max_origin_drift_cm'] < .5,
                  'every sampled frame preserves one fixed-origin storm without duplication')
            check(205 < row['travel'] < 235, 'Space completes its220cm backstep during the pending V handoff')
            check(abs(data['health'][0] - 16.) < .05 and data['health'][1:] == [100., 100.],
                  'handoff preserves all12 storm pulses for84 total damage')
            recovered(row, targets)
            rig['capture']('Countess_boundary_V_pending_space_recovered')
        check(bool(report['cases']), 'Countess boundary filter executed at least one case')
        report['passed'] = True
        save()
    finally:
        cmd('Countess.Skills.IgnoreCooldowns 0')
        for actor in walls:
            if unreal.SystemLibrary.is_valid(actor):
                actor.destroy_actor()
        save()
