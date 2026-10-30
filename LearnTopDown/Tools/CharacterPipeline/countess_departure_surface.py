"""Space departure only: torn charcoal/crimson ink, preserving F and moving ghosts."""
import hashlib
import json
from pathlib import Path

import unreal


SOURCE = '/Game/TopDown/Characters/Countess/Materials/M_CountessQualityMotionEcho'
TARGET = '/Game/TopDown/Characters/Countess/Reference20261024/M_CountessDepartureInk'
VERSION = '1'


def author(output):
    file = Path(unreal.Paths.project_content_dir()) / (SOURCE.removeprefix('/Game/') + '.uasset')
    before = hashlib.sha256(file.read_bytes()).hexdigest()
    material = unreal.load_asset(TARGET)
    if material is None:
        material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
    if not isinstance(material, unreal.Material):
        raise RuntimeError('Cannot duplicate the owned motion material for Space departure')
    graph_receipt = None
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'CountessDepartureVersion') != VERSION:
        # Earlier graph rebuilds can leave disconnected expressions in a saved
        # material. Select by actual property reachability, not global count.
        lib = unreal.MaterialEditingLibrary
        reachable = set()
        stack = [lib.get_material_property_input_node(material, prop) for prop in
                 (unreal.MaterialProperty.MP_EMISSIVE_COLOR, unreal.MaterialProperty.MP_OPACITY,
                  unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)]
        while stack:
            expression = stack.pop()
            if expression is None:
                continue
            path = unreal.SystemLibrary.get_path_name(expression)
            if path in reachable:
                continue
            if expression.get_outer() != material:
                raise RuntimeError('Connected expression is outside the owned departure material: ' + path)
            reachable.add(path)
            stack.extend(n for n in lib.get_inputs_for_material_expression(material, expression) if n is not None)
        surface, drift, disconnected = [], [], []
        for expression in unreal.ObjectIterator(unreal.MaterialExpressionCustom):
            try:
                if expression.get_outer() != material:
                    continue
                code = expression.get_editor_property('code')
            except (TypeError, AttributeError):
                continue
            is_surface = 'return float4(c*pow(1-t,.5),a)' in code
            is_drift = 'Direction*pow(t,1.4)' in code
            path = unreal.SystemLibrary.get_path_name(expression)
            if (is_surface or is_drift) and path not in reachable:
                disconnected.append(path)
                continue
            if is_surface:
                surface.append(expression)
            if is_drift:
                drift.append(expression)
        graph_receipt = {'reachable_count': len(reachable),
                         'connected_surface_nodes': [unreal.SystemLibrary.get_path_name(n) for n in surface],
                         'connected_drift_nodes': [unreal.SystemLibrary.get_path_name(n) for n in drift],
                         'disconnected_candidates_preserved': disconnected}
        (Path(output) / 'countess-departure-graph.json').write_text(json.dumps(graph_receipt, indent=2), encoding='utf-8')
        if not surface or len(drift) != 1:
            raise RuntimeError('Unexpected connected motion graph: surface=%d drift=%d' % (len(surface), len(drift)))
        for expression in surface:
            names = {str(pin.get_editor_property('input_name')) for pin in expression.get_editor_property('inputs')}
            if names != {'Noise', 'Facing', 'Clock', 'Start', 'Span', 'Opacity'}:
                raise RuntimeError('Connected surface has unexpected inputs: ' + repr(names))
            expression.set_editor_property('code', '''
float t=saturate((Clock-Start)/max(Span,.01));
float n=pow(saturate((Noise-.0075)/.5766),.55);
float facing=saturate(Facing);
float rim=pow(facing,3.4);
float threshold=.20+t*.52+facing*.14;
float flow=smoothstep(threshold,threshold+.17,n);
float torn=1-smoothstep(n*.40+.10,n*.40+.45,t);
float edge=pow(saturate(1-abs(n-threshold-.045)*24),2.3);
float inner=pow(saturate(1-abs(n-.43)*21),3);
float a=saturate(Opacity)*flow*torn*pow(1-t,.62)*(.63+.37*(1-facing));
float3 c=float3(.007,.00035,.0011)+float3(.065,.0011,.005)*n*n;
c+=float3(.69,.005,.022)*(edge*.82+inner*.22+rim*.18)*(.32+.68*flow);
return float4(c*pow(1-t,.45),a);
''')
        drift[0].set_editor_property('code', '''
float t=saturate((Clock-Start)/max(Span,.01));
float n=pow(saturate((Noise-.0075)/.5766),.55);
return Direction*pow(t,1.25)*(3+n*14);
''')
        # Original usage flags include clothing, preventing gray/default hair sections.
        material.set_editor_property('used_with_skeletal_mesh', True)
        material.set_editor_property('used_with_clothing', True)
        errors = [str(e) for e in (unreal.MaterialEditingLibrary.recompile_material(material) or [])]
        if errors:
            raise RuntimeError('Departure material compile failed: ' + repr(errors))
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'CountessDepartureVersion', VERSION)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save departure material')
    result = {'passed': True, 'asset': TARGET, 'version': VERSION,
              'source_unchanged': before == hashlib.sha256(file.read_bytes()).hexdigest(),
              'scope': 'only fixed Space departure; F and moving afterimages retain their existing material',
              'surface': 'dark interior, drifting ink patches and narrow red erosion boundary; no new particles',
              'graph': graph_receipt}
    if not result['source_unchanged']:
        raise RuntimeError('Shared motion material was modified')
    (Path(output) / 'countess-departure-surface.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
