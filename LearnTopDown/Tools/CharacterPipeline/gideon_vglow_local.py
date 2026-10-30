"""V 일렁이는 빛(10-20 「일렁이는 효과들도 점점 줄면서 블랙홀로 빨려 들어가게」 → 「바뀐 거 전혀 모르겠다」).
원본 P_PH_Shockwave_V2는 이미터가 월드 기준 좌표라 한 번 뿌린 입자는 제자리에 남아, 효과 크기를 줄여도(UpdateBlackHoleShrink)
3.9초에 2.2초와 같은 크기였다(gideon-36th-look-* r_220·r_390). 모든 이미터를 효과 기준 좌표(bUseLocalSpace)로 바꾼 사본
/Game/TopDown/Characters/Gideon/FX/P_Gideon_VGlow_Local 을 만든다 — 효과 크기를 줄이면 이미 뿌린 입자도 같이 준다.
방식은 gideon_kwang_impact_copy.py IMPACT_LOCAL과 같다. 원본은 저장하지 않는다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE = '/Game/ParagonMinions/FX/Particles/Minions/Prime_Helix/Abilities/SpecialAttack2/FX/P_PH_Shockwave_V2'
FOLDER = '/Game/TopDown/Characters/Gideon/FX'
NAME = 'P_Gideon_VGlow_Local'
report = {'passed': False, 'local': []}
assets = unreal.EditorAssetLibrary

try:
    path = f'{FOLDER}/{NAME}'
    source = unreal.load_asset(SOURCE)
    copy = unreal.load_asset(path) if assets.does_asset_exist(path) else \
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME, FOLDER, source)
    prefix = copy.get_path_name() + ':'
    for obj in unreal.ObjectIterator(unreal.Object):
        name = unreal.SystemLibrary.get_path_name(obj)
        if name.startswith(prefix) and obj.get_class() and obj.get_class().get_name() == 'ParticleModuleRequired':
            obj.set_editor_property('bUseLocalSpace', True)
            report['local'].append((name[len(prefix):], str(obj.get_editor_property('bUseLocalSpace'))))
    copy.modify()
    report['saved'] = assets.save_asset(path, only_if_is_dirty=False)
    report['passed'] = bool(report['local'])
except Exception:
    report['error'] = traceback.format_exc()
(out / 'vglow-local.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
