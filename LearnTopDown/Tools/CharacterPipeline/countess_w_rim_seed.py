"""Preserve the current W density and seed a separate outer-front variant."""
import json, os, traceback
from pathlib import Path
import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
report = {'passed': False}
try:
    source = '/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseRing'
    target = '/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing'
    assert not unreal.EditorAssetLibrary.does_asset_exist(target), 'Do not overwrite a rim candidate'
    asset = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    assert asset and unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    report.update(passed=True, source=source, destination=target)
except Exception:
    report['error'] = traceback.format_exc()
(out/'seed.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
