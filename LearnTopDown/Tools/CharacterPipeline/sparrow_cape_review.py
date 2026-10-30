"""Derive unchanged-size cape comparison sheets and sampled GIFs from native PNGs.

All source hashes are checked before and after; no source PNG is modified. This
utility creates review media and does not decide visual or user acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = args.comparison.resolve()
    comparison = json.loads(source.read_text(encoding='utf-8-sig'))
    assert comparison['passed'] and comparison.get('capture_pairs'), 'Successful paired comparison is required.'
    output = args.output.resolve() if args.output else source.parent / 'review'
    project = Path(__file__).resolve().parents[2]
    if not output.is_relative_to(project / 'Saved/QA'):
        raise ValueError('Derived cape media must remain inside project Saved/QA.')
    output.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source)
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    except OSError:
        font = ImageFont.load_default()
    pairs = comparison['capture_pairs']
    images, sources = {}, []
    for pair in pairs:
        for mode in ('before', 'after'):
            shot = pair[mode]
            path = Path(shot['image'])
            actual = digest(path)
            assert actual == shot['sha256'], str(path)
            with Image.open(path) as image:
                assert image.format == 'PNG' and image.size == (shot['width'], shot['height']), str(path)
                image.verify()
            with Image.open(path) as image:
                images[str(path)] = image.convert('RGB')
            sources.append({'case': pair['case'], 'capture': pair['capture'], 'variant': mode,
                            'path': str(path), 'sha256': actual, 'width': shot['width'], 'height': shot['height'],
                            'simulation_time_seconds': shot['state']['time']})

    def title(pair, mode):
        state = pair[mode]['state']
        times = state.get('cape_observation', {})
        age = times.get('seconds_since_spawn_processed')
        age_text = f'{age:.3f}' if age is not None else 'n/a'
        return f'{mode.upper()} | {pair["case"]} | world={state["time"]:.3f}s | spawn age={age_text}s'

    def pair_frame(pair):
        a = images[pair['before']['image']]
        b = images[pair['after']['image']]
        width, height = max(a.width, b.width), max(a.height, b.height)
        frame = Image.new('RGB', (width * 2, height + 48), '#11151d')
        frame.paste(a, (0, 48))
        frame.paste(b, (width, 48))
        draw = ImageDraw.Draw(frame)
        draw.text((5, 3), title(pair, 'before'), fill='#eeeeee', font=font)
        draw.text((width + 5, 3), title(pair, 'after'), fill='#eeeeee', font=font)
        draw.text((5, 25), pair['capture'] + ' | native scale 1:1 | sampled frames, not continuous video', fill='#c8bca4', font=font)
        return frame

    def representative(pair):
        case, label = pair['case'], pair['capture']
        if case in ('idle_flutter', 'short_reverse_110', 'held_near_release'):
            return True
        if case == 'direction_0':
            return any(text in label for text in ('pre-stop', '-stop-', 'after-030', 'after-070'))
        if case == 'direction_270':
            return any(text in label for text in ('pre-stop', '-stop-', 'after-030'))
        if case.startswith('combat_'):
            return '-recovery-' not in label
        return case == 'numeric_owner_cleanup'

    selected = [pair for pair in pairs if representative(pair)]
    products = []
    for start in range(0, len(selected), 4):
        group = selected[start:start + 4]
        frames = [pair_frame(pair) for pair in group]
        width = max(frame.width for frame in frames)
        height = sum(frame.height for frame in frames)
        sheet = Image.new('RGB', (width, height), '#11151d')
        offset = 0
        for frame in frames:
            sheet.paste(frame, (0, offset))
            offset += frame.height
        path = output / f'cape-paired-sheet-{start // 4 + 1:02}.png'
        sheet.save(path)
        products.append({'path': str(path), 'sha256': digest(path), 'kind': 'paired_sheet', 'pairs': len(group),
                         'width': width, 'height': height,
                         'captures': [{'case': pair['case'], 'capture': pair['capture']} for pair in group]})

    for case, filename in (('idle_flutter', 'cape-idle-sampled.gif'), ('direction_0', 'cape-run-stop-sampled.gif')):
        group = [pair for pair in pairs if pair['case'] == case]
        group.sort(key=lambda pair: pair['before']['state']['time'])
        if len(group) < 2:
            continue
        frames = [pair_frame(pair) for pair in group]
        width, height = max(frame.width for frame in frames), max(frame.height for frame in frames)
        padded = []
        for frame in frames:
            canvas = Image.new('RGB', (width, height), '#11151d')
            canvas.paste(frame, (0, 0))
            padded.append(canvas)
        old_times = [pair['before']['state']['time'] for pair in group]
        new_times = [pair['after']['state']['time'] for pair in group]
        # Approximate both timelines only if their measured intervals differ. Preserve both originals.
        durations = [max(10, round(((ob - oa + nb - na) / 2) * 100) * 10)
                     for oa, ob, na, nb in zip(old_times, old_times[1:], new_times, new_times[1:])]
        durations.append(500)
        path = output / filename
        padded[0].save(path, save_all=True, append_images=padded[1:], duration=durations, loop=0)
        products.append({'path': str(path), 'sha256': digest(path), 'kind': 'sampled_gif', 'case': case,
                         'frames': len(group), 'width': width, 'height': height,
                         'before_simulation_times_seconds': old_times, 'after_simulation_times_seconds': new_times,
                         'playback_milliseconds': durations, 'artificial_final_frame_hold_milliseconds': 500,
                         'continuous_video': False,
                         'timing': 'Mean of actual before/after sample intervals rounded to GIF 10ms units. Intermediate frames were not captured.',
                         'color_limit': 'GIF palette quantization applies. Native PNGs are authoritative for color.'})
    assert digest(source) == source_hash, 'Source comparison changed while generating media.'
    for item in sources:
        assert digest(item['path']) == item['sha256'], item['path']
    result = {'passed': True, 'source_comparison': str(source), 'source_comparison_sha256': source_hash,
              'style_approval': False, 'native_sources_checked': len(sources), 'native_paired_captures': len(pairs),
              'selected_pairs': len(selected), 'sources': sources, 'products': products,
              'raw_images_modified': False, 'cropped': False, 'image_scale': 1, 'continuous_video': False,
              'review_limit': 'Generated sheets/GIFs have not themselves been visually reviewed by this utility.'}
    target = output / 'cape-review-media.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'report': str(target), 'paired_captures': len(pairs), 'selected_pairs': len(selected), 'products': len(products)}))


if __name__ == '__main__':
    main()
