"""Snapshot current project and owned visual material before Q tone/cape polish."""
import json
import shutil
from baseline import PROJECT, digest

base = PROJECT/'Saved/QA/CharacterPipeline/q-tone-cape-20261016'
base.mkdir(parents=True,exist_ok=False)
shutil.copytree(PROJECT/'Source',base/'before/Source')
# Source keys are relative to the project, not the backup directory.
native = {p.relative_to(base/'before').as_posix():digest(p) for p in sorted((base/'before/Source').rglob('*')) if p.is_file()}
(base/'before-source-hashes.json').write_text(json.dumps(native,indent=2),encoding='utf-8')
files=[PROJECT/'LearnTopDown.uproject']
for folder in ('Content','Config'):
    files.extend(p for p in (PROJECT/folder).rglob('*') if p.is_file())
protected={p.relative_to(PROJECT).as_posix():digest(p) for p in sorted(files)}
(base/'baseline-before.json').write_text(json.dumps({'protected_hashes':protected},indent=2),encoding='utf-8')
material=PROJECT/'Content/TopDown/Characters/Countess/Materials/M_CountessQOutwardCut.uasset'
shutil.copy2(material,base/material.name)
print(json.dumps({'output':str(base),'protected_files':len(protected),'native_files':len(native)}),flush=True)
