"""Record the explicitly completed native-screen reviews; never approve user taste."""
import json
from pathlib import Path
from baseline import PROJECT, digest

base = PROJECT/'Saved/QA/CharacterPipeline/countess-q-outward-20261016'
independent = json.loads((base/'arch-review-30.json').read_text(encoding='utf-8-sig'))
assert independent['render_review_passed'] and not independent['user_style_approval']
reviewed = []
for folder in ('compare-60-02','motion-60-02'):
    manifest = json.loads((base/folder/'review/manifest.json').read_text(encoding='utf-8-sig'))
    reviewed += manifest['images']
reviewed += independent['reviewed_source_images']
motion = json.loads((base/'motion-60-02/countess-q-comparison-60.json').read_text(encoding='utf-8-sig'))
already = {r['path'] for r in reviewed}
reviewed += [{'path':r['image'],'sha256':r['sha256']} for r in motion['screenshots'] if r['image'] not in already]
assert len(reviewed)==65
for row in reviewed:
    assert digest(Path(row['path']))==row['sha256']
report = {
    'render_review_passed':True,
    'user_style_approval':False,
    'reviewed_source_images':reviewed,
    'review_basis':[
        'Parent explicitly inspected compare-60-02 sheets 01/02: seven Q phase pairs, fourteen native images.',
        'Independent character agent explicitly inspected compare-30-02 sheets 01/02: fourteen native images.',
        'Parent explicitly inspected motion-60-02 sheets 01..04 and all five additional native captures.',
    ],
    'observations':[
        'Previous connected curved surfaces are replaced with two independent straight tapered outward cuts.',
        'Large lateral span is retained; actual pawn/mesh orientation is retained in the direction samples.',
        'Original red-black particle texture remains around the strike and departure trail.',
        'No new grey plane, checker/default material or residual blade is visible in reviewed phases.',
        'New cut fades earlier than the previous curved afterimage; natural recovery and return remain visible.',
    ],
    'limitations':[
        'Bright red-white blade cores dominate; individual authored black flecks are less distinct at this camera size.',
        'Two reverse-direction captures place the strike near the lower HUD; those images do not prove unobstructed visibility for every camera framing.',
        'This is a stylized straight cut based on source socket direction, not the exact curved source blade trajectory.',
        'Paired native frame samples and derived GIF are not continuous video or physical OS-input verification.',
        'Technical render review is separate from user aesthetic approval.',
    ],
    'independent_review':{'path':str(base/'arch-review-30.json'),'sha256':digest(base/'arch-review-30.json')},
    'excluded_attempts':['compare-60-01','compare-30-01','motion-60-01'],
    'excluded_reason':'Initial launcher processes did not complete exit-code recording; only completed sequential runs are accepted.',
}
(base/'visual-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'render_review_passed':True,'reviewed_native_images':len(reviewed),'user_style_approval':False}))
