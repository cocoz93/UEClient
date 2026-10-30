"""Launch a single hidden project editor with the shared renderer lock."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/CharacterPipeline'))
from render_lock import render_slot

parser = argparse.ArgumentParser()
parser.add_argument('--visible', action='store_true', help='Use a native window for the final pointer-input check')
parser.add_argument('--normal-startup', action='store_true', help='Keep the normal editor module checks enabled')
parser.add_argument('--output', type=Path, default=ROOT / 'Saved/QA/TrialTower/session-20261029')
arguments = parser.parse_args()
OUT = arguments.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
env = dict(os.environ, TRIAL_TOWER_OUTPUT=str(OUT), SPARROW_QA_OUTPUT=str(OUT))
env['UE-LocalDataCachePath'] = str(ROOT / 'Saved/CharacterPipelineDDC')
query = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -or $_.Name -like 'UnrealBuildTool*' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*') }).Count"
with render_slot(ROOT):
    check = subprocess.run(['powershell.exe', '-NoProfile', '-Command', query], capture_output=True, text=True)
    if check.returncode != 0 or check.stdout.strip() != '0':
        raise RuntimeError('Editor/build occupancy could not be confirmed empty: ' + check.stdout + check.stderr)
    args = [str(ENGINE), str(ROOT / 'LearnTopDown.uproject'), '-nop4', '-nosplash',
            '-NoLiveCoding', '-NoAutoSave', '-windowed', '-ResX=1600', '-ResY=900', '-ddc=InstalledNoZenLocalFallback',
            '-ShaderWorkingDir=' + str(ROOT / 'Saved/ShaderWork'), '-abslog=' + str(OUT / ('visible-editor.log' if arguments.visible else 'editor.log')),
            '-ExecCmds=py ' + (ROOT / 'Tools/TrialTower/editor_session.py').as_posix()]
    if not arguments.normal_startup:
        args.append('-unattended')
    if not arguments.visible:
        args.append('-RenderOffscreen')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 1 if arguments.visible else subprocess.SW_HIDE
    process = subprocess.Popen(args, env=env, startupinfo=startup)
    (OUT / 'process.json').write_text(json.dumps({'pid': process.pid, 'args': args}), encoding='utf-8')
    print(json.dumps({'pid': process.pid, 'output': str(OUT)}), flush=True)
    code = process.wait()
    (OUT / 'exit.json').write_text(json.dumps({'exit_code': code}), encoding='utf-8')
    print('Editor exited: ' + str(code), flush=True)
