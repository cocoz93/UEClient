"""F 파라곤 재질 후보 사본(10-19). 파라곤 번개·광선 재질은 입자용이라 인스턴스 메시에 입히면 「missing usage flag」로 회색 기본 재질이 된다
(gideon-21st-mats-20261019-010026). 우리 폴더에 사본을 뜨고 used_with_instanced_static_meshes 를 켜 저장한다.
재질 인스턴스면 부모 재질도 사본을 떠 켜고, 인스턴스 사본의 부모를 그 사본으로 바꾼다. 원본은 건드리지 않는다.
(10-19 23차) 빔에 끼울 사본도 같은 방법: MAT_USAGE=used_with_beam_trails · MAT_SUFFIX=_Beam · MAT_DEST · MAT_SOURCES(쉼표).
빔에 입자용 재질을 그냥 끼우면 같은 이유로 회색 기본 재질이 된다(짐작 — 인스턴스 메시에서 본 것과 같은 구조)."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
DEST = os.environ.get('MAT_DEST', '/Game/TopDown/Characters/Gideon/FX/ParagonISM/')
USAGE = os.environ.get('MAT_USAGE', 'used_with_instanced_static_meshes')
SUFFIX = os.environ.get('MAT_SUFFIX', '_ISM')
SOURCES = [
    '/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_ElecBeam',
    '/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_Bolt_Energy_Spline',
    '/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_Lightning_Bolt_Master',
    '/Game/ParagonKwang/FX/Materials/Energy/lightning/M_Lightning_HighDetail',
    '/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_LightningSpiral',
    '/Game/ParagonKwang/FX/Materials/Energy/Electricity/M_Kwang_Electric_Discharge',
    '/Game/ParagonDekker/FX/Materials/Splines/M_Beam_Laser',
    '/Game/ParagonGideon/FX/Materials/Heroes/Gideon/M_Burden_Tether',
]
if os.environ.get('MAT_SOURCES'):
    SOURCES = [s for s in os.environ['MAT_SOURCES'].split(',') if s]
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {'copies': []}


def copy(source, name):
    path = DEST + name
    if assets.does_asset_exist(path):
        assets.delete_asset(path)
    return assets.duplicate_asset(source, path), path


def enable(material):
    material.set_editor_property(USAGE, True)
    lib.recompile_material(material)


try:
    for source in SOURCES:
        original = unreal.load_asset(source)
        name = source.rsplit('/', 1)[-1] + SUFFIX
        entry = {'source': source, 'class': original.get_class().get_name() if original else None}
        if original is None:
            entry['error'] = 'missing'
        elif isinstance(original, unreal.Material):
            material, path = copy(source, name)
            enable(material)
            entry.update(copy=path, saved=assets.save_asset(path, only_if_is_dirty=False))
        else:
            # 재질 인스턴스: 맨 위 부모 재질까지 올라가 사본을 떠 켜고, 인스턴스 사본을 그 사본에 붙인다.
            parent = original.get_editor_property('parent')
            while parent and not isinstance(parent, unreal.Material):
                parent = parent.get_editor_property('parent')
            parent_copy, parent_path = copy(parent.get_path_name().split('.')[0], parent.get_name() + SUFFIX)
            enable(parent_copy)
            assets.save_asset(parent_path, only_if_is_dirty=False)
            instance, path = copy(source, name)
            unreal.MaterialEditingLibrary.set_material_instance_parent(instance, parent_copy)
            entry.update(copy=path, parent_copy=parent_path, saved=assets.save_asset(path, only_if_is_dirty=False))
        report['copies'].append(entry)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'paragon-mat-copies.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
