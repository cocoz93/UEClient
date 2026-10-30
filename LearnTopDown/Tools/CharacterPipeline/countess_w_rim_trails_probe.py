"""Read the original textured trail graph without changing any asset."""
import os, json, traceback
from pathlib import Path
import unreal

out=Path(os.environ['SPARROW_QA_OUTPUT'])
r={'passed':False,'emitters':[]}
try:
    asset=unreal.load_asset('/Game/TopDown/Characters/Countess/FX/P_CountessW_DenseTrails')
    unreal.SystemLibrary.execute_console_command(None,'obj dump '+asset.get_path_name()+' recurse=true')
    for obj in unreal.ObjectIterator(unreal.Object):
        path=unreal.SystemLibrary.get_path_name(obj)
        if not path.startswith(asset.get_path_name()+':'):continue
        cls=obj.get_class().get_name()
        if cls in ('ParticleSpriteEmitter','ParticleLODLevel'):
            unreal.SystemLibrary.execute_console_command(None,'obj dump '+path+' recurse=true')
            r['emitters'].append({'class':cls,'path':path})
    r['passed']=True
except Exception:r['error']=traceback.format_exc()
(out/'probe.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
