"""New Countess/Sparrow ASDF batch: actual PIE input, damage, cleanup and quarter-view samples.

Uses the existing editor_task, input and viewport QA commands. Assets are saved only by an explicit NEW_SKILLS_AUTHOR callback.
NEW_SKILLS_ONLY=countess|sparrow limits a repair run; NEW_SKILLS_SMOKE=1 limits a second-FPS run.
"""
import json
import math
import os
from pathlib import Path
import time
import traceback

import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
MAP = '/Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom'
FPS = int(os.environ.get('SPARROW_QA_FPS', '60'))
AUDITION = json.loads(Path(os.environ['NEW_SKILLS_AUDITION']).read_text(encoding='utf-8')) if os.environ.get('NEW_SKILLS_AUDITION') else []
STATE = {'phase': 'load', 'wall': time.monotonic(), 'checks': [], 'samples': [], 'case': 'startup'}


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def pawn():
    return unreal.GameplayStatics.get_player_character(world(), 0)


def skills():
    return pawn().get_skills()


def vec(v):
    return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]


def inspect_presentation_materials():
    rows = []
    paths = ['/Game/TopDown/Characters/Gideon/FX/M_NoxGlowStrip',
             '/Game/TopDown/Characters/Gideon/FX/M_NoxSpark',
             '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotAirAccent',
             '/Game/TopDown/Characters/Sparrow/Materials/M_SparrowShotWindAxis']
    try:
        mesh = unreal.load_asset('/Game/ParagonSparrow/FX/Meshes/Heroes/Sparrow/Abilities/SM_Sparrow_Arrow')
        materials = [unreal.load_asset(path) for path in paths]
        materials.extend(slot.get_editor_property('material_interface') for slot in mesh.get_editor_property('static_materials'))
        for source in materials:
            base = source
            while isinstance(base, unreal.MaterialInstance):
                base = base.get_editor_property('parent')
            rows.append({'material': source.get_path_name(), 'base': base.get_path_name(),
                         'used_with_instanced_static_meshes': base.get_editor_property('used_with_instanced_static_meshes')})
    except Exception:
        rows.append({'inspection_error': traceback.format_exc()})
    (OUT / 'material-usage.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')


def inspect_ascension_wings():
    """Read the imported meshes' real section mapping and wing controls; never save."""
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    rows = []
    for path in ('/Game/ParagonSparrow/Characters/Heroes/Sparrow/Skins/Rogue/Meshes/Sparrow_Rogue',
                 '/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath'):
        mesh = unreal.load_asset(path)
        row = {'mesh': path, 'slots': [], 'lods': []}
        for index, slot in enumerate(mesh.get_editor_property('materials')):
            material = slot.get_editor_property('material_interface')
            item = {'index': index, 'name': str(slot.get_editor_property('material_slot_name')),
                    'material': material.get_path_name() if material else None}
            if 'Wing' in item['name'] and material:
                base = material.get_base_material()
                lib = unreal.MaterialEditingLibrary
                instance = isinstance(material, unreal.MaterialInstanceConstant)
                item['vectors'] = {}
                item['scalars'] = {}
                for name in lib.get_vector_parameter_names(material):
                    value = lib.get_material_instance_vector_parameter_value(material, name) if instance else lib.get_material_default_vector_parameter_value(base, name)
                    item['vectors'][str(name)] = [value.r, value.g, value.b, value.a]
                for name in lib.get_scalar_parameter_names(material):
                    item['scalars'][str(name)] = lib.get_material_instance_scalar_parameter_value(material, name) if instance else lib.get_material_default_scalar_parameter_value(base, name)
            row['slots'].append(item)
        for lod in range(subsystem.get_lod_count(mesh)):
            row['lods'].append({'lod': lod, 'material_ids': [subsystem.get_lod_material_slot(mesh, lod, section)
                                for section in range(subsystem.get_num_sections(mesh, lod))]})
        rows.append(row)
    (OUT / 'ascension-wing-assets.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def cmd(text):
    unreal.SystemLibrary.execute_console_command(world(), text)


def key(name):
    cmd('CountessInputQA.Key ' + name + ' Press')
    cmd('CountessInputQA.Key ' + name + ' Release')


def check(condition, label):
    row = {'case': STATE['case'], 'label': label, 'passed': bool(condition)}
    STATE['checks'].append(row)
    if not condition:
        raise AssertionError(STATE['case'] + ': ' + label)


def case(name):
    if name != STATE['case']:
        finish_video_clip()
    (OUT / 'new-skills-progress.json').write_text(json.dumps({
        'passed': False, 'phase': 'in_progress', 'last_case': STATE['case'],
        'checks': STATE['checks'], 'samples': STATE['samples']}, ensure_ascii=False, indent=2), encoding='utf-8')
    STATE['case'] = name
    unreal.log('NEW_SKILLS_CASE ' + name)


def finish_video_clip():
    clip = STATE.pop('video_clip', None)
    if clip is None:
        return
    STATE.setdefault('video_clips', []).append(clip)
    (OUT / 'new-skills-video.json').write_text(json.dumps({
        'fps': FPS, 'source': 'consecutive actual PIE viewport frames',
        'clips': STATE['video_clips'], 'assets_saved': False}, ensure_ascii=False, indent=2), encoding='utf-8')


def record_video_frame(now):
    clip = STATE.get('video_clip')
    if clip is None or now <= clip.get('last_time', -1.0) + .00001:
        return
    if clip['case'] == 'R_multishot_cone' and now < clip.get('last_time', -1.0) + 1/30 - .00001:
        return
    index = len(clip['frame_times'])
    cmd('CharacterVisualQA.Capture ' + clip['prefix'] + f'_{index:04d}')
    clip['frame_times'].append(now)
    clip['last_time'] = now


def targets():
    return [x for x in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.KwangTrainingDummy)
            if unreal.SystemLibrary.is_valid(x)]


def health(d):
    return float(d.get_editor_property('health'))


def sample(label):
    p = pawn()
    row = {'label': label, 'time': round(unreal.GameplayStatics.get_time_seconds(world()), 4),
           'pawn': p.get_class().get_name(), 'location': vec(p.get_actor_location()),
           'casting': skills().is_casting(), 'active_skill': skills().get_active_skill_number(),
           'feedback': skills().get_input_feedback(),
           'targets': [{'name': x.get_name(), 'location': vec(x.get_actor_location()), 'health': health(x)}
                       for x in STATE.get('dummies', []) if unreal.SystemLibrary.is_valid(x)]}
    row['visual_actor_counts'] = {name: len(unreal.GameplayStatics.get_all_actors_of_class(world(), getattr(unreal, name)))
                                 for name in ('CountessExtraVisual', 'SparrowSkillVisual') if hasattr(unreal, name)}
    STATE['samples'].append(row)
    return row


def capture(label):
    sample(label)
    if os.environ.get('NEW_SKILLS_NO_SHOTS') != '1':
        cmd('CharacterVisualQA.Capture ' + label)


def ground(x, y):
    cmd(f'SparrowQA.Ground new-skills-ground {x} {y} {STATE["origin"].z}')
    probe = json.loads((OUT / 'new-skills-ground.json').read_text(encoding='utf-8-sig'))
    check(probe['ground_hit'], 'fixture has a solid floor')
    g = probe['ground']
    return unreal.Vector(g['x'], g['y'], g['z'])


def layout(offsets):
    """Move only PIE fixtures; keep the real map and its saved dummy actors intact."""
    p = pawn()
    unreal.GameplayStatics.get_player_controller(world(), 0).stop_movement()
    p.get_editor_property('character_movement').stop_movement_immediately()
    p.set_actor_location(STATE['origin'], False, True)
    p.set_actor_rotation(unreal.Rotator(0, 0, 0), True)
    ds = STATE['dummies']
    for i, d in enumerate(ds):
        x, y = offsets[i] if i < len(offsets) else (-800, 700 + i * 100)
        g = ground(STATE['origin'].x + x, STATE['origin'].y + y)
        d.set_actor_location(g + unreal.Vector(0, 0, 90), False, True)
        d.reset_dummy()
    return ds


def aim(d=None, offset=None):
    if d is not None:
        # Aim at the visible target center for actor skills; real controller performs its normal ray selection.
        q = d.get_actor_location()
    else:
        q = ground(STATE['origin'].x + offset[0], STATE['origin'].y + offset[1])
    cmd(f'CountessComboQA.Mouse Move Left {q.x} {q.y} {q.z}')
    return q


def use(letter, d=None, offset=None):
    q = aim(d, offset)
    key(letter)
    sample('cast_' + STATE['case'])
    if os.environ.get('NEW_SKILLS_VIDEO') == '1' and STATE['case'] in {
            'countess_A', 'countess_S', 'countess_D', 'countess_F',
            'sparrow_A', 'sparrow_S', 'sparrow_D', 'sparrow_F', 'R_multishot_cone'}:
        STATE['video_clip'] = {'case': STATE['case'], 'prefix': STATE['case'] + '_video',
                               'cast_time': unreal.GameplayStatics.get_time_seconds(world()), 'frame_times': []}
    if os.environ.get('NEW_SKILLS_VISUAL') == '1' and STATE['case'] in {
            'countess_A', 'countess_S', 'countess_D', 'countess_F',
            'sparrow_A', 'sparrow_S', 'sparrow_D', 'sparrow_F'}:
        now = unreal.GameplayStatics.get_time_seconds(world())
        moments = [0.10, 0.25, 0.45, 0.70, 1.00]
        moments.extend({'countess_A': (0.78,), 'countess_D': (.36, .54, .84, 1.10, 1.34, 1.60), 'countess_F': (0.80, 0.90),
                        'sparrow_A': (0.15,)}.get(STATE['case'], ()))
        for delay in sorted(moments):
            STATE.setdefault('pending_shots', []).append((now + delay, STATE['case'],
                STATE['case'] + '_sequence_' + str(round(delay * 100)).zfill(3)))
    return q


def recovered():
    check(not skills().is_casting() and not pawn().is_combat_busy(), 'cast and combat state recovered')
    finish_video_clip()


def switch(name):
    key('One' if name == 'countess' else 'Two')


def countess():
    switch('countess')
    yield 0.8
    if 'countess' not in os.environ.get('NEW_SKILLS_SKIP_NORMAL', '').split(','):
        case('countess_A')
        ds = layout([(400, 0), (400, 350), (750, -350)])
        yield 0.2
        use('A', ds[0])
        yield 0.35
        capture('countess_A_mark')
        yield 0.5
        capture('countess_A_burst')
        yield 0.65
        check(abs(health(ds[0]) - 60) < 0.01, 'mark and delayed burst total 40')
        check(health(ds[1]) == 100, 'unselected target receives no mark damage')
        recovered()

        case('countess_S')
        ds = layout([(300, 0), (300, 350), (750, -350)])
        yield 0.2
        use('S', offset=(650, 0))
        yield 0.25
        capture('countess_S_rush')
        yield 0.9
        sample('countess_S_end')
        check(health(ds[0]) == 70, 'rush hits path target once for 30')
        check(health(ds[1]) == 100, 'rush excludes target outside its path')
        check(dist(pawn().get_actor_location(), STATE['origin']) > 150, 'rush visibly moves the player')
        recovered()

        case('countess_D')
        ds = layout([(450, 0), (700, 0), (450, 350)])
        yield 0.25
        use('D', ds[0])
        yield 0.55
        capture('countess_D_wave')
        yield 1.65
        check(health(ds[0]) == 60 and health(ds[1]) == 60, 'ground wave deals 40 once to two path targets')
        check(health(ds[2]) == 100, 'ground wave excludes lateral target')
        recovered()

        case('countess_F')
        ds = layout([(450, 0), (450, 150), (450, 430)])
        yield 0.25
        use('F', offset=(450, 0))
        yield 0.4
        capture('countess_F_shadow')
        yield 0.55
        capture('countess_F_burst')
        yield 0.7
        check(health(ds[0]) == 60 and health(ds[1]) == 60, 'ambush bursts for 40 inside radius')
        check(health(ds[2]) == 100, 'ambush excludes outside target')
        recovered()

    if os.environ.get('NEW_SKILLS_SMOKE') == '1':
        return
    yield from cancellation('countess', 'A', [(400, 0)], 0.10, 1.5)
    yield from cancellation('countess', 'F', [(450, 0)], 0.45, 1.4)
    case('countess_A_break_range')
    ds = layout([(400, 0), (400, 350), (750, -350)])
    yield 0.25
    use('A', ds[0])
    yield 0.35
    check(health(ds[0]) == 90, 'mark applies its initial 10 before target moves away')
    ds[0].set_actor_location(STATE['origin'] + unreal.Vector(1000, 0, 0), False, True)
    yield 0.8
    check(health(ds[0]) == 90, 'mark does not burst on a target that left range')
    recovered()
    yield from cooldown('countess', 8, 1.6, 9.0)
    yield from owner_cleanup('countess', 'D', [(550, 0)], 0.40, 1.6)
    yield from owner_cleanup('countess', 'F', [(450, 0)], 0.4, 1.6)


def sparrow():
    switch('sparrow')
    yield 0.8
    if 'sparrow' not in os.environ.get('NEW_SKILLS_SKIP_NORMAL', '').split(','):
        case('sparrow_A')
        ds = layout([(500, 0), (500, 350), (750, -350)])
        yield 0.2
        use('A', ds[0])
        yield 0.3
        capture('sparrow_A_retreat')
        yield 1.1
        check(health(ds[0]) == 76, 'retreat arrow damages aimed target once for 24')
        check(health(ds[1]) == 100, 'retreat arrow excludes lateral target')
        check(pawn().get_actor_location().x < STATE['origin'].x - 100, 'retreat moves away from shot direction')
        recovered()

        case('sparrow_S')
        ds = layout([(430, 0), (620, 170), (770, -90)])
        yield 0.2
        use('S', ds[0])
        yield 0.4
        capture('sparrow_S_chain_first')
        yield 0.3
        capture('sparrow_S_chain_next')
        yield 1.2
        check([health(d) for d in ds] == [76, 82, 86.5], 'chain reaches three distinct targets once: 24, 18, 13.5')
        sample('sparrow_S_damage')
        recovered()

        case('sparrow_D')
        ds = layout([(400, 0), (400, 100), (400, 420)])
        yield 0.2
        use('D', offset=(400, 0))
        yield 0.3
        capture('sparrow_D_arming')
        yield 0.5
        capture('sparrow_D_trigger')
        yield 0.9
        check(health(ds[0]) == 64 and health(ds[1]) == 64, 'armed trap damages nearby targets once for 36')
        check(health(ds[2]) == 100, 'trap excludes outside target')
        recovered()

        case('sparrow_F')
        ds = layout([(300, 0), (600, 0), (600, 350)])
        yield 0.2
        use('F', offset=(1000, 0))
        yield 0.3
        capture('sparrow_F_front')
        yield 0.42
        capture('sparrow_F_back')
        yield 1.0
        check(health(ds[0]) == 58 and health(ds[1]) == 58, 'line volley hits successive positions once for 42')
        check(health(ds[2]) == 100, 'line volley excludes lateral target')
        sample('sparrow_F_damage')
        recovered()
    if os.environ.get('NEW_SKILLS_SMOKE') == '1':
        return
    yield from cancellation('sparrow', 'F', [(300, 0), (600, 0)], 0.10, 2.0)
    case('sparrow_D_expiry')
    ds = layout([(850, 0), (850, 350), (750, -350)])
    yield 0.25
    use('D', offset=(400, 0))
    yield 5.6
    check(all(health(d) == 100 for d in ds), 'empty trap expires without damaging distant targets')
    check(not any('SparrowAmbushTrap' in [str(t) for t in a.tags]
                  for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.Actor)),
          'expired trap removes its visible actors')
    recovered()
    yield from cooldown('sparrow', 9, 2.0, 11.0)
    yield from owner_cleanup('sparrow', 'S', [(550, 0), (750, 180)], 0.27, 1.6)
    yield from owner_cleanup('sparrow', 'D', [(400, 0)], 0.35, 2.0)


def cancellation(character, letter, offsets, delay, wait):
    case(character + '_' + letter + '_cancel')
    ds = layout(offsets)
    yield 0.25
    use(letter, ds[0])
    yield delay
    pawn().get_editor_property('mesh').get_anim_instance().montage_stop(0.02)
    before = [health(d) for d in ds]
    yield wait
    check([health(d) for d in ds] == before, 'cancel stops all remaining damage')
    recovered()


def cooldown(character, slot, recovery, wait):
    # Practice casts retain their real cooldown deadlines. Use a fresh owner for the normal-cooldown case.
    switch('sparrow' if character == 'countess' else 'countess')
    yield 0.2
    switch(character)
    yield 0.6
    case(character + '_cooldown')
    ds = layout([(430, 0), (620, 170), (770, -90)])
    yield 0.25
    prefix = 'Countess' if character == 'countess' else 'Sparrow'
    cmd(prefix + '.Skills.IgnoreCooldowns 0')
    comp = skills()
    q = ds[0].get_actor_location()
    check(comp.try_use_skill_slot(slot, q, ds[0]), 'first use accepted with cooldown enabled')
    yield recovery
    check(not comp.try_use_skill_slot(slot, q, ds[0]), 'second use rejected during cooldown')
    check('cooldown' in comp.get_input_feedback().lower(), 'rejection identifies cooldown')
    yield wait
    for d in ds:
        d.reset_dummy()
    check(comp.try_use_skill_slot(slot, q, ds[0]), 'use accepted after cooldown expires')
    yield recovery
    cmd(prefix + '.Skills.IgnoreCooldowns 1')
    recovered()


def owner_cleanup(character, letter, offsets, delay, wait):
    case(character + '_' + letter + '_owner_cleanup')
    ds = layout(offsets)
    yield 0.25
    use(letter, ds[0])
    old = pawn()
    yield delay
    switch('sparrow' if character == 'countess' else 'countess')
    before = [health(d) for d in ds]
    yield wait
    check(not unreal.SystemLibrary.is_valid(old), 'switch destroys previous pawn')
    check([health(d) for d in ds] == before, 'destroyed owner leaves no delayed damage')
    owned_tags = {'CountessExtraAmbush', 'CountessExtraAmbushDissolving', 'CountessExtraTide'} if character == 'countess' else {
        'SparrowAmbushTrap', 'SparrowExtraIndicator', 'SparrowSkyfallArrow'}
    check(not any(owned_tags.intersection(str(t) for t in a.tags)
                  for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.Actor)),
          'destroyed owner leaves no extra visual actors')
    for name in (('CountessExtraVisual',) if character == 'countess' else ('SparrowSkillVisual',)):
        if hasattr(unreal, name):
            check(not unreal.GameplayStatics.get_all_actors_of_class(world(), getattr(unreal, name)),
                  'destroyed owner removes new visual class ' + name)
    switch(character)
    yield 0.7
    recovered()


def wall_fixture(x):
    q = ground(STATE['origin'].x + x, STATE['origin'].y) + unreal.Vector(0, 0, 160)
    STATE['fixture_id'] = STATE.get('fixture_id', 0) + 1
    name = 'NewSkillsWall_' + str(STATE['fixture_id'])
    cmd(f'CountessComboQA.Spawn {name} /Script/Engine.StaticMeshActor {q.x} {q.y} {q.z}')
    actor = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.StaticMeshActor)
                 if a.get_name() == name)
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    component.set_collision_profile_name('BlockAll')
    actor.set_actor_scale3d(unreal.Vector(0.3, 8, 3.2))
    return actor


def boundaries():
    selection = os.environ.get('NEW_SKILLS_ONLY', '')
    if selection != 'sparrow':
        switch('countess')
        yield 0.7
        case('countess_target_validation')
        ds = layout([(900, 0), (600, 350), (750, -350)])
        yield 0.25
        comp = skills()
        check(not comp.try_use_skill_slot(8, ds[0].get_actor_location(), ds[0]), 'actor mark rejects out-of-range target')
        check(not comp.try_use_skill_slot(8, STATE['origin'], None), 'actor mark rejects missing target')
        check(not comp.try_use_skill_slot(4, STATE['origin'], None), 'unused HUD slot remains unavailable')
        case('countess_wall')
        ds = layout([(550, 0), (600, 350), (750, -350)])
        barrier = wall_fixture(250)
        yield 0.25
        use('S', offset=(700, 0))
        yield 1.3
        check(pawn().get_actor_location().x < STATE['origin'].x + 240, 'rush stops before wall')
        check(health(ds[0]) == 100, 'rush cannot damage behind wall')
        recovered()
        pawn().set_actor_location(STATE['origin'], False, True)
        use('D', ds[0])
        yield 1.8
        check(health(ds[0]) == 100, 'ground wave cannot damage behind wall')
        recovered()
        barrier.destroy_actor()
        yield 0.25
    if selection != 'countess':
        switch('sparrow')
        yield 0.7
        case('sparrow_wall')
        ds = layout([(550, 0), (650, 120), (750, -100)])
        barrier = wall_fixture(250)
        yield 0.25
        use('S', ds[0])
        yield 1.8
        check(all(health(d) == 100 for d in ds), 'chain arrow cannot acquire targets through wall')
        use('F', offset=(1000, 0))
        yield 1.8
        check(all(health(d) == 100 for d in ds), 'line volley stops at wall')
        recovered()
        barrier.destroy_actor()
        yield 0.25


def existing_regression():
    selection = os.environ.get('NEW_SKILLS_ONLY', '')
    if selection != 'sparrow':
        switch('countess')
        yield 0.8
        for letter in ('Q', 'W', 'E', 'R'):
            case('existing_countess_' + letter)
            ds = layout([(170, 0), (650, 350), (750, -350)])
            yield 0.25
            use(letter, ds[0])
            yield 2.8
            check(health(ds[0]) < 100, 'original skill still damages target')
            recovered()
    if selection != 'countess':
        switch('sparrow')
        yield 0.8
        for letter, duration in (('Q', 4.7), ('W', 2.7), ('E', 1.6)):
            case('existing_sparrow_' + letter)
            ds = layout([(450, 0), (650, 350), (750, -350)])
            yield 0.25
            use(letter, ds[0])
            yield duration
            check(health(ds[0]) < 100, 'original skill still damages target')
            recovered()
        case('existing_sparrow_R_basic')
        ds = layout([(450, 0), (650, 350), (750, -350)])
        yield 0.25
        use('R', ds[0])
        yield 0.8
        q = aim(ds[0])
        cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
        yield 1.1
        cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
        yield 1.0
        check(health(ds[0]) < 100, 'original R retains basic attack connection')
        recovered()
    case('movement_switch_camera')
    switch('countess')
    yield 0.7
    previous = pawn()
    location_before = previous.get_actor_location()
    cam = previous.get_component_by_class(unreal.CameraComponent)
    arm = previous.get_component_by_class(unreal.SpringArmComponent)
    fov, length = cam.get_editor_property('field_of_view'), arm.get_editor_property('target_arm_length')
    switch('sparrow')
    yield 0.7
    cam_after = pawn().get_component_by_class(unreal.CameraComponent)
    arm_after = pawn().get_component_by_class(unreal.SpringArmComponent)
    check(dist(location_before, pawn().get_actor_location()) < 1, '1 to 2 switch preserves position')
    check(abs(cam_after.get_editor_property('field_of_view') - fov) < 0.01 and
          abs(arm_after.get_editor_property('target_arm_length') - length) < 0.01, 'switch preserves camera FOV and arm length')
    q = ground(STATE['origin'].x - 200, STATE['origin'].y + 200)
    cmd(f'CountessComboQA.Mouse Press Right {q.x} {q.y} {q.z}')
    yield 0.7
    cmd(f'CountessComboQA.Mouse Release Right {q.x} {q.y} {q.z}')
    check(dist(location_before, pawn().get_actor_location()) > 100, 'right click movement still works')
    yield 0.7


def reference_sequence():
    for character_key, label, letters in [('Three', 'gideon', ('E', 'D', 'F')), ('Four', 'aurora', ('E', 'F'))]:
        key(character_key)
        yield 0.8
        for letter in letters:
            case('reference_' + label + '_' + letter)
            ds = layout([(350, 0), (600, 180), (700, -200)])
            yield 0.25
            use(letter, ds[0])
            yield 0.55
            capture('reference_' + label + '_' + letter + '_early')
            yield 0.65
            capture('reference_' + label + '_' + letter + '_main')
            yield 3.0


def stage_audition_meshes():
    """Only unsaved editor-world stand-ins are added; PIE uses the normal gameplay camera."""
    rows = []
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for index, item in enumerate(AUDITION):
        if 'mesh' not in item:
            continue
        mesh = unreal.load_asset(item['mesh'])
        assert mesh is not None, item['mesh']
        actor = subsystem.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 100))
        actor.tags = ['SkillAssetAudition_' + str(index)]
        component = actor.static_mesh_component
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_mobility(unreal.ComponentMobility.MOVABLE)
        component.set_static_mesh(mesh)
        component.set_cast_shadow(False)
        material = unreal.load_asset(item['material']) if item.get('material') else None
        if item.get('material'):
            assert material is not None, item['material']
            component.set_material(0, material)
            if item.get('scalars') or item.get('vectors'):
                material = component.create_dynamic_material_instance(0)
                for name, value in item.get('scalars', {}).items():
                    material.set_scalar_parameter_value(name, value)
                for name, value in item.get('vectors', {}).items():
                    material.set_vector_parameter_value(name, unreal.LinearColor(*value))
        box = mesh.get_bounding_box()
        size = box.max - box.min
        center = (box.max + box.min) * .5
        scale = item.get('length', 260.0) / max(size.x, size.y, size.z, 1)
        actor.set_actor_scale3d(unreal.Vector(scale, scale, scale))
        actor.set_actor_hidden_in_game(True)
        rows.append({'name': item['name'], 'bounds_size': vec(size), 'bounds_center': vec(center),
                     'scale': scale, 'material': material.get_path_name() if material else 'mesh defaults'})
    STATE['audition_meshes'] = rows


def audition_sequence():
    switch('countess')
    yield .8
    for index, item in enumerate(AUDITION):
        case('asset_' + item['name'])
        layout([(500, 0), (700, 350), (750, -350)])
        point = ground(STATE['origin'].x + 340, STATE['origin'].y) + unreal.Vector(0, 0, item.get('up', 80))
        rotation = unreal.Rotator(0, item.get('yaw', 0), 0)
        particle = None
        mesh_actor = None
        if 'effect' in item:
            source = unreal.load_asset(item['effect'])
            assert source is not None, item['effect']
            if item.get('full_lod'):
                distances = list(source.get_editor_property('lod_distances'))
                source.set_editor_property('lod_distances', [float(i * 1000000) for i in range(len(distances))])
            scale = item.get('scale', 1.0)
            particle = unreal.GameplayStatics.spawn_emitter_at_location(world(), source, point, rotation,
                unreal.Vector(scale, scale, scale), False)
            assert particle is not None
            particle.set_actor_parameter('BoneSocketActor', pawn())
            for name, value in item.get('params', {}).items():
                particle.set_float_parameter(name, value)
        else:
            found = unreal.GameplayStatics.get_all_actors_with_tag(world(), 'SkillAssetAudition_' + str(index))
            assert len(found) == 1
            mesh_actor = found[0]
            box = mesh_actor.static_mesh_component.static_mesh.get_bounding_box()
            center = (box.min + box.max) * .5
            mesh_actor.set_actor_rotation(rotation, False)
            yaw = math.radians(item.get('yaw', 0))
            offset = center * mesh_actor.get_actor_scale3d().x
            rotated = unreal.Vector(offset.x * math.cos(yaw) - offset.y * math.sin(yaw),
                                    offset.x * math.sin(yaw) + offset.y * math.cos(yaw), offset.z)
            mesh_actor.set_actor_location(point - rotated, False, True)
            mesh_actor.set_actor_hidden_in_game(False)
        elapsed = 0
        for moment in (.12, .35, .75):
            yield moment - elapsed
            elapsed = moment
            capture('asset_' + item['name'] + '_' + str(round(moment * 100)).zfill(3))
        if particle:
            particle.destroy_component(particle)
        if mesh_actor:
            mesh_actor.set_actor_hidden_in_game(True)
        yield .25


def focused_tide_sequence():
    switch('countess')
    yield .8
    case('countess_D')
    ds = layout([(450, 0), (700, 0), (450, 350)])
    yield .25
    use('D', ds[0])
    yield .55
    capture('countess_D_wave')
    yield 1.65
    check(health(ds[0]) == 60 and health(ds[1]) == 60, 'D pierces two path targets once each for 40')
    check(health(ds[2]) == 100, 'D excludes lateral target')
    recovered()
    check(not unreal.GameplayStatics.get_all_actors_with_tag(world(), 'CountessExtraTide'), 'D actor and attached forms retire after travel')
    if os.environ.get('NEW_SKILLS_SMOKE') == '1':
        return
    case('countess_D_wall')
    ds = layout([(550, 0), (700, 0), (450, 350)])
    barrier = wall_fixture(250)
    yield .25
    use('D', ds[0])
    yield 1.8
    check(health(ds[0]) == 100 and health(ds[1]) == 100, 'D cannot damage targets behind a wall')
    recovered()
    barrier.destroy_actor()
    yield .25
    yield from owner_cleanup('countess', 'D', [(550, 0)], .40, 1.6)


def focused_countess_qwer_sequence():
    baseline = os.environ.get('QWER_BASELINE') == '1'
    switch('countess')
    yield .8
    case('countess_E_rework')
    ds = layout([(170, 0), (650, 350), (750, -350)])
    yield .25
    use('E', ds[0])
    for index, delay in enumerate((.16, .17, .17, .17, .17, .17, .30)):
        yield delay
        capture('countess_E_' + str(index))
    check(abs(health(ds[0]) - 55) < .01, 'E retains six strikes totaling 45 damage')
    recovered()
    yield .7
    if os.environ.get('QWER_VISUAL_ONLY') != '1':
        case('countess_V_binding')
        ds = layout([(170, 0), (650, 350), (750, -350)])
        yield .25
        if not baseline:
            use('W', ds[0])
            yield .2
            check(not skills().is_casting() and health(ds[0]) == 100, 'Countess W no longer casts')
        use('W' if baseline else 'V', ds[0])
        yield .8
        check(abs(health(ds[0]) - 60) < .01, 'remapped Countess area skill retains 40 damage')
        capture('countess_V_hud')
        recovered()
    case('countess_E_cancel')
    ds = layout([(170, 0), (650, 350), (750, -350)])
    yield .25
    use('E', ds[0])
    yield .34
    pawn().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    after_cancel = health(ds[0])
    yield .9
    check(health(ds[0]) == after_cancel, 'cancelled E cannot deliver later strikes')
    recovered()


def focused_qwer_sequence():
    """Review the requested QWER repair with the same real input and map fixtures."""
    baseline = os.environ.get('QWER_BASELINE') == '1'
    if os.environ.get('QWER_SCOPE') != 'sparrow':
        yield from focused_countess_qwer_sequence()
    if os.environ.get('QWER_SCOPE') == 'countess':
        return
    switch('sparrow')
    yield .8
    if os.environ.get('QWER_VISUAL_ONLY') == '1':
        for letter, times in (('W', (.35, .4, .3, 1.6)), ('E', (.2, .2, .2, .2, .2, .6)), ('R', (.25, .75))):
            case('sparrow_' + letter + '_visual')
            ds = layout([(450, 0), (650, 350), (750, -350)])
            yield .25
            use(letter, ds[0])
            for index, delay in enumerate(times):
                yield delay
                capture('sparrow_' + letter + '_' + str(index))
            if letter == 'R':
                q = aim(ds[0])
                cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
                yield .05
                cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
                yield .25
                capture('sparrow_R_attack')
                yield 1
        return
    case('sparrow_single_click')
    ds = layout([(450, 0), (650, 350), (750, -350)])
    yield .25
    q = aim(ds[0])
    shot_start = unreal.GameplayStatics.get_time_seconds(world())
    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
    yield .05
    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
    STATE['attack_trace'] = []
    for index in range(18):
        yield .04
        token = 'single_click_' + str(index)
        cmd('SparrowQA.State ' + token)
        row = json.loads((OUT / (token + '.json')).read_text(encoding='utf-8-sig'))
        STATE['attack_trace'].append(row)
        if index in (0, 7, 14):
            capture(token)
    check(health(ds[0]) < 100, 'one short click still releases its arrow')
    if not baseline:
        speed = unreal.SystemLibrary.get_console_variable_float_value('Sparrow.Attack.Speed')
        duration = 1.0 / speed
        committed = [row for row in STATE['attack_trace'] if row['time'] - shot_start < duration - .03]
        check(any(row['time'] - shot_start >= duration - .10 for row in committed) and all(row['attacking'] for row in committed),
              'short click remains committed through its speed-adjusted playback')
        if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_gold':
            active = [row for row in STATE['attack_trace'] if row['attacking'] and row['montage']]
            measured_rate = (active[-1]['montage_position'] - active[0]['montage_position']) / (active[-1]['time'] - active[0]['time'])
            check(abs(measured_rate - 1.8) < .05, 'basic montage advances at 1.8x, 1.5 times the prior 1.2x')
            check(any(not row['attacking'] and row['time'] - shot_start < .70 for row in STATE['attack_trace']),
                  'faster single attack finishes within 0.70 seconds')
    yield .7
    check(not pawn().is_attacking(), 'single click returns to idle after completion')
    case('sparrow_hold_attack')
    ds = layout([(450, 0), (650, 350), (750, -350)])
    yield .25
    q = aim(ds[0])
    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
    hold_trace = []
    for index in range(24):
        yield .08
        token = 'held_attack_' + str(index)
        cmd('SparrowQA.State ' + token)
        hold_trace.append(json.loads((OUT / (token + '.json')).read_text(encoding='utf-8-sig')))
        if index in (5, 10, 15):
            capture(token)
    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
    yield .8
    check(health(ds[0]) <= 60, 'holding left mouse still fires repeated arrows')
    check(not pawn().is_attacking(), 'release finishes current attack then returns to idle')
    (OUT / 'attack-trace.json').write_text(json.dumps({'single': STATE['attack_trace'], 'held': hold_trace}, indent=2), encoding='utf-8')
    for letter, times in (('W', (.35, .30, .05, .35, 1.6)), ('E', (.20, .20, .20, .20, .20, .6))):
        case('sparrow_' + letter + '_rework')
        ds = layout([(450, 0), (650, 350), (750, -350)])
        yield .25
        use(letter, ds[0])
        for index, delay in enumerate(times):
            yield delay
            capture('sparrow_' + letter + '_' + str(index))
            cmd('SparrowQA.State sparrow_' + letter + '_state_' + str(index))
            if letter == 'W' and index == 1 and os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_gold':
                arrows = unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowArrow)
                check(len(arrows) == 1, 'W releases one projectile for its width check')
                arrow = arrows[0]
                trail = arrow.get_component_by_class(unreal.ParticleSystemComponent)
                visual = arrow.get_component_by_class(unreal.StaticMeshComponent)
                check(vec(trail.get_editor_property('relative_scale3d')) == [1.0, 2.0, 2.0], 'W trail doubles its width without stretching its length')
                check(vec(visual.get_editor_property('relative_scale3d')) == [2.0, 2.0, 1.0], 'W arrow mesh doubles its cross-section')
                check(arrow.get_editor_property('collision_radius') == 12.0, 'W retains its original collision radius')
        check(health(ds[0]) < 100, letter + ' still damages its forward target')
        recovered()
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_gold':
        case('sparrow_Q_gold_review')
        ds = layout([(450, 0), (650, 350), (750, -350)])
        yield .25
        use('Q', ds[0])
        yield .65
        capture('sparrow_Q_gold')
        cmd('SparrowQA.State sparrow_Q_gold_state')
        yield 3.9
        recovered()
    case('sparrow_E_cancel')
    ds = layout([(450, 0), (650, 350), (750, -350)])
    yield .25
    use('E', ds[0])
    yield .32
    pawn().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    yield .4
    after_cancel = health(ds[0])
    yield .8
    check(health(ds[0]) == after_cancel, 'cancelled rapid shot stops later arrows')
    recovered()
    case('sparrow_R_rework')
    ds = layout([(450, 0), (650, 350), (750, -350)])
    yield .25
    use('R', ds[0])
    yield .25
    capture('sparrow_R_cast')
    yield .75
    q = aim(ds[0])
    cmd(f'CountessComboQA.Mouse Press Left {q.x} {q.y} {q.z}')
    yield .05
    cmd(f'CountessComboQA.Mouse Release Left {q.x} {q.y} {q.z}')
    launch_counts = []
    for index in range(8):
        yield .033
        cmd('SparrowQA.State sparrow_R_launch')
        launched = json.loads((OUT / 'sparrow_R_launch.json').read_text(encoding='utf-8-sig'))
        launch_counts.append(len(launched['projectiles']))
    check(max(launch_counts) == 5, 'R releases five arrows in one fan')
    for index in range(4):
        yield .15
        capture('sparrow_R_attack_' + str(index))
        cmd('SparrowQA.State sparrow_R_state_' + str(index))
    yield .9
    check(health(ds[0]) < 100, 'R still connects an empowered basic attack')
    recovered()
    switch('countess')
    yield .8
    case('qwer_final')
    capture('qwer_review_final')


def tagged(name):
    return [actor for actor in unreal.GameplayStatics.get_all_actors_with_tag(world(), name)
            if unreal.SystemLibrary.is_valid(actor)]


def focused_mobility_sequence():
    switch('countess')
    yield .8
    case('countess_fast_R')
    ds = layout([(380, 0), (650, 350), (750, -350)])
    yield .25
    start = pawn().get_actor_location()
    use('R', ds[0])
    yield .05
    check(dist(start, pawn().get_actor_location()) > 180, 'R approaches its target immediately')
    check(health(ds[0]) == 100, 'R approach does not apply early damage')
    capture('countess_R_immediate')
    yield .48
    check(abs(health(ds[0]) - 20) < .01, 'accelerated R delivers 80 damage')
    capture('countess_R_hit')
    yield .5
    recovered()
    case('countess_fast_R_cancel')
    ds = layout([(380, 0), (650, 350), (750, -350)])
    yield .25
    use('R', ds[0])
    yield .1
    pawn().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    yield .8
    check(health(ds[0]) == 100, 'interrupted R cancels its pending damage')
    check(str(ds[0].get_combat_status()) in ('None', ''), 'interrupted R clears its target stun')
    recovered()
    case('countess_cursor_blink')
    ds = layout([(-650, 500), (-650, 650), (-650, 800)])
    yield .25
    start = pawn().get_actor_location()
    use('SpaceBar', offset=(550, 0))
    yield .05
    check(500 < dist(start, pawn().get_actor_location()) < 600, 'Space blinks once toward the cursor')
    check(not pawn().is_combat_busy(), 'instant blink does not retain a movement lock')
    check(len(tagged('CountessCursorBlinkResidue')) == 3, 'Space leaves three real pose echoes along the blink')
    capture('countess_Space_residue')
    yield .65
    capture('countess_Space_clear')
    yield from focused_blink_boundaries()


def focused_blink_boundaries():
    switch('countess')
    yield .8
    case('countess_cursor_blink_range')
    layout([(-650, 500), (-650, 650), (-650, 800)])
    yield .25
    start = pawn().get_actor_location()
    far_cursor = ground(STATE['origin'].x, STATE['origin'].y + 1100)
    check(skills().try_use_skill_slot(17, far_cursor, None), 'clear out-of-range destination is accepted for clamping')
    yield .1
    check(650 < dist(start, pawn().get_actor_location()) <= 751, 'Space clamps its maximum distance to 750cm')
    yield .6
    case('countess_cursor_blink_wall')
    layout([(-650, 500), (-650, 650), (-650, 800)])
    barrier = wall_fixture(250)
    yield .25
    start = pawn().get_actor_location()
    use('SpaceBar', offset=(550, 0))
    yield .1
    check(dist(start, pawn().get_actor_location()) < 1, 'Space does not teleport through the wall fixture')
    barrier.destroy_actor()
    yield .3
    case('countess_cursor_blink_owner_end')
    layout([(-650, 500), (-650, 650), (-650, 800)])
    yield .25
    use('SpaceBar', offset=(500, 0))
    yield .05
    switch('sparrow')
    yield .7
    check(not tagged('CountessCursorBlinkResidue'), 'switching removes the old blink residue')
    check(not pawn().is_combat_busy(), 'character switch clears the previous input state')


def focused_ascension_sequence():
    switch('sparrow')
    yield .8
    case('sparrow_new_skill_slots')
    cmd('SparrowQA.State ascension_slots')
    slots = json.loads((OUT / 'ascension_slots.json').read_text(encoding='utf-8-sig'))['slots']
    names = {int(item['slot']): item['name'] for item in slots}
    check(all(names.get(slot, '') for slot in (8, 9, 10)), 'new A S D skills are available')
    check(not names.get(11, ''), 'old F skill is removed')
    ds = layout([(450, 0), (750, 0), (450, 350)])
    check(abs(ds[0].get_actor_location().z - ds[1].get_actor_location().z) < 5,
          'gear piercing targets stand on the same clear floor')
    yield .25
    use('F', ds[0])
    yield .2
    check(not skills().is_casting() and all(health(d) == 100 for d in ds), 'removed F cannot start an attack')
    case('sparrow_gear_arrow')
    yield .25
    use('A', ds[0])
    yield .75
    capture('sparrow_A_slow_flight')
    check(health(ds[0]) == 100, 'slow gear arrow does not instantly reach its distant target')
    yield 1.2
    capture('sparrow_A_near_target')
    yield 2.1
    check(abs(health(ds[0]) - 10) < .01 and abs(health(ds[1]) - 10) < .01,
          'gear arrow pierces both path targets once for 90 damage')
    check(health(ds[2]) == 100, 'gear arrow excludes the lateral target')
    recovered()
    yield 2.7
    case('sparrow_gear_arrow_wall')
    ds = layout([(450, 0), (750, 0), (450, 350)])
    barrier = wall_fixture(300)
    yield .25
    use('A', ds[0])
    yield 3.2
    check(health(ds[0]) == 100 and health(ds[1]) == 100, 'gear arrow stops at a wall')
    barrier.destroy_actor()
    yield .3
    if os.environ.get('NEW_SKILLS_FOCUS') not in ('ascension_gear', 'ascension_safety'):
        yield from focused_form_sequence()


def focused_ascension_safety():
    switch('sparrow')
    yield .8
    for letter in ('A', 'S', 'D'):
        yield from cancellation('sparrow', letter, [(450, 0), (750, 0), (450, 350)], .1, 1.1)
        check(not tagged('SparrowGearArrow') and not tagged('SparrowAscensionWings') and not tagged('SparrowMirrorArcher'),
              'interrupted new skill leaves no projectile, wings, or mirror actors')
    case('sparrow_gear_inflight_owner_end')
    ds = layout([(450, 0), (750, 0), (450, 350)])
    yield .25
    use('A', ds[0])
    yield .6
    check(len(tagged('SparrowGearArrow')) == 1, 'gear arrow is in flight before switching')
    switch('countess')
    yield 1.5
    check(not tagged('SparrowGearArrow') and all(health(d) == 100 for d in ds),
          'switching removes an in-flight gear arrow before it can damage')
    yield from cooldown('sparrow', 8, 1.0, 7.2)
    case('sparrow_ascension_recast')
    ds = layout([(450, 0), (750, 0), (450, 350)])
    yield .25
    use('S', ds[0])
    yield 1.0
    check(not skills().try_use_skill_slot(9, ds[0].get_actor_location(), ds[0]), 'active ascension rejects duplicate activation')
    check(len(tagged('SparrowAscensionWings')) == 1, 'rejected ascension keeps exactly one wing actor')
    switch('countess')
    yield .8
    case('countess_fast_R_wall')
    ds = layout([(380, 0), (650, 350), (750, -350)])
    barrier = wall_fixture(250)
    yield .25
    start = pawn().get_actor_location()
    use('R', ds[0])
    yield .8
    check(dist(start, pawn().get_actor_location()) < 1 and health(ds[0]) == 100,
          'instant R rejects the blocked approach without teleporting or damage')
    recovered()
    barrier.destroy_actor()
    yield .2
    case('countess_cursor_blink_busy')
    ds = layout([(380, 0), (650, 350), (750, -350)])
    yield .25
    use('R', ds[0])
    yield .05
    start = pawn().get_actor_location()
    use('SpaceBar', offset=(0, 550))
    yield .05
    check(dist(start, pawn().get_actor_location()) < 1 and not tagged('CountessCursorBlinkResidue'),
          'Space cannot interrupt the active R attack')
    yield 1.0
    recovered()
    case('countess_cursor_blink_cooldown')
    layout([(-650, 500), (-650, 650), (-650, 800)])
    yield .25
    cmd('Countess.Skills.IgnoreCooldowns 0')
    destination = ground(STATE['origin'].x, STATE['origin'].y + 500)
    check(skills().try_use_skill_slot(17, destination, None), 'first Space is accepted with normal cooldowns')
    yield .7
    destination = ground(STATE['origin'].x, STATE['origin'].y)
    check(not skills().try_use_skill_slot(17, destination, None), 'Space cannot be recast during its six-second cooldown')
    check('cooldown' in skills().get_input_feedback().lower(), 'Space rejection identifies cooldown')
    yield 5.5
    check(skills().try_use_skill_slot(17, destination, None), 'Space is accepted after its cooldown expires')
    yield .7
    cmd('Countess.Skills.IgnoreCooldowns 1')
    recovered()


def focused_form_sequence():
    switch('sparrow')
    yield .8
    case('sparrow_ascension_and_mirrors')
    ds = layout([(600, 0), (650, 350), (750, -350)])
    yield .25
    mesh = pawn().get_editor_property('mesh')
    hood = mesh.get_material_index('M14_CloakHood')
    prior = [mesh.is_material_section_shown(hood, lod) for lod in range(5)]
    use('S', ds[0])
    yield .7
    check(not any(mesh.is_material_section_shown(hood, lod) for lod in range(5)), 'S hides the actual hood sections at every LOD')
    check(len(tagged('SparrowAscensionWings')) == 1, 'S owns one separate Serath wing actor')
    capture('sparrow_S_wings')
    yield .45
    capture('sparrow_S_wings_open')
    use('D', ds[0])
    yield .5
    check(len(tagged('SparrowMirrorArcher')) == 2, 'D creates two mirror archers behind the caster')
    capture('sparrow_D_mirrors')
    yield 1.2
    check(abs(health(ds[0]) - 40) < .01, 'two mirror archers fire three arrows each totaling 60 damage')
    recovered()
    yield 6.1
    check([mesh.is_material_section_shown(hood, lod) for lod in range(5)] == prior, 'S restores the original hood visibility when it expires')
    capture('sparrow_S_restored')
    case('sparrow_ascension_owner_end')
    use('S', ds[0])
    yield 1.0
    use('D', ds[0])
    yield .5
    check(len(tagged('SparrowAscensionWings')) == 1 and len(tagged('SparrowMirrorArcher')) == 2,
          'wing and mirror lifetimes coexist before switching')
    switch('countess')
    yield .05
    health_on_switch = health(ds[0])
    yield 1.8
    check(not tagged('SparrowAscensionWings') and not tagged('SparrowMirrorArcher'), 'switching retires wings and mirror archers')
    check(not tagged('SparrowGearArrow'), 'switching retires old gear arrows')
    check(health(ds[0]) == health_on_switch, 'old mirror volley cannot damage after its owner ends')
    recovered()


def preview_serath_wings():
    """Unsaved real-mesh placement study while native implementation is prepared."""
    switch('sparrow')
    yield .8
    case('serath_wing_asset_preview')
    layout([(-650, 500), (-650, 650), (-650, 800)])
    source_mesh = pawn().get_editor_property('mesh')
    location = source_mesh.get_world_location()
    cmd(f'CountessComboQA.Spawn WingAssetStudy /Script/Engine.SkeletalMeshActor {location.x} {location.y} {location.z}')
    actor = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SkeletalMeshActor)
                 if a.get_name() == 'WingAssetStudy')
    actor.set_actor_rotation(source_mesh.get_world_rotation(), True)
    actor.set_actor_scale3d(unreal.Vector(.85, .85, .85))
    mesh = actor.get_editor_property('skeletal_mesh_component')
    mesh.set_skeletal_mesh_asset(unreal.load_asset('/Game/ParagonSerath/Characters/Heroes/Serath/Meshes/Serath'))
    mesh.set_forced_lod(1)
    mesh.suspend_clothing_simulation()
    mesh.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    for material_id in range(15):
        if material_id not in (12, 13):
            mesh.set_material(material_id, source_mesh.get_material(1))
        for lod in range(5):
            mesh.show_material_section(material_id, -1, material_id in (12, 13), lod)
    for material_id in (12, 13):
        material = mesh.create_dynamic_material_instance(material_id)
        material.set_scalar_parameter_value('WingAlpha', 1)
        material.set_scalar_parameter_value('Holy=True', 1)
        if material_id == 12:
            material.set_scalar_parameter_value('HDRTintMult', 1)
            material.set_scalar_parameter_value('GoldBoost', 2)
            for name, color in [('Holy1', (.9, .65, .18, 1)), ('Holy2', (.6, .36, .05, 1)), ('Holy3', (.14, .08, .008, 1))]:
                material.set_vector_parameter_value(name, unreal.LinearColor(*color))
        else:
            for name, color in [('HolyColor', (.8, .5, .1, 0)), ('HolyColor1', (.16, .08, .01, 0)),
                                ('HolyWeb1', (.8, .65, .18, 1)), ('HolyWeb2', (.1, .08, .01, 1))]:
                material.set_vector_parameter_value(name, unreal.LinearColor(*color))
    for lod in range(5):
        source_mesh.show_material_section(13, -1, False, lod)
    clip_rows = []
    for name in ('Wings_Unfold', 'Idle_Pose_Wings', 'E_Ability_Wing_Flap_Holy'):
        clip = unreal.load_asset('/Game/ParagonSerath/Characters/Heroes/Serath/Animations/' + name)
        row = {'clip': name, 'length': clip.get_play_length(), 'curves': {}}
        for curve in ('WingAlpha', 'HolyScale', 'thicness'):
            times, values = unreal.AnimationLibrary.get_float_keys(clip, curve)
            row['curves'][curve] = {'times': list(times), 'values': list(values)}
        mesh.play_animation(clip, False)
        yield .3
        capture('serath_' + name + '_early')
        yield min(1.4, max(.2, clip.get_play_length() - .3))
        capture('serath_' + name + '_late')
        clip_rows.append(row)
    (OUT / 'wing-clips.json').write_text(json.dumps(clip_rows, indent=2), encoding='utf-8')
    actor.destroy_actor()
    for lod in range(5):
        source_mesh.show_material_section(13, -1, True, lod)


def sparrow_feedback_production():
    """Short affected-skill check for the user's Q/W/A/S/D feedback."""
    switch('sparrow')
    yield .8
    if os.environ.get('SPARROW_FEEDBACK_W_ONLY') != '1':
        case('Q_feedback_clear_floor')
        ds = layout([(570, 80), (450, 430), (-600, -400)])
        yield .2
        use('Q', offset=(450, 0))
        yield .9
        check(not unreal.GameplayStatics.get_all_actors_with_tag(world(), 'SparrowHailAtmosphere'),
              'Q has no ground fog actor')
        capture('Q_clear_floor')
        yield 3.5
        check(abs(health(ds[0])-60) < .01 and health(ds[1]) == 100,
              'Q retains 40 damage and radius exclusion')
        recovered()
        if os.environ.get('SPARROW_FEEDBACK_Q_ONLY') == '1':
            return
    case('W_feedback_recovery')
    ds = layout([(650, 0), (650, 350), (-650, -350)])
    yield .2
    started = unreal.GameplayStatics.get_time_seconds(world())
    use('W', ds[0])
    released = None
    for _ in range(round(FPS * .9)):
        yield 1/FPS
        if released is None and unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowShotWave):
            released = unreal.GameplayStatics.get_time_seconds(world())
            capture('W_release')
        if not skills().is_casting():
            break
    unlocked = unreal.GameplayStatics.get_time_seconds(world())
    check(released is not None, 'W releases its arrow before recovery')
    check(unlocked-started < .82 and unlocked-released <= .14,
          'W unlocks within 0.14s of release')
    recovered()
    capture('W_unlocked')
    # Moving immediately after release must not recall the arrow already in flight.
    p0 = pawn().get_actor_location()
    q = ground(p0.x, p0.y + 260)
    cmd(f'CountessComboQA.Mouse Press Right {q.x} {q.y} {q.z}')
    yield 1/FPS
    cmd(f'CountessComboQA.Mouse Release Right {q.x} {q.y} {q.z}')
    yield .3
    check(dist(pawn().get_actor_location(), p0) > 30, 'W permits immediate movement after recovery')
    check(abs(health(ds[0])-65) < .01, 'released W arrow retains damage35')
    (OUT/'W-feedback-timing.json').write_text(json.dumps({'release':released-started,
        'recovery':unlocked-started,'post_release_lock':unlocked-released,'fps':FPS},indent=2),encoding='utf-8')
    yield .4
    case('W_feedback_cancel')
    ds = layout([(650, 0), (650, 350), (-650, -350)])
    yield .2
    use('W', ds[0])
    yield .25
    pawn().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    yield .7
    check(health(ds[0]) == 100, 'cancelled W does not release a delayed arrow')
    recovered()
    if os.environ.get('SPARROW_FEEDBACK_W_ONLY') == '1':
        return
    case('A_feedback_slow')
    ds = layout([(450, 0), (750, 0), (450, 350)])
    yield .2
    use('A', ds[0])
    yield .8
    arrows = unreal.GameplayStatics.get_all_actors_of_class(world(), unreal.SparrowGearArrow)
    check(len(arrows) == 1 and abs(arrows[0].get_flight_speed()-220) < .01,
          'A speed is220cm/s')
    capture('A_slower_flight')
    yield 3.5
    check(all(abs(health(d)-10) < .01 for d in ds[:2]) and health(ds[2]) == 100,
          'slower A retains90damage per target and lateral exclusion')
    yield 4.5
    recovered()


def sequence():
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_feedback':
        import runpy
        folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
        parts = os.environ.get('SPARROW_FEEDBACK_PARTS', 'production,forms,e').split(',')
        if 'production' in parts:
            yield from sparrow_feedback_production()
        for part, name in (('forms', 'sparrow_form_studies.py'), ('e', 'sparrow_e_texture_studies.py')):
            if part in parts:
                yield from runpy.run_path(str(folder/name))['sequence'](globals())
        for name in os.environ.get('SPARROW_FEEDBACK_STUDIES', '').split(','):
            if name:
                helper = (folder / name).resolve()
                assert helper.parent == folder.resolve(), 'feedback helper must be a CharacterPipeline tool'
                yield from runpy.run_path(str(helper))['sequence'](globals())
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_volume':
        import runpy
        folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
        yield from runpy.run_path(str(folder / 'sparrow_volume_polish.py'))['sequence'](globals())
        return
    if os.environ.get('NEW_SKILLS_FOCUS') in ('sparrow_arsenal', 'sparrow_arsenal_safety', 'sparrow_e_variants'):
        import runpy
        folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
        if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_e_variants':
            yield from runpy.run_path(str(folder / 'sparrow_e_variants.py'))['sequence'](globals())
        else:
            yield from runpy.run_path(str(folder / 'sparrow_arsenal_pass.py'))['sequence'](globals())
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_adopted':
        import runpy
        helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_flow_concepts.py'
        yield from runpy.run_path(str(helper))['installed_sequence'](globals())
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_refined':
        import runpy
        folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
        yield from runpy.run_path(str(folder / 'sparrow_flow_concepts.py'))['refined_sequence'](globals())
        yield from runpy.run_path(str(folder / 'sparrow_bow_audit.py'))['fitting_sequence'](globals())
        fitting = json.loads((OUT / 'sparrow-bow-fitting.json').read_text(encoding='utf-8'))
        check(fitting['passed'], 'Raven bow fitting keeps Rogue outfit and restores temporary changes')
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_bows':
        import runpy
        helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_bow_audit.py'
        bow = runpy.run_path(str(helper))
        check(STATE['bow_audit']['passed'], 'eight Sparrow skin meshes inspected before PIE')
        yield from bow['preview_sequence'](globals())
        preview = json.loads((OUT / 'sparrow-bow-preview.json').read_text(encoding='utf-8'))
        check(preview['passed'] and preview['preview_cleaned'], 'bow previews captured and temporary actor cleaned')
        yield .8
        case('sparrow_flow_R_blend')
        ds = layout([(450, 0), (650, 350), (750, -350)])
        yield .25
        use('R', ds[0])
        yield 1.0
        check(skills().is_inner_fire_active(), 'R enhancement is active for the blend check')
        check(pawn().try_basic_attack(ds[0].get_actor_location()), 'enhanced basic shot starts')
        yield .7
        check(health(ds[0]) < 100 and not pawn().is_attacking(), 'enhanced shot still hits and finishes with faster blending')
        recovered()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_flow':
        import runpy
        helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_flow_concepts.py'
        yield from runpy.run_path(str(helper))['sequence'](globals())
        return
    if AUDITION:
        yield from audition_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'mobility':
        yield from focused_mobility_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'blink_boundaries':
        yield from focused_blink_boundaries()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') in ('ascension', 'ascension_gear'):
        yield from focused_ascension_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'ascension_safety':
        yield from focused_ascension_sequence()
        yield from focused_ascension_safety()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'ascension_final':
        yield from focused_blink_boundaries()
        yield from focused_ascension_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'ascension_form':
        yield from focused_form_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'wing_preview':
        yield from preview_serath_wings()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'qwer_tint':
        switch('countess')
        yield .8
        for gain in (.02, .06, .12):
            case('countess_E_gain_' + str(gain))
            ds = layout([(170, 0), (650, 350), (750, -350)])
            yield .25
            cmd('Countess.Skills.EInkGain ' + str(gain))
            use('E', ds[0])
            yield .5
            capture('countess_E_gain_' + str(gain) + '_mid')
            yield .17
            capture('countess_E_gain_' + str(gain) + '_main')
            yield 1.0
            check(abs(health(ds[0]) - 55) < .01, 'six-strike E damage remains 45')
            recovered()
        cmd('Countess.Skills.EInkGain .06')
        return
    if os.environ.get('NEW_SKILLS_FOCUS') == 'countess_D':
        yield from focused_tide_sequence()
        return
    if os.environ.get('NEW_SKILLS_FOCUS') in ('qwer_rework', 'sparrow_gold'):
        yield from focused_qwer_sequence()
        return
    if os.environ.get('NEW_SKILLS_REFERENCE') == '1':
        yield from reference_sequence()
        return
    selection = os.environ.get('NEW_SKILLS_ONLY', '')
    if os.environ.get('NEW_SKILLS_PHASE') != 'integration':
        if selection != 'sparrow':
            yield from countess()
        if selection != 'countess':
            yield from sparrow()
    if os.environ.get('NEW_SKILLS_SMOKE') != '1' and os.environ.get('NEW_SKILLS_PHASE') != 'skills':
        yield from boundaries()
        yield from existing_regression()
    case('final')
    capture('new_skills_final_hud')


def finish(error=None):
    finish_video_clip()
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    report = {'passed': error is None, 'error': error, 'fps': FPS, 'checks': STATE['checks'],
              'samples': STATE['samples'], 'assets_saved': bool(STATE.get('author_result')), 'visual_review': 'pending',
              'scope': os.environ.get('NEW_SKILLS_ONLY', 'both'),
              'normal_cases_skipped': os.environ.get('NEW_SKILLS_SKIP_NORMAL', ''),
              'qwer_scope': os.environ.get('QWER_SCOPE', 'both'),
              'qa_memory_budget': os.environ.get('NEW_SKILLS_QA_BUDGET') == '1',
              'phase': os.environ.get('NEW_SKILLS_PHASE', 'full')}
    (OUT / 'new-skills.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if AUDITION:
        (OUT / 'asset-audition.json').write_text(json.dumps({'passed': error is None, 'error': error,
            'items': AUDITION, 'meshes': STATE.get('audition_meshes', []), 'assets_saved': False,
            'camera': 'normal gameplay viewport 1280x720'}, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()


def tick(delta):
    try:
        if STATE['phase'] == 'loading':
            return
        if time.monotonic() - STATE['wall'] > 600:
            raise TimeoutError('new skill PIE batch exceeded 600 wall seconds')
        if STATE['phase'] == 'load':
            # Asset tools may pump Slate during duplication/compilation; do not reenter map loading.
            STATE['phase'] = 'loading'
            if os.environ.get('NEW_SKILLS_QA_BUDGET') == '1':
                editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
                for command in ('r.Streaming.PoolSize 512', 'r.Streaming.UseFixedPoolSize 1',
                                'r.Shadow.Virtual.MaxPhysicalPages 1024'):
                    unreal.SystemLibrary.execute_console_command(editor_world, command)
            unreal.EditorLoadingAndSavingUtils.load_map(MAP)
            if os.environ.get('NEW_SKILLS_FOCUS') in ('sparrow_bows', 'sparrow_refined'):
                import runpy
                helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_bow_audit.py'
                STATE['bow_audit'] = runpy.run_path(str(helper))['audit'](OUT)
                assert STATE['bow_audit']['passed'], 'bow mesh inspection failed before PIE'
            if os.environ.get('ASCENSION_INSPECT') == '1':
                inspect_ascension_wings()
            if os.environ.get('NEW_SKILLS_AUTHOR'):
                import runpy
                author = runpy.run_path(os.environ['NEW_SKILLS_AUTHOR'])['author']
                STATE['author_result'] = author(OUT)
                assert STATE['author_result']['passed'], 'presentation asset author failed'
                if os.environ.get('NEW_SKILLS_FOCUS') == 'asset_author':
                    finish()
                    return
            if os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_feedback':
                import runpy
                folder = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline'
                for name in os.environ.get('SPARROW_FEEDBACK_AUTHORS', '').split(','):
                    if name:
                        result = runpy.run_path(str(folder/name))['author'](OUT)
                        assert result['passed'], name + ' failed'
            if AUDITION:
                if os.environ.get('FX_DUMP'):
                    import runpy
                    os.environ['FX_DUMP_KEEP_EDITOR'] = '1'
                    runpy.run_path(str(Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/fx_emitter_dump.py'))
                stage_audition_meshes()
            if os.environ.get('NEW_SKILLS_VISUAL') == '1':
                inspect_presentation_materials()
            STATE['phase'] = 'nav'
            return
        if STATE['phase'] == 'nav':
            ew = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            if time.monotonic() - STATE['wall'] < 3 or unreal.NavigationSystemV1.is_navigation_being_built(ew):
                return
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            STATE['phase'] = 'play'
            return
        w = world()
        p = unreal.GameplayStatics.get_player_character(w, 0) if w else None
        if not p:
            return
        now = unreal.GameplayStatics.get_time_seconds(w)
        if STATE['phase'] == 'play':
            if now < 4:
                return
            cmd('CharacterPipeline.OutputDirectory "' + OUT.as_posix() + '"')
            cmd('CharacterVisualQA.ViewportSize 1280 720')
            cmd('Countess.Skills.IgnoreCooldowns 1')
            cmd('Sparrow.Skills.IgnoreCooldowns 1')
            STATE['origin'] = p.get_actor_location()
            STATE['dummies'] = sorted(targets(), key=lambda d: d.get_name())[:3]
            check(len(STATE['dummies']) == 3, 'training room provides three target fixtures')
            STATE['iterator'] = sequence()
            STATE['phase'] = 'run'
            STATE['until'] = now + 0.2
            return
        record_video_frame(now)
        for shot in list(STATE.get('pending_shots', [])):
            deadline, shot_case, label = shot
            if now >= deadline:
                STATE['pending_shots'].remove(shot)
                if STATE['case'] == shot_case:
                    capture(label)
        if now < STATE['until']:
            return
        delay = next(STATE['iterator'])
        STATE['until'] = now + max(1.0 / FPS, float(delay))
    except StopIteration:
        finish()
    except Exception:
        error = traceback.format_exc()
        unreal.log_error(error)
        finish(error)


HANDLE = unreal.register_slate_post_tick_callback(tick)
