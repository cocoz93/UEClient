"""Read selected original FX during the existing author callback. Never saves assets."""
import json
import re
from pathlib import Path

import unreal


BASE = '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/'
SPARROW = [BASE + value for value in (
    'DrawABead/FX/P_ReleaseArrow', 'Ultimate/FX/P_Sparrow_Burst',
    'Primary/FX/P_SparrowPrimaryMuzzleFlash', 'Primary/FX/P_Sparrow_PrimaryAttack',
    'Ultimate/FX/P_Arrow_Ultimate', 'Ultimate/FX/P_Sparrow_UltHit', 'Ultimate/FX/P_SparrowBuff',
    'RainOfArrows/FX/P_RainofArrows', 'RainOfArrows/FX/P_RainArrowsTarget')]
HOLY = []  # Native dump is explicitly limited to Sparrow; no pack allowlist expansion.


def author(out):
    out = Path(out)
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + out.as_posix() + '"')
    unreal.SystemLibrary.execute_console_command(None, 'SparrowAssetQA.Dump ' + ' '.join('"' + path + '"' for path in SPARROW))
    native = json.loads((out / 'sparrow-native-inventory.json').read_text(encoding='utf-8-sig'))
    materials = set()
    for asset in native.get('assets', []):
        for emitter in asset.get('emitters', []):
            for lod in emitter.get('lods', []):
                for value in (lod.get('required', {}).get('properties', {}).get('Material', ''),
                              lod.get('type_data', {}).get('properties', {}).get('Mesh', '')):
                    materials.update(re.findall(r"(/Game/[^'\s,\)]+)", value))
    holy = []
    fields = ('emitter_name', 'material', 'emitter_duration', 'emitter_delay', 'emitter_loops',
              'rate', 'rate_scale', 'burst_list', 'start_size', 'start_lifetime', 'start_color',
              'start_alpha', 'color_over_life', 'alpha_over_life', 'color_scale_over_life',
              'alpha_scale_over_life', 'b_enabled', 'use_local_space')
    for path in HOLY:
        asset = unreal.load_asset(path)
        row = {'path': path, 'present': bool(asset), 'objects': []}
        if asset:
            prefix = asset.get_path_name() + ':'
            for obj in unreal.ObjectIterator(unreal.Object):
                if not obj.get_path_name().startswith(prefix):
                    continue
                kind = obj.get_class().get_name()
                if not any(value in kind for value in ('ParticleModule', 'ParticleEmitter', 'ParticleLODLevel')):
                    continue
                entry = {'path': obj.get_path_name(), 'class': kind, 'properties': {}}
                for field in fields:
                    try:
                        value = obj.get_editor_property(field)
                        item = {'value': str(value)}
                        if field == 'material' and value:
                            materials.add(value.get_path_name())
                        try:
                            distribution = value.get_editor_property('distribution')
                            if distribution:
                                item['distribution_class'] = distribution.get_class().get_name()
                                for key in ('constant', 'min', 'max', 'constant_curve', 'parameter_name'):
                                    try:
                                        item[key] = str(distribution.get_editor_property(key))
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        entry['properties'][field] = item
                    except Exception:
                        pass
                row['objects'].append(entry)
        holy.append(row)
    values = []
    lib = unreal.MaterialEditingLibrary
    for path in sorted(materials):
        material = unreal.load_asset(path)
        if not isinstance(material, unreal.MaterialInterface):
            continue
        row = {'path': path, 'scalars': {}, 'vectors': {}, 'textures': {}}
        instance = isinstance(material, unreal.MaterialInstanceConstant)
        try:
            base = material.get_base_material()
            for name in lib.get_scalar_parameter_names(material):
                try:
                    row['scalars'][str(name)] = lib.get_material_instance_scalar_parameter_value(material, name) if instance else lib.get_material_default_scalar_parameter_value(base, name)
                except Exception as exc:
                    row['scalars'][str(name)] = {'error': str(exc)}
            for name in lib.get_vector_parameter_names(material):
                try:
                    value = lib.get_material_instance_vector_parameter_value(material, name) if instance else lib.get_material_default_vector_parameter_value(base, name)
                    row['vectors'][str(name)] = [value.r, value.g, value.b, value.a]
                except Exception as exc:
                    row['vectors'][str(name)] = {'error': str(exc)}
            for name in lib.get_texture_parameter_names(material):
                try:
                    value = lib.get_material_instance_texture_parameter_value(material, name) if instance else lib.get_material_default_texture_parameter_value(base, name)
                    row['textures'][str(name)] = value.get_path_name() if value else None
                except Exception as exc:
                    row['textures'][str(name)] = {'error': str(exc)}
        except Exception as exc:
            row['error'] = str(exc)
        values.append(row)
    report = {'passed': bool(native.get('passed')) and all(row['present'] for row in holy),
              'read_only': True, 'assets_saved': False, 'sparrow_native': native,
              'holy_python': holy, 'material_parameters': values,
              'note': 'Protected Python properties are omitted. Native Sparrow dump contains full exported module/distribution properties.'}
    (out / 'sparrow-fx-depth-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return {'passed': report['passed'], 'read_only': True, 'assets_saved': False,
            'report': str(out / 'sparrow-fx-depth-audit.json')}
