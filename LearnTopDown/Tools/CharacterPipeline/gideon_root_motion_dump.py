"""Root motion flag and root bone travel of Gideon cast animations (whether letting the tail play can move the body).
Saves no assets."""
import json
import os
from pathlib import Path

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = '/Game/ParagonGideon/Characters/Heroes/Gideon/Animations/'
rows = {}
for name in os.environ.get('ROOT_ANIMS', 'CosmicRift,Burden,Burden_slow,Burden_Start_Fast').split(','):
    anim = unreal.load_asset(ROOT + name)
    length = anim.get_play_length()
    track = []
    for i in range(9):
        t = length * i / 8
        pose = unreal.AnimationLibrary.get_bone_pose_for_time(anim, 'root', t, False)
        v = pose.translation
        track.append([round(t, 2), round(v.x, 1), round(v.y, 1), round(v.z, 1)])
    rows[name] = {'root_motion': anim.get_editor_property('enable_root_motion'), 'root': track}
(qa / 'root-motion.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
