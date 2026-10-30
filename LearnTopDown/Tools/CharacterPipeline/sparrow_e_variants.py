"""Three scoped E studies on the real rapid-shot cast, never a production install.

Use author(out) before PIE and yield from sequence(rig) in new_skills_probe.
Only this module's preview materials are saved. The native E six shots,
animation and damage remain the fixture. A short-lived PIE plane adds a muzzle
study and selected trails are changed only on that cast's live arrow actors.
"""
import json
import math

import unreal


FOLDER = '/Game/TopDown/Characters/Sparrow/Previews/E20261022'
OPTIONS = ('E1', 'E2', 'E3')
LABELS = {
    'E1': 'Twin crescent recoil',
    'E2': 'Feather constellation',
    'E3': 'Compressed lance flash',
}
TRAILS = {
    'E2': '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/Ultimate/FX/P_Sparrow_UltArrow',
    'E3': '/Game/ParagonSparrow/FX/Particles/Sparrow/Abilities/DrawABead/FX/P_Sparrow_RMB',
}


def formulas():
    return {
        'E1': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float gap=smoothstep(.22,.57,abs(sin(a+.18)));
float radius=.29+.028*(1.-Pulse);
float crescent=pow(saturate(1.-abs(r-radius)*90.),1.25)*gap;
float inner=pow(saturate(1.-abs(r-.205)*125.),1.4)*smoothstep(.45,.75,abs(sin(a-.16)));
float ribs=pow(saturate(1.-abs(sin(a*4.))*18.),1.3)*smoothstep(.32,.335,r)*(1.-smoothstep(.365,.405,r));
float haze=pow(saturate(1.-abs(r-radius)*26.),2.)*gap*.18;
float m=(crescent+inner*.52+ribs*.65+haze)*Pulse;
return float4(float3(4.8,3.35,1.0)*m+float3(1.7,1.7,1.5)*crescent*Pulse,saturate(m*.87));''',
        'E2': '''float2 p=UV-.5; float r=length(p); float a=atan2(p.y,p.x);
float cell=frac((a+3.141593)/6.283185*6.+.07);
float taper=saturate(1.-abs(r-.285)/.14);
float feather=pow(saturate(1.-abs(cell-.5)/(.035+.17*taper)),1.1)*pow(taper,.7);
float rib=pow(saturate(1.-abs(cell-.49)/.024),1.3)*taper;
float stars=pow(saturate(1.-abs(cell-.5)*32.-abs(r-.425)*120.),1.4);
float trace=pow(saturate(1.-abs(r-.19)*125.),1.4)*smoothstep(.5,.85,cos(a*6.+.4));
float glow=pow(saturate(1.-abs(r-.285)*18.),2.)*.10;
float m=(feather*.6+rib*.5+stars*.9+trace*.6+glow)*Pulse;
return float4(float3(4.7,3.4,1.1)*m+float3(1.8,1.8,1.6)*(stars+rib*.6)*Pulse,saturate(m*.9));''',
        'E3': '''float x=UV.x; float y=UV.y-.5;
float span=smoothstep(.06,.16,x)*(1.-smoothstep(.65,.96,x));
float needle=pow(saturate(1.-abs(y)/(.006+.024*(1.-x))),1.5)*span;
float bend=.025+.13*pow(saturate(1.-x),1.45);
float side=pow(saturate(1.-abs(abs(y)-bend)*150.),1.5)*span;
float outer=pow(saturate(1.-abs(abs(y)-bend*1.8)*180.),1.5)*span*.35;
float2 q=float2((x-.18)*1.3,y);
float flash=pow(saturate(1.-abs(q.x)*22.-abs(q.y)*17.),1.5);
float cross=pow(saturate(1.-abs(q.x)*100.),1.5)*pow(saturate(1.-abs(q.y)*7.),2.)*.5;
float m=(needle+side*.8+outer+flash+cross)*Pulse;
return float4(float3(5.1,3.5,1.15)*m+float3(2.,2.,1.8)*(needle+flash)*Pulse,saturate(m*.91));''',
    }


def author(out):
    lib = unreal.MaterialEditingLibrary
    saved = []
    for option, code in formulas().items():
        name = 'M_' + option + '_RapidStudy'
        path = FOLDER + '/' + name
        material = unreal.load_asset(path)
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
        assert material, path
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        custom = lib.create_material_expression(material, unreal.MaterialExpressionCustom)
        custom.set_editor_property('code', code)
        custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        inputs = []
        for input_name in ('UV', 'Pulse'):
            item = unreal.CustomInput()
            item.set_editor_property('input_name', input_name)
            inputs.append(item)
        custom.set_editor_property('inputs', inputs)
        uv = lib.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate)
        pulse = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter)
        pulse.set_editor_property('parameter_name', 'Pulse')
        pulse.set_editor_property('default_value', 1.)
        assert lib.connect_material_expressions(uv, '', custom, 'UV')
        assert lib.connect_material_expressions(pulse, '', custom, 'Pulse')
        for prop, channels in (
                (unreal.MaterialProperty.MP_EMISSIVE_COLOR, (True, True, True, False)),
                (unreal.MaterialProperty.MP_OPACITY, (False, False, False, True))):
            mask = lib.create_material_expression(material, unreal.MaterialExpressionComponentMask)
            for key, enabled in zip(('r', 'g', 'b', 'a'), channels):
                mask.set_editor_property(key, enabled)
            assert lib.connect_material_expressions(custom, '', mask, '')
            assert lib.connect_material_property(mask, '', prop)
        lib.recompile_material(material)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        saved.append(path)
    result = {'passed': True, 'saved_materials': saved, 'production_assets_changed': False,
              'source_pack_assets_saved': False}
    (out / 'E-concept-materials.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def sequence(rig):
    """Capture two moments per candidate, with the same real native E cast/camera."""
    world, pawn, skills = rig['world'], rig['pawn'], rig['skills']
    check, capture = rig['check'], rig['capture']
    now = lambda: unreal.GameplayStatics.get_time_seconds(world())
    rig['switch']('sparrow')
    yield .8
    rows = []
    for index, option in enumerate(OPTIONS):
        rig['case']('sparrow_E_' + option)
        # Reset Relentless by a fresh pawn for comparable six-shot damage between variants.
        if index:
            rig['switch']('countess')
            yield .15
            rig['switch']('sparrow')
            yield .35
        yield .25
        ds = rig['layout']([(750, 0), (750, 350), (750, -350)])
        started = now()
        rig['use']('E', ds[0])
        yield 1 / 60
        check(skills().get_active_skill_number() == 3, 'preview is running the native E cast')
        name = 'SparrowRapidStudy_' + option
        origin = skills().get_arrow_origin()
        rig['cmd'](f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {origin.x} {origin.y} {origin.z}')
        feedback = next((actor for actor in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.StaticMeshActor)
                         if actor.get_name() == name), None)
        check(feedback is not None, 'PIE-only muzzle study surface exists')
        feedback.set_actor_enable_collision(False)
        feedback.set_life_span(1.12)
        feedback.set_editor_property('tags', [unreal.Name('SparrowRapidStudy')])
        surface = feedback.get_editor_property('static_mesh_component')
        surface.set_mobility(unreal.ComponentMobility.MOVABLE)
        surface.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        surface.set_editor_property('generate_overlap_events', False)
        surface.set_editor_property('can_ever_affect_navigation', False)
        surface.set_editor_property('cast_shadow', False)
        surface.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        material = unreal.load_asset(FOLDER + '/M_' + option + '_RapidStudy')
        check(material is not None, 'candidate material exists')
        dynamic = surface.create_dynamic_material_instance(0, material)
        check(dynamic is not None, 'candidate uses a transient instance')
        shots = []
        treated_arrows = set()
        trail = unreal.load_asset(TRAILS[option]) if option in TRAILS else None
        if option in TRAILS:
            check(trail is not None, 'original golden trail candidate exists')
        moments = [.20, .52]
        while now() - started < 1.12:
            elapsed = now() - started
            if unreal.SystemLibrary.is_valid(feedback):
                # Native E releases at .12 + n*.16. This envelope follows that schedule.
                phase = max(0., elapsed - .12) % .16
                pulse = max(0., 1. - phase / .15)
                pulse = .16 + .96 * math.pow(pulse, .55)
                if elapsed > .95:
                    pulse *= max(0., (1.10 - elapsed) / .15)
                rotation = pawn().get_actor_rotation()
                rotation.roll = 0.
                rotation.pitch = 0. if option == 'E3' else 90.
                direction = pawn().get_actor_forward_vector()
                offset = 125. if option == 'E3' else 40.
                feedback.set_actor_location(skills().get_arrow_origin() + direction * offset, False, True)
                feedback.set_actor_rotation(rotation, True)
                size = 2.05 if option == 'E1' else 2.2
                surface.set_world_scale3d(unreal.Vector(3.8, 2.0, 1.) if option == 'E3'
                                         else unreal.Vector(size, size, 1.))
                dynamic.set_scalar_parameter_value('Pulse', pulse)
                surface.set_visibility(elapsed >= .12)
            if trail:
                for arrow in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowArrow):
                    identity = arrow.get_path_name()
                    if arrow.get_owner() != pawn() or identity in treated_arrows:
                        continue
                    treated_arrows.add(identity)
                    for particle in arrow.get_components_by_class(unreal.ParticleSystemComponent):
                        particle.set_template(trail)
                        size = .65 if option == 'E2' else .45
                        particle.set_world_scale3d(unreal.Vector(size, size, size))
                        particle.activate(True)
            if moments and elapsed >= moments[0]:
                label = option + '_rapid_' + str(len(shots))
                capture(label)
                shots.append({'label': label, 'cast_elapsed': round(elapsed, 4)})
                moments.pop(0)
            yield 1 / 60
        yield .55
        rig['recovered']()
        check(not unreal.SystemLibrary.is_valid(feedback), 'short-lived study surface expires')
        check(len(shots) == 2, 'both comparison frames were requested')
        check(rig['health'](ds[0]) < 100., 'native rapid arrows still damage the target')
        rows.append({'option': option, 'name': LABELS[option], 'screenshots': shots,
                     'target_health_after': rig['health'](ds[0]), 'temporary_override': True})
    result = {'passed': True, 'options': rows, 'source': 'actual native E casts in PIE',
              'production_E_changed': False, 'selection_required_for_production': True,
              'visual_review': 'pending'}
    (rig['OUT'] / 'E-concepts.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
