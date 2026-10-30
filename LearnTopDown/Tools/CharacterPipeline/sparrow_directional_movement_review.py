"""Diagnose directional movement with the current DLL and existing PIE commands.

Default: eight world directions, tap/hold, idle/skill-chain/V-form (48 cases).
SPARROW_DIRECTION_GROUPS selects comma-separated idle_tap,idle_hold,mixed_tap,
mixed_hold,form_tap,form_hold. SPARROW_DIRECTION_KEYS defaults Q,W,E,R,A,S,D,F;
the two input modes rotate this sequence to avoid tying one skill to one axis.
SPARROW_DIRECTION_CHARACTER=countess with SPARROW_DIRECTION_ANGLES=0 and idle
groups permits a small shared-controller regression. AIM_DISTANCE selects where
skills are aimed; it defaults to 950cm independently of movement destinations.
No native combat state is forcibly unlocked. Only PIE fixture transforms reset.
"""
import json
import math
import os

import unreal


def sequence(rig):
    out, cmd = rig['OUT'], rig['cmd']
    frame = 1.0 / rig['FPS']
    groups = os.environ.get('SPARROW_DIRECTION_GROUPS',
        'idle_tap,idle_hold,mixed_tap,mixed_hold,form_tap,form_hold').split(',')
    keys = os.environ.get('SPARROW_DIRECTION_KEYS', 'Q,W,E,R,A,S,D,F').split(',')
    character = os.environ.get('SPARROW_DIRECTION_CHARACTER', 'sparrow')
    angles = [float(value) for value in os.environ.get('SPARROW_DIRECTION_ANGLES',
        '0,45,90,135,180,225,270,315').split(',')]
    distance = float(os.environ.get('SPARROW_DIRECTION_DISTANCE', '420'))
    aim_distance = float(os.environ.get('SPARROW_DIRECTION_AIM_DISTANCE', '950'))
    duration = float(os.environ.get('SPARROW_DIRECTION_SECONDS', '2.4'))
    original_origin = rig['STATE']['origin']
    minimum_travel = float(os.environ.get('SPARROW_DIRECTION_MIN_TRAVEL', '0'))
    report = {'passed': False, 'fps': rig['FPS'], 'distance_cm': distance,
              'groups': groups, 'character': character, 'angles': angles, 'aim_distance': aim_distance,
              'skill_sequence': keys, 'cases': [],
              'scope': '8 world directions; real cursor ray, nav projection, complete path, movement and heading'}

    def save():
        (out / 'sparrow-directional-movement.json').write_text(
            json.dumps(report, indent=2), encoding='utf-8')

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def vector(point):
        return unreal.Vector(point['x'], point['y'], point['z'])

    def mouse(action, point):
        cmd(f'CountessComboQA.Mouse {action} Right {point.x} {point.y} {point.z}')

    def ground_probe(point):
        cmd(f'SparrowQA.Ground directional-ground {point.x} {point.y} {rig["STATE"]["origin"].z}')
        return json.loads((out / 'directional-ground.json').read_text(encoding='utf-8-sig'))

    def state():
        pawn = rig['pawn']()
        move = pawn.get_editor_property('character_movement')
        anim = pawn.get_editor_property('mesh').get_anim_instance()
        montage = anim.get_current_active_montage()
        return {'time': now(), 'position': rig['vec'](pawn.get_actor_location()),
                'velocity': rig['vec'](pawn.get_velocity()), 'yaw': pawn.get_actor_rotation().yaw,
                'busy': pawn.is_combat_busy(), 'casting': rig['skills']().is_casting(),
                'attacking': pawn.is_attacking(), 'root_mode': str(anim.get_editor_property('root_motion_mode')),
                'orient': move.get_editor_property('orient_rotation_to_movement'),
                'move_mode': str(move.get_editor_property('movement_mode')),
                'montage': montage.get_name() if montage else None,
                'form_remaining': rig['skills']().get_ascension_remaining() if character == 'sparrow' else 0}

    def native_state():
        cmd('CountessInputQA.State directional-native')
        return json.loads((out / 'directional-native.json').read_text(encoding='utf-8-sig'))

    def path_to(goal, from_feet=None):
        pawn = rig['pawn']()
        radius = pawn.get_editor_property('capsule_component').get_scaled_capsule_half_height()
        feet = from_feet if from_feet is not None else pawn.get_actor_location() - unreal.Vector(0, 0, radius)
        path = unreal.NavigationSystemV1.find_path_to_location_synchronously(rig['world'](), feet, goal)
        points = list(path.get_editor_property('path_points')) if path else []
        length = sum(rig['dist'](a, b) for a, b in zip(points, points[1:]))
        return {'valid': bool(path and path.is_valid()), 'partial': bool(path and path.is_partial()),
                'points': [rig['vec'](point) for point in points], 'length': length}

    def nearby_collision():
        pawn = rig['pawn']()
        here = pawn.get_actor_location()
        rows = []
        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.Actor):
            for part in actor.get_components_by_class(unreal.PrimitiveComponent):
                collision = part.get_collision_enabled()
                nav = part.get_editor_property('can_ever_affect_navigation')
                if nav or collision != unreal.CollisionEnabled.NO_COLLISION:
                    center, extent, sphere = unreal.SystemLibrary.get_component_bounds(part)
                    if math.hypot(max(abs(center.x - here.x) - extent.x, 0),
                                  max(abs(center.y - here.y) - extent.y, 0)) > 1000:
                        continue
                    rows.append({'actor': actor.get_name(), 'class': actor.get_class().get_name(),
                                 'actor_location': rig['vec'](actor.get_actor_location()),
                                 'actor_tags': [str(tag) for tag in actor.tags],
                                 'component': part.get_name(), 'collision': str(collision), 'navigation': nav,
                                 'bounds_center': rig['vec'](center), 'bounds_extent': rig['vec'](extent),
                                 'bounds_sphere': sphere})
        return rows

    def select_clear_origin():
        # This is only for an explicitly requested fixture. It never edits the map
        # or disables collision/navigation to manufacture a passing movement path.
        candidates = []
        origin_ground = ground_probe(original_origin)
        height = original_origin.z - origin_ground['ground']['z']
        for dx, dy in ((0, 0), (-500, 0), (0, -500), (-500, -500), (-900, 0), (0, -900)):
            point = original_origin + unreal.Vector(dx, dy, 0)
            start_probe = ground_probe(point)
            valid = start_probe['ground_hit'] and start_probe['navigation_projected']
            details = {'offset': [dx, dy], 'start': start_probe, 'goals': []}
            if valid:
                valid = rig['dist'](vector(start_probe['ground']), vector(start_probe['nav'])) < 5
            for angle in angles if valid else []:
                yaw = math.radians(angle)
                goal_probe = ground_probe(point + unreal.Vector(math.cos(yaw) * distance, math.sin(yaw) * distance, 0))
                goal_valid = goal_probe['ground_hit'] and goal_probe['navigation_projected']
                route = path_to(vector(goal_probe['nav']), vector(start_probe['nav'])) if goal_valid else None
                details['goals'].append({'angle': angle, 'probe': goal_probe, 'path': route})
                valid &= bool(goal_valid and rig['dist'](vector(goal_probe['ground']), vector(goal_probe['nav'])) < 5 and
                              route['valid'] and not route['partial'] and route['length'] <= distance + 5)
            details['valid'] = valid
            candidates.append(details)
            if valid:
                ground = vector(start_probe['ground'])
                rig['STATE']['origin'] = ground + unreal.Vector(0, 0, height)
                report.setdefault('clear_origin_selections', []).append(candidates)
                return
        report.setdefault('clear_origin_selections', []).append(candidates)
        save()
        raise AssertionError('No unchanged-map fixture has the requested clear navigation segment')

    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    cmd('Character.Input.TraceMove 1')
    try:
        if character not in ('sparrow', 'countess') or (character == 'countess' and any(
                not group.startswith('idle_') for group in groups)):
            raise ValueError('Countess shared-controller regression uses idle groups only')
        for group in groups:
            mode = group.rsplit('_', 1)[-1]
            if group not in ('idle_tap', 'idle_hold', 'mixed_tap', 'mixed_hold', 'form_tap', 'form_hold'):
                raise ValueError('Unknown directional group ' + group)
            cmd('CountessComboQA.FlushInput')
            rig['switch']('countess' if character == 'sparrow' else 'sparrow'); yield .2
            rig['switch'](character); yield .7
            rig['layout']([(1200, 0), (1200, 600), (1200, -600)])
            yield .2
            if os.environ.get('SPARROW_DIRECTION_FIND_CLEAR_START') == '1':
                select_clear_origin()
                rig['layout']([(1200, 0), (1200, 600), (1200, -600)])
                yield .2
            if group.startswith('form'):
                rig['use']('V', offset=(950, 0)); yield 1.65
            for index, angle in enumerate(angles):
                name = group + '_' + str(int(angle)).zfill(3)
                rig['case']('Direction_' + name)
                cmd('CountessComboQA.FlushInput')
                # Keep the same owner/effect lifetime across the skill chain.
                # Repositioning is confined to the test fixture, not combat state.
                rig['layout']([(1200, 0), (1200, 600), (1200, -600)])
                yield .15
                start = rig['pawn']().get_actor_location()
                yaw = math.radians(angle)
                proposed = unreal.Vector(start.x + math.cos(yaw) * distance,
                                         start.y + math.sin(yaw) * distance, start.z)
                row = {'name': name, 'group': group, 'direction_degrees': angle,
                       'input': mode, 'initial': state(), 'samples': [], 'issues': []}
                report['cases'].append(row)
                before = ground_probe(proposed)
                row['ground_before'] = before
                if not before['ground_hit'] or not before['navigation_projected']:
                    row['issues'].append('fixture_ground_or_nav_unavailable')
                    save()
                    continue
                goal = vector(before['ground'])
                row['ground_navigation_offset'] = rig['dist'](goal, vector(before['nav']))
                if row['ground_navigation_offset'] >= 5:
                    row['issues'].append('fixture_ground_goal_shifted_by_navigation')
                row['path_before_skill'] = path_to(vector(before['nav']))
                if index == 0:
                    row['nearby_at_input'] = nearby_collision()
                    row['navigation_data'] = [{'name': actor.get_name(),
                        'runtime_generation': str(actor.get_editor_property('runtime_generation'))}
                        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.RecastNavMesh)]
                if not group.startswith('idle'):
                    skill = keys[(index + (3 if mode == 'hold' else 0)) % len(keys)]
                    row['skill'] = skill
                    rig['use'](skill, offset=(aim_distance, 0))
                    yield .12
                    row['during_skill'] = state()
                    if not row['during_skill']['busy']:
                        row['issues'].append('skill_not_active_at_move_input')
                mouse('Move', goal)
                selected = ground_probe(goal)
                row['ground_at_input'] = selected
                row['input_state'] = native_state()
                row['path_at_input'] = path_to(vector(selected['cursor_nav'])) if selected['cursor_navigation_projected'] else None
                requested_screen, cursor = selected['requested_screen'], selected['cursor_screen']
                screen_ok = requested_screen['valid'] and cursor['valid'] and max(
                    abs(requested_screen[axis] - cursor[axis]) for axis in ('x', 'y')) <= 1.001
                row['cursor_screen_matches'] = screen_ok
                if not screen_ok:
                    row['issues'].append('fixture_cursor_screen_mismatch')
                if not selected['cursor_navigation_projected']:
                    row['issues'].append('cursor_hit_has_no_nav_projection')
                elif not row['path_at_input']['valid'] or row['path_at_input']['partial']:
                    row['issues'].append('cursor_goal_has_no_complete_path')
                selected_goal = vector(selected['cursor_nav']) if selected['cursor_navigation_projected'] else goal
                row['selected_goal'] = rig['vec'](selected_goal)
                row['selected_goal_error'] = rig['dist'](selected_goal, vector(before['nav']))
                # A selected obstacle/FX is evidence, not automatically a fixture failure.
                row['cursor_ground_actor_matches'] = selected['cursor_visibility_hit']['actor'] == before['ground_actor']
                mouse('Press', goal)
                input_time = now()
                row['input_time'] = input_time
                released = False
                first_move = None
                while now() - input_time < duration:
                    elapsed = now() - input_time
                    if mode == 'hold':
                        mouse('Move', goal)
                    elif not released and elapsed >= frame - 1e-5:
                        mouse('Release', goal)
                        released = True
                        # A short click must preserve its destination after pointer movement.
                        opposite = unreal.Vector(start.x - math.cos(yaw) * distance,
                                                 start.y - math.sin(yaw) * distance, goal.z)
                        mouse('Move', opposite)
                    sample = state()
                    sample['elapsed'] = elapsed
                    row['samples'].append(sample)
                    if first_move is None and rig['dist'](start, rig['pawn']().get_actor_location()) > 1:
                        first_move = elapsed
                    yield frame
                if not released:
                    mouse('Release', goal)
                row['first_move'] = first_move
                row['after'] = state()
                row['native_after'] = native_state()
                end = rig['pawn']().get_actor_location()
                row['travel'] = rig['dist'](start, end)
                row['distance_to_selected_goal'] = rig['dist'](selected_goal, end)
                row['requested_heading_error'] = abs((row['after']['yaw'] - angle + 180) % 360 - 180)
                points = row['path_at_input']['points'] if row['path_at_input'] else []
                path_angle = math.degrees(math.atan2(points[-1][1] - points[-2][1],
                    points[-1][0] - points[-2][0])) if len(points) >= 2 else angle
                row['final_path_heading'] = path_angle
                row['heading_error'] = abs((row['after']['yaw'] - path_angle + 180) % 360 - 180)
                row['max_lateral_distance'] = max(abs((sample['position'][0] - start.x) * -math.sin(yaw) +
                    (sample['position'][1] - start.y) * math.cos(yaw)) for sample in row['samples'])
                if row['distance_to_selected_goal'] > 40:
                    row['issues'].append('did_not_reach_selected_goal')
                if row['travel'] < minimum_travel:
                    row['issues'].append('did_not_travel_required_fixture_distance')
                if row['after']['busy'] or row['after']['casting']:
                    row['issues'].append('combat_state_not_recovered')
                if any(row['initial'][field] != row['after'][field] for field in ('root_mode', 'orient', 'move_mode')):
                    row['issues'].append('movement_settings_not_restored')
                if row['travel'] > 100 and row['heading_error'] > 25:
                    row['issues'].append('ending_heading_differs_from_final_path_segment')
                if row['issues']:
                    row['nearby_collision'] = nearby_collision()
                    rig['capture']('direction_issue_' + name)
                save()
        report['issues'] = [{'name': row['name'], 'issues': row['issues']} for row in report['cases'] if row['issues']]
        report['passed'] = not report['issues']
        report['finished_all_cases'] = True
        save()
    finally:
        cmd('CountessComboQA.FlushInput')
        cmd('Character.Input.TraceMove 0')
        rig['STATE']['origin'] = original_origin
        save()
