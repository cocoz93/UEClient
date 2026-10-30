"""Read reflected Cascade module controls without saving any asset."""
import json
import os
from pathlib import Path
import traceback
import unreal

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
ROOT = Path(unreal.Paths.project_dir()).resolve()
audit = json.loads((OUT.parent / 'audit/audit.json').read_text())
report = {'passed': False, 'read_only': True, 'modules': [], 'private_properties': {}}
try:
    assets = [unreal.load_asset(p) for p in audit['effects']]
    prefixes = tuple(a.get_path_name() + ':' for a in assets)
    report['object_iterator_available'] = hasattr(unreal, 'ObjectIterator')
    if not report['object_iterator_available']:
        raise RuntimeError('Reflected ObjectIterator unavailable')
    classes = {'ParticleModuleSpawn':('rate','rate_scale','burst_list'),
               'ParticleModuleSize':('start_size',), 'ParticleModuleLifetime':('lifetime',),
               'ParticleModuleLocationPrimitiveCylinder':('start_radius',)}
    for class_name, properties in classes.items():
        for obj in unreal.ObjectIterator(getattr(unreal, class_name)):
            object_path = unreal.SystemLibrary.get_path_name(obj)
            if not object_path.startswith(prefixes):
                continue
            row = {'path': object_path, 'class':class_name, 'properties':{}}
            for name in properties:
                try:
                    value = obj.get_editor_property(name)
                    entry = {'value':str(value)}
                    if hasattr(value, 'get_editor_property') and name != 'burst_list':
                        distribution = value.get_editor_property('distribution')
                        entry['distribution'] = distribution.get_path_name() if distribution else None
                        entry['distribution_class'] = distribution.get_class().get_name() if distribution else None
                        for prop in ('constant','min','max'):
                            try:
                                entry[prop] = str(distribution.get_editor_property(prop))
                            except Exception:
                                pass
                    row['properties'][name] = entry
                except Exception as error:
                    row['properties'][name] = {'error':str(error)}
            report['modules'].append(row)
    for hero, data in audit['heroes'].items():
        component = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(data['blueprint'])).get_skills()
        names = ('VisualEffects','TeleportArrivalEffect','SiphonTrails') if hero == 'countess' else ('UltimateTrail','InnerFireEffect')
        for name in names:
            try:
                report['private_properties'][hero+'.'+name] = str(component.get_editor_property(name))
            except Exception as error:
                report['private_properties'][hero+'.'+name] = str(error)
    report['passed'] = bool(report['modules'])
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT/'probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
