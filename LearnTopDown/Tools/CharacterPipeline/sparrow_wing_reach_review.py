"""Read native Serath wing reach in the actual V unfold/idle pose.

No asset or pose edits. Run first in the parent-owned PIE integration session.
"""
import json
import unreal


def sequence(rig):
    now = lambda: unreal.GameplayStatics.get_time_seconds(rig['world']())
    xyz = lambda v: [round(v.x, 5), round(v.y, 5), round(v.z, 5)]
    report = {'passed': False, 'purpose': 'measure native wing reach axes before length-only adjustment', 'samples': []}
    rig['switch']('countess'); yield .2
    rig['switch']('sparrow'); yield .7
    rig['cmd']('CountessComboQA.FlushInput')
    rig['case']('WingReach')
    rig['layout']([(850, 0), (1000, 400), (1000, -400)])
    yield .2
    started = now()
    rig['use']('V', offset=(950, 0))
    moments = [.8, 1.2, 1.7, 2.3]
    while moments:
        if now()-started >= moments[0]:
            stamp = moments.pop(0)
            forms = [a for a in unreal.GameplayStatics.get_all_actors_of_class(rig['world'](), unreal.SparrowAscensionWings)
                     if unreal.SystemLibrary.is_valid(a)]
            rig['check'](len(forms) == 1, 'wing reach measurement has one native V form')
            wing = next(c for c in forms[0].get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'SerathWings')
            bone_names = [str(wing.get_bone_name(i)) for i in range(wing.get_num_bones())]
            selected = ['spine_03']+[b for b in bone_names if 'wing' in b]
            local = {name: xyz(wing.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT).translation)
                     for name in selected}
            world = {name: xyz(wing.get_socket_location(name)) for name in selected}
            row = {'time': now()-started, 'component_bones': local, 'world_bones': world,
                   'relative_scale': xyz(wing.get_editor_property('relative_scale3d')),
                   'relative_rotation': str(wing.get_editor_property('relative_rotation')),
                   'relative_location': xyz(wing.get_editor_property('relative_location')),
                   'player_right': xyz(rig['pawn']().get_actor_right_vector()),
                   'player_forward': xyz(rig['pawn']().get_actor_forward_vector())}
            report['samples'].append(row)
            rig['capture']('WingReach_'+str(round(stamp*100)))
            (rig['OUT']/'wing-reach-measurement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        yield 1./rig['FPS']
    rig['recovered']()
    report['passed'] = True
    (rig['OUT']/'wing-reach-measurement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    rig['switch']('countess'); yield .2
