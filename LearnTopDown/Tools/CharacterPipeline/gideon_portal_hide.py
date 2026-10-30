"""Q sky portal: the portal particle shoots its own streak along its facing. Find and hide that emitter in a private copy.
PORTAL_MODE=probe -> save one copy per emitter with only that emitter hidden (Probe/P_Portal_hide_<required module>), for side renders.
PORTAL_MODE=build -> PORTAL_HIDE = comma list of required module names to hide; saves P_Gideon_RMB_Portal_NoStreak.
Hiding = required module draw limit 0 (the module stays; nothing is drawn).
HIDE_SOURCE / HIDE_NAME override the source system and the copy name (default = the Q portal), e.g. D halo ring (10-18).
PORTAL_KEEP = comma list of required module name suffixes to keep (build mode hides every other one instead of PORTAL_HIDE)."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE = os.environ.get('HIDE_SOURCE', '/Game/ParagonGideon/FX/Particles/Gideon/Abilities/ProjectileMeteor/FX/P_Gideon_RMB_Portal')
NAME = os.environ.get('HIDE_NAME', 'P_Gideon_RMB_Portal_NoStreak')
DEST = '/Game/TopDown/Characters/Gideon/FX/'
MODE = os.environ.get('PORTAL_MODE', 'probe')
assets = unreal.EditorAssetLibrary
report = {'mode': MODE, 'copies': []}


def required_modules(system):
    prefix = system.get_path_name() + ':'
    return {unreal.SystemLibrary.get_path_name(o)[len(prefix):]: o for o in unreal.ObjectIterator(unreal.Object)
            if unreal.SystemLibrary.get_path_name(o).startswith(prefix) and o.get_class().get_name() == 'ParticleModuleRequired'}


def make_copy(path, hide):
    if assets.does_asset_exist(path):
        assets.delete_asset(path)
    system = assets.duplicate_asset(SOURCE, path)
    modules = required_modules(system)
    for name in hide:
        module = modules[name]
        # 비트필드 bool은 파이썬 이름이 엔진판마다 달라 둘 다 시도한다.
        for flag in ('use_max_draw_count', 'b_use_max_draw_count', 'bUseMaxDrawCount'):
            try:
                module.set_editor_property(flag, True)
                break
            except Exception:
                continue
        else:
            raise RuntimeError('no draw count flag on ' + name)
        for count in ('max_draw_count', 'MaxDrawCount'):
            try:
                module.set_editor_property(count, 0)
                break
            except Exception:
                continue
        else:
            raise RuntimeError('no draw count on ' + name)
    return {'copy': path, 'hidden': hide, 'saved': assets.save_asset(path, only_if_is_dirty=False)}


try:
    names = sorted(required_modules(unreal.load_asset(SOURCE)))
    report['required_modules'] = names
    if MODE == 'probe':
        for name in names:
            report['copies'].append(make_copy(DEST + 'Probe/P_Portal_hide_' + name.split('_')[-1], [name]))
    else:
        if assets.does_directory_exist(DEST + 'Probe'):
            report['probe_deleted'] = assets.delete_directory(DEST + 'Probe')
        # PORTAL_KEEP = 남길 Required 모듈 이름 끝 번호(쉼표) — 나머지를 모두 숨긴다(예 W 폭발의 돌 조각만 남긴 D 사본, 10-21).
        keep = [k for k in os.environ.get('PORTAL_KEEP', '').split(',') if k]
        hide = [n for n in names if n.split('_')[-1] not in keep] if keep else [n for n in os.environ['PORTAL_HIDE'].split(',') if n]
        report['copies'].append(make_copy(DEST + NAME, hide))
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / (NAME + '-hide.json')).write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
