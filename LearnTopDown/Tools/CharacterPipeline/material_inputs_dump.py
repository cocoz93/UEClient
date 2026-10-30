"""List every expression of a material with the expressions wired into it (read-only), to find an unconnected input.
MATERIAL_DUMP = material object path. Writes material-inputs.json: [{name, class, inputs: [class or null, ...]}, ...]."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
report = {'passed': False}
try:
    material = unreal.load_asset(os.environ['MATERIAL_DUMP'])
    lib = unreal.MaterialEditingLibrary
    rows = []
    for expression in lib.get_material_expressions(material) if hasattr(lib, 'get_material_expressions') else []:
        inputs = lib.get_inputs_for_material_expression(material, expression)
        rows.append({'name': expression.get_name(), 'class': expression.get_class().get_name(),
                     'inputs': [i.get_class().get_name() if i else None for i in inputs]})
    report['expressions'] = rows
    report['count'] = lib.get_num_material_expressions(material)
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'material-inputs.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
