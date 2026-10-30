"""Private Gideon/Dekker asset copies (10-18 requests). Saves assets under /Game/TopDown/Characters/Gideon/FX/.
1) W rune materials: copy each and multiply its opacity and emissive by a new scalar parameter `Opacity` (default 1),
   so the floor circle can be drawn fainter (the originals have no opacity parameter), and multiply emissive by a new vector
   parameter `Tint` (default white) so W can be purple and R white (10-18).
   FADE_ONLY_MATERIALS=1 skips part 2 (the cage copies stay as they are).
2) R cage: copy SM_DekkerUltPanels_Cage, raise the glass panels' top band (group 0, z >= 300) by CAGE_PANEL_RAISE so it
   meets the spear tips (spears top 424, panels top 360 in mesh space), then copy the three cage particle systems and point
   their mesh modules at the copy."""
import json
import os
from pathlib import Path
import traceback

import unreal

out = Path(os.environ['SPARROW_QA_OUTPUT'])
DEST = '/Game/TopDown/Characters/Gideon/FX/'
MATERIALS = ['/Game/ParagonGideon/FX/Materials/Heroes/Gideon/' + n for n in
             ('M_Star_Runes_Ring_VertColorFade', 'M_Star_Runes_Ring', 'M_Star_Runes_Big', 'M_Floor_Burst', 'M_Star_Runes_Ring_Ult')]
CAGE_MESH = '/Game/ParagonDekker/FX/Meshes/Hero_Specific/SM_DekkerUltPanels_Cage'
CAGE_SYSTEMS = ['/Game/ParagonDekker/FX/Particles/Abilities/Cage/FX/' + n for n in
                ('P_Dekker_Cage', 'P_Dekker_Cage_Startup', 'P_Dekker_Cage_End')]
RAISE = float(os.environ.get('CAGE_PANEL_RAISE', '50'))
lib = unreal.MaterialEditingLibrary
assets = unreal.EditorAssetLibrary
report = {'materials': [], 'cage': {}}


def fresh_copy(source, name):
    path = DEST + name
    if assets.does_asset_exist(path):
        assets.delete_asset(path)
    return assets.duplicate_asset(source, path), path


def add_opacity_parameter(material):
    parameter = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -600, 0)
    parameter.set_editor_property('parameter_name', 'Opacity')
    parameter.set_editor_property('default_value', 1.0)
    wired = []
    for prop in (unreal.MaterialProperty.MP_OPACITY, unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        node = lib.get_material_property_input_node(material, prop)
        if node is None:
            continue
        output = lib.get_material_property_input_node_output_name(material, prop)
        multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -300, 0)
        assert lib.connect_material_expressions(node, output, multiply, 'A')
        assert lib.connect_material_expressions(parameter, '', multiply, 'B')
        assert lib.connect_material_property(multiply, '', prop)
        wired.append(str(prop))
    # 색: 발광에만 곱한다(위에서 Opacity를 곱한 발광 입력 뒤에 한 번 더).
    tint = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -600, 200)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    node = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if node is not None:
        output = lib.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, -150, 200)
        assert lib.connect_material_expressions(node, output, multiply, 'A')
        assert lib.connect_material_expressions(tint, '', multiply, 'B')
        assert lib.connect_material_property(multiply, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        wired.append('tint')
    lib.recompile_material(material)
    return wired


try:
    for source in MATERIALS:
        name = source.rsplit('/', 1)[-1] + '_Fade'
        material, path = fresh_copy(source, name)
        wired = add_opacity_parameter(material)
        saved = assets.save_asset(path, only_if_is_dirty=False)
        report['materials'].append({'copy': path, 'wired': wired, 'scalars': [str(n) for n in lib.get_scalar_parameter_names(material)],
                                    'saved': saved})

    if os.environ.get('FADE_ONLY_MATERIALS') == '1':
        report['passed'] = True
        raise StopIteration
    mesh, mesh_path = fresh_copy(CAGE_MESH, 'SM_DekkerUltPanels_Cage_Even')
    description = mesh.get_static_mesh_description(0)
    moved = set()
    for polygon in description.get_polygon_group_polygons(unreal.PolygonGroupID(0)):
        for vertex in description.get_polygon_vertices(polygon):
            key = vertex.get_editor_property('id_value')
            if key in moved:
                continue
            position = description.get_vertex_position(vertex)
            if position.z >= 300.0:
                description.set_vertex_position(vertex, unreal.Vector(position.x, position.y, position.z + RAISE))
                moved.add(key)
    mesh.build_from_static_mesh_descriptions([description])
    report['cage']['mesh'] = {'copy': mesh_path, 'raised_vertices': len(moved), 'raise': RAISE,
                              'bounds': str(mesh.get_bounds().box_extent), 'saved': assets.save_asset(mesh_path, only_if_is_dirty=False)}
    report['cage']['systems'] = []
    original = unreal.load_asset(CAGE_MESH)
    for source in CAGE_SYSTEMS:
        system, path = fresh_copy(source, source.rsplit('/', 1)[-1] + '_Even')
        prefix = system.get_path_name() + ':'
        swapped = 0
        for obj in unreal.ObjectIterator(unreal.Object):
            if not unreal.SystemLibrary.get_path_name(obj).startswith(prefix):
                continue
            try:
                if obj.get_editor_property('mesh') == original:
                    obj.set_editor_property('mesh', mesh)
                    swapped += 1
            except Exception:
                pass
        report['cage']['systems'].append({'copy': path, 'mesh_modules_swapped': swapped,
                                          'saved': assets.save_asset(path, only_if_is_dirty=False)})
    report['passed'] = True
except StopIteration:
    pass
except Exception:
    report['error'] = traceback.format_exc()
(out / 'fade-assets.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
unreal.SystemLibrary.quit_editor()
