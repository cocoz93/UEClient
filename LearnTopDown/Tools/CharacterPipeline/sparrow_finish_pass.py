"""Scoped Q/W/R release review using the existing real-input PIE harness."""
import json
import os
import unreal


def _record(rig, name):
    if os.environ.get('NEW_SKILLS_VIDEO') == '1':
        rig['STATE']['video_clip'] = {
            'case': name, 'prefix': name + '_video',
            'cast_time': unreal.GameplayStatics.get_time_seconds(rig['world']()),
            'frame_times': []}


def sequence(rig):
    rig['switch']('sparrow')
    yield .8
    for letter, moments, duration in (
            ('Q', (.28, .40, .58), 1.9),
            ('W', (.68, .86, .98), 1.65),
            ('R', (.16, .32, .61), 1.3)):
        if letter not in os.environ.get('SPARROW_RELEASE_OPTIONS', 'QWR'):
            continue
        rig['case'](letter + '_release_finish')
        ds = rig['layout']([(650, 0), (250, 650), (250, -650)])
        yield .2
        rig['use'](letter, ds[0])
        _record(rig, letter + '_release_finish')
        elapsed = 0.
        if letter == 'W':
            pending = list(enumerate(moments))
            saw_arrow, saw_impact = False, False
            def impacts():
                return [p for p in unreal.ObjectIterator(unreal.ParticleSystemComponent)
                        if isinstance(p,unreal.ParticleSystemComponent) and unreal.SystemLibrary.is_valid(p)
                        and unreal.Name('SparrowPiercingImpact') in p.get_editor_property('component_tags')]
            while elapsed < duration:
                yield 1 / rig['FPS']
                elapsed += 1 / rig['FPS']
                arrows = unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowArrow)
                for arrow in arrows:
                    if saw_arrow or arrow.get_owner() != rig['pawn']() or not arrow.actor_has_tag('SparrowChargedArrow'):
                        continue
                    saw_arrow = True
                    names = {str(n) for n in arrow.get_target_impact_emitter_names()}
                    rig['check'](names == {'Main Flames','Wisps','Flare','Sparks','SparkTrailHeads','Line Burst'},
                                 'W uses its dedicated six-layer impact clone')
                    meshes = arrow.get_components_by_class(unreal.StaticMeshComponent)
                    shaft = next(p for p in meshes if p.get_name() == 'ArrowMesh')
                    width = shaft.get_editor_property('relative_scale3d')
                    rig['check'](abs(width.x - 1.1) < .001 and abs(width.y - 1.1) < .001 and abs(width.z - 1.0) < .001,
                                 'W shaft is55percent of former width with its length unchanged')
                    aura = next(p for p in arrow.get_components_by_class(unreal.ParticleSystemComponent)
                                if 'SparrowChargedArrowAura' in {str(t) for t in p.component_tags})
                    aura_scale = aura.get_editor_property('relative_scale3d')
                    rig['check'](abs(aura_scale.x - 1.5) < .001 and abs(aura_scale.y - .46) < .001,
                                 'W flying aura is thinner while the six-layer impact stays unchanged')
                    break
                saw_impact = saw_impact or bool(impacts())
                if pending and elapsed >= pending[0][1]:
                    rig['capture'](letter + '_release_' + str(pending.pop(0)[0]))
            rig['check'](saw_arrow, 'W actual charged projectile was observed')
            rig['check'](saw_impact and not impacts(), 'W dedicated impact plays and clears within the short review')
        else:
            for index, moment in enumerate(moments):
                yield moment - elapsed
                elapsed = moment
                rig['capture'](letter + '_release_' + str(index))
            yield duration - elapsed
        rig['finish_video_clip']()
        rig['recovered']()
        if letter == 'Q':
            yield 3.0
            rig['check'](abs(rig['health'](ds[0]) - 60.) < .02, 'Q still deals40damage without more falling arrows')
        elif letter == 'W':
            rig['check'](abs(rig['health'](ds[0]) - 65.) < .02, 'W retains exactly35damage from one piercing hit')
        else:
            rig['check'](abs(rig['health'](ds[0]) - 40.) < .02, 'R186arrows retain60damage per target')
        rig['check'](abs(rig['health'](ds[1]) - 100.) < .02, letter + ' excludes the far side fixture')
    # Switching must clear both short release particles and the persistent bow effect.
    rig['switch']('countess')
    yield .5
    rig['check'](not unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowShotWave),
                 'release wave is removed on owner switch')
    (rig['OUT'] / 'sparrow-release-review.json').write_text(json.dumps({
        'passed': True, 'scope': 'Q/W/R release visuals and unchanged target damage',
        'user_aesthetic_acceptance': 'pending'}, indent=2), encoding='utf-8')
