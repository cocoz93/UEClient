"""시안 여러 개를 같은 시점끼리 나란히 붙인 영상 + 고른 시점의 표 한 장.
argv: spec.json = {shots, prefixes:[[prefix, label], ...], box:[l,t,r,b], scale, columns, fps, video, sheet, sheet_title,
                   sheet_frames:[index, ...], sheet_heads:[..], frames_dir}
각 시안의 사진은 <prefix>_<숫자>.png 를 숫자 순으로 늘어놓은 것(시안마다 장수가 같아야 한다)."""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
shots = Path(spec['shots'])
box = tuple(spec['box'])
scale = spec['scale']
cw, ch = int((box[2] - box[0]) * scale), int((box[3] - box[1]) * scale)
font = ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf', 22)
small = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 18)


def frames_of(prefix):
    found = []
    for path in shots.glob(f'{prefix}_*.png'):
        match = re.fullmatch(re.escape(prefix) + r'_(\d+)', path.stem)
        if match:
            found.append((int(match.group(1)), path))
    return [path for _, path in sorted(found)]


series = [(label, frames_of(prefix)) for prefix, label in spec['prefixes']]
counts = {label: len(files) for label, files in series}
count = min(counts.values())
print('frames per draft', counts)


def tile(path):
    return Image.open(path).convert('RGB').crop(box).resize((cw, ch), Image.BICUBIC)


columns = spec['columns']
rows = (len(series) + columns - 1) // columns
frames_dir = Path(spec['frames_dir'])
frames_dir.mkdir(parents=True, exist_ok=True)
for index in range(count):
    canvas = Image.new('RGB', (cw * columns, ch * rows), (18, 18, 22))
    draw = ImageDraw.Draw(canvas)
    for slot, (label, files) in enumerate(series):
        x, y = (slot % columns) * cw, (slot // columns) * ch
        canvas.paste(tile(files[index]), (x, y))
        draw.rectangle([x, y, x + cw - 1, y + ch - 1], outline=(70, 70, 80))
        draw.rectangle([x, y, x + draw.textlength(label, font=font) + 16, y + 34], fill=(0, 0, 0))
        draw.text((x + 8, y + 4), label, font=font, fill=(255, 214, 90))
    canvas.save(frames_dir / f'frame_{index:03d}.png')

subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(spec['fps']), '-i', str(frames_dir / 'frame_%03d.png'),
                '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', spec['video']], check=True)
print(spec['video'], count, 'frames')

# 표: 한 줄에 시안 하나, 왼쪽 이름, 위 머리글.
picks = spec['sheet_frames']
label_w, head_h, title_h = 190, 34, 44
sheet = Image.new('RGB', (label_w + cw * len(picks), title_h + head_h + ch * len(series)), (24, 24, 30))
draw = ImageDraw.Draw(sheet)
draw.text((12, 8), spec['sheet_title'], font=font, fill=(240, 240, 240))
for column, head in enumerate(spec['sheet_heads']):
    draw.text((label_w + column * cw + 8, title_h + 4), head, font=font, fill=(255, 214, 90))
for row, ((prefix, label), (_, files)) in enumerate(zip(spec['prefixes'], series)):
    y = title_h + head_h + row * ch
    draw.text((12, y + 10), label, font=font, fill=(255, 214, 90))
    for line, text in enumerate(spec.get('subs', {}).get(prefix, '').split('\n')):
        draw.text((12, y + 44 + line * 24), text, font=small, fill=(210, 210, 210))
    for column, index in enumerate(picks):
        sheet.paste(tile(files[index]), (label_w + column * cw, y))
        draw.rectangle([label_w + column * cw, y, label_w + (column + 1) * cw - 1, y + ch - 1], outline=(70, 70, 80))
sheet.save(spec['sheet'])
print(spec['sheet'], sheet.size)
