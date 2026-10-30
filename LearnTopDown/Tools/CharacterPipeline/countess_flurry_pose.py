"""Read original blade and body poses for the six-cut prototype; never save source assets."""
import unreal,json,os
from pathlib import Path
out=Path(os.environ['SPARROW_QA_OUTPUT']);folder='/Game/ParagonCountess/Characters/Heroes/Countess'
options=unreal.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=unreal.load_asset(folder+'/Meshes/SM_Countess');options.evaluation_type=unreal.AnimDataEvalType.RAW
rows=[]
for name in ('Primary_Attack_Fast_V1','Primary_Attack_A_Fast_V1','Primary_Attack_B_Fast_InMotion','Primary_Attack_Fast_InMotion'):
 animation=unreal.load_asset(folder+'/Animations/'+name);samples=[]
 for frame in range(int(animation.get_play_length()*30)):
  t=frame/30;pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(animation,t,options);bones={}
  for bone in ('root','pelvis','hand_l','hand_r','foot_l','foot_r','weapon_l','weapon_r'):
   v=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD).translation;bones[bone]=[v.x,v.y,v.z]
  samples.append({'time':t,'bones':bones})
 rows.append({'clip':name,'length':animation.get_play_length(),'samples':samples})
(out/'flurry-source-poses.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
unreal.SystemLibrary.quit_editor()
