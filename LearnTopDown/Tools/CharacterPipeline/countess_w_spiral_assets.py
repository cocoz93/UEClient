"""Author a private four-arm W copy while preserving original textured assets."""
import hashlib
import json
import os
import traceback
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['SPARROW_QA_OUTPUT'])
SOURCE = '/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing'
DEST = '/Game/TopDown/Characters/Countess/FX/P_CountessW_SpiralRing'
report = {'passed': False}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


try:
    protected = {str(p.relative_to(ROOT)): digest(p)
                 for folder in ('Content/ParagonCountess', 'Content/TopDown/Characters/Countess')
                 for p in (ROOT / folder).rglob('*.uasset')
                 if p.stem != 'P_CountessW_SpiralRing'}
    source = unreal.load_asset(SOURCE)
    assert source
    asset = unreal.load_asset(DEST)
    if not asset:
        asset = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
    assert asset and asset != source
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory ' + str(OUT))
    unreal.SystemLibrary.execute_console_command(None, 'CountessFXQA.WSpiral')
    adaptation = json.loads((OUT / 'w-spiral-adaptation.json').read_text(encoding='utf-8'))
    assert adaptation['passed'], adaptation
    assert len(adaptation['arms']) == 4
    assert adaptation['uses_particle_color'] and adaptation['uses_texture_sample']
    assert adaptation['uses_texture_coordinate'] and adaptation['original_emitter_8x8_subuv_state_confirmed']
    assert adaptation['original_sampler_graph_and_emitter_subuv_state_preserved']
    assert adaptation['shader_graph'], 'Original texture and UV function graph must be recorded'
    assert adaptation['module_outers_and_gpu_cached_references_valid']
    assert adaptation['gpu_emitter_info_rebuilt'] and not adaptation['invalid_references']
    assert adaptation['exterior_smoke_preserved'] and adaptation['original_exterior_emitter_count'] == 2
    original_budget = adaptation['preserved_rim_smoke_expected_spawns']
    added_arm_budget = adaptation['spiral_expected_spawns']
    total_smoke_budget = adaptation['total_smoke_expected_spawns']
    assert added_arm_budget <= original_budget + .001, 'Four added spiral arms exceed the original exterior budget'
    assert total_smoke_budget <= 2 * original_budget + .001, 'Original exterior plus added arms exceed twice the original budget'
    assert abs(total_smoke_budget - (original_budget + added_arm_budget)) <= .001
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
                                                    include_soft_package_references=True)
    before = sorted(str(v) for v in registry.get_dependencies(SOURCE, options))
    after = sorted(str(v) for v in registry.get_dependencies(DEST, options))
    assert before == after, (before, after)
    assert all(digest(ROOT / p) == h for p, h in protected.items()), 'Existing Countess content changed'
    report.update(passed=True, source=SOURCE, destination=DEST, dependencies_preserved=after,
                  protected_original_countess_packages=len(protected), adaptation=adaptation,
                  exterior_smoke_preserved=True, original_exterior_emitter_count=2,
                  smoke_spawn_budgets={'preserved_original_exterior': original_budget,
                                      'added_four_spiral_arms': added_arm_budget,
                                      'original_plus_added_total': total_smoke_budget,
                                      'total_limit': 2 * original_budget})
except Exception:
    report['error'] = traceback.format_exc()
(OUT / 'assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
