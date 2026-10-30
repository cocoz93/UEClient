"""Record exact observed concurrent HUD changes without editing or claiming them."""
import json
from baseline import PROJECT, digest

base = PROJECT/'Saved/QA/CharacterPipeline/countess-q-outward-20261016'
names = ['T_Exp_Rail','T_Glass_Sheen','T_Globe_Cavity','T_Life_Frame','T_Life_Globe','T_Life_Liquid',
         'T_Mana_Frame','T_Mana_Globe','T_Mana_Liquid','T_SkillSlot_Active','T_SkillSlot_Frame']
names += ['T_SkillIcon_'+str(i) for i in range(10)]
content = {'Content/TopDown/UI/Textures/'+name+'.png':digest(PROJECT/'Content/TopDown/UI/Textures'/(name+'.png')) for name in names}
source = 'Source/LearnTopDown/CharacterSkillHUD.cpp'
before = json.loads((base/'before-source-hashes.json').read_text(encoding='utf-8'))
assert digest(PROJECT/source)!=before[source]
report = {'authored_by_this_Q_task':False,'modified_or_reverted_by_this_Q_task':False,
          'native_changes':{source:{'before_sha256':before[source],'current_sha256':digest(PROJECT/source)}},
          'content_additions':content,
          'integration_limit':'HUD source changed after the accepted Q editor/game builds. It is preserved, but the concurrent new HUD source is not built or verified by this Q task.',
          'accepted_Q_binary':'UnrealEditor-LearnTopDown-6164.dll'}
(base/'observed-concurrent-HUD-changes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'external_native_files':1,'external_content_additions':len(content)}))
