"""Read all imported Sparrow base and skin FX; never save source packages."""
import hashlib
import json
import os
from pathlib import Path

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
output = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
assert output.is_relative_to(root / 'Saved/QA')
output.mkdir(parents=True, exist_ok=True)
pack = root / 'Content/ParagonSparrow'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    return {str(p.relative_to(root)).replace('\\', '/'): sha(p)
            for p in pack.rglob('*.uasset')}


before = source_hashes()
paths = []
base = pack / 'FX/Particles/Sparrow/Abilities'
for folder, names in {
    'Primary': ['P_Sparrow_PrimaryAttack', 'P_Sparrow_Primary_Ballistic_HitPlayer',
                'P_Sparrow_Primary_Ballistic_HitWorld', 'P_SparrowPrimaryMuzzleFlash'],
    'RainOfArrows': ['P_RainArrowsTarget', 'P_RainofArrows', 'P_RainofArrowsProj'],
    'DrawABead': ['P_Sparrow_RMB', 'P_ReleaseArrow'],
    'Ultimate': ['P_SparrowBuff', 'P_Sparrow_UltArrow', 'P_Sparrow_UltHit', 'P_Sparrow_UltHitWorld'],
}.items():
    paths.extend(base / folder / 'FX' / (name + '.uasset') for name in names)
paths.extend(sorted((pack / 'FX/Particles/Sparrow/Skins').rglob('*.uasset')))
assets = ['/Game/' + str(p.relative_to(root / 'Content').with_suffix('')).replace('\\', '/')
          for p in paths]
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + output.as_posix() + '"')
unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + p + '"' for p in assets))
native = json.loads((output / 'sparrow-native-inventory.json').read_text(encoding='utf-8-sig'))
report = {
    'read_only': True,
    'passed': bool(native.get('passed')),
    'scope': 'Imported ParagonSparrow pack only; no claim about every original-game skin.',
    'appearance_skin_folders': sorted(p.name for p in (pack / 'Characters/Heroes/Sparrow/Skins').iterdir() if p.is_dir()),
    'fx_skin_folders': sorted(p.name for p in (pack / 'FX/Particles/Sparrow/Skins').iterdir() if p.is_dir()),
    'fx_assets': assets,
    'source_package_sha256': before,
    'native_inventory_sha256': sha(output / 'sparrow-native-inventory.json'),
    'source_unchanged': before == source_hashes(),
    'no_source_packages_saved': True,
}
report['passed'] &= report['source_unchanged']
(output / 'palette-inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('SPARROW_PALETTE_INSPECTION ' + json.dumps({'passed': report['passed'], 'assets': len(assets), 'output': str(output)}))
unreal.SystemLibrary.quit_editor()
