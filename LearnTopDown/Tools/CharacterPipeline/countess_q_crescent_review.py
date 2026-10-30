"""Compare the previous small Q preview with the new Q at the unchanged camera."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'Saved/QA/CharacterPipeline/countess-q-crescent-20261015'
OLD = ROOT/'Saved/QA/CharacterPipeline/countess-q-presentation-20261015/compare-60-04'
NEW = BASE/'compare-60-02'
DEST = BASE/'review'
DEST.mkdir(exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
before = json.loads((OLD/'countess-q-comparison-60.json').read_text())
after = json.loads((NEW/'countess-q-comparison-60.json').read_text())
manifest = []
frames = []

for phase in ('prepare', 'arrival', 'slash', 'afterimage', 'settle', 'recovery'):
    shots = [next(s for s in report['screenshots'] if f'Q-enhanced-{phase}-' in s['image'])
             for report in (before, after)]
    a, b = shots
    assert a['width'] == b['width'] and a['height'] == b['height']
    for key in ('view_location', 'view_rotation'):
        assert max(abs(x-y) for x, y in zip(a['state'][key], b['state'][key])) < .05
    width, height = a['width'], a['height']
    page = Image.new('RGB', (width*2, height+34), '#12151c')
    draw = ImageDraw.Draw(page)
    counts = []
    for column, (label, shot) in enumerate(zip(('Previous small Q', 'New large crescent Q'), shots)):
        raw = Image.open(shot['image']).convert('RGB')
        page.paste(raw, (column*width, 34))
        draw.text((column*width+8, 7), label+' / '+phase, fill='#efeff2', font=font)
        pixels = np.array(raw).astype(float)
        roi = pixels[int(height*.08):int(height*.73), int(width*.20):int(width*.85)]
        mask = (roi[:, :, 0]>180) & (roi[:, :, 0]>roi[:, :, 1]*1.25) & (roi[:, :, 0]>roi[:, :, 2]*1.25)
        counts.append(int(mask.sum()))
    path = DEST/f'previous-vs-crescent-{phase}.png'
    page.save(path)
    frames.append(page)
    manifest.append({'phase': phase, 'pair': str(path), 'sources': shots,
                     'bright_red_pixels_in_identical_gameplay_roi': counts,
                     'camera_matches': True, 'enlargement': 1.0})

frames[0].save(DEST/'previous-vs-crescent-stages.gif', save_all=True, append_images=frames[1:],
               duration=[260, 180, 260, 300, 440, 1000], loop=0)
(DEST/'comparison.json').write_text(json.dumps({'pairs': manifest,
    'raw_images_modified': False, 'cropped': False, 'zoom_changed': False,
    'gif_kind': 'stage comparison; not real-time playback',
    'pixel_measurement_is_not_user_style_approval': True}, indent=2), encoding='utf-8')

motion = BASE/'motion-60-01/countess-q-comparison-60.json'
if motion.is_file():
    report = json.loads(motion.read_text())
    if report['passed']:
        frames = []
        times = []
        cases = {case['name']: case for case in report['cases']}
        for index in range(16):
            shots = [next(s for s in report['screenshots'] if f'Q-motion-{mode}-{index:02}-' in s['image'])
                     for mode in ('original', 'enhanced')]
            ca = cases['Q_motion_original']['data']['frames'][index]
            cb = cases['Q_motion_enhanced']['data']['frames'][index]
            assert abs(ca['elapsed']-cb['elapsed']) <= 1/60
            assert max(abs(x-y) for x, y in zip(ca['camera'], cb['camera'])) < .05
            assert max(abs(x-y) for x, y in zip(ca['pawn'], cb['pawn'])) < .05
            width, height = shots[0]['width'], shots[0]['height']
            page = Image.new('RGB', (width*2, height+34), '#12151c')
            draw = ImageDraw.Draw(page)
            for column, (label, shot) in enumerate(zip(('Original Q', 'New large crescent Q'), shots)):
                page.paste(Image.open(shot['image']).convert('RGB'), (column*width, 34))
                draw.text((column*width+8, 7), label+f" / {cb['elapsed']:.2f}s", font=font, fill='#efeff2')
            frames.append(page)
            times.append(cb['elapsed'])
        durations = [max(10, round((b-a)*1000)) for a, b in zip(times, times[1:])] + [350]
        frames[0].save(DEST/'Q-gameplay-sampled-timing.gif', save_all=True, append_images=frames[1:],
                       duration=durations, loop=0)
        (DEST/'motion-derivation.json').write_text(json.dumps({
            'source_report': str(motion), 'source_simulation_seconds': times,
            'playback_frame_milliseconds': durations, 'last_frame_hold_ms': 350,
            'native_viewport_unchanged': True, 'cropped': False, 'enlargement': 1.0,
            'capture_kind': 'actual PIE screenshots sampled every 50ms; pauses used for PNG capture',
            'continuous_video_recording': False, 'simulation_timing_preserved_between_samples': True},
            indent=2), encoding='utf-8')
print(json.dumps({'review': str(DEST), 'matched_previous_preview_pairs': len(manifest)}))
