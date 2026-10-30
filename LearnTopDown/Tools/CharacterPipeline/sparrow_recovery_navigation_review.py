"""Read-only NoPath evidence around F recovery, reusing the real input reviewer.

Four sequences compare V3/V0 and F alone/W then F. The existing W->F sequence
switches pawn between casts, matching the failing recovery60 fixture exactly.
Failed gameplay checks are retained, but do not stop the other diagnostic cases.
SPARROW_NAV_RUNS=V3_F_only selects the first run for a clean-process A/B check.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy

import unreal


def sequence(rig):
    out, cmd = rig['OUT'], rig['cmd']
    helper = Path(__file__).with_name('sparrow_recovery_timing.py')
    report = {'completed': False, 'passed': False, 'fps': rig['FPS'], 'runs': [],
              'scope': 'unchanged map/controller; F form NoPath at recovery, V3/V0, with/without preceding W'}
    old_v = unreal.SystemLibrary.get_console_variable_int_value('Sparrow.FlameStudy.V')
    selected_runs = {name for name in os.environ.get('SPARROW_NAV_RUNS', '').split(',') if name}
    known_runs = {'V3_F_only', 'V3_W_then_F', 'V0_F_only', 'V0_W_then_F'}
    if not selected_runs.issubset(known_runs): raise ValueError('Unknown SPARROW_NAV_RUNS selection')

    def save():
        (out / 'sparrow-recovery-navigation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    @contextmanager
    def environment(values):
        previous = {key: os.environ.get(key) for key in values}
        os.environ.update(values)
        try:
            yield
        finally:
            for key, value in previous.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value

    def ground(point, label):
        cmd(f'SparrowQA.Ground {label} {point.x} {point.y} {point.z}')
        return json.loads((out / (label + '.json')).read_text(encoding='utf-8-sig'))

    def vector(point):
        return unreal.Vector(point['x'], point['y'], point['z'])

    def path_info(start, goal, context):
        path = unreal.NavigationSystemV1.find_path_to_location_synchronously(rig['world'](), start, goal, context)
        points = list(path.get_editor_property('path_points')) if path else []
        return {'valid': bool(path and path.is_valid()), 'partial': bool(path and path.is_partial()),
                'points': [rig['vec'](point) for point in points],
                'length': sum(rig['dist'](a, b) for a, b in zip(points, points[1:]))}

    def inventory(start, goal):
        relevant, visuals = [], []
        for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.Actor):
            if not unreal.SystemLibrary.is_valid(actor): continue
            skill = actor.get_class().get_name() in ('SparrowGatherShot', 'SparrowFlameStudies', 'SparrowAscensionWings', 'SparrowArrow')
            parts = actor.get_components_by_class(unreal.PrimitiveComponent)
            if skill:
                visuals.append({'actor': actor.get_name(), 'class': actor.get_class().get_name(),
                                'components': len(parts),
                                'navigation_enabled': [part.get_name() for part in parts if part.get_editor_property('can_ever_affect_navigation')],
                                'collision_enabled': [part.get_name() for part in parts if part.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION]})
            for part in parts:
                nav = part.get_editor_property('can_ever_affect_navigation')
                collision = part.get_collision_enabled()
                if not nav and collision == unreal.CollisionEnabled.NO_COLLISION: continue
                center, extent, sphere = unreal.SystemLibrary.get_component_bounds(part)
                low_x, high_x = min(start.x, goal.x) - 180, max(start.x, goal.x) + 180
                low_y, high_y = min(start.y, goal.y) - 180, max(start.y, goal.y) + 180
                if center.x + extent.x < low_x or center.x - extent.x > high_x: continue
                if center.y + extent.y < low_y or center.y - extent.y > high_y: continue
                relevant.append({'actor': actor.get_name(), 'class': actor.get_class().get_name(),
                                 'actor_location': rig['vec'](actor.get_actor_location()),
                                 'component': part.get_name(), 'navigation': nav, 'collision': str(collision),
                                 'center': rig['vec'](center), 'extent': rig['vec'](extent), 'sphere': sphere})
        return {'nearby_components': relevant, 'skill_components': visuals}

    try:
        for variant, keys in ((3, 'F'), (3, 'W,F'), (0, 'F'), (0, 'W,F')):
            name = 'V' + str(variant) + ('_F_only' if keys == 'F' else '_W_then_F')
            if selected_runs and name not in selected_runs: continue
            run = {'name': name, 'V_style': variant, 'keys': keys, 'checks_failed': [], 'navigation_samples': []}
            report['runs'].append(run)
            previous_paths = {}

            def probe(key, stage, goal):
                pawn = rig['pawn']()
                location = pawn.get_actor_location()
                half_height = pawn.get_editor_property('capsule_component').get_scaled_capsule_half_height()
                feet = location - unreal.Vector(0, 0, half_height)
                start = ground(location, 'recovery-nav-start')
                destination = ground(goal, 'recovery-nav-goal')
                selected = vector(destination['cursor_nav']) if destination.get('cursor_navigation_projected') else None
                projected_goal = vector(destination['nav']) if destination['navigation_projected'] else goal
                controller = unreal.GameplayStatics.get_player_controller(rig['world'](), 0)
                native = path_info(feet, projected_goal, controller)
                pawn_path = path_info(feet, projected_goal, pawn)
                row = {'key': key, 'stage': stage, 'time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                       'pawn': pawn.get_name(), 'position': rig['vec'](location), 'feet': rig['vec'](feet),
                       'busy': pawn.is_combat_busy(), 'casting': rig['skills']().is_casting(),
                       'navigation_building': unreal.NavigationSystemV1.is_navigation_being_built(rig['world']()),
                       'start_probe': start, 'goal_probe': destination,
                       'controller_context_path': native, 'pawn_context_path': pawn_path,
                       'cursor_path': path_info(feet, selected, controller) if selected is not None else None}
                if start['navigation_projected']:
                    row['projected_start_path'] = path_info(vector(start['nav']), projected_goal, controller)
                    row['start_projection_distance'] = rig['dist'](vector(start['ground']), vector(start['nav']))
                signature = (native['valid'], native['partial'], pawn_path['valid'], pawn_path['partial'])
                if stage in ('before_form', 'before_cast', 'cast_560') or previous_paths.get(key) != signature:
                    row.update(inventory(location, goal))
                previous_paths[key] = signature
                run['navigation_samples'].append(row)
                return row

            def diagnostic_check(condition, label):
                if not condition:
                    run['checks_failed'].append({'case': rig['STATE']['case'], 'label': label})
                else:
                    rig['check'](condition, label)

            wrapped = dict(rig)
            wrapped['check'] = diagnostic_check
            wrapped['recovery_navigation_probe'] = probe
            cmd('Sparrow.FlameStudy.V ' + str(variant))
            with environment({'SPARROW_RECOVERY_KEYS': keys, 'SPARROW_RECOVERY_FORM': '1'}):
                yield from runpy.run_path(str(helper))['sequence'](wrapped)
            timing = json.loads((out / 'sparrow-recovery-timing.json').read_text(encoding='utf-8-sig'))
            timing['passed'] = not run['checks_failed']
            (out / ('recovery-nav-' + name + '.json')).write_text(json.dumps(timing, indent=2), encoding='utf-8')
            run['cases'] = [{key: case.get(key) for key in ('key', 'started_at', 'first_move_at', 'last_shot_to_move', 'damage', 'native_path_trace')}
                            for case in timing['cases']]
            run['passed'] = not run['checks_failed']
            save()
        report['completed'] = True
        report['passed'] = all(run['passed'] for run in report['runs'])
    finally:
        cmd('Sparrow.FlameStudy.V ' + str(old_v))
        cmd('CountessComboQA.FlushInput')
        save()
