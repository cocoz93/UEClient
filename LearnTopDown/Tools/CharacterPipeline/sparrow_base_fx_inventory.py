"""Read default Sparrow FX modules without changing source packages."""
import json
import os
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')
fx = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/'
paths = []
for folder, names in {
    'Primary': ['P_Sparrow_PrimaryAttack', 'P_Sparrow_Primary_Ballistic_HitPlayer',
                'P_Sparrow_Primary_Ballistic_HitWorld', 'P_SparrowPrimaryMuzzleFlash'],
    'RainOfArrows': ['P_RainArrowsTarget', 'P_RainofArrows', 'P_RainofArrowsProj'],
    'DrawABead': ['P_Sparrow_RMB', 'P_ReleaseArrow'],
    'Ultimate': ['P_SparrowBuff', 'P_Sparrow_UltArrow', 'P_Sparrow_UltHit', 'P_Sparrow_UltHitWorld'],
}.items():
    paths.extend(fx + folder + '/FX/' + name for name in names)
unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + p + '"' for p in paths))
unreal.SystemLibrary.quit_editor()
