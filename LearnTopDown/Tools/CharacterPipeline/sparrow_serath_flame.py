"""Burn the actual Serath wing surfaces while preserving their geometry.

The original membrane opacity and world-position-offset graphs are duplicated
as support. Two project-owned surface clones are saved, with no new wing geometry.
The parent owns all editor, GPU, and native build execution.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy

import unreal


MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSerathGoldFlame'
SPLINE_MATERIAL = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowSerathSplineFlame'
MESH = '/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath'
SPLINES = '/Game/ParagonSerath/Characters/Heroes/Serath/Materials/M_NewWingsSplines2'
MEMBRANE = '/Game/ParagonSerath/Characters/Heroes/Serath/Materials/M_WingWebbing_HolyAndEvil2'
FIRE = '/Game/ParagonSerath/FX/Textures/Fire/T_Fire_Tiled_D'
MARKER = 'SparrowSerathGoldFlameShader'
WPO_MARKER = MARKER+'Undulation'


def _write(output, name, value):
    (Path(output)/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def _hashes(root):
    return {path: hashlib.sha256((root/'Content'/Path(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
            for path in (MESH,SPLINES,MEMBRANE)}


def _audit_material(path):
    material = unreal.load_asset(path).get_base_material()
    lib = unreal.MaterialEditingLibrary
    nodes = list(lib.get_material_expressions(material))
    uv_nodes, textures = [], []
    for expression in nodes:
        kind = expression.get_class().get_name()
        if kind == 'MaterialExpressionTextureCoordinate':
            uv_nodes.append({'name':expression.get_name(),
                             'coordinate_index':expression.get_editor_property('coordinate_index'),
                             'u_tiling':expression.get_editor_property('u_tiling'),
                             'v_tiling':expression.get_editor_property('v_tiling')})
        if kind.startswith('MaterialExpressionTextureSample') or kind.startswith('MaterialExpressionTextureObject'):
            texture = expression.get_editor_property('texture')
            textures.append({'name':expression.get_name(),'texture':texture.get_path_name() if texture else None})
    properties = {}
    for label, prop in (('opacity',unreal.MaterialProperty.MP_OPACITY),
                        ('world_position_offset',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)):
        source = lib.get_material_property_input_node(material,prop)
        properties[label] = {'node':source.get_name() if source else None,
                             'class':source.get_class().get_name() if source else None,
                             'output':lib.get_material_property_input_node_output_name(material,prop)}
    return {'material':path,'blend_mode':str(material.get_editor_property('blend_mode')),
            'uv_nodes':uv_nodes,'textures':textures,'property_inputs':properties}


def author(output):
    root = Path(unreal.Paths.project_dir()).resolve()
    output = Path(output).resolve()
    assert output.is_relative_to(root/'Saved/QA')
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    output.mkdir(parents=True,exist_ok=True)
    baseline = _hashes(root)
    lib = unreal.MaterialEditingLibrary
    source_audit = [_audit_material(SPLINES),_audit_material(MEMBRANE)]
    # Save the source evidence before touching the project-owned target.
    mesh = unreal.load_asset(MESH)
    slots = mesh.get_editor_property('materials')
    slot_report = [{'index':i,'name':str(s.get_editor_property('material_slot_name')),
                    'material':s.get_editor_property('material_interface').get_path_name()}
                   for i,s in enumerate(slots) if i in (12,13)]
    _write(output,'serath-source-material-audit.json',{'materials':source_audit,'slots':slot_report})
    assert slot_report[0]['name'] == 'M12_WingSplines' and slot_report[1]['name'] == 'M13_WingMembrane'
    helper = runpy.run_path(str(root/'Tools/CharacterPipeline/sparrow_s_silhouette.py'))
    surfaces = []
    for source_path,target_path,audit in ((MEMBRANE,MATERIAL,source_audit[1]),
                                          (SPLINES,SPLINE_MATERIAL,source_audit[0])):
        target = unreal.load_asset(target_path)
        if target is None:
            target = unreal.EditorAssetLibrary.duplicate_asset(source_path,target_path)
        assert isinstance(target,unreal.Material)
        node,wire = helper['_node'],helper['_wire']
        expressions = list(lib.get_material_expressions(target))
        authored = [n for n in expressions if n.get_editor_property('desc') == MARKER]
        assert len(authored) <= 1
        original_wpo = audit['property_inputs']['world_position_offset']
        source_wpo = next((n for n in expressions if n.get_name() == original_wpo['node']),None)
        assert (source_wpo.get_name() if source_wpo else None) == original_wpo['node']
        undulations = [n for n in expressions if n.get_editor_property('desc') == WPO_MARKER]
        assert len(undulations) <= 1
        current_wpo = lib.get_material_property_input_node(target,unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        assert current_wpo == source_wpo or (undulations and current_wpo == undulations[0])
        code = '''
float3 rel = WorldPos-RootPos;
float sideCoord = dot(rel,SideAxis);
float backCoord = dot(rel,BackAxis);
float riseCoord = rel.z;
// Both actual wing surfaces share this root-relative rising fire field.
// Translation and actor yaw move the field with the caster, never the floor.
float breath = sin(abs(sideCoord)*.019+riseCoord*.014-Clock*1.35);
float ripple = sin(riseCoord*.047-backCoord*.022+Clock*2.15);
float2 flowUV = float2(abs(sideCoord)*.012+backCoord*.004+breath*.16+ripple*.055,
                       -riseCoord*.018+Clock*.65+sideCoord*.001+breath*.055);
float fireA = Texture2DSample(Fire,FireSampler,flowUV).r;
float fireB = Texture2DSample(Fire,FireSampler,flowUV*float2(1.71,.79)+float2(.31,-Clock*.17)).g;
float heat = saturate(fireA*.74+fireB*.34);
float burning = smoothstep(.13,.55,heat);
float hot = pow(smoothstep(.47,.86,heat),1.7);
float rootGlow = 1.0-smoothstep(22.0,70.0,length(rel));
float3 ember = float3(.12,.015,.001);
float3 gold = float3(3.0,1.1,.025);
float3 whiteGold = float3(5.2,3.8,.80);
float3 color = lerp(ember,gold,burning);
color = lerp(color,whiteGold,saturate(hot*.72+rootGlow*.28*burning));
// The old opacity is only a geometry support mask. Fire now owns the active
// surface coverage, opening dark gaps and eroding edges instead of repainting.
float support = saturate(Shape);
float fireOpacity = .12+.86*burning;
fireOpacity = lerp(fireOpacity,.28+.70*burning,rootGlow*.72);
float alpha = support*fireOpacity;
return float4(color,saturate(alpha));
'''
        if authored:
            shader = authored[0]
            shader.set_editor_property('code',code)
            pins = list(shader.get_editor_property('inputs'))
            names = [str(pin.get_editor_property('input_name')) for pin in pins]
            for name in ('SideAxis','BackAxis'):
                if name not in names:
                    pin = unreal.CustomInput()
                    pin.set_editor_property('input_name',name)
                    pins.append(pin)
            shader.set_editor_property('inputs',pins)
        else:
            shape_source = lib.get_material_property_input_node(target,unreal.MaterialProperty.MP_OPACITY)
            shape_output = lib.get_material_property_input_node_output_name(target,unreal.MaterialProperty.MP_OPACITY)
            assert shape_source is not None
            shader = helper['_custom'](target,code,('UV','Clock','Shape','WorldPos','RootPos','Fire','SideAxis','BackAxis'),
                                        unreal.CustomMaterialOutputType.CMOT_FLOAT4)
            shader.set_editor_property('desc',MARKER)
            wire(node(target,'TextureCoordinate',coordinate_index=0),shader,'UV')
            wire(node(target,'Time'),shader,'Clock')
            wire(shape_source,shader,'Shape',shape_output)
            wire(node(target,'WorldPosition'),shader,'WorldPos')
            wire(node(target,'VectorParameter',parameter_name='WingRootPosition',
                      default_value=unreal.LinearColor(0,0,0,0)),shader,'RootPos')
            wire(node(target,'TextureObject',texture=unreal.load_asset(FIRE)),shader,'Fire')
            for prop,channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),
                                  (unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
                mask = node(target,'ComponentMask',r=channels[0],g=channels[1],b=channels[2],a=channels[3])
                wire(shader,mask,lib.get_material_expression_input_names(mask)[0])
                assert lib.connect_material_property(mask,'',prop)
        axis_nodes = {}
        for parameter,pin_name,default in (('WingSideAxis','SideAxis',unreal.LinearColor(0,1,0,0)),
                                           ('WingBackAxis','BackAxis',unreal.LinearColor(-1,0,0,0))):
            existing = [n for n in lib.get_material_expressions(target)
                        if n.get_class().get_name() == 'MaterialExpressionVectorParameter'
                        and str(n.get_editor_property('parameter_name')) == parameter]
            axis_node = existing[0] if existing else node(target,'VectorParameter',parameter_name=parameter,default_value=default)
            wire(axis_node,shader,pin_name)
            axis_nodes[pin_name] = axis_node
        # Keep the duplicated source WPO as an input, adding a bounded wave once.
        # Root anchoring prevents the wing attachment from drifting as it burns.
        undulation_code = '''
float3 rel = WorldPos-RootPos;
float side = abs(dot(rel,SideAxis));
float back = dot(rel,BackAxis);
float anchor = smoothstep(24.0,130.0,length(rel));
float broad = sin(side*.020+rel.z*.013-Clock*1.55);
float fine = sin(side*.043-back*.027+rel.z*.018+Clock*2.25);
float3 wave = BackAxis*(broad*1.30+fine*.30)+float3(0,0,broad*.45+fine*.15);
return ORIGINAL_OFFSET+wave*anchor;
'''.replace('ORIGINAL_OFFSET','OriginalOffset' if source_wpo else 'float3(0,0,0)')
        if undulations:
            undulation = undulations[0]
            undulation.set_editor_property('code',undulation_code)
        else:
            inputs = ('WorldPos','RootPos','Clock','SideAxis','BackAxis')
            if source_wpo:
                inputs += ('OriginalOffset',)
            undulation = helper['_custom'](target,undulation_code,inputs,unreal.CustomMaterialOutputType.CMOT_FLOAT3)
            undulation.set_editor_property('desc',WPO_MARKER)
            wire(node(target,'WorldPosition'),undulation,'WorldPos')
            root_node = next(n for n in lib.get_material_expressions(target)
                             if n.get_class().get_name() == 'MaterialExpressionVectorParameter'
                             and str(n.get_editor_property('parameter_name')) == 'WingRootPosition')
            wire(root_node,undulation,'RootPos')
            wire(node(target,'Time'),undulation,'Clock')
        for pin_name,axis_node in axis_nodes.items():
            wire(axis_node,undulation,pin_name)
        if source_wpo:
            wire(source_wpo,undulation,'OriginalOffset',original_wpo['output'])
        assert lib.connect_material_property(undulation,'',unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        target.set_editor_property('used_with_skeletal_mesh',True)
        target.set_editor_property('two_sided',True)
        lib.recompile_material(target)
        assert unreal.EditorAssetLibrary.save_loaded_asset(target,False)
        surfaces.append({'source':source_path,'target':target_path,'original_wpo_preserved':True,
                         'root_anchored_undulation_added':True,
                         'original_opacity_used_as_support_only':True})
    assert _hashes(root) == baseline
    report = {'passed':True,'material':MATERIAL,'spline_material':SPLINE_MATERIAL,'shape_mesh':MESH,
              'source_material_audit':source_audit,'source_hashes':baseline,'surfaces':surfaces,
              'new_wing_geometry_saved':False,'original_pack_saved':False,'source_wpo_graph_preserved':True,
              'fire_opacity_coverage_range':[.12,.98],'shared_root_relative_fire_coordinates':True,
              'undulation_back_axis_bound_cm':1.6,'undulation_vertical_bound_cm':.6,
              'undulation_anchor_range_cm':[24,130],'surface_flow_has_broad_and_fine_waves':True,
              'intent':'Both original Serath wing materials burn and erode themselves; no fixed membrane repaint or overlay cards.'}
    _write(output,'serath-gold-flame-author.json',report)
    return report


def _clip(rig,name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case':name,'prefix':name+'_video',
                                    'cast_time':unreal.GameplayStatics.get_time_seconds(rig['world']()),'frame_times':[]}


def sequence(rig):
    rig['switch']('sparrow')
    yield .7
    targets = rig['layout']([(700,0),(900,400),(900,-400)])
    yield .2
    body = rig['pawn']().get_editor_property('mesh')
    lod_count = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(body.get_skeletal_mesh_asset())
    materials = [body.get_material(i).get_path_name() for i in range(body.get_num_materials())]
    sections = [[body.is_material_section_shown(i,lod) for i in range(body.get_num_materials())] for lod in range(lod_count)]
    _clip(rig,'S_serath_gold_flame')
    rig['use']('S',targets[0])
    yield .75
    forms = list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowAscensionWings))
    rig['check'](len(forms) == 1,'S creates one original-shape Serath form')
    form = forms[0]
    wings = [p for p in form.get_components_by_class(unreal.SkeletalMeshComponent) if p.get_name() == 'SerathWings']
    rig['check'](len(wings) == 1 and wings[0].is_visible(),'S displays the restored Serath skeletal wing component')
    wing = wings[0]
    rig['check'](wing.get_skeletal_mesh_asset().get_path_name().startswith(MESH+'.'),'S uses the original Serath mesh')
    energy = [p for p in form.get_components_by_class(unreal.StaticMeshComponent)
              if 'SparrowEnergyWings' in [str(t) for t in p.get_editor_property('component_tags')]]
    rig['check'](not energy,'S does not create the rejected energy-band mesh')
    rig['check'](wing.is_material_section_shown(12,0) and wing.is_material_section_shown(13,0),
                 'S restores both original spline and membrane sections')
    rig['check'](wing.get_material(12).get_base_material().get_path_name().startswith(SPLINE_MATERIAL+'.'),
                 'S spline itself uses the dedicated burning surface material')
    rig['check'](wing.get_material(13).get_base_material().get_path_name().startswith(MATERIAL+'.'),
                 'S membrane uses the dedicated flowing gold-flame material')
    rig['check'](rig['skills']().get_ascension_remaining() > 39.0,'S retains40second form lifetime')
    montage = body.get_anim_instance().get_current_active_montage()
    rig['check'](montage is not None and abs(montage.get_play_length()-1.35) < .02,
                 'S uses the extended1.35second transformation montage')
    rig['capture']('S_serath_unfurl')
    if os.environ.get('SPARROW_S_SMOOTH_REVIEW') == '1':
        yield .15
        start = rig['pawn']().get_actor_location()
        goal = rig['ground'](start.x,start.y+250.)
        rig['cmd'](f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield 1./rig['FPS']
        rig['cmd'](f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        yield 1.15-1./rig['FPS']
        rig['check']((rig['pawn']().get_actor_location()-start).length() > 80.,
                     'S smoothly returns to actual queued movement after its extended cast')
    else:
        yield 1.3
    rig['recovered']()
    rig['capture']('S_serath_hold')
    yield 1.0
    rig['finish_video_clip']()
    form.destroy_actor()
    yield .1
    rig['check']([body.get_material(i).get_path_name() for i in range(body.get_num_materials())] == materials,
                 'S restores all original body material overrides')
    restored = [[body.is_material_section_shown(i,lod) for i in range(body.get_num_materials())] for lod in range(lod_count)]
    rig['check'](restored == sections,'S restores original cloak and hood section visibility')
    rig['use']('S',targets[0])
    yield .75
    rig['switch']('countess')
    yield .2
    rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](),unreal.SparrowAscensionWings),
                 'S restored wing actor retires when the owner is replaced')
    _write(rig['OUT'],'serath-gold-flame-review.json',{'passed':True,'mesh':MESH,'membrane_material':MATERIAL,
            'spline_material':SPLINE_MATERIAL,'duration':40,'new_band_mesh_spawned':False,'D_changed':False})
