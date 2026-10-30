"""Build the Q-only, world-sized crescent/rush/impact material without pack edits."""
import json
import os
from pathlib import Path
import traceback
import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
PATH = '/Game/TopDown/Characters/Countess/Materials/M_CountessQCrescent'

# All positions and time below are local to a transient Q visual. No scene depth,
# camera effect, world position offset or gameplay collision is involved.
SHADER = r'''
float age = max(0, Clock - SpawnTime);
float t = saturate(age / max(Duration, 0.001));
float2 p = (UV - 0.5) * 2;
float3 blood = float3(9.0, 0.025, 0.08);
float3 hot = float3(23.0, 9.0, 6.0);
float shape = 0;
float core = 0;
float fade = pow(1 - t, 1.1);
if (Mode < 0.5)
{
    // A wide curved blade sweeps 100 degrees in 120ms, then leaves its silhouette.
    float spin = -0.9 + 1.75 * smoothstep(0.0, 0.12, age);
    float cs = cos(spin), sn = sin(spin);
    float2 q = float2(p.x * cs + p.y * sn, -p.x * sn + p.y * cs);
    float a = atan2(q.y, q.x);
    float radius = length(q);
    float taper = pow(saturate((cos(a) + 0.42) / 1.42), 0.65);
    float ridge = 0.65 + 0.045 * cos(a * 1.5);
    float d = abs(radius - ridge);
    float width = 0.015 + 0.15 * taper;
    float blade = pow(saturate(1 - d / width), 1.35) * taper;
    float edge = pow(saturate(1 - d / 0.022), 1.5) * taper;
    float brush = 0.78 + 0.22 * sin(radius * 235 + a * 7);
    // Separate narrow strands behind the blade keep the sweep directional.
    float echo = pow(saturate(1 - abs(radius - ridge + 0.115) / 0.025), 2) * taper * 0.24;
    shape = saturate(blade * brush + echo);
    core = edge;
}
else if (Mode < 1.5)
{
    // The actual departure-to-target segment, tapered at both ends.
    float ends = pow(saturate(sin(UV.x * 3.14159265)), 0.7);
    float bend = 0.045 * sin(UV.x * 3.14159265);
    float d = abs(p.y - bend);
    shape = pow(saturate(1 - d / (0.18 * ends + 0.008)), 2) * ends;
    core = pow(saturate(1 - d / 0.023), 2) * ends;
    fade = pow(1 - t, 2.0);
}
else
{
    // A short bright impact at the real damage event, not a permanent cross.
    float r = length(p);
    float a = atan2(p.y, p.x);
    float star = pow(abs(cos(a * 2)), 30);
    float rays = star * pow(saturate(1 - r), 2);
    float center = pow(saturate(1 - r / 0.25), 3);
    float ring = pow(saturate(1 - abs(r - (0.10 + t * 0.65)) / 0.035), 2) * 0.22;
    shape = saturate(rays + center + ring);
    core = center + rays * 0.7;
    fade = pow(1 - t, 2.0);
}
return float4(blood * shape + hot * core, saturate(shape * fade));
'''

report = {'passed': False, 'asset': PATH}
try:
    library = unreal.MaterialEditingLibrary
    material = unreal.load_asset(PATH)
    if material is None:
        folder, name = PATH.rsplit('/', 1)
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, unreal.Material, unreal.MaterialFactoryNew())
    material.modify()
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    existing = list(library.get_material_expressions(material))
    cursor = 0

    def node(kind, **properties):
        global cursor
        cls = getattr(unreal, 'MaterialExpression' + kind)
        result = existing[cursor] if cursor < len(existing) else library.create_material_expression(material, cls)
        if result.get_class().get_name() != 'MaterialExpression' + kind:
            raise RuntimeError('Unexpected existing Q crescent graph node ' + str(cursor))
        cursor += 1
        for key, value in properties.items():
            result.set_editor_property(key, value)
        return result

    custom = node('Custom', code=SHADER,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4,
                  description='Q sweeping crescent / departure ribbon / hit burst')
    names = ('UV', 'Clock', 'SpawnTime', 'Duration', 'Mode')
    inputs = []
    for name in names:
        entry = unreal.CustomInput()
        entry.set_editor_property('input_name', name)
        inputs.append(entry)
    custom.set_editor_property('inputs', inputs)
    sources = [node('TextureCoordinate'), node('Time', ignore_pause=False)]
    sources += [node('ScalarParameter', parameter_name=name, default_value=value)
                for name, value in (('SpawnTime', 0), ('Duration', .44), ('Mode', 0))]
    for name, source in zip(names, sources):
        if not library.connect_material_expressions(source, '', custom, name):
            raise RuntimeError('Unconnected custom material input ' + name)
    for channels, prop in ((dict(r=True, g=True, b=True, a=False), unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                           (dict(r=False, g=False, b=False, a=True), unreal.MaterialProperty.MP_OPACITY)):
        mask = node('ComponentMask', **channels)
        pin = library.get_material_expression_input_names(mask)[0]
        if not library.connect_material_expressions(custom, '', mask, pin):
            raise RuntimeError('Unconnected crescent output mask')
        if not library.connect_material_property(mask, '', prop):
            raise RuntimeError('Unconnected crescent material output')
    if existing and cursor != len(existing):
        raise RuntimeError('Unexpected unused Q graph nodes')
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Q crescent material save failed')
    report.update(passed=True, graph_connections_verified=True, shader_compile_verified=False,
                  shader=SHADER, original_pack_changed=False)
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT / 'material.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
