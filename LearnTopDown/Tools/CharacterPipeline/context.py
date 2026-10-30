"""Shared execution context for editor scripts. Outputs live only under Saved/QA."""
import json
import os
from pathlib import Path

import unreal

root = Path(unreal.Paths.project_dir()).resolve()
job = json.loads(Path(os.environ['CHARACTER_PIPELINE_JOB']).read_text(encoding='utf-8'))
qa = Path(job['output']).resolve()
if not qa.is_relative_to(root / 'Saved/QA'):
    raise ValueError('Pipeline output must be inside this project Saved/QA')
qa.mkdir(parents=True, exist_ok=True)
profile = json.loads(Path(job['profile']).read_text(encoding='utf-8'))
fps = int(job['fps'])
protected = json.loads(Path(job['baseline']).read_text(encoding='utf-8'))['protected_hashes']
unreal.SystemLibrary.execute_console_command(None, 'CharacterPipeline.OutputDirectory "' + qa.as_posix() + '"')


def configure_practice(enabled):
    for name, value in profile.get('console_variables', {}).items():
        if name in ('Countess.Skills.IgnoreCooldowns', 'Sparrow.Skills.IgnoreCooldowns'):
            value = int(enabled)
        unreal.SystemLibrary.execute_console_command(None, name + ' ' + str(value))


def write_json(name, value):
    (qa / name).write_text(json.dumps(value, indent=2), encoding='utf-8')
