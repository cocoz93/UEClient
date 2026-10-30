"""Real native S binding / F counter ward through the existing probe rig.

No author callback. The two videos are actual S/F casts. Test projectiles are
launched by the editor-only C++ fixture through native InitArrow/Launch/Sweep;
their retained hit counts and training-dummy health are evidence, not light props.
SPARROW_SANCTUARY_SHORT=1 repeats the two main cases without AI/cooldown repeats.
"""
import json
import os
from pathlib import Path

import unreal


def _now(rig):
    return unreal.GameplayStatics.get_time_seconds(rig['world']())


def _valid(value):
    return value is not None and unreal.SystemLibrary.is_valid(value)


def _effects(rig):
    return list(unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowSanctuary))


def _json(rig, name):
    return json.loads((Path(rig['OUT'])/(name+'.json')).read_text(encoding='utf-8-sig'))


def _state(rig, name):
    rig['cmd']('SparrowSanctuaryQA.State '+name)
    return _json(rig, name)


def _launch(rig, name, shooter, position, direction, kind='arrow', speed=12000., damage=14.):
    rig['cmd'](f'SparrowSanctuaryQA.Launch {name} {shooter.get_name()} '
               f'{position.x} {position.y} {position.z} {direction.x} {direction.y} {direction.z} {speed} {damage} {kind}')
    row = _json(rig, name)
    rig['check'](row['launched'], 'real native '+kind+' projectile launched')
    return row


def _shot(rig, name):
    rig['cmd']('SparrowSanctuaryQA.Shot '+name)
    return _json(rig, name+'_shot')


def _world_impacts(rig):
    # SpawnEmitterAtLocation owns its native PSC on WorldSettings.
    rows = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.WorldSettings):
        for particle in actor.get_components_by_class(unreal.ParticleSystemComponent):
            template = particle.get_editor_property('template')
            if _valid(template) and template.get_name() == 'P_Sparrow_Primary_Ballistic_HitWorld':
                point = particle.get_world_location()
                rows.append({'name': particle.get_name(), 'template': template.get_path_name(),
                             'position': [point.x, point.y, point.z]})
    return rows


def _clip(rig, name):
    rig['case'](name)
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {'case': name, 'prefix': name+'_video',
            'cast_time': _now(rig), 'frame_times': []}


def _fresh(rig):
    rig['switch']('countess')
    yield .2
    rig['switch']('sparrow')
    yield .65


def sequence(rig):
    short = os.environ.get('SPARROW_SANCTUARY_SHORT') == '1'
    previous_cooldowns = unreal.SystemLibrary.get_console_variable_int_value('Sparrow.Skills.IgnoreCooldowns')
    rows = {'short_repeat': short, 'clips': []}
    fixtures = []
    try:
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns 0')
        yield from _fresh(rig)
        ds = rig['layout']([(430, 0), (650, 380), (650, -350)])
        yield .2
        before = rig['health'](ds[0])
        _clip(rig, 'S_native_golden_binding')
        started = _now(rig)
        rig['use']('S', offset=(450, 20))
        yield 1./rig['FPS']
        state_s = _state(rig, 'sanctuary_S_started')
        rig['check'](state_s['active_skill'] == 10 and state_s['cooldown_s'] > 9.5 and state_s['cooldown_v'] == 0.,
                     'new S is active number10 with its own cooldown while V remains ready')
        rig['key']('SpaceBar')
        yield 1./rig['FPS']
        rig['use']('S', offset=(450, 20))
        yield 1./rig['FPS']
        rig['check'](rig['skills']().get_active_skill_number() == 10 and len(_effects(rig)) == 1,
                     'Space and recast are rejected during S casting without a duplicate actor')
        captured = set()
        bound_status = None
        while _now(rig)-started < 2.85:
            elapsed = _now(rig)-started
            if elapsed >= .65 and bound_status is None:
                bound_status = str(ds[0].get_combat_status())
                rig['check'](abs(before-rig['health'](ds[0])-12.) < .01 and bound_status == 'GOLD_BIND',
                             'S selects the cursor-near enemy and applies one12-damage native binding')
            for moment in (.65, 1.35, 2.45):
                if elapsed >= moment and moment not in captured:
                    rig['capture']('S_binding_'+str(round(moment*100)))
                    captured.add(moment)
            yield 1./rig['FPS']
        rig['recovered']()
        rig['check'](str(ds[0].get_combat_status()) == 'None' and not _effects(rig),
                     'S releases its owned status and all visuals after the two-second binding')
        rows['S'] = {'damage': before-rig['health'](ds[0]), 'bound_status': bound_status,
            'initial_state': state_s, 'remaining_status': str(ds[0].get_combat_status())}
        rows['clips'].append('S_native_golden_binding_video')
        if not short:
            rig['use']('V', offset=(550, 0))
            yield 1./rig['FPS']
            state_v = _state(rig, 'sanctuary_V_independent')
            rig['check'](state_v['active_skill'] == 17 and state_v['cooldown_s'] > 6.5 and state_v['cooldown_v'] > 15.,
                         'S9 and V16 retain independent cooldowns and V active number17')
            yield 1.5
            rig['recovered']()
            rows['S_V_independence'] = state_v

        yield from _fresh(rig)
        ds = rig['layout']([(650, 130), (-250, 130), (750, -350)])
        yield .2
        base = rig['pawn']().get_actor_location()
        z = ds[0].get_actor_location().z
        # A direct center-lane control proves the native arrow can hit the real
        # player even though this demo character does not expose gameplay health.
        _launch(rig, 'sanctuary_control_body', ds[0], unreal.Vector(base.x+595., base.y, z), unreal.Vector(-1., 0., 0.))
        yield .18
        control_body = _shot(rig, 'sanctuary_control_body')
        rig['check'](control_body['native_hit_count'] == 1, 'unprotected native center-lane projectile actually hits the player')
        _launch(rig, 'sanctuary_control_dummy', ds[0], unreal.Vector(base.x+595., base.y+130., z), unreal.Vector(-1., 0., 0.))
        yield .18
        control_dummy = _shot(rig, 'sanctuary_control_dummy')
        rig['check'](control_dummy['native_hit_count'] == 1 and abs(rig['health'](ds[1])-86.) < .01,
                     'unprotected native side lane deals the real14damage to the rear dummy')
        ds[0].reset_dummy()
        ds[1].reset_dummy()
        _clip(rig, 'F_native_counter_ward')
        started = _now(rig)
        rig['use']('F', offset=(600, 0))
        yield 1./rig['FPS']
        f_start = _state(rig, 'sanctuary_F_started')
        rig['check'](f_start['active_skill'] == 12 and f_start['cooldown_f'] > 11.5, 'new F uses active number12 and its own cooldown')
        rig['key']('SpaceBar')
        yield 1./rig['FPS']
        rig['use']('F', offset=(600, 0))
        yield 1./rig['FPS']
        rig['check'](rig['skills']().get_active_skill_number() == 12 and len(_effects(rig)) == 1,
                     'Space and F recast are rejected during F casting')
        guard = _effects(rig)[0]
        launched, captured, friendly_crossed = set(), set(), False
        forward_result = None
        while _now(rig)-started < 3.05:
            elapsed = _now(rig)-started
            if elapsed >= .45 and 'arrow' not in launched:
                _launch(rig, 'sanctuary_guard_body', ds[0], unreal.Vector(base.x+595., base.y, z), unreal.Vector(-1., 0., 0.))
                launched.add('arrow')
            if elapsed >= .90 and 'gideon' not in launched:
                _launch(rig, 'sanctuary_guard_gideon', ds[0], unreal.Vector(base.x+595., base.y+130., z),
                        unreal.Vector(-1., 0., 0.), kind='gideon')
                launched.add('gideon')
            if elapsed >= 1.35 and forward_result is None:
                blocked_shot = _shot(rig, 'sanctuary_guard_body')
                forward_result = {'blocked': guard.get_blocked_projectile_count(), 'counters': guard.get_counter_shot_count(),
                    'native_body_hit_count': blocked_shot['native_hit_count'], 'shooter_health': rig['health'](ds[0]),
                    'rear_health': rig['health'](ds[1])}
                rig['check'](forward_result['blocked'] == 2 and forward_result['counters'] == 2 and
                             forward_result['native_body_hit_count'] == 0 and abs(forward_result['shooter_health']-76.) < .01 and
                             abs(forward_result['rear_health']-100.) < .01,
                             'F intercepts both high-speed native classes before body impact and counters each shooter once for12')
                _launch(rig, 'sanctuary_friendly', rig['pawn'](), unreal.Vector(base.x+450., base.y+130., z),
                        unreal.Vector(-1., 0., 0.), speed=1200., damage=0.)
            for actor in unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'sanctuary_friendly'):
                friendly_crossed = friendly_crossed or actor.get_actor_location().x < base.x+65.
            if elapsed >= 2.0 and 'rear' not in launched:
                _launch(rig, 'sanctuary_rear', ds[0], unreal.Vector(base.x-600., base.y+130., z), unreal.Vector(1., 0., 0.))
                launched.add('rear')
            for moment in (.65, 1.08, 1.8):
                if elapsed >= moment and moment not in captured:
                    rig['capture']('F_counter_'+str(round(moment*100)))
                    captured.add(moment)
            yield 1./rig['FPS']
        rig['finish_video_clip']()
        rig['check'](friendly_crossed, 'an incoming own projectile passes through the active ward')
        rig['check'](abs(rig['health'](ds[1])-86.) < .01, 'rear-origin native attacks remain outside the frontal defense contract')
        rig['check'](not _effects(rig), 'F actor and short accents finish their own lifetime')
        rig['key']('SpaceBar')
        yield 1./rig['FPS']
        rig['check'](rig['skills']().get_active_skill_number() == 18, 'Space rolling keeps active number18 after F has finished')
        yield 1.1
        rig['recovered']()
        rows['F'] = {'unprotected_body': control_body, 'unprotected_dummy': control_dummy,
            'protected': forward_result, 'friendly_passed': friendly_crossed, 'rear_damage': 14.,
            'projectile_speed': 12000., 'fps': rig['FPS']}
        rows['clips'].append('F_native_counter_ward_video')

        # One ordered-collision regression: wall and guard are in the same
        # high-speed native Sweep; the nearer world impact must win.
        yield from _fresh(rig)
        ds = rig['layout']([(650, 130), (-250, 130), (750, -350)])
        rig['case']('F_wall_before_guard')
        base = rig['pawn']().get_actor_location()
        rig['use']('F', offset=(600, 0))
        yield .35
        guard = _effects(rig)[0]
        wall = rig['wall_fixture'](240)
        fixtures.append(wall)
        try:
            old_impacts = {row['name'] for row in _world_impacts(rig)}
            _launch(rig, 'sanctuary_wall_first', ds[0],
                    unreal.Vector(base.x+420., base.y, ds[0].get_actor_location().z),
                    unreal.Vector(-1., 0., 0.), speed=24000.)
            yield 1./rig['FPS']
            wall_shot = _shot(rig, 'sanctuary_wall_first')
            world_impacts = [row for row in _world_impacts(rig) if row['name'] not in old_impacts]
            wall_result = {'shot': wall_shot, 'blocked': guard.get_blocked_projectile_count(),
                'counters': guard.get_counter_shot_count(), 'native_world_impacts': world_impacts,
                'frame_distance': 24000./rig['FPS'], 'guard_entry_distance': 288., 'fps': rig['FPS']}
            rig['check'](not wall_shot['alive'] and wall_shot['native_hit_count'] == 0 and
                         100. < wall_shot['distance_travelled'] < 240. and world_impacts and
                         wall_result['blocked'] == 0 and wall_result['counters'] == 0,
                         'nearer wall keeps native world impact and stops the one-frame projectile before F can block or counter')
            rows['wall_before_guard'] = wall_result
        finally:
            wall.destroy_actor()
        yield from _fresh(rig)

        if not short:
            rig['cmd']('Sparrow.Skills.IgnoreCooldowns 1')
            yield from _fresh(rig)
            ds = rig['layout']([(430, 0), (650, 380), (650, -350)])
            # Preserve a genuine older status, including its own timer, through S.
            rig['cmd'](f'SparrowSanctuaryQA.Status {ds[0].get_name()} ROOT 8')
            rig['use']('S', ds[0])
            yield .50
            rig['check'](str(ds[0].get_combat_status()) == 'ROOT', 'S does not overwrite another existing ROOT status')
            rig['switch']('countess')
            yield .20
            rig['check'](str(ds[0].get_combat_status()) == 'ROOT', 'owner cleanup does not erase the unrelated ROOT status')
            ds[0].reset_dummy()
            yield from _fresh(rig)
            origin = rig['pawn']().get_actor_location()
            ground = rig['ground'](origin.x+430., origin.y)
            start_nav = _json(rig, 'new-skills-ground')
            rig['ground'](origin.x+550., origin.y)
            goal_nav = _json(rig, 'new-skills-ground')
            rig['check'](start_nav['navigation_projected'] and goal_nav['navigation_projected'],
                         'AI fixture start and short destination both project onto actual training-room navigation')
            start_point, goal_point = start_nav['nav'], goal_nav['nav']
            rig['cmd'](f'SparrowSanctuaryQA.Movement sanctuary_movement '
                       f'{start_point["x"]} {start_point["y"]} {start_point["z"]+90.} '
                       f'{goal_point["x"]} {goal_point["y"]} {goal_point["z"]}')
            movement_info = _json(rig, 'sanctuary_movement')
            probe = next(a for a in unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'sanctuary_movement'))
            # Keep this short valid path in progress across the binding checks.
            probe.get_editor_property('character_movement').set_editor_property('max_walk_speed', 20.)
            fixtures = list(unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'SparrowSanctuaryQAMovement'))
            # Only this QA case moves the normal dummy fixtures out of cursor selection.
            for index, dummy in enumerate(ds):
                dummy.set_actor_location(origin+unreal.Vector(4000., 4000.+index*200., 0.), False, True)
            yield .15
            rig['check'](movement_info['path_status'] == 3 and movement_info['tick_enabled'],
                         'real AI probe starts an active navigation request with movement ticking')
            rig['use']('S', probe)
            yield .5
            paused = _state(rig, 'sanctuary_AI_paused')['movement'][0]
            rig['check'](paused['mode'] == 1 and not paused['tick_enabled'] and paused['path_status'] == 2 and
                         paused['request_id'] == movement_info['request_id'],
                         'binding preserves walking mode and the same paused AI request while disabling movement tick')
            fixed = probe.get_actor_location()
            yield .5
            bound_delta = (probe.get_actor_location()-fixed).length()
            rig['check'](bound_delta < .1, 'bound AI character cannot continue moving')
            rig['use']('S', probe)
            yield .5
            rebound = _state(rig, 'sanctuary_AI_rebound')['movement'][0]
            rig['check'](not rebound['tick_enabled'] and rebound['path_status'] == 2 and
                         rebound['request_id'] == movement_info['request_id'],
                         'recasting binding replaces the previous lease without leaving an unlocked final state')
            yield 2.1
            restored = _state(rig, 'sanctuary_AI_restored')['movement'][0]
            rig['check'](restored['mode'] == 1 and restored['tick_enabled'] and restored['path_status'] == 3 and
                         restored['request_id'] == movement_info['request_id'],
                         'expiry restores movement tick and resumes the same AI navigation request')
            resumed_at = probe.get_actor_location()
            yield .15
            resumed_delta = (probe.get_actor_location()-resumed_at).length()
            rig['check'](resumed_delta > .1, 'the same resumed AI request actually moves the character again')
            rig['use']('S', probe)
            yield .3
            rig['cmd']('SparrowSanctuaryQA.Cancel')
            cancelled = _state(rig, 'sanctuary_AI_cancelled')['movement'][0]
            rig['check'](cancelled['tick_enabled'] and cancelled['path_status'] == 3 and
                         cancelled['request_id'] == movement_info['request_id'],
                         'cancelling a committed but still casting S immediately restores target movement')
            rig['use']('S', probe)
            yield .5
            rig['switch']('countess')
            yield .2
            cleaned = _state(rig, 'sanctuary_AI_owner_cleanup')['movement'][0]
            rig['check'](cleaned['tick_enabled'] and cleaned['path_status'] == 3 and
                         cleaned['request_id'] == movement_info['request_id'] and not _effects(rig),
                         'owner switching cleans the binding and restores the independent AI target')
            rows['movement'] = {'initial': movement_info, 'paused': paused, 'restored': restored,
                'bound_distance': bound_delta, 'resumed_distance': resumed_delta,
                'start_navigation': start_nav, 'goal_navigation': goal_nav,
                'recast_checked': True, 'cancel_and_owner_cleanup': True, 'previous_ROOT_preserved': True}
    finally:
        rig['finish_video_clip']()
        rig['switch']('countess')
        rig['cmd']('SparrowSanctuaryQA.Reset')
        for actor in fixtures:
            if _valid(actor):
                actor.destroy_actor()
        rig['cmd']('Sparrow.Skills.IgnoreCooldowns '+str(previous_cooldowns))
    yield .2
    rig['check'](not _effects(rig) and not unreal.GameplayStatics.get_all_actors_with_tag(rig['world'](), 'SparrowSanctuaryQAProjectile'),
                 'all sanctuary actors and live native probe projectiles are cleaned')
    (Path(rig['OUT'])/'sanctuary-native-review.json').write_text(json.dumps(
        {'passed': True, 'assets_saved': False, 'source': 'actual installed native skill inputs and actual projectile Sweep/damage',
         'visual_acceptance': 'pending parent actual viewport review', 'results': rows},
        ensure_ascii=False, indent=2), encoding='utf-8')
