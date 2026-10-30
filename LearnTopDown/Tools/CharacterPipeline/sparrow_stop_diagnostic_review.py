"""Summarize measured stop/cloth traces and derive unchanged-viewport review media.

This is an observation report, not a style acceptance test. No excursion threshold
is used to declare animation or cloth correct. Run against one 30/60 FPS output.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    index = (len(values) - 1) * fraction
    low, high = math.floor(index), math.ceil(index)
    return values[low] + (values[high] - values[low]) * (index - low)


def stats(values):
    values = [float(value) for value in values if value is not None]
    return {'count': len(values), 'mean': statistics.fmean(values) if values else None,
            'rms': math.sqrt(statistics.fmean(value * value for value in values)) if values else None,
            'p95': percentile(values, .95), 'maximum': max(values) if values else None}


def angle(a, b):
    return abs((a - b + 180) % 360 - 180)


def quaternion_angle(a, b):
    norm = math.sqrt(sum(v * v for v in a) * sum(v * v for v in b))
    if norm == 0:
        return None
    return math.degrees(2 * math.acos(min(1, abs(sum(x * y for x, y in zip(a, b))) / norm)))


def point_map(snapshot):
    result = {}
    for cloth in (snapshot or {}).get('cloth', []):
        indices, points = cloth['particle_indices'], cloth['points']
        if len(indices) != len(points) or len(indices) != len(set(indices)):
            raise ValueError('Invalid or duplicate sampled particle indices')
        for index, point in zip(indices, points):
            if len(point) != 3 or not all(math.isfinite(value) for value in point):
                raise ValueError('Invalid cloth particle coordinates')
            result[(cloth['index'], cloth['vertices'], index)] = point
    return result


def edges(samples):
    result = []
    for first, second in zip(samples, samples[1:]):
        dt = second['time'] - first['time']
        if dt <= 0:
            raise ValueError('Full trace must have strictly increasing simulation time')
        before, after = first.get('motion'), second.get('motion')
        if not before or not after:
            continue
        row = {'start': first['time'], 'end': second['time'], 'dt': dt,
               'actor_yaw_step_degrees': angle(before['actor_yaw'], after['actor_yaw']), 'bones': {}}
        for bone in ('foot_l', 'foot_r', 'head', 'pelvis'):
            a = before['bones_component_space'][bone]
            b = after['bones_component_space'][bone]
            row['bones'][bone] = {'translation_step_cm': math.dist(a['translation'], b['translation']),
                                 'rotation_step_degrees': quaternion_angle(a['rotation_quaternion'], b['rotation_quaternion'])}
        first_points = point_map(first.get('cloth_points_component_space'))
        second_points = point_map(second.get('cloth_points_component_space'))
        common = first_points.keys() & second_points.keys()
        displacements = [math.dist(first_points[key], second_points[key]) for key in common]
        row['cloth'] = {'matched_particles': len(common),
                        'dropped_or_changed_identity': len(first_points.keys() ^ second_points.keys()),
                        'displacement_cm': stats(displacements),
                        'speed_cm_per_second': stats([value / dt for value in displacements])}
        result.append(row)
    return result


def summarize_edges(rows):
    def peak(field):
        candidates = [(field(row), row) for row in rows if field(row) is not None]
        if not candidates:
            return None
        value, row = max(candidates, key=lambda item: item[0])
        return {'value': value, 'interval_start': row['start'], 'interval_end': row['end']}

    return {'intervals': len(rows), 'time_step_seconds': stats([row['dt'] for row in rows]),
            'actor_yaw_step_degrees': stats([row['actor_yaw_step_degrees'] for row in rows]),
            'peak_actor_yaw_step_degrees': peak(lambda row: row['actor_yaw_step_degrees']),
            'bones_component_space': {bone: {
                field: stats([row['bones'][bone][field] for row in rows])
                for field in ('translation_step_cm', 'rotation_step_degrees')}
                for bone in ('foot_l', 'foot_r', 'head', 'pelvis')},
            'peak_bone_translation_steps_cm': {
                bone: peak(lambda row, name=bone: row['bones'][name]['translation_step_cm'])
                for bone in ('foot_l', 'foot_r', 'head', 'pelvis')},
            'cloth_component_space': {
                'matched_particle_comparisons': sum(row['cloth']['matched_particles'] for row in rows),
                'identity_change_count': sum(row['cloth']['dropped_or_changed_identity'] for row in rows),
                'per_frame_max_displacement_cm': stats([row['cloth']['displacement_cm']['maximum'] for row in rows]),
                'peak_displacement_cm': peak(lambda row: row['cloth']['displacement_cm']['maximum']),
                'per_frame_rms_speed_cm_per_second': stats([row['cloth']['speed_cm_per_second']['rms'] for row in rows]),
                'per_frame_max_speed_cm_per_second': stats([row['cloth']['speed_cm_per_second']['maximum'] for row in rows])}}


def resolve_file(value, directory):
    path = Path(value)
    return path if path.is_absolute() else directory / path


def summarize_leg(leg, samples, all_edges, fps, next_leg_started=None):
    stop, start = leg['stopped'], leg['started']
    observed_until = min(stop + 1.5, next_leg_started) if next_leg_started is not None else stop + 1.5
    all_edges = [row for row in all_edges if row['end'] <= observed_until + 1e-6]
    moving = [row for row in samples if start <= row['time'] <= stop and row['speed'] > 20
              and row.get('motion', {}).get('velocity_yaw') is not None]
    last_heading = moving[-1]['motion']['velocity_yaw'] if moving else None
    stop_row = min(samples, key=lambda row: abs(row['time'] - stop))
    windows = {}
    for low, high in ((0, .3), (.3, .7), (.7, 1.5)):
        # Require both interval endpoints inside each window: no moving pre-stop edge
        # contaminates residual motion and no interval is counted in two windows.
        rows = [row for row in all_edges if row['start'] >= stop + low - 1e-6
                and row['end'] <= stop + high + 1e-6]
        coverage = sum(row['dt'] for row in rows)
        windows[f'{low:g}_to_{high:g}_seconds'] = {
            'requested_duration_seconds': high - low, 'observed_interval_seconds': coverage,
            'unobserved_duration_seconds': max(0, high - low - coverage),
            'full_window_observed_within_one_frame': coverage >= high - low - 1 / fps - 1e-6,
            'measurements': summarize_edges(rows)}
    around = [row for row in all_edges if row['start'] >= stop - .25 - 1e-6
              and row['end'] <= stop + .3 + 1e-6]
    post = [row for row in samples if stop <= row['time'] <= observed_until]
    snapshots = [row['cloth_points_component_space'] for row in samples
                 if start <= row['time'] <= observed_until and row.get('cloth_points_component_space')]
    nonzero_modes = [{'time_relative_to_stop': row['time'] - stop,
                      'pending_teleport_mode': row.get('pending_teleport_mode')}
                     for row in snapshots if row.get('pending_teleport_mode', 0) != 0]
    return {'label': leg.get('label', 'held-input-release'), 'started': start, 'stopped': stop,
            'next_movement_input_time': next_leg_started,
            'residual_observation_capped_at_next_movement_input': next_leg_started is not None and next_leg_started < stop + 1.5,
            'actual_stop_sample_offset_seconds': stop_row['time'] - stop,
            'last_moving_speed_selection_cm_per_second': '>20; heading reference only, not acceptance threshold',
            'last_moving_velocity_yaw_degrees': last_heading,
            'actor_yaw_at_nearest_stop_sample_degrees': stop_row['motion']['actor_yaw'],
            'stop_actor_vs_last_motion_error_degrees': angle(stop_row['motion']['actor_yaw'], last_heading) if last_heading is not None else None,
            'post_stop_actor_vs_last_motion_error_degrees': stats([
                angle(row['motion']['actor_yaw'], last_heading) for row in post]) if last_heading is not None else None,
            'moving_actor_velocity_error_degrees': stats([row['motion'].get('actor_velocity_error_degrees') for row in moving]),
            'stop_transition_minus_025_to_plus_030_seconds': summarize_edges(around),
            'residual_motion_windows': windows,
            'pending_teleport_observations': nonzero_modes,
            'reset_after_teleport_values': sorted(set(row.get('reset_after_teleport') for row in snapshots
                                                    if 'reset_after_teleport' in row)),
            'reset_history_available': False,
            'reset_observation_limit': 'Pending mode snapshots cannot prove or disprove solver resets already consumed.'}


def media(report, directory, output, fps):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    except OSError:
        font = ImageFont.load_default()
    groups = {}
    sources = []
    for shot in report.get('screenshots', []):
        path = resolve_file(shot['image'], directory)
        before = digest(path)
        if shot.get('sha256') and before != shot['sha256']:
            raise ValueError('Screenshot hash mismatch: ' + str(path))
        with Image.open(path) as image:
            raw = image.convert('RGB')
        time = shot.get('state', {}).get('time')
        case = shot.get('case', 'unclassified')
        groups.setdefault(case, []).append((time, path, raw))
        sources.append({'path': str(path), 'sha256': before, 'case': case, 'time': time,
                        'width': raw.width, 'height': raw.height})
    products = []
    for case, shots in groups.items():
        shots.sort(key=lambda row: float('-inf') if row[0] is None else row[0])
        frames = []
        width, height = max(row[2].width for row in shots), max(row[2].height for row in shots)
        for time, path, raw in shots:
            frame = Image.new('RGB', (width, height + 30), '#12151c')
            frame.paste(raw, (0, 30))
            ImageDraw.Draw(frame).text((5, 5), f'{path.stem} / t={time}', fill='#efeff2', font=font)
            frames.append(frame)
        for start in range(0, len(frames), 4):
            batch = frames[start:start + 4]
            sheet = Image.new('RGB', (width * 2, (height + 30) * math.ceil(len(batch) / 2)), '#12151c')
            for index, frame in enumerate(batch):
                sheet.paste(frame, (index % 2 * width, index // 2 * (height + 30)))
            target = output / f'{case}-sheet-{start // 4 + 1}.png'
            sheet.save(target)
            products.append(str(target))
        if len(frames) > 1 and all(row[0] is not None for row in shots):
            durations = [max(10, round((b[0] - a[0]) * 1000 / 10) * 10) for a, b in zip(shots, shots[1:])]
            durations.append(max(10, round(1000 / fps / 10) * 10))
            target = output / f'{case}-sampled.gif'
            frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0)
            products.append({'path': str(target), 'simulation_times_seconds': [row[0] for row in shots],
                             'playback_milliseconds': durations,
                             'last_frame_hold': 'one simulation frame rounded to GIF 10 ms resolution'})
    for source in sources:
        if digest(Path(source['path'])) != source['sha256']:
            raise ValueError('Raw screenshot changed during derivation')
    return {'sources': sources, 'products': products, 'raw_images_modified': False,
            'cropped': False, 'image_scale': 1, 'continuous_video': False,
            'gif_timing': 'Measured sample intervals rounded to GIF 10 ms resolution; intermediate frames were not captured.',
            'gif_color_limit': 'Derived GIF is palette quantized; source PNGs are authoritative.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--fps', type=int, choices=(30, 60), required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--no-media', action='store_true')
    args = parser.parse_args()
    directory = args.directory.resolve()
    report_path = directory / f'sparrow-stop-diagnostic-{args.fps}.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    output = args.output.resolve() if args.output else directory / 'review'
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for case in report.get('cases', []):
        data = case.get('data', {})
        descriptor = data.get('full_simulation_trace')
        if not descriptor:
            cases.append({'name': case['name'], 'analysis_available': False,
                          'reason': 'Full simulation trace absent; 10 Hz report samples are not substituted.'})
            continue
        path = resolve_file(descriptor['path'], directory)
        if digest(path) != descriptor['sha256']:
            raise ValueError('Full trace hash mismatch: ' + str(path))
        trace = json.loads(path.read_text(encoding='utf-8'))
        samples = trace['samples']
        if trace['fps'] != args.fps or len(samples) != descriptor['samples']:
            raise ValueError('Full trace metadata mismatch: ' + str(path))
        edge_rows = edges(samples)
        legs = list(data.get('legs', []))
        if data.get('held_input'):
            legs.append(data['held_input'])
        cases.append({'name': case['name'], 'analysis_available': True,
                      'source': {'path': str(path), 'sha256': digest(path)},
                      'trace_samples': len(samples), 'full_trace_time_step_seconds': stats([
                          b['time'] - a['time'] for a, b in zip(samples, samples[1:])]),
                      'legs': [summarize_leg(leg, samples, edge_rows, args.fps,
                                             legs[index + 1]['started'] if index + 1 < len(legs) else None)
                               for index, leg in enumerate(legs)]})
    result = {'fps': args.fps, 'source_report': str(report_path), 'source_report_sha256': digest(report_path),
              'source_runner_passed': report.get('passed'), 'style_acceptance_decided': False,
              'statistics_only_no_arbitrary_acceptance_thresholds': True, 'cases': cases,
              'measurement_limits': [
                  'Bone and cloth coordinates are in mesh component space, separating actor translation and yaw from local pose motion.',
                  'Cloth speed describes sampled particle motion, including animation-driven shape changes; it does not isolate numerical instability.',
                  'Particle identity uses cloth index, original vertex count and original particle index; changed identities are not compared.',
                  'A pending teleport mode is not a solver-reset event history. Zero pending flags do not prove that no reset occurred.',
                  'Per-frame displacement depends on FPS. Compare speeds and real-time windows across 30/60 FPS, not displacement alone.',
                  'Unobserved residual windows remain explicitly incomplete and are not interpreted as zero motion.'],
              'cause_interpretation': {
                  'confirmed': 'Only the recorded pose, heading and sampled cloth motion statistics are confirmed by this report.',
                  'hypotheses_requiring_comparison': [
                      'Large actor yaw changes near natural stop can explain a visible turn and inject discontinuous cloth input.',
                      'A local bone pose step with stable actor yaw points toward animation blending rather than navigation facing.',
                      'Persistent cloth speed after bone pose settles warrants a separate damping/animation-drive comparison.'],
                  'automatically_attributed_cause': None}}
    if not args.no_media:
        result['media_derivation'] = media(report, directory, output, args.fps)
    target = output / 'motion-analysis.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    stops = [{'case': case['name'], 'label': leg['label'],
              'stop_heading_error_degrees': leg['stop_actor_vs_last_motion_error_degrees'],
              'maximum_stop_yaw_step_degrees': leg['stop_transition_minus_025_to_plus_030_seconds']['actor_yaw_step_degrees']['maximum'],
              'maximum_stop_foot_steps_cm': {bone: leg['stop_transition_minus_025_to_plus_030_seconds']['bones_component_space'][bone]['translation_step_cm']['maximum']
                                            for bone in ('foot_l', 'foot_r')},
              'residual_cloth_rms_speed_cm_per_second': {
                  key: window['measurements']['cloth_component_space']['per_frame_rms_speed_cm_per_second']['rms']
                  for key, window in leg['residual_motion_windows'].items()}}
             for case in cases for leg in case.get('legs', [])]
    print(json.dumps({'analysis': str(target), 'fps': args.fps, 'cases': len(cases),
                      'observed_stops': sum(len(case.get('legs', [])) for case in cases),
                      'style_acceptance_decided': False, 'measured_stop_summary': stops}, ensure_ascii=False))


if __name__ == '__main__':
    main()
