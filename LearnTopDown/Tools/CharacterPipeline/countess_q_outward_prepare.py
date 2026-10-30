"""Snapshot protected files and native source before the approved Q visual change."""
import json
import shutil
from baseline import PROJECT, digest

base = PROJECT / 'Saved/QA/CharacterPipeline/countess-q-outward-20261016'
base.mkdir(parents=True, exist_ok=False)
files = [PROJECT/'LearnTopDown.uproject']
for directory in ('Content', 'Config'):
    files += [p for p in (PROJECT/directory).rglob('*') if p.is_file()]
protected = {p.relative_to(PROJECT).as_posix(): digest(p) for p in sorted(files)}
(base/'baseline-before.json').write_text(json.dumps({'protected_hashes':protected}, indent=2))
native = {p.relative_to(PROJECT).as_posix():digest(p) for p in sorted((PROJECT/'Source').rglob('*')) if p.is_file()}
(base/'before-source-hashes.json').write_text(json.dumps(native, indent=2))
shutil.copytree(PROJECT/'Source', base/'before/Source')
print(json.dumps({'protected_files':len(protected), 'native_files':len(native), 'output':str(base)}))
