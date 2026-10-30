"""Make full-viewport comparison evidence without cropping or enlarging gameplay."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Saved/QA/CharacterPipeline/countess-q-dual-20261015'
SOURCE=BASE/'motion-60-02/countess-q-comparison-60.json'
report=json.loads(SOURCE.read_text())
assert report['passed'] and len(report['cases'])==9
DEST=BASE/'review-final'
DEST.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
cases={c['name']:c for c in report['cases']}
shots=report['screenshots']
frames=[]
manifest=[]
times=[]
for index in range(16):
    pair=[next(s for s in shots if f'Q-motion-{name}-{index:02}-' in s['image']) for name in ('legacy','enhanced')]
    a,b=[cases['Q_motion_'+name]['data']['frames'][index] for name in ('legacy','enhanced')]
    assert abs(a['elapsed']-b['elapsed'])<=1/60
    for field in ('pawn','camera'):
        assert max(abs(x-y) for x,y in zip(a[field],b[field]))<.05
    assert pair[0]['width']==pair[1]['width'] and pair[0]['height']==pair[1]['height']
    w,h=pair[0]['width'],pair[0]['height']
    page=Image.new('RGB',(w*2,h+34),'#12151c')
    draw=ImageDraw.Draw(page)
    for col,(label,shot) in enumerate(zip(('Previous crescent','Dual blade sweep'),pair)):
        page.paste(Image.open(shot['image']).convert('RGB'),(col*w,34))
        draw.text((col*w+8,7),label+f" / {b['elapsed']:.2f}s",font=font,fill='#efeff2')
    path=DEST/f'comparison-{index:02}.png'
    page.save(path)
    frames.append(page)
    times.append(b['elapsed'])
    manifest.append({'pair':str(path),'images':[{'path':p['image'],'sha256':p['sha256']} for p in pair]})
for start in range(0,16,4):
    page=Image.new('RGB',(frames[0].width,frames[0].height*4),'#12151c')
    for row,frame in enumerate(frames[start:start+4]):page.paste(frame,(0,row*frame.height))
    page.save(DEST/f'motion-sheet-{start//4+1}.png')
durations=[round((b-a)*1000) for a,b in zip(times,times[1:])]+[350]
frames[0].save(DEST/'Q-before-after-sampled.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0)
other=[s for s in shots if s['case'] not in ('Q_motion_legacy','Q_motion_enhanced')]
for start in range(0,len(other),4):
    batch=other[start:start+4]
    w,h=batch[0]['width'],batch[0]['height']
    page=Image.new('RGB',(w*2,(h+30)*2),'#12151c');draw=ImageDraw.Draw(page)
    for i,shot in enumerate(batch):
        x,y=(i%2)*w,(i//2)*(h+30)
        page.paste(Image.open(shot['image']).convert('RGB'),(x,y+30))
        draw.text((x+5,y+5),Path(shot['image']).stem,font=font,fill='#efeff2')
    page.save(DEST/f'other-sheet-{start//4+1}.png')
(DEST/'derivation.json').write_text(json.dumps({'source':str(SOURCE),'pairs':manifest,
    'camera_pawn_and_simulation_times_match':True,'cropped':False,'enlargement':1,
    'simulation_seconds':times,'playback_milliseconds':durations,'last_frame_hold_ms':350,
    'actual_PIE_samples':True,'continuous_video':False,'raw_images_modified':False},indent=2))
print(json.dumps({'pairs':len(manifest),'other_native_frames':len(other),'review':str(DEST)}))
