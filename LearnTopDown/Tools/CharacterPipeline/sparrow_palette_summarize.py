"""Summarize read-only source color modules, keeping their exact HDR values."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--inspection', required=True, type=Path)
args = parser.parse_args()
directory = args.inspection.resolve()
inspection = json.loads((directory / 'palette-inspection.json').read_text(encoding='utf-8-sig'))
inventory_path = directory / 'sparrow-native-inventory.json'
inventory = json.loads(inventory_path.read_text(encoding='utf-8-sig'))
assert inspection['passed'] and inspection['source_unchanged'] and inventory['passed']
assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == inspection['native_inventory_sha256']


def descendants(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from descendants(child)
    elif isinstance(value, list):
        for child in value:
            yield from descendants(child)


assets = []
for asset in inventory['assets']:
    emitters = []
    for emitter in asset.get('emitters', []):
        lods = emitter.get('lods', [])
        if not lods:
            continue
        lod = lods[0]
        colors = []
        for obj in descendants(lod):
            cls = obj.get('class', '')
            if 'DistributionVector' in cls and 'Color' in obj.get('path', ''):
                colors.append({'path': obj['path'], 'class': cls, 'properties': obj['properties']})
        emitters.append({'name': emitter['properties']['EmitterName'], 'enabled_lod0': lod['enabled'],
                         'material': lod.get('required', {}).get('properties', {}).get('Material'),
                         'color_distributions': colors})
    assets.append({'path': asset['path'], 'source_present': asset['present'], 'emitters': emitters})

report = {
    'passed': True,
    'scope': inspection['scope'],
    'native_color_inventory_sha256': inspection['native_inventory_sha256'],
    'source_unchanged': inspection['source_unchanged'],
    'appearance_skin_folders': inspection['appearance_skin_folders'],
    'fx_skin_folders': inspection['fx_skin_folders'],
    'interpretation_limitations': [
        'Exact HDR RGB distribution values are source input, not final display RGB.',
        'Material graphs, texture modulation, refraction, bloom and lighting affect display color.',
        'EmitterEditorColor is editor decoration and is never used as evidence.',
        'Asset existence does not mean the current pawn references that asset.',
        'No source color, E skill, material or package was modified.',
    ],
    'current_default_palette': {
        'Primary': 'Gold/amber/white release, trail and impact.',
        'Q': 'Gold/white falling arrows with purple/pink mist and spark accents.',
        'W': 'Lavender/violet charge and ribbon with gold/amber release and impact.',
        'E': 'Current Relentless is passive; no separate cast or impact effect.',
        'R': 'Gold/amber buff, empowered trails and impact, bright white highlights.',
    },
    'available_rogue_palette': {
        'Primary': 'Crimson/red with shadow tendrils and pale flash accents.',
        'Q': 'Red falling arrows and target glow; some inherited pale/gold modules remain.',
        'W': 'Red/crimson charge, ribbon and impact with shadow tendrils.',
        'E': 'No dedicated later passive E particle entry in the imported Rogue folder.',
        'R': 'Red/crimson buff and empowered arrows/impact with shadow tendrils.',
    },
    'assets': assets,
}
(directory / 'palette-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'passed': True, 'assets': len(assets), 'output': str(directory / 'palette-summary.json')}))
