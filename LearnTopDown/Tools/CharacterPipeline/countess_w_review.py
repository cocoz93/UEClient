"""Derive labeled full-viewport W comparisons from unchanged native PNGs."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--fps', type=int, choices=(30, 60), required=True)
args = parser.parse_args()
directory = args.directory.resolve()
report = json.loads((directory / f'countess-w-comparison-{args.fps}.json').read_text(encoding='utf-8'))
assert report['passed'] and len(report['cases']) == 10
shots = report['screenshots']
cases = {c['name']: c['data'] for c in report['cases']}
out = directory / 'review'
out.mkdir(exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
frames, times, pairs = [], [], []
for index in range(16):
    pair = [next(s for s in shots if f'W-{name}-{index:02}-' in s['image']) for name in ('original', 'dense')]
    left, right = [cases[name]['frames'][index] for name in ('W_original', 'W_dense')]
    assert abs(left['elapsed'] - right['elapsed']) <= 1 / args.fps
    for field in ('pawn', 'camera'):
        assert max(abs(x-y) for x, y in zip(left[field], right[field])) < .05
    for field in ('view_location', 'view_rotation'):
        assert max(abs(x-y) for x, y in zip(pair[0]['state'][field], pair[1]['state'][field])) < .05
    w, h = pair[0]['width'], pair[0]['height']
    assert [w, h] == [pair[1]['width'], pair[1]['height']]
    page = Image.new('RGB', (w*2, h+34), '#12151c')
    draw = ImageDraw.Draw(page)
    for col, (label, shot) in enumerate(zip(('Previous W', 'Denser original-texture W'), pair)):
        page.paste(Image.open(shot['image']).convert('RGB'), (col*w, 34))
        draw.text((col*w+8, 7), label+f" / {right['elapsed']:.2f}s", font=font, fill='#efeff2')
    path = out / f'pair-{index:02}.png'
    page.save(path)
    frames.append(page)
    times.append(right['elapsed'])
    pairs.append({'pair': str(path), 'sources': pair})
for start in range(0, 16, 4):
    page = Image.new('RGB', (frames[0].width, frames[0].height*4), '#12151c')
    for row, frame in enumerate(frames[start:start+4]):
        page.paste(frame, (0, row*frame.height))
    page.save(out / f'comparison-sheet-{start//4+1}.png')
other = [s for s in shots if not any(f'W-{name}-{index:02}-' in s['image']
                                   for name in ('original', 'dense') for index in range(16))]
for start in range(0, len(other), 4):
    batch = other[start:start+4]
    w, h = batch[0]['width'], batch[0]['height']
    page = Image.new('RGB', (w*2, (h+30)*2), '#12151c')
    draw = ImageDraw.Draw(page)
    for index, shot in enumerate(batch):
        x, y = (index % 2)*w, (index // 2)*(h+30)
        page.paste(Image.open(shot['image']).convert('RGB'), (x, y+30))
        draw.text((x+4, y+5), Path(shot['image']).stem, font=font, fill='#efeff2')
    page.save(out / f'other-sheet-{start//4+1}.png')
durations = [round((b-a)*1000) for a, b in zip(times, times[1:])] + [350]
frames[0].save(out / 'W-before-after-sampled.gif', save_all=True, append_images=frames[1:],
               duration=durations, loop=0)
(out / 'derivation.json').write_text(json.dumps({'pairs': pairs,
    'camera_pawn_and_simulation_times_match': True, 'cropped': False, 'enlargement': 1,
    'simulation_seconds': times, 'playback_milliseconds': durations,
    'actual_PIE_samples': True, 'continuous_video': False, 'raw_images_modified': False}, indent=2), encoding='utf-8')
print(json.dumps({'paired_frames': 16, 'other_native_images': len(other), 'review': str(out)}))
