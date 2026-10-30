import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/QA/TrialTower/session-20261029'
paths = [
 '/Game/ParagonProps/Monolith/Ruins/Meshes/' + name for name in
 ['JungleWall_01A', 'JungleArch_01A', 'JunglePillarBlock_01A', 'JungleStairs_Strait01', 'Ruins_DecoFloor', 'Ruins_WhiteBuffFloor', 'MonoStatue']
] + ['/Game/ParagonProps/Agora/Props/Meshes/' + name for name in ['TerminusGateway','Terminus_Pillar_D','Base_Core_Stairs']]
rows = []
for path in paths:
    asset = unreal.load_asset(path)
    row = {'path': path, 'exists': bool(asset)}
    if isinstance(asset, unreal.StaticMesh):
        bbox = asset.get_bounding_box()
        row.update(min=[bbox.min.x,bbox.min.y,bbox.min.z], max=[bbox.max.x,bbox.max.y,bbox.max.z],
                   materials=[str(s.material_interface.get_path_name()) if s.material_interface else None for s in asset.get_editor_property('static_materials')])
    rows.append(row)
gm = unreal.load_asset('/Game/TopDown/Blueprints/BP_CountessGameMode')
cdo = unreal.get_default_object(gm.generated_class())
rows.append({'game_mode': gm.get_path_name(), 'controller': cdo.get_editor_property('player_controller_class').get_path_name(), 'pawn': cdo.get_editor_property('default_pawn_class').get_path_name()})
(OUT / 'inspection.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
RESULT = rows
