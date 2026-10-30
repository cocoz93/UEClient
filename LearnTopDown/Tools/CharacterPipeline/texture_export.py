"""Export textures as PNG files so their patterns and channels can be looked at outside the editor (read-only for assets).
EXPORT_TEXTURES = comma list of texture object paths. Writes <name>.png and texture-export.json into the output folder."""
import json
import os
from pathlib import Path
import traceback

import unreal

qa = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
report = {'passed': False, 'textures': {}}
try:
    for path in os.environ['EXPORT_TEXTURES'].split(','):
        texture = unreal.load_asset(path)
        if texture is None:
            report['textures'][path] = 'missing'
            continue
        task = unreal.AssetExportTask()
        task.object = texture
        task.filename = str(qa / (texture.get_name() + '.png'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = unreal.TextureExporterPNG()
        ok = unreal.Exporter.run_asset_export_task(task)
        report['textures'][path] = {'exported': ok, 'compression': str(texture.get_editor_property('compression_settings')),
                                    'srgb': texture.get_editor_property('srgb'),
                                    'size': [texture.blueprint_get_size_x(), texture.blueprint_get_size_y()]}
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (qa / 'texture-export.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
