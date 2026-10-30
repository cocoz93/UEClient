"""Import only the CC0 Quaternius Roll and its original mannequin into an owned folder."""
import json
from pathlib import Path
import struct


FOLDER = '/Game/TopDown/Characters/Sparrow/Mobility/Quaternius'
MESH = FOLDER + '/SK_QuaterniusRoll'
ANIMATION = FOLDER + '/AS_QuaterniusRoll'


def prepare(source):
    """Preserve original mesh/rig/Roll channels; discard unrelated animation buffers."""
    source = Path(source)
    data = source.read_bytes()
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4e4f534a
    doc = json.loads(data[20:20+size])
    bin_size, bin_kind = struct.unpack_from('<II', data, 20+size)
    assert bin_kind == 0x004e4942
    binary = data[28+size:28+size+bin_size]
    doc['animations'] = [a for a in doc['animations'] if a.get('name') == 'Roll']
    assert len(doc['animations']) == 1
    accessors = set()
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            accessors.update(primitive['attributes'].values())
            if 'indices' in primitive:
                accessors.add(primitive['indices'])
            for target in primitive.get('targets', []):
                accessors.update(target.values())
    for skin in doc['skins']:
        if 'inverseBindMatrices' in skin:
            accessors.add(skin['inverseBindMatrices'])
    for animation in doc['animations']:
        for sampler in animation['samplers']:
            accessors.update((sampler['input'], sampler['output']))
    mapping = {old:new for new,old in enumerate(sorted(accessors))}
    doc['accessors'] = [doc['accessors'][old] for old in sorted(accessors)]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            primitive['attributes'] = {k:mapping[v] for k,v in primitive['attributes'].items()}
            if 'indices' in primitive:
                primitive['indices'] = mapping[primitive['indices']]
            for target in primitive.get('targets', []):
                for key,value in target.items():
                    target[key] = mapping[value]
    for skin in doc['skins']:
        if 'inverseBindMatrices' in skin:
            skin['inverseBindMatrices'] = mapping[skin['inverseBindMatrices']]
    for animation in doc['animations']:
        for sampler in animation['samplers']:
            sampler['input'], sampler['output'] = mapping[sampler['input']], mapping[sampler['output']]
    view_refs = [(a,'bufferView') for a in doc['accessors'] if 'bufferView' in a]
    for accessor in doc['accessors']:
        if 'sparse' in accessor:
            view_refs += [(accessor['sparse'][key], 'bufferView') for key in ('indices','values')]
    view_refs += [(image,'bufferView') for image in doc.get('images',[]) if 'bufferView' in image]
    views = sorted({obj[key] for obj,key in view_refs})
    view_mapping, compact, new_views = {}, bytearray(), []
    for old in views:
        view = dict(doc['bufferViews'][old])
        assert view['buffer'] == 0
        offset, length = view.get('byteOffset',0), view['byteLength']
        compact.extend(b'\0' * (-len(compact)%4))
        view['byteOffset'] = len(compact)
        compact.extend(binary[offset:offset+length])
        view_mapping[old] = len(new_views)
        new_views.append(view)
    for obj,key in view_refs:
        obj[key] = view_mapping[obj[key]]
    compact.extend(b'\0' * (-len(compact)%4))
    doc['bufferViews'] = new_views
    doc['buffers'] = [{'byteLength':len(compact)}]
    encoded = json.dumps(doc,separators=(',',':')).encode('utf-8')
    encoded += b' ' * (-len(encoded)%4)
    result = struct.pack('<III',0x46546c67,2,28+len(encoded)+len(compact))
    result += struct.pack('<II',len(encoded),0x4e4f534a)+encoded
    result += struct.pack('<II',len(compact),0x004e4942)+compact
    target = source.with_name('Quaternius_Roll.glb')
    target.write_bytes(result)
    return {'source_bytes':len(data),'roll_only_bytes':len(result),'animations':['Roll'],
            'mesh_and_rig_preserved':True,'animation_samples_changed':False}


def author(output):
    import unreal
    output = Path(output)
    root = Path(unreal.Paths.project_dir()).resolve()
    source = root/'SourceAssets/Quaternius/Roll/Quaternius_Roll.glb'
    assert source.is_file()
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not unreal.load_asset(MESH):
        task = unreal.AssetImportTask()
        for key,value in {'filename':str(source),'destination_path':FOLDER,
                          'automated':True,'replace_existing':False,'save':True}.items():
            task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assets = [unreal.load_asset(p) for p in unreal.EditorAssetLibrary.list_assets(FOLDER,True,False)]
        meshes = [a for a in assets if isinstance(a,unreal.SkeletalMesh)]
        animations = [a for a in assets if isinstance(a,unreal.AnimSequence)]
        assert len(meshes) == len(animations) == 1, [(a.get_path_name(),a.get_class().get_name()) for a in assets if a]
        for asset,target in ((meshes[0],MESH),(animations[0],ANIMATION)):
            if asset.get_path_name().split('.')[0] != target:
                assert unreal.EditorAssetLibrary.rename_asset(asset.get_path_name(),target)
    mesh,animation = unreal.load_asset(MESH),unreal.load_asset(ANIMATION)
    assert isinstance(mesh,unreal.SkeletalMesh) and isinstance(animation,unreal.AnimSequence)
    assert mesh.get_editor_property('skeleton') == animation.get_editor_property('skeleton')
    animation.set_editor_property('enable_root_motion',False)
    assert unreal.EditorAssetLibrary.save_loaded_asset(animation,False)
    result = {'passed':True,'mesh':MESH,'animation':ANIMATION,'seconds':animation.get_play_length(),
              'skeleton':animation.get_editor_property('skeleton').get_path_name(),
              'root_motion_enabled':False,'license':'CC0 1.0','original_matching_rig':True,
              'retargeted':False,'source':'https://quaternius.itch.io/universal-animation-library',
              'assets':[str(p) for p in unreal.EditorAssetLibrary.list_assets(FOLDER,True,False)]}
    (output/'quaternius-roll-import.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(prepare(sys.argv[1])))
