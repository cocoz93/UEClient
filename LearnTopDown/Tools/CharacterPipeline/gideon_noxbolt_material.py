"""F 녹스 번개용 빛 재질(10-19). /Game/TopDown/Characters/Gideon/FX/M_NoxBolt 를 새로 만든다.
가산 섞기·빛만(그늘 없음)·양면, 발광 = Color(벡터) × Intensity(스칼라). 인스턴스 메시(줄 조각·불티)에 쓰므로
used_with_instanced_static_meshes 를 켠다. 녹스 클라는 번개를 화면에 선으로 긋고 그 아래 반투명 띠(빛무리)를 깐다
(third_party/opennox-src/src/legacy/client__draw__lightning.c) — 여기선 같은 색 원통을 굵기만 달리해 겹친다."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
PATH = '/Game/TopDown/Characters/Gideon/FX/M_NoxBolt'
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {}
try:
    if assets.does_asset_exist(PATH):
        assets.delete_asset(PATH)
    folder, name = PATH.rsplit('/', 1)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('used_with_instanced_static_meshes', True)
    color = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -500, 0)
    color.set_editor_property('parameter_name', 'Color')
    color.set_editor_property('default_value', unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    intensity = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 200)
    intensity.set_editor_property('parameter_name', 'Intensity')
    intensity.set_editor_property('default_value', 1.0)
    multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -250, 100)
    assert lib.connect_material_expressions(color, '', multiply, 'A')
    assert lib.connect_material_expressions(intensity, '', multiply, 'B')
    assert lib.connect_material_property(multiply, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    report['saved'] = assets.save_asset(PATH, only_if_is_dirty=False)
    report['scalars'] = [str(n) for n in lib.get_scalar_parameter_names(material)]
    report['vectors'] = [str(n) for n in lib.get_vector_parameter_names(material)]
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
(out / 'noxbolt-material.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
