"""Seed only new private assets before a native constructor references them."""
import json, os, traceback
from pathlib import Path
import unreal

out=Path(os.environ['SPARROW_QA_OUTPUT']);report={'passed':False}
try:
    source='/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing'
    destination='/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing'
    assert not unreal.EditorAssetLibrary.does_asset_exist(destination)
    asset=unreal.EditorAssetLibrary.duplicate_asset(source,destination)
    assert asset and unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
    report.update(passed=True,source=source,destination=destination)
except Exception:report['error']=traceback.format_exc()
(out/'seed.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
