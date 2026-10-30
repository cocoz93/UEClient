"""Actual-key Space gold-roll regression, with archived M9 backstep cases.

Use new_skills_probe with NEW_SKILLS_FOCUS=sparrow_feedback,
SPARROW_FEEDBACK_PARTS=, SPARROW_FEEDBACK_STUDIES=this filename.
SPARROW_BACKSTEP_SHORT=1 limits a second-FPS run to the four filmed cases.
SPARROW_BACKSTEP_CASES=M9_normal_cooldown selects only named cases for a repair run.
SPARROW_ROLL_REVIEW=1 is required for the current production Space mapping.
The legacy M9 branch has no current production key route and must not be run.
SPARROW_ROLL_SHORT=1 films the normal idle roll. V blink uses sparrow_phase_mobility_review.py.
SPARROW_ROLL_CASES=F_idle selects named normal-roll cases. The old F_S_form roll case is retired.
Legacy F/S_form case names remain stable; roll now uses Space at 2.625x and form uses V.
Capture suffix t### is the original presentation phase times 100, not elapsed time:
F_idle_t095 targets phase 0.95, or 0.362 elapsed game seconds after queued Space input.
The full 1.05-phase roll takes 0.40 game seconds; frame quantization is reported separately.
SPARROW_MOBILITY_VIDEO_CASES=F_idle,F_S_form films four real seconds per selected case.
F blend samples inspect existing component tags, material alpha and frozen poses.
This helper never saves assets, changes native source, or authors animation.
"""
import json
import os

import unreal


def sequence(rig):
    out, state = rig['OUT'], rig['STATE']
    check, cmd = rig['check'], rig['cmd']
    roll_review = os.environ.get('SPARROW_ROLL_REVIEW') == '1'
    roll_rate = 2.625
    roll_key = 'SpaceBar'
    frame_seconds = 1.0 / rig['FPS']
    check(roll_review, 'current Space route requires SPARROW_ROLL_REVIEW=1; legacy M9 is unbound')
    prefix = 'SPARROW_ROLL' if roll_review else 'SPARROW_BACKSTEP'
    short = os.environ.get(prefix + '_SHORT') == '1'
    selected = {name.strip() for name in os.environ.get(prefix + '_CASES', '').split(',') if name.strip()}
    known_cases = ({'F_idle', 'F_wall', 'F_destroy_cancel', 'F_cast_lock',
                    'F_switch_cleanup', 'F_normal_cooldown', 'F_cardinal'} if roll_review else
                   {'M9_idle', 'M9_W_handoff', 'M9_W_after_release', 'M9_backward_wall',
                    'M9_cancel_Q_before_release', 'M9_D_coexistence',
                    'M9_switch_cleans_transferred_W', 'M9_normal_cooldown', 'M9_S_form'})
    check(not selected.difference(known_cases), prefix + ' case filter contains valid case names')
    report = {'passed': False, 'fps': rig['FPS'], 'short': short, 'mode': 'Space_roll_2_625x' if roll_review else 'legacy_Space_backstep',
              'selected_cases': sorted(selected), 'cases': []}
    report['roll_timing'] = {
        'input_key': roll_key, 'active_skill_number': 18, 'playback_rate': roll_rate,
        'presentation_duration': 1.05, 'elapsed_duration_seconds': 1.05 / roll_rate,
        'frame_seconds': frame_seconds, 'pose_phase_tolerance': roll_rate * frame_seconds,
        'capture_suffix_units': 'original presentation phase multiplied by 100',
        'input_clock': 'game seconds since QA queued Space; native input is processed on the next tick',
        'pose_tolerance_reason': 'one native tick of input/actor observation skew; SetPlayRate(0) prevents free animation advance'}

    def enabled(name):
        return not selected or name in selected

    def save():
        (out / ('sparrow-gold-roll-review.json' if roll_review else 'sparrow-backstep-review.json')).write_text(
            json.dumps(report, indent=2), encoding='utf-8')

    def ghosts():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowBackstepEcho) if unreal.SystemLibrary.is_valid(a)]

    def rolls():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowGoldRoll) if unreal.SystemLibrary.is_valid(a)]

    def active_roll(label):
        actors = rolls()
        check(rig['skills']().is_rolling() and rig['skills']().get_active_skill_number() == 18 and len(actors) == 1,
              label + ' processes Space as active skill18 with exactly one roll actor')
        return actors[0]

    def check_backstep_presentation(row, ghost, moment, initial):
        mesh = rig['pawn']().get_editor_property('mesh')
        parts = ghost.get_components_by_class(unreal.SkeletalMeshComponent)
        proxy_parts = [part for part in parts if 'SparrowGoldRoll' in {str(tag) for tag in part.component_tags}]
        row.setdefault('backstep_visual_samples', []).append({
            'moment': moment, 'body_visible': mesh.is_visible(), 'roll_proxy_count': len(proxy_parts)})
        check(mesh.is_visible() == initial['mesh_visible'], row['case'] + ' keeps Sparrow visible during Space')
        check(not proxy_parts, row['case'] + ' does not replace Space with the donor roll')
        check(any(part.get_skeletal_mesh_asset() == mesh.get_skeletal_mesh_asset() for part in parts),
              row['case'] + ' keeps the original Sparrow origin clone')

    def form_wings():
        return [a for a in unreal.GameplayStatics.get_all_actors_of_class(
            rig['world'](), unreal.SparrowAscensionWings) if unreal.SystemLibrary.is_valid(a)]

    def form_state():
        # These visibility properties still require this case's runtime probe;
        # a C++ UPROPERTY declaration alone does not prove Python availability.
        def wing_alpha(part):
            values = []
            for slot in ('M12_WingSplines', 'M13_WingMembrane'):
                index = part.get_material_index(slot)
                material = part.get_material(index) if index >= 0 else None
                if isinstance(material, unreal.MaterialInstanceDynamic):
                    values.append(material.get_scalar_parameter_value('WingAlpha'))
            return values
        return [{'name': form.get_name(), 'hidden': form.get_editor_property('hidden'),
                 'wings': [{'name': part.get_name(), 'visible': part.is_visible(),
                            'hidden_in_game': part.get_editor_property('hidden_in_game'),
                            'wing_alpha': wing_alpha(part)}
                           for part in form.get_components_by_class(unreal.SkeletalMeshComponent)
                           if part.get_name() == 'SerathWings']} for form in form_wings()]

    def body_state():
        mesh = rig['pawn']().get_editor_property('mesh')
        lods = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(
            mesh.get_skeletal_mesh_asset())
        return {'visible': mesh.is_visible(),
                'materials': [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())],
                'sections': [[mesh.is_material_section_shown(i, lod) for i in range(mesh.get_num_materials())]
                             for lod in range(lods)]}

    def yaw_error(left, right):
        return abs((left - right + 180.0) % 360.0 - 180.0)

    def expected_roll_position(age):
        age = max(0.0, min(1.05, age))
        if age <= .12:
            return age
        if age <= .62:
            return .12 + (.78 - .12) * (age - .12) / .50
        return .78 + (1.4666667 - .78) * (age - .62) / .43

    def check_roll(row, ghost, moment, visible, initial):
        label = row['case'] + ' at presentation phase ' + str(moment)
        check('SparrowGoldRollActor' in {str(tag) for tag in ghost.tags},
              label + ' uses the Space roll actor')
        proxies = [part for part in ghost.get_components_by_class(unreal.SkeletalMeshComponent)
                   if 'SparrowGoldRoll' in {str(tag) for tag in part.component_tags}]
        check(len(proxies) == 1, label + ' owns exactly one tagged roll silhouette')
        proxy = proxies[0]
        mesh = proxy.get_skeletal_mesh_asset()
        anim = proxy.get_anim_instance()
        # SingleNode CurrentAsset failed Python access in visual30. The native
        # BlueprintPure getter returns the actual Node->GetCurrentAsset value.
        check(hasattr(ghost, 'get_roll_animation'), label + ' exposes the native actual-animation getter')
        check(hasattr(ghost, 'get_roll_duration'), label + ' exposes the native roll duration')
        animation = ghost.get_roll_animation()
        mesh_skeleton = mesh.get_editor_property('skeleton') if mesh else None
        animation_skeleton = animation.get_editor_property('skeleton') if animation else None
        materials = [proxy.get_material(i) for i in range(proxy.get_num_materials())]
        tints = [material.get_vector_parameter_value('BodyTint')
                 for material in materials if isinstance(material, unreal.MaterialInstanceDynamic)]
        offset = proxy.get_world_location() - rig['pawn']().get_actor_location()
        sample = {'moment': moment, 'name': proxy.get_name(), 'visible': proxy.is_visible(),
                  'mesh': mesh.get_path_name() if mesh else None,
                  'animation': animation.get_path_name() if animation else None,
                  'mesh_skeleton': mesh_skeleton.get_path_name() if mesh_skeleton else None,
                  'animation_skeleton': animation_skeleton.get_path_name() if animation_skeleton else None,
                  'playing': proxy.is_playing(), 'position': proxy.get_position(),
                  'play_rate': proxy.get_play_rate(), 'active_skill_number': rig['skills']().get_active_skill_number(),
                  'roll_duration': ghost.get_roll_duration(),
                  'owner_yaw': rig['pawn']().get_actor_rotation().yaw,
                  'proxy_yaw': proxy.get_world_rotation().yaw,
                  'root_motion_mode': str(anim.get_editor_property('root_motion_mode')) if anim else None,
                  'collision': str(proxy.get_collision_enabled()),
                  'location': rig['vec'](proxy.get_world_location()),
                  'owner_xy_offset': (offset.x * offset.x + offset.y * offset.y) ** .5,
                  'scale': rig['vec'](proxy.get_world_scale()),
                  'material_sources': [material.get_base_material().get_path_name() if material else None
                                       for material in materials],
                  'body_tints': [[tint.r, tint.g, tint.b, tint.a] for tint in tints],
                  'body_visible': rig['pawn']().get_editor_property('mesh').is_visible(),
                  'form': form_state()}
        row.setdefault('roll_samples', []).append(sample)
        save()
        check(proxy.get_name() == 'RollSilhouette', label + ' uses the native roll component')
        check(sample['visible'] == visible, label + (' displays' if visible else ' hides') + ' the roll proxy')
        check(proxy.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION,
              label + ' keeps the visual roll proxy collision-free')
        if visible:
            folder = '/Game/TopDown/Characters/Sparrow/Mobility/Quaternius/'
            mesh_path = folder + 'SK_QuaterniusRoll.SK_QuaterniusRoll'
            animation_path = folder + 'AS_QuaterniusRoll.AS_QuaterniusRoll'
            skeleton_path = folder + 'Quaternius_Roll/SkeletalMeshes/Quaternius_Roll_Skeleton.Quaternius_Roll_Skeleton'
            check(mesh is not None and mesh.get_path_name() == mesh_path,
                  label + ' uses the imported donor mesh')
            check(animation is not None and animation.get_path_name() == animation_path,
                  label + ' plays the imported original Roll asset')
            check(animation is not None and abs(animation.get_play_length() - 1.4666667) < .002,
                  label + ' retains the original donor animation length')
            check(abs(sample['roll_duration'] - 1.05 / roll_rate) < .002,
                  label + ' uses the0.40second accelerated vault and recovery duration')
            check(mesh_skeleton is not None and mesh_skeleton == animation_skeleton and
                  mesh_skeleton.get_path_name() == skeleton_path,
                  label + ' uses the original animation skeleton without retargeting')
            check(sample['playing'] and 0.0 < sample['position'] < animation.get_play_length(),
                  label + ' advances the original Roll animation')
            check(abs(sample['play_rate']) < .001, label + ' advances poses only through the native phase clock')
            check(sample['owner_xy_offset'] < 6.0,
                  label + ' follows the moving character instead of the fixed-origin clone')
            check(yaw_error(sample['proxy_yaw'], sample['owner_yaw'] - 90.0) < 1.0,
                  label + ' aligns donor forward with the actual travel direction')
            scale = sample['scale']
            check(min(scale) > 0.0 and max(scale) - min(scale) < .001,
                  label + ' fits the donor with a positive uniform scale')
            check(anim.get_editor_property('root_motion_mode') == unreal.RootMotionMode.IGNORE_ROOT_MOTION,
                  label + ' ignores donor root motion')
            check(len(materials) > 0 and len(tints) == len(materials) and
                  all(tint.r > tint.g > tint.b and tint.g > .1 for tint in tints),
                  label + ' uses gold BodyTint dynamic materials in every donor slot')
            check(all(source == '/Game/TopDown/Characters/Sparrow/Materials/'
                      'M_SparrowRollBlend.M_SparrowRollBlend'
                      for source in sample['material_sources']),
                  label + ' uses the dedicated translucent roll material')
            if .15 <= moment < .75:
                check(not sample['body_visible'], label + ' hides the original body during the roll core')
        else:
            check(sample['body_visible'] == initial['mesh_visible'],
                  label + ' restores the original Sparrow visibility')

    def check_roll_blend(row, actor, moment, initial):
        label = row['case'] + ' blend at' + str(moment)
        source = rig['pawn']().get_editor_property('mesh')
        parts = actor.get_components_by_class(unreal.SkeletalMeshComponent)
        proxies = [part for part in parts if 'SparrowGoldRoll' in {str(tag) for tag in part.component_tags}]
        transitions = [part for part in parts if 'SparrowGoldRollTransition' in {str(tag) for tag in part.component_tags}]
        echoes = [part for part in actor.get_components_by_class(unreal.PoseableMeshComponent)
                  if 'SparrowGoldRollAfterimage' in {str(tag) for tag in part.component_tags}]
        check(len(proxies) == 1 and len(transitions) == 1 and len(echoes) == 5,
              label + ' owns one roll, one body transition and five afterimages')
        proxy, transition = proxies[0], transitions[0]
        blend_path = '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowRollBlend.M_SparrowRollBlend'

        def material_state(component):
            materials = [component.get_material(i) for i in range(component.get_num_materials())]
            check(materials and all(isinstance(material, unreal.MaterialInstanceDynamic) for material in materials),
                  label + ' ' + component.get_name() + ' uses dynamic fade materials')
            check(all(material.get_base_material().get_path_name() == blend_path for material in materials),
                  label + ' ' + component.get_name() + ' uses the owned roll blend material')
            colors = [material.get_vector_parameter_value('BodyTint') for material in materials]
            check(all(color.r > color.g > color.b and color.g > .1 for color in colors),
                  label + ' ' + component.get_name() + ' keeps the golden silhouette tint')
            alpha = [material.get_scalar_parameter_value('Visibility') for material in materials]
            check(all(-.001 <= value <= 1.001 for value in alpha), label + ' keeps material visibility in range')
            check(component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION,
                  label + ' ' + component.get_name() + ' has no collision')
            return {'visible': component.is_visible(), 'alpha': alpha[0]}

        sample = {'moment': moment, 'observed_game_seconds': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                  'body_visible': source.is_visible(),
                  'roll': material_state(proxy), 'transition': material_state(transition), 'afterimages': []}
        check(transition.get_skeletal_mesh_asset() == source.get_skeletal_mesh_asset(),
              label + ' joins to the real Sparrow mesh instead of the donor mesh')
        source_bones = {str(source.get_bone_name(index)) for index in range(source.get_num_bones())}
        anchors = [bone for bone in ('spine_03', 'head', 'hand_r') if bone in source_bones]
        check(bool(anchors), label + ' has original body pose anchors')
        check(all(rig['dist'](source.get_socket_location(bone), transition.get_socket_location(bone)) < .5
                  and abs(source.get_socket_location(bone).z - transition.get_socket_location(bone).z) < .5
                  for bone in anchors), label + ' body transition follows the original animated pose')
        if 'before_F' in row:
            snapshot = row['before_F']['body']
            current = body_state()
            check(current['materials'] == snapshot['materials'] and current['sections'] == snapshot['sections'],
                  label + ' preserves every original body material and cloth section')
            cloth_slots = {name: transition.get_material_index(name)
                           for name in ('M08_Cloak', 'M16_CloakStraps', 'M14_CloakHood')}
            check(all(index >= 0 for index in cloth_slots.values()), label + ' identifies the three cloth material slots')
            cloth_indices = set(cloth_slots.values())
            sample['transition_hidden_cloth_slots'] = cloth_slots
            check(all(not transition.is_material_section_shown(index, lod)
                      for index in cloth_indices for lod in range(len(snapshot['sections']))),
                  label + ' hides cloth only on the body transition overlay')
            check(all(transition.is_material_section_shown(index, lod) == shown
                      for lod, sections in enumerate(snapshot['sections']) for index, shown in enumerate(sections)
                      if index not in cloth_indices), label + ' preserves every other source overlay section')
        # Keep a failing observation as well as the last passing sample. A newly
        # visible poseable mesh can otherwise leave only its stale birth pose in
        # the report when its component-space transforms refresh on the next tick.
        row.setdefault('blend_samples', []).append(sample)
        references = row.setdefault('afterimage_snapshots', {})
        for echo in echoes:
            state = material_state(echo)
            state.update({'name': echo.get_name(), 'location': rig['vec'](echo.get_world_location()),
                          'rotation': [echo.get_world_rotation().pitch, echo.get_world_rotation().yaw,
                                       echo.get_world_rotation().roll], 'scale': rig['vec'](echo.get_world_scale())})
            count = echo.get_num_bones()
            selected_bones = [str(echo.get_bone_name(index)) for index in sorted({0, count // 3, count * 2 // 3})] if count else []
            state['bones'] = {bone: rig['vec'](echo.get_socket_location(bone)) for bone in selected_bones}
            sample['afterimages'].append(state)
            check(echo.get_skinned_asset() == proxy.get_skeletal_mesh_asset(),
                  label + ' ' + echo.get_name() + ' snapshots the original donor roll mesh')
            if state['visible'] and abs(state['alpha'] - .44) < .0001:
                # Native UpdateAfterimages sets .44 only on the birth tick. The
                # copied pose must already match the donor before it is displayed;
                # waiting for a later component tick would expose a reference pose.
                state['birth_source_bones'] = {bone: rig['vec'](proxy.get_socket_location(bone))
                                               for bone in selected_bones}
                state['birth_pose_max_error'] = max((abs(a - b)
                    for bone, point in state['bones'].items()
                    for a, b in zip(point, state['birth_source_bones'][bone])), default=0.0)
                if state['birth_pose_max_error'] >= .15 or not state['bones']:
                    save()
                check(bool(state['bones']) and state['birth_pose_max_error'] < .15,
                      label + ' ' + echo.get_name() + ' displays the copied donor pose on its birth tick')
            if echo.get_name() in references:
                reference = references[echo.get_name()]
                state['snapshot_bone_deltas'] = {
                    bone: [a - b for a, b in zip(point, reference['bones'][bone])]
                    for bone, point in state['bones'].items()}
                pose_error = max((abs(value) for values in state['snapshot_bone_deltas'].values()
                                  for value in values), default=0.0)
                if pose_error >= .15 or not state['bones']:
                    save()
                for field in ('location', 'rotation', 'scale'):
                    check(max(abs(a - b) for a, b in zip(state[field], reference[field])) < .05,
                          label + ' ' + echo.get_name() + ' keeps its captured world ' + field)
                check(bool(state['bones']) and pose_error < .15,
                      label + ' ' + echo.get_name() + ' keeps its captured pose')
                check(state['alpha'] <= reference['alpha'] + .002,
                      label + ' ' + echo.get_name() + ' fades instead of growing again')
            elif state['visible'] and state['alpha'] > .002:
                references[echo.get_name()] = state.copy()
        save()
        if moment < .12:
            check(0.0 < sample['roll']['alpha'] < .99 and 0.0 < sample['transition']['alpha'] < .99,
                  label + ' overlaps two partial silhouettes at departure')
        elif .15 <= moment <= .60:
            check(sample['roll']['alpha'] > .98 and sample['transition']['alpha'] < .002,
                  label + ' keeps a clear roll silhouette through the core motion')
            check(any(echo['visible'] and echo['alpha'] > .002 for echo in sample['afterimages']),
                  label + ' shows fading motion afterimages')
        elif moment >= .90:
            check(sample['roll']['alpha'] < .002 and sample['transition']['alpha'] > .01,
                  label + ' transfers the landing outline back to Sparrow')
            check(source.is_visible() == initial['mesh_visible'], label + ' restores the real body before the lock ends')
            check(not any(echo['visible'] for echo in sample['afterimages']),
                  label + ' retires the afterimages before movement unlock')
        return sample

    def read(label):
        p = rig['pawn']()
        move = p.get_editor_property('character_movement')
        anim = p.get_editor_property('mesh').get_anim_instance()
        return {'label': label,
                'time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                'location': rig['vec'](p.get_actor_location()),
                'backstepping': rig['skills']().is_backstepping(),
                'rolling': rig['skills']().is_rolling() if hasattr(rig['skills'](), 'is_rolling') else False,
                'active_skill_number': rig['skills']().get_active_skill_number(),
                'busy': p.is_combat_busy(), 'casting': rig['skills']().is_casting(),
                'attacking': p.is_attacking(),
                'movement_mode': str(move.get_editor_property('movement_mode')),
                'navigation_building': unreal.NavigationSystemV1.is_navigation_being_built(rig['world']()),
                'root_motion_mode': str(anim.get_editor_property('root_motion_mode')),
                'orient_rotation_to_movement': move.get_editor_property('orient_rotation_to_movement'),
                'mesh_visible': p.get_editor_property('mesh').is_visible(),
                'ghosts': [{'name': g.get_name(), 'location': rig['vec'](g.get_actor_location()),
                            'transferred_shots': g.get_transferred_shot_count()} for g in ghosts()]}

    def recovered(initial, label):
        row = read(label)
        check(not row['backstepping'], label + ' exits backstep state')
        check(not row['rolling'], label + ' exits independent roll state')
        rig['recovered']()
        for field in ('movement_mode', 'root_motion_mode', 'orient_rotation_to_movement'):
            check(row[field] == initial[field], label + ' restores ' + field)
        check(row['mesh_visible'] == initial['mesh_visible'], label + ' restores body visibility')
        return row

    def nav_probe():
        world = rig['world']()
        api = getattr(unreal.NavigationSystemV1, 'project_point_to_navigation', None)
        result = {'building': unreal.NavigationSystemV1.is_navigation_being_built(world),
                  'building_or_locked': unreal.NavigationSystemV1.is_navigation_being_built_or_locked(world),
                  'api': str(getattr(api, '__doc__', None)), 'points': []}
        if api:
            for x, y in ((0, -400), (-220, -400), (220, -400), (-220, -300), (-220, -500)):
                for extent in ((35, 35, 100), (100, 100, 250)):
                    try:
                        projected = api(world, unreal.Vector(x, y, 0), None, None, unreal.Vector(*extent))
                        result['points'].append({'point': [x, y, 0], 'extent': extent, 'result': str(projected)})
                    except Exception as error:
                        result['points'].append({'error': str(error)})
                        return result
        return result

    def record(name):
        recorded_cases = {value.strip() for value in os.environ.get('SPARROW_MOBILITY_VIDEO_CASES', '').split(',')
                          if value.strip()}
        if os.environ.get('NEW_SKILLS_VIDEO') == '1' and (not recorded_cases or name in recorded_cases):
            state['video_clip'] = {
                'case': name, 'prefix': name + '_video',
                'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
                'frame_times': []}

    def clear():
        cmd('CountessComboQA.FlushInput')
        unreal.GameplayStatics.get_player_controller(rig['world'](), 0).stop_movement()

    def fresh(name):
        rig['switch']('countess')
        yield .2
        rig['switch']('sparrow')
        yield .7
        clear()
        rig['case'](name)
        targets = rig['layout']([(650, 0), (250, 650), (250, -650)])
        yield .2
        report['cases'].append({'case': name, 'initial': read(name + '_initial')})
        save()
        return targets

    def check_distance(row, start, forward):
        current = rig['pawn']().get_actor_location()
        delta = current - start
        backward = -(delta.x * forward.x + delta.y * forward.y)
        sideways = abs(delta.x * forward.y - delta.y * forward.x)
        row['distance'] = rig['dist'](start, current)
        row['backward_distance'] = backward
        row['sideways_distance'] = sideways
        check(205.0 <= backward <= 235.0, row['case'] + ' travels220cm backward')
        check(sideways < 6.0, row['case'] + ' does not drift sideways')

    def fixed_clone(row, ghost, origin, expected_shots):
        check(unreal.SystemLibrary.is_valid(ghost), row['case'] + ' retains its short-lived origin clone')
        position = ghost.get_actor_location()
        row.setdefault('clone_samples', []).append({
            'time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
            'location': rig['vec'](position), 'shots': ghost.get_transferred_shot_count()})
        check(rig['dist'](position, origin) < 2.0,
              row['case'] + ' leaves the clone at its original world position')
        check(ghost.get_transferred_shot_count() == expected_shots,
              row['case'] + ' transferred W shots=' + str(expected_shots))

    def fresh_move(row):
        clear()
        before = rig['pawn']().get_actor_location()
        goal = rig['ground'](before.x, before.y + 300)
        cmd(f'CountessComboQA.Mouse Press Right {goal.x} {goal.y} {goal.z}')
        yield 1.0 / rig['FPS']
        cmd(f'CountessComboQA.Mouse Release Right {goal.x} {goal.y} {goal.z}')
        yield .8
        moved = rig['dist'](before, rig['pawn']().get_actor_location())
        row['fresh_move_distance'] = moved
        check(moved > 180.0, row['case'] + ' accepts fresh movement after recovery')
        clear()

    def roll_distance(row, start):
        delta = rig['pawn']().get_actor_location() - start
        row['distance'] = rig['dist'](start, rig['pawn']().get_actor_location())
        row['mouse_direction_distance'] = delta.x
        row['sideways_distance'] = abs(delta.y)
        check(465.0 <= delta.x <= 495.0, row['case'] + ' travels480cm toward the mouse')
        check(abs(delta.y) < 6.0, row['case'] + ' does not drift off the mouse direction')

    def roll_restored(row, initial, label):
        check(not rolls(), label + ' removes its visual roll actor')
        check(not ghosts(), label + ' creates no Space departure clone')
        check(rig['skills']().get_active_skill_number() == 0, label + ' clears active skill18')
        row['recovered'] = recovered(initial, label)
        return row['recovered']

    def roll_cases():
        check(hasattr(unreal, 'SparrowGoldRoll') and hasattr(rig['skills'](), 'is_rolling'),
              'Space roll native class and state API are loaded')
        for name in ('F_idle',):
            if not enabled(name):
                continue
            targets = yield from fresh(name)
            row = report['cases'][-1]
            if name == 'F_S_form':
                rig['aim'](targets[0])
                rig['key']('V')
                yield 2.1
                check(len(form_wings()) == 1 and rig['skills']().get_ascension_remaining() > 37.0,
                      'S form is active before F')
            initial = read(name + '_before_F')
            before_body, before_form = body_state(), form_state()
            row['before_F'] = {'body': before_body, 'form': before_form}
            check(before_body['visible'], name + ' starts with the real Sparrow body visible')
            if name == 'F_S_form':
                check(len(before_form) == 1 and all(not form['hidden'] and form['wings'] and
                      all(part['visible'] and not part['hidden_in_game'] for part in form['wings'])
                      for form in before_form), 'S wings are visibly active before F hides them')
            rig['aim'](offset=(550, 0))
            start = rig['pawn']().get_actor_location()
            record(name)
            filming = state.get('video_clip', {}).get('case') == name
            film_start = unreal.GameplayStatics.get_time_seconds(rig['world']())
            if filming:
                yield .30
            input_time = unreal.GameplayStatics.get_time_seconds(rig['world']())
            if filming:
                state['video_clip']['skill_input_time'] = input_time
            rig['key'](roll_key)
            row['roll_input'] = {'key': roll_key, 'queued_at_game_seconds': input_time}
            landed = None
            for moment in (.04, .20, .40, .55, .80, .95):
                delay = moment / roll_rate - (unreal.GameplayStatics.get_time_seconds(rig['world']()) - input_time)
                if delay > .001:
                    yield delay
                actual_age = unreal.GameplayStatics.get_time_seconds(rig['world']()) - input_time
                actor = active_roll(name + ' at presentation phase ' + str(moment))
                blend = check_roll_blend(row, actor, moment, initial)
                blend['actual_age'] = actual_age
                blend['target_elapsed_seconds'] = moment / roll_rate
                blend['observed_presentation_age'] = actual_age * roll_rate
                blend['sample_lateness_seconds'] = actual_age - moment / roll_rate
                if moment == .80:
                    landed = rig['pawn']().get_actor_location()
                    row['landing_location'] = rig['vec'](landed)
                    continue
                check(not ghosts(), name + ' has no departure clone during F')
                check_roll(row, actor, moment, moment < .90, initial)
                sample = row['roll_samples'][-1]
                sample['actual_age'] = actual_age
                sample['presentation_age'] = actual_age * roll_rate
                sample['expected_position'] = expected_roll_position(actual_age * roll_rate)
                # The key is queued before native input processing. Compare the
                # actual observation time with a one-native-tick phase window,
                # rather than giving both 30 and 60 FPS the same 0.16s tolerance.
                phase_tolerance = roll_rate * frame_seconds
                sample['expected_position_window'] = [
                    expected_roll_position(actual_age * roll_rate - phase_tolerance) - .003,
                    expected_roll_position(actual_age * roll_rate + phase_tolerance) + .003]
                save()
                check(sample['expected_position_window'][0] <= sample['position'] <= sample['expected_position_window'][1],
                      name + ' preserves launch, rotation and landing pose segments')
                if len(row['roll_samples']) > 1:
                    check(sample['position'] > row['roll_samples'][-2]['position'],
                          name + ' advances through distinct original roll poses')
                if name == 'F_S_form':
                    forms = form_state()
                    alphas = [alpha for form in forms for part in form['wings'] for alpha in part['wing_alpha']]
                    check(len(forms) == 1 and len(alphas) == 2,
                          name + ' observes both original wing surface alpha values')
                    check([form['hidden'] for form in forms] == [form['hidden'] for form in before_form],
                          name + ' preserves the wing actor hidden state while fading its materials')
                    if .15 <= moment <= .60:
                        check(max(alphas) < .01, name + ' fades the wings during the roll core')
                    elif moment >= .90:
                        check(min(alphas) > .95, name + ' smoothly restores wing surfaces by landing')
                rig['capture'](name + '_t' + str(round(moment * 100)).zfill(3))
                if moment == .20:
                    before_actor = actor
                    for rejected_key in ('Q', 'W', 'E', 'R', 'A', 'S', 'D', 'V', 'SpaceBar', 'F'):
                        rig['key'](rejected_key)
                    q = targets[0].get_actor_location()
                    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
                    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
                    # The input QA commands enqueue events; same-tick state
                    # cannot prove rejection. Let native input consume them.
                    yield frame_seconds
                    row['blocked_input_state'] = read(name + '_after_blocked_input_tick')
                    save()
                    check(active_roll(name + ' after blocked input processing') == before_actor and
                          not rig['skills']().is_backstepping() and rig['skills']().is_casting() and
                          not rig['pawn']().is_attacking(),
                          name + ' rejects basic attacks and other skills without restarting Space')
                    check(not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowSanctuary),
                          name + ' rejected S and F create no sanctuary actor')
            delay = 1.20 / roll_rate - (unreal.GameplayStatics.get_time_seconds(rig['world']()) - input_time)
            if delay > .001:
                yield delay
            row['post_landing_drift'] = rig['dist'](landed, rig['pawn']().get_actor_location())
            check(row['post_landing_drift'] < 2.0, name + ' does not slide after presentation phase0.80')
            roll_distance(row, start)
            roll_restored(row, initial, name + '_complete')
            row['after_F'] = {'body': body_state(), 'form': form_state()}
            check(row['after_F']['body'] == before_body, name + ' restores exact original body materials and sections')
            check(row['after_F']['form'] == before_form, name + ' restores exact S wing visibility and identity')
            check(all(abs(rig['health'](target) - 100.0) < .02 for target in targets),
                  name + ' blocked attacks and skills produce no damage')
            check(rig['skills']().get_active_hail_count() == 0 and not
                  unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher),
                  name + ' rejected Q and D create no hail zone or mirror partner')
            if name == 'F_S_form':
                check(rig['skills']().get_ascension_remaining() > 35.0, 'Space roll preserves V lifetime')
            rig['capture'](name + '_complete')
            yield from fresh_move(row)
            if filming:
                delay = 4.0 - (unreal.GameplayStatics.get_time_seconds(rig['world']()) - film_start)
                if delay > .001:
                    yield delay
                row['video_seconds'] = unreal.GameplayStatics.get_time_seconds(rig['world']()) - film_start
                check(3.9 <= row['video_seconds'] <= 4.15, name + ' films four continuous real seconds')
            rig['finish_video_clip']()
            save()

        if short and not selected:
            return

        if enabled('F_cardinal'):
            targets = yield from fresh('F_cardinal')
            row = report['cases'][-1]
            row['directions'] = []
            for direction_name, dx, dy, expected_yaw in (
                    ('positive_X', 1.0, 0.0, 0.0), ('negative_X', -1.0, 0.0, 180.0),
                    ('positive_Y', 0.0, 1.0, 90.0), ('negative_Y', 0.0, -1.0, -90.0)):
                clear()
                rig['layout']([(900, 900), (900, 650), (650, 900)])
                rig['pawn']().set_actor_rotation(unreal.Rotator(pitch=0.0, yaw=37.0, roll=0.0), True)
                yield .10
                rig['aim'](offset=(dx * 550.0, dy * 550.0))
                start = rig['pawn']().get_actor_location()
                start_yaw = rig['pawn']().get_actor_rotation().yaw
                initial = read('F_cardinal_' + direction_name + '_initial')
                rig['key'](roll_key)
                yield .20
                active_roll(direction_name + ' directional input')
                proxies = [part for part in rolls()[0].get_components_by_class(unreal.SkeletalMeshComponent)
                           if 'SparrowGoldRoll' in {str(tag) for tag in part.component_tags}]
                check(len(proxies) == 1, direction_name + ' displays one roll silhouette')
                owner_yaw = rig['pawn']().get_actor_rotation().yaw
                proxy_yaw = proxies[0].get_world_rotation().yaw
                check(yaw_error(owner_yaw, expected_yaw) < 1.0,
                      direction_name + ' turns toward the mouse independently of the starting yaw')
                check(yaw_error(proxy_yaw, owner_yaw - 90.0) < 1.0,
                      direction_name + ' aligns the donor roll to the requested direction')
                if direction_name == 'positive_Y' or os.environ.get('SPARROW_ROLL_CARDINAL_SHOTS') == '1':
                    rig['capture']('F_cardinal_' + direction_name)
                yield 1.00
                delta = rig['pawn']().get_actor_location() - start
                forward = delta.x * dx + delta.y * dy
                sideways = abs(delta.x * dy - delta.y * dx)
                distance = rig['dist'](start, rig['pawn']().get_actor_location())
                direction = {'name': direction_name, 'start_yaw': start_yaw,
                             'owner_yaw': owner_yaw, 'proxy_yaw': proxy_yaw,
                             'delta': rig['vec'](delta), 'forward_distance': forward,
                             'sideways_distance': sideways, 'move_dot': forward / max(distance, .001)}
                row['directions'].append(direction)
                save()
                check(465.0 <= forward <= 495.0 and sideways < 6.0 and direction['move_dot'] > .999,
                      direction_name + ' travels480cm in the selected cardinal direction')
                direction['recovered'] = roll_restored(row, initial, 'F_cardinal_' + direction_name + '_complete')
            save()

        if enabled('F_wall'):
            targets = yield from fresh('F_wall')
            row = report['cases'][-1]
            barrier = rig['wall_fixture'](250)
            try:
                yield .2
                rig['aim'](offset=(550, 0))
                start = rig['pawn']().get_actor_location()
                rig['key'](roll_key)
                yield 1.0 / rig['FPS']
                active_roll('forward wall input')
                yield .40 / roll_rate - 1.0 / rig['FPS']
                wall_blend = check_roll_blend(row, rolls()[0], .40, row['initial'])
                check(all(echo['location'][0] < start.x + 240.0 for echo in wall_blend['afterimages']
                          if echo['alpha'] > .002), 'F afterimages stay on the safe side of the wall')
                yield .80
                end = rig['pawn']().get_actor_location()
                row['distance'], row['end_location'] = rig['dist'](start, end), rig['vec'](end)
                check(100.0 < row['distance'] < 235.0 and end.x < start.x + 240.0,
                      'F capsule sweep stops before the forward wall')
                roll_restored(row, row['initial'], 'F_wall_complete')
                rig['capture']('F_wall_stop')
                yield from fresh_move(row)
            finally:
                if unreal.SystemLibrary.is_valid(barrier):
                    barrier.destroy_actor()
            save()

        if enabled('F_destroy_cancel'):
            targets = yield from fresh('F_destroy_cancel')
            row = report['cases'][-1]
            rig['aim'](offset=(550, 0))
            rig['key'](roll_key)
            yield .95 / roll_rate
            active_roll('destroy cancel fixture')
            check_roll_blend(row, rolls()[0], .95, row['initial'])
            rolls()[0].destroy_actor()
            yield .10
            roll_restored(row, row['initial'], 'F_destroy_cancel_complete')
            yield from fresh_move(row)
            save()

        if enabled('F_cast_lock'):
            targets = yield from fresh('F_cast_lock')
            row = report['cases'][-1]
            rig['aim'](targets[0])
            rig['key']('W')
            yield .10
            check(rig['skills']().is_casting(), 'W is preparing before F rejection')
            rig['key'](roll_key)
            yield .10
            check(not rig['skills']().is_rolling() and not rolls() and not ghosts() and rig['skills']().is_casting(),
                  'F is rejected during W without cancelling or transferring its shot')
            yield 1.0
            check(abs(rig['health'](targets[0]) - 65.0) < .02, 'rejected F lets W finish exactly one35damage shot')
            roll_restored(row, row['initial'], 'F_cast_lock_complete')
            yield from fresh_move(row)
            save()

        if enabled('F_switch_cleanup'):
            targets = yield from fresh('F_switch_cleanup')
            row = report['cases'][-1]
            rig['aim'](offset=(550, 0))
            rig['key'](roll_key)
            yield .20
            old_pawn = rig['pawn']()
            active_roll('numeric switch fixture')
            rig['switch']('countess')
            yield .50
            check(not unreal.SystemLibrary.is_valid(old_pawn) and not rolls() and not ghosts(),
                  'numeric switch destroys F and its old owner without departure clones')
            check(rig['pawn']().get_editor_property('mesh').is_visible() and not rig['pawn']().is_combat_busy(),
                  'numeric switch leaves Countess visible and movement unlocked')
            save()

        if enabled('F_normal_cooldown'):
            targets = yield from fresh('F_normal_cooldown')
            row = report['cases'][-1]
            cmd('Sparrow.Skills.IgnoreCooldowns 0')
            rig['aim'](offset=(550, 0))
            first_time = unreal.GameplayStatics.get_time_seconds(rig['world']())
            rig['key'](roll_key)
            yield .20
            active_roll('first input with normal cooldowns')
            yield 1.00
            roll_restored(row, row['initial'], 'F_first_cooldown_complete')
            before = rig['pawn']().get_actor_location()
            rig['key'](roll_key)
            yield .10
            check(not rig['skills']().is_rolling() and not rolls() and
                  rig['dist'](before, rig['pawn']().get_actor_location()) < 2.0,
                  'F is rejected during its normal cooldown')
            check('cooldown' in rig['skills']().get_input_feedback().lower(), 'F cooldown reports its rejection reason')
            now = unreal.GameplayStatics.get_time_seconds(rig['world']())
            yield max(.001, 6.20 - (now - first_time))
            rig['aim'](offset=(550, 0))
            rig['key'](roll_key)
            yield .20
            active_roll('input after six second cooldown')
            yield 1.00
            roll_restored(row, row['initial'], 'F_cooldown_complete')
            cmd('Sparrow.Skills.IgnoreCooldowns 1')
            yield from fresh_move(row)
            save()

    check(hasattr(unreal, 'SparrowBackstepEcho'), 'native backstep clone class is loaded')
    rig['switch']('sparrow')
    yield .7
    check(hasattr(rig['skills'](), 'is_backstepping'), 'native backstep state API is loaded')
    cmd('Sparrow.Skills.IgnoreCooldowns 1')
    save()

    try:
        if roll_review:
            yield from roll_cases()
            report['passed'] = True
            save()
            return
        # Idle, pre-release W and already-released W are deliberately separate.
        # All actions use controller key presses rather than TryUseSkillSlot.
        for name, w_delay in (('M9_idle', None), ('M9_W_handoff', .30), ('M9_W_after_release', .67)):
            if not enabled(name):
                continue
            targets = yield from fresh(name)
            row = report['cases'][-1]
            initial = row['initial']
            rig['aim'](targets[0])
            record(name)
            if w_delay is not None:
                rig['key']('W')
                yield w_delay
                check(rig['skills']().is_casting(), name + ' starts Space from the W cast')
            start = rig['pawn']().get_actor_location()
            forward = rig['pawn']().get_actor_forward_vector()
            rig['key']('SpaceBar')
            yield 1.0 / rig['FPS']
            row['after_space'] = read(name + '_after_space')
            row['after_space']['feedback'] = rig['skills']().get_input_feedback()
            save()
            if not row['after_space']['backstepping']:
                rig['capture'](name + '_failed_space')
                row['navigation_failure_samples'] = [nav_probe()]
                for delay in (.2, .3, .5, 1.):
                    yield delay
                    row['navigation_failure_samples'].append(nav_probe())
                    save()
            check(row['after_space']['backstepping'], name + ' accepts the real Space input')
            current_ghosts = ghosts()
            check(len(current_ghosts) == 1, name + ' creates exactly one origin clone')
            ghost = current_ghosts[0]
            origin = ghost.get_actor_location()
            check(rig['dist'](origin, start) < 2.0, name + ' creates clone at pre-backstep position')
            fixed_clone(row, ghost, origin, 0)
            elapsed = 1.0 / rig['FPS']
            for moment in (.06, .10, .20, .42, .59):
                yield moment - elapsed
                elapsed = moment
                if moment == .06:
                    for rejected_key in ('Q', 'W', 'E', 'R', 'A', 'D'):
                        rig['key'](rejected_key)
                    check(rig['skills']().is_backstepping(), name + ' rejects other skill inputs during backstep')
                    row['fast_departure_distance'] = rig['dist'](start, rig['pawn']().get_actor_location())
                    check(row['fast_departure_distance'] > 100.0,
                          name + ' opens more than100cm within its first two frames at30fps')
                if moment == .20:
                    row['fast_recovery'] = read(name + '_fast_recovery')
                    check(not row['fast_recovery']['backstepping'], name + ' finishes movement within0.20seconds')
                    check_distance(row, start, forward)
                if moment in (.10, .20):
                    check_backstep_presentation(row, ghost, moment, initial)
                if moment in (.10, .42):
                    poses = [p for p in ghost.get_components_by_class(unreal.PoseableMeshComponent)
                             if 'SparrowBackstepAfterimage' in {str(t) for t in p.component_tags}]
                    visible = sum(p.is_visible() for p in poses)
                    row.setdefault('motion_afterimages', []).append({'time':moment,'count':len(poses),'visible':visible})
                    check(len(poses) == 3, name + ' owns three visual pose echoes')
                    check(visible >= 1 if moment == .10 else visible == 0,
                          name + (' shows a golden motion echo' if moment == .10 else ' fades motion echoes by0.42seconds'))
                expected_shots = 1 if w_delay == .30 and moment >= .42 else 0
                fixed_clone(row, ghost, origin, expected_shots)
                rig['capture'](name + '_t' + str(round(moment * 100)).zfill(3))
            yield .35
            rig['finish_video_clip']()
            check_distance(row, start, forward)
            row['recovered'] = recovered(initial, name + '_recovered')
            row['target_health'] = [rig['health'](d) for d in targets]
            expected_health = 100.0 if w_delay is None else 65.0
            check(abs(row['target_health'][0] - expected_health) < .02,
                  name + (' transfers exactly35damage' if w_delay == .30 else ' has no duplicate W damage'))
            check(all(abs(h - 100.0) < .02 for h in row['target_health'][1:]),
                  name + ' does not damage side fixtures')
            yield from fresh_move(row)
            check(not ghosts(), name + ' retires the1.10second origin clone')
            save()

        if enabled('M9_S_form'):
            targets = yield from fresh('M9_S_form')
            row = report['cases'][-1]
            rig['aim'](targets[0])
            rig['key']('V')
            yield 2.1
            check(len(form_wings()) == 1 and rig['skills']().get_ascension_remaining() > 37.0,
                  'S form is active before its original Space backstep')
            before_body = body_state()
            before_form = form_state()
            row['S_before_roll'] = {'body': before_body, 'form': before_form}
            check(before_body['visible'] and all(not form['hidden'] for form in before_form),
                  'S body and original wing actor are visible before Space')
            check(all(form['wings'] and all(part['visible'] and not part['hidden_in_game']
                                           for part in form['wings']) for form in before_form),
                  'S displays its original wing components before Space')
            initial = read('M9_S_form_before_roll')
            start = rig['pawn']().get_actor_location()
            forward = rig['pawn']().get_actor_forward_vector()
            record('M9_S_form')
            rig['key']('SpaceBar')
            yield .10
            check(rig['skills']().is_backstepping() and len(ghosts()) == 1,
                  'S form accepts the actual Space input and keeps one origin clone')
            ghost = ghosts()[0]
            check_backstep_presentation(row, ghost, .10, initial)
            fixed_clone(row, ghost, start, 0)
            check(form_state() == before_form, 'S wings remain visible throughout the original Space backstep')
            rig['capture']('M9_S_form_t010')
            yield .10
            check_backstep_presentation(row, ghost, .20, initial)
            row['S_after_roll'] = {'body': body_state(), 'form': form_state()}
            check(row['S_after_roll']['body'] == before_body,
                  'Space restores the exact S body materials and hidden cloak sections')
            check(row['S_after_roll']['form'] == before_form,
                  'Space restores the same S wing actor and visibility state')
            check(rig['skills']().get_ascension_remaining() > 36.0,
                  'Space preserves the active S transformation lifetime')
            check_distance(row, start, forward)
            rig['capture']('M9_S_form_t020')
            yield .70
            fixed_clone(row, ghost, start, 0)
            row['recovered'] = recovered(initial, 'M9_S_form_recovered')
            rig['capture']('M9_S_form_recovered')
            rig['finish_video_clip']()
            yield from fresh_move(row)
            check(not ghosts(), 'S form origin clone retires after its normal lifetime')
            save()

        if short and not selected:
            report['passed'] = True
            save()
            return

        if enabled('M9_backward_wall'):
            targets = yield from fresh('M9_backward_wall')
            row = report['cases'][-1]
            barrier = rig['wall_fixture'](-130)
            try:
                yield .2
                start = rig['pawn']().get_actor_location()
                rig['key']('SpaceBar')
                yield .85
                end = rig['pawn']().get_actor_location()
                row['distance'] = rig['dist'](start, end)
                row['end_location'] = rig['vec'](end)
                check(end.x > start.x - 110.0 and row['distance'] < 125.0,
                      'backstep capsule sweep stops before the rear wall')
                rig['capture']('M9_backward_wall_stop')
                row['recovered'] = recovered(row['initial'], 'M9_backward_wall_recovered')
                yield from fresh_move(row)
            finally:
                if unreal.SystemLibrary.is_valid(barrier):
                    barrier.destroy_actor()
            save()

        if enabled('M9_cancel_Q_before_release'):
            targets = yield from fresh('M9_cancel_Q_before_release')
            row = report['cases'][-1]
            rig['use']('Q', targets[0])
            yield .1
            start = rig['pawn']().get_actor_location()
            forward = rig['pawn']().get_actor_forward_vector()
            check(rig['skills']().is_casting(), 'Q is preparing before Space')
            rig['key']('SpaceBar')
            yield .1
            check(rig['skills']().is_backstepping() and len(ghosts()) == 1,
                  'Space cancels a preparing Q and takes priority as backstep')
            check(ghosts()[0].get_transferred_shot_count() == 0,
                  'cancelled Q does not become a transferred W shot')
            yield .8
            check_distance(row, start, forward)
            check(rig['skills']().get_active_hail_count() == 0 and
                  all(abs(rig['health'](d) - 100.0) < .02 for d in targets),
                  'Q cancelled before release leaves no hail zone or damage')
            row['recovered'] = recovered(row['initial'], 'M9_cancel_Q_recovered')
            yield from fresh_move(row)
            save()

        if enabled('M9_D_coexistence'):
            targets = yield from fresh('M9_D_coexistence')
            row = report['cases'][-1]
            rig['use']('D', targets[0])
            yield .9
            companions = unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher)
            check(len(companions) == 1, 'D has one shadow partner before Space')
            rig['key']('SpaceBar')
            yield .2
            check(len(ghosts()) == 1, 'Space clone coexists with D partner')
            check(len(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowMirrorArcher)) == 1,
                  'Space does not replace or duplicate D partner')
            yield .7
            row['recovered'] = recovered(row['initial'], 'M9_D_coexistence_recovered')
            save()

        if enabled('M9_switch_cleans_transferred_W'):
            targets = yield from fresh('M9_switch_cleans_transferred_W')
            row = report['cases'][-1]
            rig['use']('W', targets[0])
            yield .30
            rig['key']('SpaceBar')
            yield .10
            old_pawn = rig['pawn']()
            check(rig['skills']().is_backstepping() and len(ghosts()) == 1,
                  'switch cleanup starts before the transferred W release')
            rig['switch']('countess')
            yield 1.0
            check(not unreal.SystemLibrary.is_valid(old_pawn) and not ghosts(),
                  'switch destroys the moving Sparrow and its fixed-origin clone')
            check(abs(rig['health'](targets[0]) - 100.0) < .02,
                  'destroyed owner cancels delayed transferred W damage')
            check(not rig['pawn']().is_combat_busy(), 'switch leaves Countess movement unlocked')
            save()

        if enabled('M9_normal_cooldown'):
            targets = yield from fresh('M9_normal_cooldown')
            row = report['cases'][-1]
            cmd('Sparrow.Skills.IgnoreCooldowns 0')
            first_cast_time = unreal.GameplayStatics.get_time_seconds(rig['world']())
            rig['key']('SpaceBar')
            yield .1
            check(rig['skills']().is_backstepping(), 'first Space is accepted with normal cooldowns')
            yield .7
            recovered(row['initial'], 'M9_first_cooldown_cast_recovered')
            before = rig['pawn']().get_actor_location()
            rig['key']('SpaceBar')
            yield .15
            row['rejected_input_elapsed'] = unreal.GameplayStatics.get_time_seconds(rig['world']()) - first_cast_time
            check(not rig['skills']().is_backstepping() and
                  rig['dist'](before, rig['pawn']().get_actor_location()) < 2.0,
                  'real Space input is rejected during cooldown')
            check('cooldown' in rig['skills']().get_input_feedback().lower(),
                  'Space cooldown rejection reports its reason')
            now = unreal.GameplayStatics.get_time_seconds(rig['world']())
            yield max(.001, 6.15 - (now - first_cast_time))
            rig['key']('SpaceBar')
            yield .1
            row['accepted_input_elapsed'] = unreal.GameplayStatics.get_time_seconds(rig['world']()) - first_cast_time
            check(rig['skills']().is_backstepping(), 'Space accepts input after its normal cooldown expires')
            yield .8
            row['recovered'] = recovered(row['initial'], 'M9_cooldown_recovered')
            cmd('Sparrow.Skills.IgnoreCooldowns 1')
            yield from fresh_move(row)
            save()

        report['passed'] = True
        save()
    finally:
        cmd('Sparrow.Skills.IgnoreCooldowns 1')
