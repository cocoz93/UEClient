"""Room-owned 2K environment textures; never edit imported source textures or hero quality."""
import unreal

DEST = '/Game/TopDown/TrainingRoom'
SOURCE = '/Game/MedievalDungeon/'
textures = {}
materials = {}
changes = []


def budget_texture(source):
    if not source or not source.get_path_name().startswith(SOURCE):
        return source
    key = source.get_path_name()
    if key in textures:
        return textures[key]
    size = [source.blueprint_get_size_x(), source.blueprint_get_size_y()]
    if max(size) <= 2048:
        textures[key] = source
        return source
    path = DEST + '/Textures/T_Room_' + source.get_name().removeprefix('T_')
    texture = unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset(key, path)
    if not texture:
        raise RuntimeError('Could not create room texture copy: ' + key)
    texture.set_editor_property('max_texture_size', 2048)
    if not unreal.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('Could not save room texture copy: ' + path)
    textures[key] = texture
    changes.append({'source': key, 'copy': path, 'source_size': size, 'maximum_size': 2048})
    return texture


def budget_material(source):
    if not source or not source.get_path_name().startswith(SOURCE):
        return source
    key = source.get_path_name()
    if key in materials:
        return materials[key]
    lib = unreal.MaterialEditingLibrary
    if isinstance(source, unreal.Material):
        path = DEST + '/Materials/M_Room_' + source.get_name()
        material = unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset(key, path)
        for expression in lib.get_material_expressions(material):
            if isinstance(expression, (unreal.MaterialExpressionTextureSample, unreal.MaterialExpressionTextureObject)):
                texture = expression.get_editor_property('texture')
                if texture:
                    expression.set_editor_property('texture', budget_texture(texture))
        lib.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material, False)
        materials[key] = material
        return material
    names = lib.get_texture_parameter_names(source)
    getter = (lib.get_material_instance_texture_parameter_value if isinstance(source, unreal.MaterialInstanceConstant)
              else lib.get_material_default_texture_parameter_value)
    replacements = {name: budget_texture(getter(source, name)) for name in names}
    path = DEST + '/Materials/MI_Room_' + source.get_name()
    material = unreal.load_asset(path)
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/', 1)[1],
            DEST + '/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(material, source)
    for name, texture in replacements.items():
        if texture:
            lib.set_material_instance_texture_parameter_value(material, name, texture)
    lib.update_material_instance(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, False)
    materials[key] = material
    return material
