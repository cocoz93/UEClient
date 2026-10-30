"""Small read-only shape audit requested for the F redesign."""
import json
from pathlib import Path
import unreal

def author(out):
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    names={'SM_Plasma_Mesh_Reduced','SM_Sparrow_Bow_Flames','SM_Sparrow_Arrow','SM_ShockwaveFlame'}
    rows=[]
    for data in registry.get_assets_by_path('/Game/ParagonSparrow/FX',recursive=True):
        if str(data.asset_name) not in names:continue
        mesh=data.get_asset()
        bounds=mesh.get_bounds()
        rows.append({'name':str(data.asset_name),'path':mesh.get_path_name(),
                     'origin':str(bounds.origin),'extent':str(bounds.box_extent),
                     'materials':[str(x.material_interface.get_path_name()) if x.material_interface else None for x in mesh.static_materials]})
        if str(data.asset_name)=='SM_ShockwaveFlame':
            vertices,indices,normals,uvs,tangents=unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)
            section={'mesh':mesh.get_path_name(),'section':0,'vertices':len(vertices),
                     'triangles':len(indices)//3,'indices':list(indices),
                     'points':[[v.x,v.y,v.z,uv.x,uv.y] for v,uv in zip(vertices,uvs)],
                     'normals':[[v.x,v.y,v.z] for v in normals]}
            (Path(out)/'f-shockwave-section.json').write_text(json.dumps(section,indent=2),encoding='utf-8')
    texture=unreal.load_asset('/Game/ParagonSparrow/FX/Textures/Tile/Noise/T_PerlinPlasma_Noisey_Packed')
    export=unreal.AssetExportTask()
    export.object=texture
    export.filename=str(Path(out)/'F-plasma-channels.png')
    export.automated=True
    export.prompt=False
    export.replace_identical=True
    export.exporter=unreal.TextureExporterPNG()
    texture_result={'exported':unreal.Exporter.run_asset_export_task(export),
                    'srgb':texture.get_editor_property('srgb'),
                    'compression':str(texture.get_editor_property('compression_settings'))}
    result={'passed':bool(rows),'assets':rows,'texture':texture_result}
    (Path(out)/'f-mesh-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
