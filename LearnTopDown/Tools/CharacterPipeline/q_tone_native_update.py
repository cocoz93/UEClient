"""Wire the approved Q color-only material and half-length presentation controls."""
import json
from baseline import PROJECT,digest

base=PROJECT/'Saved/QA/CharacterPipeline/q-tone-cape-20261016'
before=json.loads((base/'before-source-hashes.json').read_text(encoding='utf-8'))
relative='Source/LearnTopDown/CountessSkillComponent.cpp'
path=PROJECT/relative
assert digest(path)==before[relative], 'Requires the exact pre-edit Countess source'
data=path.read_bytes()
edits=[
('static TAutoConsoleVariable<int32> CVarCountessWPresentation(',
 'static TAutoConsoleVariable<int32> CVarCountessQTone(\n\tTEXT("Countess.Skills.QTone"), 1,\n\tTEXT("Q color only: 1 matches muted blood-red effects; 0 compares the previous bright core."));\n\nstatic TAutoConsoleVariable<float> CVarCountessQLengthScale(\n\tTEXT("Countess.Skills.QLengthScale"), 0.52f,\n\tTEXT("Outward Q lateral visual length only, clamped to 0.35..1; damage and reach are unchanged."));\n\nstatic TAutoConsoleVariable<int32> CVarCountessWPresentation('),
('TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.M_CountessQOutwardCut")',
 'TEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardMuted.M_CountessQOutwardMuted")'),
('\t\tMaterial->SetScalarParameterValue(TEXT("Duration"), Duration);\n\t\tUStaticMeshComponent* Visual',
 '\t\tMaterial->SetScalarParameterValue(TEXT("Duration"), Duration);\n\t\tif (bOutwardCut)\n\t\t{\n\t\t\tMaterial->SetScalarParameterValue(TEXT("ToneMix"), static_cast<float>(FMath::Clamp(CVarCountessQTone.GetValueOnGameThread(), 0, 1)));\n\t\t}\n\t\tUStaticMeshComponent* Visual'),
('\t\t\tMesh->GetComponentScale(), 0.0f, Now - (bAtImpact ? 0.20f : 0.10f), 0.58f);',
 '\t\t\tMesh->GetComponentScale() * FVector(bOutwardCut ? FMath::Clamp(CVarCountessQLengthScale.GetValueOnGameThread(), 0.35f, 1.0f) : 1.0f, 1.0f, 1.0f),\n\t\t\t0.0f, Now - (bAtImpact ? 0.20f : 0.10f), 0.58f);'),
]
for old,new in edits:
    a,b=(value.replace('\n','\r\n').encode('utf-8') for value in (old,new))
    assert data.count(a)==1,(old,data.count(a))
    data=data.replace(a,b)
path.write_bytes(data)
(base/'countess-approved-edits.json').write_text(json.dumps(edits,indent=2),encoding='utf-8')
print('Q tone=muted; lateral visual length=52%; gameplay and mesh/alpha/timing retained.')
