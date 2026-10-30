"""Build labeled review sheets from immutable native Q comparison screenshots."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('--fps', type=int, required=True, choices=(30,60))
args = parser.parse_args()
directory = args.directory.resolve()
report = json.loads((directory/f'countess-q-comparison-{args.fps}.json').read_text())
destination = directory/'review'
destination.mkdir(exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
screenshots = report['screenshots']


def screenshot(text):
    return next(r for r in screenshots if text in Path(r['image']).name)


pairs = [(phase, screenshot(f'Q-original-{phase}-'), screenshot(f'Q-enhanced-{phase}-'))
         for phase in ('prepare','arrival','slash','afterimage','settle','recovery','return')]
pairs += [(phase, next(r for r in screenshots if r['case']=='E_with_original_Q_setting' and f'-E-{phase}-' in r['image']),
                 next(r for r in screenshots if r['case']=='E_with_enhanced_Q_setting' and f'-E-{phase}-' in r['image']))
          for phase in ('prepare','impact','recovery')]
manifest = []
for offset in range(0,len(pairs),3):
    batch = pairs[offset:offset+3]
    width, height = screenshots[0]['width'], screenshots[0]['height']
    page = Image.new('RGB',(2*width,len(batch)*(height+30)),'#12151c')
    draw = ImageDraw.Draw(page)
    covered = []
    for row,(phase,before,after) in enumerate(batch):
        for column,shot in enumerate((before,after)):
            x,y=column*width,row*(height+30)
            text=('Original' if column==0 else 'Enhanced')+' / '+phase+' / '+str(args.fps)+' FPS simulation'
            draw.text((x+8,y+5),text,font=font,fill='#efeff2')
            page.paste(Image.open(shot['image']).convert('RGB'),(x,y+30))
            covered.append({'path':shot['image'],'sha256':shot['sha256']})
    path=destination/f'sheet-{offset//3+1:02}.png'
    page.save(path)
    manifest.append({'sheet':str(path),'images':covered})
# The room overview is reviewed separately at native resolution.
overview=screenshot('room-countess-overview-')
manifest.append({'sheet':overview['image'],'images':[{'path':overview['image'],'sha256':overview['sha256']}]})
(destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
frames=[]
for phase,before,after in pairs[:6]:
    width,height=before['width'],before['height']
    page=Image.new('RGB',(2*width,height+36),'#12151c');draw=ImageDraw.Draw(page)
    for column,shot in enumerate((before,after)):
        page.paste(Image.open(shot['image']).convert('RGB'),(column*width,36))
        draw.text((column*width+10,7),('Original Q' if column==0 else 'Enhanced Q')+' / '+phase,
                  fill='#efeff2',font=font)
    page.save(destination/f'pair-{phase}.png')
    frames.append(page)
frames[0].save(destination/'Q-staged-comparison.gif',save_all=True,append_images=frames[1:],
               duration=[260,140,260,300,440,1000],loop=0)
detail_frames=[]
box=(int(screenshots[0]['width']*.40),int(screenshots[0]['height']*.18),
     int(screenshots[0]['width']*.80),int(screenshots[0]['height']*.78))
for phase,before,after in pairs[:6]:
    size=(int((box[2]-box[0])*1.5),int((box[3]-box[1])*1.5))
    page=Image.new('RGB',(size[0]*2,size[1]+36),'#12151c');draw=ImageDraw.Draw(page)
    for column,shot in enumerate((before,after)):
        crop=Image.open(shot['image']).convert('RGB').crop(box).resize(size,Image.Resampling.LANCZOS)
        page.paste(crop,(column*size[0],36))
        draw.text((column*size[0]+8,7),('Original Q' if column==0 else 'Enhanced Q')+' / '+phase,
                  font=font,fill='#efeff2')
    page.save(destination/f'detail-{phase}.png')
    detail_frames.append(page)
cyclic=detail_frames[1:]+detail_frames[:1]
cyclic[0].save(destination/'Q-staged-detail.gif',save_all=True,append_images=cyclic[1:],
               duration=[140,260,300,440,1000,260],loop=0)
(destination/'detail-derivation.json').write_text(json.dumps({'same_crop_for_both_variants':True,
    'crop_box_pixels':box,'enlargement':1.5,'resampling':'Lanczos','real_time_recording':False,
    'cyclic_start_phase':'arrival','raw_screenshots_modified':False},indent=2),encoding='utf-8')
print(json.dumps({'images':len(screenshots),'sheets':len(manifest),'review':str(destination)}))
