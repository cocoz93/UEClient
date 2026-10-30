"""Read Sparrow skin/bow structure before PIE; preview during PIE; save no assets.

audit(output) writes sparrow-bow-audit.json and never changes a player or map.
preview_sections(actor, skin, material_slots, lods, leader) works ONLY on an explicitly tagged
SkeletalMeshActor supplied by the caller; its section mask is component-local.
Material names are candidate hints, not proof that a section contains only bow.
"""
import json
import os
from pathlib import Path
import traceback

import unreal


HERO = '/Game/ParagonSparrow/Characters/Heroes/Sparrow'
SKINS = {
    'base': HERO + '/Meshes/Sparrow',
    **{name: HERO + '/Skins/' + name + '/Meshes/Sparrow_' + name
       for name in ('Rogue', 'AutumnFire', 'FelineQueen', 'Monarch', 'Raven', 'Tough', 'ZechinHuntress')},
}
PREVIEW_TAG = 'SparrowBowAuditPreview'


def _path(obj):
    return obj.get_path_name() if obj else None


def _vector(value):
    return [value.x, value.y, value.z]


def _validate_lods(lods, material_count):
    if not lods:
        raise ValueError('No LOD mapping; audit must run before PIE')
    for row in lods:
        if row.get('vertices', 0) <= 0 or not row.get('sections'):
            raise ValueError('LOD ' + str(row.get('lod')) + ' has no vertices/sections; editor query did not succeed')
        for section in row['sections']:
            if not 0 <= section['material_slot'] < material_count:
                raise ValueError('Invalid material slot in LOD ' + str(row['lod']))


def _material(material, detailed=False):
    if material is None:
        return None
    row = {'path': _path(material), 'base': _path(material.get_base_material())}
    if detailed:
        lib = unreal.MaterialEditingLibrary
        row['used_textures'] = [_path(t) for t in lib.get_material_used_textures(material)]
        instance = isinstance(material, unreal.MaterialInstanceConstant)
        row['vectors'] = {}
        for name in lib.get_vector_parameter_names(material):
            value = (lib.get_material_instance_vector_parameter_value(material, name) if instance else
                     lib.get_material_default_vector_parameter_value(material, name))
            row['vectors'][str(name)] = [value.r, value.g, value.b, value.a]
        row['scalar_names'] = [str(n) for n in lib.get_scalar_parameter_names(material)]
    return row


def _inspect(name, mesh, subsystem):
    row = {'skin': name, 'mesh': _path(mesh), 'skeleton': _path(mesh.get_editor_property('skeleton')),
           'physics_asset': _path(mesh.get_editor_property('physics_asset')), 'materials': [], 'lods': []}
    for index, slot in enumerate(mesh.get_editor_property('materials')):
        material = slot.get_editor_property('material_interface')
        slot_name = str(slot.get_editor_property('material_slot_name'))
        hint = any(token in (slot_name + ' ' + (_path(material) or '')).lower()
                   for token in ('bow', 'weapon', 'arrow', 'string'))
        row['materials'].append({'index': index, 'slot_name': slot_name,
                                 'weapon_name_hint': hint, 'material': _material(material, hint)})
    for lod in range(subsystem.get_lod_count(mesh)):
        sections = []
        for section in range(subsystem.get_num_sections(mesh, lod)):
            slot = subsystem.get_lod_material_slot(mesh, lod, section)
            sections.append({'section': section, 'material_slot': slot})
        row['lods'].append({'lod': lod, 'vertices': subsystem.get_num_verts(mesh, lod), 'sections': sections})
    try:
        _validate_lods(row['lods'], len(row['materials']))
    except ValueError as error:
        row['error'] = str(error)
        return row

    # An unregistered transient component exposes reference-skeleton queries. It
    # never enters a world and does not replace the operating character mesh.
    component = unreal.new_object(unreal.SkeletalMeshComponent)
    try:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property('generate_overlap_events', False)
        component.set_component_tick_enabled(False)
        component.set_skeletal_mesh_asset(mesh)
        names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
        parents = {bone: str(component.get_parent_bone(bone)) for bone in names}
        bow = {bone for bone in names if 'bow' in bone.lower()}
        descendants = set(bow)
        while True:
            children = {bone for bone, parent in parents.items() if parent in descendants}
            previous = len(descendants)
            descendants |= children
            if len(descendants) == previous:
                break
        row['bone_count'] = len(names)
        row['bone_names'] = names
        row['bow_bones_and_descendants'] = []
        for bone in names:
            if bone not in descendants and 'arrow' not in bone.lower():
                continue
            index = component.get_bone_index(bone)
            transform = component.get_ref_pose_transform(index)
            row['bow_bones_and_descendants'].append({
                'name': bone, 'index': index, 'parent': parents[bone],
                'bow_subtree': bone in descendants,
                'local_ref_translation': _vector(transform.translation),
                'local_ref_rotation': [transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w],
                'local_ref_scale': _vector(transform.scale3d)})
        row['bow_sockets'] = []
        for socket in component.get_all_socket_names():
            text = str(socket)
            if any(token in text.lower() for token in ('bow', 'arrow', 'weapon')):
                row['bow_sockets'].append({'name': text, 'bone': str(component.get_socket_bone_name(socket))})
        row['required_attachment_points'] = {
            key: component.does_socket_exist(key)
            for key in ('bow_base', 'arrow_anchor', 'arrow_nock', 'BowEmitterSocket')}
    finally:
        # This component was never registered; normal transient-object GC owns it.
        component.set_skeletal_mesh_asset(None)
    return row


def audit(output):
    """Read the eight actual skin meshes before PIE; write JSON only."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'read_only': True, 'assets_saved': False, 'skins': [],
              'geometry_limit': 'Section-to-material and reference bones are measured. Bone-weight-to-triangle membership is not exposed by these APIs; shared material slots are not proof of bow-only geometry.',
              'preview_tag': PREVIEW_TAG}
    try:
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            raise RuntimeError('audit() must run before PIE; SkeletalMeshEditorSubsystem cannot inspect LODs during play')
        subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        for name, path in SKINS.items():
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.SkeletalMesh):
                report['skins'].append({'skin': name, 'mesh': path, 'error': 'SkeletalMesh missing'})
                continue
            try:
                report['skins'].append(_inspect(name, mesh, subsystem))
            except Exception:
                report['skins'].append({'skin': name, 'mesh': path, 'error': traceback.format_exc()})
        rogue = next((r for r in report['skins'] if r['skin'] == 'Rogue' and 'error' not in r), None)
        if rogue:
            for row in report['skins']:
                if 'error' in row:
                    continue
                row['same_skeleton_asset_as_rogue'] = row['skeleton'] == rogue['skeleton']
                row['same_bone_order_as_rogue'] = row['bone_names'] == rogue['bone_names']
                row['missing_rogue_bow_bones'] = sorted(
                    {b['name'] for b in rogue['bow_bones_and_descendants']} - set(row['bone_names']))
        # Actual operating assignments are read from the CDO, not inferred from
        # the historical skin name. Runtime material overrides may differ.
        bp = unreal.load_asset('/Game/TopDown/Characters/Sparrow/BP_SparrowCharacter')
        if bp:
            cdo = unreal.get_default_object(bp.generated_class())
            component = cdo.get_editor_property('mesh')
            report['operating_blueprint'] = {
                'path': _path(bp), 'mesh': _path(component.get_editor_property('skeletal_mesh_asset')),
                'overrides': [_path(m) for m in component.get_editor_property('override_materials')]}
        report['passed'] = len(report['skins']) == len(SKINS) and all('error' not in r for r in report['skins'])
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'sparrow-bow-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('SPARROW_BOW_AUDIT passed=' + str(report['passed']) + ' output=' + str(output))
    return report


def preview_sections(actor, skin, material_slots, lods, leader):
    """Mask sections on a caller-owned preview actor, never on the live Pawn.

    Add SparrowBowAuditPreview to an existing transient SkeletalMeshActor in the
    desired PIE world, then pass explicit material-slot indices and LOD mapping
    from the successful pre-PIE audit. No editor mesh subsystem runs during PIE.
    Shared slots can contain body/arrow geometry; inspect the image before
    describing this as a bow-only preview. No actor is spawned and no asset saved.
    """
    if not isinstance(actor, unreal.SkeletalMeshActor) or not actor.actor_has_tag(PREVIEW_TAG):
        raise ValueError('Requires an explicitly tagged SkeletalMeshActor preview; operating Pawn is never accepted')
    mesh = unreal.load_asset(SKINS.get(skin, skin))
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise ValueError('SkeletalMesh missing: ' + str(skin))
    slots = set(int(index) for index in material_slots)
    if not slots or min(slots) < 0 or max(slots) >= len(mesh.get_editor_property('materials')):
        raise ValueError('Choose explicit valid material-slot indices from audit JSON')
    _validate_lods(lods, len(mesh.get_editor_property('materials')))
    leader_mesh = leader.get_editor_property('skeletal_mesh_asset')
    if not leader_mesh or mesh.get_editor_property('skeleton') != leader_mesh.get_editor_property('skeleton'):
        raise ValueError('Different skeleton: live Sparrow leader pose cannot be applied')
    actor.set_actor_enable_collision(False)
    component = actor.get_editor_property('skeletal_mesh_component')
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_editor_property('generate_overlap_events', False)
    # Use SetMaterial's render-thread-safe invalidation, never write the raw
    # OverrideMaterials array while the registered comparison actor is rendering.
    for index in range(len(component.get_editor_property('override_materials'))):
        component.set_material(index, None)
    component.set_leader_pose_component(None, False, False)
    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    component.set_animation(None)
    component.set_skeletal_mesh_asset(mesh)
    component.set_forced_lod(1)
    # USkinnedMeshComponent::UpdateLeaderBoneMap resolves differing meshes by
    # bone name, not by matching index order. Mirror that lookup for evidence;
    # skin-specific accessory bones may remain unmapped and are listed below.
    names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    leader_indices = [leader.get_bone_index(name) for name in names]
    required_bow = [str(leader.get_bone_name(i)) for i in range(leader.get_num_bones())
                    if str(leader.get_bone_name(i)).startswith(('bow_', 'arrow_nock'))]
    missing_required = [name for name in required_bow if component.get_bone_index(name) < 0]
    if missing_required:
        raise ValueError('Follower lacks live bow bones: ' + ', '.join(missing_required))
    component.set_leader_pose_component(leader, False, False)
    # Assign the selected donor's materials explicitly on the temporary actor.
    # A spawned engine actor can carry inherited per-component overrides.
    for index, material_slot in enumerate(mesh.get_editor_property('materials')):
        component.set_material(index, material_slot.get_editor_property('material_interface'))
    for row in lods:
        lod = row['lod']
        component.show_all_material_sections(lod)
        for section in row['sections']:
            slot = section['material_slot']
            component.show_material_section(slot, section['section'], slot in slots, lod)
    actor.set_life_span(45.)
    resolved = [_path(component.get_material(index)) for index in range(len(mesh.get_editor_property('materials')))]
    expected = [_path(slot.get_editor_property('material_interface')) for slot in mesh.get_editor_property('materials')]
    if resolved != expected:
        raise ValueError('Preview material defaults did not resolve to the selected skin')
    return {'mesh': _path(mesh), 'visible_material_slots': sorted(slots), 'component': _path(component),
            'leader_component': _path(leader), 'pose': 'live Sparrow held-attack leader pose',
            'bone_mapping': {'method': 'UpdateLeaderBoneMap bone-name lookup',
                             'leader_indices': leader_indices,
                             'missing_accessory_bones': [name for name, index in zip(names, leader_indices) if index < 0],
                             'required_bow_bones_present': True},
            'resolved_materials': resolved, 'material_defaults_match': True,
            'assets_saved': False, 'note': 'Explicit section mask only. Shared sections may include body.'}


def spawn_preview(world, command):
    """Create a PIE-only stand-in using the existing QA console connection."""
    before = {_path(a) for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor)}
    command('summon /Script/Engine.SkeletalMeshActor')
    actors = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor)
              if _path(a) not in before]
    if len(actors) != 1:
        raise RuntimeError('Expected one PIE SkeletalMeshActor from summon; found ' + str(len(actors)))
    actor = actors[0]
    actor.set_editor_property('tags', [unreal.Name(PREVIEW_TAG)])
    actor.set_actor_enable_collision(False)
    actor.set_life_span(45.)
    component = actor.get_editor_property('skeletal_mesh_component')
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_editor_property('generate_overlap_events', False)
    component.set_editor_property('can_ever_affect_navigation', False)
    return actor


def update_preview(actor, skin, material_slots=None, lods=None, leader=None):
    """Show a complete donor skin, or explicit material slots, on the stand-in."""
    mesh = unreal.load_asset(SKINS.get(skin, skin))
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise ValueError('SkeletalMesh missing: ' + str(skin))
    slots = list(range(len(mesh.get_editor_property('materials')))) if material_slots is None else material_slots
    if leader is None:
        raise ValueError('Live Sparrow mesh leader is required')
    result = preview_sections(actor, skin, slots, lods, leader)
    result['presentation'] = 'full donor skin' if material_slots is None else 'material slot mask'
    return result


def cleanup_preview(actor):
    if actor and actor.actor_has_tag(PREVIEW_TAG):
        actor.get_editor_property('skeletal_mesh_component').set_leader_pose_component(None, False, False)
        actor.destroy_actor()


def preview_sequence(rig):
    """Capture donor skins following the live Sparrow's normal attack pose.

    The rig supplies its already-running world, console command, screenshot and
    case callbacks. All stand-ins exist only in PIE and are destroyed in finally.
    QA sends held-attack input only; no skin, material, map or camera is changed.
    """
    world = rig['world']() if callable(rig['world']) else rig['world']
    output = Path(rig['OUT'])
    report = {'assets_saved': False, 'operating_pawn_changed': False,
              'camera_changed': False, 'frames': [], 'preview_actor': None}
    actor = None
    held = False
    target = None
    try:
        audit_report = rig['STATE'].get('bow_audit')
        if not audit_report or not audit_report.get('passed'):
            raise ValueError('STATE[bow_audit] must contain a successful pre-PIE audit report')
        skins = {row['skin']: row for row in audit_report['skins']}
        rig['switch']('sparrow')
        yield .8
        pawn = rig['pawn']() if callable(rig['pawn']) else rig['pawn']
        leader = pawn.get_editor_property('mesh')
        leader_mesh = leader.get_editor_property('skeletal_mesh_asset')
        report['operating_mesh_before'] = _path(leader_mesh)
        rig['case']('sparrow_bow_skins')
        fixtures = rig['layout']([(650, 0), (750, 350), (750, -350)])
        yield .2
        target = rig['aim'](fixtures[0])
        rig['cmd'](f'CountessComboQA.Mouse Press Left {target.x} {target.y} {target.z}')
        held = True
        yield .2
        actor = spawn_preview(world, rig['cmd'])
        report['preview_actor'] = _path(actor)
        # Imported Paragon mesh faces +Y. Keep the game's original camera and
        # enlarge only this comparison actor; the live character stays intact.
        location = leader.get_world_location() + unreal.Vector(180., 0., 0.)
        actor.set_actor_location(location, False, True)
        rotation = leader.get_world_rotation()
        rotation.yaw += 180.
        actor.set_actor_rotation(rotation, False)
        actor.set_actor_scale3d(unreal.Vector(2.0, 2.0, 2.0))
        requested = os.environ.get('SPARROW_BOW_PREVIEW_SKINS',
            'Rogue,Raven,Tough,ZechinHuntress,AutumnFire,FelineQueen,Monarch,base').split(',')
        for name in requested:
            name = name.strip()
            if name not in SKINS:
                raise ValueError('Unknown Sparrow skin: ' + name)
            if skins[name]['skeleton'] != _path(leader_mesh.get_editor_property('skeleton')):
                report.setdefault('excluded', []).append({'skin': name, 'reason': 'different skeleton; live leader pose unsupported'})
                continue
            row = update_preview(actor, name, lods=skins[name]['lods'], leader=leader)
            yield .35
            label = 'bow_skin_' + name
            rig['capture'](label)
            report['frames'].append({'skin': name, 'capture': label, **row})
            yield .2
            if name == 'Raven':
                mesh = unreal.load_asset(SKINS[name])
                indices = [i for i, slot in enumerate(mesh.get_editor_property('materials'))
                           if 'weapon_bow' in (_path(slot.get_editor_property('material_interface')) or '').lower()]
                if indices:
                    row = update_preview(actor, name, indices, skins[name]['lods'], leader)
                    yield .2
                    label = 'bow_skin_Raven_weapon_slots'
                    rig['capture'](label)
                    report['frames'].append({'skin': name, 'capture': label, **row})
                    yield .2
        report['operating_mesh_after'] = _path(leader.get_editor_property('skeletal_mesh_asset'))
        report['operating_pawn_changed'] = report['operating_mesh_after'] != report['operating_mesh_before']
        report['passed'] = True
    except Exception:
        report['passed'] = False
        report['error'] = traceback.format_exc()
        unreal.log_warning('SPARROW_BOW_PREVIEW ' + report['error'])
    finally:
        if held:
            rig['cmd'](f'CountessComboQA.Mouse Release Left {target.x} {target.y} {target.z}')
        cleanup_preview(actor)
        report['preview_cleaned'] = not any(a.actor_has_tag(PREVIEW_TAG)
            for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor))
        output.mkdir(parents=True, exist_ok=True)
        (output / 'sparrow-bow-preview.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        unreal.log('SPARROW_BOW_PREVIEW passed=' + str(report.get('passed')) + ' output=' + str(output))


def fitting_sequence(rig):
    """PIE-only Rogue outfit + Raven weapon fitting; restore all touched slots."""
    world = rig['world']() if callable(rig['world']) else rig['world']
    output = Path(rig['OUT'])
    report = {'passed': False, 'presentation_only': True, 'assets_saved': False,
              'outfit_mesh_changed': False, 'recolor': 'original Raven purple', 'frames': []}
    actor, leader, target = None, None, None
    original = {}
    rogue_lods = []
    held = False

    def sync():
        if actor:
            actor.set_actor_location(leader.get_world_location(), False, True)
            actor.set_actor_rotation(leader.get_world_rotation(), False)
            actor.set_actor_scale3d(unreal.Vector(1., 1., 1.))

    def wait(seconds):
        remaining = seconds
        while remaining > .00001:
            sync()
            step = min(1. / 60., remaining)
            yield step
            remaining -= step

    def capture(label):
        sync()
        rig['capture'](label)
        montage = leader.get_anim_instance().get_current_active_montage()
        report['frames'].append({'capture': label, 'montage': _path(montage),
            'outfit_mesh': _path(leader.get_editor_property('skeletal_mesh_asset')),
            'bow_location': _vector(actor.get_actor_location()) if actor else None,
            'leader_location': _vector(leader.get_world_location())})

    def mouse(pressed):
        nonlocal held
        rig['cmd'](f'CountessComboQA.Mouse {"Press" if pressed else "Release"} Left {target.x} {target.y} {target.z}')
        held = pressed

    try:
        audit_report = rig['STATE'].get('bow_audit')
        if not audit_report or not audit_report.get('passed'):
            raise ValueError('fitting_sequence requires the successful pre-PIE bow audit')
        skins = {row['skin']: row for row in audit_report['skins']}
        rig['switch']('sparrow')
        yield .8
        pawn = rig['pawn']() if callable(rig['pawn']) else rig['pawn']
        leader = pawn.get_editor_property('mesh')
        if _path(leader.get_editor_property('skeletal_mesh_asset')) != skins['Rogue']['mesh']:
            raise ValueError('Rogue operating mesh required; another outfit will not be altered')
        rogue_lods = skins['Rogue']['lods']
        _validate_lods(rogue_lods, len(skins['Rogue']['materials']))
        for row in rogue_lods:
            for section in row['sections']:
                slot = section['material_slot']
                if slot in (2, 5, 6):
                    original[(row['lod'], slot)] = leader.is_material_section_shown(slot, row['lod'])
        if {slot for _, slot in original} != {2, 5, 6}:
            raise ValueError('Rogue Arrow/String/Bow slots 2/5/6 not present in audit mapping')
        report['original_sections'] = [{'lod': lod, 'slot': slot, 'shown': shown}
            for (lod, slot), shown in sorted(original.items())]
        report['operating_mesh_before'] = _path(leader.get_editor_property('skeletal_mesh_asset'))
        report['operating_materials_before'] = [_path(m) for m in leader.get_materials()]
        rig['case']('sparrow_raven_bow_fitting')
        fixtures = rig['layout']([(650, 0), (750, 350), (750, -350)])
        yield .25
        target = rig['aim'](fixtures[0])
        capture('bow_fitting_rogue_original')
        actor = spawn_preview(world, rig['cmd'])
        report['weapon'] = update_preview(actor, 'Raven', [3, 7], skins['Raven']['lods'], leader)
        report['preview_actor'] = _path(actor)
        for row in rogue_lods:
            for section in row['sections']:
                if section['material_slot'] in (2, 5, 6):
                    leader.show_material_section(section['material_slot'], section['section'], False, row['lod'])
        yield from wait(.2)
        capture('bow_fitting_raven_ready')
        mouse(True)
        yield from wait(.28)
        capture('bow_fitting_raven_basic_draw')
        yield from wait(.25)
        capture('bow_fitting_raven_basic_release')
        mouse(False)
        yield from wait(.65)
        for letter, times in (('W', (.55, 1.2, .95)), ('E', (.35, .45, .9))):
            fixtures = rig['layout']([(650, 0), (750, 350), (750, -350)])
            yield from wait(.15)
            rig['use'](letter, fixtures[0])
            yield from wait(times[0])
            capture('bow_fitting_raven_' + letter + '_draw')
            yield from wait(times[1])
            capture('bow_fitting_raven_' + letter + '_release')
            yield from wait(times[2])
        fixtures = rig['layout']([(650, 0), (750, 350), (750, -350)])
        yield from wait(.15)
        rig['use']('R', fixtures[0])
        yield from wait(.65)
        capture('bow_fitting_raven_R_buff')
        target = rig['aim'](fixtures[0])
        mouse(True)
        yield from wait(.4)
        capture('bow_fitting_raven_R_basic')
        yield from wait(.35)
        mouse(False)
        yield from wait(.65)
        rig['use']('S', fixtures[0])
        yield from wait(.7)
        capture('bow_fitting_raven_S_wings')
        yield from wait(.55)
        capture('bow_fitting_raven_S_open')
        # The production ascension expires after eight seconds; let its original
        # hood restoration run before restoring only our three weapon slots.
        yield from wait(7.1)
        capture('bow_fitting_raven_S_restored')
        report['outfit_mesh_changed'] = _path(leader.get_editor_property('skeletal_mesh_asset')) != report['operating_mesh_before']
        report['outfit_materials_changed'] = [_path(m) for m in leader.get_materials()] != report['operating_materials_before']
        report['passed'] = not report['outfit_mesh_changed'] and not report['outfit_materials_changed']
    except Exception:
        report['error'] = traceback.format_exc()
        unreal.log_warning('SPARROW_BOW_FITTING ' + report['error'])
    finally:
        try:
            if held:
                mouse(False)
            if leader and unreal.SystemLibrary.is_valid(leader):
                for row in rogue_lods:
                    for section in row['sections']:
                        key = (row['lod'], section['material_slot'])
                        if key in original:
                            leader.show_material_section(section['material_slot'], section['section'], original[key], row['lod'])
                report['sections_restored'] = all(leader.is_material_section_shown(slot, lod) == shown
                    for (lod, slot), shown in original.items())
        except Exception:
            report['cleanup_error'] = traceback.format_exc()
            report['passed'] = False
        finally:
            cleanup_preview(actor)
        report['preview_cleaned'] = not any(a.actor_has_tag(PREVIEW_TAG)
            for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor))
        report['passed'] = report['passed'] and report.get('sections_restored', False) and report['preview_cleaned']
        output.mkdir(parents=True, exist_ok=True)
        (output / 'sparrow-bow-fitting.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        unreal.log('SPARROW_BOW_FITTING passed=' + str(report['passed']) + ' output=' + str(output))


if __name__ == '__main__':
    destination = os.environ.get('SPARROW_QA_OUTPUT') or str(Path(unreal.Paths.project_saved_dir()) / 'QA/CharacterPipeline/sparrow-bow-audit-20261022')
    audit(destination)
