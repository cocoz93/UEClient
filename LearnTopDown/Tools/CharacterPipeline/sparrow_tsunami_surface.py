"""Author A's gold/platinum wave surface; native geometry stays read-only.

Only M_SparrowTsunamiWave is saved. The native ASparrowGearArrow bends the
existing subdivided blade mesh into three open, axially staggered crescents.
author(out) is called by the parent before its single editor/PIE integration.
"""
import hashlib
import json
from pathlib import Path

import unreal


ROOT = '/Game/TopDown/Characters/Sparrow/Materials'
TARGET = ROOT+'/M_SparrowTsunamiWave'
FLOW = '/Game/ParagonSparrow/FX/Textures/FluidPatterns/T_InkSmoky_M'
MESH = '/Game/TopDown/Characters/Countess/FX/SM_CountessRuinClawBlade'
VERSION = '2'

_SURFACE = '''
float u = saturate(UV.x);
float v = frac(UV.y);
float envelope = max(Envelope,0.0);
float grain = saturate(Flow.r*.68+Flow.g*.32);
// The original eight-sided tapered mesh has cutting edges at v=.25/.75.
// Those thin white-gold edges stay distinct from the denser gold face.
float cuttingEdge = pow(abs(sin(v*6.2831853)),10.0);
float crest = pow(saturate(.5+.5*sin(u*37.0-Clock*8.5+grain*4.0+Seed)),5.0);
float stream = smoothstep(.17,.65,grain);
float lengthFade = pow(saturate(sin(u*3.14159265)),.28);
float3 body = lerp(float3(1.35,.47,.025),float3(3.55,1.90,.28),stream);
body += float3(.80,.55,.13)*crest*.36;
float3 edge = float3(3.75,3.20,1.72)*cuttingEdge*(.72+.28*grain);
float3 color = (body+edge*lerp(.60,.16,saturate(Wake)))*envelope;
// Low-amplitude texture erosion gives flowing energy rather than solid metal.
// A nonzero interior keeps each open crescent legible throughout its rotation.
float alpha = lengthFade*(.76+.18*stream+.04*cuttingEdge)*saturate(envelope)*lerp(1.0,.68,saturate(Wake));
return float4(color,alpha);
'''


def _hash_sources():
    content = Path(unreal.Paths.project_content_dir()).resolve()
    sources = (FLOW, MESH, ROOT+'/M_SparrowGearFeather', ROOT+'/M_SparrowAscensionGold')
    return {asset: hashlib.sha256((content/(asset.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
            for asset in sources}


def author(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    before = _hash_sources()
    texture, mesh = unreal.load_asset(FLOW), unreal.load_asset(MESH)
    assert isinstance(texture, unreal.Texture2D), FLOW
    assert isinstance(mesh, unreal.StaticMesh) and mesh.get_num_triangles(0) >= 480, MESH
    material = unreal.load_asset(TARGET)
    reused = material is not None and unreal.EditorAssetLibrary.get_metadata_tag(material, 'SparrowTsunamiVersion') == VERSION
    lib = unreal.MaterialEditingLibrary
    if not reused:
        if material is None:
            material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                TARGET.rsplit('/',1)[1], ROOT, unreal.Material, unreal.MaterialFactoryNew())
        assert isinstance(material, unreal.Material), TARGET
        lib.delete_all_material_expressions(material)
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        material.set_editor_property('two_sided', True)
        material.set_editor_property('used_with_spline_meshes', True)

        def node(kind, **values):
            item = lib.create_material_expression(material, getattr(unreal, 'MaterialExpression'+kind))
            for key, value in values.items():
                item.set_editor_property(key, value)
            return item

        def wire(source, target, pin, channel=''):
            assert lib.connect_material_expressions(source, channel, target, pin), pin

        def custom(code, kind, inputs):
            item = node('Custom', code=code, output_type=kind)
            pins = []
            for name, source in inputs:
                pin = unreal.CustomInput()
                pin.set_editor_property('input_name', name)
                pins.append(pin)
            item.set_editor_property('inputs', pins)
            for name, source in inputs:
                wire(source, item, name)
            return item

        uv = node('TextureCoordinate')
        clock = node('Time')
        seed = node('ScalarParameter', parameter_name='WaveSeed', default_value=0.)
        strength = node('ScalarParameter', parameter_name='Envelope', default_value=1.)
        wake = node('ScalarParameter', parameter_name='WaveWake', default_value=0.)
        flow_uv = custom('return float2(UV.x*3.2-Clock*.82+Seed*.13,UV.y*1.8+Clock*.045);',
                         unreal.CustomMaterialOutputType.CMOT_FLOAT2,
                         (('UV',uv),('Clock',clock),('Seed',seed)))
        sample = node('TextureSample', texture=texture)
        wire(flow_uv, sample, 'UVs')
        surface = custom(_SURFACE, unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                         (('UV',uv),('Clock',clock),('Seed',seed),('Envelope',strength),('Flow',sample),('Wake',wake)))
        for prop, channels in ((unreal.MaterialProperty.MP_EMISSIVE_COLOR,(True,True,True,False)),
                               (unreal.MaterialProperty.MP_OPACITY,(False,False,False,True))):
            mask = node('ComponentMask')
            for key, value in zip(('r','g','b','a'),channels):
                mask.set_editor_property(key,value)
            wire(surface, mask, '')
            assert lib.connect_material_property(mask, '', prop)
        errors = [str(error) for error in (lib.recompile_material(material) or [])]
        assert not errors, errors
        unreal.EditorAssetLibrary.set_metadata_tag(material,'SparrowTsunamiVersion',VERSION)
        assert unreal.EditorAssetLibrary.save_loaded_asset(material,False), TARGET
    assert material.get_editor_property('used_with_spline_meshes'), 'spline usage required before native rendering'
    after = _hash_sources()
    assert before == after, 'A source material/texture/shared mesh changed'
    result = {'passed':True,'version':VERSION,'asset':TARGET,'reused':reused,
              'saved_scope':[TARGET],'source_hashes_unchanged':True,'source_hashes':after,
              'geometry':{'mesh':MESH,'triangles':mesh.get_num_triangles(0),'source_mesh_read_only':True,
                          'runtime_blades':3,'interior_wakes':3,'axial_spacing_cm':22.,'largest_height_cm':230.},
              'gameplay':'native A speed160cm/s, damage90, range1800cm and hit path unchanged',
              'visual_acceptance':'pending actual PIE quarter-view review'}
    (out/'A-tsunami-surface-author.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
