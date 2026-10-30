"""Read the actual saved archer animation and cloth assets without installing settings."""
import json, os, traceback
from pathlib import Path
import unreal

out=Path(os.environ['SPARROW_QA_OUTPUT'])
r={'passed':False}
try:
    unreal.SystemLibrary.execute_console_command(None,'CharacterPipeline.OutputDirectory '+str(out))
    paths=(
        '/Game/TopDown/Characters/Sparrow/Animations/ABP_Sparrow_TopDown',
        '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue',
        '/Game/TopDown/Characters/Sparrow/Animations/A_Sparrow_RelaxedIdle',
        '/Game/TopDown/Characters/Sparrow/Animations/BS_Sparrow_RelaxedMove')
    unreal.SystemLibrary.execute_console_command(None,'SparrowAssetQA.Dump '+' '.join(paths))
    dump=json.loads((out/'sparrow-native-inventory.json').read_text(encoding='utf-8'))
    r.update(passed=dump.get('passed',False),requested=list(paths))
except Exception:r['error']=traceback.format_exc()
(out/'inventory-result.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
