"""F 가능성 조사(10-19 23차): 번개 빔 굵기 곡선(TaperFactor) 값이 어느 단계에서 안 먹는지 가른다. 에셋은 저장하지 않는다."""
import json, os, traceback
from pathlib import Path
import unreal
out = Path(os.environ['SPARROW_QA_OUTPUT'])
log = []
try:
    system = unreal.load_asset('/Game/TopDown/Characters/Gideon/FX/Probe/P_Probe_H2')
    prefix = system.get_path_name() + ':'
    mods = [o for o in unreal.ObjectIterator(unreal.Object) if unreal.SystemLibrary.get_path_name(o).startswith(prefix) and o.get_class() and o.get_class().get_name() == 'ParticleModuleTypeDataBeam2']
    for m in mods:
        raw = m.get_editor_property('TaperFactor')
        dist = raw.get_editor_property('distribution')
        curve = dist.get_editor_property('ConstantCurve')
        pts = curve.get_editor_property('Points')
        row = {'module': unreal.SystemLibrary.get_path_name(m).split(':')[-1], 'dist': dist.get_class().get_name(), 'n': len(pts),
               'max_before': max(p.get_editor_property('out_val') for p in pts)}
        pts[-2].set_editor_property('out_val', 0.123)
        row['step1_list_elem'] = pts[-2].get_editor_property('out_val')
        curve.set_editor_property('Points', pts)
        row['step2_curve'] = curve.get_editor_property('Points')[-2].get_editor_property('out_val')
        for name in ('ConstantCurve', 'constant_curve'):
            try:
                dist.set_editor_property(name, curve)
                row[f'step3_{name}'] = dist.get_editor_property(name).get_editor_property('Points')[-2].get_editor_property('out_val')
            except Exception as e:
                row[f'step3_{name}'] = f'X {e}'[:120]
        try:
            row['attr_points'] = len(curve.points)
        except Exception as e:
            row['attr_points'] = f'X {e}'[:80]
        log.append(row)
except Exception:
    log.append(traceback.format_exc())
(out / 'taper-diag.json').write_text(json.dumps(log, indent=1, default=str), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
