"""F(10-19 23차): 입자 효과의 색·밝기·모형·재질을 바꿀 자리를 찾는다(번개 빔, 콰앙 궁극기 번개). 색 모듈 분포값과 재질 인자 이름을 C++ 이름으로 읽는다.
FX_DUMP = 쉼표로 이은 입자 효과 경로. 에셋은 저장하지 않는다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SYSTEMS = [p for p in os.environ.get('FX_DUMP', '').split(',') if p]
FIELDS = {
    'ParticleModuleColor': ['StartColor', 'StartAlpha', 'bClampAlpha'],
    'ParticleModuleColorOverLife': ['ColorOverLife', 'AlphaOverLife'],
    'ParticleModuleColorScaleOverLife': ['ColorScaleOverLife', 'AlphaScaleOverLife', 'bEmitterTime'],
    'ParticleModuleRequired': ['Material', 'bUseLocalSpace', 'EmitterDuration', 'EmitterLoops', 'EmitterDelay'],
    'ParticleModuleSize': ['StartSize'],
    'ParticleModuleLifetime': ['Lifetime'],
    'ParticleModuleTypeDataBeam2': ['BeamMethod', 'Speed', 'Sheets', 'TaperMethod', 'TaperFactor', 'TaperScale', 'InterpolationPoints',
                                    'TextureTile', 'TextureTileDistance', 'MaxBeamCount', 'UpVectorStepSize'],
    'ParticleModuleSpawn': ['Rate', 'RateScale', 'BurstList'],
    'ParticleModuleTypeDataMesh': ['Mesh', 'bOverrideMaterial', 'MeshAlignment', 'bCameraFacing', 'CameraFacingUpAxisOption_DEPRECATED'],
    'ParticleModuleMeshMaterial': ['MeshMaterials'],
    'ParticleModuleLocation': ['StartLocation'],
    'ParticleModuleMeshRotation': ['StartRotation', 'bInheritParent'],
    'ParticleModuleMeshRotationRate': ['StartRotationRate'],
    'ParticleModuleRotation': ['StartRotation'],
    'ParticleModuleRotationRate': ['StartRotationRate'],
    'ParticleModuleVelocity': ['StartVelocity', 'StartVelocityRadial', 'bInWorldSpace'],
    'ParticleModuleLocationPrimitiveSphere': ['StartRadius', 'Positive_X', 'Positive_Y', 'Positive_Z'],
    'ParticleModuleOrientationAxisLock': ['LockAxisFlags'],
    'ParticleModuleSizeMultiplyLife': ['LifeMultiplier'],
    'ParticleModuleSizeScale': ['SizeScale'],
    'ParticleModuleSubUV': ['SubImageIndex'],
    'ParticleModuleParameterDynamic': ['DynamicParams'],
}
report = {'passed': False, 'systems': []}


def text(value):
    try:
        dist = value.get_editor_property('distribution')
    except Exception:
        return str(value)[:200]
    if not dist:
        return 'None'
    item = dist.get_class().get_name()
    for key in ('constant', 'min', 'max', 'parameter_name', 'constant_curve'):
        try:
            item += f' {key}={str(dist.get_editor_property(key))[:260]}'
        except Exception:
            pass
    return item


try:
    lib = unreal.MaterialEditingLibrary
    for path in SYSTEMS:
        system = unreal.load_asset(path)
        prefix = system.get_path_name() + ':'
        entry = {'system': path, 'modules': [], 'materials': {}}
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if not name.startswith(prefix):
                continue
            cls = obj.get_class().get_name()
            if cls not in FIELDS:
                continue
            row = {'class': cls, 'path': name[len(prefix):]}
            for field in FIELDS[cls]:
                try:
                    row[field] = text(obj.get_editor_property(field))
                except Exception as error:
                    row[field] = f'X {error}'[:100]
            entry['modules'].append(row)
            if cls == 'ParticleModuleRequired':
                material = obj.get_editor_property('Material')
                if material and material.get_path_name() not in entry['materials']:
                    info = {'class': material.get_class().get_name()}
                    for kind, getter in (('scalars', lib.get_scalar_parameter_names), ('vectors', lib.get_vector_parameter_names),
                                         ('textures', lib.get_texture_parameter_names)):
                        try:
                            info[kind] = [str(n) for n in getter(material)]
                        except Exception as error:
                            info[kind] = f'X {error}'[:100]
                    base = material.get_base_material()
                    info['base'] = base.get_path_name() if base else None
                    info['blend'] = str(base.get_editor_property('blend_mode')) if base else None
                    entry['materials'][material.get_path_name()] = info
        # 이미터별 모듈 목록: LOD 레벨의 Modules·RequiredModule·TypeDataModule도 C++ 이름으로는 읽힌다(스네이크 이름은 「Failed to find」).
        entry['emitters'] = []
        for obj in unreal.ObjectIterator(unreal.Object):
            name = unreal.SystemLibrary.get_path_name(obj)
            if not name.startswith(prefix) or not obj.get_class() or obj.get_class().get_name() != 'ParticleLODLevel':
                continue
            row = {'lod': name[len(prefix):]}
            try:
                outer = obj.get_outer()
                row['emitter_name'] = str(outer.get_editor_property('EmitterName'))
            except Exception as error:
                row['emitter_name'] = f'X {error}'[:80]
            for key in ('RequiredModule', 'TypeDataModule', 'SpawnModule', 'Modules', 'bEnabled'):
                try:
                    value = obj.get_editor_property(key)
                    if key == 'Modules':
                        row[key] = [unreal.SystemLibrary.get_path_name(m)[len(prefix):] for m in value if m]
                    elif isinstance(value, unreal.Object):
                        row[key] = unreal.SystemLibrary.get_path_name(value)[len(prefix):]
                    else:
                        row[key] = str(value)
                except Exception as error:
                    row[key] = f'X {error}'[:80]
            entry['emitters'].append(row)
        report['systems'].append(entry)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'bolt-color-dump.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
