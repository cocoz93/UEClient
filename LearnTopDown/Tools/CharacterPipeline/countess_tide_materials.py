"""Adapt three copied Countess graphs to static meshes; save only the named copies.

Import and call author(output) from the QA editor hook, or execute as an Unreal
Python script with SPARROW_QA_OUTPUT. Pack graphs, textures and VertexColor stay
intact. Graph snapshots include every input (including disconnected slots).
"""
import hashlib
import json
import os
from pathlib import Path
import traceback

import unreal


VERSION = '1'
ROOT = '/Game/TopDown/Characters/Countess/Materials/'
SPECS = (
    ('Wing', '/Game/ParagonCountess/FX/Materials/Smoke/M_Countess_AimingInkWings'),
    ('Blade', '/Game/ParagonCountess/FX/Materials/Trails/M_MeshSwipe_rollingDarkInst'),
    ('Edge', '/Game/ParagonCountess/FX/Materials/Shockwaves/M_Countess_ShockwaveLeadingEdge'),
)
CONTROL_CLASSES = ('MaterialExpressionParticleColor', 'MaterialExpressionDynamicParameter')
PROPERTY_NAMES = (
    'MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_OPACITY_MASK', 'MP_BASE_COLOR',
    'MP_METALLIC', 'MP_SPECULAR', 'MP_ROUGHNESS', 'MP_ANISOTROPY', 'MP_NORMAL',
    'MP_TANGENT', 'MP_WORLD_POSITION_OFFSET', 'MP_SUBSURFACE_COLOR',
    'MP_CUSTOM_DATA_0', 'MP_CUSTOM_DATA_1', 'MP_CUSTOM_DATA0', 'MP_CUSTOM_DATA1',
    'MP_AMBIENT_OCCLUSION', 'MP_REFRACTION',
    'MP_CUSTOMIZED_U_VS_0', 'MP_CUSTOMIZED_U_VS_1', 'MP_CUSTOMIZED_U_VS_2',
    'MP_CUSTOMIZED_U_VS_3', 'MP_CUSTOMIZED_U_VS_4', 'MP_CUSTOMIZED_U_VS_5',
    'MP_CUSTOMIZED_U_VS_6', 'MP_CUSTOMIZED_U_VS_7', 'MP_PIXEL_DEPTH_OFFSET',
    'MP_CUSTOMIZED_UVS0', 'MP_CUSTOMIZED_UVS1', 'MP_CUSTOMIZED_UVS2', 'MP_CUSTOMIZED_UVS3',
    'MP_CUSTOMIZED_UVS4', 'MP_CUSTOMIZED_UVS5', 'MP_CUSTOMIZED_UVS6', 'MP_CUSTOMIZED_UVS7',
    'MP_CUSTOMIZED_UVS_0', 'MP_CUSTOMIZED_UVS_1', 'MP_CUSTOMIZED_UVS_2', 'MP_CUSTOMIZED_UVS_3',
    'MP_CUSTOMIZED_UVS_4', 'MP_CUSTOMIZED_UVS_5', 'MP_CUSTOMIZED_UVS_6', 'MP_CUSTOMIZED_UVS_7',
    'MP_SHADING_MODEL', 'MP_FRONT_MATERIAL', 'MP_SURFACE_THICKNESS',
    'MP_DISPLACEMENT', 'MP_MATERIAL_ATTRIBUTES',
)


def _require(condition, message):
    if not condition:
        raise RuntimeError(message)


def _value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, unreal.LinearColor):
        return [value.r, value.g, value.b, value.a]
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    return str(value)


def _kind(node):
    return node.get_class().get_name()


def _node_name(node):
    return node.get_name() if node else None


def _props(node):
    result = {}
    for name in ('desc', 'parameter_name', 'default_value', 'param_names',
                 'parameter_index', 'texture', 'r', 'g', 'b', 'a', 'const_a',
                 'const_b', 'const_alpha', 'exponent', 'min_default',
                 'max_default', 'coordinate_index', 'u_tiling', 'v_tiling',
                 'speed_x', 'speed_y', 'function', 'material_function'):
        try:
            result[name] = _value(node.get_editor_property(name))
        except Exception:
            pass
    return result


def _output_name(consumer, source):
    # UE Python versions expose the bool/out-string pair as str or tuple.
    result = unreal.MaterialEditingLibrary.get_input_node_output_name_for_material_expression(consumer, source)
    if isinstance(result, str):
        return result
    if isinstance(result, tuple):
        _require(not any(isinstance(v, bool) and not v for v in result), 'Output lookup failed')
        strings = [v for v in result if isinstance(v, str)]
        if len(strings) == 1:
            return strings[0]
    raise RuntimeError('Unexpected output-name result: ' + repr(result))


def _inputs(material, consumer):
    """Read exact per-pin channels on a COPY, then restore every connection.

    The library's lookup finds the first matching source, not a named input.
    Detaching in iterator order exposes the next occurrence, including a source
    feeding A and B through different channels. Never call this on a pack graph.
    """
    lib = unreal.MaterialEditingLibrary
    names = [str(n) for n in lib.get_material_expression_input_names(consumer)]
    sources = list(lib.get_inputs_for_material_expression(material, consumer))
    _require(len(names) == len(sources), 'Input-name/null-slot alignment changed: ' + consumer.get_path_name())
    connected_names = [name for name, source in zip(names, sources) if source is not None]
    _require(len(connected_names) == len(set(connected_names)), 'Ambiguous duplicate input names: ' + consumer.get_path_name())
    detached = []
    rows = []
    try:
        for name, source in zip(names, sources):
            if source is None:
                rows.append({'pin': name, 'source': None, 'output': None})
                continue
            output = _output_name(consumer, source)
            _require(lib.disconnect_material_expressions(consumer, name), 'Cannot detach input: ' + name)
            detached.append((source, output, name))
            rows.append({'pin': name, 'source': _node_name(source), 'output': output})
    finally:
        for source, output, name in detached:
            _require(lib.connect_material_expressions(source, output, consumer, name), 'Cannot restore input: ' + name)
    _require(list(lib.get_inputs_for_material_expression(material, consumer)) == sources,
             'Input restoration failed: ' + consumer.get_path_name())
    return rows


def _properties(material):
    lib = unreal.MaterialEditingLibrary
    result = {}
    for name in PROPERTY_NAMES:
        prop = getattr(unreal.MaterialProperty, name, None)
        if prop is None:
            continue
        source = lib.get_material_property_input_node(material, prop)
        if source:
            result[name] = {'source': _node_name(source),
                            'output': lib.get_material_property_input_node_output_name(material, prop)}
    return result


def _graph(material):
    lib = unreal.MaterialEditingLibrary
    nodes = list(lib.get_material_expressions(material))
    # GetOutputs refreshes DynamicParameter's custom channel labels. The output
    # lookup helper reads its Outputs array directly, so initialize all first.
    outputs = {node.get_name(): [str(n) for n in lib.get_material_expression_output_names(node)] for node in nodes}
    return {'nodes': {node.get_name(): {'class': _kind(node), 'props': _props(node),
                                      'inputs': _inputs(material, node),
                                      'outputs': outputs[node.get_name()]}
                      for node in nodes},
            'properties': _properties(material)}


def _parameters(material):
    lib = unreal.MaterialEditingLibrary
    instance = isinstance(material, unreal.MaterialInstanceConstant)
    base = material.get_base_material()
    result = {}
    for category in ('scalar', 'vector', 'texture', 'static_switch'):
        names = getattr(lib, 'get_' + category + '_parameter_names')(material)
        getter = getattr(lib, ('get_material_instance_' if instance else 'get_material_default_') + category + '_parameter_value')
        result[category] = {str(name): _value(getter(material if instance else base, name)) for name in names}
    return result


def _apply_instance_defaults(source, material):
    """Flatten the MI's effective values into ONLY the duplicated base nodes."""
    if not isinstance(source, unreal.MaterialInstanceConstant):
        return {}
    lib = unreal.MaterialEditingLibrary
    result = {'effective': _parameters(source), 'copied_nodes': []}
    for node in lib.get_material_expressions(material):
        try:
            name = str(node.get_editor_property('parameter_name'))
        except Exception:
            continue
        kind = _kind(node)
        if isinstance(node, unreal.MaterialExpressionScalarParameter):
            value = lib.get_material_instance_scalar_parameter_value(source, name)
            prop = 'default_value'
        elif isinstance(node, unreal.MaterialExpressionVectorParameter):
            value = lib.get_material_instance_vector_parameter_value(source, name)
            prop = 'default_value'
        elif kind.startswith(('MaterialExpressionTextureSampleParameter', 'MaterialExpressionTextureObjectParameter')):
            value = lib.get_material_instance_texture_parameter_value(source, name)
            prop = 'texture'
        elif isinstance(node, unreal.MaterialExpressionStaticBoolParameter):
            value = lib.get_material_instance_static_switch_parameter_value(source, name)
            prop = 'default_value'
        else:
            continue
        node.set_editor_property(prop, value)
        result['copied_nodes'].append({'node': node.get_name(), 'name': name, 'value': _value(value)})
    return result


def _same_values(expected, actual):
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        return abs(expected - actual) <= max(1.e-6, abs(expected) * 1.e-6)
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(_same_values(a, b) for a, b in zip(expected, actual))
    return expected == actual


def _check_parameters(expected, material):
    actual = _parameters(material)
    for category, parameters in expected.items():
        for name, value in parameters.items():
            _require(name in actual[category] and _same_values(value, actual[category][name]),
                     'Effective MI/default value was not preserved: ' + category + ':' + name)
    return actual


def _pack_hashes(paths):
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    result = {}
    for path in sorted(set(paths)):
        _require(path.startswith('/Game/ParagonCountess/'), 'Unexpected source hash path: ' + path)
        filename = content / (path[len('/Game/'):].split('.')[0] + '.uasset')
        _require(filename.is_file(), 'Source package missing: ' + str(filename))
        result[path] = hashlib.sha256(filename.read_bytes()).hexdigest()
    return result


def _new_parameter(material, old, name, value):
    lib = unreal.MaterialEditingLibrary
    x, y = lib.get_material_expression_node_position(old)
    node = lib.create_material_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    _require(node is not None, 'Cannot create ' + name)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    node.set_editor_property('desc', 'Static-mesh adapter for ' + old.get_name() + '; original graph retained')
    return node


def _mapped_output(info, output):
    _require(output in info['channels'], 'Unsupported source output: ' + repr(output))
    return info['channels'][output]


def _author_one(source, target_path, row):
    lib = unreal.MaterialEditingLibrary
    base = source.get_base_material()
    existing = unreal.load_asset(target_path)
    if existing and not unreal.EditorAssetLibrary.get_metadata_tag(existing, 'CountessNightTideVersion') and os.environ.get('COUNTESS_TIDE_REBUILD_PENDING') == '1':
        # Explicit recovery of this run's new duplicate after an interrupted author.
        _require(target_path in {ROOT + 'M_CountessNightTide' + label for label, _ in SPECS}, 'Recovery target outside owned set')
        _require(unreal.EditorAssetLibrary.delete_asset(target_path), 'Cannot remove incomplete owned duplicate')
        existing = None
    if existing:
        _require(unreal.EditorAssetLibrary.get_metadata_tag(existing, 'CountessNightTideVersion') == VERSION,
                 'Refusing to overwrite an unrecognized existing target: ' + target_path)
        _require(unreal.EditorAssetLibrary.get_metadata_tag(existing, 'CountessNightTideSource') == source.get_path_name(),
                 'Existing target has another source: ' + target_path)
        row['reused'] = True
        return existing
    material = unreal.EditorAssetLibrary.duplicate_asset(base.get_path_name(), target_path)
    _require(isinstance(material, unreal.Material), 'Could not duplicate base graph: ' + target_path)
    _require(material.get_path_name().split('.')[0] == target_path, 'Duplicate returned an unexpected asset')
    before = _graph(material)
    row['source_graph'] = before
    row['particle_node_classes'] = sorted({item['class'] for item in before['nodes'].values() if 'Particle' in item['class']})
    expected_parameters = _parameters(source)
    row['mi_defaults'] = _apply_instance_defaults(source, material)
    nodes = {n.get_name(): n for n in lib.get_material_expressions(material)}
    replacements = {}
    phase_defaults = None
    for old in list(nodes.values()):
        kind = _kind(old)
        if kind not in CONTROL_CLASSES:
            continue
        if kind == 'MaterialExpressionParticleColor':
            new = _new_parameter(material, old, 'TideTint', unreal.LinearColor(1., 1., 1., 1.))
            channels = {name: name for name in before['nodes'][old.get_name()]['outputs']}
        else:
            default = old.get_editor_property('default_value')
            _require(old.get_editor_property('parameter_index') == 0, 'Multiple DP indices need separate runtime controls')
            if phase_defaults is None:
                phase_defaults = _value(default)
            _require(phase_defaults == _value(default), 'Conflicting DynamicParameter defaults')
            new = _new_parameter(material, old, 'TidePhase', default)
            outputs = before['nodes'][old.get_name()]['outputs']
            _require(len(outputs) in (4, 6), 'Unexpected DynamicParameter output count: ' + repr(outputs))
            channels = dict(zip(outputs, ('R', 'G', 'B', 'A', 'RGB', 'RGBA')))
            _require(len(channels) == len(outputs), 'Ambiguous DynamicParameter output names')
        replacements[old.get_name()] = {'node': new, 'channels': channels}
    _require(replacements, 'No ParticleColor/DynamicParameter controls found')
    rewired = []
    for consumer_name, data in before['nodes'].items():
        consumer = nodes[consumer_name]
        for link in data['inputs']:
            info = replacements.get(link['source'])
            if info:
                output = _mapped_output(info, link['output'])
                _require(lib.connect_material_expressions(info['node'], output, consumer, link['pin']),
                         'Cannot adapt expression input: ' + consumer_name + ':' + link['pin'])
                rewired.append({'consumer': consumer_name, 'pin': link['pin'], 'old_source': link['source'],
                                'old_output': link['output'], 'new_source': info['node'].get_name(), 'new_output': output})
    for name, link in before['properties'].items():
        info = replacements.get(link['source'])
        if info:
            _require(lib.connect_material_property(info['node'], _mapped_output(info, link['output']), getattr(unreal.MaterialProperty, name)),
                     'Cannot adapt direct material property: ' + name)
    for old_name in replacements:
        lib.delete_material_expression(material, nodes[old_name])

    opacity_source = lib.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY)
    _require(opacity_source is not None, 'Original graph has no opacity input')
    opacity_output = lib.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_OPACITY)
    opacity = lib.create_material_expression(material, unreal.MaterialExpressionScalarParameter, 200, 300)
    opacity.set_editor_property('parameter_name', 'TideOpacity')
    opacity.set_editor_property('default_value', 1.)
    multiply = lib.create_material_expression(material, unreal.MaterialExpressionMultiply, 400, 300)
    multiply.set_editor_property('desc', 'Original opacity x TideOpacity; source texture/vertex mask retained')
    _require(lib.connect_material_expressions(opacity_source, opacity_output, multiply, 'A'), 'Original opacity reconnect failed')
    _require(lib.connect_material_expressions(opacity, '', multiply, 'B'), 'TideOpacity connect failed')
    _require(lib.connect_material_property(multiply, '', unreal.MaterialProperty.MP_OPACITY), 'Opacity material connect failed')

    after = _graph(material)
    for consumer_name, data in before['nodes'].items():
        if consumer_name in replacements:
            continue
        expected = []
        for link in data['inputs']:
            info = replacements.get(link['source'])
            expected.append({'pin': link['pin'], 'source': info['node'].get_name() if info else link['source'],
                             'output': _mapped_output(info, link['output']) if info else link['output']})
        _require(after['nodes'][consumer_name]['inputs'] == expected,
                 'Graph input/channel validation failed: ' + consumer_name)
    for name, link in before['properties'].items():
        if name == 'MP_OPACITY':
            continue
        info = replacements.get(link['source'])
        expected = {'source': info['node'].get_name() if info else link['source'],
                    'output': _mapped_output(info, link['output']) if info else link['output']}
        _require(after['properties'][name] == expected, 'Material property/WPO changed: ' + name)
    _require(after['nodes'][multiply.get_name()]['inputs'][0]['source'] == opacity_source.get_name(), 'Opacity source mismatch')
    _require(not any(n['class'] in CONTROL_CLASSES for n in after['nodes'].values()), 'Particle control node survived')
    row['replacement_nodes'] = {name: {'new': info['node'].get_name(), 'channels': info['channels']}
                                for name, info in replacements.items()}
    row['rewired'] = rewired
    row['phase_default'] = phase_defaults
    row['adapted_graph'] = after
    row['remaining_particle_nodes'] = [{'name': name, 'class': item['class']} for name, item in after['nodes'].items() if 'Particle' in item['class']]
    row['graph_inputs_and_outputs_verified'] = True
    errors = list(lib.recompile_material(material) or [])
    row['compile_errors'] = [str(e) for e in errors]
    _require(not errors, 'Material compiler errors: ' + repr(errors))
    row['effective_parameters'] = _check_parameters(expected_parameters, material)
    for key, value in {
        'CountessNightTideVersion': VERSION,
        'CountessNightTideSource': source.get_path_name(),
        'CountessNightTideSourceBase': base.get_path_name(),
        'CountessNightTideControls': json.dumps({'TideTint': [1, 1, 1, 1], 'TidePhase': phase_defaults, 'TideOpacity': 1}),
        'CountessNightTideGraphVerified': 'true',
    }.items():
        unreal.EditorAssetLibrary.set_metadata_tag(material, key, value)
    return material


def author(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'version': VERSION, 'pack_assets_saved': False,
              'saved_assets': [], 'materials': [], 'phase_channels': {
                  'Wing': ['WipeOn', 'WipeOff', 'EmissiveWipe', 'TexScale'],
                  'Blade': ['PanPosition', 'Param2', 'Param3', 'Param4']}}
    try:
        sources = []
        for label, source_path in SPECS:
            source = unreal.load_asset(source_path)
            _require(source is not None, 'Source missing: ' + source_path)
            sources.append((label, source))
        hash_paths = [obj.get_path_name() for _, obj in sources]
        hash_paths += [obj.get_base_material().get_path_name() for _, obj in sources]
        hash_paths.append('/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/P_Countess_BladeSiphon_Trails')
        report['source_sha256_before'] = _pack_hashes(hash_paths)
        pending = []
        for label, source in sources:
            target = ROOT + 'M_CountessNightTide' + label
            row = {'label': label, 'source': source.get_path_name(), 'base': source.get_base_material().get_path_name(), 'target': target}
            report['materials'].append(row)
            material = _author_one(source, target, row)
            nodes = list(unreal.MaterialEditingLibrary.get_material_expressions(material))
            _require(not any(_kind(n) in CONTROL_CLASSES for n in nodes), 'Unadapted particle control in target')
            _require('TideOpacity' in [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)], 'TideOpacity missing')
            row['effective_parameters'] = _check_parameters(_parameters(source), material)
            pending.append((material, target))
        _require(_pack_hashes(hash_paths) == report['source_sha256_before'], 'Source packages changed before save')
        for material, target in pending:
            _require(target in {ROOT + 'M_CountessNightTide' + label for label, _ in SPECS}, 'Unapproved save target')
            _require(unreal.EditorAssetLibrary.save_loaded_asset(material, False), 'Save failed: ' + target)
            report['saved_assets'].append(target)
        body_path = '/Game/TopDown/Characters/Countess/FX/P_CountessNightTideBody'
        body = unreal.load_asset(body_path)
        if body is None:
            body = unreal.EditorAssetLibrary.duplicate_asset(
                '/Game/ParagonCountess/FX/Particles/Abilities/BladeSiphon/FX/P_Countess_BladeSiphon_Trails', body_path)
        _require(body is not None, 'Could not create dedicated tide body')
        prefix = body.get_path_name() + ':'
        adapted = []
        for item in unreal.ObjectIterator(unreal.Object):
            object_path = unreal.SystemLibrary.get_path_name(item)
            if not object_path.startswith(prefix):
                continue
            kind = item.get_class().get_name()
            if kind == 'ParticleModuleRequired':
                item.set_editor_property('bUseLocalSpace', True)
                item.set_editor_property('bKillOnDeactivate', False)
                item.set_editor_property('EmitterLoops', 0)
                item.set_editor_property('EmitterDuration', .24)
                item.set_editor_property('EmitterDurationLow', .24)
                adapted.append(object_path)
            elif kind == 'ParticleModuleLocationBoneSocket':
                item.set_editor_property('bEnabled', False)
            elif kind == 'ParticleModuleLifetime':
                distribution = item.get_editor_property('lifetime').get_editor_property('distribution')
                _require(unreal.SystemLibrary.get_path_name(distribution).startswith(prefix), 'Lifetime distribution is outside dedicated body')
                if distribution.get_class().get_name() == 'DistributionFloatConstant':
                    distribution.set_editor_property('constant', .40)
                elif distribution.get_class().get_name() == 'DistributionFloatUniform':
                    distribution.set_editor_property('min', .32)
                    distribution.set_editor_property('max', .40)
        _require(adapted, 'No required modules in dedicated tide body')
        _require(unreal.EditorAssetLibrary.save_loaded_asset(body, False), 'Cannot save dedicated tide body')
        report['body_effect'] = {'asset': body_path, 'local_space_modules': len(adapted), 'source_saved': False}
        report['saved_assets'].append(body_path)
        report['source_sha256_after'] = _pack_hashes(hash_paths)
        _require(report['source_sha256_before'] == report['source_sha256_after'], 'Original source package changed')
        report['passed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    (output / 'countess-tide-materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.log('COUNTESS_TIDE_MATERIALS passed=' + str(report['passed']) + ' output=' + str(output))
    return report


if __name__ == '__main__':
    destination = os.environ.get('SPARROW_QA_OUTPUT') or str(Path(unreal.Paths.project_saved_dir()) / 'QA/CharacterPipeline/countess-D-rebuild-20261021/tide-materials')
    author(destination)
    unreal.SystemLibrary.quit_editor()
