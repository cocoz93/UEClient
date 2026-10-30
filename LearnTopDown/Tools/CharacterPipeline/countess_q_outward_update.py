"""Apply narrowly scoped native Q presentation wiring, preserving source encoding."""
import json
from baseline import PROJECT, digest

base = PROJECT/'Saved/QA/CharacterPipeline/countess-q-outward-20261016'
assert (base/'before-source-hashes.json').is_file(), 'Wait for the before snapshot'
before = json.loads((base/'before-source-hashes.json').read_text())
for relative in ('Source/LearnTopDown/CountessSkillComponent.cpp', 'Source/LearnTopDown/CountessSkillComponent.h'):
    assert digest(PROJECT/relative) == before[relative], 'This one-shot wiring requires the exact pre-edit source: ' + relative

def change(path, replacements):
    data = path.read_bytes()
    for old, new, count in replacements:
        old = old.replace('\n', '\r\n').encode('utf-8')
        new = new.replace('\n', '\r\n').encode('utf-8')
        assert data.count(old) == count, (path.name, old, data.count(old))
        data = data.replace(old, new)
    path.write_bytes(data)

change(PROJECT/'Source/LearnTopDown/CountessSkillComponent.h', [
    ('\tTObjectPtr<UStaticMesh> DualSweepMesh;', '\tTObjectPtr<UStaticMesh> DualSweepMesh;\n\tUPROPERTY()\n\tTObjectPtr<UMaterialInterface> OutwardCutMaterial;\n\tUPROPERTY()\n\tTObjectPtr<UStaticMesh> OutwardCutMesh;', 1)])
change(PROJECT/'Source/LearnTopDown/CountessSkillComponent.cpp', [
    ('TEXT("Countess.Skills.QPresentation"), 2,', 'TEXT("Countess.Skills.QPresentation"), 3,', 1),
    ('Q visuals only: 2 uses measured dual blade sweeps; 1 compares the previous crescent; 0 preserves the original.',
     'Q visuals only: 3 uses short outward cuts; 2 compares measured curves; 1 compares the crescent; 0 preserves the original.', 1),
    ('\tDualSweepMesh = DualSweepMeshAsset.Object;', '\tDualSweepMesh = DualSweepMeshAsset.Object;\n\tConstructorHelpers::FObjectFinder<UMaterialInterface> OutwardCutMaterialAsset(\n\t\tTEXT("/Game/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.M_CountessQOutwardCut"));\n\tOutwardCutMaterial = OutwardCutMaterialAsset.Object;\n\tConstructorHelpers::FObjectFinder<UStaticMesh> OutwardCutMeshAsset(\n\t\tTEXT("/Game/TopDown/Characters/Countess/FX/SM_CountessQOutwardCut.SM_CountessQOutwardCut"));\n\tOutwardCutMesh = OutwardCutMeshAsset.Object;', 1),
    ('CVarCountessQPresentation.GetValueOnGameThread() == 2', 'CVarCountessQPresentation.GetValueOnGameThread() >= 2', 2),
    ('\tif (!Character.IsValid() || !DualSweepMaterial || !DualSweepMesh || !BlinkAccentMesh)',
     '\tconst bool bOutwardCut = CVarCountessQPresentation.GetValueOnGameThread() >= 3;\n\tUMaterialInterface* SelectedMaterial = bOutwardCut ? OutwardCutMaterial.Get() : DualSweepMaterial.Get();\n\tUStaticMesh* SelectedMesh = bOutwardCut ? OutwardCutMesh.Get() : DualSweepMesh.Get();\n\tif (!Character.IsValid() || !SelectedMaterial || !SelectedMesh || !BlinkAccentMesh)', 1),
    ('UMaterialInstanceDynamic::Create(DualSweepMaterial, Owner)', 'UMaterialInstanceDynamic::Create(SelectedMaterial, Owner)', 1),
    ('\t\tAddVisual(Sweep, DualSweepMesh, Mesh->GetComponentLocation()',
     '\t\t// 새 표현은 소켓의 시작점과 좌우 방향만 사용한 짧은 직선 베기다.\n\t\tAddVisual(Sweep, SelectedMesh, Mesh->GetComponentLocation()', 1)])
print('Countess Q variant 3 wired; gameplay and other skill branches retained.')
