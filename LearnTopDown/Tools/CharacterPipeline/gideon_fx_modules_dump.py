"""효과(ParticleSystem) 안의 이미터·모듈을 적어 어디서 뿜는지 본다(10-20 A 시전 빛 덩어리 자리 — 입자 경계가 몸 원점·반경 176 고정이라 못 읽음).
FX_DUMP = 쉼표로 이은 효과 경로. 뼈·소켓에서 뿜는 모듈(ParticleModuleLocationBoneSocket)은 뼈 이름·종류를, 효과 기준 좌표 여부(bUseLocalSpace)도 적는다.
저장하지 않는다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
PATHS = [p for p in os.environ.get('FX_DUMP', '/Game/ParagonGideon/FX/Particles/Gideon/Abilities/Burden/FX/P_Burden_Cast').split(',') if p]
report = {'passed': False, 'effects': {}}


def safe(obj, prop):
    try:
        return str(obj.get_editor_property(prop))
    except Exception as error:
        return f'X {error}'[:120]


def dist(obj, prop):
    # RawDistributionVector/Float 안의 실제 값(상수 또는 균등 최소·최대). 문자열로만 나오던 것(첫 덤프)을 풀어 적는다.
    try:
        raw = obj.get_editor_property(prop)
        inner = raw.get_editor_property('distribution')
        if inner is None:
            return 'none'
        cls = inner.get_class().get_name()
        values = {}
        for key in ('constant', 'min', 'max'):
            try:
                values[key] = str(inner.get_editor_property(key))
            except Exception:
                pass
        return f'{cls} {values}'
    except Exception as error:
        return f'X {error}'[:160]


try:
    for path in PATHS:
        system = unreal.load_asset(path)
        prefix = system.get_path_name() + ':'
        rows = []
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if not name.startswith(prefix) or not obj.get_class():
                continue
            cls = obj.get_class().get_name()
            row = {'path': name[len(prefix):], 'class': cls}
            if cls == 'ParticleSpriteEmitter' or cls.endswith('Emitter'):
                row['emitter'] = safe(obj, 'EmitterName')
            if cls == 'ParticleModuleRequired':
                row['local'] = safe(obj, 'bUseLocalSpace')
                row['origin'] = safe(obj, 'EmitterOrigin')
                row['emitter_rotation'] = safe(obj, 'EmitterRotation')
            if cls == 'ParticleModuleLocationPrimitiveSphere':
                row['radius'] = dist(obj, 'StartRadius')
                row['start'] = dist(obj, 'StartLocation')
            if cls.startswith('ParticleModuleVelocity'):
                row['velocity'] = dist(obj, 'StartVelocity')
            if cls.startswith('ParticleModuleSize'):
                row['size'] = dist(obj, 'StartSize')
            if 'BoneSocket' in cls:
                row['source_type'] = safe(obj, 'SourceType')
                try:
                    row['bones'] = [str(s.get_editor_property('BoneSocketName')) for s in obj.get_editor_property('SourceLocations')]
                except Exception as error:
                    row['bones'] = f'X {error}'[:120]
                row['skel_param'] = safe(obj, 'SkelMeshActorParamName')
            if cls in ('ParticleModuleLocation', 'ParticleModuleLocation_Seeded'):
                row['start'] = dist(obj, 'StartLocation')
            rows.append(row)
        report['effects'][path] = rows
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'fx-modules.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
