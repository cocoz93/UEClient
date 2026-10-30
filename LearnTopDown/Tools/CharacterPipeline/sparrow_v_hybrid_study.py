"""V4: native flame feathers with a restrained outer crown, preview only.

Reuse VSignature's owned-material author and actual-V capture/restore contract.
Only two materials under VHybrid20261024 are saved. Native wing geometry,
scale, unfold, lifetime, body materials and production bindings are unchanged.
The parent owns all editor execution and visual acceptance.
"""
import os
from pathlib import Path
import runpy

import unreal


_LOADED = runpy.run_path(str(Path(__file__).with_name('sparrow_v_signature_studies.py')))
# run_path can return a copy; use the functions' actual private global namespace.
_SIGNATURE = _LOADED['author'].__globals__
_author, _sequence = _LOADED['author'], _LOADED['sequence']
_write = _LOADED['write']
_Signature, valid = _LOADED['Signature'], _LOADED['valid']

PREVIEW = '/Game/TopDown/Characters/Sparrow/Previews/VHybrid20261024'
OPTIONS = ('V4',)
DESIGNS = {
    'V4': {
        'label': '깃불 왕관',
        'surface': '촘촘한 V1 깃불과 어두운 깃 사이를 유지하고, 외곽에만 V3 왕관 발광을 40% 섞는다.',
        'entry': '원래 날개 펼침을 따라 아래에서 위로 점화한 뒤 바깥 깃끝에 짧게 불이 오른다.',
        'hold': '깃결을 타는 불꽃과 비대칭 외곽 맥동; 별도 왕관 도형이나 큰 섬광은 없다.',
        'crown_weight': .40,
    },
}

_SHADER = '''
// V1's dense, rising feather texture remains the continuous wing surface.
float bend = sin(rel.z*.027-Clock*2.8+side*.012)*.16;
float2 uv = float2(side*.022+back*.007+bend, -rel.z*.024+Clock*.96);
float fa = Texture2DSample(Fire,FireSampler,uv).r;
float fb = Texture2DSample(Fire,FireSampler,uv*float2(1.8,.72)+float2(.23,-Clock*.19)).g;
float shaft = pow(saturate(1-abs(frac(side*.055+rel.z*.004+bend*.25)-.5)*2),1.4);
float heat = saturate(fa*.78+fb*.38);
float flame = smoothstep(.11,.53,heat)*(.38+.62*shaft);
float hot = pow(smoothstep(.43,.83,heat),2)*shaft;
float reveal = 1-smoothstep(age/.30,age/.30+.16,h);
float3 feathers = lerp(float3(.15,.022,.001),float3(3.3,1.14,.025),flame);
feathers = lerp(feathers,float3(4.8,3.2,.66),hot*.58);

// Narrow the V3 crown to the true outer/top region. It lives on the same
// native membrane: no added ring, crown mesh, or fire sheet around the wing.
float2 crownUV = float2(side*.018+back*.010+sin(Clock*1.7+h*5)*.08,
                       -rel.z*.021+Clock*.62);
float crownFire = Texture2DSample(Fire,FireSampler,crownUV).r;
float outer = max(smoothstep(.52,.86,x),
                  smoothstep(.62,.86,h)*smoothstep(.25,.62,x));
float teeth = .64+.36*pow(saturate(sin(x*31+h*5+crownFire*2)),3);
float crown = outer*(.38+.62*smoothstep(.055,.39,crownFire))*teeth;
float sector = min(floor(x*3),2.0);
float phase = frac(age*.78);
float beat = exp(-pow((phase-(.12+sector*.15))/.085,2));
float entry = smoothstep(sector*.075,sector*.075+.14,age);
float crownWeight = .40*entry;
float3 edgeFire = float3(3.8,1.65,.055)*crown*(.90+.45*beat);
edgeFire += float3(4.6,3.5,1.1)*pow(crown,3)*beat*.30;
// Local interpolation retains the V1 interior and keeps dark feather gaps.
float3 color = lerp(feathers,feathers*.68+edgeFire,crownWeight*outer);
float alpha = support*(.28+.71*flame);
alpha = lerp(alpha,support*(.18+.73*outer+.07*spline*outer),crownWeight*outer);
return float4(color,alpha*saturate(reveal));
'''


def _hybrid_result(value):
    result = dict(value)
    # These fields belong to the old three-option run, not this isolated study.
    result.pop('V2_existing_packages_unchanged', None)
    result.pop('V2_package_hashes', None)
    result['crown_weight'] = .40
    result['production_installed'] = False
    return result


def _write_hybrid(out, name, value):
    _write(out, name.replace('V-signature', 'V-hybrid'), _hybrid_result(value))


class Hybrid(_Signature):
    def __init__(self, rig, option):
        super().__init__(rig, option)
        self.slot_restoration = []

    def update(self):
        super().update()
        if self.birth is None:
            return
        age = self.now()-self.birth
        # A small boundary accent bridges V1's surface-only silhouette and V3.
        # Stagger each side, rather than synchronously flashing a large crown.
        cycle = int(age/.84)
        phase = age-cycle*.84
        for side, moment, reach in ((-1, .17, .78), (1, .29, .94)):
            token = (cycle, side)
            if phase >= moment and token not in self.beats:
                self.beats.add(token)
                self.emit('impact', ('Sparks',), side, reach, 7.,
                          (.24,.16,.28), .20, rise=8.)

    def close(self):
        original_slots = [(slot, original) for slot, original, _ in self.slots]
        result = super().close()
        # Check the actual native component before sequence destroys its form.
        self.slot_restoration = [
            {'slot': slot, 'material': original.get_path_name(),
             'restored': valid(self.wing) and self.wing.get_material(slot) == original}
            for slot, original in original_slots]
        restored = len(self.slot_restoration) == 2 and all(
            row['restored'] for row in self.slot_restoration)
        self.rig['check'](restored, 'V4 restores both native wing MID slots before form destruction')
        _write(self.rig['OUT'], 'V-hybrid-slot-restoration.json',
               {'passed': restored, 'slots': self.slot_restoration,
                'production_installed': False})
        return result


_SIGNATURE.update({
    'PREVIEW': PREVIEW, 'OPTIONS': OPTIONS, 'VERSIONS': {'V4': '1'},
    'DESIGNS': DESIGNS, '_SHADERS': {'V4': _SHADER},
    'Signature': Hybrid, 'write': _write_hybrid,
})


def author(out):
    """Save only the two V4 preview surfaces; source hash proof is inherited."""
    return _hybrid_result(_author(out))


def sequence(rig):
    """Capture V_signature_V4_video via the unchanged signature rig contract."""
    key = 'SPARROW_V_SIGNATURE_OPTIONS'
    previous = os.environ.get(key)
    os.environ[key] = 'V4'
    try:
        yield from _sequence(rig)
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous
