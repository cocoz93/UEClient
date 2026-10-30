"""Read native emitter connections and their exact distribution values."""
import json, os, traceback
from pathlib import Path
import unreal

out=Path(os.environ['SPARROW_QA_OUTPUT'])
report={'passed':False,'objects':[]}
try:
    unreal.SystemLibrary.execute_console_command(None,'CharacterPipeline.OutputDirectory '+str(out))
    unreal.SystemLibrary.execute_console_command(None,'CountessFXQA.WInventory')
    asset=unreal.load_asset('/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing')
    prefix=asset.get_path_name()+':'
    for obj in unreal.ObjectIterator(unreal.Object):
        path=unreal.SystemLibrary.get_path_name(obj)
        if not path.startswith(prefix):continue
        cls=obj.get_class().get_name()
        if 'Distribution' not in cls and cls!='ParticleLODLevel':continue
        row={'path':path,'class':cls,'properties':{}}
        for field in ('Constant','Min','Max','ConstantCurve','Points','bEnabled'):
            try:row['properties'][field]=str(obj.get_editor_property(field))
            except Exception:pass
        report['objects'].append(row)
    report['passed']=(out/'w-emitter-inventory.json').is_file()
except Exception:report['error']=traceback.format_exc()
(out/'distributions.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
