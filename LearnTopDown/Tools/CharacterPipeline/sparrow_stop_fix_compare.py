"""Compare measured archer stop traces without equating smoothing with style approval.

Native reports, full traces and PNGs remain unchanged. Derived comparison files
are written only to --output. Existing review analyses are consumed when present.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import sparrow_stop_diagnostic_review as review


BONES = ('foot_l', 'foot_r', 'pelvis', 'head')
DEFAULT_CASES = ('direction_0', 'direction_270', 'short_reverse_110')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def change(before, after):
    return {'before': before, 'after': after,
            'after_minus_before': after - before if before is not None and after is not None else None,
            'after_divided_by_before': after / before if before not in (None, 0) and after is not None else None}


def rotated(vector, quaternion):
    x, y, z, w = quaternion
    length = math.sqrt(x*x + y*y + z*z + w*w)
    if length == 0:
        raise ValueError('Invalid mesh quaternion')
    x, y, z, w = [value / length for value in (x, y, z, w)]
    vx, vy, vz = vector
    tx, ty, tz = 2*(y*vz-z*vy), 2*(z*vx-x*vz), 2*(x*vy-y*vx)
    return [vx+w*tx+y*tz-z*ty, vy+w*ty+z*tx-x*tz, vz+w*tz+x*ty-y*tx]


def world_bone(sample, bone):
    transform = sample['motion']['mesh_world_transform']
    local = sample['motion']['bones_component_space'][bone]['translation']
    scaled = [value * scale for value, scale in zip(local, transform['scale'])]
    return [value + offset for value, offset in zip(rotated(scaled, transform['rotation_quaternion']), transform['translation'])]


def trajectory(points, times=None):
    if not points:
        return None
    steps = [math.dist(a, b) for a, b in zip(points, points[1:])]
    speeds = [step / (b-a) for step, a, b in zip(steps, times, times[1:])] if times else []
    return {'samples': len(points), 'start': points[0], 'end': points[-1],
            'net_displacement_cm': math.dist(points[0], points[-1]),
            'path_length_cm': sum(steps), 'maximum_frame_step_cm': max(steps, default=None),
            'maximum_frame_speed_cm_per_second': max(speeds, default=None),
            'maximum_distance_from_first_sample_cm': max(math.dist(points[0], point) for point in points)}


def displacement_evidence(samples, leg, next_started):
    start, stop = leg['started'], leg['stopped']
    cap = min(stop + 1.5, next_started) if next_started is not None else stop + 1.5
    output = {}
    for label, low, high in (('transition_minus_025_to_plus_030', -.25, .3),
                             ('transition_minus_025_to_plus_150', -.25, 1.5),
                             ('post_stop_000_to_030', 0, .3), ('post_stop_000_to_070', 0, .7),
                             ('post_stop_000_to_150', 0, 1.5)):
        rows = [row for row in samples if max(start, stop + low) - 1e-6 <= row['time'] <= min(stop + high, cap) + 1e-6
                and row.get('motion')]
        times = [row['time'] for row in rows]
        output[label] = {'requested_relative_window_seconds': [low, high],
                         'observed_relative_window_seconds': [rows[0]['time'] - stop, rows[-1]['time'] - stop] if rows else None,
                         'actor_world_xy': trajectory([row['position'][:2] for row in rows], times),
                         'bones': {}}
        for bone in BONES:
            world = [world_bone(row, bone) for row in rows]
            output[label]['bones'][bone] = {
                'component': trajectory([row['motion']['bones_component_space'][bone]['translation'] for row in rows], times),
                'world_xy': trajectory([point[:2] for point in world], times),
                'world_z': trajectory([[point[2]] for point in world], times)}
    return output


def open_run(directory, fps):
    path = directory / f'sparrow-stop-diagnostic-{fps}.json'
    report = load(path)
    analysis_path = directory / 'review/motion-analysis.json'
    existing = load(analysis_path) if analysis_path.is_file() else None
    if existing and existing.get('source_report_sha256') != review.digest(path):
        raise ValueError('Existing motion analysis belongs to a different report: ' + str(analysis_path))
    analysis_cases = {case['name']: case for case in (existing or {}).get('cases', [])}
    cases = {}
    for case in report.get('cases', []):
        data = case.get('data', {})
        descriptor = data.get('full_simulation_trace')
        if not descriptor:
            raise ValueError('Missing full trace: ' + case['name'])
        trace_path = review.resolve_file(descriptor['path'], directory)
        if review.digest(trace_path) != descriptor['sha256']:
            raise ValueError('Trace hash mismatch: ' + str(trace_path))
        trace = load(trace_path)
        samples = trace['samples']
        if trace['fps'] != fps or descriptor['samples'] != len(samples):
            raise ValueError('Trace metadata mismatch: ' + str(trace_path))
        edge_rows = review.edges(samples)
        legs = list(data.get('legs', []))
        if data.get('held_input'):
            legs.append(dict(data['held_input'], label='held-input-release'))
        matched = {}
        for index, leg in enumerate(legs):
            next_started = legs[index + 1]['started'] if index + 1 < len(legs) else None
            measured = review.summarize_leg(leg, samples, edge_rows, fps, next_started)
            previous = next((row for row in analysis_cases.get(case['name'], {}).get('legs', [])
                             if row['label'] == measured['label']), None)
            matched[measured['label']] = {'leg': leg, 'measured': measured,
                'existing_analysis_leg_available': previous is not None,
                'existing_analysis_step_summary_matches_recomputed': previous['stop_transition_minus_025_to_plus_030_seconds'] == measured['stop_transition_minus_025_to_plus_030_seconds'] if previous else None,
                'displacement': displacement_evidence(samples, leg, next_started)}
        cases[case['name']] = {'data': data, 'legs': matched, 'trace_samples': len(samples),
                               'trace_path': str(trace_path), 'trace_sha256': descriptor['sha256']}
    return {'directory': directory, 'report': report, 'report_path': path,
            'report_sha256': review.digest(path), 'cases': cases,
            'existing_analysis': {'path': str(analysis_path), 'sha256': review.digest(analysis_path)} if existing else None}


def measured_comparison(before, after):
    first, second = before['measured'], after['measured']
    a = first['stop_transition_minus_025_to_plus_030_seconds']
    b = second['stop_transition_minus_025_to_plus_030_seconds']
    cloth = {}
    for key in ('per_frame_max_displacement_cm', 'per_frame_rms_speed_cm_per_second', 'per_frame_max_speed_cm_per_second'):
        cloth[key] = change(a['cloth_component_space'][key]['maximum'], b['cloth_component_space'][key]['maximum'])
    windows = {}
    for key, window in first['residual_motion_windows'].items():
        other = second['residual_motion_windows'][key]
        windows[key] = {'before_observed_interval_seconds': window['observed_interval_seconds'],
                        'after_observed_interval_seconds': other['observed_interval_seconds'],
                        'before_full_window': window['full_window_observed_within_one_frame'],
                        'after_full_window': other['full_window_observed_within_one_frame'],
                        'sampled_cloth_rms_speed_cm_per_second': change(
                            window['measurements']['cloth_component_space']['per_frame_rms_speed_cm_per_second']['rms'],
                            other['measurements']['cloth_component_space']['per_frame_rms_speed_cm_per_second']['rms'])}
    paths = {}
    for label, current in before['displacement'].items():
        new = after['displacement'][label]
        paths[label] = {'observed_relative_seconds_before': current['observed_relative_window_seconds'],
                        'observed_relative_seconds_after': new['observed_relative_window_seconds'], 'bones': {},
                        'actor_world_xy': {key: change((current['actor_world_xy'] or {}).get(key), (new['actor_world_xy'] or {}).get(key))
                                           for key in ('net_displacement_cm', 'path_length_cm', 'maximum_frame_step_cm', 'maximum_frame_speed_cm_per_second')}}
        for bone in BONES:
            paths[label]['bones'][bone] = {space: {key: change((current['bones'][bone][space] or {}).get(key),
                                                                 (new['bones'][bone][space] or {}).get(key))
                for key in ('net_displacement_cm', 'path_length_cm', 'maximum_frame_step_cm', 'maximum_frame_speed_cm_per_second', 'maximum_distance_from_first_sample_cm')}
                for space in ('component', 'world_xy', 'world_z')}
    return {'maximum_bone_frame_step_cm': {bone: change(a['bones_component_space'][bone]['translation_step_cm']['maximum'],
                                                        b['bones_component_space'][bone]['translation_step_cm']['maximum']) for bone in BONES},
            'maximum_bone_frame_rotation_degrees': {bone: change(a['bones_component_space'][bone]['rotation_step_degrees']['maximum'],
                                                                b['bones_component_space'][bone]['rotation_step_degrees']['maximum']) for bone in BONES},
            'stop_heading_error_degrees': change(first['stop_actor_vs_last_motion_error_degrees'], second['stop_actor_vs_last_motion_error_degrees']),
            'maximum_stop_actor_yaw_frame_step_degrees': change(a['actor_yaw_step_degrees']['maximum'], b['actor_yaw_step_degrees']['maximum']),
            'maximum_post_stop_heading_error_degrees': change(first['post_stop_actor_vs_last_motion_error_degrees']['maximum'], second['post_stop_actor_vs_last_motion_error_degrees']['maximum'])
                if first['post_stop_actor_vs_last_motion_error_degrees'] and second['post_stop_actor_vs_last_motion_error_degrees'] else None,
            'stop_transition_sampled_cloth': cloth, 'residual_cloth_motion_windows': windows,
            'complete_bone_trajectory_and_world_displacement': paths,
            'before': {'measured': first, 'displacement': before['displacement'],
                       'existing_analysis_step_summary_matches_recomputed': before['existing_analysis_step_summary_matches_recomputed']},
            'after': {'measured': second, 'displacement': after['displacement'],
                      'existing_analysis_step_summary_matches_recomputed': after['existing_analysis_step_summary_matches_recomputed']}}


def capture_pairs(before, after, case):
    def map_captures(run):
        result = {}
        shots = [shot for shot in run['report'].get('screenshots', []) if shot.get('case') == case]
        for label, entry in run['cases'][case]['legs'].items():
            leg = entry['leg']
            for capture in leg.get('captures', []):
                if not shots:
                    continue
                shot = min(shots, key=lambda row: abs(row['state']['time'] - capture['time']))
                if abs(shot['state']['time'] - capture['time']) > 1e-5:
                    continue
                result[(label, capture['phase'])] = {'shot': shot, 'relative_seconds': shot['state']['time'] - leg['stopped']}
        return result
    first, second = map_captures(before), map_captures(after)
    return [(key, first[key], second[key]) for key in first if key in second]


def derive_media(before, after, cases, output, fps, make_gif):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    except OSError:
        font = ImageFont.load_default()
    sources, products, metadata = {}, [], []
    for case in cases:
        pairs = capture_pairs(before, after, case)
        frames, times = [], []
        for index, (key, old, new) in enumerate(pairs):
            images, rows = [], []
            for label, value, run in (('BEFORE', old, before), ('AFTER', new, after)):
                shot = value['shot']
                path = review.resolve_file(shot['image'], run['directory'])
                sha = review.digest(path)
                if sha != shot['sha256']:
                    raise ValueError('Native PNG hash mismatch: ' + str(path))
                with Image.open(path) as image:
                    raw = image.convert('RGB')
                images.append(raw)
                sources[str(path)] = {'path': str(path), 'sha256': sha, 'dimensions': [raw.width, raw.height]}
                rows.append({'variant': label, 'image': str(path), 'sha256': sha,
                             'simulation_time': shot['state']['time'], 'relative_to_actual_stop_seconds': value['relative_seconds']})
            width, height = max(image.width for image in images), max(image.height for image in images)
            frame = Image.new('RGB', (2 * width, height + 52), '#12151c')
            draw = ImageDraw.Draw(frame)
            for col, (image, row) in enumerate(zip(images, rows)):
                frame.paste(image, (col * width, 52))
                draw.text((col * width + 5, 5), f"{row['variant']} {case} {key[1]}", fill='#efeff2', font=font)
                draw.text((col * width + 5, 27), f"actual stop offset {row['relative_to_actual_stop_seconds']:+.4f} s", fill='#efeff2', font=font)
            target = output / f'{case}-pair-{index:02}.png'
            frame.save(target)
            frames.append(frame)
            times.append(new['relative_seconds'])
            products.append(str(target))
            state_delta = {}
            for field in ('view_location', 'view_rotation', 'position'):
                a, b = old['shot']['state'].get(field), new['shot']['state'].get(field)
                if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
                    state_delta[field] = [y - x for x, y in zip(a, b)]
            metadata.append({'case': case, 'leg': key[0], 'phase': key[1], 'pair': str(target), 'sources': rows,
                             'after_minus_before_stop_offset_seconds': new['relative_seconds'] - old['relative_seconds'],
                             'camera_and_pawn_state_after_minus_before': state_delta,
                             'same_instant_or_framing_asserted': False})
        for start in range(0, len(frames), 3):
            batch = frames[start:start + 3]
            width, height = max(frame.width for frame in batch), max(frame.height for frame in batch)
            sheet = Image.new('RGB', (width, height * len(batch)), '#12151c')
            for index, frame in enumerate(batch):
                sheet.paste(frame, (0, index * height))
            target = output / f'{case}-comparison-sheet-{start // 3 + 1}.png'
            sheet.save(target)
            products.append(str(target))
        if make_gif and len(frames) > 1:
            if any(b <= a for a, b in zip(times, times[1:])):
                raise ValueError('Paired capture timing must increase within each case')
            durations = [max(10, round((b - a) * 100) * 10) for a, b in zip(times, times[1:])]
            durations.append(max(10, round(100 / fps) * 10))
            target = output / f'{case}-before-after-sampled.gif'
            frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0)
            products.append({'path': str(target), 'after_relative_simulation_seconds': times,
                             'playback_milliseconds': durations,
                             'timing_source': 'AFTER capture intervals; BEFORE stop offset differences are labeled on every frame.'})
    for source in sources.values():
        if review.digest(Path(source['path'])) != source['sha256']:
            raise ValueError('Native source image changed during derivation')
    return {'native_sources': list(sources.values()), 'pairs': metadata, 'products': products,
            'raw_images_modified': False, 'cropped': False, 'image_scale': 1,
            'camera_pawn_and_stop_relative_times_forced_to_match': False,
            'continuous_video': False, 'gif_limitations': 'Palette quantization and 10 ms time resolution; no interpolated frames.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--fps', type=int, choices=(30, 60), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', dest='media_cases', help='Media cases only, repeat at most four times; all cases are measured.')
    parser.add_argument('--no-media', action='store_true')
    parser.add_argument('--gif', action='store_true', help='Also derive sampled comparison GIFs.')
    args = parser.parse_args()
    before_dir, after_dir, output = args.before.resolve(), args.after.resolve(), args.output.resolve()
    if before_dir == after_dir or output in (before_dir, after_dir) or output.is_relative_to(before_dir) or output.is_relative_to(after_dir):
        raise ValueError('Use distinct before/after runs and a separate output directory')
    media_cases = args.media_cases or list(DEFAULT_CASES)
    if len(media_cases) > 4 or len(set(media_cases)) != len(media_cases):
        raise ValueError('Select at most four distinct cases for derived images')
    before, after = open_run(before_dir, args.fps), open_run(after_dir, args.fps)
    matched = sorted(before['cases'].keys() & after['cases'].keys())
    comparisons = []
    for case in matched:
        old, new = before['cases'][case], after['cases'][case]
        legs = old['legs'].keys() & new['legs'].keys()
        comparisons.append({'case': case, 'before_trace': {'path': old['trace_path'], 'sha256': old['trace_sha256']},
                            'after_trace': {'path': new['trace_path'], 'sha256': new['trace_sha256']},
                            'unmatched_before_legs': sorted(old['legs'].keys() - new['legs'].keys()),
                            'unmatched_after_legs': sorted(new['legs'].keys() - old['legs'].keys()),
                            'legs': [{'label': label, **measured_comparison(old['legs'][label], new['legs'][label])}
                                     for label in sorted(legs)]})
    if any(case not in matched for case in media_cases):
        raise ValueError('Requested media case missing from a run')
    findings = []
    for case in comparisons:
        for leg in case['legs']:
            head = leg['maximum_bone_frame_step_cm']['head']
            pelvis = leg['complete_bone_trajectory_and_world_displacement']['post_stop_000_to_030']['bones']['pelvis']['world_xy']['path_length_cm']
            findings.append({'case': case['case'], 'leg': leg['label'],
                             'head_peak_step_cm': head,
                             'post_stop_first_030_seconds_pelvis_world_xy_path_cm': pelvis,
                             'heading_error_degrees': leg['stop_heading_error_degrees'],
                             'interpretation': 'A smaller single-frame step alone does not establish a natural stop; inspect total body displacement and native play-view pairs.'})
    result = {'fps': args.fps, 'user_style_acceptance': False, 'style_acceptance_automatically_decided': False,
              'measurements_only': True, 'before_report': {'path': str(before['report_path']), 'sha256': before['report_sha256'],
                                                          'runner_passed': before['report'].get('passed'), 'existing_analysis': before['existing_analysis']},
              'after_report': {'path': str(after['report_path']), 'sha256': after['report_sha256'],
                               'runner_passed': after['report'].get('passed'), 'existing_analysis': after['existing_analysis']},
              'matched_cases': len(matched), 'unmatched_before_cases': sorted(before['cases'].keys() - after['cases'].keys()),
              'unmatched_after_cases': sorted(after['cases'].keys() - before['cases'].keys()),
              'comparisons': comparisons, 'findings_measurement': findings,
              'interpretation_limits': [
                  'A blend may spread the same large pose offset across frames. Component/world trajectories, net offsets and path lengths are retained to expose that possibility.',
                  'Post-stop foot world motion includes foot lifting and animation pose changes; these statistics alone do not classify planted-foot sliding.',
                  'World displacement separates actor translation from local pose motion but still includes actor facing changes.',
                  'The same physical cloth particles are matched only within a run, never by index across before/after simulation histories.',
                  'Missing residual intervals remain incomplete. The next movement input caps each approach-leg observation.',
                  'Pending teleport flags are snapshots, not a history of consumed cloth solver resets.',
                  'Fixed FPS and matched case/phase do not guarantee identical camera, pawn position or stop-relative sample times. Media metadata records differences.',
                  'Aim, combat recovery, user style approval and protected baseline preservation are separate parent-level checks.']}
    output.mkdir(parents=True, exist_ok=True)
    if not args.no_media:
        result['media_derivation'] = derive_media(before, after, media_cases, output, args.fps, args.gif)
    target = output / 'stop-fix-comparison.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'comparison': str(target), 'matched_cases': len(matched),
                      'matched_stops': len(findings), 'user_style_acceptance': False,
                      'derived_media_cases': [] if args.no_media else media_cases}, ensure_ascii=False))


if __name__ == '__main__':
    main()
