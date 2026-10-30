"""Two temporary D appearances on real mirror actors; production is untouched.

D1: almost absent between attacks, then a short gold-outline echo pulse.
D2: floating upper-body spirit, with the lower body fading below the waist.
Root owns all author, GPU, and native build execution.
"""
import json
import os
from pathlib import Path
import runpy

import unreal


MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowDShadowStudy'


def _write(output,name,value):
    (Path(output)/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def author(output):
    root = Path(unreal.Paths.project_dir()).resolve()
    output = Path(output).resolve()
    assert output.is_relative_to(root/'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True,exist_ok=True)
    helper = runpy.run_path(str(root/'Tools/CharacterPipeline/sparrow_s_silhouette.py'))
    lib,node,wire = unreal.MaterialEditingLibrary,helper['_node'],helper['_wire']
    material = helper['_material'](MATERIAL,False)
    shader = helper['_custom'](material,'''
float rim = pow(saturate(Facing),.85);
float echoPulse = pow(saturate(Pulse),.72);
float height = WorldPos.z-CutBaseZ;
float waistWarp = sin(WorldPos.x*.07+Clock*1.7)*3.0+sin(WorldPos.y*.09-Clock*1.2)*3.0;
float torsoFade = smoothstep(73.0,108.0,height+waistWarp);
torsoFade = lerp(torsoFade,1.0,saturate(KeepWeapon));
float outlineAlpha = .018+echoPulse*(.07+.52*rim);
float spiritRim = pow(saturate(Facing),1.35);
float spiritFlow = .94+.06*sin(height*.14-Clock*1.4+WorldPos.x*.017);
// Keep the torso transparent and let the outer contour carry the form.
// D2 ignores back faces to avoid layered translucent surfaces becoming paint.
float spiritFace = lerp(saturate(FaceSign),1.0,saturate(KeepWeapon));
float spiritAlpha = (.065+.32*spiritRim*spiritFlow+echoPulse*spiritRim*.10)*torsoFade*spiritFace;
float alpha = lerp(outlineAlpha,spiritAlpha,saturate(Mode));
float3 gold = float3(.94,.52,.065)*(.58+.48*rim);
float3 color = gold+float3(.70,.57,.22)*echoPulse*rim;
return float4(color,saturate(alpha));
''',('Facing','Pulse','WorldPos','CutBaseZ','Clock','Mode','KeepWeapon','FaceSign'),unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    wire(node(material,'Fresnel',exponent=2.8,base_reflect_fraction=.025),shader,'Facing')
    wire(node(material,'WorldPosition'),shader,'WorldPos')
    wire(node(material,'Time'),shader,'Clock')
    wire(node(material,'TwoSidedSign'),shader,'FaceSign')
    for name,value in (('Pulse',0.0),('CutBaseZ',0.0),('Mode',0.0),('KeepWeapon',0.0)):
        wire(node(material,'ScalarParameter',parameter_name=name,default_value=value),shader,name)
    for prop,channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),
                          (unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
        mask = node(material,'ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
        wire(shader,mask,lib.get_material_expression_input_names(mask)[0])
        assert lib.connect_material_property(mask,'',prop)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material,False)
    report = {'passed':True,'preview_material':MATERIAL,'production_assets_saved':False,
              'D1':'Near-absent at rest, actual echo-count increase drives a .28second gold outline pulse.',
              'D2':'Rim-first upper spirit, .065 fill/.32 rim, no back-face accumulation; lower body fades73-108cm, whole bow retained.'}
    _write(output,'partner-study-author.json',report)
    return report


def _now(rig):
    return unreal.GameplayStatics.get_time_seconds(rig['world']())


def _clones(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowMirrorArcher))


def _clip(rig,name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case':name,'prefix':name+'_video','cast_time':_now(rig),'frame_times':[]}


def _preview_materials(mesh,source,mode):
    body = mesh.create_dynamic_material_instance(0,source)
    assert body is not None
    weapon_slots = {mesh.get_material_index(name) for name in ('M11_Arrow','M12_String','M17_Bow')}
    for index in range(mesh.get_num_materials()):
        mesh.set_material(index,body)
    materials = [body]
    for index in sorted(weapon_slots):
        if index < 0:
            continue
        weapon = mesh.create_dynamic_material_instance(index,source)
        assert weapon is not None
        weapon.set_scalar_parameter_value('KeepWeapon',1.0)
        materials.append(weapon)
    for material in materials:
        material.set_scalar_parameter_value('Mode',float(mode))
        material.set_scalar_parameter_value('Pulse',0.0)
        material.set_scalar_parameter_value('CutBaseZ',mesh.get_world_location().z)
    return materials


def _pulse(rig,clone,mesh,materials,state):
    now = _now(rig)
    count = clone.get_echo_shot_count()
    if count > state['count']:
        state['pulses'].append({'time':now,'count':count})
        state['last_pulse'] = now
        state['count'] = count
    value = max(0.0,1.0-(now-state['last_pulse'])/.28)
    for material in materials:
        material.set_scalar_parameter_value('Pulse',value)
        material.set_scalar_parameter_value('CutBaseZ',mesh.get_world_location().z)
    return value


def sequence(rig):
    source = unreal.load_asset(MATERIAL)
    rig['check'](isinstance(source,unreal.Material),'D preview material is authored before the studies')
    report = {'passed':False,'temporary_only':True,'production_D_changed':False,'options':[]}
    selected = [value.strip().upper() for value in os.environ.get('SPARROW_PARTNER_STUDY_OPTIONS','D1,D2').split(',') if value.strip()]
    assert selected and all(value in ('D1','D2') for value in selected),selected
    for mode,name in ((0,'D1_attack_outline'),(1,'D2_upper_spirit')):
        if ('D1' if mode == 0 else 'D2') not in selected:
            continue
        rig['switch']('countess')
        yield .2
        rig['switch']('sparrow')
        yield .7
        targets = rig['layout']([(900,0),(900,420),(900,-420)])
        yield .2
        pawn = rig['pawn']()
        rig['use']('D',targets[0])
        yield .95
        clones = _clones(rig)
        rig['check'](len(clones) == 1,name+' uses the real single D partner actor')
        clone = clones[0]
        meshes = list(clone.get_components_by_class(unreal.SkeletalMeshComponent))
        rig['check'](len(meshes) == 1,name+' partner has one wingless source mesh')
        mesh = meshes[0]
        original = [mesh.get_material(i) for i in range(mesh.get_num_materials())]
        materials = _preview_materials(mesh,source,mode)
        state = {'count':clone.get_echo_shot_count(),'last_pulse':-1000.0,'pulses':[]}
        _clip(rig,name)
        for _ in range(max(1,round(.20*rig['FPS']))):
            _pulse(rig,clone,mesh,materials,state)
            yield 1.0/rig['FPS']
        rig['capture'](name+'_rest')
        start = pawn.get_actor_location()
        goal = rig['ground'](start.x,start.y+300.0)
        rig['use']('W',targets[0])
        started = _now(rig)
        pressed,released,captured = False,False,False
        press_time = -1000.0
        while _now(rig)-started < 1.85:
            elapsed = _now(rig)-started
            pulse = _pulse(rig,clone,mesh,materials,state)
            if state['pulses'] and not captured and _now(rig)-state['pulses'][0]['time']+.0001 >= 2.0/rig['FPS']:
                captured = True
                rig['capture'](name+'_echo')
            # A real short right-click during W exercises the actual queued
            # navigation path; no actor teleport produces the movement clip.
            if elapsed >= .35 and not pressed:
                rig['cmd'](f'CountessComboQA.Mouse Move Left {goal.x} {goal.y} {goal.z}')
                rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                pressed,press_time = True,_now(rig)
            if pressed and not released and _now(rig)-press_time >= 1.0/rig['FPS']-.0001:
                rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                released = True
            yield 1.0/rig['FPS']
        rig['capture'](name+'_after_move')
        rig['finish_video_clip']()
        moved = (pawn.get_actor_location()-start).length()
        rig['check'](state['count'] >= 1 and len(state['pulses']) >= 1,name+' pulse follows an actual W echo')
        rig['check'](moved > 90.0,name+' clip contains actual click navigation')
        rig['check'](all(mesh.get_material(i).get_base_material().get_path_name().startswith(MATERIAL+'.')
                         for i in range(mesh.get_num_materials())),name+' preview stays isolated from the native material pointer')
        report['options'].append({'name':name,'mode':mode,'moved_cm':moved,'pulses':state['pulses'],
                                   'production_materials_restored':True,'preview_material':MATERIAL,
                                   'echo_poster_delay_frames':2})
        for index,material in enumerate(original):
            mesh.set_material(index,material)
        rig['switch']('countess')
        yield .2
        rig['check'](not _clones(rig),name+' mirror and preview MIDs retire with their owner')
    report['passed'] = True
    _write(rig['OUT'],'partner-shadow-studies.json',report)
