"""Prepare source changes with exact anchors and preserve the native CRLF encoding."""
from pathlib import Path
import shutil, json, hashlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/QA/CharacterPipeline/countess-w-rim-20261016'
baseline=ROOT/'Saved/QA/CharacterPipeline/baseline-countess-w-rim-before-20261016/baseline.json'
data=json.loads(baseline.read_text(encoding='utf-8'))
assert len(data['protected_hashes'])==7013
shutil.copy2(baseline,OUT/'baseline-before.json')
prior_source=baseline.parent/'before/Source'
shutil.copytree(prior_source,OUT/'before-Source')
hashes={'Source/'+p.relative_to(prior_source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prior_source.rglob('*') if p.is_file()}
(OUT/'before-source-hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')

def edit(relative, changes):
    path=ROOT/relative
    raw=path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf') and b'\r\n' in raw
    text=raw.decode('utf-8').replace('\r\n','\n')
    for old,new in changes:
        assert text.count(old)==1,old
        text=text.replace(old,new)
    path.write_bytes(text.replace('\n','\r\n').encode('utf-8'))

edit('Source/LearnTopDown/CountessSkillComponent.h', [
    ('\tTObjectPtr<UParticleSystem> DetailedSiphonRing;', '\tTObjectPtr<UParticleSystem> DetailedSiphonRing;\n\tUPROPERTY()\n\tTObjectPtr<UParticleSystem> RimSiphonRing;')])
edit('Source/LearnTopDown/CountessSkillComponent.cpp', [
    ('TEXT("Countess.Skills.WPresentation"), 1,\n\tTEXT("W visuals only: 1 strengthens the original textured vortex; 0 preserves its previous density.")',
     'TEXT("Countess.Skills.WPresentation"), 2,\n\tTEXT("W visuals only: 2 fills the textured outer front; 1 compares the dense vortex; 0 preserves the original.")'),
    ('\tDetailedSiphonRing = DenseRing.Object;', '\tDetailedSiphonRing = DenseRing.Object;\n\tConstructorHelpers::FObjectFinder<UParticleSystem> RimRing(\n\t\tTEXT("/Game/TopDown/Characters/Countess/FX/P_CountessW_RimRing.P_CountessW_RimRing"));\n\tRimSiphonRing = RimRing.Object;'),
    ('\t\tUParticleSystemComponent* Ring = SpawnOwnedEffect(bDenseW && DetailedSiphonRing ?\n\t\t\tDetailedSiphonRing.Get() : Skills[1].CastEffect.Get(), GetFeetLocation(), Character->GetActorRotation());',
     '\t\tUParticleSystem* RingEffect = bDenseW && DetailedSiphonRing ? DetailedSiphonRing.Get() : Skills[1].CastEffect.Get();\n\t\tif (bDenseW && CVarCountessWPresentation.GetValueOnGameThread() >= 2 && RimSiphonRing)\n\t\t{\n\t\t\tRingEffect = RimSiphonRing.Get();\n\t\t}\n\t\tUParticleSystemComponent* Ring = SpawnOwnedEffect(RingEffect, GetFeetLocation(), Character->GetActorRotation());')])
