"""Read the authored Sparrow AS particle candidates; saves no source assets."""
import json
import os
from pathlib import Path

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
qa.mkdir(parents=True, exist_ok=True)
root = '/Game/ParagonSparrow/FX/Particles/Sparrow/'
paths = [root + suffix for suffix in (
    'Abilities/DrawABead/FX/P_Sparrow_RMB',
    'Abilities/Ultimate/FX/P_Sparrow_Burst',
    'Abilities/Ultimate/FX/P_SparrowBuff',
    'Abilities/Ultimate/FX/P_Sparrow_UltArrow',
    'Abilities/Ultimate/FX/P_Sparrow_UltHit',
    'Abilities/Ultimate/FX/P_Sparrow_UltHitWorld',
    'Abilities/RainOfArrows/FX/P_RainofArrowsProj',
    'Abilities/Primary/FX/P_Sparrow_PrimaryAttack',
    'Abilities/Primary/FX/P_Sparrow_Primary_Ballistic_HitPlayer',
    'Effects/P_Sparrow_DustKickUp')]
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + path + '"' for path in paths))
(qa / 'candidates.json').write_text(json.dumps(paths, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
