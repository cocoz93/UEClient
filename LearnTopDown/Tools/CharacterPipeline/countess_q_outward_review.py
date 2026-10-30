"""Pair immutable actual PIE screenshots of curve and straight-cut variants."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--fps', type=int, choices=(30,60), required=True)
args = parser.parse_args()
directory = args.directory.resolve()
report = json.loads((directory/f'countess-q-comparison-{args.fps}.json').read_text())
assert report['passed']
shots = report['screenshots']
cases = {c['name']:c for c in report['cases']}
motion = 'Q_motion_original' in cases
if motion:
    labels = [f'{i:02}' for i in range(16)]
    before_case, after_case = 'Q_motion_original', 'Q_motion_enhanced'
    before_pattern, after_pattern = 'Q-motion-original-', 'Q-motion-enhanced-'
else:
    labels = ['prepare','arrival','slash','afterimage','settle','recovery','return']
    before_case, after_case = 'Q_original', 'Q_enhanced'
    before_pattern, after_pattern = 'Q-original-', 'Q-enhanced-'
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
out = directory/'review'
out.mkdir(exist_ok=True)
pairs, images = [], []
for label in labels:
    selected = []
    for case, pattern in ((before_case,before_pattern), (after_case,after_pattern)):
        shot = next(s for s in shots if s['case']==case and pattern+label+'-' in Path(s['image']).name)
        path = Path(shot['image'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==shot['sha256']
        selected.append(shot)
    assert selected[0]['width']==selected[1]['width'] and selected[0]['height']==selected[1]['height']
    width,height = selected[0]['width'],selected[0]['height']
    page = Image.new('RGB',(width*2,height+32),'#14151a')
    draw = ImageDraw.Draw(page)
    for index, shot in enumerate(selected):
        draw.text((index*width+8,5), ('Previous curved Q' if index==0 else 'New outward cuts')+' / '+label, font=font, fill='white')
        page.paste(Image.open(shot['image']).convert('RGB'),(index*width,32))
        images.append({'path':shot['image'],'sha256':shot['sha256']})
    path = out/f'pair-{label}.png'
    page.save(path)
    pairs.append((page, {'path':str(path),'source_images':selected}))
sheets = []
for offset in range(0,len(pairs),4):
    selected = pairs[offset:offset+4]
    width,height = selected[0][0].size
    sheet = Image.new('RGB',(width,height*len(selected)),'#14151a')
    for index,(page,_) in enumerate(selected):
        sheet.paste(page,(0,index*height))
    path = out/f'sheet-{offset//4+1:02}.png'
    sheet.save(path)
    sheets.append({'path':str(path),'pairs':[p[1] for p in selected]})
gif = out/'Q-curve-vs-outward-sampled.gif'
pairs[0][0].save(gif,save_all=True,append_images=[p[0] for p in pairs[1:]],loop=0,
    duration=([50]*15+[650]) if motion else [100,100,100,120,160,220,650])
(out/'manifest.json').write_text(json.dumps({'source_report':str(directory/f'countess-q-comparison-{args.fps}.json'),
    'images':images,'sheets':sheets,'gif':str(gif),'native_raw_images_modified':False,
    'continuous_recording':False,'camera_or_image_crop_changed':False,'user_style_approval':False},indent=2))
print(json.dumps({'pairs':len(pairs),'sheets':len(sheets),'gif':str(gif)}))
