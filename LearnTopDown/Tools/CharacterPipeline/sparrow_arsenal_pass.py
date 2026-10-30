"""Scoped native PIE checks for the ground Q / multishot R / event-driven mirrors batch."""
import json
import os
import unreal


def sequence(rig):
    world, pawn, skills = rig['world'], rig['pawn'], rig['skills']
    check, case, capture = rig['check'], rig['case'], rig['capture']
    use, layout, health = rig['use'], rig['layout'], rig['health']
    def actors(cls):
        return list(unreal.GameplayStatics.get_all_actors_of_class(world(), cls))
    def tagged(tag):
        return list(unreal.GameplayStatics.get_all_actors_with_tag(world(), tag))
    def now():
        return unreal.GameplayStatics.get_time_seconds(world())
    def arrows():
        return actors(unreal.SparrowArrow)
    def mirrors():
        return actors(unreal.SparrowMirrorArcher)
    def cancel():
        pawn().get_editor_property('mesh').get_anim_instance().montage_stop(.02)
    def xy_distance(a, b):
        return ((a.x-b.x)**2 + (a.y-b.y)**2)**.5
    result = {'passed': False, 'fps': rig['FPS'], 'runtime_visual_overrides': False}
    rig['switch']('sparrow')
    yield .8
    safety = os.environ.get('NEW_SKILLS_FOCUS') == 'sparrow_arsenal_safety'

    if not safety:
        case('Q_empty_ground')
        ds = layout([(570, 80), (450, 430), (-600, -400)])
        yield .2
        aim = use('Q', offset=(450, 0))
        yield .55
        indicators = tagged('SparrowHailRangeIndicator')
        check(skills().get_active_hail_count() == 1, 'Q casts on empty ground with no selected object')
        check(len(indicators) == 1 and xy_distance(indicators[0].get_actor_location(), aim) < 5,
              'Q remains at the cursor ground point instead of snapping to a nearby object')
        capture('Q_ground_rain')
        yield .6
        capture('Q_ground_impacts')
        yield 3.4
        check(abs(health(ds[0])-60) < .01, 'Q still deals 40 total damage inside radius300')
        check(health(ds[1]) == 100, 'Q excludes targets outside its radius')
        check(skills().get_active_hail_count() == 0, 'Q zone and timer expire')
        rig['recovered']()

        case('W_compressed_release')
        ds = layout([(650, 0), (750, 350), (750, -350)])
        yield .2
        use('W', ds[0])
        waves = []
        for _ in range(80):
            yield 1/60
            waves = actors(unreal.SparrowShotWave)
            if waves: break
        check(len(waves) == 1, 'W releases the production wave actor')
        wave = waves[0]
        started = now()
        capture('W_release_flash')
        yield .055
        capture('W_release_rings')
        yield .115
        if unreal.SystemLibrary.is_valid(wave):
            check(not any(m.is_visible() for m in wave.get_components_by_class(unreal.StaticMeshComponent)),
                  'W ring and axial flash are invisible within .18s')
        yield .15
        check(not actors(unreal.SparrowShotWave), 'W release actor clears within .32s')
        result['W_checked_cleanup_seconds'] = now()-started
        yield 1.6
        check(abs(health(ds[0])-65) < .01, 'W retains damage35')
        rig['recovered']()

        case('A_compact_feather')
        ds = layout([(450, 0), (750, 0), (450, 350)])
        yield .2
        use('A', ds[0])
        yield .75
        gear = actors(unreal.SparrowGearArrow)
        check(len(gear) == 1, 'A produces one slow feather projectile')
        arrow = gear[0]
        check(abs(arrow.get_flight_speed()-320) < .01, 'A slow speed remains320cm/s')
        rings = [m for m in arrow.get_components_by_class(unreal.StaticMeshComponent) if 'FeatherRing' in m.get_name()]
        check(len(rings) == 2 and max(m.get_editor_property('relative_scale3d').x for m in rings) < 1.7,
              'A feather silhouette is smaller than the prior2.35 scale')
        capture('A_compact_feather')
        yield 3.3
        check(all(abs(health(d)-10) < .01 for d in ds[:2]), 'compact A still pierces each target once for90')
        check(health(ds[2]) == 100, 'A retains lateral exclusion')
        yield 2.1
        rig['recovered']()

    case('R_multishot_cone')
    ds = layout([(450, 0), (560, 300), (450, -550)])
    yield .2
    use('R', offset=(750, 0))
    seen = set()
    peak = 0
    fps = rig['FPS']
    sample_frames = {round(13 * fps / 60) - 1: 12, round(30 * fps / 60) - 1: 29}
    for index in range(round(.75 * fps)):
        yield 1/fps
        active = arrows()
        seen.update(a.get_path_name() for a in active)
        peak = max(peak, len(active))
        if index in sample_frames: capture('R_multishot_' + str(sample_frames[index]))
    yield .65
    check(peak >= 62, 'R visibly overlaps multiple31-arrow waves')
    check(len(seen) == 186, 'R emits all186 small arrows across six waves')
    check(abs(health(ds[0])-40) < .01, 'R central target takes10 perwave,60 total without shotgun stacking')
    check(health(ds[1]) < 100, 'R wide cone hits a lateral target')
    check(health(ds[2]) == 100, 'R excludes a target outside the cone')
    check(not skills().is_inner_fire_active(), 'R ends as an active volley without leaving the old buff')
    rig['recovered']()
    result['R_peak_arrows'] = peak
    result['R_unique_observed_arrows'] = len(seen)
    yield .8

    if os.environ.get('SPARROW_R_WALL_VISUAL') == '1':
        case('D_R_wall_visual')
        ds = layout([(650, 0), (750, 350), (750, -350)])
        use('D', offset=(650, 0))
        yield 1.
        use('R', offset=(850, 0))
        yield .75
        check(all(e.get_echo_shot_count() == 186 for e in mirrors()), 'wall visual pass preserves all186 mirrored R arrows')
        capture('D_echo_R')
        yield .5
        rig['switch']('countess')
        yield .7
        check(not mirrors() and not arrows(), 'wall visual pass cleans owned arrows and mirrors')
        result.update(passed=True, scope='R and mirrored R wall impact visual refinement')
        (rig['OUT']/'arsenal-pass.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        return

    case('R_cancel')
    ds = layout([(450, 0), (650, 350), (750, -350)])
    yield .2
    use('R', offset=(750, 0))
    yield .23
    cancel()
    yield .65
    after = health(ds[0])
    yield .5
    check(after >= 80 and health(ds[0]) == after, 'interrupted R stops future waves while released arrows finish')
    rig['recovered']()

    case('D_echo_events')
    ds = layout([(650, 0), (750, 350), (750, -350)])
    yield .2
    use('D', offset=(650, 0))
    yield 1.0
    echo = mirrors()
    check(len(echo) == 2 and all(e.is_active() for e in echo), 'D creates exactly2 persistent active mirrors')
    check(all(e.get_echo_shot_count() == 0 for e in echo), 'D waits for actual player attacks instead of auto-firing3shots')
    before = [e.get_actor_location() for e in echo]
    p0 = pawn().get_actor_location()
    pawn().set_actor_location(p0 + unreal.Vector(0, 110, 0), False, True)
    yield .3
    check(all(xy_distance(e.get_actor_location(), p) > 50 for e, p in zip(echo, before)), 'D mirrors follow the moving owner')
    pawn().set_actor_location(p0, False, True)
    yield .2
    q = rig['aim'](ds[0])
    check(pawn().try_basic_attack(q), 'basic attack starts while D is active')
    yield .8
    check(all(e.get_echo_shot_count() == 1 for e in echo), 'each D mirror copies one actual basic arrow')
    ds = layout([(650, 0), (750, 350), (750, -350)])
    use('E', ds[0])
    yield .45
    if not safety: capture('D_echo_E')
    yield .95
    check(all(e.get_echo_shot_count() == 7 for e in echo), 'each D mirror copies all6 E releases')
    if not safety: capture('D_echo_formation')
    use('W', ds[1])
    yield 2.4
    check(all(e.get_echo_shot_count() == 8 for e in echo), 'each D mirror copies W release')
    use('Q', offset=(450, -200))
    yield .55
    check(skills().get_active_hail_count() == 3, 'D mirrors copy Q with3 scaled rain zones')
    if not safety: capture('D_echo_Q')
    yield 1.2
    rig['recovered']()
    yield 4.4
    check(not mirrors() and skills().get_mirror_remaining() == 0, 'D mirrors expire after their lifetime')
    check(skills().get_active_hail_count() == 0, 'mirrored Q zones clear without orphan timers')

    case('D_echo_R_A_and_owner_end')
    ds = layout([(650, 0), (750, 350), (750, -350)])
    use('D', offset=(650, 0))
    yield 1.0
    echo = mirrors()
    use('R', offset=(850, 0))
    yield .75
    check(all(e.get_echo_shot_count() == 186 for e in echo), 'each mirror copies all186 R arrows without recursion')
    capture('D_echo_R')
    yield .5
    use('A', offset=(800, -150))
    yield .7
    check(len(actors(unreal.SparrowGearArrow)) == 3, 'D mirrors copy the slow A projectile')
    check(all(e.get_echo_shot_count() == 187 for e in echo), 'A increments each mirror once')
    rig['switch']('countess')
    yield .7
    check(not mirrors() and not arrows() and not tagged('SparrowHailRangeIndicator'),
          'switching character removes mirrors, arrows and owned range indicators')
    rig['switch']('sparrow')
    yield .8
    rig['recovered']()

    case('S_golden_form_restore')
    mesh = pawn().get_editor_property('mesh')
    material_paths = [mesh.get_material(i).get_path_name() for i in range(mesh.get_num_materials())]
    # These slots were audited from the imported Rogue mesh, not inferred from appearance.
    slots = [mesh.get_material_index(name) for name in ('M16_CloakStraps', 'M08_Cloak', 'M14_CloakHood')]
    slots = [i for i in slots if i >= 0]
    check(len(slots) == 3, 'Rogue hood, cape and strap material slots resolve')
    visibility = {(i,lod): mesh.is_material_section_shown(i,lod) for i in slots for lod in range(mesh.get_num_lods())}
    use('S', offset=(650, 0))
    yield 1.25
    check(skills().get_ascension_remaining() > 6, 'S golden form is active')
    check(all(not mesh.is_material_section_shown(i,lod) for i,lod in visibility), 'S hides cape, straps and hood in every LOD')
    changed = [i for i in range(mesh.get_num_materials()) if mesh.get_material(i).get_path_name() != material_paths[i]]
    check(len(changed) >= 5, 'S applies the golden form to the body materials')
    if not safety: capture('S_gold_cape_removed')
    use('D', offset=(650, 0))
    yield 1.1
    echo = mirrors()
    check(len(echo) == 2, 'D remains available during S')
    for clone in echo:
        wing = next((c for c in clone.get_components_by_class(unreal.SkeletalMeshComponent)
                     if c.get_name() == 'MirrorAscensionWings'), None)
        check(wing is not None and wing.is_visible(), 'D mirrors also display the active S wings')
    if not safety: capture('S_D_gold_formation')
    use('D', offset=(650, 0))
    yield .2
    check(len(mirrors()) == 2 and not skills().is_casting(), 'D recast cannot accumulate extra mirrors')
    yield 6.2
    check(skills().get_ascension_remaining() == 0, 'S expires normally')
    check(all(mesh.get_material(i).get_path_name() == path for i,path in enumerate(material_paths)), 'S restores every original body material')
    check(all(mesh.is_material_section_shown(i,lod) == shown for (i,lod),shown in visibility.items()), 'S restores prior cape visibility for every LOD')
    if not safety: capture('S_form_restored')
    rig['recovered']()
    check(all(not c.is_visible() for clone in mirrors()
              for c in clone.get_components_by_class(unreal.SkeletalMeshComponent)
              if c.get_name() == 'MirrorAscensionWings'), 'D copied wings disappear when S ends')
    rig['switch']('countess')
    yield .6
    check(not mirrors() and not actors(unreal.SparrowAscensionWings), 'owner switch clears the remaining form and mirrors')
    rig['switch']('sparrow')
    yield .6
    result['passed'] = True
    (rig['OUT']/'arsenal-pass.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if not safety and os.environ.get('SPARROW_VOLUME_REVIEW') == '1':
        import runpy
        from pathlib import Path
        helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_volume_polish.py'
        yield from runpy.run_path(str(helper))['sequence'](rig)
    if not safety and os.environ.get('SPARROW_ARSENAL_E') == '1':
        import runpy
        from pathlib import Path
        helper = Path(unreal.Paths.project_dir()) / 'Tools/CharacterPipeline/sparrow_e_variants.py'
        yield from runpy.run_path(str(helper))['sequence'](rig)
