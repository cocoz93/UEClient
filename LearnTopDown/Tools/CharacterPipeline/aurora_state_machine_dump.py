"""Read-only: dump the state machines of Aurora's original anim blueprint and Countess's TopDown copy
(AuroraAssetQA.DumpStateMachines) into the QA folder, to compare how a stop after a short move is handled. Saves no assets."""
import os
from pathlib import Path

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
PATHS = os.environ.get('DUMP_PATHS', '/Game/ParagonAurora/Characters/Heroes/Aurora/Aurora_AnimBlueprint.Aurora_AnimBlueprint '
                       '/Game/TopDown/Characters/Countess/Animations/ABP_Countess_TopDown.ABP_Countess_TopDown')
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
unreal.SystemLibrary.execute_console_command(None, 'AuroraAssetQA.DumpStateMachines ' + PATHS)
unreal.SystemLibrary.quit_editor()
