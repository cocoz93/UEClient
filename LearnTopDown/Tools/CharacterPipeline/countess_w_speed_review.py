"""Pair eight equal real-time W samples; preserve and hash every native source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont

parser=argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
parser.add_argument('--fps',type=int,choices=(30,60),required=True)
args=parser.parse_args()
directory=args.directory.resolve()
report_path=directory/f'countess-w-speed-comparison-{args.fps}.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
assert report['passed'] and len(report['cases'])==10
cases={c['name']:c['data'] for c in report['cases']}
out=directory/'review'
out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
frames,pairs,sources=[],[],[]
for index in range(8):
    selected=[next(s for s in report['screenshots'] if f'W-rate-{rate}-{index:02}-' in Path(s['image']).name)
              for rate in ('1','1.5')]
    a,b=[cases[name]['frames'][index] for name in ('W_rate_1','W_rate_1_5')]
    assert abs(a['elapsed']-b['elapsed'])<=2/args.fps+.0001
    for field in ('pawn','camera'):
        assert max(abs(x-y) for x,y in zip(a[field],b[field]))<.05
    assert all([s['width'],s['height']]==[700,330] for s in selected)
    page=Image.new('RGB',(1400,364),'#13151c')
    draw=ImageDraw.Draw(page)
    for col,(shot,label,data) in enumerate(zip(selected,('Previous W 1x','Faster W 1.5x'),(a,b))):
        path=Path(shot['image'])
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==shot['sha256']
        with Image.open(path) as image:
            assert image.size==(700,330)
            page.paste(image.convert('RGB'),(700*col,34))
        draw.text((700*col+8,8),label+f" | actual time {data['elapsed']:.3f}s",font=font,fill='white')
        sources.append({'path':str(path),'sha256':digest})
    pair=out/f'W-speed-pair-{index:02}.png'
    page.save(pair)
    pairs.append({'path':str(pair),'sha256':hashlib.sha256(pair.read_bytes()).hexdigest(),'sources':selected})
    frames.append(page)
sheets=[]
for start in (0,4):
    sheet=Image.new('RGB',(1400,364*4),'#13151c')
    for row,page in enumerate(frames[start:start+4]):
        sheet.paste(page,(0,row*364))
    path=out/f'W-speed-sheet-{start//4+1:02}.png'
    sheet.save(path)
    sheets.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
times=[f['elapsed'] for f in cases['W_rate_1_5']['frames']]
durations=[max(30,round((b-a)*1000)) for a,b in zip(times,times[1:])]+[500]
gif=out/'W-speed-before-after-sampled.gif'
frames[0].save(gif,save_all=True,append_images=frames[1:],duration=durations,loop=0)
manifest={'report':{'path':str(report_path),'sha256':hashlib.sha256(report_path.read_bytes()).hexdigest()},
          'pairs':pairs,'reviewed_source_candidates':sources,'sheets':sheets,'gif':str(gif),
          'actual_time_comparison':True,'animation_phase_is_intentionally_different':True,
          'native_source_images_modified':False,'image_crop_or_scale_changed':False,
          'continuous_video':False,'human_visual_review_completed':False,'user_style_approval':False}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'pairs':8,'native_sources':16,'sheets':2,'review':str(out)}))
