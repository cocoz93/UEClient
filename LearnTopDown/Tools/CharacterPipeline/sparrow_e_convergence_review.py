"""Short E3 native boundary regression; run after the existing ingame sequence.

Uses the existing PIE rig and its wall fixture.  No assets/maps are saved.
Maximum-distance aiming uses the public skill entry point with an elevated
direction so a floor hit cannot be mistaken for premature curved-range expiry.
Cancellation/recast use the same real queued keyboard/mouse commands as the rig.
"""
import json
import math
import re
import traceback

import unreal


END = re.compile(r'SPARROW_CONVERGE_END arrow=(\S+) target=\(([^)]+)\) '
                 r'final=\(([^)]+)\) distance=([\d.]+) reached=(\d+) stopped=(\d+)')


def inspect_candidate_mesh_slots(output):
    """Read reimported section maps; never repair/save assets inside the probe."""
    folders = ('/Game/TopDown/Characters/Sparrow/FX/FDesign20261027',
               '/Game/TopDown/Characters/Sparrow/FX/SunArrow20261027',
               '/Game/TopDown/Characters/Sparrow/FX/EDesign20261027',
               '/Game/TopDown/Characters/Sparrow/Previews/QVDesign20261027')
    rows = []
    for folder in folders:
        for path in unreal.EditorAssetLibrary.list_assets(folder, True, False):
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                continue
            row = {'mesh': path, 'slots': [], 'lods': []}
            try:
                for index, slot in enumerate(mesh.get_editor_property('static_materials')):
                    material = slot.get_editor_property('material_interface')
                    row['slots'].append({'index': index, 'name': str(slot.get_editor_property('material_slot_name')),
                                         'material': material.get_path_name() if material else None})
                # Editor subsystem GetLODMaterialSlot rejects PIE and returns -1.
                # Read the reflected map instead. StaticMesh.cpp uses upper16
                # key bits for LOD and lower16 for section; no writes/builds.
                sections = mesh.get_editor_property('section_info_map').get_editor_property('map')
                by_lod = {}
                for key, info in sections.items():
                    lod, section = int(key) >> 16, int(key) & 0xffff
                    by_lod.setdefault(lod, {})[section] = int(info.get_editor_property('material_index'))
                row['reader'] = 'read-only reflected SectionInfoMap during PIE'
                for lod, mapped in sorted(by_lod.items()):
                    ids = [mapped.get(section, by_lod.get(0, {}).get(section, section))
                           for section in range(mesh.get_num_sections(lod))]
                    row['lods'].append({'lod': lod, 'section_material_ids': ids,
                                        'invalid_slot_ids': [index for index in ids if index < 0 or index >= len(row['slots'])]})
            except Exception:
                row['error'] = traceback.format_exc()
            rows.append(row)
    result = {'assets_saved': False, 'rows': rows,
              'skipped_reason': None if rows else 'Editor asset enumeration unavailable in PIE; use the separate editor author before/after audit',
              'invalid_meshes': [row['mesh'] for row in rows if any(lod['invalid_slot_ids'] for lod in row['lods'])]}
    (output/'candidate-mesh-section-audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def sequence(rig):
    out, cmd, frame = rig['OUT'], rig['cmd'], 1. / rig['FPS']
    selectors = ('Sparrow.EDesign.Style', 'Sparrow.Skills.IgnoreCooldowns')
    previous = {key: unreal.SystemLibrary.get_console_variable_int_value(key) for key in selectors}
    report = {'passed': False, 'fps': rig['FPS'], 'cases': [], 'checks': []}
    barrier = None
    platform = None

    def save():
        (out/'e-convergence-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    def verify(condition, label):
        # Keep all three independent cases even when a native regression fails.
        report['checks'].append({'label': label, 'passed': bool(condition)})

    def now():
        return unreal.GameplayStatics.get_time_seconds(rig['world']())

    def arrows():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow)
                if unreal.SystemLibrary.is_valid(a) and a.get_owner() == rig['pawn']() and
                'SparrowConvergingFlight' in {str(tag) for tag in a.tags}]

    def restored():
        p = rig['pawn']()
        anim = p.get_editor_property('mesh').get_anim_instance()
        movement = p.get_editor_property('character_movement')
        return {'casting': rig['skills']().is_casting(), 'busy': p.is_combat_busy(),
                'root': str(anim.get_editor_property('root_motion_mode')),
                'orient': movement.get_editor_property('orient_rotation_to_movement')}

    def endings(row):
        log = out/'editor.log'
        values = []
        if log.exists():
            for match in END.finditer(log.read_text(encoding='utf-8', errors='replace')):
                if match[1] not in row['arrows']:
                    continue
                target = [float(x) for x in match[2].split(',')]
                final = [float(x) for x in match[3].split(',')]
                values.append({'arrow': match[1], 'target': target, 'final': final,
                               'distance': float(match[4]), 'reached': bool(int(match[5])),
                               'stopped': bool(int(match[6])), 'endpoint_gap_cm': math.dist(target, final)})
        row['native_endings'] = values
        return values

    def watch(row, duration, cancel_at=None):
        start = now()
        press_at = None
        released = False
        p = rig['pawn']().get_actor_location()
        goal = rig['ground'](p.x-220, p.y-220) if cancel_at is not None else None
        while now()-start < duration:
            elapsed = now()-start
            for arrow in arrows():
                name = arrow.get_name()
                record = row['arrows'].setdefault(name, {'first_seen': elapsed, 'samples': []})
                record['samples'].append({'time': elapsed, 'location': rig['vec'](arrow.get_actor_location()),
                                          'distance': arrow.get_distance_travelled(),
                                          'remaining': arrow.get_remaining_range(), 'speed': arrow.get_flight_speed()})
            if goal is not None and press_at is None and elapsed >= cancel_at:
                cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
                press_at = elapsed
                row['right_press_at'] = elapsed
            elif press_at is not None and not released and elapsed >= press_at+frame-1e-5:
                cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
                released = True
            yield frame
        row['after'] = restored()
        row['active_arrows_after'] = len(arrows())

    def fresh(name, offsets):
        cmd('CountessComboQA.FlushInput')
        rig['switch']('countess'); yield .20
        rig['switch']('sparrow'); yield .65
        rig['case'](name)
        rig['layout'](offsets); yield .15

    try:
        report['candidate_mesh_section_audit'] = inspect_candidate_mesh_slots(out)
        cmd('Sparrow.EDesign.Style 3')
        cmd('Sparrow.Skills.IgnoreCooldowns 1')
        yield from fresh('E3_boundary_max_range', [(600, 700), (700, -700), (-600, 700)])
        definition = rig['skills']().get_editor_property('skills')[2]
        report['definition'] = {key: float(definition.get_editor_property(key)) for key in ('range', 'damage', 'action_time')}
        # The room wall is only 1,015-1,287cm from the old fixture. An elevated,
        # temporary floor retains MOVE_Walking and the real skill/arrow sweep
        # without deleting room geometry or disabling projectile collision.
        base = rig['STATE']['origin']
        rig['STATE']['fixture_id'] = rig['STATE'].get('fixture_id', 0)+1
        name = 'E3RangePlatform_'+str(rig['STATE']['fixture_id'])
        cmd(f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {base.x} {base.y} 10000')
        platform = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.StaticMeshActor)
                        if a.get_name() == name)
        mesh = platform.get_component_by_class(unreal.StaticMeshComponent)
        mesh.set_mobility(unreal.ComponentMobility.MOVABLE)
        mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
        mesh.set_collision_profile_name('BlockAll')
        platform.set_actor_scale3d(unreal.Vector(60., 20., .2))
        platform.set_actor_hidden_in_game(True)
        actor = rig['pawn']()
        capsule_height = actor.get_editor_property('capsule_component').get_scaled_capsule_half_height()
        actor.set_actor_location(unreal.Vector(base.x, base.y, 10010.+capsule_height+2.), False, True)
        movement = actor.get_editor_property('character_movement')
        movement.stop_movement_immediately()
        movement.set_movement_mode(unreal.MovementMode.MOVE_WALKING)
        yield .20
        p = rig['pawn']().get_actor_location()
        row = {'name': 'max_range', 'arrows': {}, 'initial': restored(),
               'fixture': {'temporary_platform': name, 'floor_z': 10010., 'floor_size_cm': [6000., 2000., 20.],
                           'pawn': rig['vec'](p), 'movement_mode': str(movement.get_editor_property('movement_mode')),
                           'collision_disabled': False, 'saved_map_changed': False}}
        report['cases'].append(row)
        verify(movement.get_editor_property('movement_mode') == unreal.MovementMode.MOVE_WALKING,
               'elevated range fixture retains walking on a real blocking floor')
        aim = unreal.Vector(p.x+report['definition']['range']+1000., p.y, p.z+45.)
        row['requested_aim'] = rig['vec'](aim)
        row['accepted'] = rig['skills']().try_use_skill_slot(2, aim, None)
        yield from watch(row, 1.30)
        end = endings(row)
        verify(row['accepted'] and len(row['arrows']) == 5, 'max range launches five real curved projectiles')
        verify(len(end) == 5 and all(x['reached'] and not x['stopped'] and x['endpoint_gap_cm'] < .1 for x in end),
               'all five curved lanes finish at the selected endpoint; no last-frame position approximation')
        verify(len(end) == 5 and min(x['distance'] for x in end) >= report['definition']['range']-.1 and
               max(x['distance'] for x in end) > report['definition']['range']+100.,
               'outer lanes use their longer arc budget instead of expiring at straight distance')
        verify(row['active_arrows_after'] == 0 and row['after'] == row['initial'], 'max range retires projectiles and restores cast state')
        save()
        rig['layout']([(600, 700), (700, -700), (-600, 700)])
        platform.destroy_actor(); platform = None
        yield .15

        yield from fresh('E3_boundary_wall', [(550, 0), (650, 120), (750, -100)])
        ds = rig['STATE']['dummies']
        before = [rig['health'](d) for d in ds]
        barrier = rig['wall_fixture'](250)
        yield .20
        row = {'name': 'wall', 'arrows': {}, 'initial': restored(), 'wall': barrier.get_name()}
        report['cases'].append(row)
        rig['use']('E', ds[0])
        yield from watch(row, 1.30)
        row['damage'] = [a-rig['health'](d) for a,d in zip(before, ds)]
        end = endings(row)
        verify(len(row['arrows']) == 5, 'wall test starts all five real lanes')
        verify(len(end) == 5 and all(x['stopped'] and not x['reached'] for x in end), 'every curved lane stops on the actual wall sweep')
        verify(all(abs(d) < .001 for d in row['damage']), 'no target behind the wall receives damage')
        verify(row['active_arrows_after'] == 0 and row['after'] == row['initial'], 'wall termination restores cast state')
        barrier.destroy_actor(); barrier = None
        save()

        yield from fresh('E3_boundary_cancel_recast', [(420, 0), (700, 370), (700, -370)])
        ds = rig['STATE']['dummies']
        initial = restored()
        before = [rig['health'](d) for d in ds]
        row = {'name': 'pre_shot_cancel', 'arrows': {}, 'initial': initial}
        report['cases'].append(row)
        rig['use']('E', ds[0])
        yield from watch(row, 1.15, min(.10, report['definition']['action_time']*.35))
        row['damage'] = [a-rig['health'](d) for a,d in zip(before, ds)]
        verify(len(row['arrows']) == 0 and all(abs(d) < .001 for d in row['damage']), 'pre-shot move cancels E3 with no hidden launch or damage')
        verify(row['after'] == initial, 'cancel restores action, root-motion and orientation state')
        cmd('CountessComboQA.FlushInput')
        ds = rig['layout']([(420, 0), (700, 370), (700, -370)])
        yield .15
        before = [rig['health'](d) for d in ds]
        row = {'name': 'recast_after_cancel', 'arrows': {}, 'initial': restored()}
        report['cases'].append(row)
        rig['use']('E', ds[0])
        yield from watch(row, 1.30)
        row['damage'] = [a-rig['health'](d) for a,d in zip(before, ds)]
        endings(row)
        verify(len(row['arrows']) == 5, 'same pawn can recast five lanes after cancellation')
        verify(abs(row['damage'][0]-report['definition']['damage']) < .05 and all(abs(d) < .001 for d in row['damage'][1:]),
               'five converging arrows preserve the definition total damage on one target')
        verify(row['active_arrows_after'] == 0 and row['after'] == row['initial'], 'recast retires all projectiles and restores cast state')
        report['passed'] = all(x['passed'] for x in report['checks'])
        save()
        rig['check'](report['passed'], 'E3 max-range, wall, pre-shot cancel and same-pawn recast regression')
    finally:
        if barrier and unreal.SystemLibrary.is_valid(barrier):
            barrier.destroy_actor()
        if platform and unreal.SystemLibrary.is_valid(platform):
            if unreal.SystemLibrary.is_valid(rig['pawn']()):
                rig['pawn']().set_actor_location(rig['STATE']['origin'], False, True)
                rig['pawn']().get_editor_property('character_movement').stop_movement_immediately()
            platform.destroy_actor()
        cmd('CountessComboQA.FlushInput')
        for key,value in previous.items(): cmd(key+' '+str(value))
        report['restored_selectors'] = {key: unreal.SystemLibrary.get_console_variable_int_value(key) for key in selectors}
        save()
