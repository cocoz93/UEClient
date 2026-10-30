"""F 가능성 조사(10-19 23차): 콰앙 번개 빔(P_LightStrike_Beams) 사본의 흔들림·굵기·밝기·색을 바꾼다.
캐스케이드 모듈 클래스는 파이썬에 안 열려 있어(unreal.ParticleModuleBeamNoise 없음) 스네이크 이름(noise_range)은 「Failed to find property」로
실패하고, C++ 이름 그대로(NoiseRange·Frequency·Frequency_LowRange·Speed·StartSize·StartColor·Material)는 읽고 쓰인다
(gideon-f1-noise-20261019-103347, gideon-f5-color-20261019-104630).
Frequency_LowRange가 Frequency보다 크면 엔진이 Frequency를 거기로 올린다(ParticleBeamModules.cpp PostEditChangeProperty) → 둘 다 쓴다.
원본 값: 흔들림 ±(16,7,12) · 꺾임 60/22 · 자라는 속도 5000/1200cm/s(0이면 한 번에 그어짐) · 굵기 3/1.85~2.4cm · 색 (50,1,1)
· 재질 M_Kwang_ElecBeam(Color_0·Color_1·Pow).
BOLT_SPEC = JSON 목록 [{name, gain, freq, speed?, size?, bright?, color0?, color1?, pow?, flat?, material?}] → /Game/TopDown/Characters/Gideon/FX/Probe/P_Probe_<name>.
flat = 빔 길이 방향 굵기 변화(TaperFactor 곡선 점)를 1 이하로 자름 — 원본 곡선 하나가 대상 쪽 끝에서 1.9→3.5배로 부풀어 뭉침.
color0/1·pow(가로 방향 빛 꺼짐 세기, 원본 4 — 낮을수록 넓게 번짐)가 있으면 재질 인스턴스 MI_Probe_<name>을 만들어 사본에 끼운다. 원본은 저장하지 않는다.
BOLT_FOLDER·BOLT_PREFIX(10-20 A 광선 — 시험용이 아니라 게임이 쓰는 사본)를 주면 그 폴더에 P_<PREFIX>_<name>·MI_<PREFIX>_<name>으로 만든다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE = '/Game/ParagonKwang/FX/Particles/Abilities/LightStrike/FX/P_LightStrike_Beams'
FOLDER = os.environ.get('BOLT_FOLDER', '/Game/TopDown/Characters/Gideon/FX/Probe')
PREFIX = os.environ.get('BOLT_PREFIX', 'Probe')
SPECS = json.loads(os.environ.get('BOLT_SPEC', '[{"name": "G4F8S0", "gain": 4, "freq": 8, "speed": 0}]'))
report = {'passed': False, 'copies': []}
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary


def modules(system, cls):
    prefix = system.get_path_name() + ':'
    found = []
    for o in unreal.ObjectIterator(unreal.Object):
        if unreal.SystemLibrary.get_path_name(o).startswith(prefix) and o.get_class() and o.get_class().get_name() == cls:
            found.append(o)
    return found


def name_of(module):
    return unreal.SystemLibrary.get_path_name(module).split(':')[-1]


def scale_vector_distribution(module, field, factor, base):
    """사본 값 = 원본(base, 같은 이름 모듈) 값 × factor. 같은 이름 사본을 다시 고쳐도 배수가 겹치지 않는다."""
    raw = module.get_editor_property(field)
    dist = raw.get_editor_property('distribution')
    source = base.get_editor_property(field).get_editor_property('distribution')
    keys = ('constant',) if 'Constant' in dist.get_class().get_name() else ('min', 'max')
    for key in keys:
        vector = source.get_editor_property(key)
        dist.set_editor_property(key, unreal.Vector(vector.x * factor, vector.y * factor, vector.z * factor))
    module.set_editor_property(field, raw)
    return [str(dist.get_editor_property(k)) for k in keys]


def make_instance(spec):
    path = f"{FOLDER}/MI_{PREFIX}_{spec['name']}"
    # 같은 이름을 지우고 다시 만들면 duplicate·create가 None을 돌려준다(gideon-f6-noise-20261019-104842) → 있으면 그대로 고쳐 쓴다.
    instance = unreal.load_asset(path) if assets.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        f"MI_{PREFIX}_{spec['name']}", FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    parent = unreal.load_asset('/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_ElecBeam')
    lib.set_material_instance_parent(instance, parent)
    lib.clear_all_material_instance_parameters(instance)
    for key in ('color0', 'color1'):
        if key in spec:
            r, g, b = spec[key]
            lib.set_material_instance_vector_parameter_value(instance, f'Color_{key[-1]}', unreal.LinearColor(r, g, b, 1.0))
    if 'pow' in spec:
        lib.set_material_instance_scalar_parameter_value(instance, 'Pow', float(spec['pow']))
    assets.save_asset(path, only_if_is_dirty=False)
    return instance


try:
    source = unreal.load_asset(SOURCE)
    parent = unreal.load_asset('/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_ElecBeam')
    report['material_defaults'] = {name: str(lib.get_material_default_vector_parameter_value(parent, name)) for name in ('Color_0', 'Color_1')}
    report['material_defaults']['Pow'] = lib.get_material_default_scalar_parameter_value(parent, 'Pow')
    base = {cls: {name_of(m): m for m in modules(source, cls)} for cls in
            ('ParticleModuleBeamNoise', 'ParticleModuleTypeDataBeam2', 'ParticleModuleSize', 'ParticleModuleColor', 'ParticleModuleRequired')}
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for spec in SPECS:
        path = f"{FOLDER}/P_{PREFIX}_{spec['name']}"
        copy = unreal.load_asset(path) if assets.does_asset_exist(path) else tools.duplicate_asset(f"P_{PREFIX}_{spec['name']}", FOLDER, source)
        row = {'path': path, 'spec': spec}
        for module in modules(copy, 'ParticleModuleBeamNoise'):
            module.set_editor_property('Frequency_LowRange', int(spec['freq']))
            module.set_editor_property('Frequency', int(spec['freq']))
            row.setdefault('noise', []).append(scale_vector_distribution(module, 'NoiseRange', float(spec['gain']),
                                                                         base['ParticleModuleBeamNoise'][name_of(module)]))
        for module in modules(copy, 'ParticleModuleTypeDataBeam2'):
            original = base['ParticleModuleTypeDataBeam2'][name_of(module)].get_editor_property('Speed')
            module.set_editor_property('Speed', float(spec.get('speed', original)))
            row.setdefault('speed', []).append(module.get_editor_property('Speed'))
            # 굵기 변화 곡선(TaperFactor)의 점 값을 1로. 분포 클래스는 파이썬에 없어(unreal.DistributionFloatConstant 없음) 새로 못 끼우므로
            # 이미 있는 곡선(ConstantCurve)의 점만 고친다. 원본 점 값은 base에서 읽어 둔다.
            raw = module.get_editor_property('TaperFactor')
            dist = raw.get_editor_property('distribution')
            curve = dist.get_editor_property('ConstantCurve')
            source_points = base['ParticleModuleTypeDataBeam2'][name_of(module)].get_editor_property('TaperFactor') \
                .get_editor_property('distribution').get_editor_property('ConstantCurve').get_editor_property('Points')
            points = curve.get_editor_property('Points')
            # 목록에서 꺼낸 점은 사본이라 고친 뒤 제자리에 다시 넣어야 한다(gideon-f8-taperdiag-* step1). 부푸는 곡선은 TypeDataBeam2_6(끝 1.9→3.5배).
            for index in range(len(points)):
                point = points[index]
                value = source_points[index].get_editor_property('out_val')
                point.set_editor_property('out_val', min(value, 1.0) if spec.get('flat') else value)
                points[index] = point
            curve.set_editor_property('Points', points)
            dist.set_editor_property('ConstantCurve', curve)
            module.set_editor_property('TaperFactor', raw)
            row.setdefault('taper_points', []).append([(round(s.get_editor_property('InVal'), 2), round(s.get_editor_property('out_val'), 2),
                                                        round(q.get_editor_property('out_val'), 2)) for s, q in
                                                       zip(source_points, module.get_editor_property('TaperFactor').get_editor_property('distribution').get_editor_property('ConstantCurve').get_editor_property('Points'))])
            row.setdefault('taper', []).append(module.get_editor_property('TaperFactor').get_editor_property('distribution').get_class().get_name())
        for module in modules(copy, 'ParticleModuleSize'):
            row.setdefault('size', []).append(scale_vector_distribution(module, 'StartSize', float(spec.get('size', 1)),
                                                                        base['ParticleModuleSize'][name_of(module)]))
        for module in modules(copy, 'ParticleModuleColor'):
            row.setdefault('color', []).append(scale_vector_distribution(module, 'StartColor', float(spec.get('bright', 1)),
                                                                         base['ParticleModuleColor'][name_of(module)]))
        material = make_instance(spec) if ('color0' in spec or 'color1' in spec or 'pow' in spec) else None
        if spec.get('material'):
            material = unreal.load_asset(spec['material'])  # 다른 재질을 통째로(빔 사용 표시를 켠 사본, gideon_paragon_mat_copies.py)
        for module in modules(copy, 'ParticleModuleRequired'):
            module.set_editor_property('Material', material or base['ParticleModuleRequired'][name_of(module)].get_editor_property('Material'))
        row['material'] = material.get_path_name() if material else 'original'
        row['saved'] = assets.save_asset(path, only_if_is_dirty=False)
        report['copies'].append(row)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'bolt-noise-probe.json').write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
