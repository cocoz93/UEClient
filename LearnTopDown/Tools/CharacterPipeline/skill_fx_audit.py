"""Read the installed Q/W/R presentation without changing hero or source assets."""
import json
import os
from pathlib import Path
import sys
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
from baseline import verify

OUT = Path(os.environ['SPARROW_QA_OUTPUT']).resolve()
report = {'passed': False, 'read_only': True, 'heroes': {}, 'effects': {}}


def path(value):
    return value.get_path_name() if isinstance(value, unreal.Object) else str(value)


def property_value(obj, name):
    try:
        return obj.get_editor_property(name)
    except Exception as error:
        return 'unavailable: ' + str(error)


def describe(effect):
    if not effect or effect.get_path_name() in report['effects']:
        return
    row = {'path': effect.get_path_name(), 'emitters': []}
    emitters = property_value(effect, 'emitters')
    if isinstance(emitters, str):
        row['error'] = emitters
    else:
        for emitter in emitters:
            entry = {'path': path(emitter), 'name': str(property_value(emitter, 'emitter_name')), 'lods': []}
            lods = property_value(emitter, 'lod_levels')
            if isinstance(lods, str):
                entry['error'] = lods
            else:
                for lod in lods:
                    item = {'path': path(lod), 'enabled': str(property_value(lod, 'enabled')), 'modules': []}
                    for kind in ('required_module', 'spawn_module', 'type_data_module'):
                        item[kind] = path(property_value(lod, kind))
                    modules = property_value(lod, 'modules')
                    if not isinstance(modules, str):
                        for module in modules:
                            item['modules'].append({'path':path(module), 'class':module.get_class().get_name()})
                    entry['lods'].append(item)
            row['emitters'].append(entry)
    report['effects'][effect.get_path_name()] = row


try:
    report['baseline'] = verify(ROOT / 'Saved/QA/CharacterPipeline/baseline-training-room-complete-20261015/baseline.json')
    if not report['baseline']['passed']:
        raise RuntimeError('Current room baseline changed before QWR audit')
    for hero in ('countess', 'sparrow'):
        profile = json.loads((ROOT / f'Tools/CharacterPipeline/Profiles/{hero}.json').read_text())
        cls = unreal.EditorAssetLibrary.load_blueprint_class(profile['character_blueprint'])
        component = unreal.get_default_object(cls).get_skills()
        skill_rows = []
        for index, definition in enumerate(component.get_editor_property('skills')):
            row = {name:path(definition.get_editor_property(name)) for name in
                   ('name','animation','cast_effect','impact_effect','cast_sound','damage','cooldown','range','action_time','recovery_time')}
            row['slot'] = index
            skill_rows.append(row)
            if index != 2:
                for key in ('cast_effect','impact_effect'):
                    describe(definition.get_editor_property(key))
        extra = {}
        names = ('visual_effects','teleport_arrival_effect','siphon_trails') if hero == 'countess' else ('ultimate_trail','inner_fire_effect')
        for name in names:
            value = property_value(component, name)
            if name == 'visual_effects' and not isinstance(value, str):
                extra[name] = [path(e) for e in value]
                for i in (0,1,5,6,7,8,10,13,14,15):
                    describe(value[i])
            else:
                extra[name] = path(value)
                if isinstance(value, unreal.ParticleSystem):
                    describe(value)
        report['heroes'][hero] = {'blueprint':profile['character_blueprint'],'skills':skill_rows,'extra':extra}
    report['passed'] = True
except Exception:
    report['error'] = traceback.format_exc()
finally:
    (OUT/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.SystemLibrary.quit_editor()
