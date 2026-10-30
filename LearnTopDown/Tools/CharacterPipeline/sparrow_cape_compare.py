"""Actual training-room cape observations and hash-checked before/after analysis.

Editor mode consumes CHARACTER_PIPELINE_JOB. Ordinary Python uses --review DIR
--fps N after the two independent old/new editor runs have finished.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pulse_values(age, maximum):
    scale = max(0, min(200, maximum)) / 180
    target = (110 + 50 * math.sin(2 * math.pi * .65 * age)
              + 20 * math.sin(2 * math.pi * 1.15 * age + .8)) * scale
    lateral = 1.3 * math.sin(2 * math.pi * .48 * age) + .7 * math.sin(2 * math.pi * .83 * age + .5)
    return target, lateral


def pulse_fit(age, maximum, actual_target, actual_lateral, target_fps):
    # The timer updates at most once in one game frame; its last value can be older than the snapshot.
    lag_limit = .05 + 1 / target_fps + .002
    low, high = max(0, age - lag_limit), max(0, age)
    steps = max(1, math.ceil((high - low) / .001))
    candidates = []
    for index in range(steps + 1):
        time = low + (high - low) * index / steps
        target, lateral = pulse_values(time, maximum)
        target_error, lateral_error = abs(target - actual_target), abs(lateral - actual_lateral)
        candidates.append((max(target_error / .4, lateral_error / .01), time, target_error, lateral_error))
    score, time, target_error, lateral_error = min(candidates)
    return {'matches': score <= 1, 'observation_age_seconds': age,
            'compatible_update_age_seconds': time, 'maximum_permitted_update_lag_seconds': lag_limit,
            'compatible_update_lag_seconds': age - time, 'target_error_cm_per_second': target_error,
            'lateral_error_cm': lateral_error, 'target_tolerance_cm_per_second': .4, 'lateral_tolerance_cm': .01,
            'timestamp_limit': 'A compatible 20Hz update time is inferred inside a one-timer-period plus one-game-frame window; it is not an exact timer-fire or cloth-solver timestamp.'}


def flutter_measurement(samples):
    """Track the same eight initially lowest sampled vertices, retaining body data."""
    from sparrow_stop_diagnostic_review import point_map, stats
    if len(samples) < 3:
        return {'available': False, 'reason': 'Fewer than three complete cloth frames.'}
    maps = [point_map(row.get('cloth_points_component_space')) for row in samples]
    common = set.intersection(*(set(row) for row in maps))
    if len(common) < 8:
        return {'available': False, 'reason': 'Fewer than eight stable sampled particle identities.'}
    keys = sorted(common, key=lambda key: maps[0][key][2])[:8]
    times = [row['time'] for row in samples]
    duration = times[-1] - times[0]
    pelvis = [row['motion']['bones_component_space']['pelvis']['translation'] for row in samples]
    relative = [[[row[key][axis] - body[axis] for axis in range(3)] for key in keys]
                for row, body in zip(maps, pelvis)]
    means = [[sum(row[index][axis] for row in relative) / len(relative) for axis in range(3)]
             for index in range(len(keys))]
    residuals = [math.dist(point, means[index]) for row in relative for index, point in enumerate(row)]
    steps = [math.dist(a[index], b[index]) for a, b in zip(relative, relative[1:]) for index in range(len(keys))]
    speeds = [math.dist(a[index], b[index]) / (tb - ta)
              for a, b, ta, tb in zip(relative, relative[1:], times, times[1:]) for index in range(len(keys))]
    # A short idle sample may contain fewer than two cycles. Preserve that uncertainty.
    z = [sum(point[2] for point in row) / len(keys) for row in relative]
    mean_t = sum(times) / len(times)
    mean_z = sum(z) / len(z)
    denom = sum((t - mean_t) ** 2 for t in times)
    slope = sum((t - mean_t) * (value - mean_z) for t, value in zip(times, z)) / denom if denom else 0
    values = [value - mean_z - slope * (t - mean_t) for t, value in zip(times, z)]
    candidates = []
    for step in range(8, 81):
        frequency = step * .05
        phase = [2 * math.pi * frequency * (t - times[0]) for t in times]
        cosine = sum(v * math.cos(p) for v, p in zip(values, phase)) * 2 / len(values)
        sine = sum(v * math.sin(p) for v, p in zip(values, phase)) * 2 / len(values)
        candidates.append((math.hypot(cosine, sine), frequency))
    amplitude, frequency = max(candidates)
    cycles = duration * frequency
    return {'available': True, 'window_seconds': [times[0], times[-1]], 'duration_seconds': duration,
            'samples': len(samples), 'particle_identities': [list(key) for key in keys],
            'selection': 'Eight lowest Z vertices in the first frame of the fixed 32-vertex sample.',
            'pelvis_relative_position_residual_cm': stats(residuals),
            'pelvis_relative_frame_step_cm': stats(steps),
            'pelvis_relative_speed_cm_per_second': stats(speeds),
            'pelvis_component_span_cm': max(math.dist(pelvis[0], p) for p in pelvis),
            'period_estimate': {'method': 'Detrended lower-hem mean-Z sinusoid projection; 0.4–4 Hz in 0.05 Hz bins.',
                                'strongest_candidate_seconds': 1 / frequency,
                                'candidate_amplitude_cm': amplitude, 'observed_candidate_cycles': cycles,
                                'at_least_two_cycles_observed': cycles >= 2,
                                'confirmed_physical_period': False,
                                'limit': 'Short windows and animation motion can create apparent periods; this is an observation, not a solver frequency or wind phase.'}}


def review(directory, target_fps, new_only=False, old_run=None):
    from sparrow_stop_diagnostic_review import edges, summarize_edges, summarize_leg, stats, point_map
    directory = Path(directory).resolve()
    runs = {}
    for mode in (('new',) if new_only else ('old', 'new')):
        root = Path(old_run).resolve() if mode == 'old' and old_run else directory / mode
        path = root / f'sparrow-cape-{target_fps}.json'
        report = load(path)
        assert report['passed'] and report['protected_files_match'], str(path)
        assert load(root / 'launch-result.json')['passed'], str(root)
        assert report['cape_variant'] == (0 if mode == 'old' else 1)
        cases = {}
        for case in report['cases']:
            descriptor = case['data']['full_simulation_trace']
            trace_path = Path(descriptor['path'])
            assert digest(trace_path) == descriptor['sha256']
            trace = load(trace_path)
            assert trace['fps'] == target_fps and len(trace['samples']) == descriptor['samples']
            rows = [row for row in trace['samples'] if row.get('pawn_class') == 'BP_SparrowCharacter_C']
            edge_rows = edges(rows)
            # Do not compare an old pawn's last frame with a newly spawned pawn.
            owner_changes = {a['time'] for a, b in zip(rows, rows[1:]) if a['pawn'] != b['pawn']}
            edge_rows = [edge for edge in edge_rows if edge['start'] not in owner_changes]
            bounds = [cloth for row in rows for cloth in row['cloth']]
            windows = []
            for window in case['data'].get('observation_windows', []):
                chosen = [row for row in rows if window['start'] - 1e-6 <= row['time'] <= window['end'] + 1e-6]
                windows.append(dict(window, flutter=flutter_measurement(chosen)))
            legs = case['data'].get('legs', [])
            if case['data'].get('held_input'):
                legs = legs + [dict(case['data']['held_input'], label='held-input-release')]
            stops = [summarize_leg(leg, rows, edge_rows, target_fps,
                                  legs[index + 1]['started'] if index + 1 < len(legs) else None)
                     for index, leg in enumerate(legs)]
            fraction_above = []
            for row in rows:
                points = point_map(row.get('cloth_points_component_space'))
                head = row['motion']['bones_component_space']['head']['translation'][2]
                if points:
                    fraction_above.append(sum(p[2] > head for p in points.values()) / len(points))
            cases[case['name']] = {'source_trace': descriptor, 'archer_frames': len(rows),
                'world_time_interval': [rows[0]['time'], rows[-1]['time']] if rows else None,
                'measurements': summarize_edges(edge_rows), 'stops': stops, 'windows': windows,
                'cloth_max_above_head_cm': stats([c['max_above_head_cm'] for c in bounds]),
                'cloth_p95_above_head_cm': stats([c['p95_above_head_cm'] for c in bounds]),
                'cloth_max_radius_cm': stats([c['max_radius_cm'] for c in bounds]),
                'sampled_particle_fraction_above_head': stats(fraction_above),
                'all_cloth_simulation_enabled': all(not row['cloth_disabled'] and not row['cloth_suspended'] for row in rows),
                'cape_configuration_at_spawn': case['data'].get('cape_configuration_at_spawn')}
        shots = {}
        for shot in report['screenshots']:
            image = Path(shot['image'])
            assert digest(image) == shot['sha256']
            key = (shot['case'], image.stem.split('-', 1)[1])
            assert key not in shots
            shots[key] = shot
        log_path = root / 'editor.log'
        module_lines = [line for line in log_path.read_text(encoding='utf-8', errors='replace').splitlines()
                        if "InternalLoadLibrary: 'LearnTopDown'" in line]
        modules = sorted(set(re.findall(r'UnrealEditor-LearnTopDown(?:-\d+)?\.dll', '\n'.join(module_lines))))
        assert len(modules) == 1, str(log_path)
        runs[mode] = {'directory': str(root), 'report': str(path), 'sha256': digest(path),
                      'source_module': modules[0], 'source_editor_log': {'path': str(log_path), 'sha256': digest(log_path)},
                      'cases': cases, 'shots': shots}
    if new_only:
        new = runs['new']
        result = {'passed': True, 'fps': target_fps, 'scope': 'new30stabilityonly' if target_fps == 30 else 'new_variant_stability_only',
                  'style_approval': False, 'comparison': None, 'paired_native_captures': 0,
                  'case_count': len(new['cases']), 'runs': {'new': {k: v for k, v in new.items() if k != 'shots'}},
                  'capture_integrity_checked': len(new['shots']),
                  'limitations': ['Only the new cape variant was run; this output does not establish a same-FPS before/after difference.',
                                  'Cloth and pose statistics are measurements; they are not artistic approval.',
                                  'Full traces retain every unique observed simulation frame and fixed sampled cloth identities.']}
        path = directory / f'sparrow-cape-stability-{target_fps}.json'
        path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'passed': True, 'report': str(path), 'scope': result['scope'], 'cases': len(new['cases'])}))
        return result
    before, after = runs['old'], runs['new']
    assert before['cases'].keys() == after['cases'].keys()
    assert before['shots'].keys() == after['shots'].keys()
    pairs = []
    for key, old in before['shots'].items():
        new = after['shots'][key]
        a, b = old['state'], new['state']
        pairs.append({'case': key[0], 'capture': key[1], 'before': old, 'after': new,
                      'equal_viewport_size': [old['width'], old['height']] == [new['width'], new['height']],
                      'camera_world_position_difference_cm': math.dist(a['view_location'], b['view_location']),
                      'pawn_world_position_difference_cm': math.dist(a['position'], b['position']),
                      'world_time_difference_seconds': b['time'] - a['time'],
                      'wind_phase_matched': False,
                      'phase_limit': 'Actual world time and post-spawn age are recorded; no unobserved sine phase or identical random cloth state is assumed.'})
    result = {'passed': True, 'fps': target_fps, 'style_approval': False,
              'case_count_per_variant': len(before['cases']), 'paired_native_captures': len(pairs),
              'runs': {name: {k: v for k, v in run.items() if k != 'shots'} for name, run in runs.items()},
              'capture_pairs': pairs,
              'reused_old_directory': str(Path(old_run).resolve()) if old_run else None,
              'same_module_binary': before['source_module'] == after['source_module'],
              'limitations': ['Native PNGs remain unchanged and unscaled; these are sampled frames, not continuous video.',
                              'Cloth and bone trajectories both remain in full traces; cloth speed includes pose-driven movement.',
                              'Per-frame displacement is FPS-dependent; compare equal-FPS variants and real-time speed windows.',
                              'Maximum and p95 head-height bounds use all simulated vertices; flutter trajectories sample fixed 32 vertex identities.',
                              'New and old runs use separate editors. World time is recorded; no sine phase or solver state equality is inferred.',
                              'RMS or a strongest sinusoid candidate does not establish artistic improvement; actual paired images require review.']}
    if old_run:
        result['limitations'].append('Old evidence is referenced in place from its original completed run. Old/new loaded module names are reported separately; new wind assertions were not retroactively executed on the old run.')
    path = directory / f'sparrow-cape-comparison-{target_fps}.json'
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'report': str(path), 'cases_per_variant': len(before['cases']), 'paired_native_captures': len(pairs)}))
    return result


def editor_main():
    import types
    import unreal
    root = Path(unreal.Paths.project_dir()).resolve()
    sys.path[:0] = [str(root / 'Tools/CharacterPipeline'), str(root / 'Tools/CharacterPipeline/Suites')]
    from context import fps, job, qa
    from sparrow_runtime import Runner, valid, xyz
    from character_switch import FieldRig, field_meshes, angle_error
    from training_room_verify import TrainingRunner, ROOM, room, select, primary, skill, cleanup, HERO_PROFILES
    from sparrow_stop_diagnostic import record_motion, camera_check, motion_measurement, held_near

    variant = int(job['cape_variant'])
    assert variant in (0, 1)

    def settled_camera_switch(rig, name, moving=False, camera_settled=True):
        if not moving and camera_settled:
            observation = {'target_hero': name, 'started': rig.now,
                           'required_pawn_speed_below_cm_per_second': 1,
                           'required_camera_speed_at_most_cm_per_second': .1,
                           'required_continuous_seconds': .2, 'maximum_wait_seconds': 5,
                           'samples': [], 'existing_switch_location_tolerance_cm': 1}
            rig.data.setdefault('camera_switch_preconditions', []).append(observation)
            previous_time = rig.now
            previous_camera = xyz(rig.controller.player_camera_manager.get_camera_location())
            stable_since = None
            while rig.now - observation['started'] <= 5:
                yield 1 / fps
                now = rig.now
                camera = xyz(rig.controller.player_camera_manager.get_camera_location())
                dt = now - previous_time
                camera_speed = math.dist(camera, previous_camera) / dt if dt > 0 else float('inf')
                pawn_speed = math.sqrt(sum(value * value for value in xyz(rig.pawn.get_velocity())))
                sample = {'time': now, 'time_step': dt, 'camera_location': camera,
                          'camera_speed_cm_per_second': camera_speed, 'pawn_speed_cm_per_second': pawn_speed}
                observation['samples'].append(sample)
                if pawn_speed < 1 and camera_speed <= .1:
                    if stable_since is None:
                        stable_since = previous_time
                    sample['continuous_stable_seconds'] = now - stable_since
                    if now - stable_since >= .2 - .00001:
                        observation.update(passed=True, fulfilled_at=now, waited_seconds=now - observation['started'],
                                           continuous_stable_seconds=now - stable_since)
                        break
                else:
                    stable_since = None
                previous_time, previous_camera = now, camera
            rig.check(observation.get('passed', False),
                      'Cape-only switch precondition observes a physically stopped pawn and camera speed <=0.1cm/s continuously for 0.2 seconds')
        # Preserve the existing shared 1cm/angle/projection assertions without changing that suite.
        yield from FieldRig.switch(rig, name, moving=moving, camera_settled=camera_settled)

    def tagged_sources(pawn):
        return [component for component in pawn.get_components_by_class(unreal.SceneComponent)
                if component.component_has_tag('SparrowCapeWind')]

    def wind_source_row(component, rig):
        location = component.get_world_location()
        relative = xyz(component.get_editor_property('relative_location'))
        radius = component.get_editor_property('radius')
        distance = math.dist(xyz(location), xyz(rig.mesh.get_world_location()))
        speed = component.get_editor_property('speed')
        falloff = 1 - (distance / radius) ** 2
        effective = speed * falloff * 100 * 25
        maximum = unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.WindSpeed')
        age = rig.pawn.get_game_time_since_creation()
        return {'component': component.get_path_name(), 'class': component.get_class().get_path_name(),
                'owner': component.get_owner().get_path_name() if component.get_owner() else None,
                'owner_name': component.get_owner().get_name() if component.get_owner() else None,
                'owner_is_current_pawn': component.get_owner() == rig.pawn,
                'point_wind': component.get_editor_property('point_wind'),
                'radius_cm': radius, 'raw_source_speed': speed,
                'strength': component.get_editor_property('strength'),
                'minimum_gust': component.get_editor_property('min_gust_amount'),
                'maximum_gust': component.get_editor_property('max_gust_amount'),
                'relative_location_cm': relative,
                'world_location_cm': xyz(location),
                'mesh_origin_distance_cm': distance,
                'computed_point_falloff': falloff,
                'computed_equivalent_legacy_wind_cm_per_second': effective,
                'pawn_creation_age_seconds': age,
                'pulse_fit_using_creation_age': pulse_fit(age, maximum, effective, relative[0], fps),
                'pulse_formula': 'speed=(110+50*sin(2*pi*.65*t)+20*sin(2*pi*1.15*t+.8))*(max/180); lateral=1.3*sin(2*pi*.48*t)+.7*sin(2*pi*.83*t+.5)',
                'unit_conversion': 'raw scene m/s * point falloff * 100 cm/m * legacy 25',
                'source_query_not_called': True}

    def cape_record(rig):
        previous = len(rig.trace)
        record_motion(rig)
        if len(rig.trace) == previous:
            return
        rig.latest['cape_observation'] = {
            'world_time_seconds': rig.now,
            'variant_cvar': unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Cloth.Presentation'),
            'seconds_since_spawn_processed': rig.now - rig.cape_spawn_time if hasattr(rig, 'cape_spawn_time') and isinstance(rig.pawn, unreal.SparrowCharacter) else None,
            'wind_speed_cvar_cm_per_second': unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.WindSpeed'),
            'wind_sine_phase': 'Two speed and two lateral phases are calculated from observed pawn age; native start-time logs are checked after process completion.',
            'phase_note': 'Actual source values are CPU component observations. A compatible 20Hz update age is fitted with bounded timer/game-frame lag; cloth solver phase is not observed.',
            'owner_wind_sources': [wind_source_row(component, rig) for component in tagged_sources(rig.pawn)]
                if isinstance(rig.pawn, unreal.SparrowCharacter) else []}

    def spawn_variant(rig):
        if isinstance(rig.pawn, unreal.SparrowCharacter):
            yield from rig.switch('countess')
        unreal.SystemLibrary.execute_console_command(rig.world, 'Sparrow.Cloth.Presentation ' + str(variant))
        rig.check(unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Cloth.Presentation') == variant,
                  'the requested cape variant is set before the new pawn BeginPlay')
        queued = rig.now
        yield from rig.switch('sparrow')
        switch_row = rig.data['switches'][-1]
        rig.cape_spawn_time = switch_row['immediate']['time']
        yield .5
        camera_check(rig)
        rig.check(rig.mesh.get_editor_property('anim_class').get_path_name() == HERO_PROFILES['sparrow']['expected'].get('runtime_anim_class', HERO_PROFILES['sparrow']['expected']['anim_class']),
                  'cape variant uses the declared runtime copy containing the preserved stop graph')
        sources = tagged_sources(rig.pawn)
        source_rows = [wind_source_row(component, rig) for component in sources]
        rig.check(len(sources) == variant, 'actual cape owner has exactly one tagged wind source only in the new variant')
        for source_row in source_rows:
            rig.check(source_row['class'] == '/Script/Engine.WindDirectionalSourceComponent',
                      'tagged cape source is an actual engine wind component')
            rig.check(source_row['owner_is_current_pawn'], 'local cape wind is owned by the actual current archer')
            rig.check(source_row['point_wind'] and abs(source_row['radius_cm'] - 20) < .001,
                      'local cape wind retains its narrow 20cm point radius')
            rig.check(source_row['mesh_origin_distance_cm'] <= math.sqrt(29) + .01,
                      'point wind remains inside the 5cm forward and 2cm lateral offset envelope')
            rig.check(source_row['pulse_fit_using_creation_age']['matches'],
                      'source speed and lateral offset match one common pulse-update age within the bounded 20Hz observation lag')
        rig.data['cape_configuration_at_spawn'] = {'variant': variant, 'spawn_queued_at': queued,
            'spawn_processed_at': rig.cape_spawn_time,
            'observed_at': rig.now, 'fresh_numeric_selection': True,
            'wind_speed_cvar': unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.WindSpeed'),
            'damping_cvar': unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.Damping'),
            'local_damping_cvar': unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.LocalDamping'),
            'owner_wind_sources': source_rows,
            'configuration_cvars_are_not_solver_readback': True}
        for name in ('Countess', 'Sparrow'):
            unreal.SystemLibrary.execute_console_command(rig.world, name + '.Skills.IgnoreCooldowns 1')

    def idle(rig):
        yield from spawn_variant(rig)
        start = rig.now
        rig.data['observation_windows'] = [{'label': 'idle-three-seconds', 'start': start}]
        for at in (0, .5, 1.0, 1.5, 2.0, 2.5, 3.0):
            if at:
                yield max(1 / fps, at - (rig.now - start))
            rig.data.setdefault('phase_captures', []).append({'label': 'idle-' + str(at), 'time': rig.now, 'seconds_from_phase_start': rig.now - start})
            yield rig.capture('cape-idle-' + str(at).replace('.', ''))
        rig.data['observation_windows'][0]['end'] = rig.now
        rig.check(rig.latest['speed'] < 1 and not rig.pawn.is_combat_busy(), 'idle observation contains no movement or cast input')

    def fixed_room(rig):
        unreal.SystemLibrary.execute_console_command(rig.world, 'CharacterVisualQA.ViewportSize 700 330')
        yield 2 / fps
        rig.check(rig.snapshot()['viewport_size'] == [700, 330],
                  'actual PIE render viewport is fixed at 700x330 before the first comparison capture')
        yield from room(rig)

    def movement(index):
        def run(rig):
            yield from spawn_variant(rig)
            theta = math.radians(index)
            yield from motion_measurement(rig, 'direction-' + str(index), rig.ground(600 * math.cos(theta), 600 * math.sin(theta)))
        return run

    def short_turn(label, dx, dy):
        def run(rig):
            yield from spawn_variant(rig)
            yield from motion_measurement(rig, label + '-approach', rig.ground(0, 500), False)
            position = rig.pawn.get_actor_location()
            yield from motion_measurement(rig, label, rig.ground_absolute(position.x + dx, position.y + dy))
        return run

    def hold(rig):
        yield from spawn_variant(rig)
        yield from held_near(rig)

    def combat(key):
        def run(rig):
            yield from spawn_variant(rig)
            if key == 'Attack':
                yield from primary('sparrow')(rig)
            else:
                yield from skill('sparrow', key)(rig)
        return run

    def owner_cleanup(rig):
        yield from spawn_variant(rig)
        previous_sources = tagged_sources(rig.pawn)
        previous_paths = [component.get_path_name() for component in previous_sources]
        yield from cleanup(rig)
        rig.check(not unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.SparrowCharacter),
                  'numeric One removes the prior cape owner without a remaining archer')
        rig.check(all(not valid(component) for component in previous_sources),
                  'numeric One invalidates every wind component owned by the destroyed archer')
        remaining = [component.get_path_name()
                     for actor in unreal.GameplayStatics.get_all_actors_of_class(rig.world, unreal.Actor)
                     for component in actor.get_components_by_class(unreal.SceneComponent)
                     if component.component_has_tag('SparrowCapeWind')]
        rig.check(not remaining, 'destroyed archer leaves no tagged wind source registered on another world actor')
        rig.data['wind_owner_cleanup'] = {'source_paths_before': previous_paths,
            'source_references_invalid_after': [not valid(component) for component in previous_sources],
            'remaining_tagged_sources': remaining}

    class CapeRunner(TrainingRunner):
        def __init__(self):
            cases = [('room', fixed_room), ('idle_flutter', idle)]
            cases += [('direction_' + str(index), movement(index)) for index in (0, 90, 270)]
            cases += [('short_reverse_110', short_turn('short-reverse-110', 0, -110)),
                      ('short_cross_110', short_turn('short-cross-110', 110, 0)), ('held_near_release', hold)]
            cases += [('combat_' + key, combat(key)) for key in ('Attack', 'Q', 'W', 'R')]
            cases += [('numeric_owner_cleanup', owner_cleanup)]
            Runner.__init__(self, 'sparrow_cape', cases)
            self.report_name = f'sparrow-cape-{fps}.json'
            self.report.update(map=ROOM, cape_variant=variant, physical_input_tested=False,
                source_assets_modified=False, scene_changes_saved=False, camera_zoom_changed=False,
                full_trace_sampling='Every unique simulation frame with fixed original cloth particle identities, pose bones and world time.',
                style_approval=False)

        def case_generator(self, factory):
            rig = self.rig
            rig.record = types.MethodType(cape_record, rig)
            rig.switch = types.MethodType(settled_camera_switch, rig)
            yield from TrainingRunner.case_generator(self, factory)
            rig.check(field_meshes(rig.world) == self.original_field, 'cape observations preserve every saved room mesh actor')
            legs = list(rig.data.get('legs', []))
            if rig.data.get('held_input'):
                legs.append(dict(rig.data['held_input'], label='held-input-release'))
            for leg in legs:
                if leg.get('captures'):
                    rig.data.setdefault('observation_windows', []).append({
                        'label': leg['label'] + '-post-stop-settling',
                        'start': leg['stopped'], 'end': leg['stopped'] + 1.5})
            directory = qa / 'traces'
            directory.mkdir(exist_ok=True)
            path = directory / (self.case_name + '-' + str(fps) + '.json')
            path.write_text(json.dumps({'case': self.case_name, 'fps': fps, 'cape_variant': variant, 'samples': rig.trace}, indent=2), encoding='utf-8')
            rig.data['full_simulation_trace'] = {'path': str(path), 'sha256': digest(path), 'samples': len(rig.trace)}
            rows = [row for row in rig.trace if row.get('pawn_class') == 'BP_SparrowCharacter_C']
            if rows:
                rig.check(all(not row['cloth_disabled'] and not row['cloth_suspended'] for row in rows),
                          'cape simulation remains enabled and unsuspended on every archer observation frame')
                rig.check(all(all(math.isfinite(cloth[key]) and cloth[key] <= limit for key, limit in
                    (('max_above_head_cm', 30), ('p95_above_head_cm', 10), ('max_radius_cm', 130))) for row in rows for cloth in row['cloth']),
                    'cape retains the existing head-height and radial stability bounds')
                observed_wind = [source for row in rows for source in row.get('cape_observation', {}).get('owner_wind_sources', [])]
                rig.check(all(source['owner_is_current_pawn'] and source['mesh_origin_distance_cm'] <= math.sqrt(29) + .01
                              for source in observed_wind), 'observed local wind continues to follow only its actual cape owner')
                for source in observed_wind:
                    x, y, z = source['relative_location_cm']
                    maximum = max(0, min(200, unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Cloth.WindSpeed')))
                    effective = source['computed_equivalent_legacy_wind_cm_per_second']
                    rig.check(abs(x) <= 2.001 and abs(y - 5) < .001 and abs(z) < .001,
                              'lateral pulse stays within 2cm and adds no vertical wind-source offset')
                    rig.check(40 * maximum / 180 - .02 <= effective <= maximum + .02,
                              'pulse source retains bounded airflow with both engine unit conversions')
                    rig.check(source['pulse_fit_using_creation_age']['matches'],
                              'every observed source speed and lateral value fits a common bounded pulse-update age')
                if self.case_name == 'idle_flutter' and observed_wind:
                    speeds = [source['computed_equivalent_legacy_wind_cm_per_second'] for source in observed_wind]
                    lateral = [source['relative_location_cm'][0] for source in observed_wind]
                    rig.check(max(speeds) - min(speeds) > 40 and max(lateral) - min(lateral) > 1,
                              'the idle observation actually contains changing airflow and side sway rather than constant wind')
                rig.check(all(shot['width'] == 700 and shot['height'] == 330 for shot in self.report['screenshots']),
                          'all actual captured viewport PNGs preserve the fixed 700x330 framing')
                for row in rows:
                    for effect in row['effects']:
                        if effect['active'] and effect['particles'] > 0:
                            for emitter in effect.get('render_emitters', []):
                                if emitter.get('renders_surface', True) and emitter['particles'] > 0:
                                    rig.check(not any('WorldGridMaterial' in material or 'DefaultMaterial' in material
                                        for material in emitter['materials']), 'observed active skills retain non-placeholder surface materials')
            for leg in rig.data.get('legs', []):
                if leg.get('last_moving_velocity_yaw') is not None:
                    error = angle_error(leg['post_settling_actor_yaw'], leg['last_moving_velocity_yaw'])
                    rig.check(error < .1, 'settled natural stop preserves its final actual movement heading')
            if rig.data.get('held_input'):
                held = rig.data['held_input']
                moving = [row for row in rows if held['started'] <= row['time'] <= held['stopped'] and row['speed'] > 20]
                if moving:
                    error = angle_error(held['post_settling_actor_yaw'], moving[-1]['motion']['velocity_yaw'])
                    held['settled_heading_error_degrees'] = error
                    rig.check(error < .1, 'held movement release preserves its last actual movement heading')

        def advance(self):
            # Raw excursions are recorded first; whole-case checks use the existing stable-cloth contract.
            Runner.advance(self)

    runtime = CapeRunner()
    runtime.start()


if __name__ == '__main__':
    if '--review' in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument('--review', type=Path, required=True)
        parser.add_argument('--fps', type=int, choices=(30, 60), required=True)
        parser.add_argument('--new-only', action='store_true')
        parser.add_argument('--old-run', type=Path)
        arguments = parser.parse_args()
        if arguments.new_only and arguments.old_run:
            parser.error('--old-run cannot be combined with --new-only')
        review(arguments.review, arguments.fps, arguments.new_only, arguments.old_run)
    else:
        editor_main()
