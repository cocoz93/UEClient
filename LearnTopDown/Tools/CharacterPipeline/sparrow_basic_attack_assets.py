"""Create/configure only two private Sparrow basic-attack presentation assets."""
import hashlib
import json
import os
from pathlib import Path
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
DEST = '/Game/TopDown/Characters/Sparrow/Animations/'
PAIRS = [('ABP_Sparrow_SmoothStop', 'ABP_Sparrow_BasicNatural'),
         ('AM_Sparrow_Primary', 'AM_Sparrow_PrimaryNatural')]
HELD = os.environ.get('SPARROW_ATTACK_HELD_PREPARE') == '1'
if HELD:
    PAIRS = [('ABP_Sparrow_BasicNatural', 'ABP_Sparrow_HeldAim')]
report = {'passed': False, 'saved_assets': [], 'original_assets_unchanged': False}

def file(name):
    return ROOT / 'Content/TopDown/Characters/Sparrow/Animations' / (name + '.uasset')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

try:
    assert OUT.is_relative_to(ROOT / 'Saved/QA')
    hashes = {str(file(source).relative_to(ROOT)): digest(file(source)) for source, _ in PAIRS}
    copies = []
    for source, target in PAIRS:
        original = unreal.load_asset(DEST + source)
        assert original is not None
        copied = unreal.load_asset(DEST + target) or unreal.EditorAssetLibrary.duplicate_asset(DEST + source, DEST + target)
        assert copied is not None
        copies.append(copied)
    if not os.environ.get('SPARROW_ATTACK_PREPARE_ONLY'):
        unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + OUT.as_posix() + '"')
        unreal.SystemLibrary.execute_console_command(None, 'SparrowAttackQA.ConfigureHeld' if HELD else 'SparrowAttackQA.Configure')
        configured = OUT / ('sparrow-held-aim-configuration.json' if HELD else 'sparrow-basic-attack-configuration.json')
        assert configured.is_file(), 'New SparrowAttackQA editor module is required'
        report['configuration'] = json.loads(configured.read_text(encoding='utf-8-sig'))
        assert report['configuration']['passed'], report['configuration']
        unreal.BlueprintEditorLibrary.compile_blueprint(copies[0])
        assert copies[0].get_editor_property('status') != unreal.BlueprintStatus.BS_ERROR
    for copied in copies:
        assert unreal.EditorAssetLibrary.save_loaded_asset(copied, False)
        report['saved_assets'].append(copied.get_path_name())
    report['original_assets_unchanged'] = all(digest(ROOT / path) == expected for path, expected in hashes.items())
    assert report['original_assets_unchanged']
    report['asset_hashes'] = {str(file(target).relative_to(ROOT)): digest(file(target)) for _, target in PAIRS}
    report['prepare_only'] = bool(os.environ.get('SPARROW_ATTACK_PREPARE_ONLY'))
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / ('sparrow-held-aim-assets.json' if HELD else 'sparrow-basic-attack-assets.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
