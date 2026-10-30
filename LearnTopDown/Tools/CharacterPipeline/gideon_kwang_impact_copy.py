"""F(10-19 23차): 콰앙 궁극기 번개(P_Kwang_Ult_Lightning) 사본에서 필요 없는 이미터를 그리지 않게 해 「맞는 자리 번개 터짐」만 남긴다.
이미터 이름(EmitterName)으로 고른다: HIDE에 든 것은 DetailModeBitmask를 0으로(어느 화질에서도 안 돌게). 이미터는 C++ 이름으로만 읽힌다(gideon_bolt_color_dump.py).
IMPACT_HIDE = 쉼표로 이은 숨길 이미터 이름(또는 IMPACT_KEEP = 남길 이름만), IMPACT_NAME = 사본 이름.
IMPACT_LOCAL=1 = 모든 이미터를 효과 기준 좌표(bUseLocalSpace)로 — 효과를 돌리면 줄기 방향도 따라 돌게.
IMPACT_SIZE="x,y,z" = 모든 크기 모듈(StartSize) = 원본 × 축별 배수(모형 입자는 X가 모형 길이 축 — gideon-b8-*에서 확인).
IMPACT_FIXROT=1 = 모형 입자 무작위 회전(MeshRotation 최소~최대)을 최소값으로 고정, 도는 속도(MeshRotationRate)는 0. 원본은 저장하지 않는다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE = '/Game/ParagonKwang/FX/Particles/Abilities/Ultimate/FX/P_Kwang_Ult_Lightning'
FOLDER = '/Game/TopDown/Characters/Gideon/FX/Probe'
NAME = os.environ.get('IMPACT_NAME', 'P_Probe_KwangImpact')
KEEP = [k for k in os.environ.get('IMPACT_KEEP', '').split(',') if k]
HIDE = [h for h in os.environ.get('IMPACT_HIDE', 'Main_Lightning_bolt,Swipe,Rocks,Rocks_02,Fire,Fire_Small,Clouds_Build,Plasma_Gas,Dust_Risdual').split(',') if h]
report = {'passed': False, 'emitters': []}
assets = unreal.EditorAssetLibrary

try:
    path = f'{FOLDER}/{NAME}'
    source = unreal.load_asset(SOURCE)
    copy = unreal.load_asset(path) if assets.does_asset_exist(path) else \
        unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(NAME, FOLDER, source)
    prefix = copy.get_path_name() + ':'
    # EmitterRenderMode(열거형)는 파이썬에서 숫자·이름 모두 「Failed to convert」(kwang-impact-copy-20261019-145850) →
    # 정수 속성 DetailModeBitmask(화질 단계별로 돌지 여부)를 0으로 해 끈다. 숨길 것만 쓴다.
    for obj in unreal.ObjectIterator(unreal.Object):
        name = unreal.SystemLibrary.get_path_name(obj)
        if not name.startswith(prefix) or not obj.get_class() or 'Emitter' not in obj.get_class().get_name() \
                or 'Module' in obj.get_class().get_name() or '.' in name[len(prefix):]:
            continue
        row = {'path': name[len(prefix):], 'name': str(obj.get_editor_property('EmitterName'))}
        if (row['name'] not in KEEP) if KEEP else (row['name'] in HIDE):
            try:
                obj.set_editor_property('DetailModeBitmask', 0)
                row['set'] = f"bitmask={obj.get_editor_property('DetailModeBitmask')}"
            except Exception as error:
                row['set'] = f'X {error}'[:160]
        report['emitters'].append(row)
    if os.environ.get('IMPACT_LOCAL') == '1':
        # 줄기가 효과 회전을 안 따르는 것(피치 ±90에도 하늘 쪽, gideon-b1·b2·b3)이 월드 기준 좌표 때문이라는 짐작을 시험한다.
        report['local'] = []
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if name.startswith(prefix) and obj.get_class() and obj.get_class().get_name() == 'ParticleModuleRequired':
                obj.set_editor_property('bUseLocalSpace', True)
                report['local'].append((name[len(prefix):], str(obj.get_editor_property('bUseLocalSpace'))))
    if os.environ.get('IMPACT_SIZE'):
        # 효과 크기(컴포넌트 배율)를 1/3로 줄여도 줄기 길이가 그대로였다(gideon-b7-*) → 입자 자체 크기를 고친다. 다른 이미터는 꺼져 있어 줄기만 바뀐다.
        sx, sy, sz = (float(v) for v in os.environ['IMPACT_SIZE'].split(','))
        source_sizes = {}
        source_prefix = source.get_path_name() + ':'
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if name.startswith(source_prefix) and obj.get_class() and obj.get_class().get_name() == 'ParticleModuleSize':
                source_sizes[name[len(source_prefix):]] = obj.get_editor_property('StartSize').get_editor_property('distribution')
        report['sizes'] = []
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if not (name.startswith(prefix) and obj.get_class() and obj.get_class().get_name() == 'ParticleModuleSize'):
                continue
            raw = obj.get_editor_property('StartSize')
            dist = raw.get_editor_property('distribution')
            base = source_sizes[name[len(prefix):]]
            keys = ('constant',) if 'Constant' in dist.get_class().get_name() else ('min', 'max')
            for key in keys:
                v = base.get_editor_property(key)
                dist.set_editor_property(key, unreal.Vector(v.x * sx, v.y * sy, v.z * sz))
            obj.set_editor_property('StartSize', raw)
            report['sizes'].append((name[len(prefix):], [str(base.get_editor_property(k)) for k in keys], [str(dist.get_editor_property(k)) for k in keys]))
    if os.environ.get('IMPACT_FIXROT') == '1':
        # 줄기 MeshRotation_0 = 세우기(피치 0.25바퀴) + 0~1바퀴 무작위 — 짧게 줄이면 방향이 틀어져 보여(gideon-b8-*) 무작위를 없앤다.
        report['fixrot'] = []
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if not name.startswith(prefix) or not obj.get_class():
                continue
            cls = obj.get_class().get_name()
            if cls not in ('ParticleModuleMeshRotation', 'ParticleModuleMeshRotationRate'):
                continue
            field = 'StartRotation' if cls == 'ParticleModuleMeshRotation' else 'StartRotationRate'
            raw = obj.get_editor_property(field)
            dist = raw.get_editor_property('distribution')
            low = dist.get_editor_property('min') if cls == 'ParticleModuleMeshRotation' else unreal.Vector(0, 0, 0)
            dist.set_editor_property('min', low)
            dist.set_editor_property('max', low)
            obj.set_editor_property(field, raw)
            report['fixrot'].append((name[len(prefix):], str(dist.get_editor_property('min')), str(dist.get_editor_property('max'))))
    copy.modify()
    report['saved'] = assets.save_asset(path, only_if_is_dirty=False)
    report['path'] = path
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'kwang-impact-copy.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
