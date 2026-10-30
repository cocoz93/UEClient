"""Sample Aurora animation hand / sword positions (component space) over time to find when a slash or a hand reach
peaks, so R's bursts can land on them (2026-10-19 「R 애니 어색 — 다른 거 없나, 자연스럽게」). Saves no assets.
AURORA_HAND_ANIMS = animations (comma), AURORA_HAND_POINTS = bones (comma, missing ones are reported, not fatal)."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = '/Game/ParagonAurora/Characters/Heroes/Aurora/Animations/'
ANIMS = os.environ.get('AURORA_HAND_ANIMS', 'Emote_Ice_Sculpture,Emote_Slice').split(',')
POINTS = os.environ.get('AURORA_HAND_POINTS', 'hand_r,hand_l,weapon_r,pelvis').split(',')
RATE = 30


result = {'passed': True, 'anims': []}
try:
    options = unreal.AnimPoseEvaluationOptions()
    for name in ANIMS:
        anim = unreal.load_asset(ROOT + name)
        entry = {'anim': name, 'length': round(anim.get_play_length(), 3), 'samples': []}
        first = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, 0.0, options)
        names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(first)]
        entry['bones'] = [n for n in names if any(word in n.lower() for word in ('weapon', 'sword', 'hand', 'blade'))]
        points = [p for p in POINTS if p in names]
        entry['missing'] = [p for p in POINTS if p not in names]
        previous = {}
        for frame in range(int(anim.get_play_length() * RATE) + 1):
            t = frame / RATE
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, options)
            row = {'t': round(t, 3)}
            for point in points:
                transform = unreal.AnimPoseExtensions.get_bone_pose(pose, point, unreal.AnimPoseSpaces.WORLD)
                location = transform.translation
                speed = (location - previous[point]).length() * RATE if point in previous else 0.0
                previous[point] = location
                row[point] = [round(location.x, 1), round(location.y, 1), round(location.z, 1), round(speed)]
                # 뼈 크기(칼이 0에서 커지며 손에 생기는 동작 — 10-20 A Level_Start)
                row[point + '_scale'] = round(transform.scale3d.x, 3)
                # 칼끝은 뼈가 없어 칼 뼈의 축 방향으로 잰다(어느 축이 칼날인지는 받은 쪽이 고른다)
                axes = [transform.rotation.rotate_vector(axis) for axis in (unreal.Vector(1, 0, 0), unreal.Vector(0, 1, 0), unreal.Vector(0, 0, 1))]
                row[point + '_axes'] = [[round(a.x, 3), round(a.y, 3), round(a.z, 3)] for a in axes]
            entry['samples'].append(row)
        result['anims'].append(entry)
except Exception:
    result = {'passed': False, 'error': traceback.format_exc(), 'partial': result}
(qa / 'aurora-hand-timing.json').write_text(json.dumps(result, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
