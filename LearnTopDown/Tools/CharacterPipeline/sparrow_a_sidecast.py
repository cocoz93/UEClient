"""A-only wake material and read-only authored bow-pose audition.

author(out) is safe before PIE. sequence(rig) records the installed A cast;
SPARROW_A_AUDITION=1 records candidate original clips without installing them.
"""
import json
import math
import os
from pathlib import Path

import unreal


ANIMS = '/Game/ParagonSparrow/Characters/Heroes/Sparrow/Animations/'
MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowGearWake'
CANDIDATES = ('Primary_Fire_Fast', 'Primary_Fire_Med', 'R_Ability_Fast_Fire', 'R_Ability_Med_Fire', 'R_Ability_Slow_Fire',
              'RMB_Drawback', 'RMB_Loop', 'RMB_Fire')


def author(out):
    out = Path(out)
    result = {'passed': False, 'source_assets_saved': False, 'pose_candidates': []}
    options = unreal.AnimPoseEvaluationOptions()
    for name in CANDIDATES:
        clip = unreal.load_asset(ANIMS + name)
        assert isinstance(clip, unreal.AnimSequence), name
        row = {'name': name, 'length': clip.get_play_length(), 'samples': []}
        for fraction in (0., .1, .25, .5, .75, .95):
            seconds = clip.get_play_length() * fraction
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(clip, seconds, options)
            bones = {}
            for bone in ('bow_shaft_top_03', 'bow_shaft_bott_03', 'bow_base', 'hand_l', 'hand_r'):
                transform = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
                v = transform.translation
                bones[bone] = [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
            top, bottom = bones['bow_shaft_top_03'], bones['bow_shaft_bott_03']
            d = [a-b for a, b in zip(top, bottom)]
            length = math.sqrt(sum(v*v for v in d))
            row['samples'].append({'seconds': seconds, 'bones': bones,
                                   'bow_vertical_fraction': abs(d[2])/max(length, .001)})
        result['pose_candidates'].append(row)
    lib = unreal.MaterialEditingLibrary
    material = unreal.load_asset(MATERIAL)
    if material is None:
        folder, name = MATERIAL.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    assert isinstance(material, unreal.Material)
    lib.delete_all_material_expressions(material)
    for key, value in {'blend_mode': unreal.BlendMode.BLEND_ADDITIVE,
                       'shading_model': unreal.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True, 'used_with_instanced_static_meshes': True}.items():
        material.set_editor_property(key, value)

    def node(kind, **properties):
        value = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
        for key, setting in properties.items():
            value.set_editor_property(key, setting)
        return value

    def wire(a, b, pin, output=''):
        assert lib.connect_material_expressions(a, output, b, pin)

    code = '''
// UV.x runs from the fading rear to the projectile; retain dark gaps between strands.
float x = saturate(UV.x);
float y = UV.y - .5;
float envelope = smoothstep(.015,.25,x) * (1.-smoothstep(.92,1.,x));
float taper = .10 + .18*x;
float mask = 0.;
float core = 0.;
for (int i = -2; i <= 2; ++i) {
    float bend = float(i) * taper * .43;
    bend += sin(x*11.-Clock*9.+float(i)*1.9) * .016 * (1.-x);
    float width = .008 + .010*x;
    float strand = pow(saturate(1.-abs(y-bend)/width), 1.8);
    float pulse = .40 + .60*pow(saturate(sin(x*25.+Clock*15.+float(i)*1.7)),2.);
    mask += strand * pulse;
    core += strand * .18;
}
float haze = pow(saturate(1.-abs(y)/(.035+.09*x)),3.)*.07;
float alpha = saturate((mask+haze)*envelope*.67);
float3 color = float3(2.4,1.65,.32) + float3(.6,.6,.48)*core;
return float4(color, alpha);
'''
    custom = node('Custom', code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    inputs = []
    for name in ('UV', 'Clock'):
        value = unreal.CustomInput()
        value.set_editor_property('input_name', name)
        inputs.append(value)
    custom.set_editor_property('inputs', inputs)
    wire(node('TextureCoordinate'), custom, 'UV')
    wire(node('Time'), custom, 'Clock')
    for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                           (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
        mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
        wire(custom, mask, lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask, '', prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    result.update(passed=True, saved_material=MATERIAL, shader_compilation_verified=False,
                  shader_validation='Recompile/save schedules shaders; inspect the next PIE log and actual wake image')
    (out/'sparrow-a-sidecast-assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def sequence(rig):
    rig['switch']('sparrow')
    yield .7
    mesh = rig['pawn']().get_editor_property('mesh')
    if os.environ.get('SPARROW_A_AUDITION') == '1':
        original_class = mesh.get_anim_instance().get_class()
        try:
            for name in CANDIDATES:
                rig['case']('A_sidecast_audition_' + name)
                rig['layout']([(700, 250), (800, 450), (850, -350)])
                asset = unreal.load_asset(ANIMS+name)
                mesh.play_animation(asset, False)
                yield min(.15, asset.get_play_length()*.3)
                rig['capture']('A_pose_' + name)
        finally:
            mesh.set_anim_instance_class(original_class)
            mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
        return
    rig['case']('A_slow_sidecast_wake')
    ds = rig['layout']([(450, 0), (750, 0), (450, 350)])
    yield .2
    rig['use']('A', ds[0])
    samples = []
    for frame in range(round(rig['FPS']*5.8)):
        yield 1/rig['FPS']
        if frame < round(rig['FPS']*2.4):
            rig['capture']('A_sidecast_video_%04d' % frame)
        if frame == round(rig['FPS']*.33):
            rig['capture']('A_sidecast_release_pose')
            top = mesh.get_socket_location('bow_shaft_top_03')
            bottom = mesh.get_socket_location('bow_shaft_bott_03')
            axis = top-bottom
            samples.append({'bow_vertical_fraction': abs(axis.z)/max(axis.length(), .001)})
        if frame == round(rig['FPS']*1.5):
            rig['capture']('A_sidecast_wake')
    arrows = rig['tagged']('SparrowGearArrow')
    rig['check'](len(arrows) == 1 and abs(arrows[0].get_flight_speed()-150.) < .01,
                 'A speed is 150 cm per second')
    wake = [c for c in arrows[0].get_components_by_class(unreal.StaticMeshComponent)
            if c.get_name().startswith('GearWake')]
    rig['check'](len(wake) == 2 and all(c.is_visible() and c.get_material(0).get_path_name().startswith(MATERIAL) for c in wake),
                 'A owns two visible isolated wake planes')
    rig['check'](len(samples) == 1 and samples[0]['bow_vertical_fraction'] < .45,
                 'A casts with the authored horizontal bow posture')
    rig['check'](rig['health'](ds[0]) == 10 and rig['health'](ds[1]) == 10 and rig['health'](ds[2]) == 100,
                 'A retains single 90-damage piercing hits and side exclusion')
    rig['recovered']()
    rig['switch']('countess')
    yield .3
    rig['check'](not rig['tagged']('SparrowGearArrow'), 'A and attached wake retire when its owner ends')
    rig['switch']('sparrow')
    yield .6
    rig['case']('A_sidecast_cancel')
    ds = rig['layout']([(450, 0), (750, 0), (450, 350)])
    rig['use']('A', ds[0])
    yield .16
    rig['pawn']().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    yield .9
    rig['check'](not rig['tagged']('SparrowGearArrow') and all(rig['health'](d) == 100 for d in ds),
                 'cancelled horizontal A does not release a late arrow')
    rig['recovered']()
    (rig['OUT']/'sparrow-a-sidecast.json').write_text(json.dumps({'pose_samples': samples, 'passed': True,
        'speed': 150, 'source_assets_saved': False}, indent=2), encoding='utf-8')
