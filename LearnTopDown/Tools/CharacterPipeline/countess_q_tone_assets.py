"""Create a color-only, A/B-capable muted Q material; never save an existing asset."""
import ast
import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(unreal.Paths.project_dir()).resolve()
CONTENT = Path(unreal.Paths.project_content_dir()).resolve()
SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut'
TARGET = '/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted'
OWNED = CONTENT/'TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted.uasset'
MESH = CONTENT/'TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.uasset'

# RGB inputs only. Original alpha, reveal, noise, lifetime, mesh and UV logic remain exact.
COLORS = (
    ('fleck_red', (1.9, .018, .035), (.65, .002, .016), 'float3(1.9, 0.018, 0.035)'),
    ('blade_body', (1.8, .012, .028), (.65, .0018, .014), 'float3(1.8, 0.012, 0.028)'),
    ('blade_core', (15, 7.4, 5.2), (1.2, .012, .035), 'float3(15, 7.4, 5.2)'),
    ('blade_filament', (4.5, .05, .10), (1, .004, .022), 'float3(4.5, 0.05, 0.10)'),
    ('rush_body', (5, .014, .04), (.8, .002, .018), 'float3(5, 0.014, 0.04)'),
    ('rush_core', (15, 7, 5), (1.25, .01, .03), 'float3(15, 7, 5)'),
    ('impact_rays', (6, .02, .06), (.95, .0025, .022), 'float3(6, 0.02, 0.06)'),
    ('impact_core', (18, 8, 5), (1.8, .018, .045), 'float3(18, 8, 5)'),
)
REFERENCES = (
    '/Game/ParagonCountess/FX/Materials/Trails/M_MeshSwipe_FinalDarkInst',
    '/Game/ParagonCountess/FX/Materials/Trails/m_CountessBlinkRibbon',
    '/Game/ParagonCountess/FX/Materials/Smoke/WispySmokeSoft/M_Turbulent_SmokeSubUV_RandomColorVaration_VampInst',
    '/Game/ParagonCountess/FX/Materials/Flares/M_Countess_ImpactFlare',
)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def protected():
    files = [ROOT/'LearnTopDown.uproject']
    for directory in ('Content','Config'):
        files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and p != OWNED]
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}


def source_shader():
    # Parse the literal without importing its authoring script (which would mutate old assets).
    script = ROOT/'Tools/CharacterPipeline/countess_q_outward_assets.py'
    tree = ast.parse(script.read_text(encoding='utf-8-sig'))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id == 'SHADER' for t in n.targets)]
    if len(values) != 1:
        raise RuntimeError('Expected one reviewed outward shader literal')
    return values[0], {'path':str(script),'sha256':sha(script)}


def reference_parameters():
    result = []
    for path in REFERENCES:
        asset = unreal.load_asset(path)
        row = {'path':path,'present':asset is not None,'instance_vector_overrides':[],'instance_scalar_overrides':[]}
        if asset is not None:
            row['class'] = asset.get_class().get_name()
            # These are source inputs, not rendered RGB. Inherited graph modulation is separate.
            for prop,target in (('vector_parameter_values','instance_vector_overrides'),
                                ('scalar_parameter_values','instance_scalar_overrides')):
                try:
                    for value in asset.get_editor_property(prop):
                        info = value.get_editor_property('parameter_info')
                        parameter = value.get_editor_property('parameter_value')
                        rgba = [parameter.r,parameter.g,parameter.b,parameter.a] if hasattr(parameter,'r') else parameter
                        row[target].append({'name':str(info.get_editor_property('name')),'value':rgba})
                except Exception as error:
                    row[prop+'_inspection_note'] = str(error)
        result.append(row)
    return result


report = {'passed':False,'asset':TARGET,'source_material':SOURCE,
          'shader_compile_verified':False,'new_material_only':True}
before = protected()
try:
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError('Existing outward Q material missing')
    library = unreal.MaterialEditingLibrary
    original,script_evidence = source_shader()
    source_custom = [n for n in library.get_material_expressions(source)
                     if n.get_class().get_name() == 'MaterialExpressionCustom']
    if len(source_custom) != 1 or source_custom[0].get_editor_property('code') != original:
        raise RuntimeError('Saved outward material shader differs from reviewed literal')
    shader = original
    replacements = []
    for name,old,new,literal in COLORS:
        if shader.count(literal) != 1:
            raise RuntimeError('RGB literal must occur exactly once: '+literal)
        replacement = 'lerp('+literal+', float3('+', '.join(format(v,'.8g') for v in new)+'), saturate(ToneMix))'
        shader = shader.replace(literal,replacement)
        replacements.append({'name':name,'previous_HDR_RGB':list(old),'muted_HDR_RGB':list(new),
                             'old_literal':literal,'new_expression':replacement})
    restored = shader
    for entry in replacements:
        restored = restored.replace(entry['new_expression'],entry['old_literal'])
    if restored != original:
        raise RuntimeError('Q tone modification changed more than the approved RGB expressions')
    # Alpha assignments and every non-color byte are covered by exact reverse reconstruction.
    alpha_before = [line.strip() for line in original.splitlines() if line.strip().startswith('alpha =')]
    alpha_after = [line.strip() for line in shader.splitlines() if line.strip().startswith('alpha =')]
    if alpha_before != alpha_after:
        raise RuntimeError('Q opacity changed')
    material = unreal.load_asset(TARGET)
    if material is None:
        folder,name = TARGET.rsplit('/',1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,unreal.Material,unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError('Muted material creation failed')
    material.modify()
    for key in ('blend_mode','shading_model','two_sided'):
        material.set_editor_property(key,source.get_editor_property(key))
    library.delete_all_material_expressions(material)

    def node(kind,**properties):
        result = library.create_material_expression(material,getattr(unreal,'MaterialExpression'+kind))
        for key,value in properties.items():
            result.set_editor_property(key,value)
        return result

    custom = node('Custom',code=shader,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                  description='Same outward Q shape; ToneMix 0 previous bright / 1 muted blood-red')
    names = ('UV','Clock','SpawnTime','Duration','Mode','ToneMix')
    inputs = []
    for name in names:
        value = unreal.CustomInput()
        value.set_editor_property('input_name',name)
        inputs.append(value)
    custom.set_editor_property('inputs',inputs)
    sources = [node('TextureCoordinate'),node('Time',ignore_pause=False)]
    sources += [node('ScalarParameter',parameter_name=name,default_value=value)
                for name,value in (('SpawnTime',0),('Duration',.58),('Mode',0),('ToneMix',1))]
    for name,entry in zip(names,sources):
        if not library.connect_material_expressions(entry,'',custom,name):
            raise RuntimeError('Unconnected custom input '+name)
    for channels,prop in ((dict(r=True,g=True,b=True,a=False),unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                           (dict(r=False,g=False,b=False,a=True),unreal.MaterialProperty.MP_OPACITY)):
        mask = node('ComponentMask',**channels)
        pin = library.get_material_expression_input_names(mask)[0]
        if not library.connect_material_expressions(custom,'',mask,pin) or not library.connect_material_property(mask,'',prop):
            raise RuntimeError('Muted material output connection failed')
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material,False):
        raise RuntimeError('Muted material save failed')
    after = protected()
    changed = [p for p,h in before.items() if after.get(p) != h]
    added = sorted(set(after)-set(before))
    if changed or added:
        raise RuntimeError('Protected project assets changed: '+str(changed+added))
    references = reference_parameters()
    # A second check covers read-only reference inspection as well as authoring.
    if protected() != after:
        raise RuntimeError('Reference material inspection changed an existing file')
    report.update(passed=True,source_shader_literal=script_evidence,
                  source_shader_sha256=hashlib.sha256(original.encode()).hexdigest(),
                  shader=shader,shader_sha256=hashlib.sha256(shader.encode()).hexdigest(),
                  colors=replacements,graph_inputs_wired=list(names),
                  tone_parameter={'name':'ToneMix','default':1,'previous_bright':0,'muted_blood_red':1},
                  tone_zero_reconstructs_previous_RGB=True,
                  color_expressions_only_changed=True,
                  all_non_color_shader_bytes_identical=True,
                  opacity_assignments_unchanged=alpha_before,
                  mesh_unchanged={'path':str(MESH),'sha256':sha(MESH)},
                  shape_UV_reveal_noise_timing_unchanged=True,
                  blend_mode=str(material.get_editor_property('blend_mode')),
                  graph_connections_verified=True,private_asset_dependencies=[],
                  contains_texture_or_particle_asset_references=False,
                  protected_files=len(before),protected_changes=changed,
                  protected_additions=added,new_asset_file=str(OWNED),new_asset_sha256=sha(OWNED),
                  reference_materials_read_only=references,
                  original_materials_unchanged=True,
                  interpretation_limitations=[
                      'HDR RGB inputs are not final display RGB; exposure, bloom, blend and material modulation affect appearance.',
                      'Muted colors are an authored match to observed Countess blood-red/black appearance, not a claim of copied original final pixel values.',
                      'Existing original particle impact flashes remain unchanged; only the private Q overlay color changes.',
                      'Shader compilation and actual PIE visual acceptance must be checked after authoring.'])
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT/'tone-material.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
