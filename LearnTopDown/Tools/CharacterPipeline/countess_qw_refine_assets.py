"""Author separate wispy Q and interior-only W veil assets; preserve existing assets."""
import json
from pathlib import Path

import unreal


Q_SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted'
Q_TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardWispy'
Q_NOISE = '/Game/ParagonCountess/FX/Textures/Masks/T_NoisyMask'
W_SOURCE = '/Game/TopDown/Characters/Countess/FX/P_CountessW_LightRing'
W_TARGET = '/Game/TopDown/Characters/Countess/FX/P_CountessW_VeilRing'
W_BASE_SOURCE = '/Game/ParagonCountess/FX/Materials/Smoke/WispySmokeSoft/M_Turbulent_SmokeSubUV_RandomColorVaration'
W_INSTANCE_SOURCE = W_BASE_SOURCE + '_VampInst'
W_BASE_TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessWSmokeVeilBase'
W_INSTANCE_TARGET = '/Game/TopDown/Characters/Countess/Materials/MI_CountessWSmokeVeil'
BODY_REMAP = '''// Retain the short, thin Mode 0 geometry mask; preserve detached flecks and other modes' geometry.
if (Mode < 0.5 && UV.y <= 1.5)
{
    UV.x /= 0.60;
    float bodyV = 0.5 + (UV.y - 0.5) / 0.40;
    if (bodyV < 0 || bodyV > 1) return float4(0, 0, 0, 0);
    UV.y = bodyV;
}
'''
BODY_BREAKUP = '''// Let the original weapon trail lead; break up only the added continuous overlay.
if (Mode < 0.5 && UV.y <= 1.5)
{
    float grain = smoothstep(0.24, 0.72, Grain);
    color *= 0.40 * (0.45 + 0.55 * grain);
    alpha *= 0.35 * (0.20 + 0.80 * grain);
}
else if (Mode >= 1.5)
{
    color *= 0.40;
    alpha *= 0.50;
}
'''


def private_copy(source_path, target_path):
    source = unreal.load_asset(source_path)
    assert source, source_path
    target = unreal.load_asset(target_path)
    if not target:
        target = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    assert target and target != source, target_path
    return source, target


def author_refinements(output, q_only=False):
    """Importable by the shared editor session; does not launch PIE or quit the editor."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    library = unreal.MaterialEditingLibrary
    source, material = private_copy(Q_SOURCE, Q_TARGET)
    source_custom = [node for node in library.get_material_expressions(source)
                     if node.get_class().get_name() == 'MaterialExpressionCustom']
    target_custom = [node for node in library.get_material_expressions(material)
                     if node.get_class().get_name() == 'MaterialExpressionCustom']
    assert len(source_custom) == len(target_custom) == 1
    original = source_custom[0].get_editor_property('code')
    assert original.count('float age = max(0, Clock - SpawnTime);') == 1
    final_return = 'return float4(color, saturate(alpha));'
    assert original.count(final_return) == 1
    expected = BODY_REMAP + original.replace(final_return, BODY_BREAKUP + final_return)
    material.modify()
    target_custom[0].modify()
    target_custom[0].set_editor_property('code', expected)
    restored = target_custom[0].get_editor_property('code').removeprefix(BODY_REMAP)
    assert restored.replace(BODY_BREAKUP, '') == original
    custom_inputs = list(target_custom[0].get_editor_property('inputs'))
    if not any(str(value.get_editor_property('input_name')) == 'Grain' for value in custom_inputs):
        grain_input = unreal.CustomInput()
        grain_input.set_editor_property('input_name', 'Grain')
        custom_inputs.append(grain_input)
        target_custom[0].set_editor_property('inputs', custom_inputs)
    noise = unreal.load_asset(Q_NOISE)
    assert noise, Q_NOISE
    # T_NoisyMask is referenced by the original M_MeshSwipe and Countess trail master.
    coordinates = library.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
    coordinates.set_editor_property('u_tiling', 4.0)
    coordinates.set_editor_property('v_tiling', 1.0)
    panner = library.create_material_expression(material, unreal.MaterialExpressionPanner)
    panner.set_editor_property('speed_x', .35)
    panner.set_editor_property('speed_y', .06)
    sample = library.create_material_expression(material, unreal.MaterialExpressionTextureSample)
    sample.set_editor_property('texture', noise)
    assert library.connect_material_expressions(coordinates, '', panner, 'Coordinate')
    assert library.connect_material_expressions(panner, '', sample, 'UVs')
    assert library.connect_material_expressions(sample, 'R', target_custom[0], 'Grain')
    library.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False), Q_TARGET

    q_report = {'source': Q_SOURCE, 'asset': Q_TARGET, 'continuous_body_length_multiplier': .60,
                'continuous_body_width_multiplier': .40, 'detached_flecks_unchanged': True,
                'continuous_body_alpha_max_multiplier': .35, 'continuous_body_brightness_max_multiplier': .40,
                'original_trail_noise_texture': Q_NOISE, 'impact_brightness_multiplier': .40,
                'impact_alpha_multiplier': .50, 'rush_mode_unchanged': True,
                'existing_mesh_and_muted_hue_unchanged': True}
    if q_only:
        report = {'passed': True, 'q': q_report, 'w_unchanged': True}
        (output / 'assassin-qw-assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        return report

    _, particle = private_copy(W_SOURCE, W_TARGET)
    _, veil_base = private_copy(W_BASE_SOURCE, W_BASE_TARGET)
    _, veil_instance = private_copy(W_INSTANCE_SOURCE, W_INSTANCE_TARGET)
    override_properties = ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')
    overrides = {key: str(veil_instance.get_editor_property(key)) for key in override_properties}
    unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory ' + str(output))
    unreal.SystemLibrary.execute_console_command(None, 'CountessFXQA.WVeil')
    adaptation = json.loads((output / 'w-spiral-adaptation.json').read_text(encoding='utf-8'))
    assert adaptation['passed'], adaptation
    assert adaptation['interior_material_replaced_emitters'] == 4
    assert adaptation['exterior_material_preserved_emitters'] == 2
    assert abs(adaptation['final_opacity_multiplier_after_saturate'] - .40) < .0001
    assert adaptation['spawn_density_size_timing_color_unchanged']
    assert adaptation['mesh_strands_sparks_droplets_unchanged']
    assert adaptation['module_outers_and_gpu_cached_references_valid']
    assert adaptation['gpu_emitter_info_rebuilt'] and not adaptation['invalid_references']
    assert all(str(veil_instance.get_editor_property(key)) == value for key, value in overrides.items())
    library.recompile_material(veil_base)
    for asset in (veil_base, veil_instance, particle):
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False), asset.get_path_name()
    report = {
        'passed': True,
        'q': q_report,
        'w': {'source': W_SOURCE, 'asset': W_TARGET, 'smoke': adaptation,
              'base_material': W_BASE_TARGET, 'instance': W_INSTANCE_TARGET,
              'vamp_parameter_overrides_preserved': True, 'exterior_and_bright_strands_unchanged': True,
              'previous_spawn_density_preserved': True, 'world_scale': 1.0, 'play_rate': 1.95},
    }
    (output / 'assassin-qw-assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
