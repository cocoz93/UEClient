"""Author ASDF-private ink material and sample the source F attack; never edit pack assets."""
import json
import os
import traceback
from pathlib import Path

import unreal

TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessExtraInkQuality2_20261021'
NOISE = '/Game/ParagonCountess/FX/Textures/Tile/Noise/T_Inky_Smoke_Tile'
ANIMATIONS = '/Game/ParagonCountess/Characters/Heroes/Countess/Animations/'


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'asset': TARGET, 'source_noise': NOISE, 'pack_assets_saved': False, 'material_version': 2, 'shape_basis': 'Dedicated plane UV: scars, black filaments, torn wave front, ground erosion, small ink flecks; old S material preserved'}
    report['source_signal'] = {'srgb': True, 'channel': 'R', 'noise_linear_p1_p99': [.0075, .5841],
                               'ink_linear_p1_p99': [.0009, .3140], 'noise_power': .55, 'ink_power': .30,
                               'evidence': 'texture-inspect/channel-distribution.json'}
    try:
        lib = unreal.MaterialEditingLibrary
        material = unreal.load_asset(TARGET)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                TARGET.rsplit('/', 1)[1], TARGET.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())
        assert material is not None
        if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessExtraInkVersion') != '2':
            lib.delete_all_material_expressions(material)
            material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
            material.set_editor_property('two_sided', True)

            def node(kind, **props):
                item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression' + kind))
                for key, value in props.items():
                    item.set_editor_property(key, value)
                return item

            uv = node('TextureCoordinate')
            card = node('ScalarParameter', parameter_name='Card', default_value=1.0)
            mapped = uv
            tiling = node('Multiply')
            assert lib.connect_material_expressions(mapped, '', tiling, 'A')
            assert lib.connect_material_expressions(node('Constant2Vector', r=3.0, g=2.0), '', tiling, 'B')
            pan = node('Panner', speed_x=.025, speed_y=.04)
            assert lib.connect_material_expressions(tiling, '', pan, 'Coordinate')
            texture = unreal.load_asset(NOISE)
            assert texture is not None
            sample = node('TextureSample', texture=texture)
            assert lib.connect_material_expressions(pan, '', sample, 'UVs')
            ink_sample = node('TextureSample', texture=unreal.load_asset('/Game/ParagonCountess/FX/Textures/FluidPatterns/T_InkSmoky_M'))
            assert ink_sample.get_editor_property('texture') is not None
            ink_pan = node('Panner', speed_x=.035, speed_y=-.02)
            assert lib.connect_material_expressions(uv, '', ink_pan, 'Coordinate')
            assert lib.connect_material_expressions(ink_pan, '', ink_sample, 'UVs')
            shader = node('Custom', output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4, code='''
// Source PNG inspection: sRGB textures, R median .1248 / .0091 after linear sampling.
// Normalize measured linear P1..P99 separately, retaining the original source texture settings.
float n=pow(saturate((Noise-.0075)/.5766),.55);
float ink=pow(saturate((Ink-.0009)/.3131),.30);
float2 p=UV*2-1;
float u=UV.x;
float shape=0;
float edge=0;
float charcoal=0;
float grain=smoothstep(.08,.72,n*.55+ink*.45);
float endFade=smoothstep(.0,.10,u)*(1-smoothstep(.90,1,u));
if(Shape<1.5)
{
    float curve=.055*sin(u*13+Seed)+.025*sin(u*31+Seed*2);
    float taper=pow(saturate(1-p.x*p.x),.75);
    float dist=abs(p.y-curve)-(.20*taper+(n-.5)*.065);
    float cut=1-smoothstep(-.035,.055,dist);
    float branch1=exp(-pow((p.y-.38*(p.x+.1))/.075,2))*(1-smoothstep(.14,.55,abs(p.x+.2)));
    float branch2=exp(-pow((p.y+.32*(p.x-.2))/.06,2))*(1-smoothstep(.1,.4,abs(p.x-.35)));
    shape=max(cut,max(branch1,branch2)*.5)*endFade;
    shape*=smoothstep(.06,.30,n+ink*.35);
    edge=exp(-pow((dist+.025)/.055,2))*endFade;
    charcoal=.18;
}
else if(Shape<2.5)
{
    float bend=.20*sin(u*5.4+Seed)+.065*sin(u*14-Seed);
    float strand=exp(-pow((p.y-bend)/.050,2));
    strand+=.55*exp(-pow((p.y-bend-.11*sin(u*8+1))/.035,2));
    strand+=.35*exp(-pow((p.y-bend+.14)/.03,2));
    shape=saturate(strand)*endFade*smoothstep(.03,.40,n+.15);
    edge=shape*pow(grain,2)*.18;
    charcoal=.84;
}
else if(Shape<3.5)
{
    float front=.65-.22*p.y*p.y+.045*sin(p.y*17+Seed)+(n-.5)*.10;
    float leading=1-smoothstep(front-.04,front+.06,u);
    float tail=smoothstep(.0,.25,u);
    float side=1-smoothstep(.48,.96,abs(p.y)+(.5-n)*.12);
    shape=leading*tail*side*pow(smoothstep(.04,.78,n*.45+ink*.75),.85);
    edge=exp(-pow((u-front+.03)/.045,2))*side*grain;
    charcoal=.42;
}
else if(Shape<4.5)
{
    float path=.10*sin(u*8+Seed)+.06*sin(u*19);
    float vein=exp(-pow((p.y-path)/.16,2));
    float branch=exp(-pow((p.y+.40*(p.x-.1))/.095,2))*(1-smoothstep(.2,.8,abs(p.x)));
    shape=max(vein,branch*.65)*endFade*smoothstep(.07,.52,n*.4+ink*.8);
    edge=pow(shape,2)*grain*.24;
    charcoal=.76;
}
else
{
    float fleck=1-smoothstep(.24,.80,abs(p.x)+abs(p.y)*.85+(n-.5)*.30);
    shape=fleck*smoothstep(.04,.52,n+ink*.25);
    edge=shape*grain*.40;
    charcoal=.50;
}
float erosion=1-smoothstep(n*.70+.04,n*.70+.28,1-saturate(Fade));
float density=.10+.78*grain;
if(Shape<1.5) density=.24+.66*grain;
else if(Shape>=2.5 && Shape<3.5) density=.17+.76*grain;
float alpha=saturate(shape*density+edge*.32)*erosion*saturate(Fade)*saturate(Opacity);
float3 body=lerp(float3(.018,.0005,.004),float3(.62,.004,.035),grain);
body=lerp(body,float3(.012,.0005,.0035)*( .5+grain),charcoal);
float3 rim=float3(1.05,.012,.050)*edge*(.45+.55*grain);
return float4((body+rim)*(.90+.22*saturate(Pulse))*saturate(Fade),alpha);
''')
            inputs = []
            for name in ('UV', 'Noise', 'Ink', 'Fade', 'Pulse', 'Card', 'Opacity', 'Shape', 'Seed'):
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', name)
                inputs.append(pin)
            shader.set_editor_property('inputs', inputs)
            for source, pin, channel in ((mapped, 'UV', ''), (sample, 'Noise', 'R'), (ink_sample, 'Ink', 'R'),
                                        (node('ScalarParameter', parameter_name='Fade', default_value=1.0), 'Fade', ''),
                                        (node('ScalarParameter', parameter_name='Pulse', default_value=0.0), 'Pulse', ''),
                                        (card, 'Card', ''),
                                        (node('ScalarParameter', parameter_name='Opacity', default_value=1.0), 'Opacity', ''),
                                        (node('ScalarParameter', parameter_name='Shape', default_value=1.0), 'Shape', ''),
                                        (node('ScalarParameter', parameter_name='Seed', default_value=0.0), 'Seed', '')):
                assert lib.connect_material_expressions(source, channel, shader, pin)
            for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                                   (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
                mask = node('ComponentMask', r=channels[0], g=channels[1], b=channels[2], a=channels[3])
                assert lib.connect_material_expressions(shader, '', mask, lib.get_material_expression_input_names(mask)[0])
                assert lib.connect_material_property(mask, '', prop)
            lib.recompile_material(material)
            unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessExtraInkVersion', '2')
            assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)

        mesh = unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Meshes/SM_Countess')
        animation = unreal.load_asset(ANIMATIONS + 'Primary_Attack_B_Normal')
        assert mesh is not None and animation is not None
        options = unreal.AnimPoseEvaluationOptions()
        options.optional_skeletal_mesh = mesh
        options.evaluation_type = unreal.AnimDataEvalType.RAW
        length = animation.get_play_length()
        samples = []
        for frame in range(int(length * 60) + 1):
            at = min(frame / 60.0, length - .00001)
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(animation, at, options)
            row = {'time': at, 'tips': {}}
            for side in ('L', 'R'):
                v = unreal.AnimPoseExtensions.get_socket_pose(pose, 'FX_WeaponTip_' + side, unreal.AnimPoseSpaces.WORLD).translation
                row['tips'][side] = [v.x, v.y, v.z]
            if samples:
                dt = max(.00001, at - samples[-1]['time'])
                row['tip_speed_sum'] = sum(sum((row['tips'][side][axis] - samples[-1]['tips'][side][axis]) ** 2
                                               for axis in range(3)) ** .5 / dt for side in ('L', 'R'))
            else:
                row['tip_speed_sum'] = 0.0
            samples.append(row)
        candidates = [row for row in samples if .10 <= row['time'] <= min(.65, length * .72)]
        peak = max(candidates, key=lambda row: row['tip_speed_sum'])
        report.update(passed=True, animation=animation.get_path_name(), animation_length=length,
                      proposed_clip_hit_time=peak['time'], proposed_hit_tip_speed_sum=peak['tip_speed_sum'],
                      timing_note='Source-socket speed peak only; verify the visible strike and body pose in PIE.', samples=samples)
        bounds = []
        for name in ('SM_Countess_SwordAbstractMesh', 'SM_Countess_RollingDark_SwordMesh'):
            source = unreal.load_asset('/Game/ParagonCountess/FX/Meshes/Shapes/' + name)
            assert source is not None
            box = source.get_bounding_box()
            bounds.append({'path': source.get_path_name(), 'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]})
        report['source_mesh_bounds'] = bounds
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'countess-extra-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    destination = os.environ.get('SPARROW_QA_OUTPUT') or str(Path(unreal.Paths.project_saved_dir()) / 'QA/CharacterPipeline/new-skills-polish-20261021/countess-materials')
    author(destination)
    unreal.SystemLibrary.quit_editor()
