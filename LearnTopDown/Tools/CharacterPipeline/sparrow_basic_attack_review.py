"""Hash-checked 1:1 native old/new frame pairs; no source-image edits."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

parser=argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
parser.add_argument('--fps',type=int,default=60)
args=parser.parse_args()
root=args.directory.resolve()
report_path=root/f'sparrow-basic-natural-{args.fps}.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
assert report['passed']
out=root/'review';out.mkdir(exist_ok=True)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

manifest={'report':{'path':str(report_path),'sha256':digest(report_path)},'pairs':[],
          'sheets':[],'gifs':[],'sources':[], 'source_images_modified':False,
          'crop_or_scale_changed':False,'continuous_video':False,
          'visual_review_completed':False,'user_style_approval':False}
for view in ('field','close'):
    shots={mode:[s for s in report['screenshots'] if s['case']==mode+'_'+view] for mode in ('old','new')}
    assert len(shots['old'])==len(shots['new'])==10
    frames=[]
    for index,(old,new) in enumerate(zip(shots['old'],shots['new'])):
        assert math.dist(old['state']['position'],new['state']['position'])<.1
        assert math.dist(old['state']['view_location'],new['state']['view_location'])<.1
        assert abs(old['state']['view_fov']-new['state']['view_fov'])<.001
        pair=Image.new('RGB',(1400,362),(17,20,26))
        draw=ImageDraw.Draw(pair)
        for x,mode,shot in ((0,'Before',old),(700,'After',new)):
            path=Path(shot['image']);assert digest(path)==shot['sha256']
            with Image.open(path) as source:
                assert source.size==(700,330)
                pair.paste(source.convert('RGB'),(x,32))
            case=next(c for c in report['cases'] if c['name']==('old' if mode=='Before' else 'new')+'_'+view)
            elapsed=0 if index==0 else case['data']['capture_times'][index-1]
            draw.text((x+8,8),f'{mode} | {view} | {elapsed:.3f}s',fill='white')
            manifest['sources'].append({'path':str(path),'sha256':shot['sha256']})
        path=out/f'{view}-pair-{index:02d}.png';pair.save(path)
        manifest['pairs'].append({'path':str(path),'sha256':digest(path),'view':view,'index':index})
        frames.append(pair)
    for start in (0,5):
        sheet=Image.new('RGB',(1400,362*5),(17,20,26))
        for index,frame in enumerate(frames[start:start+5]):sheet.paste(frame,(0,index*362))
        path=out/f'{view}-sheet-{start//5+1:02d}.png';sheet.save(path)
        manifest['sheets'].append({'path':str(path),'sha256':digest(path)})
    path=out/f'{view}-before-after-sampled.gif'
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=[300,66,66,100,83,117,250,300,200,350],loop=0)
    manifest['gifs'].append({'path':str(path),'sha256':digest(path),'view':view,
                              'sampled_comparison_not_continuous_video':True})
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'pairs':len(manifest['pairs']),'sources':len(manifest['sources']),'review':str(out)}))
