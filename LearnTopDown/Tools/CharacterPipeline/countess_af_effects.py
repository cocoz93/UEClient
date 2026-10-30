"""Copy authored A/F effects; preserve source meshes, materials and color curves."""
import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal


VERSION = '1'
SOURCE = '/Game/ParagonCountess/FX/Particles/'
DESTINATION = '/Game/TopDown/Characters/Countess/FX/'
# label, original complete system, one-shot emission duration, maximum particle life
EFFECTS = (
    ('P_CountessBloodSealGather', 'Abilities/Ultimate/FX/p_CountessUlt_CastFX', .48, .36),
    ('P_CountessBloodSealBurst', 'Abilities/Ultimate/FX/p_CountessUltImpact', .08, .32),
    ('P_CountessBloodSealGround', 'Abilities/Ultimate/FX/p_CountessUlt_GroundImpactFX', .10, .38),
    ('P_CountessShadowAmbushSlash', 'Abilities/BlinkStrike/FX/p_Countess_XSlash', .08, .24),
    ('P_CountessShadowContact', 'Abilities/BlinkStrike/FX/P_Countess_BlinkStrike_HitFX', .05, .20),
)


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _digest(path):
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    file = content / (path.removeprefix('/Game/') + '.uasset')
    return hashlib.sha256(file.read_bytes()).hexdigest()


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'version': VERSION, 'pack_assets_saved': False,
              'effects': [], 'saved_assets': [],
              'preserved': 'All source emitters, authored meshes/materials, color/alpha/dynamic curves, spawn counts and motion modules; only origin/loop/duration/lifetime adapted'}
    try:
        for name, relative_source, duration, max_life in EFFECTS:
            source_path = SOURCE + relative_source
            target_path = DESTINATION + name
            source_hash = _digest(source_path)
            source = unreal.load_asset(source_path)
            _require(source is not None, 'Missing source: ' + source_path)
            target = unreal.load_asset(target_path)
            if target is None:
                target = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
            _require(target is not None, 'Could not duplicate ' + target_path)
            _require(target.get_path_name().split('.')[0] == target_path, 'Unexpected copy target')
            row = {'source': source_path, 'target': target_path, 'source_sha256_before': source_hash,
                   'emission_seconds': duration, 'max_particle_seconds': max_life,
                   'required_modules': [], 'bone_modules_disabled': [], 'lifetimes': []}
            report['effects'].append(row)
            prefix = target.get_path_name() + ':'
            objects = [item for item in unreal.ObjectIterator(unreal.Object)
                       if unreal.SystemLibrary.get_path_name(item).startswith(prefix)]
            row['mesh_modules'] = []
            for item in objects:
                kind = item.get_class().get_name()
                path = unreal.SystemLibrary.get_path_name(item)
                if kind == 'ParticleModuleRequired':
                    # Entire authored systems are preserved. Explicit local space
                    # makes target-relative copies independent of skeletal bones.
                    for prop, value in (('bUseLocalSpace', True), ('bKillOnDeactivate', False),
                                        ('bKillOnCompleted', False), ('EmitterLoops', 1),
                                        ('EmitterDuration', duration), ('EmitterDurationLow', duration),
                                        ('EmitterDelay', 0.), ('EmitterDelayLow', 0.)):
                        item.set_editor_property(prop, value)
                    row['required_modules'].append(path)
                elif kind == 'ParticleModuleLocationBoneSocket':
                    # The editor-only native helper handles Python-private bEnabled.
                    row['bone_modules_disabled'].append(path)
                elif kind == 'ParticleModuleLifetime':
                    distribution = item.get_editor_property('lifetime').get_editor_property('distribution')
                    _require(distribution is not None, 'Missing lifetime distribution')
                    _require(unreal.SystemLibrary.get_path_name(distribution).startswith(prefix),
                             'Refusing to modify an external distribution')
                    dist_kind = distribution.get_class().get_name()
                    values = {'path': path, 'class': dist_kind}
                    if dist_kind == 'DistributionFloatConstant':
                        old = distribution.get_editor_property('constant')
                        value = min(max(.04, old), max_life)
                        distribution.set_editor_property('constant', value)
                        values.update(before=old, after=value)
                    elif dist_kind == 'DistributionFloatUniform':
                        before = [distribution.get_editor_property('min'), distribution.get_editor_property('max')]
                        after = [min(max(.04, v), max_life) for v in before]
                        distribution.set_editor_property('min', after[0])
                        distribution.set_editor_property('max', max(after))
                        values.update(before=before, after=after)
                    else:
                        values['unchanged'] = True
                    row['lifetimes'].append(values)
                elif kind == 'ParticleModuleTypeDataMesh':
                    mesh = item.get_editor_property('mesh')
                    row['mesh_modules'].append({'module': path, 'mesh': mesh.get_path_name() if mesh else None})
            _require(row['required_modules'], 'No required modules in ' + target_path)
            editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.SystemLibrary.execute_console_command(editor_world, 'CharacterPipeline.OutputDirectory "' + output.as_posix() + '"')
            unreal.SystemLibrary.execute_console_command(editor_world, 'CountessFXQA.DisableExtraBoneSources ' + name)
            native_report = output / ('countess-af-bones-' + name + '.json')
            _require(native_report.is_file(), 'Missing native bone-source report: ' + name)
            row['native_bone_sources'] = json.loads(native_report.read_text(encoding='utf-8-sig'))
            _require(row['native_bone_sources']['passed'], 'Native bone-source adjustment failed: ' + name)
            unreal.EditorAssetLibrary.set_metadata_tag(target, 'CountessAFVersion', VERSION)
            unreal.EditorAssetLibrary.set_metadata_tag(target, 'CountessAFSource', source_path)
            unreal.EditorAssetLibrary.set_metadata_tag(target, 'CountessAFOrigin', 'Actor-relative local space; skeletal BoneSocket locations disabled')
            _require(unreal.EditorAssetLibrary.save_loaded_asset(target, False), 'Save failed: ' + target_path)
            report['saved_assets'].append(target_path)
            row['source_sha256_after'] = _digest(source_path)
            _require(row['source_sha256_before'] == row['source_sha256_after'], 'Pack source changed: ' + source_path)
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'countess-af-effects.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('COUNTESS_AF_EFFECTS passed=' + str(report['passed']) + ' output=' + str(output))
    return report


if __name__ == '__main__':
    destination = os.environ.get('SPARROW_QA_OUTPUT') or str(Path(unreal.Paths.project_saved_dir()) / 'QA/CharacterPipeline/new-skills-quality3-20261021/countess-assets')
    author(destination)
    unreal.SystemLibrary.quit_editor()
