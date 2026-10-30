"""Scoped cadence check and three W material studies in the existing PIE runner.

Preview materials are separate from the explicitly approved production install mode.
"""
import json
import os
from pathlib import Path
import runpy
import unreal

FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/W20261022'
REFINED_FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/WRefined20261022'


def refined_formulas():
    return {
        'A1': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float cut=smoothstep(.12,.36,abs(sin(a*2.+.45)));
float cut2=smoothstep(.2,.5,abs(sin(a*2.-.45)));
float core=pow(saturate(1.-abs(r-.335)*90.),1.4)*cut;
float inner=pow(saturate(1.-abs(r-.265)*100.),1.4)*cut2;
float outer=pow(saturate(1.-abs(r-.395)*150.),1.5)*smoothstep(.55,.85,cos(a*6.));
float glow=pow(saturate(1.-abs(r-.335)*25.),2.)*cut*.3;
float m=core+inner*.75+outer*.55+glow;
return float4(float3(5.4,3.6,1.15)*m+float3(2.,2.,1.8)*(core+inner*.4),saturate(m*.86));''',
        'A2': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float cut=smoothstep(.14,.38,abs(sin(a*2.+.45)));
float core=pow(saturate(1.-abs(r-.29)*95.),1.3)*cut;
float outer=pow(saturate(1.-abs(r-.405)*170.),1.4)*cut*.6;
float cell=abs(frac((a+3.141593)/6.283185*12.+.25)-.5);
float glyph=pow(saturate(1.-cell*14.),1.5)*smoothstep(.325,.34,r)*(1.-smoothstep(.375,.39,r));
float feet=pow(saturate(1.-abs(r-.35)*180.),1.3)*saturate(1.-cell*5.5);
float halo=pow(saturate(1.-abs(r-.29)*25.),2.)*cut*.26;
float m=core+outer+glyph*.85+feet*.55+halo;
return float4(float3(5.4,3.6,1.15)*m+float3(2.,2.,1.8)*core,saturate(m*.85));''',
        'A3': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float cut=smoothstep(.10,.30,abs(sin(a*2.+.45)));
float cell=frac((a+3.141593)/6.283185*10.+r*1.6);
float taper=saturate(1.-abs(r-.335)/.105);
float blade=pow(saturate(1.-abs(cell-.5)/(.025+.18*taper)),1.1)*pow(taper,.65)*cut;
float rib=pow(saturate(1.-abs(cell-.46)/.025),1.4)*taper*cut;
float core=pow(saturate(1.-abs(r-.265)*110.),1.4)*cut;
float glow=pow(saturate(1.-abs(r-.34)*17.),2.)*cut*.16;
float m=blade*.75+rib*.55+core*.75+glow;
return float4(float3(5.5,3.8,1.3)*m+float3(2.,2.,1.8)*(rib*.6+core),saturate(m*.85));''',
        'A4': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float cut=smoothstep(.12,.34,abs(sin(a*2.+.45)));
float radius=.325+.012*sin(a*7.)+.006*sin(a*19.);
float core=pow(saturate(1.-abs(r-radius)*100.),1.35)*cut;
float doubleArc=pow(saturate(1.-abs(r-radius+.028)*145.),1.5)*cut*.5;
float cell=abs(frac((a+3.141593)/6.283185*9.+.17)-.5);
float shard=pow(saturate(1.-cell/(.035+.075*saturate((.44-r)/.075))),1.3)*smoothstep(.355,.375,r)*(1.-smoothstep(.405,.465,r));
float halo=pow(saturate(1.-abs(r-radius)*25.),2.)*cut*.24;
float m=core+doubleArc+shard*.8+halo;
return float4(float3(5.4,3.6,1.15)*m+float3(2.2,2.2,1.9)*core,saturate(m*.88));'''
    }


def author(out):
    lib = unreal.MaterialEditingLibrary
    formulas = {
        'A': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float arc=smoothstep(.28,.58,abs(sin(a*2.+.35)));
float core=pow(saturate(1.-abs(r-.34)*75.),1.4)*arc;
float haze=pow(saturate(1.-abs(r-.34)*22.),2.)*arc*.3;
float m=core+haze; return float4(float3(5.,3.5,1.3)*m+core*2.,saturate(m*.8));''',
        'B': '''float x=UV.x; float y=abs(UV.y-.5);
float taper=smoothstep(.03,.19,x)*(1.-smoothstep(.78,.99,x));
float curve=.035+.38*pow(saturate(1.-x),1.5);
float core=pow(saturate(1.-abs(y-curve)*80.),2.);
float fine=pow(saturate(1.-abs(y-curve*.72)*130.),2.)*.5;
float glow=pow(saturate(1.-abs(y-curve)*22.),2.)*.25;
float m=(core+fine+glow)*taper; return float4(float3(6.,4.,1.25)*m+core*taper*1.5,saturate(m*.85));''',
        'C': '''float x=UV.x; float y=abs(UV.y-.5);
float taper=smoothstep(.02,.3,x)*(1.-smoothstep(.86,.99,x));
float core=pow(saturate(1.-y/(.007+.025*(1.-x))),2.)*taper;
float wake=pow(saturate(1.-abs(y-(.06+.13*(1.-x)))*140.),2.)*taper*.45;
float tip=saturate(1.-abs(x-.82)*24.-y*28.);
float m=core+wake+tip; return float4(float3(6.,4.,1.1)*m+float3(5.,5.,4.)*(core+tip),saturate(m*.9));'''
    }
    install = os.environ.get('SPARROW_W_INSTALL') == '1'
    refined = os.environ.get('SPARROW_W_REFINED') == '1' or install
    if refined:
        formulas = refined_formulas()
    folder = REFINED_FOLDER if refined else FOLDER
    names = {name: 'M_WOption' + name for name in formulas}
    if install:
        formulas = {name: formulas[name] for name in ('A1', 'A3')}
        folder = '/Game/TopDown/Characters/Sparrow/Materials'
        names = {'A1': 'M_SparrowShotSplitRing', 'A3': 'M_SparrowGearFeather'}
    saved = []
    for name, formula in formulas.items():
        asset_name = names[name]
        path = folder + '/' + asset_name
        material = unreal.load_asset(path)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(asset_name, folder,
                unreal.Material, unreal.MaterialFactoryNew())
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
        custom = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
        custom.set_editor_property('code', formula)
        custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        uv_input = unreal.CustomInput()
        uv_input.set_editor_property('input_name', 'UV')
        custom.set_editor_property('inputs', [uv_input])
        assert lib.connect_material_expressions(uv, '', custom, 'UV')
        source = custom
        if refined:
            strength = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
            strength.set_editor_property('parameter_name', 'Envelope' if install else 'Strength')
            strength.set_editor_property('default_value', 1.)
            source = lib.create_material_expression(material, unreal.MaterialExpressionMultiply)
            assert lib.connect_material_expressions(custom, '', source, 'A')
            assert lib.connect_material_expressions(strength, '', source, 'B')
        for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True,True,True,False)),
                               (unreal.MaterialProperty.MP_OPACITY, (False,False,False,True))):
            mask = lib.create_material_expression(material, unreal.MaterialExpressionComponentMask)
            for key, enabled in zip(('r','g','b','a'), channels):
                mask.set_editor_property(key, enabled)
            assert lib.connect_material_expressions(source, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        saved.append(path)
    result = {'passed': True, 'saved_materials': saved, 'approved_production_assets': install,
              'source_pack_assets_saved': False}
    (out / 'W-concept-materials.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def refined_sequence(rig):
    """Same real W release and camera; static shape studies, no gameplay changes."""
    world = rig['world']
    rig['switch']('sparrow')
    yield .8
    for option in ('A1', 'A2', 'A3', 'A4'):
        rig['case']('W_refined_' + option)
        ds = rig['layout']([(650, 0), (750, 350), (750, -350)])
        yield .25
        rig['use']('W', ds[0])
        waves = []
        for _ in range(90):
            yield 1/60
            waves = list(unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowShotWave))
            if waves:
                break
        rig['check'](bool(waves), 'real W release provides the refined study fixture')
        yield .08
        wave = waves[0]
        wave.set_actor_tick_enabled(False)
        material = unreal.load_asset(REFINED_FOLDER + '/M_WOption' + option)
        meshes = sorted(wave.get_components_by_class(unreal.StaticMeshComponent), key=lambda c: c.get_name())
        for i, mesh in enumerate(meshes):
            dynamic = mesh.create_dynamic_material_instance(0, material)
            dynamic.set_scalar_parameter_value('Strength', (1., .5, .25)[i])
            mesh.set_visibility(i < (3 if option == 'A4' else 2))
            diameter = (2.75, 1.7, .95)[i]
            mesh.set_relative_location(unreal.Vector(60+i*95, 0, 0), False, True)
            mesh.set_relative_scale3d(unreal.Vector(diameter, diameter, 1.))
        yield 1/60
        rig['capture']('W_refined_' + option)
        yield 1.5
        rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowShotWave),
                     'refined preview wave expires normally')
        rig['recovered']()


def installed_sequence(rig):
    """Check the adopted W/A visuals without replacing live actors or materials."""
    world, check = rig['world'], rig['check']
    rig['switch']('sparrow')
    yield .8
    rig['case']('sparrow_W_A1_installed')
    ds = rig['layout']([(650, 0), (750, 350), (750, -350)])
    yield .25
    rig['use']('W', ds[0])
    waves = []
    for _ in range(90):
        yield 1/60
        waves = list(unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowShotWave))
        if waves:
            break
    check(len(waves) == 1, 'W releases one native wave actor')
    wave = waves[0]
    meshes = wave.get_components_by_class(unreal.StaticMeshComponent)
    check(len(meshes) == 2, 'W uses the two selected A1 depth layers')
    check(all(mesh.get_material(0).get_base_material().get_name() == 'M_SparrowShotSplitRing' for mesh in meshes),
          'W uses the production A1 material without a preview override')
    for index, delay in enumerate((.05, .065, .085)):
        yield delay
        rig['capture']('W_A1_live_' + str(index))
    yield 1.7
    check(abs(rig['health'](ds[0])-65) < .01, 'W retains its 35 damage')
    check(not unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowShotWave), 'W layers expire')
    rig['recovered']()
    rig['case']('sparrow_A_feather_installed')
    ds = rig['layout']([(450, 0), (750, 0), (450, 350)])
    yield .25
    rig['use']('A', ds[0])
    yield .75
    arrows = list(unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowGearArrow))
    check(len(arrows) == 1, 'A releases one native slow projectile')
    arrow = arrows[0]
    rings = [mesh for mesh in arrow.get_components_by_class(unreal.StaticMeshComponent)
             if mesh.get_material(0) and mesh.get_material(0).get_base_material().get_name() == 'M_SparrowGearFeather']
    check(len(rings) == 2, 'A uses two production feather ring layers')
    check(arrow.get_editor_property('collision_radius') == 70., 'A keeps its existing collision radius')
    check(rig['health'](ds[0]) == 100, 'A keeps slow travel before reaching the target')
    rig['capture']('A_feather_live_0')
    start = arrow.get_actor_location()
    started = unreal.GameplayStatics.get_time_seconds(world())
    yield .25
    elapsed = unreal.GameplayStatics.get_time_seconds(world()) - started
    speed = rig['dist'](start, arrow.get_actor_location()) / elapsed
    check(abs(speed-320.) < .5, 'A keeps its 320 cm/s travel speed')
    rig['capture']('A_feather_live_1')
    yield .95
    rig['capture']('A_feather_live_2')
    yield 2.1
    check(all(abs(rig['health'](d)-10) < .01 for d in ds[:2]), 'A pierces both path targets once for 90 damage')
    check(rig['health'](ds[2]) == 100, 'A still excludes the lateral target')
    rig['recovered']()
    yield 2.7
    check(not unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowGearArrow), 'A and its feather layers expire')
    rig['case']('sparrow_A_feather_owner_end')
    ds = rig['layout']([(450, 0), (750, 0), (450, 350)])
    yield .25
    rig['use']('A', ds[0])
    yield .6
    check(bool(unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowGearArrow)), 'A is in flight before switching')
    rig['switch']('countess')
    yield .7
    check(not unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowGearArrow), 'character switch cleans the feather projectile')
    rig['switch']('sparrow')
    yield .7
    rig['recovered']()
    (rig['OUT'] / 'adopted-visuals.json').write_text(json.dumps({'passed': True, 'A_speed': speed,
        'W_material': 'M_SparrowShotSplitRing', 'A_material': 'M_SparrowGearFeather',
        'runtime_overrides': False}, indent=2), encoding='utf-8')


def sequence(rig):
    out, state = rig['OUT'], rig['STATE']
    pawn, world, cmd = rig['pawn'], rig['world'], rig['cmd']
    case, check, capture = rig['case'], rig['check'], rig['capture']
    now = lambda: unreal.GameplayStatics.get_time_seconds(world())
    rig['switch']('sparrow')
    yield .8
    case('attack_flow_single')
    ds = rig['layout']([(450,0),(650,350),(750,-350)])
    yield .25
    q = rig['aim'](ds[0])
    anim = pawn().get_editor_property('mesh').get_anim_instance()
    cooldown = pawn().get_editor_property('combo_restart_cooldown')
    check(abs(cooldown - .08/1.8) < .0001, 'post-montage wait reduced from 0.167 to 0.044 seconds')
    started = now()
    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
    yield 1/60
    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
    trace = []
    for i in range(44):
        montage = anim.get_current_active_montage()
        trace.append({'elapsed': now()-started, 'attacking': pawn().is_attacking(),
                      'montage': montage.get_name() if montage else '',
                      'position': anim.montage_get_position(montage) if montage else None})
        if i in (7,17,27):
            capture('flow_single_' + str(i))
        yield 1/60
    check(all(r['attacking'] for r in trace if r['elapsed'] < .51), 'short click commits the full sped-up shot')
    check(not pawn().is_attacking(), 'single shot returns to idle')
    check(abs(rig['health'](ds[0])-80) < .01, 'single click releases exactly one normal arrow')
    case('attack_flow_held')
    ds = rig['layout']([(450,0),(650,350),(750,-350)])
    yield .25
    q = rig['aim'](ds[0])
    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
    starts, idle_gaps, last_idle, was_active = [now()], [], None, True
    hold_started = now()
    for i in range(120):
        yield 1/60
        active = pawn().is_attacking()
        if was_active and not active:
            last_idle = now()
        if active and not was_active:
            starts.append(now())
            if last_idle is not None:
                idle_gaps.append(now()-last_idle)
        was_active = active
    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
    intervals = [b-a for a,b in zip(starts,starts[1:])]
    check(len(starts) >= 3 and all(.54 < t < .7 for t in intervals), 'held shots repeat without restarting an unfinished montage')
    check(idle_gaps and max(idle_gaps) <= .08, 'held-shot idle gaps stay within 0.08 seconds including frame scheduling')
    yield .7
    rig['recovered']()
    case('attack_flow_cancel')
    ds = rig['layout']([(450,0),(650,350),(750,-350)])
    yield .25
    check(pawn().try_basic_attack(ds[0].get_actor_location()), 'cancel fixture starts a shot')
    yield 1/60
    anim.montage_stop(.02)
    yield .7
    check(rig['health'](ds[0]) == 100, 'explicit interruption before release cancels damage')
    rig['recovered']()
    q = rig['aim'](offset=(0,220))
    before = pawn().get_actor_location()
    cmd(f'CountessComboQA.Mouse Press Right {q.x} {q.y} {q.z}')
    yield 1/60
    cmd(f'CountessComboQA.Mouse Release Right {q.x} {q.y} {q.z}')
    yield .6
    check(rig['dist'](pawn().get_actor_location(),before) > 50, 'movement resumes after the attack')
    (out/'attack-flow.json').write_text(json.dumps({'single':trace,'held_starts':starts,
        'held_intervals':intervals,'idle_gaps':idle_gaps,'restart_cooldown':cooldown},indent=2),encoding='utf-8')
    for option in ('current','A','B','C'):
        case('W_concept_'+option)
        ds = rig['layout']([(650,0),(750,350),(750,-350)])
        yield .25
        rig['use']('W',ds[0])
        waves = []
        for i in range(90):
            yield 1/60
            waves = list(unreal.GameplayStatics.get_all_actors_of_class(world(),unreal.SparrowShotWave))
            if waves:
                break
        check(bool(waves),'real W release provides the study fixture')
        yield .08
        wave = waves[0]
        if option != 'current':
            wave.set_actor_tick_enabled(False)
            material = unreal.load_asset(FOLDER+'/M_WOption'+option)
            meshes = sorted(wave.get_components_by_class(unreal.StaticMeshComponent),key=lambda c:c.get_name())
            for i, mesh in enumerate(meshes):
                mesh.set_material(0,material)
                mesh.set_visibility(i < (2 if option == 'A' else 1))
                if option == 'A':
                    mesh.set_relative_location(unreal.Vector(60+i*100,0,0),False,True)
                    mesh.set_relative_scale3d(unreal.Vector(1.9-i*.8,1.9-i*.8,1))
                else:
                    mesh.set_relative_rotation(unreal.Rotator(0,0,0),False,True)
                    mesh.set_relative_location(unreal.Vector(120 if option=='B' else 235,0,0),False,True)
                    mesh.set_relative_scale3d(unreal.Vector(3.4,3.0,1) if option=='B' else unreal.Vector(5.2,1.9,1))
        yield 1/60
        capture('W_option_'+option)
        yield 1.5
        check(not unreal.GameplayStatics.get_all_actors_of_class(world(),unreal.SparrowShotWave),'preview wave expires normally')
        rig['recovered']()
    helper = Path(unreal.Paths.project_dir())/'Tools/CharacterPipeline/sparrow_bow_audit.py'
    if helper.exists():
        bow = runpy.run_path(str(helper))
        # The read-only inventory and presentation callback share this render session.
        if 'audit' in bow:
            bow['audit'](out)
        if 'preview_sequence' in bow:
            yield from bow['preview_sequence'](rig)
