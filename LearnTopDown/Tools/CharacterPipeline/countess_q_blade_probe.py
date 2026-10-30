import json, os, traceback
from pathlib import Path
import unreal
if os.environ.get('COUNTESS_SKILL_CANDIDATES') == '1':
    out=Path(os.environ['SPARROW_QA_OUTPUT'])
    report={'passed':False,'clips':[]}
    try:
        base='/Game/ParagonCountess/Characters/Heroes/Countess/'
        mesh=unreal.load_asset(base+'Meshes/SM_Countess')
        options=unreal.AnimPoseEvaluationOptions()
        options.set_editor_property('optional_skeletal_mesh',mesh)
        options.set_editor_property('evaluation_type',unreal.AnimDataEvalType.RAW)
        for name in ('Ability_Ultimate','Ability_Ultimate_InMotion','Primary_Attack_Fast_V1','Primary_Attack_A_Fast_V1','Primary_Attack_B_Fast_InMotion','Attack_Melee_Air','Cast'):
            animation=unreal.load_asset(base+'Animations/'+name)
            assert animation is not None, name
            row={'name':name,'path':animation.get_path_name(),'length':animation.get_play_length(),
                 'skeleton_matches':animation.get_editor_property('skeleton')==mesh.get_editor_property('skeleton'),
                 'additive':str(animation.get_editor_property('additive_anim_type')),'samples':[]}
            for i in range(int(row['length']/.05)+1):
                at=min(i*.05,row['length']-.00001)
                pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,at,options)
                sample={'time':at,'bones':{},'sockets':{}}
                for bone in ('root','pelvis','head','hand_l','hand_r','foot_l','foot_r'):
                    v=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD).translation
                    sample['bones'][bone]=[v.x,v.y,v.z]
                for side in ('L','R'):
                    for part in ('Base','Tip'):
                        socket=f'FX_Weapon{part}_{side}'
                        v=unreal.AnimPoseExtensions.get_socket_pose(pose,socket,unreal.AnimPoseSpaces.WORLD).translation
                        sample['sockets'][socket]=[v.x,v.y,v.z]
                row['samples'].append(sample)
            report['clips'].append(row)
        report['passed']=True
    except Exception: report['error']=traceback.format_exc()
    (out/'skill-candidates.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
else:
    out=Path(os.environ['SPARROW_QA_OUTPUT'])
    r={'passed':False}
    try:
        mesh=unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Meshes/SM_Countess')
        anim=unreal.load_asset('/Game/ParagonCountess/Characters/Heroes/Countess/Animations/Ability_Q')
        options=unreal.AnimPoseEvaluationOptions()
        options.set_editor_property('optional_skeletal_mesh',mesh)
        options.set_editor_property('evaluation_type',unreal.AnimDataEvalType.RAW)
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(anim,0,options)
        r['api']={k:str(getattr(unreal.AnimPoseExtensions,k).__doc__) for k in dir(unreal.AnimPoseExtensions) if 'socket' in k or 'bone_names' in k}
        bones=unreal.AnimPoseExtensions.get_bone_names(pose)
        r['bones']=[str(b) for b in bones]
        names=[b for b in bones if any(v in str(b).lower() for v in ('weapon','hand','blade'))]
        r['sockets']=[str(n) for n in unreal.AnimPoseExtensions.get_socket_names(pose)]
        r['length']=anim.get_play_length()
        r['samples']=[]
        for i in range(61):
            t=i/120
            pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(anim,t,options)
            row={'time':t,'bones':{}}
            for b in names:
                v=unreal.AnimPoseExtensions.get_bone_pose(pose,b,unreal.AnimPoseSpaces.WORLD).translation
                row['bones'][str(b)]=[v.x,v.y,v.z]
            row['sockets']={}
            for side in ('L','R'):
                for part in ('Base','Tip'):
                    n=f'FX_Weapon{part}_{side}'
                    v=unreal.AnimPoseExtensions.get_socket_pose(pose,n,unreal.AnimPoseSpaces.WORLD).translation
                    row['sockets'][n]=[v.x,v.y,v.z]
            r['samples'].append(row)
        r['passed']=True
    except Exception:r['error']=traceback.format_exc()
    (out/'pose.json').write_text(json.dumps(r,indent=2))
    unreal.SystemLibrary.quit_editor()
